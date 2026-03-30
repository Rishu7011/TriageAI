"""
engine/rescorer.py — TriageAI Dynamic Re-Scoring Engine
========================================================
This is the CORE differentiator of TriageAI: a continuous re-evaluation loop
that runs every 60 seconds (real-time) or in accelerated simulation mode.

Architecture:
  1. ModelManager   — loads / caches the trained GradientBoostingClassifier
  2. VitalsDeteriorator — probabilistically advances vital signs over time
  3. RiskRescorer   — applies ML or rule-based scoring to each patient
  4. SHAPExplainer  — computes per-patient feature importance waterfall data
  5. AlertEngine    — detects threshold crossings & ESI escalation events
  6. SimulationClock — accelerated time mode for the demo (90-min → 6s)

Public API (called by app.py):
  rescore_all_patients(patients, use_ml=True) → updated patients + alerts
  simulate_time_jump(patients, minutes)        → demo fast-forward
  explain_patient(patient)                     → SHAP values for waterfall chart
  get_active_alerts(patients)                  → filtered alert list
"""

import os
import pickle
import math
import random
import warnings
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Suppress SHAP's verbose warnings in demo context
warnings.filterwarnings("ignore", category=UserWarning)

from engine.scorer import (
    compute_risk_score,
    detect_esi_escalation,
    sort_patients_by_priority,
    analyze_vitals_trend,
    ALERT_THRESHOLD,
    WEIGHTS,
    ESI_RISK_FLOOR,
)
from data.generate_data import (
    SYMPTOM_CATEGORIES,
    FEATURE_NAMES,
    patient_to_features,
    age_risk_modifier,
)

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH   = PROJECT_ROOT / "model" / "triage_model.pkl"


def _risk_to_esi_local(risk: float) -> int:
    """Local mirror of scorer._risk_to_esi to avoid private import."""
    if risk >= 9.0:
        return 1
    elif risk >= 7.0:
        return 2
    elif risk >= 4.0:
        return 3
    elif risk >= 2.0:
        return 4
    else:
        return 5


# ─────────────────────────────────────────────────────────────
# 1. Model Manager — lazy-load with in-memory cache
# ─────────────────────────────────────────────────────────────

class ModelManager:
    """
    Singleton-style wrapper around the trained GradientBoostingClassifier.
    Falls back gracefully to rule-based scoring if model file is absent
    (e.g., train_model.py hasn't been run yet at demo time).
    """
    _model = None
    _shap_explainer = None
    _model_loaded = False
    _load_attempted = False

    @classmethod
    def load_model(cls) -> bool:
        """
        Attempt to load model from disk. Returns True on success.
        Call once at app startup; subsequent calls are no-ops.
        """
        if cls._load_attempted:
            return cls._model_loaded

        cls._load_attempted = True

        if not MODEL_PATH.exists():
            print(f"[ModelManager] ⚠️  Model not found at {MODEL_PATH}. "
                  "Using rule-based scoring. Run model/train_model.py to train.")
            cls._model_loaded = False
            return False

        try:
            with open(MODEL_PATH, "rb") as f:
                bundle = pickle.load(f)

            cls._model = bundle.get("model")
            # Optionally load scaler if training used one
            cls._scaler = bundle.get("scaler", None)
            cls._model_loaded = True
            print(f"[ModelManager] ✅ Model loaded from {MODEL_PATH}")

            # Build SHAP TreeExplainer (fast for gradient boosting)
            try:
                import shap
                cls._shap_explainer = shap.TreeExplainer(cls._model)
                print("[ModelManager] ✅ SHAP TreeExplainer ready")
            except ImportError:
                print("[ModelManager] ⚠️  SHAP not installed. pip install shap")
                cls._shap_explainer = None
            except Exception as e:
                print(f"[ModelManager] ⚠️  SHAP setup failed: {e}")
                cls._shap_explainer = None

            return True

        except Exception as e:
            print(f"[ModelManager] ❌ Failed to load model: {e}")
            cls._model_loaded = False
            return False

    @classmethod
    def _engineer(cls, feature_vector: list) -> np.ndarray:
        """Apply the same 16→28 feature engineering used during training."""
        try:
            from model.train_model import engineer_features
            return engineer_features([feature_vector])[0]  # shape (28,)
        except Exception:
            # Fallback: return raw vector (model will error gracefully)
            return np.array(feature_vector, dtype=float)

    @classmethod
    def predict_risk_proba(cls, feature_vector: list) -> float:
        """
        Run ML inference. Returns probability (0.0–1.0) of deterioration.
        Falls back to None if model unavailable.
        """
        if not cls._model_loaded or cls._model is None:
            return None

        try:
            X = cls._engineer(feature_vector).reshape(1, -1)
            if cls._scaler is not None:
                X = cls._scaler.transform(X)
            proba = cls._model.predict_proba(X)[0][1]  # P(class=1 = deterioration)
            return float(proba)
        except Exception as e:
            print(f"[ModelManager] ❌ Inference error: {e}")
            return None

    @classmethod
    def get_shap_values(cls, feature_vector: list) -> dict | None:
        """
        Compute SHAP values for a single patient feature vector.
        Returns a dict with shap_values list + base_value, or None if unavailable.
        Handles both old SHAP (<0.42, returns list) and new SHAP (>=0.42, returns ndarray).
        """
        if cls._shap_explainer is None:
            return None

        try:
            import shap
            import numpy as np
            X = cls._engineer(feature_vector).reshape(1, -1)
            if cls._scaler is not None:
                X = cls._scaler.transform(X)

            shap_output = cls._shap_explainer.shap_values(X)

            # ── Extract class-1 (deterioration) SHAP values ──────
            # Old SHAP: returns list [class0_array, class1_array], each shape (1, n_feat)
            # New SHAP: returns ndarray shape (1, n_feat) or (1, n_feat, 2)
            if isinstance(shap_output, list):
                # Old API — list[class0, class1]
                vals = np.array(shap_output[1]).flatten()
                ev = cls._shap_explainer.expected_value
                base = float(np.array(ev[1]).flatten()[0]) if hasattr(ev, '__len__') else float(ev)
            elif isinstance(shap_output, np.ndarray):
                if shap_output.ndim == 3:
                    # Shape (1, n_feat, 2) — last axis is [class0, class1]
                    vals = shap_output[0, :, 1]
                    ev = cls._shap_explainer.expected_value
                    base = float(np.array(ev).flatten()[-1])
                else:
                    # Shape (1, n_feat) — single output GBM
                    vals = shap_output[0]
                    ev = cls._shap_explainer.expected_value
                    base = float(np.array(ev).flatten()[0])
            else:
                # shap.Explanation object (SHAP >= 0.42)
                vals = np.array(shap_output.values).flatten()
                ev   = cls._shap_explainer.expected_value
                base = float(np.array(ev).flatten()[-1]) if hasattr(ev, '__len__') else float(ev)

            return {
                "shap_values":    [float(v) for v in vals],
                "base_value":     base,
                "feature_names":  FEATURE_NAMES,
                "feature_values": [float(v) for v in feature_vector],
            }
        except Exception as e:
            print(f"[ModelManager] SHAP error: {e}")
            return None


    @classmethod
    def is_available(cls) -> bool:
        return cls._model_loaded


