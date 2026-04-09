"""
api/main.py — TriageAI FastAPI Bridge
======================================
Bridges the React frontend to the Python ML engine.
All patient storage is in-memory (demo-grade, intentional).

Start: uvicorn api.main:app --reload --port 8000

CRITICAL-2 FIX: Added route aliases and missing endpoints:
  POST /admit          (alias for POST /api/patients)
  GET  /queue          (alias for GET /api/patients/rescore)
  POST /rescore        (alias for GET /api/patients/rescore with POST semantics)
  GET  /alerts         (NEW: returns unacknowledged alerts sorted by risk)
  PATCH /alerts/{id}/acknowledge (NEW: for useAlerts.js markRead)

QW-2 FIX: Added Pydantic Field validators to PatientIntake.
"""

import sys
import copy
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
    get_active_alerts,
    acknowledge_alert,
)

# ── App ───────────────────────────────────────────────────────
app = FastAPI(title="TriageAI Bridge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://triage-ai-liart.vercel.app",        # replace with your actual Vercel URL
        "https://triage-ai-liart.vercel.app",       # add any alternate Vercel URLs
    ],
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
    """
    QW-2 FIX: All vital sign fields now have Pydantic Field validators
    with physiological min/max constraints to reject invalid intake data.
    """
    name: str
    age: int = Field(ge=1, le=120, description="Patient age in years")
    sex: str = "Unknown"
    symptom_category: str
    chief_complaint: str
    # QW-2: Field validators with physiological bounds
    hr:   float = Field(ge=0, le=300,   description="Heart rate bpm")
    sbp:  float = Field(ge=0, le=300,   description="Systolic BP mmHg")
    dbp:  float = Field(ge=0, le=200,   description="Diastolic BP mmHg")
    rr:   float = Field(ge=0, le=80,    description="Respiratory rate /min")
    spo2: float = Field(ge=0, le=100,   description="Oxygen saturation %")
    temp: float = Field(ge=80.0, le=115.0, description="Temperature °F")
    has_comorbidity: bool = False


# ── Helper: alert level from risk score 0-10 ─────────────────
def _alert_level(risk: float) -> str:
    """Map 0-10 risk score to alert level string."""
    if risk >= 7.5:
        return "CRITICAL"
    elif risk >= 5.5:
        return "WARNING"
    elif risk >= 3.5:
        return "WATCH"
    return "STABLE"


# ── Helper: convert internal patient → API response ───────────
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
            f"Alert: {_alert_level(risk)}",
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
        "alert_level":      _alert_level(risk),
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
        "has_comorbidity":  p.get("has_comorbidity", False),
        "esi_level":        p.get("esi_level", 3),
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


# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": ModelManager.is_available(),
        "patient_count": len(_store),
    }


# ── Patient Intake ─────────────────────────────────────────────

@app.post("/api/patients")
def add_patient(intake: PatientIntake):
    """Add a single patient from the intake form."""
    return _admit_patient(intake)


@app.post("/admit")
def admit(intake: PatientIntake):
    """CRITICAL-2 FIX: Route alias for POST /api/patients. Frontend uses /admit."""
    return _admit_patient(intake)


def _admit_patient(intake: PatientIntake) -> dict:
    """Shared logic for patient admission."""
    global _store
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


# ── Queue / Rescore ──────────────────────────────────────────

@app.get("/api/patients/rescore")
def rescore(sim_offset_minutes: float = Query(0.0)):
    """Re-score all patients and return sorted queue."""
    return _rescore_queue(sim_offset_minutes)


@app.get("/queue")
def queue_get(sim_offset_minutes: float = Query(0.0)):
    """CRITICAL-2 FIX: Route alias for GET /api/patients/rescore. Frontend polls /queue."""
    return _rescore_queue(sim_offset_minutes)

@app.get("/api/queue")
def queue_get_api(sim_offset_minutes: float = Query(0.0), no_rescore: bool = Query(False)):
    """Frontend exact match for GET /api/queue"""
    if no_rescore:
        return [_patient_to_api(p) for p in _store]
    return _rescore_queue(sim_offset_minutes)


@app.post("/rescore")
def rescore_post(sim_offset_minutes: float = Query(0.0)):
    """CRITICAL-2 FIX: POST alias for rescoring (for frontend useQueue hook)."""
    return _rescore_queue(sim_offset_minutes)


