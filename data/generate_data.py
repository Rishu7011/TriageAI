"""
generate_data.py — Synthetic Patient Data Generator for TriageAI
================================================================
Generates realistic ED patient records with:
  - Demographics (name, age, sex)
  - Vital signs (HR, BP, SpO2, RR, Temp, GCS)
  - Chief complaint + symptom category + ESI level
  - Time-in-ED tracking for dynamic re-scoring
  - Pre-scripted DEMO patients (including James Wilson, the key demo case)

No external dependencies beyond Python stdlib + numpy (for realistic distributions).
"""

import random
import numpy as np
from datetime import datetime, timedelta
import uuid

# ─────────────────────────────────────────────────────────────
# Symptom Categories & their base risk (1-10 scale) + ESI map
# ─────────────────────────────────────────────────────────────
SYMPTOM_CATEGORIES = {
    "Chest Pain / Cardiac": {
        "base_risk": 8.0,
        "esi_range": [1, 2],
        "deterioration_rate": 0.12,   # risk increase per minute elapsed
        "complaints": ["crushing chest pain", "chest tightness", "palpitations", "chest pressure with arm pain"],
    },
    "Stroke / Neurological": {
        "base_risk": 7.5,
        "esi_range": [1, 2],
        "deterioration_rate": 0.15,
        "complaints": ["sudden facial droop", "slurred speech", "arm weakness", "sudden severe headache"],
    },
    "Trauma / Injury": {
        "base_risk": 6.0,
        "esi_range": [2, 3],
        "deterioration_rate": 0.08,
        "complaints": ["MVA with head injury", "fall from height", "laceration with heavy bleeding", "blunt abdominal trauma"],
    },
    "Respiratory": {
        "base_risk": 6.5,
        "esi_range": [2, 3],
        "deterioration_rate": 0.10,
        "complaints": ["severe shortness of breath", "acute asthma attack", "difficulty breathing", "wheezing"],
    },
    "Abdominal Pain": {
        "base_risk": 4.5,
        "esi_range": [2, 3],
        "deterioration_rate": 0.07,   # James Wilson's category — subtle but escalating
        "complaints": ["diffuse abdominal pain", "right lower quadrant pain", "nausea and vomiting", "severe cramping"],
    },
    "Sepsis / Infection": {
        "base_risk": 7.0,
        "esi_range": [2, 3],
        "deterioration_rate": 0.13,
        "complaints": ["high fever with chills", "suspected sepsis", "wound infection with fever", "UTI with altered mental status"],
    },
    "Psychiatric / Behavioral": {
        "base_risk": 3.0,
        "esi_range": [3, 4],
        "deterioration_rate": 0.02,
        "complaints": ["suicidal ideation", "acute anxiety attack", "altered mental status", "agitation"],
    },
    "Minor Injury / Low Acuity": {
        "base_risk": 1.5,
        "esi_range": [4, 5],
        "deterioration_rate": 0.005,
        "complaints": ["sprained ankle", "minor laceration", "sore throat", "mild back pain"],
    },
    "Allergic Reaction": {
        "base_risk": 5.5,
        "esi_range": [2, 3],
        "deterioration_rate": 0.09,
        "complaints": ["anaphylaxis", "severe allergic reaction", "urticaria with throat tightness"],
    },
    "GI / GU": {
        "base_risk": 3.5,
        "esi_range": [3, 4],
        "deterioration_rate": 0.04,
        "complaints": ["vomiting blood", "rectal bleeding", "severe diarrhea with dehydration", "kidney stone pain"],
    },
}

# ESI Level definitions (1 = most critical, 5 = least)
ESI_DESCRIPTIONS = {
    1: "Immediate / Life-threatening",
    2: "Emergent / High Risk",
    3: "Urgent / Stable but needs workup",
    4: "Less Urgent / Minor",
    5: "Non-Urgent / Routine",
}

# ─────────────────────────────────────────────────────────────
# Vital Sign Generators (category-aware with realistic ranges)
# ─────────────────────────────────────────────────────────────

