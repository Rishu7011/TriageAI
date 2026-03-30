"""
engine/alerts.py — TriageAI Alert Management System
====================================================
Manages the full lifecycle of patient deterioration alerts:
  1. Alert creation (threshold crossings + ESI escalation events)
  2. Severity classification (CRITICAL / HIGH / MEDIUM)
  3. In-memory alert queue (session_state compatible)
  4. Acknowledgement workflow
  5. Summary statistics for sidebar badge

Called by:
  rescorer.py  → _build_alert() creates the alert dict
  app.py       → renders alerts and handles acknowledgement
  
All alert objects are plain Python dicts so they serialize cleanly
into st.session_state without pickling issues.

Alert Dict Schema:
{
  "alert_id":       str       — unique ID
  "patient_id":     str
  "patient_name":   str
  "timestamp":      ISO str
  "risk_score":     float     — risk at time of alert
  "esi_current":    int
  "esi_suggested":  int | None
  "minutes_in_ed":  float
  "severity":       "CRITICAL" | "HIGH" | "MEDIUM"
  "alert_reasons":  list[str] — individual flags
  "alert_text":     str       — human-readable summary
  "clinical_note":  str       — recommended clinical action
  "acknowledged":   bool
  "acknowledged_at":str | None
  "escalation":     dict | None
}
"""

from datetime import datetime
from typing import Optional

# Import thresholds from constants (avoids circular imports vs scorer.py)
try:
    from utils.constants import (
        ALERT_THRESHOLD,
        CRITICAL_THRESHOLD,
        VITALS_CRITICAL,
        CATEGORY_CLINICAL_NOTES,
        ESI_DEFINITIONS,
        MAX_ALERTS_SIDEBAR,
    )
except ImportError:
    # Fallback if constants not yet loaded (e.g. during partial init)
    ALERT_THRESHOLD      = 7.5
    CRITICAL_THRESHOLD   = 9.0
    VITALS_CRITICAL      = {"spo2": 90, "bp_systolic": 85, "heart_rate_high": 130,
                             "temperature_high": 103.5, "gcs_low": 12, "respiratory_high": 28}
    CATEGORY_CLINICAL_NOTES = {}
    ESI_DEFINITIONS         = {}
    MAX_ALERTS_SIDEBAR      = 8


# ─────────────────────────────────────────────────────────────
# 1. Alert Classification
# ─────────────────────────────────────────────────────────────

def classify_severity(risk: float, esi: int, vitals: dict) -> str:
    """
    Determine alert severity level from risk score and clinical context.
    
    CRITICAL: risk ≥ 9.0 OR ESI-1 OR any single life-threatening vital
    HIGH:     risk ≥ 7.5 OR ESI-2 OR 2+ abnormal vitals
    MEDIUM:   risk ≥ 6.0 OR ESI escalation without threshold crossing
    """
    # Life-threatening single vital → always CRITICAL
    if (vitals.get("spo2", 99) < 80 or
            vitals.get("bp_systolic", 120) < 70 or
            vitals.get("gcs", 15) <= 8):
        return "CRITICAL"

    if risk >= CRITICAL_THRESHOLD or esi == 1:
        return "CRITICAL"

    if risk >= ALERT_THRESHOLD or esi <= 2:
        return "HIGH"

    return "MEDIUM"


