"""
app.py — TriageAI Streamlit Application
========================================
8-10 minute demo flow:
  1. Live patient queue with real-time risk scores
  2. 90-minute simulation → James Wilson escalates ESI 3→2 with alert
  3. Patient detail card → SHAP waterfall explanation
  4. What-If mode → inject Marcus Johnson (ESI-1), watch queue reorder
  5. Alert sidebar with acknowledge workflow

Run:
  streamlit run app.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json

# ── Autorefresh (real-time mode) ──────────────────────────────
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# ── TriageAI engine imports ───────────────────────────────────
from data.generate_data import generate_demo_patients, generate_critical_trauma_patient
from engine.scorer import (
    compute_risk_score, risk_to_color, risk_to_label, esi_to_color,
    sort_patients_by_priority, ALERT_THRESHOLD
)
from engine.rescorer import (
    ModelManager, rescore_all_patients, simulate_time_jump,
    explain_patient, inject_patient, get_active_alerts,
    acknowledge_alert, get_alert_summary, get_risk_curve_data,
)

# ─────────────────────────────────────────────────────────────
# Page Config + CSS
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TriageAI — Intelligent ED Triage",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = """
<style>
/* ── Global ─────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0a0e1a;
    color: #e2e8f0;
}

.stApp { background-color: #0a0e1a; }

/* ── Sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1629 0%, #0a0e1a 100%);
    border-right: 1px solid #1e2d4a;
}

/* ── Metric boxes ───────────────────────────────────── */
[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 1rem;
}

/* ── Buttons ─────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed);
    color: white;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.6rem 1.4rem;
    transition: all 0.2s ease;
    cursor: pointer;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(124, 58, 237, 0.5);
}

/* ── Patient card ────────────────────────────────────── */
.patient-card {
    background: linear-gradient(135deg, #111827 0%, #0f1629 100%);
    border: 1px solid #1e2d4a;
    border-radius: 16px;
    padding: 1.25rem;
    margin-bottom: 0.75rem;
    transition: all 0.25s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}
.patient-card:hover {
    border-color: #3b82f6;
    transform: translateY(-2px);
    box-shadow: 0 12px 35px rgba(59, 130, 246, 0.15);
}
.patient-card.alert {
    border-color: #ef4444 !important;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.25);
    animation: pulse-border 2s infinite;
}
@keyframes pulse-border {
    0%   { box-shadow: 0 0 15px rgba(239,68,68,0.25); }
    50%  { box-shadow: 0 0 30px rgba(239,68,68,0.55); }
    100% { box-shadow: 0 0 15px rgba(239,68,68,0.25); }
}

/* ── Risk badge ──────────────────────────────────────── */
.risk-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* ── ESI badge ───────────────────────────────────────── */
.esi-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34px;
    height: 34px;
    border-radius: 50%;
    font-weight: 800;
    font-size: 1rem;
    color: #000;
}

/* ── Alert banner ────────────────────────────────────── */
.alert-banner {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.05));
    border: 1px solid rgba(239,68,68,0.4);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    animation: fadeIn 0.5s ease;
}
@keyframes fadeIn { from { opacity:0; transform:translateY(-8px); } to { opacity:1; transform:translateY(0); } }

/* ── Section headers ─────────────────────────────────── */
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #93c5fd;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e2d4a;
}

/* ── Vitals grid ─────────────────────────────────────── */
.vital-chip {
    display: inline-block;
    background: rgba(30,45,74,0.7);
    border: 1px solid #1e2d4a;
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 0.78rem;
    margin: 2px;
    font-family: 'Inter', monospace;
}

/* ── Progress bar override ───────────────────────────── */
.stProgress > div > div {
    border-radius: 8px;
}

/* ── Tabs ────────────────────────────────────────────── */
[data-testid="stTabs"] > div > div {
    background: #111827;
    border-radius: 12px;
    border: 1px solid #1e2d4a;
}