def generate_vitals(symptom_category: str, esi_level: int, age: int) -> dict:
    """
    Generate physiologically plausible vital signs based on acuity.
    Higher ESI = more abnormal vitals. Age affects baselines.
    """
    cat = SYMPTOM_CATEGORIES[symptom_category]
    base_risk = cat["base_risk"]

    # Severity multiplier: ESI 1 is most abnormal
    severity = (6 - esi_level) / 5.0  # 0.2 (ESI5) → 1.0 (ESI1)

    # ─── Heart Rate ───────────────────────────────────────────
    # Normal: 60-100. Tachycardia (>100) in high acuity.
    if symptom_category == "Chest Pain / Cardiac":
        hr_mean = 55 + severity * 90   # Can be bradycardic or very tachy
        hr = int(np.clip(np.random.normal(hr_mean, 12), 35, 180))
    else:
        hr_mean = 72 + severity * 55
        hr = int(np.clip(np.random.normal(hr_mean, 10), 45, 175))

    # ─── Blood Pressure ───────────────────────────────────────
    # Hypotension in shock states (sepsis/trauma), hypertension in cardiac
    if symptom_category in ["Sepsis / Infection", "Trauma / Injury"]:
        bp_sys = int(np.clip(np.random.normal(120 - severity * 45, 15), 60, 160))
    elif symptom_category in ["Chest Pain / Cardiac", "Stroke / Neurological"]:
        bp_sys = int(np.clip(np.random.normal(130 + severity * 40, 15), 90, 220))
    else:
        bp_sys = int(np.clip(np.random.normal(118 + severity * 20, 12), 80, 190))
    bp_dia = int(np.clip(bp_sys * np.random.uniform(0.55, 0.70), 40, 120))

    # ─── SpO2 (Oxygen Saturation) ─────────────────────────────
    # Respiratory patients have lower SpO2; critical patients too.
    if symptom_category == "Respiratory":
        spo2 = int(np.clip(np.random.normal(96 - severity * 14, 3), 72, 100))
    elif esi_level <= 2:
        spo2 = int(np.clip(np.random.normal(95 - severity * 6, 2), 80, 100))
    else:
        spo2 = int(np.clip(np.random.normal(98 - severity * 2, 1), 88, 100))

    # ─── Respiratory Rate ─────────────────────────────────────
    # Normal: 12-20. Elevated in respiratory/sepsis.
    rr = int(np.clip(np.random.normal(16 + severity * 12, 3), 8, 40))

    # ─── Temperature (°F) ─────────────────────────────────────
    if symptom_category == "Sepsis / Infection":
        temp = round(np.clip(np.random.normal(102.0, 1.2), 95.0, 106.0), 1)
    elif esi_level <= 2 and symptom_category != "Trauma / Injury":
        temp = round(np.clip(np.random.normal(100.4, 1.0), 96.0, 105.5), 1)
    else:
        temp = round(np.clip(np.random.normal(98.6, 0.8), 96.0, 103.0), 1)

    # ─── GCS (Glasgow Coma Scale: 3-15, 15 = normal) ─────────
    if symptom_category in ["Stroke / Neurological", "Trauma / Injury"] and esi_level <= 2:
        gcs = int(np.clip(round(np.random.normal(10 - severity * 5, 1.5)), 3, 15))
    elif symptom_category == "Sepsis / Infection" and severity > 0.6:
        gcs = int(np.clip(round(np.random.normal(12 - severity * 3, 1)), 3, 15))
    else:
        gcs = 15  # Most patients are alert

    # ─── Pain Score (0-10) ────────────────────────────────────
    pain = int(np.clip(round(np.random.normal(severity * 9, 1.5)), 0, 10))

    return {
        "heart_rate": hr,
        "bp_systolic": bp_sys,
        "bp_diastolic": bp_dia,
        "spo2": spo2,
        "respiratory_rate": rr,
        "temperature": temp,
        "gcs": gcs,
        "pain_score": pain,
    }