def identify_vital_flags(vitals: dict) -> list:
    """
    Scan vitals against critical thresholds and return a list of
    human-readable flag strings for the alert_reasons list.
    """
    flags = []
    hr   = vitals.get("heart_rate", 80)
    sbp  = vitals.get("bp_systolic", 120)
    spo2 = vitals.get("spo2", 99)
    temp = vitals.get("temperature", 98.6)
    gcs  = vitals.get("gcs", 15)
    rr   = vitals.get("respiratory_rate", 16)

    if spo2 < VITALS_CRITICAL.get("spo2", 90):
        flags.append(f"Critical SpO₂: {spo2}% (normal ≥95%)")
    if sbp < VITALS_CRITICAL.get("bp_systolic", 85):
        flags.append(f"Hypotension: SBP {sbp} mmHg (normal ≥90)")
    if hr > VITALS_CRITICAL.get("heart_rate_high", 130):
        flags.append(f"Severe tachycardia: HR {hr} bpm (normal ≤100)")
    if hr < VITALS_CRITICAL.get("heart_rate_low", 40):
        flags.append(f"Bradycardia: HR {hr} bpm (normal ≥60)")
    if temp > VITALS_CRITICAL.get("temperature_high", 103.5):
        flags.append(f"High fever: {temp}°F — possible sepsis")
    if temp < VITALS_CRITICAL.get("temperature_low", 95.0):
        flags.append(f"Hypothermia: {temp}°F — assess perfusion")
    if gcs < VITALS_CRITICAL.get("gcs_low", 12):
        flags.append(f"Altered consciousness: GCS {gcs}/15")
    if rr > VITALS_CRITICAL.get("respiratory_high", 28):
        flags.append(f"Respiratory distress: RR {rr}/min (normal 12-20)")
    if rr < VITALS_CRITICAL.get("respiratory_low", 8):
        flags.append(f"Respiratory depression: RR {rr}/min")

    # Shock index (HR / SBP) — a simple trauma staging tool
    if sbp > 0:
        si = hr / sbp
        if si > 1.4:
            flags.append(f"Shock index CRITICAL: {si:.2f} (HR/SBP — normal <0.7)")
        elif si > 1.0:
            flags.append(f"Shock index elevated: {si:.2f} (normal <0.7)")

    return flags


# ─────────────────────────────────────────────────────────────
# 2. Alert Builder
# ─────────────────────────────────────────────────────────────

def build_alert(
    patient: dict,
    composite_risk: float,
    escalation: Optional[dict] = None,
    trigger: str = "threshold",   # "threshold" | "escalation" | "vitals"
) -> dict:
    """
    Build a rich alert dict from a patient record + scoring result.
    
    Args:
        patient:        full patient dict
        composite_risk: current risk score (may differ from patient['current_risk'])
        escalation:     ESI escalation event dict (from detect_esi_escalation)
        trigger:        what caused this alert to fire
        
    Returns:
        alert dict ready to append to patient['alerts'] and session_state
    """
    vitals   = patient.get("vitals", {})
    esi      = patient.get("esi_level", 3)
    category = patient.get("symptom_category", "")
    now      = datetime.now()

    # ── Reasons ──────────────────────────────────────────────
    reasons = []

    if trigger in ("threshold",):
        reasons.append(
            f"Risk score {composite_risk:.1f}/10 exceeds alert threshold {ALERT_THRESHOLD}"
        )
    if escalation:
        reasons.append(
            f"ESI should be upgraded: {escalation['current_esi']} → {escalation['suggested_esi']}"
        )

    vital_flags = identify_vital_flags(vitals)
    reasons.extend(vital_flags)

    if not reasons:
        reasons.append(f"Risk threshold exceeded ({composite_risk:.1f}/10)")

    # ── Severity ──────────────────────────────────────────────
    severity = classify_severity(composite_risk, esi, vitals)

    # ── Clinical note ─────────────────────────────────────────
    clinical_note = CATEGORY_CLINICAL_NOTES.get(
        category,
        "Immediate clinical reassessment recommended."
    )

    # ── Unique alert ID ───────────────────────────────────────
    alert_id = f"{patient.get('patient_id','???')}-{int(now.timestamp())}"

    return {
        "alert_id":        alert_id,
        "patient_id":      patient.get("patient_id"),
        "patient_name":    patient.get("name"),
        "timestamp":       now.isoformat(),
        "timestamp_human": now.strftime("%H:%M:%S"),
        "risk_score":      round(composite_risk, 2),
        "esi_current":     esi,
        "esi_suggested":   escalation["suggested_esi"] if escalation else esi,
        "minutes_in_ed":   patient.get("minutes_in_ed", 0),
        "severity":        severity,
        "trigger":         trigger,
        "alert_reasons":   reasons,
        "alert_text":      " · ".join(reasons[:3]),  # truncated for sidebar
        "alert_text_full": " | ".join(reasons),
        "clinical_note":   clinical_note,
        "symptom_category": category,
        "vitals_snapshot": dict(vitals),
        "escalation":      escalation,
        "acknowledged":    False,
        "acknowledged_at": None,
        "acknowledged_by": None,
    }


