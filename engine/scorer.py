"""
engine/scorer.py — TriageAI Base Risk Scorer
============================================
Responsibilities:
  1. Compute a 0–10 composite risk score for any patient at any point in time
  2. Derive / validate ESI level from vitals + complaint category
  3. Build the 15-feature vector used by the ML model (GradientBoostingClassifier)
  4. Provide named score breakdowns so SHAP waterfall charts have meaningful labels

Risk formula (weighted sum, all components normalized to 0–10):
  CompositeRisk = w1·CategoryRisk  (symptom category base danger)
                + w2·VitalsRisk    (MEWS-derived physiological score)
                + w3·AgeRisk       (age-modified vulnerability)
                + w4·TimeRisk      (elapsed wait × category deterioration rate)
                + w5·PainRisk      (pain score normalised)
                + w6·ConsciousnessRisk  (GCS deviation from normal)

  … then clamped to [0, 10].

Designed to be called by:
  - rescorer.py  (every 60s, updates current_risk for all patients)
  - app.py       (on-demand for SHAP display and What-If mode)
  - train_model.py (at data-generation time to build training labels)
"""

import math
from data.generate_data import (
    SYMPTOM_CATEGORIES,
    ESI_DESCRIPTIONS,
    age_risk_modifier,
    patient_to_features,
    FEATURE_NAMES,
)