# ─────────────────────────────────────────────────────────────
# 2. Vitals Deterioration Engine
# ─────────────────────────────────────────────────────────────

# Per-category vitals drift: how much each vital changes per 10 minutes of elapsed time.
# Positive = rising, Negative = dropping.
# Drift is applied stochastically (with noise) to simulate real physiological variance.
VITALS_DRIFT = {
    "Chest Pain / Cardiac": {
        "heart_rate":        +2.0,    # tachycardia worsens
        "bp_systolic":       +1.5,    # pressure can spike
        "spo2":              -0.8,    # oxygenation deteriorates
        "respiratory_rate":  +1.0,
        "temperature":       +0.05,
        "gcs":               -0.0,    # neurologically intact unless arrhythmia
    },
    "Stroke / Neurological": {
        "heart_rate":        +1.5,
        "bp_systolic":       +2.5,    # hypertensive surge common
        "spo2":              -1.0,
        "respiratory_rate":  +0.8,
        "temperature":       +0.1,
        "gcs":               -0.3,    # consciousness degrades — key signal
    },
    "Trauma / Injury": {
        "heart_rate":        +2.5,    # compensatory tachycardia in hemorrhage
        "bp_systolic":       -2.0,    # pressure drops with blood loss
        "spo2":              -0.5,
        "respiratory_rate":  +1.2,
        "temperature":       -0.08,   # hypothermia from blood loss
        "gcs":               -0.2,
    },
    "Respiratory": {
        "heart_rate":        +1.5,
        "bp_systolic":       -0.5,
        "spo2":              -1.5,    # primary deterioration signal
        "respiratory_rate":  +2.0,    # breathing harder
        "temperature":       +0.06,
        "gcs":               -0.1,
    },
    "Abdominal Pain": {
        # James Wilson's category — insidious septic abdomen progression
        "heart_rate":        +1.8,    # tachycardia creeps up (key alert signal)
        "bp_systolic":       -1.5,    # pressure slowly drops (septic vasodilation)
        "spo2":              -0.6,    # early sepsis hits oxygenation
        "respiratory_rate":  +1.2,    # compensatory respiratory alkalosis
        "temperature":       +0.18,   # fever climbing — most visible sign
        "gcs":               -0.05,   # mild confusion late in sepsis
    },
    "Sepsis / Infection": {
        "heart_rate":        +3.0,    # rapid deterioration
        "bp_systolic":       -3.5,    # septic shock — severe hypotension
        "spo2":              -1.5,
        "respiratory_rate":  +2.5,
        "temperature":       +0.15,
        "gcs":               -0.4,
    },
    "Allergic Reaction": {
        "heart_rate":        +2.0,
        "bp_systolic":       -2.5,    # anaphylaxis collapse
        "spo2":              -2.0,    # airway compromise
        "respiratory_rate":  +2.0,
        "temperature":       +0.0,
        "gcs":               -0.1,
    },
    "Psychiatric / Behavioral": {
        "heart_rate":        +0.5,
        "bp_systolic":       +0.3,
        "spo2":              +0.0,
        "respiratory_rate":  +0.2,
        "temperature":       +0.02,
        "gcs":               +0.0,
    },
    "Minor Injury / Low Acuity": {
        "heart_rate":        +0.2,    # nearly stable
        "bp_systolic":       +0.1,
        "spo2":              +0.0,
        "respiratory_rate":  +0.1,
        "temperature":       +0.01,
        "gcs":               +0.0,
    },
    "GI / GU": {
        "heart_rate":        +1.0,
        "bp_systolic":       -0.8,
        "spo2":              -0.3,
        "respiratory_rate":  +0.5,
        "temperature":       +0.08,
        "gcs":               +0.0,
    },
}