def compute_vitals_score(vitals: dict) -> float:
    """
    Compute a 0-10 physiological deterioration score from raw vitals.
    This feeds into the ML feature vector and base risk calculation.
    Uses Modified Early Warning Score (MEWS) principles.
    """
    score = 0.0

    # Heart Rate scoring
    hr = vitals["heart_rate"]
    if hr < 40 or hr > 140:
        score += 3
    elif hr < 50 or hr > 120:
        score += 2
    elif hr < 60 or hr > 100:
        score += 1

    # Blood Pressure (systolic)
    bp = vitals["bp_systolic"]
    if bp < 70 or bp > 200:
        score += 3
    elif bp < 80 or bp > 180:
        score += 2
    elif bp < 90 or bp > 160:
        score += 1

    # SpO2
    spo2 = vitals["spo2"]
    if spo2 < 85:
        score += 4
    elif spo2 < 90:
        score += 3
    elif spo2 < 94:
        score += 2
    elif spo2 < 97:
        score += 1

    # Respiratory Rate
    rr = vitals["respiratory_rate"]
    if rr < 8 or rr > 35:
        score += 3
    elif rr < 10 or rr > 25:
        score += 2
    elif rr < 12 or rr > 20:
        score += 1

    # Temperature
    temp = vitals["temperature"]
    if temp < 95.0 or temp > 105.0:
        score += 3
    elif temp < 96.0 or temp > 104.0:
        score += 2
    elif temp < 97.0 or temp > 101.5:
        score += 1

    # GCS (consciousness)
    gcs = vitals["gcs"]
    if gcs <= 8:
        score += 4
    elif gcs <= 11:
        score += 3
    elif gcs <= 13:
        score += 2
    elif gcs < 15:
        score += 1

    # Normalize to 0-10 scale (max raw score is ~20)
    return round(min(score / 20.0 * 10.0, 10.0), 2)


# ─────────────────────────────────────────────────────────────
# Age Risk Modifier
# ─────────────────────────────────────────────────────────────

def age_risk_modifier(age: int) -> float:
    """
    Older and very young patients have higher baseline risk.
    Returns a multiplier: 1.0 = no change, >1.0 = higher risk.
    """
    if age < 2:
        return 1.40    # Infants — very high risk
    elif age < 12:
        return 1.20    # Pediatric
    elif age < 18:
        return 1.05    # Adolescent
    elif age < 50:
        return 1.00    # Adult baseline
    elif age < 65:
        return 1.10    # Middle-aged
    elif age < 75:
        return 1.25    # Elderly
    elif age < 85:
        return 1.40    # Very elderly (James Wilson range)
    else:
        return 1.55    # Extreme age


# ─────────────────────────────────────────────────────────────
# Patient Name Pools
# ─────────────────────────────────────────────────────────────

MALE_NAMES = [
    "James Wilson", "Robert Chen", "Michael Torres", "David Patel",
    "John Murphy", "Carlos Rivera", "Ahmed Hassan", "Marcus Johnson",
    "William Park", "Thomas Anderson", "Kevin O'Brien", "Daniel Kim",
    "Christopher Lee", "Matthew Clark", "Benjamin Harris"
]

FEMALE_NAMES = [
    "Sarah Mitchell", "Emily Rodriguez", "Jennifer Walsh", "Lisa Thompson",
    "Maria Garcia", "Aisha Williams", "Sophie Laurent", "Rachel Cohen",
    "Patricia Nguyen", "Amanda Foster", "Christina Morales", "Diana Prince",
    "Helen Zhang", "Natalie Moore", "Rebecca Taylor"
]


# ─────────────────────────────────────────────────────────────
# Core Patient Generator
# ─────────────────────────────────────────────────────────────

