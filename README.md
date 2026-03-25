# TriageAI — Intelligent Emergency Department Flow Optimizer with Real-Time Acuity Re-Scoring

This is **NOT** a basic queue system. TriageAI is a dynamic, machine-learning-powered healthcare dashboard built on a core, life-saving insight:

**The problem:** In real emergency departments, a patient triaged as "low priority" at 2 PM might deteriorate by 3 PM — but nobody re-evaluates them. People literally die in waiting rooms because static triage scores don't update. This happens regularly and has been documented in news stories worldwide.

**The solution:** A system that continuously re-scores patient acuity using time-decay models and symptom progression patterns, dynamically re-prioritizing the queue and alerting staff to patients at risk of deterioration.

---

## Why This Idea Wins

Most healthcare projects are either basic medication reminders or simple FIFO queues. **TriageAI is categorically different because:**
- **It solves a problem most don't know exists:** The "deterioration in the waiting room" problem is real, documented, and shocking. This directly addresses the fatal flaw of one-time assessment.
- **Visible "before vs. after" impact:** Simulating a waiting room, showing a patient declining, and watching the system organically flag them in real time creates a powerful narrative.
- **Defensible and Explainable AI:** The ML isn't just a black box sorting a list. It's a time-aware risk model that can explicitly explain *why* it made its decisions.

---

## Key Features

- **Dynamic Acuity Re-Scoring Engine (The Core):** Every N minutes, each patient's risk score is recalculated based on time elapsed since triage (longer waits increase risk for certain conditions), vital sign trends if available (even simulated), symptom category (chest pain escalates differently than a sprained ankle), and age/comorbidity modifiers. This isn't just a timer — it's a clinical risk curve.
- **"Red Zone" Deterioration Alert:** When a patient's re-scored acuity crosses a threshold (≥ 7.50), the system fires a visual warning banner on the staff dashboard. This is the "wow moment" — watching a seemingly stable patient quietly escalate until the alert catches them.
- **Explainable Prioritization (Not a Black Box):** For each patient, SHAP (SHapley Additive exPlanations) integration shows exactly why they were moved up or down (e.g., "Patient re-prioritized: time-in-queue exceeds safe threshold for cardiac symptoms").
- **Simulated Waiting Room Visualization:** A fully offline-capable React frontend using Framer Motion physically transitions patient cards (green → yellow → red) and reorders them in real-time.
- **"What-If" Scenario Mode:** A clinical decision support tool that projects the future state of the waiting room queue if patients are left untreated, allowing for interactive queue forecasting.

---

## Tech Stack

The architecture is fully decoupled, using a modern Python backend bridged to a fast React frontend.

**Backend (Engine & API)**
- **Python 3.10+**
- **FastAPI & Uvicorn** (REST API bridge)
- **scikit-learn** (GradientBoostingClassifier)
- **SHAP** (TreeExplainer for model interpretability)
- **Pandas / NumPy**

**Frontend (Client)**
- **React 18** (via Vite)
- **Tailwind CSS** (for precise, dark-mode medical aesthetics)
- **Framer Motion** (for fluid queue-reordering layout physics)
- **Recharts** (for SHAP waterfall charts and time-lapse graphs)
- **Axios & lucide-react**

---

## How It Works

1. **Intake Processing:** A patient's demographics, primary symptom category, chief complaint, and initial vitals (HR, BP, SpO2, RR, Temp, GCS) are entered.
2. **Base Scoring:** The Python `engine/scorer.py` applies a deterministic, rule-based algorithm to assign an initial risk floor based on standard ESI protocols.
3. **ML Inference:** The patient vector is passed through the pre-trained Gradient Boosting model (`model/triage_model.pkl`). The model calculates the probability of acute deterioration within the next 60 minutes.
4. **Composite Risk Calculation:** The `engine/rescorer.py` merges the rule-based score, the ML probability, and a time-penalty modifier to generate a final dynamic score.
5. **Continuous Re-evaluation:** As simulation time elapses, physiological "drift" is applied to the patient's vitals based on their specific symptom category, forcing the ML model to continuously update its prediction.

---

## Installation & Setup

### 1. Start the Backend API
You will need Python 3 installed. Using a virtual environment is highly recommended.

```bash
# Clone the repository and enter the directory
git clone https://github.com/your-org/TriageAI.git
cd TriageAI

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install Python requirements
pip install -r requirements.txt
venv\Scripts\python.exe -m model.train_model --samples=500
# Start the FastAPI server on port 8000

uvicorn api.main:app --reload --port 8000
```