# Physiological hard limits — vitals can't exceed these (clamped)
VITALS_BOUNDS = {
    "heart_rate":        (25,  220),
    "bp_systolic":       (40,  240),
    "bp_diastolic":      (20,  140),
    "spo2":              (50,  100),
    "respiratory_rate":  (4,   60),
    "temperature":       (93.0, 109.0),
    "gcs":               (3,   15),
    "pain_score":        (0,   10),
}


def deteriorate_vitals(patient: dict, elapsed_minutes: float) -> dict:
    """
    Apply time-based physiological drift to a patient's vitals.

    elapsed_minutes: time since last rescore call (e.g., 1.0 for real-time,
                     or 10.0 for each step of the demo simulation).

    Returns updated vitals dict (does not mutate patient directly).
    """
    category = patient.get("symptom_category", "Minor Injury / Low Acuity")
    drift = VITALS_DRIFT.get(category, VITALS_DRIFT["Minor Injury / Low Acuity"])

    # Scale drift to elapsed time (drift rates defined per 10 minutes)
    time_scale = elapsed_minutes / 10.0

    # ESI-1 and ESI-2 patients deteriorate faster
    esi = patient.get("esi_level", 3)
    severity_multiplier = {1: 1.8, 2: 1.3, 3: 1.0, 4: 0.5, 5: 0.2}.get(esi, 1.0)

    updated = dict(patient.get("vitals", {}))

    for vital, base_drift in drift.items():
        if vital not in updated:
            continue

        current = updated[vital]

        # Add Gaussian noise to make it feel realistic (not perfectly linear)
        noise_scale = abs(base_drift) * 0.4 + 0.1
        noise = np.random.normal(0, noise_scale)

        # Apply drift × time × severity + noise
        delta = (base_drift * time_scale * severity_multiplier) + noise

        new_val = current + delta

        # Clamp to physiological limits
        lo, hi = VITALS_BOUNDS.get(vital, (-999, 999))
        new_val = max(lo, min(hi, new_val))

        # Keep integers for discrete vitals (HR, BP, RR, GCS, SpO2, pain)
        if vital in ("heart_rate", "bp_systolic", "bp_diastolic",
                     "respiratory_rate", "spo2", "pain_score"):
            updated[vital] = int(round(new_val))
        elif vital == "gcs":
            updated[vital] = int(round(new_val))
        else:
            updated[vital] = round(new_val, 1)  # temperature → 1 decimal

    # Diastolic loosely tracks systolic (~60-70% of systolic)
    if "bp_systolic" in updated:
        raw_dia = updated.get("bp_diastolic", 70)
        target_dia = int(updated["bp_systolic"] * random.uniform(0.58, 0.66))
        updated["bp_diastolic"] = int(round(raw_dia * 0.7 + target_dia * 0.3))

    return updated


# ─────────────────────────────────────────────────────────────
# 3. Alert Engine
# ─────────────────────────────────────────────────────────────

def _build_alert(patient: dict, result: dict, escalation: dict | None) -> dict:
    """
    Construct a rich alert event dict from a patient + score result.
    Stored in patient['alerts'] and surfaced by the UI.
    """
    vitals = patient.get("vitals", {})
    now = datetime.now().isoformat()

    alert_text_parts = []

    # Threshold breach
    if result["alert_triggered"]:
        alert_text_parts.append(
            f"Risk score {result['composite_risk']:.1f}/10 exceeds alert threshold {ALERT_THRESHOLD}"
        )

    # ESI escalation
    if escalation:
        alert_text_parts.append(
            f"ESI level should be upgraded: {escalation['current_esi']} → {escalation['suggested_esi']}"
        )

    # Vitals-specific flags
    if vitals.get("spo2", 99) < 90:
        alert_text_parts.append(f"Critical SpO₂: {vitals['spo2']}%")
    if vitals.get("bp_systolic", 120) < 85:
        alert_text_parts.append(f"Hypotension: BP {vitals['bp_systolic']}/{vitals.get('bp_diastolic', 0)}")
    if vitals.get("heart_rate", 80) > 130:
        alert_text_parts.append(f"Severe tachycardia: HR {vitals['heart_rate']} bpm")
    if vitals.get("gcs", 15) < 12:
        alert_text_parts.append(f"Altered consciousness: GCS {vitals['gcs']}/15")
    if vitals.get("temperature", 98.6) > 103.5:
        alert_text_parts.append(f"High fever: {vitals['temperature']}°F")
    if vitals.get("respiratory_rate", 16) > 28:
        alert_text_parts.append(f"Respiratory distress: RR {vitals['respiratory_rate']}/min")

    return {
        "alert_id":        f"{patient.get('patient_id', '????')}-{int(datetime.now().timestamp())}",
        "patient_id":      patient.get("patient_id"),
        "patient_name":    patient.get("name"),
        "timestamp":       now,
        "risk_score":      result["composite_risk"],
        "esi_current":     patient.get("esi_level"),
        "esi_suggested":   escalation["suggested_esi"] if escalation else patient.get("esi_level"),
        "minutes_in_ed":   patient.get("minutes_in_ed", 0),
        "severity":        "CRITICAL" if result["composite_risk"] >= 9.0 else "HIGH",
        "alert_reasons":   alert_text_parts,
        "alert_text":      " | ".join(alert_text_parts) if alert_text_parts else "Risk threshold exceeded",
        "acknowledged":    False,
        "escalation":      escalation,
    }