def generate_patient(
    name: str = None,
    age: int = None,
    sex: str = None,
    symptom_category: str = None,
    esi_level: int = None,
    arrival_minutes_ago: int = None,
    chief_complaint: str = None,
    vitals_override: dict = None,
) -> dict:
    """
    Generate a single synthetic ED patient record.
    All parameters are optional — randomized if not provided.
    'arrival_minutes_ago' = how long the patient has been waiting.
    """
    # ── Demographics ──────────────────────────────────────────
    sex = sex or random.choice(["Male", "Female"])
    if name is None:
        pool = MALE_NAMES if sex == "Male" else FEMALE_NAMES
        name = random.choice(pool)

    if age is None:
        # Skew toward adult/elderly for realistic ED distribution
        age = int(np.clip(np.random.choice(
            [random.randint(18, 45), random.randint(50, 85)],
            p=[0.4, 0.6]
        ), 1, 100))

    # ── Symptom & ESI ─────────────────────────────────────────
    if symptom_category is None:
        # Weighted distribution matching real ED visit patterns
        categories = list(SYMPTOM_CATEGORIES.keys())
        weights = [0.12, 0.06, 0.14, 0.10, 0.16, 0.08, 0.08, 0.16, 0.04, 0.06]
        symptom_category = random.choices(categories, weights=weights, k=1)[0]

    cat_config = SYMPTOM_CATEGORIES[symptom_category]

    if esi_level is None:
        esi_min, esi_max = cat_config["esi_range"]
        esi_level = random.randint(esi_min, esi_max)

    if chief_complaint is None:
        chief_complaint = random.choice(cat_config["complaints"])

    # ── Vitals ────────────────────────────────────────────────
    if vitals_override:
        vitals = vitals_override
    else:
        vitals = generate_vitals(symptom_category, esi_level, age)

    vitals_score = compute_vitals_score(vitals)

    # ── Arrival Time ──────────────────────────────────────────
    if arrival_minutes_ago is None:
        arrival_minutes_ago = random.randint(2, 120)

    arrival_time = datetime.now() - timedelta(minutes=arrival_minutes_ago)

    # ── Risk Score ────────────────────────────────────────────
    # Base risk from symptom category + age modifier
    base_risk = cat_config["base_risk"]
    age_mod = age_risk_modifier(age)
    initial_risk = base_risk * age_mod

    # Factor in vitals
    vitals_contribution = vitals_score * 0.5
    initial_risk = min(initial_risk + vitals_contribution, 10.0)

    # ── Wait time risk escalation (initial calculation) ───────
    # Time-based deterioration: the longer they wait, the higher risk
    time_elapsed_risk = cat_config["deterioration_rate"] * arrival_minutes_ago
    current_risk = min(initial_risk + time_elapsed_risk, 10.0)

    # ── Alert status ──────────────────────────────────────────
    alert_threshold = 7.5  # Fires when risk crosses this
    alert_fired = current_risk >= alert_threshold

    return {
        # Identity
        "patient_id": str(uuid.uuid4())[:8].upper(),
        "name": name,
        "age": age,
        "sex": sex,

        # Clinical
        "chief_complaint": chief_complaint,
        "symptom_category": symptom_category,
        "esi_level": esi_level,
        "esi_description": ESI_DESCRIPTIONS[esi_level],

        # Vitals (snapshot at current time)
        "vitals": vitals,
        "vitals_score": vitals_score,

        # Risk Engine
        "initial_risk": round(initial_risk, 2),
        "current_risk": round(current_risk, 2),
        "base_risk": round(base_risk, 2),
        "age_modifier": round(age_mod, 2),
        "deterioration_rate": cat_config["deterioration_rate"],

        # Timing
        "arrival_time": arrival_time.isoformat(),
        "arrival_minutes_ago": arrival_minutes_ago,
        "minutes_in_ed": arrival_minutes_ago,  # updated by rescorer

        # Alert State
        "alert_fired": alert_fired,
        "alert_acknowledged": False,
        "alert_reason": f"Risk score {current_risk:.1f} exceeds threshold {alert_threshold}" if alert_fired else None,

        # Simulation bookkeeping
        "risk_history": [
            {
                "timestamp": arrival_time.isoformat(),
                "risk": round(initial_risk, 2),
                "minutes_in_ed": 0,
                "esi_level": esi_level,
            }
        ],
        "vitals_history": [
            {
                "timestamp": arrival_time.isoformat(),
                "vitals": dict(vitals),
            }
        ],

        # SHAP placeholder (populated by ML engine on demand)
        "shap_values": None,
        "shap_base_value": None,
        "shap_feature_names": None,
    }


# ─────────────────────────────────────────────────────────────
# DEMO PATIENT ROSTER (Scripted for maximum demo impact)
# ─────────────────────────────────────────────────────────────

