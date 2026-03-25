"""
api/main.py — TriageAI FastAPI Bridge
======================================
Bridges the React frontend to the Python ML engine (unchanged).
All patient storage is in-memory (demo-grade, intentional).

Start: uvicorn api.main:app --reload --port 8000
"""

import sys
import copy
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Project root on path ─────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.generate_data import (
    generate_demo_patients,
    generate_patient,
    SYMPTOM_CATEGORIES,
    compute_vitals_score,
)
from engine.scorer import compute_risk_score, sort_patients_by_priority
from engine.rescorer import (
    ModelManager,
    rescore_patient,
    rescore_all_patients,
    simulate_time_jump,
    explain_patient,
)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="TriageAI Bridge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory store ───────────────────────────────────────────
_store: list[dict] = []

# Load model once at startup
ModelManager.load_model()


# ── Schemas ───────────────────────────────────────────────────
class PatientIntake(BaseModel):
    name: str
    age: int
    sex: str = "Unknown"
    symptom_category: str
    chief_complaint: str
    hr: float
    sbp: float
    dbp: float
    rr: float
    spo2: float
    temp: float
    has_comorbidity: bool = False


# ── Helper: convert internal patient → API response ───────────
def _alert_level(risk_prob: float) -> str:
    if risk_prob >= 0.70:
        return "CRITICAL"
    elif risk_prob >= 0.50:
        return "WARNING"
    elif risk_prob >= 0.30:
        return "WATCH"
    return "STABLE"


def _patient_to_api(p: dict) -> dict:
    risk = p.get("current_risk", 0.0)
    risk_prob = round(min(risk / 10.0, 1.0), 3)
    vitals = p.get("vitals", {})

    # Build SHAP / explanation
    shap_data = explain_patient(p)
    if shap_data:
        labels = shap_data.get("feature_labels", shap_data.get("feature_names", []))
        values = shap_data.get("shap_values", [])
        # Sort by absolute impact, take top 8
        pairs = sorted(zip(labels, values), key=lambda x: abs(x[1]), reverse=True)[:8]
        shap_labels = [pr[0] for pr in pairs]
        shap_values = [round(pr[1], 4) for pr in pairs]
        # Top 4 factors → plain-English
        explanation = []
        for lbl, val in pairs[:4]:
            direction = "increased" if val > 0 else "decreased"
            explanation.append(f"{lbl} {direction} risk by {abs(val):.3f}")
    else:
        shap_labels, shap_values = [], []
        explanation = [
            f"Alert: {_alert_level(risk_prob)}",
            f"Risk Score: {risk:.1f}/10",
            f"Category: {p.get('symptom_category', 'Unknown')}",
            f"Wait Time: {p.get('minutes_in_ed', 0):.0f} min",
        ]

    return {
        "patient_id":       p.get("patient_id"),
        "name":             p.get("name"),
        "age":              p.get("age"),
        "sex":              p.get("sex", "Unknown"),
        "symptom_category": p.get("symptom_category"),
        "chief_complaint":  p.get("chief_complaint"),
        "base_acuity":      p.get("esi_level"),
        "dynamic_acuity":   p.get("esi_level"),
        "original_acuity":  p.get("esi_level"),
        "acuity_changed":   p.get("esi_upgraded", False),
        "risk_probability": risk_prob,
        "alert_level":      _alert_level(risk_prob),
        "wait_time_min":    round(p.get("minutes_in_ed", 0)),
        "explanation":      explanation,
        "shap_labels":      shap_labels,
        "shap_values":      shap_values,
        "hr":               vitals.get("heart_rate", 0),
        "sbp":              vitals.get("bp_systolic", 0),
        "dbp":              vitals.get("bp_diastolic", 0),
        "spo2":             vitals.get("spo2", 0),
        "rr":               vitals.get("respiratory_rate", 0),
        "temp":             vitals.get("temperature", 0),
        "gcs":              vitals.get("gcs", 15),
        "pain_score":       vitals.get("pain_score", 0),
        "risk_history":     p.get("risk_history", []),
        "vitals_trend":     p.get("vitals_trend", {}),
        "_demo_note":       p.get("_demo_note", ""),
        "arrival_time":     p.get("arrival_time", datetime.now().isoformat()),
    }


def _initial_score(p: dict) -> dict:
    """Run initial rule-based score pass on a fresh patient."""
    result = compute_risk_score(p)
    p["current_risk"]     = result["composite_risk"]
    p["component_scores"] = result["component_scores"]
    p["weighted_scores"]  = result["weighted_scores"]
    p["score_breakdown"]  = result["score_breakdown"]
    p["alerts"]           = []
    p["vitals_trend"]     = {}
    p["esi_upgraded"]     = False
    return p