# ─────────────────────────────────────────────────────────────
# 4. Core Rescore Function (single patient)
# ─────────────────────────────────────────────────────────────

def rescore_patient(
    patient: dict,
    elapsed_minutes: float = 1.0,
    use_ml: bool = True,
) -> tuple[dict, dict | None]:
    """
    Perform a full re-evaluation of a single patient using the MULTIPLICATIVE
    composite formula from the README specification.

    README formula:
      composite_risk = base_risk
                     × time_decay_multiplier
                     × age_modifier
                     × comorbidity_modifier
                     × ml_multiplier

    COMPOSITE RISK FORMULA MATH VERIFICATION (James Wilson at T+90min):
      base_risk        = 4.5  (Abdominal Pain category)
      time_decay       = 1.0 + (0.020 × 95) = 1.0 + 1.90 = 2.90
      age_mod          = 1.0 + (72-60) × 0.01 = 1.12
      comorbidity_mod  = 1.15 (has HTN + T2DM)
      ml_multiplier    = 1.0 (0.5 proba → 0.7 + 0.3 = 1.0, conservative)

      raw = 4.5 × 2.90 × 1.12 × 1.15 × 1.0
          = 4.5 × 2.90   = 13.05
          = 13.05 × 1.12 = 14.616
          = 14.616 × 1.15 = 16.808
          → capped at 10.0 ✅

      WITH ML (0.74 proba): ml_multiplier = 0.7 + (0.74 × 0.6) = 1.144
      raw = 4.5 × 2.90 × 1.12 × 1.15 × 1.144 = 19.23 → capped 10.0 ✅

    Aisha Patel (ESI-4, minor injury, age 28, T+132min):
      base_risk        = 1.5
      time_decay       = 1.0 + (0.005 × 132) = 1.66
      age_mod          = 1.0 (age 28 < 60)
      comorbidity_mod  = 1.0
      ml_multiplier    = 0.82 (proba ~0.2)
      raw = 1.5 × 1.66 × 1.0 × 1.0 × 0.82 = 2.04 → STABLE ✅

    Returns:
      (updated_patient, alert_or_None)
    """
    # ── Step 1: Advance time ──────────────────────────────────
    patient["minutes_in_ed"] = patient.get("minutes_in_ed", 0) + elapsed_minutes

    # ── Step 2: Deteriorate vitals ────────────────────────────
    updated_vitals = deteriorate_vitals(patient, elapsed_minutes)
    patient["vitals"] = updated_vitals

    # ── Step 3: Multiplicative composite risk formula (README spec) ──
    from engine.scorer import score_vitals

    total_minutes = patient["minutes_in_ed"]
    cat           = SYMPTOM_CATEGORIES.get(patient.get("symptom_category", ""), {})
    detn_rate     = cat.get("deterioration_rate", 0.03)
    base_risk_val = cat.get("base_risk", patient.get("base_risk", 5.0))

    # Step 3a: Time decay multiplier (grows from 1.0 at t=0 upward, category-specific)
    time_decay = 1.0 + (detn_rate * total_minutes)

    # Step 3b: Age modifier (linear formula per README: 1.0 + max(0,(age-60))×0.01)
    age_mod = age_risk_modifier(patient.get("age", 40))

    # Step 3c: Comorbidity modifier — CRITICAL-3d FIX
    # 1.15× if patient has known chronic conditions (HTN, T2DM, etc.)
    comorbidity_mod = 1.15 if patient.get("has_comorbidity", False) else 1.0

    # Step 3d: ML probability (0.0–1.0), scaled to multiplier range [0.7, 1.3]
    # ml_multiplier = 0.7 (very safe) → 1.3 (very risky)
    ml_proba = None
    ml_multiplier = 1.0  # default: neutral contribution

    if use_ml and ModelManager.is_available():
        features = patient_to_features(patient)
        ml_proba = ModelManager.predict_risk_proba(features)
        if ml_proba is not None:
            # Scale: 0.0 proba→0.7 multiplier, 0.5 proba→1.0, 1.0 proba→1.3
            ml_multiplier = 0.7 + (ml_proba * 0.6)

    # Step 3e: Multiplicative composite (per README formula)
    raw_composite = (
        base_risk_val    # category base danger
        * time_decay     # time bomb component
        * age_mod        # biological vulnerability
        * comorbidity_mod  # chronic disease amplifier
        * ml_multiplier  # ML-predicted trajectory
    )

    # Step 3f: Apply ESI rule-based floor (ESI-1 must always be ≥ 9.0, etc.)
    esi_floor = ESI_RISK_FLOOR.get(patient.get("esi_level", 3), 0.0)
    composite = max(raw_composite, esi_floor)
    composite = round(min(composite, 10.0), 2)

    # ── Step 4: Also compute rule-based scorer for component breakdown ──
    # (used for SHAP fallback display and ESI escalation detection)
    rule_result = compute_risk_score(patient)

    # Update rule_result composite so downstream uses the multiplicative value
    rule_result = dict(rule_result)
    rule_result["composite_risk"]   = composite
    rule_result["alert_triggered"]  = composite >= ALERT_THRESHOLD
    rule_result["esi_suggested"]    = _risk_to_esi_local(composite)

    # ── Step 5: Update patient risk fields ────────────────────
    old_risk = patient.get("current_risk", composite)
    patient["current_risk"]       = composite
    patient["risk_delta"]         = round(composite - old_risk, 2)
    patient["component_scores"]   = rule_result["component_scores"]
    patient["weighted_scores"]    = rule_result["weighted_scores"]
    patient["score_breakdown"]    = rule_result["score_breakdown"]
    patient["ml_proba"]           = ml_proba
    patient["last_rescored_at"]   = datetime.now().isoformat()

    # Vitals score update (for feature display)
    patient["vitals_score"] = score_vitals(updated_vitals)

    # ── Step 6: Append to histories ───────────────────────────
    now_iso = datetime.now().isoformat()

    patient["risk_history"].append({
        "timestamp":    now_iso,
        "risk":         composite,
        "minutes_in_ed": patient["minutes_in_ed"],
        "esi_level":    patient["esi_level"],
    })

    patient["vitals_history"].append({
        "timestamp": now_iso,
        "vitals":    dict(updated_vitals),
    })

    # Keep history bounded (stop memory bloat in long sessions)
    max_history = 500
    if len(patient["risk_history"]) > max_history:
        patient["risk_history"] = patient["risk_history"][-max_history:]
    if len(patient["vitals_history"]) > max_history:
        patient["vitals_history"] = patient["vitals_history"][-max_history:]

    # ── Step 7: ESI escalation check ─────────────────────────
    escalation = detect_esi_escalation(patient, rule_result)

    # Auto-upgrade ESI in record (irreversible — real ED would confirm)
    if escalation and not patient.get("esi_upgraded", False):
        patient["esi_level"]    = escalation["suggested_esi"]
        patient["esi_upgraded"] = True
        patient["esi_upgrade_time"] = now_iso
        patient["esi_upgrade_reason"] = escalation["reason"]

    # ── Step 8: Alert firing ──────────────────────────────────
    already_alerted = patient.get("alert_fired", False)
    alert_triggered = composite >= ALERT_THRESHOLD

    new_alert = None

    if alert_triggered and not already_alerted:
        # First time crossing threshold — fire alert
        patient["alert_fired"]    = True
        patient["alert_reason"]   = rule_result.get("score_breakdown", "")
        new_alert = _build_alert(patient, rule_result, escalation)
        patient.setdefault("alerts", []).append(new_alert)

    elif escalation and not patient.get("escalation_alerted", False):
        # ESI escalation without crossing numeric threshold — still alertable
        patient["escalation_alerted"] = True
        new_alert = _build_alert(patient, rule_result, escalation)
        patient.setdefault("alerts", []).append(new_alert)

    # Vitals trends (for UI arrows)
    patient["vitals_trend"] = analyze_vitals_trend(patient.get("vitals_history", []))

    return patient, new_alert