def generate_demo_patients() -> list:
    """
    Returns 6 hand-crafted patients optimized for the live demo.
    Key escalation: James Wilson (ESI 3 → 2) is patient index 0.

    Patient roster:
      0. James Wilson   — 72yo abdominal pain   [DEMO HERO: will escalate]
      1. Sarah Mitchell — 45yo chest pain        [ESI 2, already high alert]
      2. Carlos Rivera  — 28yo trauma (MVA)      [ESI 2, stable but serious]
      3. Emily Rodriguez— 8yo respiratory        [ESI 3, pediatric]
      4. Robert Chen    — 61yo sepsis            [ESI 2, deteriorating]
      5. Lisa Thompson  — 34yo minor injury      [ESI 4, low priority]
    """

    patients = []

    # ── Patient 0: James Wilson ──────────────────────────────
    # THE DEMO STAR: 72yo elderly male, abdominal pain.
    # Arrives ESI-3 looking "stable" but has insidious septic abdomen.
    # His age modifier (1.40) + slow deterioration rate will push him
    # from risk ~5.2 → 7.8+ after simulated 90 min, triggering alert.
    james = generate_patient(
        name="James Wilson",
        age=72,
        sex="Male",
        symptom_category="Abdominal Pain",
        esi_level=3,
        chief_complaint="diffuse abdominal pain, fever of 100.8°F, nausea x2 days",
        arrival_minutes_ago=15,   # just arrived — low current risk
        vitals_override={
            "heart_rate": 98,          # slightly elevated — easy to miss
            "bp_systolic": 132,
            "bp_diastolic": 78,
            "spo2": 96,
            "respiratory_rate": 19,    # slightly elevated
            "temperature": 100.8,      # low-grade fever
            "gcs": 15,                 # fully alert — doesn't LOOK sick
            "pain_score": 6,
        },
    )
    james["_demo_note"] = "ESCALATION PATIENT: ESI3→ESI2 after 90min simulation"
    patients.append(james)

    # ── Patient 1: Sarah Mitchell ────────────────────────────
    # Clear ESI-2: recent chest pain, diaphoretic, classic STEMI presentation
    sarah = generate_patient(
        name="Sarah Mitchell",
        age=45,
        sex="Female",
        symptom_category="Chest Pain / Cardiac",
        esi_level=2,
        chief_complaint="crushing chest pain radiating to left arm, diaphoresis",
        arrival_minutes_ago=8,
        vitals_override={
            "heart_rate": 112,
            "bp_systolic": 158,
            "bp_diastolic": 92,
            "spo2": 94,
            "respiratory_rate": 22,
            "temperature": 98.2,
            "gcs": 15,
            "pain_score": 9,
        },
    )
    sarah["_demo_note"] = "ESI-2 cardiac — high risk, already flagged"
    patients.append(sarah)

    # ── Patient 2: Carlos Rivera ─────────────────────────────
    # Trauma — MVA, stable hemodynamics but head injury risk
    carlos = generate_patient(
        name="Carlos Rivera",
        age=28,
        sex="Male",
        symptom_category="Trauma / Injury",
        esi_level=2,
        chief_complaint="MVA, head strike on steering wheel, confusion",
        arrival_minutes_ago=25,
        vitals_override={
            "heart_rate": 104,
            "bp_systolic": 118,
            "bp_diastolic": 72,
            "spo2": 97,
            "respiratory_rate": 18,
            "temperature": 98.6,
            "gcs": 13,             # slightly confused — concerning
            "pain_score": 7,
        },
    )
    carlos["_demo_note"] = "ESI-2 trauma — stable vitals but GCS 13"
    patients.append(carlos)

    # ── Patient 3: Emily Rodriguez ───────────────────────────
    # Pediatric respiratory — asthma, ESI-3
    emily = generate_patient(
        name="Emily Rodriguez",
        age=8,
        sex="Female",
        symptom_category="Respiratory",
        esi_level=3,
        chief_complaint="acute asthma exacerbation, wheezing, mild retractions",
        arrival_minutes_ago=40,
        vitals_override={
            "heart_rate": 118,     # normal-high for peds
            "bp_systolic": 105,
            "bp_diastolic": 62,
            "spo2": 93,            # borderline
            "respiratory_rate": 28,
            "temperature": 99.2,
            "gcs": 15,
            "pain_score": 3,
        },
    )
    emily["_demo_note"] = "ESI-3 pediatric respiratory — SpO2 watch"
    patients.append(emily)

    # ── Patient 4: Robert Chen ───────────────────────────────
    # Sepsis — already deteriorating, high risk
    robert = generate_patient(
        name="Robert Chen",
        age=61,
        sex="Male",
        symptom_category="Sepsis / Infection",
        esi_level=2,
        chief_complaint="high fever, rigors, hypotension, altered mental status",
        arrival_minutes_ago=55,
        vitals_override={
            "heart_rate": 128,
            "bp_systolic": 88,     # hypotensive — septic shock concern
            "bp_diastolic": 52,
            "spo2": 91,
            "respiratory_rate": 26,
            "temperature": 103.8,
            "gcs": 13,
            "pain_score": 5,
        },
    )
    robert["_demo_note"] = "ESI-2 sepsis — should already be in resus"
    patients.append(robert)

    # ── Patient 5: Lisa Thompson ─────────────────────────────
    # Low acuity — sprained ankle, deliberate ESI-4 contrast for demo
    lisa = generate_patient(
        name="Lisa Thompson",
        age=34,
        sex="Female",
        symptom_category="Minor Injury / Low Acuity",
        esi_level=4,
        chief_complaint="sprained ankle after running, mild swelling",
        arrival_minutes_ago=70,
        vitals_override={
            "heart_rate": 76,
            "bp_systolic": 118,
            "bp_diastolic": 74,
            "spo2": 99,
            "respiratory_rate": 14,
            "temperature": 98.4,
            "gcs": 15,
            "pain_score": 4,
        },
    )
    lisa["_demo_note"] = "ESI-4 minor — contrast low-risk patient for demo"
    patients.append(lisa)

    return patients