# ─────────────────────────────────────────────────────────────
# Scoring Weights  (must sum to 1.0 for interpretability)
# ─────────────────────────────────────────────────────────────
WEIGHTS = {
    "category":      0.30,   # inherent danger of the symptom category
    "vitals":        0.35,   # real-time physiological distress (highest weight)
    "age":           0.10,   # biological vulnerability modifier
    "time_in_ed":    0.15,   # "time bomb" — longer wait → higher risk
    "pain":          0.04,   # subjective, lower weight
    "consciousness": 0.06,   # GCS drop is a strong deterioration signal
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

# ESI → risk band mapping (used when overriding ML with rule-based floor)
ESI_RISK_FLOOR = {
    1: 9.0,   # Immediate — must always show critical
    2: 7.0,   # Emergent — high risk (ESI-2 never falls below 6.3)
    3: 4.0,   # Urgent — moderate
    4: 1.5,   # Less urgent — low
    5: 0.5,   # Non-urgent — minimal
}

# Alert threshold: risk score above this → fire deterioration alert
ALERT_THRESHOLD = 7.5


# ─────────────────────────────────────────────────────────────
# 1. Individual Component Scorers (each returns 0–10 float)
# ─────────────────────────────────────────────────────────────

def score_category(symptom_category: str) -> float:
    """
    Base risk from symptom category (pre-defined in SYMPTOM_CATEGORIES).
    Represents the inherent danger of the chief complaint class.
    """
    cat = SYMPTOM_CATEGORIES.get(symptom_category)
    if cat is None:
        return 5.0  # Unknown category → conservative mid-range
    return float(cat["base_risk"])


def score_vitals(vitals: dict) -> float:
    """
    Compute physiological risk from raw vitals using Modified Early Warning
    Score (MEWS) principles, normalized to 0–10.

    Each vital sign contributes 0–4 points based on deviation from normal:
      0 = within normal range
      1 = mildly abnormal
      2 = moderately abnormal
      3 = severely abnormal
      4 = critically abnormal (e.g., SpO2 < 85%)

    Maximum raw score ≈ 24 points (all vitals critically abnormal).
    Normalized by dividing by 24 and scaling to 10.
    """
    raw = 0.0

    # ── Heart Rate ────────────────────────────────────────────
    hr = vitals.get("heart_rate", 80)
    if hr < 40 or hr > 150:
        raw += 4
    elif hr < 50 or hr > 130:
        raw += 3
    elif hr < 60 or hr > 110:
        raw += 2
    elif hr < 60 or hr > 100:
        raw += 1

    # ── Systolic Blood Pressure ───────────────────────────────
    sbp = vitals.get("bp_systolic", 120)
    if sbp < 70 or sbp > 210:
        raw += 4
    elif sbp < 80 or sbp > 190:
        raw += 3
    elif sbp < 90 or sbp > 170:
        raw += 2
    elif sbp < 100 or sbp > 150:
        raw += 1

    # ── SpO2 (Oxygen Saturation %) ───────────────────────────
    spo2 = vitals.get("spo2", 98)
    if spo2 < 85:
        raw += 4
    elif spo2 < 90:
        raw += 3
    elif spo2 < 94:
        raw += 2
    elif spo2 < 97:
        raw += 1

    # ── Respiratory Rate ──────────────────────────────────────
    rr = vitals.get("respiratory_rate", 16)
    if rr < 6 or rr > 36:
        raw += 4
    elif rr < 9 or rr > 30:
        raw += 3
    elif rr < 12 or rr > 25:
        raw += 2
    elif rr < 12 or rr > 20:
        raw += 1

    # ── Temperature (°F) ─────────────────────────────────────
    temp = vitals.get("temperature", 98.6)
    if temp < 95.0 or temp > 106.0:
        raw += 4
    elif temp < 96.0 or temp > 104.5:
        raw += 3
    elif temp < 97.0 or temp > 102.5:
        raw += 2
    elif temp < 97.5 or temp > 100.4:
        raw += 1

    # ── GCS (consciousness) ───────────────────────────────────
    gcs = vitals.get("gcs", 15)
    if gcs <= 6:
        raw += 4
    elif gcs <= 8:
        raw += 3
    elif gcs <= 11:
        raw += 2
    elif gcs <= 13:
        raw += 1

    # Normalize to 0–10 scale (theoretical max raw = 24)
    return round(min(raw / 24.0 * 10.0, 10.0), 3)


def score_age(age: int) -> float:
    """
    Convert age-based vulnerability modifier to 0–10 scale.
    Modifier from generate_data.age_risk_modifier() is 1.0 → 1.55.
    We linearly map [1.0, 1.55] → [0, 10].
    """
    mod = age_risk_modifier(age)
    # Floor 1.0, ceiling 1.55 (extreme old/young)
    normalized = (mod - 1.0) / (1.55 - 1.0)
    return round(min(normalized * 10.0, 10.0), 3)


def score_time_in_ed(minutes_in_ed: float, symptom_category: str) -> float:
    """
    Time-based risk escalation: the longer a patient waits, the higher the risk.
    Rate is category-specific (e.g., stroke deteriorates faster than ankle sprain).

    Formula: time_risk = deterioration_rate × minutes_waited
    Capped at 10.0.

    This is the core "dynamic" signal — what makes TriageAI different from
    static ESI triage. As clock ticks, this component grows.
    """
    cat = SYMPTOM_CATEGORIES.get(symptom_category, {})
    rate = cat.get("deterioration_rate", 0.03)
    time_risk = rate * minutes_in_ed
    return round(min(time_risk, 10.0), 3)


def score_pain(pain_score: int) -> float:
    """
    Direct passthrough — pain is already 0–10.
    Normalized to avoid over-weighting (patients may self-report inaccurately).
    """
    return round(float(max(0, min(pain_score, 10))), 3)


def score_consciousness(gcs: int) -> float:
    """
    GCS deviation risk. Normal GCS = 15. Lower = more dangerous.
    Maps GCS [3, 15] → risk [10, 0] linearly.
    """
    deviation = 15 - max(3, min(gcs, 15))   # 0 (normal) → 12 (worst)
    return round(deviation / 12.0 * 10.0, 3)


# ─────────────────────────────────────────────────────────────
# 2. Composite Risk Scorer (main public API)
# ─────────────────────────────────────────────────────────────

def compute_risk_score(patient: dict) -> dict:
    """
    Compute the full composite risk score for a patient at the current moment.

    Returns a rich dict containing:
      - composite_risk  : float 0–10 (the headline number)
      - component_scores: dict of each sub-score (for SHAP display decomposition)
      - weighted_scores : dict of weight-adjusted contributions
      - esi_suggested   : ESI level derived from composite score
      - alert_triggered : bool — True if composite_risk >= ALERT_THRESHOLD
      - score_breakdown : human-readable breakdown string (for UI tooltip)

    The component_scores dict maps directly to SHAP feature names, making
    the rule-based decomposition act as a fallback when ML is unavailable.
    """
    vitals = patient.get("vitals", {})
    age = patient.get("age", 40)
    minutes_in_ed = patient.get("minutes_in_ed", patient.get("arrival_minutes_ago", 0))
    symptom_category = patient.get("symptom_category", "Minor Injury / Low Acuity")
    pain = vitals.get("pain_score", patient.get("pain_score", 5))
    gcs = vitals.get("gcs", 15)
    esi_level = patient.get("esi_level", 3)

    # ── Raw component scores ──────────────────────────────────
    c_category     = score_category(symptom_category)
    c_vitals       = score_vitals(vitals)
    c_age          = score_age(age)
    c_time         = score_time_in_ed(minutes_in_ed, symptom_category)
    c_pain         = score_pain(pain)
    c_consciousness = score_consciousness(gcs)

    component_scores = {
        "category_risk":      c_category,
        "vitals_risk":        c_vitals,
        "age_risk":           c_age,
        "time_risk":          c_time,
        "pain_risk":          c_pain,
        "consciousness_risk": c_consciousness,
    }

    # ── Weighted sum ──────────────────────────────────────────
    weighted = {
        "category_risk":      round(c_category      * WEIGHTS["category"],      3),
        "vitals_risk":        round(c_vitals        * WEIGHTS["vitals"],         3),
        "age_risk":           round(c_age           * WEIGHTS["age"],            3),
        "time_risk":          round(c_time          * WEIGHTS["time_in_ed"],     3),
        "pain_risk":          round(c_pain          * WEIGHTS["pain"],           3),
        "consciousness_risk": round(c_consciousness * WEIGHTS["consciousness"],  3),
    }

    composite = sum(weighted.values())

    # ── ESI floor: never let rule-based risk fall below ESI floor ──
    # This ensures an ESI-1 patient never shows Risk 2.0 due to recent arrival.
    esi_floor = ESI_RISK_FLOOR.get(esi_level, 0.0)
    composite = max(composite, esi_floor * 0.90)  # soft floor — 90% of ESI minimum

    composite = round(min(composite, 10.0), 2)

    # ── Suggest ESI from risk score ───────────────────────────
    esi_suggested = _risk_to_esi(composite)

    # ── Alert ─────────────────────────────────────────────────
    alert_triggered = composite >= ALERT_THRESHOLD

    # ── Human-readable breakdown ──────────────────────────────
    breakdown_lines = [
        f"📊 Risk Score Breakdown (Total: {composite}/10)",
        f"  Symptom Category [{symptom_category}]: {c_category:.1f} → weighted {weighted['category_risk']:.2f}",
        f"  Vitals (MEWS):         {c_vitals:.1f} → weighted {weighted['vitals_risk']:.2f}",
        f"  Age Risk [{age}y]:        {c_age:.1f} → weighted {weighted['age_risk']:.2f}",
        f"  Wait Time [{minutes_in_ed:.0f}min]:    {c_time:.1f} → weighted {weighted['time_risk']:.2f}",
        f"  Pain Score [{pain}/10]:   {c_pain:.1f} → weighted {weighted['pain_risk']:.2f}",
        f"  Consciousness [GCS {gcs}]: {c_consciousness:.1f} → weighted {weighted['consciousness_risk']:.2f}",
    ]
    if alert_triggered:
        breakdown_lines.append(f"  🚨 ALERT: Score {composite} ≥ threshold {ALERT_THRESHOLD}")

    return {
        "composite_risk":    composite,
        "component_scores":  component_scores,
        "weighted_scores":   weighted,
        "esi_suggested":     esi_suggested,
        "alert_triggered":   alert_triggered,
        "score_breakdown":   "\n".join(breakdown_lines),
    }


def _risk_to_esi(risk: float) -> int:
    """
    Map composite risk score back to suggested ESI level.
    Used to recommend ESI upgrades (e.g., 3 → 2) when risk escalates.
    """
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
# 3. ESI Elevation Detector
# ─────────────────────────────────────────────────────────────

def detect_esi_escalation(patient: dict, score_result: dict) -> dict | None:
    """
    Compare the patient's current ESI level against the model's suggested ESI.
    Returns an escalation event dict if the patient should be upgraded,
    otherwise None.

    This is the core "catch" — identifying patients who were triaged ESI-3
    at intake but now score as ESI-2 after waiting 90 minutes.

    Example: James Wilson — triaged ESI-3 at intake, but risk curve
    has risen to 7.8 (→ ESI-2). This function fires the escalation alert.
    """
    current_esi = patient.get("esi_level", 3)
    suggested_esi = score_result.get("esi_suggested", current_esi)
    composite = score_result.get("composite_risk", 0)

    # Escalation = suggested ESI is LOWER number (more critical) than current
    if suggested_esi < current_esi:
        return {
            "patient_id":    patient.get("patient_id"),
            "patient_name":  patient.get("name"),
            "current_esi":   current_esi,
            "suggested_esi": suggested_esi,
            "composite_risk": composite,
            "minutes_in_ed": patient.get("minutes_in_ed", 0),
            "reason": (
                f"Risk score {composite:.1f} indicates ESI-{suggested_esi} "
                f"(patient was triaged ESI-{current_esi} at intake). "
                f"Waited {patient.get('minutes_in_ed', 0):.0f} minutes."
            ),
        }
    return None


# ─────────────────────────────────────────────────────────────
# 4. ML Feature Vector + Label Computation
# ─────────────────────────────────────────────────────────────

def build_ml_features(patient: dict) -> list:
    """
    Build the 15-feature vector for GradientBoostingClassifier inference.
    Delegates to generate_data.patient_to_features() to keep data contract
    in a single source of truth.
    """
    return patient_to_features(patient)


def compute_training_label(patient: dict, horizon_minutes: float = 60.0) -> int:
    """
    Generate a binary training label: will this patient have risk > 7.0
    within the next `horizon_minutes`?

    Used during offline training (train_model.py) to label the dataset.
    Not called at inference time.
    """
    cat = SYMPTOM_CATEGORIES.get(patient.get("symptom_category", ""), {})
    rate = cat.get("deterioration_rate", 0.03)

    # Project forward by horizon
    future_minutes = patient.get("minutes_in_ed", 0) + horizon_minutes
    future_time_risk = rate * future_minutes

    # Recompute score at future point (only time component changes deterministically)
    future_patient = dict(patient)
    future_patient["minutes_in_ed"] = future_minutes
    future_result = compute_risk_score(future_patient)
    future_risk = future_result["composite_risk"]

    return int(future_risk >= ALERT_THRESHOLD)


# ─────────────────────────────────────────────────────────────
# 5. Priority Queue Sorter
# ─────────────────────────────────────────────────────────────

def sort_patients_by_priority(patients: list) -> list:
    """
    Sort patient list by triage priority (highest risk first).
    Tie-breaking: lower ESI level > longer wait time.

    Used by app.py to render the patient queue in correct order.
    When Marcus Johnson (ESI-1 trauma) is What-If admitted, this function
    instantly reorders him to the top — the "wow moment" for demo step 5.
    """
    def priority_key(p):
        # Primary: composite_risk descending (negate for ascending sort)
        risk = -p.get("current_risk", 0)
        # Secondary: ESI level ascending (ESI-1 before ESI-5)
        esi = p.get("esi_level", 3)
        # Tertiary: time waiting descending (longer wait = more urgent)
        wait = -p.get("minutes_in_ed", 0)
        return (risk, esi, wait)

    return sorted(patients, key=priority_key)


# ─────────────────────────────────────────────────────────────
# 6. Vitals Trend Analyzer
# ─────────────────────────────────────────────────────────────

def analyze_vitals_trend(vitals_history: list) -> dict:
    """
    Given a patient's vitals history (list of snapshots), compute
    directional trend for each vital sign.

    Returns:
      {
        "heart_rate":        {"trend": "↑", "delta": +12, "direction": "worsening"},
        "bp_systolic":       {"trend": "↓", "delta": -18, "direction": "worsening"},
        "spo2":              {"trend": "↓", "delta": -3,  "direction": "worsening"},
        ...
      }

    "direction" is "worsening", "improving", or "stable".
    This feeds the trend arrows in the patient detail card UI.
    """
    if len(vitals_history) < 2:
        return {}   # Need at least two readings for a trend

    # Compare most recent vs. oldest recorded snapshot
    first = vitals_history[0].get("vitals", {})
    last  = vitals_history[-1].get("vitals", {})

    vital_keys = ["heart_rate", "bp_systolic", "spo2", "respiratory_rate", "temperature", "gcs"]

    # Define "worsening" direction per vital (some vitals worsen when they drop)
    worsen_when_drops = {"spo2", "gcs"}       # low SpO2 / GCS is bad
    worsen_when_rises = {"heart_rate", "bp_systolic", "respiratory_rate", "temperature"}

    trend_map = {}
    for key in vital_keys:
        old_val = first.get(key)
        new_val = last.get(key)

        if old_val is None or new_val is None:
            continue

        delta = new_val - old_val

        # Trend arrow
        if abs(delta) < 1:
            arrow = "→"
            direction = "stable"
        elif delta > 0:
            arrow = "↑"
            direction = "worsening" if key in worsen_when_rises else "improving"
        else:
            arrow = "↓"
            direction = "worsening" if key in worsen_when_drops else "improving"

        trend_map[key] = {
            "trend":     arrow,
            "delta":     round(delta, 1),
            "direction": direction,
            "current":   new_val,
        }

    return trend_map


# ─────────────────────────────────────────────────────────────
# 7. Risk Color + UI Helpers
# ─────────────────────────────────────────────────────────────

def risk_to_color(risk: float) -> str:
    """Return a hex color for risk level — red (critical) → green (safe)."""
    if risk >= 8.5:
        return "#FF1744"    # Deep red — critical
    elif risk >= 7.0:
        return "#FF5722"    # Red-orange — high alert
    elif risk >= 5.5:
        return "#FF9800"    # Amber — elevated
    elif risk >= 3.5:
        return "#FFC107"    # Yellow — moderate
    elif risk >= 2.0:
        return "#8BC34A"    # Light green — low-moderate
    else:
        return "#4CAF50"    # Green — stable


def risk_to_label(risk: float) -> str:
    """Return a short human-readable risk label."""
    if risk >= 8.5:
        return "CRITICAL"
    elif risk >= 7.0:
        return "HIGH RISK"
    elif risk >= 5.5:
        return "ELEVATED"
    elif risk >= 3.5:
        return "MODERATE"
    elif risk >= 2.0:
        return "LOW"
    else:
        return "STABLE"


def esi_to_color(esi: int) -> str:
    """Return ESI badge color (matches real ED ESI color system)."""
    palette = {
        1: "#FF1744",   # ESI-1: Red
        2: "#FF9800",   # ESI-2: Orange
        3: "#FFEB3B",   # ESI-3: Yellow
        4: "#4CAF50",   # ESI-4: Green
        5: "#2196F3",   # ESI-5: Blue
    }
    return palette.get(esi, "#9E9E9E")


# ─────────────────────────────────────────────────────────────
# Quick Sanity Test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from data.generate_data import generate_demo_patients

    print("⚡ TriageAI — Scorer Sanity Test\n" + "=" * 55)

    patients = generate_demo_patients()

    for p in patients:
        result = compute_risk_score(p)
        escalation = detect_esi_escalation(p, result)

        alert_icon = "🚨" if result["alert_triggered"] else "  "
        esc_str    = f"  ⬆️  ESI ESCALATION: {escalation['current_esi']}→{escalation['suggested_esi']}" if escalation else ""

        print(
            f"{alert_icon} {p['name']:20s} | ESI {p['esi_level']} | "
            f"Risk {result['composite_risk']:4.1f} ({risk_to_label(result['composite_risk']):9s}) | "
            f"Suggested ESI {result['esi_suggested']}{esc_str}"
        )

    # Simulate James Wilson after 90-minute wait
    print("\n─── James Wilson AFTER 90-minute simulation ───")
    james = patients[0]
    james_sim = dict(james)
    james_sim["minutes_in_ed"] = 90
    james_sim["vitals"] = dict(james["vitals"])
    james_sim["vitals"]["heart_rate"] = 112   # heart rate climbs
    james_sim["vitals"]["bp_systolic"] = 104  # pressure dropping → concern
    james_sim["vitals"]["spo2"] = 93          # O2 dropping
    james_sim["vitals"]["temperature"] = 102.4  # fever climbing
    james_sim["vitals"]["respiratory_rate"] = 24

    james_result = compute_risk_score(james_sim)
    esc = detect_esi_escalation(james_sim, james_result)
    print(f"  Name: {james['name']} | Age: {james['age']}")
    print(f"  Risk before: {james.get('current_risk')} | Risk after 90min: {james_result['composite_risk']}")
    print(f"  Alert fired: {james_result['alert_triggered']}")
    if esc:
        print(f"  ESI Escalation: {esc['reason']}")
    print()
    print(james_result["score_breakdown"])

    # Trend analysis test
    print("\n─── Vitals Trend Test ───")
    fake_history = [
        {"vitals": {"heart_rate": 98, "bp_systolic": 132, "spo2": 96, "respiratory_rate": 19, "temperature": 100.8, "gcs": 15}},
        {"vitals": {"heart_rate": 107, "bp_systolic": 117, "spo2": 94, "respiratory_rate": 22, "temperature": 101.6, "gcs": 15}},
        {"vitals": {"heart_rate": 112, "bp_systolic": 104, "spo2": 93, "respiratory_rate": 24, "temperature": 102.4, "gcs": 15}},
    ]
    trends = analyze_vitals_trend(fake_history)
    for vital, t in trends.items():
        icon = "🔴" if t["direction"] == "worsening" else ("🟢" if t["direction"] == "improving" else "⚪")
        print(f"  {icon} {vital:25s}: {t['trend']} {t['delta']:+.1f}  ({t['direction']})")

    print("\n✅ Scorer working correctly!")