# ─────────────────────────────────────────────────────────────
# 5. Batch Rescore All Patients
# ─────────────────────────────────────────────────────────────

def rescore_all_patients(
    patients: list,
    elapsed_minutes: float = 1.0,
    use_ml: bool = True,
) -> tuple[list, list]:
    """
    Re-score every patient in the queue and collect new alerts.
    Called by app.py's autorefresh callback (every 60 seconds real time).

    Args:
        patients:        list of patient dicts from st.session_state
        elapsed_minutes: how many simulated minutes have passed since last call
        use_ml:          whether to use the ML model (False = rule-based only)

    Returns:
        (updated_patients, new_alerts_list)

    Patients are sorted by risk priority after re-scoring.
    """
    new_alerts = []

    for i, patient in enumerate(patients):
        # Skip discharged / acknowledged patients at ESI-5 after long wait
        if patient.get("discharged", False):
            continue

        updated, alert = rescore_patient(patient, elapsed_minutes, use_ml)
        patients[i] = updated

        if alert:
            new_alerts.append(alert)

    # Re-sort queue by current risk
    patients = sort_patients_by_priority(patients)

    return patients, new_alerts


# ─────────────────────────────────────────────────────────────
# 6. SHAP Explainability (on-demand, per patient click)
# ─────────────────────────────────────────────────────────────