# ── Endpoints ─────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": ModelManager.is_available(),
        "patient_count": len(_store),
    }


@app.post("/api/patients")
def add_patient(intake: PatientIntake):
    """Add a single patient from the intake form."""
    vitals_override = {
        "heart_rate":       intake.hr,
        "bp_systolic":      intake.sbp,
        "bp_diastolic":     intake.dbp,
        "respiratory_rate": intake.rr,
        "spo2":             intake.spo2,
        "temperature":      intake.temp,
        "gcs":              15,
        "pain_score":       5,
    }
    p = generate_patient(
        name=intake.name,
        age=intake.age,
        sex=intake.sex,
        symptom_category=intake.symptom_category,
        chief_complaint=intake.chief_complaint,
        arrival_minutes_ago=0,
        vitals_override=vitals_override,
    )
    p["has_comorbidity"] = intake.has_comorbidity
    p = _initial_score(p)
    _store.append(p)
    return _patient_to_api(p)


@app.get("/api/patients/rescore")
def rescore(sim_offset_minutes: float = Query(0.0)):
    """Re-score all patients and return sorted queue."""
    global _store
    if not _store:
        return []

    # Advance each patient by 1 minute per call as baseline
    # (the frontend calls this every 30s, sim_offset drives fast-forward)
    elapsed = max(sim_offset_minutes, 0.0)

    # Apply elapsed time advancement if sim_offset > 0
    if elapsed > 0:
        patients_copy = copy.deepcopy(_store)
        updated, _ = rescore_all_patients(patients_copy, elapsed_minutes=elapsed)
        _store = updated
    else:
        updated, _ = rescore_all_patients(_store, elapsed_minutes=1.0)
        _store = updated

    return [_patient_to_api(p) for p in _store]


@app.post("/api/patients/load-demo")
def load_demo(sim_offset_minutes: float = Query(0.0)):
    """Load 6 scripted demo patients and return initial scores."""
    global _store
    patients = generate_demo_patients()
    for p in patients:
        p = _initial_score(p)
    _store = sort_patients_by_priority(patients)

    # Apply sim_offset if requested
    if sim_offset_minutes > 0:
        _store, _ = rescore_all_patients(_store, elapsed_minutes=sim_offset_minutes)

    return [_patient_to_api(p) for p in _store]


@app.delete("/api/patients")
def clear_patients():
    global _store
    _store.clear()
    return {"cleared": True}


@app.get("/api/patients/whatif")
def whatif(
    future_minutes: float = Query(60.0),
    sim_offset_minutes: float = Query(0.0),
):
    """Simulate future patient states without mutating stored data."""
    if not _store:
        return []
    patients_copy = copy.deepcopy(_store)
    if sim_offset_minutes > 0:
        patients_copy, _ = rescore_all_patients(
            patients_copy, elapsed_minutes=sim_offset_minutes
        )
    updated, _, _ = simulate_time_jump(
        patients_copy, total_minutes=future_minutes, step_minutes=5.0
    )
    return [_patient_to_api(p) for p in updated]


@app.get("/api/patients/simulate")
def simulate_jump(total_minutes: float = Query(90.0)):
    """Fast-forward simulation (⏩ Simulate 90 min button)."""
    global _store
    if not _store:
        return {"patients": [], "alerts": [], "snapshots": []}
    updated, alerts, snapshots = simulate_time_jump(
        _store, total_minutes=total_minutes, step_minutes=5.0
    )
    _store = updated
    return {
        "patients":  [_patient_to_api(p) for p in _store],
        "alert_count": len(alerts),
        "snapshots": snapshots,
    }


@app.get("/api/patients/timelapse")
def timelapse(step_minutes: float = Query(10.0), total_minutes: float = Query(120.0)):
    """Return risk snapshots for time-lapse chart (non-mutating)."""
    if not _store:
        return []
    steps = []
    patients_copy = copy.deepcopy(_store)
    t = 0.0
    while t <= total_minutes:
        snapshot = {
            "t": t,
            "patients": [
                {
                    "patient_id": p.get("patient_id"),
                    "name":       p.get("name"),
                    "risk":       round(min(p.get("current_risk", 0) / 10.0, 1.0), 3),
                    "alert":      _alert_level(min(p.get("current_risk", 0) / 10.0, 1.0)),
                }
                for p in patients_copy
            ],
        }
        steps.append(snapshot)
        if t < total_minutes:
            patients_copy, _ = rescore_all_patients(
                patients_copy, elapsed_minutes=step_minutes
            )
        t += step_minutes
    return steps


@app.get("/api/categories")
def get_categories():
    """Return available symptom categories for patient intake form."""
    return list(SYMPTOM_CATEGORIES.keys())