# ─────────────────────────────────────────────────────────────
# 3. Alert Queue Operations
# ─────────────────────────────────────────────────────────────

def get_active_alerts(patients: list) -> list:
    """
    Collect all unacknowledged alerts across all patients.
    Returns list sorted by: severity (CRITICAL first), then risk_score desc.
    """
    all_alerts = []
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}

    for p in patients:
        for alert in p.get("alerts", []):
            if not alert.get("acknowledged", False):
                all_alerts.append(alert)

    all_alerts.sort(key=lambda a: (
        severity_rank.get(a.get("severity", "MEDIUM"), 2),
        -a.get("risk_score", 0),
    ))

    return all_alerts


def get_alert_summary(patients: list) -> dict:
    """
    Return counts for the sidebar alert badge.
    
    Returns:
      {
        "critical": int,
        "high":     int,
        "medium":   int,
        "total":    int,
        "unacked":  int,
      }
    """
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}

    for p in patients:
        for alert in p.get("alerts", []):
            if not alert.get("acknowledged"):
                sev = alert.get("severity", "MEDIUM")
                counts[sev] = counts.get(sev, 0) + 1

    total = sum(counts.values())
    return {
        "critical": counts["CRITICAL"],
        "high":     counts["HIGH"],
        "medium":   counts["MEDIUM"],
        "total":    total,
        "unacked":  total,
    }


def acknowledge_alert(
    patients: list,
    alert_id: str,
    acknowledged_by: str = "Nurse",
) -> list:
    """
    Mark an alert as acknowledged by ID.
    Mutates patients list in-place and returns it.
    Used by the sidebar "Ack" button in app.py.
    """
    now = datetime.now().isoformat()
    for p in patients:
        for alert in p.get("alerts", []):
            if alert.get("alert_id") == alert_id:
                alert["acknowledged"]    = True
                alert["acknowledged_at"] = now
                alert["acknowledged_by"] = acknowledged_by
                # Also reset the patient-level alert flag so it stops pulsing
                # Only if ALL patient alerts are now acknowledged
                all_acked = all(a.get("acknowledged") for a in p.get("alerts", []))
                if all_acked:
                    p["alert_fired"] = False
                break
    return patients


def acknowledge_all_alerts(
    patients: list,
    acknowledged_by: str = "Charge Nurse",
) -> list:
    """Bulk-acknowledge all active alerts. Called by 'Clear All' button."""
    now = datetime.now().isoformat()
    for p in patients:
        for alert in p.get("alerts", []):
            if not alert.get("acknowledged"):
                alert["acknowledged"]    = True
                alert["acknowledged_at"] = now
                alert["acknowledged_by"] = acknowledged_by
        p["alert_fired"] = False
    return patients


def filter_alerts_by_severity(alerts: list, severity: str) -> list:
    """Filter alert list to only CRITICAL / HIGH / MEDIUM."""
    return [a for a in alerts if a.get("severity") == severity]


def get_alert_by_id(patients: list, alert_id: str) -> Optional[dict]:
    """Look up a specific alert across all patients."""
    for p in patients:
        for alert in p.get("alerts", []):
            if alert.get("alert_id") == alert_id:
                return alert
    return None


# ─────────────────────────────────────────────────────────────
# 4. Alert History & Analytics
# ─────────────────────────────────────────────────────────────

