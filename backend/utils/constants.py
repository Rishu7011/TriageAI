"""
utils/constants.py — TriageAI Central Configuration
=====================================================
Single source of truth for all thresholds, display config, color maps,
and clinical reference values used across the TriageAI system.

Centralizing here means judges and clinicians can review / tune
all model behaviour from one file without touching engine logic.
"""

# ─────────────────────────────────────────────────────────────
# Risk Scoring Weights
# ─────────────────────────────────────────────────────────────
# These are the 6 components of the composite risk score (0–10).
# Must sum to ≤ 1.0 (the ESI floor adds a hard minimum on top).

SCORING_WEIGHTS = {
    "vitals":        0.35,   # most important — direct physiological state
    "category":      0.30,   # chief complaint category severity
    "time":          0.15,   # time-elapsed penalty (deterioration builds over wait)
    "age":           0.10,   # age modifier (elderly & paediatric at higher risk)
    "pain":          0.05,   # pain score contribution
    "consciousness": 0.05,   # GCS contribution
}

# ESI floor multipliers (minimum risk imposed by ESI grade alone)
ESI_FLOOR_MAP = {
    1: 9.0,    # Immediate — always critical
    2: 6.5,    # Emergent — high floor
    3: 3.8,    # Urgent — moderate floor (James Wilson starts here)
    4: 1.5,    # Less-urgent — low floor
    5: 0.5,    # Non-urgent — near-zero floor
}

# ─────────────────────────────────────────────────────────────
# Alert / Escalation Thresholds
# ─────────────────────────────────────────────────────────────

ALERT_THRESHOLD     = 7.5   # risk score that triggers a real-time alert
CRITICAL_THRESHOLD  = 9.0   # risk score for CRITICAL severity tag
ESI_UPGRADE_MARGIN  = 1.5   # risk must exceed ESI floor by this to suggest upgrade
TREND_WINDOW_STEPS  = 3     # how many history entries to use for vitals trend arrows

# ─────────────────────────────────────────────────────────────
# Vital Signs — Normal Ranges & Alert Thresholds
# ─────────────────────────────────────────────────────────────
# Used by both the scorer and the alert builder to flag individual vitals.

VITALS_NORMAL = {
    "heart_rate":        (60,   100),   # bpm
    "bp_systolic":       (90,   140),   # mmHg
    "bp_diastolic":      (60,   90),    # mmHg
    "spo2":              (95,   100),   # %
    "respiratory_rate":  (12,   20),    # breaths/min
    "temperature":       (97.0, 99.5),  # °F
    "gcs":               (15,   15),    # Glasgow Coma Scale
    "pain_score":        (0,    3),     # NRS pain
}

# Hard-limit thresholds for critical single-vital alerts
VITALS_CRITICAL = {
    "spo2":              90,    # SpO2 < 90% → critical hypoxia
    "bp_systolic":       85,    # SBP < 85 → hypotension / shock
    "heart_rate_high":   130,   # HR > 130 → severe tachycardia
    "heart_rate_low":    40,    # HR < 40 → bradycardia
    "temperature_high":  103.5, # °F → high fever (sepsis signal)
    "temperature_low":   95.0,  # °F → hypothermia (trauma / shock)
    "gcs_low":           12,    # GCS < 12 → altered consciousness
    "respiratory_high":  28,    # RR > 28 → respiratory distress
    "respiratory_low":   8,     # RR < 8 → respiratory depression
}

# Shock Index = HR / SBP (> 1.0 = concern, > 1.4 = critical)
SHOCK_INDEX_WARN     = 1.0
SHOCK_INDEX_CRITICAL = 1.4

# ─────────────────────────────────────────────────────────────
# ESI Level Definitions
# ─────────────────────────────────────────────────────────────