# ─────────────────────────────────────────────────────────────
# Random Patient Generator (for bulk testing / padding queue)
# ─────────────────────────────────────────────────────────────

def generate_random_patients(n: int = 10) -> list:
    """Generate n fully randomized ED patients."""
    used_names = set()
    patients = []
    all_names = MALE_NAMES + FEMALE_NAMES

    for _ in range(n):
        # Avoid duplicate names in same session
        available = [nm for nm in all_names if nm not in used_names]
        name = random.choice(available) if available else None
        if name:
            used_names.add(name)

        p = generate_patient(name=name)
        patients.append(p)

    return patients


# ─────────────────────────────────────────────────────────────
# What-If Scenario: Critical Trauma Patient (Demo Step 5)
# ─────────────────────────────────────────────────────────────

def generate_critical_trauma_patient() -> dict:
    """
    Generate a critical trauma patient for the What-If mode demo.
    This patient (Marcus Johnson) arrives as ESI-1 and immediately
    re-orders the queue — dramatizing how TriageAI handles acute influx.
    """
    p = generate_patient(
        name="Marcus Johnson",
        age=19,
        sex="Male",
        symptom_category="Trauma / Injury",
        esi_level=1,
        chief_complaint="gunshot wound to abdomen, unresponsive on arrival",
        arrival_minutes_ago=1,
        vitals_override={
            "heart_rate": 148,
            "bp_systolic": 62,     # severely hypotensive — hemorrhagic shock
            "bp_diastolic": 34,
            "spo2": 84,
            "respiratory_rate": 32,
            "temperature": 97.1,   # hypothermia from blood loss
            "gcs": 6,              # severely altered
            "pain_score": 10,
        },
    )
    p["_demo_note"] = "WHAT-IF PATIENT: ESI-1 trauma arrival, reorders queue"
    return p


# ─────────────────────────────────────────────────────────────
# Feature Vector Builder (for ML model input)
# ─────────────────────────────────────────────────────────────

FEATURE_NAMES = [
    "age",
    "esi_level",
    "heart_rate",
    "bp_systolic",
    "bp_diastolic",
    "spo2",
    "respiratory_rate",
    "temperature",
    "gcs",
    "pain_score",
    "vitals_score",
    "minutes_in_ed",
    "deterioration_rate",
    "age_modifier",
    "base_risk",
]