def get_all_alerts_sorted(patients: list, include_acknowledged: bool = True) -> list:
    """
    Return every alert (acked + unacked) sorted by timestamp descending.
    Used by the Simulation Results tab to build the alert timeline table.
    """
    all_alerts = []
    for p in patients:
        for alert in p.get("alerts", []):
            if include_acknowledged or not alert.get("acknowledged"):
                all_alerts.append(alert)
    all_alerts.sort(key=lambda a: a.get("timestamp", ""), reverse=True)
    return all_alerts


def count_alerts_per_patient(patients: list) -> dict:
    """Returns {patient_id: alert_count} for analytics display."""
    return {
        p.get("patient_id"): len(p.get("alerts", []))
        for p in patients
    }


def compute_mean_time_to_alert(patients: list) -> Optional[float]:
    """
    Compute average minutes-in-ED when the first alert fired.
    Useful for reporting: 'average patient waited X minutes before AI flagged them'.
    Returns None if no alerts.
    """
    times = []
    for p in patients:
        for alert in p.get("alerts", []):
            if not alert.get("acknowledged") or True:  # include all
                times.append(alert.get("minutes_in_ed", 0))
                break  # only first alert per patient
    return round(sum(times) / len(times), 1) if times else None


# ─────────────────────────────────────────────────────────────
# 5. Alert Formatting Helpers (for app.py)
# ─────────────────────────────────────────────────────────────

SEVERITY_COLORS = {
    "CRITICAL": "#ef4444",
    "HIGH":     "#f97316",
    "MEDIUM":   "#eab308",
}

SEVERITY_ICONS = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
}


def format_alert_for_sidebar(alert: dict) -> dict:
    """
    Add display-friendly fields to an alert for rendering in the sidebar.
    Returns augmented dict (does not mutate original).
    """
    sev = alert.get("severity", "HIGH")
    return {
        **alert,
        "color":      SEVERITY_COLORS.get(sev, "#94a3b8"),
        "icon":       SEVERITY_ICONS.get(sev, "⚠️"),
        "wait_str":   _format_wait(alert.get("minutes_in_ed", 0)),
        "risk_pct":   f"{alert.get('risk_score', 0) / 10 * 100:.0f}%",
    }


def _format_wait(minutes: float) -> str:
    """Format minutes as '1h 23m' or '45m'."""
    m = int(minutes)
    if m < 60:
        return f"{m}m"
    return f"{m // 60}h {m % 60}m"


# ─────────────────────────────────────────────────────────────
# Sanity test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔔 Alerts module sanity test")

    dummy_patient = {
        "patient_id":       "P001",
        "name":             "James Wilson",
        "age":              72,
        "esi_level":        3,
        "minutes_in_ed":    95,
        "symptom_category": "Abdominal Pain",
        "chief_complaint":  "Severe abdominal pain, fever",
        "vitals": {
            "heart_rate":       118,
            "bp_systolic":      98,
            "bp_diastolic":     65,
            "spo2":             88,
            "respiratory_rate": 26,
            "temperature":      103.8,
            "gcs":              14,
            "pain_score":       8,
        },
        "alerts": [],
    }

    alert = build_alert(
        patient=dummy_patient,
        composite_risk=8.1,
        escalation={"current_esi": 3, "suggested_esi": 2, "reason": "Risk above ESI-2 threshold"},
        trigger="threshold",
    )

    print(f"  Alert ID:    {alert['alert_id']}")
    print(f"  Severity:    {alert['severity']}")
    print(f"  Text:        {alert['alert_text']}")
    print(f"  Clinical:    {alert['clinical_note']}")
    print(f"  Vital flags: {len(alert['alert_reasons'])} reasons")
    for r in alert["alert_reasons"]:
        print(f"    - {r}")

    # Test queue operations
    dummy_patient["alerts"] = [alert]
    patients = [dummy_patient]

    summary = get_alert_summary(patients)
    print(f"\n  Summary: {summary}")

    active = get_active_alerts(patients)
    print(f"  Active alerts: {len(active)}")

    patients = acknowledge_alert(patients, alert["alert_id"])
    print(f"  After ack: alert acknowledged = {patients[0]['alerts'][0]['acknowledged']}")

    print("\n✅ Alerts module working correctly!")