ESI_DEFINITIONS = {
    1: {
        "label":       "Immediate",
        "description": "Requires immediate life-saving intervention",
        "max_wait":    0,          # minutes — should be seen immediately
        "color":       "#ef4444",  # red
        "bg_color":    "#450a0a",
    },
    2: {
        "label":       "Emergent",
        "description": "High risk situation; should not wait",
        "max_wait":    15,
        "color":       "#f97316",  # orange
        "bg_color":    "#431407",
    },
    3: {
        "label":       "Urgent",
        "description": "Requires multiple resources; stable for now",
        "max_wait":    30,
        "color":       "#eab308",  # yellow
        "bg_color":    "#422006",
    },
    4: {
        "label":       "Less Urgent",
        "description": "One resource needed; stable",
        "max_wait":    60,
        "color":       "#22c55e",  # green
        "bg_color":    "#052e16",
    },
    5: {
        "label":       "Non-Urgent",
        "description": "No resources needed; stable",
        "max_wait":    120,
        "color":       "#3b82f6",  # blue
        "bg_color":    "#172554",
    },
}

# ─────────────────────────────────────────────────────────────
# Risk Score → Display Mapping
# ─────────────────────────────────────────────────────────────

RISK_LEVELS = [
    # (min_score, label, hex_color)
    (9.0,  "CRITICAL",    "#ef4444"),  # red
    (7.5,  "HIGH RISK",   "#f97316"),  # orange
    (5.5,  "ELEVATED",    "#eab308"),  # yellow
    (3.5,  "MODERATE",    "#22c55e"),  # green
    (0.0,  "LOW",         "#3b82f6"),  # blue
]

# ─────────────────────────────────────────────────────────────
# Symptom Category Config
# ─────────────────────────────────────────────────────────────
# Mirrors the keys in generate_data.SYMPTOM_CATEGORIES.
# Used by alerts.py to format human-readable alert messages.

CATEGORY_CLINICAL_NOTES = {
    "Chest Pain / Cardiac":   "ACS protocol — obtain 12-lead ECG immediately",
    "Stroke / Neurological":  "Stroke alert — FAST assessment, CT head stat",
    "Trauma / Injury":        "Trauma activation — assess for hemorrhage",
    "Respiratory":            "O₂ therapy — prepare intubation if SpO₂ < 88%",
    "Abdominal Pain":         "Surgical consult — rule out perforation/ischemia",
    "Sepsis / Infection":     "Sepsis bundle — blood cultures, IV antibiotics stat",
    "Allergic Reaction":      "Anaphylaxis protocol — IM epinephrine if needed",
    "Psychiatric / Behavioral": "Safety assessment — 1:1 monitoring",
    "Minor Injury / Low Acuity": "Standard wound care",
    "GI / GU":                "Fluid resuscitation if hypotensive",
}

# ─────────────────────────────────────────────────────────────
# Simulation Parameters
# ─────────────────────────────────────────────────────────────

SIM_TOTAL_MINUTES     = 90     # default total simulation window
SIM_STEP_MINUTES      = 5      # granularity of each simulation step
REALTIME_REFRESH_MS   = 60_000 # real-time polling interval (ms) — used by the frontend

# Demo escalation targets — used in generate_data to bake in correct risk
DEMO_JAMES_INITIAL_RISK  = 4.5   # ESI-3, abdominal pain, 72yo — "stable" intake
DEMO_JAMES_TARGET_RISK   = 7.8   # should breach alert at ~70-90 min

# ─────────────────────────────────────────────────────────────
# ML Model Config
# ─────────────────────────────────────────────────────────────

ML_BLEND_RATIO      = 0.40    # fraction of composite score from ML (0.6 from rules)
ML_LABEL_HORIZON    = 60      # minutes ahead for deterioration label
ML_POSITIVE_RISK    = 7.5     # risk threshold that defines a positive label

# ─────────────────────────────────────────────────────────────
# App Display Config
# ─────────────────────────────────────────────────────────────

APP_TITLE          = "TriageAI — Intelligent ED Dynamic Triage"
APP_ICON           = "🏥"
APP_SUBTITLE       = "AI-powered continuous patient re-evaluation · Real-time deterioration detection"

MAX_ALERTS_SIDEBAR = 8      # max alerts shown in sidebar
MAX_HISTORY_POINTS = 500    # max entries in patient risk/vitals history
TOP_N_SHAP         = 6      # number of features shown in SHAP chart