/* ── Dividers ────────────────────────────────────────── */
hr { border-color: #1e2d4a; }

/* ── Inputs ──────────────────────────────────────────── */
[data-testid="stSelectbox"] > div, [data-testid="stSlider"] {
    background: #111827;
}

/* ── Scrollbar ───────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #1e2d4a; border-radius: 4px; }

/* ── Hide Streamlit branding ─────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
</style>
"""

st.markdown(DARK_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────

def init_session():
    """Initialize all session state on first load."""
    if "initialized" not in st.session_state:
        st.session_state.initialized         = True
        st.session_state.patients            = []
        st.session_state.all_alerts          = []
        st.session_state.selected_patient_id = None
        st.session_state.simulation_run      = False
        st.session_state.simulation_snapshots = []
        st.session_state.whatif_mode         = False
        st.session_state.whatif_injected     = False
        st.session_state.real_time_mode      = False
        st.session_state.real_time_elapsed   = 0.0
        st.session_state.last_rescore_time   = time.time()
        st.session_state.show_shap           = False
        st.session_state.model_loaded        = False
        st.session_state.demo_mode           = True        # start with demo patients
        st.session_state.tick_count          = 0

    # Load model once
    if not st.session_state.model_loaded:
        st.session_state.model_loaded = ModelManager.load_model()

    # Load demo patients if queue is empty
    if not st.session_state.patients:
        patients = generate_demo_patients()
        # Initial score pass so all patients have component_scores
        for p in patients:
            result = compute_risk_score(p)
            p["current_risk"]     = result["composite_risk"]
            p["component_scores"] = result["component_scores"]
            p["weighted_scores"]  = result["weighted_scores"]
            p["score_breakdown"]  = result["score_breakdown"]
            p["alerts"]           = []
            p["vitals_trend"]     = {}
            p["esi_upgraded"]     = False

        st.session_state.patients = sort_patients_by_priority(patients)


# ─────────────────────────────────────────────────────────────
# Helper Renderers
# ─────────────────────────────────────────────────────────────

def render_risk_bar(risk: float, height: int = 8) -> str:
    """Render an HTML risk progress bar."""
    pct   = min(risk / 10.0 * 100, 100)
    color = risk_to_color(risk)
    return f"""
    <div style="background:#1e2d4a; border-radius:4px; height:{height}px; width:100%; overflow:hidden;">
      <div style="width:{pct:.1f}%; height:100%; background:{color};
                  border-radius:4px; transition:width 0.5s ease;"></div>
    </div>"""


def render_vitals_chips(vitals: dict, trend: dict = None) -> str:
    """Render compact vitals chips row with trend arrows."""
    trend = trend or {}
    items = [
        ("❤️", "HR", vitals.get("heart_rate", "—"), "bpm"),
        ("🩸", "BP", f"{vitals.get('bp_systolic','—')}/{vitals.get('bp_diastolic','—')}", ""),
        ("🫁", "SpO₂", vitals.get("spo2", "—"), "%"),
        ("🌡️", "T", vitals.get("temperature", "—"), "°F"),
        ("💨", "RR", vitals.get("respiratory_rate", "—"), "/m"),
        ("🧠", "GCS", vitals.get("gcs", "—"), "/15"),
    ]
    chips = []
    vital_key_map = {
        "HR": "heart_rate", "BP": "bp_systolic",
        "SpO₂": "spo2", "T": "temperature",
        "RR": "respiratory_rate", "GCS": "gcs"
    }
    for icon, label, val, unit in items:
        t = trend.get(vital_key_map.get(label, ""), {})
        arrow = t.get("trend", "")
        color = "#ef4444" if t.get("direction") == "worsening" else \
                "#22c55e" if t.get("direction") == "improving" else "#94a3b8"
        chips.append(
            f'<span class="vital-chip" style="color:{color}">'
            f'{icon} {label}: <b>{val}</b>{unit} {arrow}</span>'
        )
    return "".join(chips)


def render_esi_badge(esi: int) -> str:
    color = esi_to_color(esi)
    return (f'<span class="esi-badge" style="background:{color};">{esi}</span>')


def render_patient_card(patient: dict, selected: bool = False) -> str:
    """Render a full patient card as HTML."""
    risk      = patient.get("current_risk", 0)
    esi       = patient.get("esi_level", 3)
    name      = patient.get("name", "Unknown")
    age       = patient.get("age", "—")
    sex       = patient.get("sex", "")
    complaint = patient.get("chief_complaint", "")[:55]
    mins      = patient.get("minutes_in_ed", 0)
    vitals    = patient.get("vitals", {})
    trend     = patient.get("vitals_trend", {})
    alerted   = patient.get("alert_fired", False)
    upgraded  = patient.get("esi_upgraded", False)
    delta     = patient.get("risk_delta", 0)

    risk_color  = risk_to_color(risk)
    risk_label  = risk_to_label(risk)
    card_class  = "patient-card alert" if alerted else "patient-card"
    border_style= f"border-left: 4px solid {risk_color};"
    sel_style   = "box-shadow: 0 0 0 2px #3b82f6;" if selected else ""

    delta_html = ""
    if abs(delta) > 0.05:
        d_color = "#ef4444" if delta > 0 else "#22c55e"
        d_arrow = "▲" if delta > 0 else "▼"
        delta_html = f'<span style="color:{d_color}; font-size:0.78rem; font-weight:600;">{d_arrow}{abs(delta):.1f}</span>'

    esi_badge  = render_esi_badge(esi)
    risk_bar   = render_risk_bar(risk)
    vital_chips = render_vitals_chips(vitals, trend)

    esc_tag = ""
    if upgraded:
        esc_tag = '<span style="background:#7c3aed22;border:1px solid #7c3aed;border-radius:4px;padding:1px 7px;font-size:0.7rem;color:#a78bfa;font-weight:700;margin-left:6px;">ESI UPGRADED ⬆</span>'

    alert_tag = ""
    if alerted:
        alert_tag = '<span style="background:#ef444422;border:1px solid #ef4444;border-radius:4px;padding:1px 7px;font-size:0.7rem;color:#fca5a5;font-weight:700;margin-left:6px;">🚨 ALERT</span>'

    wait_str = f"{int(mins)}m" if mins < 60 else f"{int(mins//60)}h {int(mins%60)}m"

    return f"""
    <div class="{card_class}" style="{border_style}{sel_style}">
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
        <div style="display:flex; align-items:center; gap:10px;">
          {esi_badge}
          <div>
            <div style="font-weight:700; font-size:1rem; color:#f1f5f9;">{name}</div>
            <div style="font-size:0.78rem; color:#64748b;">{age}y {sex} · ⏱ {wait_str}</div>
          </div>
          {esc_tag}{alert_tag}
        </div>
        <div style="text-align:right;">
          <div style="font-size:1.6rem; font-weight:800; color:{risk_color}; line-height:1;">{risk:.1f}</div>
          <div style="font-size:0.7rem; color:{risk_color}; font-weight:600;">{risk_label} {delta_html}</div>
        </div>
      </div>
      <div style="font-size:0.82rem; color:#94a3b8; margin-bottom:0.5rem; font-style:italic;">"{complaint}…"</div>
      {risk_bar}
      <div style="margin-top:0.5rem;">{vital_chips}</div>
    </div>
    """


# ─────────────────────────────────────────────────────────────
# SHAP Waterfall Chart
# ─────────────────────────────────────────────────────────────

def render_shap_chart(patient: dict) -> go.Figure:
    """Render an interactive SHAP waterfall / force bar chart."""
    shap_data = explain_patient(patient)

    labels  = shap_data.get("feature_labels", shap_data.get("feature_names", []))
    values  = shap_data.get("shap_values", [])
    base    = shap_data.get("base_value", 3.5)
    is_fallback = shap_data.get("is_fallback", True)

    if not values:
        return go.Figure()

    # Sort by absolute impact descending
    pairs = sorted(zip(labels, values), key=lambda x: abs(x[1]), reverse=True)
    labels_s, values_s = zip(*pairs)

    colors = ["#ef4444" if v > 0 else "#22c55e" for v in values_s]

    fig = go.Figure(go.Bar(
        x=list(values_s),
        y=list(labels_s),
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v:+.3f}" for v in values_s],
        textposition="outside",
        textfont=dict(color="#e2e8f0", size=11),
        hovertemplate="<b>%{y}</b><br>SHAP impact: %{x:+.3f}<extra></extra>",
    ))

    total = base + sum(values_s)
    title_suffix = " (Rule-based)" if is_fallback else " (ML SHAP)"

    fig.update_layout(
        title=dict(
            text=f"Why is {patient.get('name', 'Patient')}'s risk <b>{patient.get('current_risk', 0):.1f}/10</b>?{title_suffix}",
            font=dict(size=14, color="#e2e8f0"),
        ),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#e2e8f0", family="Inter"),
        height=380,
        margin=dict(l=10, r=80, t=50, b=20),
        xaxis=dict(
            title="Risk Impact Score (↑ increases risk, ↓ decreases risk)",
            gridcolor="#1e2d4a",
            zerolinecolor="#374151",
            zerolinewidth=2,
            tickfont=dict(size=10),
        ),
        yaxis=dict(gridcolor="#1e2d4a", tickfont=dict(size=11)),
        shapes=[dict(
            type="line",
            x0=0, x1=0, y0=-0.5, y1=len(labels_s) - 0.5,
            line=dict(color="#4b5563", width=1, dash="dot"),
        )],
        annotations=[dict(
            x=max(values_s) * 1.1,
            y=len(labels_s) - 1,
            text=f"Base: {base:.2f} | Total: {total:.2f}",
            showarrow=False,
            font=dict(size=10, color="#6b7280"),
            xanchor="right",
        )],
    )
    return fig


# ─────────────────────────────────────────────────────────────
# Risk Curve Chart
# ─────────────────────────────────────────────────────────────

def render_risk_curves(patients: list, highlight_id: str = None) -> go.Figure:
    """
    Multi-line risk curve chart showing all patients' risk over time.
    The WOW chart — James Wilson's line visibly climbs and crosses 7.5.
    """
    fig = go.Figure()

    # Add alert threshold line
    fig.add_hline(
        y=ALERT_THRESHOLD,
        line=dict(color="#ef4444", width=1.5, dash="dash"),
        annotation_text=f"Alert Threshold ({ALERT_THRESHOLD})",
        annotation_font=dict(color="#ef4444", size=10),
        annotation_position="top right",
    )

    for p in patients:
        if p.get("discharged"):
            continue

        curve    = get_risk_curve_data(p)
        x_vals   = curve["x"]
        y_vals   = curve["y"]
        name     = p.get("name", "?")
        pid      = p.get("patient_id")
        risk_col = risk_to_color(p.get("current_risk", 0))

        if len(x_vals) < 2:
            continue

        # Highlight selected patient with thicker line
        is_highlight = pid == highlight_id or "James Wilson" in name
        line_width   = 3.5 if is_highlight else 1.2
        opacity      = 1.0 if is_highlight else 0.45
        mode         = "lines+markers" if is_highlight else "lines"

        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode=mode,
            name=name,
            line=dict(color=risk_col, width=line_width),
            opacity=opacity,
            marker=dict(size=5 if is_highlight else 3),
            hovertemplate=f"<b>{name}</b><br>Time: %{{x:.0f}} min<br>Risk: %{{y:.1f}}/10<extra></extra>",
        ))

        # Alert annotation
        for ann in curve.get("annotations", []):
            fig.add_annotation(
                x=ann["x"], y=ann["y"],
                text=ann["label"],
                showarrow=True,
                arrowhead=2,
                arrowcolor=risk_col,
                font=dict(color=risk_col, size=10, family="Inter"),
                bgcolor="#0a0e1a",
                bordercolor=risk_col,
                borderwidth=1,
                borderpad=4,
            )

    fig.update_layout(
        paper_bgcolor="#111827",
        plot_bgcolor="#0f1629",
        font=dict(color="#e2e8f0", family="Inter"),
        height=380,
        margin=dict(l=10, r=10, t=20, b=40),
        legend=dict(
            bgcolor="#111827", bordercolor="#1e2d4a",
            borderwidth=1, font=dict(size=10),
            x=0, y=1, xanchor="left", yanchor="top",
        ),
        xaxis=dict(
            title="Time in ED (minutes)",
            gridcolor="#1e2d4a",
            zerolinecolor="#1e2d4a",
        ),
        yaxis=dict(
            title="Composite Risk Score",
            range=[0, 10.5],
            gridcolor="#1e2d4a",
            zerolinecolor="#1e2d4a",
        ),
        hovermode="x unified",
    )
    return fig


# ─────────────────────────────────────────────────────────────
# Patient Detail Panel
# ─────────────────────────────────────────────────────────────

def render_patient_detail(patient: dict):
    """Render expanded patient detail in right panel."""
    v    = patient.get("vitals", {})
    risk = patient.get("current_risk", 0)
    esi  = patient.get("esi_level", 3)

    risk_color = risk_to_color(risk)
    esi_color  = esi_to_color(esi)

    st.markdown(f"""
    <div style="border-bottom:1px solid #1e2d4a; padding-bottom:1rem; margin-bottom:1rem;">
      <div style="display:flex; align-items:center; gap:12px;">
        <div class="esi-badge" style="background:{esi_color}; width:44px; height:44px; font-size:1.3rem;">{esi}</div>
        <div>
          <div style="font-size:1.4rem; font-weight:800; color:#f1f5f9;">{patient.get('name')}</div>
          <div style="color:#64748b; font-size:0.85rem;">
            {patient.get('age')}y {patient.get('sex')} ·
            {patient.get('symptom_category')} ·
            ⏱ {int(patient.get('minutes_in_ed',0))}min in ED
          </div>
        </div>
        <div style="margin-left:auto; text-align:right;">
          <div style="font-size:2.4rem; font-weight:900; color:{risk_color}; line-height:1;">{risk:.1f}</div>
          <div style="font-size:0.8rem; color:{risk_color}; font-weight:700;">{risk_to_label(risk)}</div>
        </div>
      </div>
      <div style="margin-top:0.75rem; font-style:italic; color:#94a3b8;">
        "{patient.get('chief_complaint')}"
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Vitals grid ─────────────────────────────────────
    st.markdown('<div class="section-header">Vital Signs</div>', unsafe_allow_html=True)
    trend = patient.get("vitals_trend", {})

    def vital_display(key, label, val, unit, normal_range=None):
        t     = trend.get(key, {})
        arrow = t.get("trend", "→")
        dire  = t.get("direction", "stable")
        color = "#ef4444" if dire=="worsening" else "#22c55e" if dire=="improving" else "#94a3b8"
        delta = t.get("delta", 0)
        delta_str = f"{delta:+.1f}" if abs(delta) >= 0.1 else ""
        return f"""
        <div style="background:#0f1629; border:1px solid #1e2d4a; border-radius:10px;
                    padding:0.75rem; text-align:center;">
          <div style="font-size:0.72rem; color:#64748b; font-weight:600; text-transform:uppercase;">{label}</div>
          <div style="font-size:1.3rem; font-weight:700; color:{color};">{val}<span style="font-size:0.75rem; color:#64748b;">{unit}</span></div>
          <div style="font-size:0.75rem; color:{color};">{arrow} {delta_str}</div>
        </div>"""

    cols = st.columns(4)
    vitals_display = [
        ("heart_rate",       "Heart Rate",   v.get("heart_rate","—"),         " bpm"),
        ("bp_systolic",      "Blood Press",  f"{v.get('bp_systolic','—')}/{v.get('bp_diastolic','—')}", " mmHg"),
        ("spo2",             "SpO₂",         v.get("spo2","—"),                "%"),
        ("respiratory_rate", "Resp Rate",    v.get("respiratory_rate","—"),    "/min"),
        ("temperature",      "Temperature",  v.get("temperature","—"),         "°F"),
        ("gcs",              "GCS",          v.get("gcs","—"),                 "/15"),
        ("pain_score",       "Pain Score",   v.get("pain_score","—"),          "/10"),
        ("vitals_score",     "MEWS Score",   f"{patient.get('vitals_score',0):.1f}", "/10"),
    ]
    for i, (key, label, val, unit) in enumerate(vitals_display):
        with cols[i % 4]:
            st.markdown(vital_display(key, label, val, unit), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Score breakdown ──────────────────────────────────
    with st.expander("📊 Risk Score Breakdown", expanded=False):
        st.code(patient.get("score_breakdown", "Run rescoring to see breakdown..."), language=None)

    # ── ESI escalation notice ────────────────────────────
    if patient.get("esi_upgraded"):
        st.error(f"⬆️ **ESI Escalated**: {patient.get('esi_upgrade_reason', '')}")

    # ── Alerts ──────────────────────────────────────────
    alerts = [a for a in patient.get("alerts", []) if not a.get("acknowledged")]
    if alerts:
        for alert in alerts[-3:]:
            st.markdown(f"""
            <div class="alert-banner">
              <div style="font-weight:700; color:#fca5a5; margin-bottom:4px;">
                🚨 {alert.get('severity','HIGH')} ALERT — {alert.get('timestamp','')[:19]}
              </div>
              <div style="font-size:0.85rem; color:#fecaca;">{alert.get('alert_text','')}</div>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        # ── Logo / Title ─────────────────────────────────
        st.markdown("""
        <div style="text-align:center; padding:1rem 0 1.5rem;">
          <div style="font-size:2.2rem;">🏥</div>
          <div style="font-size:1.4rem; font-weight:800; background:linear-gradient(135deg,#60a5fa,#a78bfa);
                      -webkit-background-clip:text; -webkit-text-fill-color:transparent;">TriageAI</div>
          <div style="font-size:0.72rem; color:#475569; letter-spacing:0.1em; text-transform:uppercase;">
            Intelligent ED Dynamic Triage
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Alert summary badge ───────────────────────────
        patients = st.session_state.patients
        summary  = get_alert_summary(patients)
        active   = summary["critical"] + summary["high"]

        if active > 0:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(239,68,68,0.2),rgba(220,38,38,0.1));
                        border:1px solid rgba(239,68,68,0.5); border-radius:12px;
                        padding:0.75rem 1rem; margin-bottom:1rem; text-align:center;">
              <div style="font-size:1.6rem; font-weight:800; color:#ef4444;">{active}</div>
              <div style="font-size:0.78rem; color:#fca5a5; font-weight:600;">ACTIVE ALERT{"S" if active>1 else ""}</div>
              <div style="font-size:0.7rem; color:#64748b;">{summary['critical']} Critical · {summary['high']} High</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3);
                        border-radius:12px; padding:0.6rem 1rem; margin-bottom:1rem; text-align:center;">
              <div style="color:#22c55e; font-size:0.85rem; font-weight:600;">✅ All Clear</div>
            </div>
            """, unsafe_allow_html=True)

        # ── Model status ──────────────────────────────────
        model_ok = st.session_state.model_loaded
        ml_badge = ("🤖 ML + SHAP Active" if model_ok else "📐 Rule-Based Mode")
        ml_color = "#22c55e" if model_ok else "#f59e0b"
        st.markdown(f'<div style="font-size:0.75rem; color:{ml_color}; text-align:center; margin-bottom:1rem;">{ml_badge}</div>', unsafe_allow_html=True)

        st.divider()

        # ── Active Alerts list ────────────────────────────
        st.markdown('<div class="section-header">🚨 Active Alerts</div>', unsafe_allow_html=True)
        active_alerts = get_active_alerts(patients)

        if not active_alerts:
            st.markdown('<p style="color:#475569; font-size:0.82rem;">No active alerts.</p>', unsafe_allow_html=True)
        else:
            for _ai, alert in enumerate(active_alerts[:8]):
                alerted_patient = next((p for p in patients if p.get("patient_id") == alert.get("patient_id")), None)
                risk_color = risk_to_color(alert.get("risk_score", 0))
                with st.container():
                    st.markdown(f"""
                    <div style="background:#111827; border:1px solid {risk_color}44;
                                border-left:3px solid {risk_color}; border-radius:8px;
                                padding:0.6rem 0.75rem; margin-bottom:0.5rem;">
                      <div style="font-weight:700; font-size:0.85rem; color:#f1f5f9;">
                        {alert.get('patient_name','?')}
                      </div>
                      <div style="font-size:0.72rem; color:#94a3b8;">
                        Risk {alert.get('risk_score',0):.1f} · {int(alert.get('minutes_in_ed',0))}min waiting
                      </div>
                      <div style="font-size:0.7rem; color:{risk_color}; margin-top:2px;">
                        {alert.get('alert_text','')[:60]}…
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    col_a, col_b = st.columns([2, 1])
                    with col_a:
                        if alerted_patient and st.button("View", key=f"sb_view_{_ai}_{alert['alert_id'][-8:]}", use_container_width=True):
                            st.session_state.selected_patient_id = alert["patient_id"]
                    with col_b:
                        if st.button("Ack", key=f"sb_ack_{_ai}_{alert['alert_id'][-8:]}", use_container_width=True):
                            st.session_state.patients = acknowledge_alert(patients, alert["alert_id"])
                            st.rerun()

        st.divider()

        # ── Real-time mode toggle ─────────────────────────
        st.markdown('<div class="section-header">⚙️ Controls</div>', unsafe_allow_html=True)

        if AUTOREFRESH_AVAILABLE:
            rt = st.toggle("Real-Time Auto-Refresh (60s)", value=st.session_state.real_time_mode, key="rt_toggle")
            if rt != st.session_state.real_time_mode:
                st.session_state.real_time_mode = rt

        if st.button("🔄 Reset Demo", use_container_width=True):
            for key in ["patients", "all_alerts", "selected_patient_id", "simulation_run",
                        "simulation_snapshots", "whatif_mode", "whatif_injected",
                        "real_time_elapsed", "show_shap"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # ── Stats footer ──────────────────────────────────
        st.divider()
        total_pts = len([p for p in patients if not p.get("discharged")])
        esi12 = len([p for p in patients if p.get("esi_level", 5) <= 2 and not p.get("discharged")])
        avg_wait = np.mean([p.get("minutes_in_ed", 0) for p in patients]) if patients else 0

        st.markdown(f"""
        <div style="font-size:0.75rem; color:#475569; line-height:1.8;">
          👥 Patients in queue: <b style="color:#94a3b8;">{total_pts}</b><br>
          🔴 ESI-1/2 (critical): <b style="color:#ef4444;">{esi12}</b><br>
          ⏱ Avg wait: <b style="color:#94a3b8;">{avg_wait:.0f} min</b><br>
          🕐 {datetime.now().strftime('%H:%M:%S')}
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Dashboard Header
# ─────────────────────────────────────────────────────────────

def render_header():
    patients = st.session_state.patients
    active   = len([p for p in patients if p.get("alert_fired") and not p.get("alert_acknowledged")])
    esi1     = len([p for p in patients if p.get("esi_level") == 1])
    esi2     = len([p for p in patients if p.get("esi_level") == 2])
    total    = len(patients)

    st.markdown("""
    <div style="display:flex; align-items:center; gap:12px; margin-bottom:1.5rem;">
      <span style="font-size:1.8rem;">🏥</span>
      <div>
        <h1 style="margin:0; font-size:1.6rem; font-weight:800;
                   background:linear-gradient(135deg,#60a5fa,#a78bfa);
                   -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
          Emergency Department Triage Dashboard
        </h1>
        <p style="margin:0; font-size:0.82rem; color:#475569;">
          AI-powered continuous patient re-evaluation · Real-time deterioration detection
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Patients", total)
    with c2:
        st.metric("ESI-1 (Immediate)", esi1, delta=None)
    with c3:
        st.metric("ESI-2 (Emergent)", esi2, delta=None)
    with c4:
        st.metric("🚨 Active Alerts", active, delta=None)
    with c5:
        sim_status = "✅ Simulated" if st.session_state.simulation_run else "⏸ Live"
        st.metric("Mode", sim_status)


# ─────────────────────────────────────────────────────────────
# Demo Controls Strip
# ─────────────────────────────────────────────────────────────

def render_demo_controls():
    st.markdown("---")
    st.markdown('<div style="font-size:0.85rem; font-weight:700; color:#60a5fa; margin-bottom:0.5rem;">🎮 DEMO CONTROLS</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("⏩ Simulate 90 Minutes", use_container_width=True, type="primary"):
            with st.spinner("Running 90-minute simulation…"):
                updated, alerts, snapshots = simulate_time_jump(
                    st.session_state.patients,
                    total_minutes=90,
                    step_minutes=5,
                    use_ml=st.session_state.model_loaded,
                )
                st.session_state.patients            = updated
                st.session_state.all_alerts.extend(alerts)
                st.session_state.simulation_run      = True
                st.session_state.simulation_snapshots = snapshots
            alert_count = len(alerts)
            if alert_count:
                st.success(f"Simulation complete — {alert_count} alert(s) fired! 🚨")
            else:
                st.info("Simulation complete — no threshold breaches.")
            st.rerun()

    with col2:
        if st.button("💉 What-If: Critical Trauma", use_container_width=True):
            if not st.session_state.whatif_injected:
                trauma = generate_critical_trauma_patient()
                st.session_state.patients = inject_patient(st.session_state.patients, trauma)
                st.session_state.whatif_injected = True
                st.session_state.whatif_mode = True
                st.success("Marcus Johnson (ESI-1 GSW) admitted — queue reordered!")
                st.rerun()
            else:
                st.warning("Marcus Johnson already in queue.")

    with col3:
        step_mins = st.selectbox("Manual step →", [1, 5, 10, 15, 30], index=1, label_visibility="collapsed")
        if st.button(f"➕ Advance {step_mins}min", use_container_width=True):
            updated, alerts = rescore_all_patients(
                st.session_state.patients,
                elapsed_minutes=float(step_mins),
                use_ml=st.session_state.model_loaded,
            )
            st.session_state.patients = updated
            st.session_state.all_alerts.extend(alerts)
            if alerts:
                st.warning(f"{len(alerts)} new alert(s)!")
            st.rerun()

    with col4:
        selected = st.session_state.selected_patient_id
        sel_patient = next((p for p in st.session_state.patients if p.get("patient_id") == selected), None)
        if sel_patient and st.button("🔍 Explain Risk (SHAP)", use_container_width=True):
            st.session_state.show_shap = not st.session_state.show_shap
        elif not sel_patient:
            st.markdown('<div style="font-size:0.78rem; color:#475569; padding-top:0.3rem;">← Select a patient card to explain</div>', unsafe_allow_html=True)

    st.markdown("---")


# ─────────────────────────────────────────────────────────────
# Main Patient Queue
# ─────────────────────────────────────────────────────────────

def render_patient_queue():
    patients = st.session_state.patients
    selected_id = st.session_state.selected_patient_id

    left, right = st.columns([1.0, 1.1], gap="large")

    # ── LEFT: Patient cards ────────────────────────────────────
    with left:
        st.markdown('<div class="section-header">Patient Queue (Priority Order)</div>', unsafe_allow_html=True)

        for p in patients:
            if p.get("discharged"):
                continue
            pid       = p.get("patient_id")
            is_sel    = pid == selected_id
            card_html = render_patient_card(p, selected=is_sel)
            st.markdown(card_html, unsafe_allow_html=True)

            if st.button(
                "📋 View Details" if not is_sel else "✓ Selected",
                key=f"card_btn_{pid}",
                use_container_width=True,
            ):
                if is_sel:
                    st.session_state.selected_patient_id = None
                    st.session_state.show_shap           = False
                else:
                    st.session_state.selected_patient_id = pid
                    st.session_state.show_shap           = False
                st.rerun()

    # ── RIGHT: Detail panel ────────────────────────────────────
    with right:
        sel_patient = next((p for p in patients if p.get("patient_id") == selected_id), None)

        if sel_patient:
            # ── Patient detail ──────────────────────────────
            st.markdown('<div class="section-header">Patient Detail</div>', unsafe_allow_html=True)
            render_patient_detail(sel_patient)

            # ── SHAP waterfall ──────────────────────────────
            if st.session_state.show_shap:
                st.markdown('<div class="section-header">🧠 AI Explainability — Why is this risk score?</div>', unsafe_allow_html=True)
                shap_fig = render_shap_chart(sel_patient)
                st.plotly_chart(shap_fig, use_container_width=True, config={"displayModeBar": False})

                is_fallback = not st.session_state.model_loaded
                if is_fallback:
                    st.caption("ℹ️ Showing rule-based explanation (ML model not loaded). Run `python -m model.train_model` for full SHAP.")
            else:
                # ── Risk curve for selected patient ──────────
                st.markdown('<div class="section-header">📈 Risk Curve</div>', unsafe_allow_html=True)
                if len(sel_patient.get("risk_history", [])) >= 2:
                    single_curve = render_risk_curves([sel_patient], highlight_id=selected_id)
                    st.plotly_chart(single_curve, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.info("Run a simulation to see the risk curve evolve over time.")

                if st.button("🧠 Show SHAP Explanation", use_container_width=True):
                    st.session_state.show_shap = True
                    st.rerun()

        else:
            # ── No selection: show all-patient risk curves ──
            st.markdown('<div class="section-header">📈 All Patient Risk Curves</div>', unsafe_allow_html=True)

            if any(len(p.get("risk_history", [])) >= 2 for p in patients):
                multi_fig = render_risk_curves(patients)
                st.plotly_chart(multi_fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown("""
                <div style="background:#111827; border:1px solid #1e2d4a; border-radius:12px;
                            padding:2rem; text-align:center; color:#475569;">
                  <div style="font-size:2rem; margin-bottom:0.5rem;">📊</div>
                  <div style="font-weight:600;">Run a simulation to see risk curves</div>
                  <div style="font-size:0.82rem; margin-top:0.5rem;">
                    Click "⏩ Simulate 90 Minutes" to watch James Wilson's risk escalate
                  </div>
                </div>
                """, unsafe_allow_html=True)

            # ── What-If highlight ─────────────────────────────────
            if st.session_state.whatif_mode:
                st.markdown("""
                <div style="background:rgba(124,58,237,0.1); border:1px solid rgba(124,58,237,0.4);
                            border-radius:12px; padding:1rem; margin-top:1rem;">
                  <div style="font-weight:700; color:#a78bfa; margin-bottom:4px;">
                    💉 What-If Mode Active
                  </div>
                  <div style="font-size:0.82rem; color:#c4b5fd;">
                    Marcus Johnson (ESI-1, GSW) has been admitted. The queue has been
                    reordered by AI priority. His risk score dominates the critical zone.
                  </div>
                </div>
                """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Simulation Results Tab
# ─────────────────────────────────────────────────────────────

def render_simulation_tab():
    st.markdown('<div class="section-header">🎬 Simulation Time-Lapse Results</div>', unsafe_allow_html=True)

    snapshots = st.session_state.simulation_snapshots
    patients  = st.session_state.patients

    if not snapshots:
        st.info("Run '⏩ Simulate 90 Minutes' first to see the time-lapse.")
        return

    # Summary stats
    alerts_during = st.session_state.all_alerts
    james = next((p for p in patients if "James Wilson" in p.get("name", "")), None)

    cols = st.columns(4)
    with cols[0]:
        st.metric("Alerts Fired", len(alerts_during))
    with cols[1]:
        escalated = [p for p in patients if p.get("esi_upgraded")]
        st.metric("ESI Escalations", len(escalated))
    with cols[2]:
        if james:
            st.metric("James Wilson Risk", f"{james.get('current_risk',0):.1f}/10",
                      delta=f"+{james.get('current_risk',0) - 6.92:.1f}")
    with cols[3]:
        high_risk = len([p for p in patients if p.get("current_risk", 0) >= ALERT_THRESHOLD])
        st.metric("Currently High Risk", high_risk)

    # ── Multi-patient risk curves ──────────────────────
    st.markdown("#### Risk Trajectory: All Patients (90 min simulation)")
    multi_fig = render_risk_curves(patients)
    st.plotly_chart(multi_fig, use_container_width=True)

    # ── Alert timeline ─────────────────────────────────
    if alerts_during:
        st.markdown("#### Alert Timeline")
        alert_df = pd.DataFrame([{
            "Patient":    a.get("patient_name"),
            "Time (min)": int(a.get("minutes_in_ed", 0)),
            "Risk Score": a.get("risk_score", 0),
            "Severity":   a.get("severity"),
            "Reason":     a.get("alert_text", "")[:80],
        } for a in alerts_during]).sort_values("Time (min)")

        st.dataframe(
            alert_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Risk Score": st.column_config.ProgressColumn("Risk Score", min_value=0, max_value=10),
            }
        )

    # ── ESI escalation highlight ───────────────────────
    escalated = [p for p in patients if p.get("esi_upgraded")]
    if escalated:
        st.markdown("#### ESI Escalations (AI detected patients missed by intake triage)")
        for p in escalated:
            orig_esi = (p["esi_level"] + 1)  # current ESI was upgraded, reconstruct original
            st.markdown(f"""
            <div style="background:#7c3aed22; border:1px solid #7c3aed55; border-radius:10px;
                        padding:0.75rem 1rem; margin-bottom:0.5rem;">
              <b style="color:#a78bfa;">{p['name']}</b> —
              <span style="color:#94a3b8;">
                ESI upgraded after {int(p.get('minutes_in_ed',0))}min waiting
              </span><br>
              <span style="font-size:0.82rem; color:#c4b5fd;">{p.get('esi_upgrade_reason','')}</span>
            </div>
            """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Real-Time Mode
# ─────────────────────────────────────────────────────────────

def handle_real_time_refresh():
    """Called when auto-refresh fires. Advances all patients by elapsed time."""
    if AUTOREFRESH_AVAILABLE and st.session_state.real_time_mode:
        st_autorefresh(interval=60_000, key="realtime_refresh")

        now = time.time()
        last = st.session_state.last_rescore_time
        elapsed_real_seconds = now - last
        elapsed_sim_minutes  = elapsed_real_seconds / 60.0

        if elapsed_sim_minutes >= 1.0:
            updated, alerts = rescore_all_patients(
                st.session_state.patients,
                elapsed_minutes=elapsed_sim_minutes,
                use_ml=st.session_state.model_loaded,
            )
            st.session_state.patients            = updated
            st.session_state.all_alerts.extend(alerts)
            st.session_state.last_rescore_time   = now
            st.session_state.real_time_elapsed  += elapsed_sim_minutes
            st.session_state.tick_count         += 1


# ─────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────

def main():
    init_session()
    handle_real_time_refresh()
    render_sidebar()
    render_header()
    render_demo_controls()

    # ── Main content tabs ────────────────────────────────
    tab1, tab2 = st.tabs(["🏥 Live Patient Queue", "🎬 Simulation Results"])

    with tab1:
        render_patient_queue()

    with tab2:
        render_simulation_tab()


if __name__ == "__main__":
    main()