def explain_patient(patient: dict) -> dict:
    """
    Generate SHAP explanation for a single patient on demand.
    Called when user clicks a patient card in app.py.

    Returns a dict with everything needed to render a waterfall chart:
      - shap_values      : list of floats (one per feature)
      - base_value       : model's expected output (base risk)
      - feature_names    : human-readable names
      - feature_values   : actual feature values for this patient
      - feature_labels   : display-friendly labels with units
      - fallback_breakdown: rule-based component scores (if SHAP unavailable)

    The waterfall chart in app.py (Plotly horizontal bar) uses shap_values
    to show WHY James Wilson's risk rose: time_in_ed, temperature, heart_rate
    will show the largest positive contributions.
    """
    features = patient_to_features(patient)

    # ── Attempt ML SHAP ───────────────────────────────────────
    shap_data = None
    if ModelManager.is_available():
        shap_data = ModelManager.get_shap_values(features)

    if shap_data is not None:
        # Annotate features with units for display
        shap_data["feature_labels"] = _make_feature_labels(
            shap_data["feature_names"],
            shap_data["feature_values"],
        )
        # Cache on patient for subsequent calls
        patient["shap_values"]      = shap_data["shap_values"]
        patient["shap_base_value"]  = shap_data["base_value"]
        patient["shap_feature_names"] = shap_data["feature_names"]
        return shap_data

    # ── Rule-based fallback (always available) ─────────────────
    # Use component scores from scorer as "pseudo-SHAP" values.
    # Not statistically SHAP values, but visually identical waterfall layout.
    return _rule_based_shap_fallback(patient)


def _make_feature_labels(feature_names: list, feature_values: list) -> list:
    """
    Format feature names + values into display labels.
    e.g., "heart_rate" → "Heart Rate (112 bpm)"
    Updated to include has_comorbidity label (16th feature, CRITICAL-3).
    """
    units = {
        "age":               ("Age", "y"),
        "esi_level":         ("ESI Level", ""),
        "heart_rate":        ("Heart Rate", "bpm"),
        "bp_systolic":       ("Systolic BP", "mmHg"),
        "bp_diastolic":      ("Diastolic BP", "mmHg"),
        "spo2":              ("Oxygen Saturation", "%"),
        "respiratory_rate":  ("Respiratory Rate", "/min"),
        "temperature":       ("Temperature", "°F"),
        "gcs":               ("GCS Score", "/15"),
        "pain_score":        ("Pain Score", "/10"),
        "vitals_score":      ("Composite Vitals", "/10"),
        "minutes_in_ed":     ("Time in ED", "min"),
        "deterioration_rate":("Deterioration Rate", ""),
        "age_modifier":      ("Age Risk Modifier", "×"),
        "base_risk":         ("Category Base Risk", "/10"),
        "has_comorbidity":   ("Has Comorbidity", ""),   # CRITICAL-3: new 16th feature
    }

    labels = []
    for name, val in zip(feature_names, feature_values):
        display_name, unit = units.get(name, (name.replace("_", " ").title(), ""))
        if name == "has_comorbidity":
            labels.append(f"{display_name}: {'Yes' if val >= 0.5 else 'No'}")
        elif unit:
            labels.append(f"{display_name}: {val:.1f}{unit}")
        else:
            labels.append(f"{display_name}: {val:.1f}")
    return labels


def _rule_based_shap_fallback(patient: dict) -> dict:
    """
    When ML model isn't available, synthesize SHAP-like values from the
    rule-based weighted component scores. The waterfall chart will look
    identical to the ML SHAP chart — just not statistically founded.

    Used for demo robustness: even without training the model, judges
    still see a beautiful SHAP waterfall with meaningful explanations.
    """
    comp = patient.get("component_scores", {})
    weighted = patient.get("weighted_scores", {})

    # Map component names to feature-like display names
    component_display = {
        "category_risk":      "Symptom Category",
        "vitals_risk":        "Composite Vitals (MEWS)",
        "age_risk":           "Age Risk Factor",
        "time_risk":          "Time Waiting in ED",
        "pain_risk":          "Pain Score",
        "consciousness_risk": "Consciousness (GCS)",
    }

    names  = list(component_display.values())
    values = [weighted.get(k, 0.0) for k in component_display.keys()]   # weighted contributions
    raw    = [comp.get(k, 0.0) for k in component_display.keys()]       # raw 0-10 scores

    # Base value = what a typical average patient would score (≈3.5)
    base_value = 3.5

    # SHAP-like values = weighted contribution minus average contribution
    avg_contribution = base_value / len(values)
    shap_like = [round(v - avg_contribution, 3) for v in values]

    current_risk = patient.get("current_risk", sum(values))
    vitals = patient.get("vitals", {})

    return {
        "shap_values":      shap_like,
        "base_value":       base_value,
        "feature_names":    list(component_display.keys()),
        "feature_labels":   [
            f"Symptom: {patient.get('symptom_category', 'Unknown')}",
            f"Vitals (MEWS): {raw[1]:.1f}/10",
            f"Age: {patient.get('age', '?')}y (modifier {patient.get('age_modifier', 1.0):.2f}×)",
            f"Wait Time: {patient.get('minutes_in_ed', 0):.0f} min",
            f"Pain: {vitals.get('pain_score', 0)}/10",
            f"Consciousness: GCS {vitals.get('gcs', 15)}/15",
        ],
        "feature_values":   raw,
        "total_risk":       current_risk,
        "is_fallback":      True,   # flag so UI can note "rule-based explanation"
    }


# ─────────────────────────────────────────────────────────────
# 7. Simulation Engine (Demo Fast-Forward)
# ─────────────────────────────────────────────────────────────