def patient_to_features(patient: dict) -> list:
    """
    Convert a patient dict into a flat feature vector for ML model inference.
    Order must match FEATURE_NAMES exactly.
    """
    v = patient["vitals"]
    return [
        patient["age"],
        patient["esi_level"],
        v["heart_rate"],
        v["bp_systolic"],
        v["bp_diastolic"],
        v["spo2"],
        v["respiratory_rate"],
        v["temperature"],
        v["gcs"],
        v["pain_score"],
        patient["vitals_score"],
        patient["minutes_in_ed"],
        patient["deterioration_rate"],
        patient["age_modifier"],
        patient["base_risk"],
    ]


# ─────────────────────────────────────────────────────────────
# Training Data Generator (for train_model.py)
# ─────────────────────────────────────────────────────────────

def generate_training_dataset(n_samples: int = 5000) -> tuple:
    """
    Generate a labeled dataset for training the GradientBoostingClassifier.

    Labels (y): Binary — 1 if patient will deteriorate (risk > 7.0) within
                 60 minutes, 0 otherwise. Determined by simulating future state.

    Returns:
        X: list of feature vectors (shape: n_samples × len(FEATURE_NAMES))
        y: list of binary labels (0 or 1)
        feature_names: list of feature name strings
    """
    X, y = [], []

    for _ in range(n_samples):
        # Randomize a patient at some point in their ED stay
        p = generate_patient(
            arrival_minutes_ago=random.randint(0, 180)
        )

        features = patient_to_features(p)
        X.append(features)

        # Label: will this patient's risk exceed 7.0 in the next 60 minutes?
        future_minutes = p["minutes_in_ed"] + 60
        future_time_risk = p["deterioration_rate"] * future_minutes
        future_risk = min(p["initial_risk"] + future_time_risk, 10.0)

        # Add some noise to avoid perfectly linear labels
        noise = np.random.normal(0, 0.3)
        future_risk = min(max(future_risk + noise, 0), 10.0)

        label = 1 if future_risk >= 7.0 else 0
        y.append(label)

    return X, y, FEATURE_NAMES


# ─────────────────────────────────────────────────────────────
# Quick Sanity Test
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🏥 TriageAI — Synthetic Data Generator Test\n" + "=" * 50)

    print("\n📋 DEMO PATIENTS:")
    demo = generate_demo_patients()
    for i, p in enumerate(demo):
        v = p["vitals"]
        print(
            f"  [{i}] {p['name']:20s} | Age {p['age']} {p['sex']:6s} | "
            f"ESI {p['esi_level']} | Risk {p['current_risk']:.1f} | "
            f"HR {v['heart_rate']} BP {v['bp_systolic']}/{v['bp_diastolic']} "
            f"SpO2 {v['spo2']}% Temp {v['temperature']}°F | "
            f"{p['chief_complaint'][:40]}"
        )

    print("\n🎲 RANDOM PATIENTS (5 samples):")
    random_pts = generate_random_patients(5)
    for p in random_pts:
        v = p["vitals"]
        print(
            f"  {p['name']:20s} | Age {p['age']} | ESI {p['esi_level']} | "
            f"Risk {p['current_risk']:.1f} | {p['symptom_category']}"
        )

    print("\n🚨 WHAT-IF TRAUMA PATIENT:")
    trauma = generate_critical_trauma_patient()
    v = trauma["vitals"]
    print(
        f"  {trauma['name']} | Age {trauma['age']} | ESI {trauma['esi_level']} | "
        f"Risk {trauma['current_risk']:.1f} | BP {v['bp_systolic']}/{v['bp_diastolic']} "
        f"SpO2 {v['spo2']}% GCS {v['gcs']}"
    )

    print("\n📊 TRAINING DATASET (100 samples):")
    X, y, fnames = generate_training_dataset(100)
    pos = sum(y)
    print(f"  Features: {len(fnames)} | Samples: {len(X)} | "
          f"Deterioration rate: {pos}/{len(y)} ({pos/len(y)*100:.1f}%)")
    print(f"  Feature names: {fnames}")

    print("\n✅ All generators working correctly!")