### 2. Start the Frontend Application
In a new terminal window / tab:

```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

Open your browser to `http://localhost:5173/` to view the dashboard.

---

## Usage Example

1. **Load the Demo Roster**: Click the "Load 10 Demo Patients" button on the empty queue screen. This loads a medically curated roster of patients operating at T=0 minutes.
2. **Watch the Escalation**: Click "⏩ Simulate 90 Minutes". Watch as the system fast-forwards time, drifts the patients' vitals, and automatically catches the hidden sepsis patient (James Wilson) before he crashes.
3. **Analyze the AI Logic**: Click on James Wilson's expanded patient card. Review the SHAP waterfall graph to see how his accumulating wait time and subtly climbing heart rate forced the ML model to flag him.
4. **Manual Intake**: Navigate to the "Add Patient" tab and input a custom patient to see how the mathematical baseline reacts in real-time.

### Example Intake Data (Hidden Sepsis)
An example of a case that traditional triage often misses, but exactly what this model is trained to catch.
- **Name:** James Wilson (Age: 72, Male)
- **Symptom Category:** Abdominal Pain
- **Chief Complaint:** Diffuse abdominal pain, nausea x2 days
- **Vitals at T=0:** HR 96, BP 124/76, SpO2 96%, RR 19, Temp 100.6°F
- **Outcome:** Starts as a low-priority ESI-3. After 60 minutes of waiting, his HR edges to 110 and Temp to 101.4°F. The model dynamically flags him as `CRITICAL` without requiring a nurse to manually re-take his vitals.

---

## Triage / Scoring Logic (Architecture Assumptions)

This system blends two distinct mathematical approaches:
1. **Rule-Based Anchor:** We implement a hard floor based on the Emergency Severity Index (ESI v5, AHRQ). For example, a patient presenting with active crushing chest pain is immediately locked at a minimum risk of 7.0 (ESI-2), regardless of what the machine learning model thinks. The AI is only permitted to *escalate* risk, never downgrade a fundamentally critical complaint.
2. **ML Deterioration Probability:** The Gradient Booster is trained on synthetic data representing distributions from the MIMIC-IV clinical database. It heavily relies on engineered interaction features (e.g., `age_x_vitals`, `hr_bp_ratio` proxying the shock index).

---

## ⚠️ Validation & Safety Disclaimer

**CRITICAL NOTICE: NOT A MEDICAL DEVICE.**

TriageAI was developed strictly as a technology demonstration / hackathon prototype.
- **NOT FOR CLINICAL USE:** This software has not been cleared or approved by the FDA or any regulatory body.
- **SYNTHETIC DATA:** The underlying machine learning model was trained on thousands of synthetically generated records, not real hospital outcomes. 
- **NO MEDICAL ADVICE:** The risk scores, "SHAP interpretations," and suggested triage levels generated by this application are for illustrative software engineering purposes only and must never be used to guide human medical care, triage, or diagnosis.

---

## Future Improvements

- **Live EHR Integration:** Replacing the manual intake form with real-time HL7 / FHIR data feeds directly from Epic or Cerner.
- **Pediatric-Specific Modeling:** The current engine is tuned strictly for adult physiology (Age > 18). A secondary ML model using pediatric vital sign thresholds (PEWS) must be separated.
- **Continuous Wearable Integration:** Integrating live, continuous vital sign feeds from waiting-room wearable biosensors instead of relying on the simulated vital-drift algorithm.

---

## Folder Structure

```text
triageai/
├── api/
│   └── main.py                 # FastAPI routing and bridge logic
├── data/
│   └── generate_data.py        # Synthetic patient demographics & vitals generator
├── engine/
│   ├── scorer.py               # Rule-based ESI & MEWS baseline calculations
│   └── rescorer.py             # ML inference, SHAP evaluation, and time-drift logic
├── frontend/                   # React + Vite Client Application
│   ├── src/
│   │   ├── components/         # Self-contained React UI elements
│   │   ├── hooks/              # Custom state & API lifecycles
│   │   └── index.css           # Global Tailwind tokens & animations
│   ├── package.json
│   └── tailwind.config.js
├── model/
│   ├── train_model.py          # Training pipeline & GridSearchCV for GBM
│   └── triage_model.pkl        # Serialized ML model and TreeExplainer
└── requirements.txt            # Python dependencies
```

---

## License

MIT License. See `LICENSE` for more information.