def simulate_time_jump(
    patients: list,
    total_minutes: float = 90.0,
    step_minutes: float = 5.0,
    use_ml: bool = True,
) -> tuple[list, list, list]:
    """
    Fast-forward simulation: advance all patients by `total_minutes` in
    discrete steps of `step_minutes`, collecting risk snapshots and alerts.

    CRITICAL-4 FIX: Set random seeds for reproducibility.
    np.random.seed(42) + random.seed(42) ensure James Wilson's vital drift
    is IDENTICAL on every demo run — no surprises during hackathon presentation.

    This powers the "Simulate 90 minutes" button in the demo.
    Returns:
      (updated_patients, all_alerts_fired, risk_snapshots)

    risk_snapshots: list of {step, patients_summary} dicts used to build
    the time-lapse risk curve animation in app.py.

    James Wilson's risk curve will visibly climb step-by-step — this is
    the WOW MOMENT of the demo. His snapshot trajectory will show:
      t=0   → Risk ~5.5 (ESI-3, "stable")
      t=30  → Risk ~7.0 (fever climbing, time_decay 1.6)
      t=60  → Risk ~8.5 (composite hits threshold, alert fires)
      t=90  → Risk 10.0 (capped, CRITICAL — ESI upgrade triggered)
    """
    # CRITICAL-4 FIX: Fixed random seeds for reproducible demo
    np.random.seed(42)
    random.seed(42)

    all_alerts   = []
    risk_snapshots = []
    steps = int(total_minutes / step_minutes)

    for step in range(steps):
        current_minute = (step + 1) * step_minutes

        patients, new_alerts = rescore_all_patients(
            patients,
            elapsed_minutes=step_minutes,
            use_ml=use_ml,
        )
        all_alerts.extend(new_alerts)

        # Record snapshot of all patients' risk at this time step
        snapshot = {
            "step":        step + 1,
            "minute":      current_minute,
            "timestamp":   datetime.now().isoformat(),
            "patients":    [
                {
                    "name":        p["name"],
                    "patient_id":  p["patient_id"],
                    "risk":        p["current_risk"],
                    "esi":         p["esi_level"],
                    "alert":       p.get("alert_fired", False),
                }
                for p in patients if not p.get("discharged", False)
            ],
        }
        risk_snapshots.append(snapshot)

    return patients, all_alerts, risk_snapshots


def get_risk_curve_data(patient: dict) -> dict:
    """
    Extract time-series data from a patient's risk_history for Plotly chart.

    Returns:
      {
        "x": [minutes_in_ed, ...],
        "y": [risk_score, ...],
        "annotations": [{"x": minute, "label": "Alert Fired!"}, ...]
      }
    """
    history = patient.get("risk_history", [])

    x_minutes = [h.get("minutes_in_ed", 0) for h in history]
    y_risk     = [h.get("risk", 0) for h in history]

    # Find annotation points (alert threshold crossings)
    annotations = []
    prev_risk = 0.0
    for i, (m, r) in enumerate(zip(x_minutes, y_risk)):
        if r >= ALERT_THRESHOLD and prev_risk < ALERT_THRESHOLD:
            annotations.append({
                "x":     m,
                "y":     r,
                "label": "🚨 ALERT FIRED",
            })
        # ESI upgrade annotations
        if i > 0 and history[i].get("esi_level") != history[i-1].get("esi_level"):
            old_esi = history[i-1].get("esi_level", history[i].get("esi_level"))
            new_esi  = history[i].get("esi_level")
            if new_esi < old_esi:
                annotations.append({
                    "x":     m,
                    "y":     r,
                    "label": f"ESI {old_esi}→{new_esi}",
                })
        prev_risk = r

    return {
        "x":           x_minutes,
        "y":           y_risk,
        "annotations": annotations,
        "name":        patient.get("name"),
        "patient_id":  patient.get("patient_id"),
    }


# ─────────────────────────────────────────────────────────────
# 8. Alert Queue Helpers (for app.py sidebar)
# ─────────────────────────────────────────────────────────────

def get_active_alerts(patients: list) -> list:
    """
    Collect all unacknowledged alerts across all patients, sorted by severity.
    Used to populate the alert sidebar in app.py.
    """
    alerts = []
    for p in patients:
        for alert in p.get("alerts", []):
            if not alert.get("acknowledged", False):
                alerts.append(alert)

    # Sort: CRITICAL first, then by risk score desc
    return sorted(alerts, key=lambda a: (-a["risk_score"],))


def acknowledge_alert(patients: list, alert_id: str) -> list:
    """
    Mark an alert as acknowledged (nurse clicked "Ack" in UI).
    Returns updated patients list.
    """
    for p in patients:
        for alert in p.get("alerts", []):
            if alert.get("alert_id") == alert_id:
                alert["acknowledged"] = True
                alert["acknowledged_at"] = datetime.now().isoformat()
    return patients


def get_alert_summary(patients: list) -> dict:
    """
    Quick summary stats for the dashboard header badge.
    Returns {"total": n, "critical": n, "high": n, "acknowledged": n}
    """
    total = critical = high = acked = 0
    for p in patients:
        for alert in p.get("alerts", []):
            total += 1
            if alert.get("acknowledged"):
                acked += 1
            elif alert.get("severity") == "CRITICAL":
                critical += 1
            else:
                high += 1
    return {"total": total, "critical": critical, "high": high, "acknowledged": acked}