def _rescore_queue(sim_offset_minutes: float) -> list:
    """Shared rescore logic."""
    global _store
    if not _store:
        return []

    elapsed = max(sim_offset_minutes, 0.0)

    if elapsed > 0:
        patients_copy = copy.deepcopy(_store)
        updated, _ = rescore_all_patients(patients_copy, elapsed_minutes=elapsed)
        _store = updated
    else:
        updated, _ = rescore_all_patients(_store, elapsed_minutes=1.0)
        _store = updated

    return [_patient_to_api(p) for p in _store]


# ── Demo Load ─────────────────────────────────────────────────

@app.post("/api/patients/load-demo")
def load_demo(sim_offset_minutes: float = Query(0.0)):
    """Load 10 scripted demo patients and return initial scores."""
    global _store
    patients = generate_demo_patients()
    for p in patients:
        p = _initial_score(p)
    _store = sort_patients_by_priority(patients)

    if sim_offset_minutes > 0:
        _store, _ = rescore_all_patients(_store, elapsed_minutes=sim_offset_minutes)

    return [_patient_to_api(p) for p in _store]


@app.post("/load-demo")
def load_demo_alias(sim_offset_minutes: float = Query(0.0)):
    """CRITICAL-2 FIX: Route alias for POST /api/patients/load-demo."""
    return load_demo(sim_offset_minutes)


# ── Clear ─────────────────────────────────────────────────────

@app.delete("/api/patients")
def clear_patients():
    global _store
    _store.clear()
    return {"cleared": True}


# ── Alerts ───────────────────────────────────────────────────

@app.get("/api/alerts")
def get_alerts():
    """
    CRITICAL-2 / QW-6 FIX: New endpoint — returns all unacknowledged alerts
    from _store sorted by risk_score descending.
    Used by frontend useAlerts.js hook (polls every 10 seconds).
    """
    if not _store:
        return []
    active = get_active_alerts(_store)
    # Sort by risk score descending
    return sorted(active, key=lambda a: -a.get("risk_score", 0))


@app.get("/alerts")
def get_alerts_alias():
    """CRITICAL-2 FIX: Route alias for GET /api/alerts."""
    return get_alerts()


@app.patch("/api/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str):
    """
    Mark an alert as acknowledged. Called by useAlerts.js markRead function.
    """
    global _store
    _store = acknowledge_alert(_store, alert_id)
    return {"acknowledged": True, "alert_id": alert_id}


@app.patch("/alerts/{alert_id}/acknowledge")
def ack_alert_alias(alert_id: str):
    """Route alias for PATCH /api/alerts/{id}/acknowledge."""
    return ack_alert(alert_id)


# ── What-If ───────────────────────────────────────────────────

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


@app.get("/whatif")
def whatif_alias(future_minutes: float = Query(60.0)):
    """CRITICAL-2 FIX: Route alias for GET /api/patients/whatif."""
    return whatif(future_minutes=future_minutes)


# ── Simulate ─────────────────────────────────────────────────

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


@app.get("/simulate")
def simulate_alias(total_minutes: float = Query(90.0)):
    """CRITICAL-2 FIX: Route alias for GET /api/patients/simulate."""
    return simulate_jump(total_minutes)

@app.post("/api/simulate")
def simulate_post_api(minutes: float = Query(90.0)):
    """Frontend exact match for POST /api/simulate?minutes=90"""
    return simulate_jump(total_minutes=minutes)


# ── Time Lapse ────────────────────────────────────────────────

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
                    "risk":       round(p.get("current_risk", 0), 2),
                    "alert":      _alert_level(p.get("current_risk", 0)),
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


# ── Categories ────────────────────────────────────────────────

@app.get("/api/categories")
def get_categories():
    """Return available symptom categories for patient intake form."""
    return list(SYMPTOM_CATEGORIES.keys())

# ──Home Page ─────────────────────────────────────────────────
@app.get("/")
def home():
    return {
        "message": "✅ TriageAI Backend is running!",
        "info": "This is the TriageAI API server. To use TriageAI, visit the frontend:",
        "frontend_url": "https://triage-ai-liart.vercel.app",
    }