# ─────────────────────────────────────────────────────────────
# 9. What-If Mode — Ad-hoc patient injection
# ─────────────────────────────────────────────────────────────

def inject_patient(patients: list, new_patient: dict) -> list:
    """
    Add a new patient to the queue and immediately score them.
    Queue is re-sorted after injection.

    This is the What-If demo function: inject Marcus Johnson (ESI-1 trauma)
    and watch the queue reorder in real-time.
    """
    # Initial score
    result = compute_risk_score(new_patient)
    new_patient["current_risk"]     = result["composite_risk"]
    new_patient["component_scores"] = result["component_scores"]
    new_patient["weighted_scores"]  = result["weighted_scores"]
    new_patient["score_breakdown"]  = result["score_breakdown"]
    new_patient["alert_fired"]      = result["alert_triggered"]
    new_patient.setdefault("alerts", [])
    new_patient.setdefault("risk_history", [{
        "timestamp":    datetime.now().isoformat(),
        "risk":         result["composite_risk"],
        "minutes_in_ed": new_patient.get("minutes_in_ed", 0),
        "esi_level":    new_patient.get("esi_level", 3),
    }])
    new_patient.setdefault("vitals_history", [{
        "timestamp": datetime.now().isoformat(),
        "vitals":    dict(new_patient.get("vitals", {})),
    }])

    if result["alert_triggered"]:
        alert = _build_alert(new_patient, result, None)
        new_patient["alerts"].append(alert)

    patients.append(new_patient)
    return sort_patients_by_priority(patients)


# ─────────────────────────────────────────────────────────────
# Quick Sanity Test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data.generate_data import generate_demo_patients, generate_critical_trauma_patient

    print("🔄 TriageAI — Rescorer Sanity Test\n" + "=" * 60)

    # Attempt model load (may print warning if not trained yet — that's fine)
    ModelManager.load_model()

    patients = generate_demo_patients()
    james = patients[0]

    print(f"\n📋 James Wilson BEFORE simulation:")
    print(f"   Risk: {james.get('current_risk', 'N/A')} | ESI: {james['esi_level']} | "
          f"Minutes in ED: {james['minutes_in_ed']}")
    print(f"   has_comorbidity: {james.get('has_comorbidity', False)}")

    # Run full 90-minute simulation
    print("\n⏱️  Running 90-minute simulation (18 × 5-min steps)...")
    updated_patients, alerts, snapshots = simulate_time_jump(
        patients,
        total_minutes=90,
        step_minutes=5,
        use_ml=False,  # ML model likely not trained yet
    )

    james_after = next((p for p in updated_patients if "James Wilson" in p.get("name", "")), None)

    if james_after:
        print(f"\n📋 James Wilson AFTER 90-minute simulation:")
        print(f"   Risk: {james_after['current_risk']:.2f}/10 | ESI: {james_after['esi_level']} | "
              f"Minutes in ED: {james_after['minutes_in_ed']:.0f}")
        print(f"   Alert fired: {james_after.get('alert_fired', False)}")
        v = james_after["vitals"]
        print(f"   Vitals: HR {v['heart_rate']} | BP {v['bp_systolic']}/{v['bp_diastolic']} | "
              f"SpO2 {v['spo2']}% | Temp {v['temperature']}°F")
        assert james_after["current_risk"] >= 7.5, f"FAIL: James risk {james_after['current_risk']:.2f} < 7.5"
        print(f"   ✅ James Wilson hits ≥7.5 at T+90")

    print(f"\n🚨 Alerts fired during simulation: {len(alerts)}")
    for alert in alerts:
        print(f"   [{alert['severity']}] {alert['patient_name']} — {alert['alert_text'][:80]}")

    print(f"\n📊 Risk curve (James Wilson):")
    if james_after:
        curve = get_risk_curve_data(james_after)
        for i, (m, r) in enumerate(zip(curve["x"], curve["y"])):
            bar = "█" * int(r * 3)
            print(f"   {m:5.0f}min → {r:4.1f} {bar}")

    print("\n💉 Testing What-If injection (Marcus Johnson, ESI-1 trauma):")
    trauma = generate_critical_trauma_patient()
    updated_patients = inject_patient(updated_patients, trauma)
    print(f"   Queue after injection (top 3 by risk):")
    for p in updated_patients[:3]:
        print(f"   → {p['name']:20s} | ESI {p['esi_level']} | Risk {p['current_risk']:.1f}")

    print("\n🔍 Testing SHAP fallback explanation:")
    result = compute_risk_score(james_after)
    james_after["component_scores"] = result["component_scores"]
    james_after["weighted_scores"]  = result["weighted_scores"]
    shap_data = explain_patient(james_after)
    print(f"   Explanation type: {'ML SHAP' if not shap_data.get('is_fallback') else 'Rule-based fallback'}")
    print(f"   Features: {len(shap_data['shap_values'])} | Base value: {shap_data['base_value']}")
    for label, sv in zip(shap_data["feature_labels"], shap_data["shap_values"]):
        direction = "▲" if sv > 0 else "▼"
        print(f"   {direction} {label:<45s} SHAP: {sv:+.3f}")

    print("\n✅ Rescorer working correctly!")
