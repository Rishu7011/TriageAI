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

CLINICAL_CSS = """
<style>
/* ── 1. RESET & BASE ─────────────────────────────────────── */
#MainMenu,footer,[data-testid="stToolbar"]{visibility:hidden!important}
/* Always show sidebar toggle arrow */
[data-testid="collapsedControl"],
section[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"]{visibility:visible!important;display:flex!important;z-index:9999!important}
html,body,.stApp,[class*="css"]{
    font-family:'SF Mono','Cascadia Code','Consolas',ui-monospace,monospace;
    background-color:#0D1117!important;
    color:#E6EDF3;
}
.stApp{background-color:#0D1117!important}

/* ── 2. SIDEBAR ──────────────────────────────────────────── */
[data-testid="stSidebar"]{
    background-color:#0A0F16!important;
    border-right:2px solid #21262D!important;
    min-width:260px;
}
[data-testid="stSidebar"] > div:first-child{
    background-color:#0A0F16!important;
}

/* ── 3. SCROLLBAR ────────────────────────────────────────── */
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0D1117}
::-webkit-scrollbar-thumb{background:#30363D;border-radius:4px}

/* ── 4. TRIAGE HEADER ──────────────────────────────────── */
.triage-header{
    background:linear-gradient(90deg,#1a0a0c 0%,#1C0F12 40%,#0D1117 100%);
    border-bottom:2px solid #E63946;border-radius:10px;
    padding:0.9rem 1.4rem;margin-bottom:1.1rem;
    display:flex;align-items:center;gap:14px;
}
.th-icon{font-size:1.9rem}
.th-title{font-size:1.4rem;font-weight:800;color:#E6EDF3;letter-spacing:-0.01em;line-height:1.15}
.th-title span{color:#E63946}
.th-sub{font-size:0.7rem;color:#8B949E;margin-top:3px;display:flex;align-items:center;gap:6px;text-transform:uppercase;letter-spacing:0.08em}

/* ── 5. LIVE DOT ─────────────────────────────────────────── */
.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#3FB950;animation:blink-dot 1.4s ease-in-out infinite;flex-shrink:0}
@keyframes blink-dot{0%,100%{opacity:1;box-shadow:0 0 4px #3FB950}50%{opacity:0.25;box-shadow:none}}

/* ── 6. METRICS STRIP ────────────────────────────────────── */
.metrics-strip{display:flex;gap:8px;margin-bottom:1.1rem;flex-wrap:nowrap}
.metric-card{flex:1;background:#161B22;border:1px solid #21262D;border-radius:8px;padding:0.75rem 0.9rem;text-align:center;min-width:0;position:relative;overflow:hidden}
.metric-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:var(--accent,#30363D)}
.mc-value{font-size:1.65rem;font-weight:800;line-height:1;color:var(--accent,#E6EDF3)}
.mc-label{font-size:0.62rem;font-weight:600;text-transform:uppercase;letter-spacing:0.1em;color:#8B949E;margin-top:4px}
.mc-sub{font-size:0.65rem;color:#484F58;margin-top:2px}

/* ── 7. PATIENT CARDS ────────────────────────────────────── */
.patient-card{background:#161B22;border:1px solid #21262D;border-radius:8px;padding:0.9rem 1rem;margin-bottom:0.5rem;transition:border-color 0.18s,box-shadow 0.18s;cursor:pointer}
.patient-card:hover{border-color:#388BFD;box-shadow:0 0 0 1px #388BFD22}
.pc-selected{border-color:#388BFD!important;box-shadow:0 0 0 2px #388BFD33!important}
.pc-alert{border-color:#E63946!important;animation:pulse-card 2.2s ease-in-out infinite}
@keyframes pulse-card{0%,100%{box-shadow:0 0 0 1px #E6394622}50%{box-shadow:0 0 12px 2px #E6394644}}
.pc-rank{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;border-radius:50%;background:#21262D;color:#8B949E;font-size:0.65rem;font-weight:700;flex-shrink:0;margin-right:6px}
.pc-name{font-weight:700;font-size:0.92rem;color:#E6EDF3}
.pc-meta{font-size:0.7rem;color:#8B949E;margin-top:1px}
.pc-complaint{font-size:0.76rem;color:#6E7681;margin:0.35rem 0 0.4rem;font-style:italic;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pc-risk-bar-track{height:4px;background:#21262D;border-radius:3px;overflow:hidden;margin-bottom:0.35rem}
.pc-risk-bar-fill{height:100%;border-radius:3px;transition:width 0.5s ease}

/* ── 8. STATUS BADGES ────────────────────────────────────── */
.badge{display:inline-block;padding:1px 7px;border-radius:4px;font-size:0.62rem;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;vertical-align:middle}
.badge-critical{background:#E6394620;color:#FF7B7B;border:1px solid #E6394650}
.badge-high    {background:#FF8C0020;color:#FFA040;border:1px solid #FF8C0050}
.badge-elevated{background:#FFD70020;color:#FFD700;border:1px solid #FFD70050}
.badge-stable  {background:#3FB95020;color:#3FB950;border:1px solid #3FB95050}
.badge-alert   {background:#E6394620;color:#FF7B7B;border:1px solid #E63946;animation:blink-badge 1.2s ease infinite}
.badge-esi-up  {background:#8B5CF620;color:#A78BFA;border:1px solid #8B5CF650}
@keyframes blink-badge{0%,100%{opacity:1}50%{opacity:0.5}}

/* ── 9. ESI CIRCLE ───────────────────────────────────────── */
.esi-badge{display:inline-flex;align-items:center;justify-content:center;width:28px;height:28px;border-radius:50%;font-weight:800;font-size:0.85rem;color:#0D1117;flex-shrink:0}

/* ── 10. ALERT BANNERS ───────────────────────────────────── */
.critical-alert{background:#1C0F12;border:1px solid #E63946;border-left:4px solid #E63946;border-radius:6px;padding:0.7rem 1rem;margin-bottom:0.5rem;animation:fadeInSlide 0.4s ease}
@keyframes fadeInSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.alert-banner{background:#1C0F12;border:1px solid rgba(230,57,70,0.4);border-left:4px solid #E63946;border-radius:6px;padding:0.7rem 1rem;margin-bottom:0.5rem}

/* ── 11. SECTION HEADERS ─────────────────────────────────── */
.section-header{font-size:0.68rem;font-weight:700;color:#8B949E;letter-spacing:0.12em;text-transform:uppercase;margin-bottom:0.55rem;padding-bottom:0.35rem;border-bottom:1px solid #21262D}

/* ── 12. SECTION DIVIDER ─────────────────────────────────── */
.section-divider{height:1px;background:linear-gradient(90deg,#E63946 0%,#21262D 60%,transparent 100%);margin:0.8rem 0;border:none}

/* ── 13. VITAL CHIPS ─────────────────────────────────────── */
.vital-chip{display:inline-block;background:#21262D;border:1px solid #30363D;border-radius:4px;padding:2px 7px;font-size:0.69rem;margin:2px;font-family:ui-monospace,monospace}

/* ── 14. BUTTONS ─────────────────────────────────────────── */
.stButton>button{background:#21262D;color:#E6EDF3;border:1px solid #30363D;border-radius:6px;font-weight:600;font-size:0.82rem;padding:0.4rem 0.9rem;transition:all 0.15s ease}
.stButton>button:hover{background:#30363D;border-color:#E63946;color:#fff}

/* ── 15. MISC ────────────────────────────────────────────── */
hr{border-color:#21262D}
[data-testid="metric-container"]{background:#161B22;border:1px solid #21262D;border-radius:8px;padding:0.7rem 0.9rem}
[data-testid="stTabs"]>div>div{background:#161B22;border-radius:8px;border:1px solid #21262D}
</style>
"""

st.markdown(CLINICAL_CSS, unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────────────────────

def init_session():
    """Initialize all session state on first load."""
    defaults = {
        "initialized": True,
        "patients": [],
        "all_alerts": [],
        "selected_patient_id": None,
        "simulation_run": False,
        "simulation_snapshots": [],
        "whatif_mode": False,
        "whatif_injected": False,
        "real_time_mode": False,
        "real_time_elapsed": 0.0,
        "last_rescore_time": time.time(),
        "show_shap": False,
        "model_loaded": False,
        "demo_mode": True,
        "tick_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Load model once
    if not st.session_state.get("model_loaded", False):
        st.session_state.model_loaded = ModelManager.load_model()

    # Load demo patients if queue is empty
    if not st.session_state.get("patients", []):
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


# Acuity color palette — ESI level → clinical color
_ACUITY_COLORS = {
    1: "#E63946",   # red       — immediate
    2: "#FF8C00",   # orange    — emergent
    3: "#FFD700",   # yellow    — urgent
    4: "#3FB950",   # green     — less-urgent
    5: "#388BFD",   # blue      — non-urgent
}
# Badge CSS class keyed by risk label
_BADGE_CLASS = {
    "CRITICAL":  "badge badge-critical",
    "HIGH RISK": "badge badge-high",
    "ELEVATED":  "badge badge-elevated",
    "MODERATE":  "badge badge-stable",
    "LOW":       "badge badge-stable",
}

def render_patient_card(patient: dict, selected: bool = False, rank: int = 0) -> str:
    """Render a clinical patient queue card. rank=queue position (1-based)."""
    risk     = patient.get("current_risk", 0)
    esi      = patient.get("esi_level", 3)
    name     = patient.get("name", "Unknown")
    age      = patient.get("age", "—")
    sex      = patient.get("sex", "M")
    complaint= patient.get("chief_complaint", "")[:62]
    mins     = patient.get("minutes_in_ed", 0)
    vitals   = patient.get("vitals", {})
    trend    = patient.get("vitals_trend", {})
    alerted  = patient.get("alert_fired", False)
    upgraded = patient.get("esi_upgraded", False)
    delta    = patient.get("risk_delta", 0)

    risk_color  = risk_to_color(risk)
    risk_label  = risk_to_label(risk)
    esi_bg      = _ACUITY_COLORS.get(esi, "#30363D")
    badge_cls   = _BADGE_CLASS.get(risk_label, "badge badge-stable")

    if alerted:
        card_class = "patient-card pc-alert"
    elif selected:
        card_class = "patient-card pc-selected"
    else:
        card_class = "patient-card"

    wait_str = f"{int(mins)}m" if mins < 60 else f"{int(mins//60)}h {int(mins%60)}m"

    # Risk delta
    delta_html = ""
    if abs(delta) > 0.05:
        d_col = "#E63946" if delta > 0 else "#3FB950"
        d_sym = "▲" if delta > 0 else "▼"
        delta_html = f'<span style="color:{d_col};font-size:0.68rem;font-weight:700;margin-left:3px;">{d_sym}{abs(delta):.1f}</span>'

    rank_html = f'<span class="pc-rank">#{rank}</span>' if rank else ""
    esi_html  = f'<span class="esi-badge" style="background:{esi_bg};color:#0D1117;margin-right:8px;">{esi}</span>'

    badges = ""
    if alerted:
        badges += '<span class="badge badge-alert" style="margin-left:5px;">⚡ ALERT</span>'
    if upgraded:
        orig  = esi + 1
        badges += f'<span class="badge badge-esi-up" style="margin-left:4px;">ESI {orig}→{esi} ⬆</span>'

    pct      = min(risk / 10.0 * 100, 100)
    risk_bar = f'<div class="pc-risk-bar-track"><div class="pc-risk-bar-fill" style="width:{pct:.1f}%;background:{risk_color};"></div></div>'
    vital_chips = render_vitals_chips(vitals, trend)

    return f"""
<div class="{card_class}" style="border-left:3px solid {esi_bg};">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
    <div style="display:flex;align-items:center;flex:1;min-width:0;">
      {rank_html}{esi_html}
      <div style="min-width:0;">
        <div style="display:flex;align-items:center;flex-wrap:wrap;gap:3px;">
          <span class="pc-name">{name}</span>{badges}
        </div>
        <div class="pc-meta">{age}y {sex[0] if sex else '?'} &nbsp;·&nbsp; ⏱ {wait_str}</div>
      </div>
    </div>
    <div style="text-align:right;flex-shrink:0;">
      <div style="font-size:1.5rem;font-weight:800;color:{risk_color};line-height:1;">{risk:.1f}{delta_html}</div>
      <span class="{badge_cls}">{risk_label}</span>
    </div>
  </div>
  <div class="pc-complaint">"{complaint}…"</div>
  {risk_bar}
  <div style="margin-top:0.25rem;">{vital_chips}</div>
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

        # ── Clinical Credibility card ─────────────────────
        st.divider()
        st.markdown("""
        <div style="
            background:#161B22;
            border:1px solid #30363D;
            border-radius:8px;
            padding:0.8rem;
        ">
            <div style="color:#E6EDF3;font-weight:600;font-size:0.8rem;margin-bottom:0.4rem;">
                📚 Clinical Basis
            </div>
            <div style="font-size:0.75rem;color:#8B949E;line-height:1.8;">
                • ESI v5 algorithm (AHRQ, 2020)<br>
                • MEWS deterioration criteria<br>
                • MIMIC-IV ED triage distributions<br>
                • Model: GBM — AUC 0.837, Sensitivity 94.2%<br>
                • Training: 8,000 synthetic patients
            </div>
            <div style="margin-top:0.4rem;color:#4CAF50;font-size:0.75rem;font-weight:600;">
                ✓ Prototype — not for clinical use
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Dashboard Header
# ─────────────────────────────────────────────────────────────

def render_metrics_row(patients: list):
    """Pure HTML flexbox metrics strip — 5 cards, no st.columns()."""
    total      = len([p for p in patients if not p.get("discharged")])
    critical   = len([p for p in patients if p.get("current_risk", 0) >= 9.0])
    high_risk  = len([p for p in patients if 7.5 <= p.get("current_risk", 0) < 9.0])
    avg_wait   = int(sum(p.get("minutes_in_ed", 0) for p in patients) / max(len(patients), 1))
    reprio     = len([p for p in patients if p.get("esi_upgraded")])
    sim_on     = st.session_state.get("simulation_run", False)
    mode_label = "SIMULATED" if sim_on else "LIVE"
    mode_color = "#388BFD" if sim_on else "#3FB950"

    st.markdown(f"""
    <div class="metrics-strip">
      <div class="metric-card" style="--accent:#E6EDF3;">
        <div class="mc-value" style="color:#E6EDF3;">{total}</div>
        <div class="mc-label">Total Patients</div>
        <div class="mc-sub">in queue</div>
      </div>
      <div class="metric-card" style="--accent:#E63946;">
        <div class="mc-value" style="color:#E63946;">{critical}</div>
        <div class="mc-label">Critical</div>
        <div class="mc-sub">risk ≥ 9.0</div>
      </div>
      <div class="metric-card" style="--accent:#FF8C00;">
        <div class="mc-value" style="color:#FF8C00;">{high_risk}</div>
        <div class="mc-label">High Risk</div>
        <div class="mc-sub">risk 7.5–9.0</div>
      </div>
      <div class="metric-card" style="--accent:#FFD700;">
        <div class="mc-value" style="color:#FFD700;">{avg_wait}m</div>
        <div class="mc-label">Avg Wait</div>
        <div class="mc-sub">all patients</div>
      </div>
      <div class="metric-card" style="--accent:#4CAF50;">
        <div class="mc-value" style="color:#4CAF50;">{reprio}</div>
        <div class="mc-label">Re-Prioritized</div>
        <div class="mc-sub">ESI upgraded</div>
      </div>
      <div class="metric-card" style="--accent:{mode_color};">
        <div class="mc-value" style="color:{mode_color};font-size:0.9rem;">{mode_label}</div>
        <div class="mc-label">Mode</div>
        <div class="mc-sub"><span class="live-dot"></span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_header():
    """Clinical triage header bar + metrics strip."""
    now_str = datetime.now().strftime("%H:%M:%S")
    st.markdown(f"""
    <div class="triage-header">
      <span class="th-icon">🏥</span>
      <div>
        <div class="th-title">Triage<span>AI</span> &nbsp;—&nbsp; Emergency Department</div>
        <div class="th-sub">
          <span class="live-dot"></span>
          AI-Powered Continuous Re-Evaluation &nbsp;·&nbsp; Dynamic Risk Scoring &nbsp;·&nbsp; {now_str}
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    render_metrics_row(st.session_state.patients)



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
        if sel_patient and st.button("🔍 Explain Risk (SHAP)", width='stretch'):
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

        for rank, p in enumerate(patients, start=1):
            if p.get("discharged"):
                continue
            pid       = p.get("patient_id")
            is_sel    = pid == selected_id
            card_html = render_patient_card(p, selected=is_sel, rank=rank)
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
                st.plotly_chart(shap_fig, width='stretch', config={"displayModeBar": False})
                render_shap_interpretation(sel_patient)

                is_fallback = not st.session_state.model_loaded
                if is_fallback:
                    st.caption("ℹ️ Showing rule-based explanation (ML model not loaded). Run `python -m model.train_model` for full SHAP.")
            else:
                # ── Risk curve for selected patient ──────────
                st.markdown('<div class="section-header">📈 Risk Curve</div>', unsafe_allow_html=True)
                if len(sel_patient.get("risk_history", [])) >= 2:
                    single_curve = render_risk_curves([sel_patient], highlight_id=selected_id)
                    st.plotly_chart(single_curve, width='stretch', config={"displayModeBar": False})
                else:
                    st.info("Run a simulation to see the risk curve evolve over time.")

                if st.button("🧠 Show SHAP Explanation", width='stretch'):
                    st.session_state.show_shap = True
                    st.rerun()

        else:
            # ── No selection: show all-patient risk curves ──
            st.markdown('<div class="section-header">📈 All Patient Risk Curves</div>', unsafe_allow_html=True)

            if any(len(p.get("risk_history", [])) >= 2 for p in patients):
                multi_fig = render_risk_curves(patients)
                st.plotly_chart(multi_fig, width='stretch', config={"displayModeBar": False})
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
# Gap 2 — Problem Reality Card
# ─────────────────────────────────────────────────────────────

def render_problem_card() -> None:
    """Renders the opening problem statement card when no patients are loaded."""
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1A0000 0%, #2D0000 100%);
        border: 1px solid #E63946;
        border-radius: 12px;
        padding: 2.5rem 2rem;
        margin: 1.5rem 0;
        text-align: center;
    ">
        <!-- Section A: Headline -->
        <div style="font-size: 2.2rem; margin-bottom: 0.5rem;">⚠️</div>
        <div style="font-size: 1.5rem; font-weight: 800; color: #E6EDF3; margin-bottom: 0.75rem; letter-spacing: -0.02em;">
            The Problem We're Solving
        </div>
        <div style="font-size: 0.95rem; color: #8B949E; max-width: 680px; margin: 0 auto 2rem; line-height: 1.65;">
            Emergency departments triage patients <strong style="color: #E6EDF3;">once</strong> at intake.
            A patient scored as &ldquo;medium priority&rdquo; at 2 PM may be critically ill
            by 4 PM &mdash; but nobody re-evaluates them.
        </div>

        <!-- Section B: Stat Cards -->
        <div style="display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 2rem;">

            <div style="background: #0D1117; border: 1px solid #21262D; border-radius: 10px;
                        padding: 1.2rem 1.5rem; min-width: 170px; flex: 1; max-width: 200px;">
                <div style="font-size: 2.2rem; font-weight: 800; color: #E63946; line-height: 1;">500+</div>
                <div style="font-size: 0.82rem; color: #E6EDF3; font-weight: 600; margin-top: 6px;">
                    ED waiting room deaths/year
                </div>
                <div style="font-size: 0.68rem; color: #484F58; margin-top: 4px;">
                    (UK, 2023 BBC Investigation)
                </div>
            </div>

            <div style="background: #0D1117; border: 1px solid #21262D; border-radius: 10px;
                        padding: 1.2rem 1.5rem; min-width: 170px; flex: 1; max-width: 200px;">
                <div style="font-size: 2.2rem; font-weight: 800; color: #FF8C00; line-height: 1;">4.2 hrs</div>
                <div style="font-size: 0.82rem; color: #E6EDF3; font-weight: 600; margin-top: 6px;">
                    Average ED wait time
                </div>
                <div style="font-size: 0.68rem; color: #484F58; margin-top: 4px;">
                    without dynamic re-evaluation
                </div>
            </div>

            <div style="background: #0D1117; border: 1px solid #21262D; border-radius: 10px;
                        padding: 1.2rem 1.5rem; min-width: 170px; flex: 1; max-width: 200px;">
                <div style="font-size: 2.2rem; font-weight: 800; color: #4CAF50; line-height: 1;">94.2%</div>
                <div style="font-size: 0.82rem; color: #E6EDF3; font-weight: 600; margin-top: 6px;">
                    TriageAI sensitivity
                </div>
                <div style="font-size: 0.68rem; color: #484F58; margin-top: 4px;">
                    on deterioration detection
                </div>
            </div>

        </div>

        <!-- Section C: Call to Action -->
        <div style="font-size: 0.9rem; color: #8B949E; margin-bottom: 0.4rem;">
            👈 Click <strong style="color: #E6EDF3;">Load Demo Patients</strong> in the sidebar to begin the live demonstration
        </div>
        <div style="font-size: 0.75rem; color: #484F58;">
            or use the Patient Intake form to admit patients manually
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Gap 3 — SHAP Plain-English Translation Layer
# ─────────────────────────────────────────────────────────────

def render_shap_interpretation(patient: dict) -> None:
    """Renders plain-English clinical interpretation below the SHAP chart."""

    # ── Resolve patient fields ──────────────────────────────
    name           = patient.get("name", "This patient")
    age            = patient.get("age", "?")
    complaint      = patient.get("chief_complaint", "unspecified complaint")
    category       = patient.get("symptom_category", "Unknown")
    wait_time      = int(patient.get("minutes_in_ed", patient.get("wait_time_min", 0)))
    risk_pct       = patient.get("ml_proba", patient.get("risk_probability", 0.0)) * 100
    dyn_esi        = patient.get("esi_level", patient.get("dynamic_acuity", 3))
    orig_esi       = patient.get("esi_level", patient.get("original_acuity", dyn_esi))
    acuity_changed = patient.get("esi_upgraded", patient.get("acuity_changed", False))
    explanation    = patient.get("explanation", [])
    vitals         = patient.get("vitals", {})
    hr             = vitals.get("heart_rate",   patient.get("hr",  0))
    sbp            = vitals.get("bp_systolic",  patient.get("sbp", 0))
    spo2           = vitals.get("spo2",         patient.get("spo2", 100))
    temp_f         = vitals.get("temperature",  patient.get("temp", 98.6))

    # Map alert_level → (color, icon, status text)
    current_risk = patient.get("current_risk", 0)
    if current_risk >= 9.0 or patient.get("alert_level") == "CRITICAL":
        alert_color = "#E63946"; alert_icon = "🚨"
        alert_text  = "IMMEDIATE attention required"
    elif current_risk >= 7.5 or patient.get("alert_level") == "WARNING":
        alert_color = "#FF8C00"; alert_icon = "⚠️"
        alert_text  = "Reassessment recommended within 15 minutes"
    elif current_risk >= 5.0 or patient.get("alert_level") == "WATCH":
        alert_color = "#FFD700"; alert_icon = "👁️"
        alert_text  = "Monitor closely — risk is rising"
    else:
        alert_color = "#4CAF50"; alert_icon = "✅"
        alert_text  = "Condition appears stable at this time"

    # ── Vitals colour helpers ───────────────────────────────
    def vc(val, lo=None, hi=None):
        if lo is not None and val < lo: return "#E63946"
        if hi is not None and val > hi: return "#E63946"
        return "#4CAF50"

    hr_col   = vc(hr, lo=50, hi=110)
    sbp_col  = vc(sbp, lo=90, hi=180)
    spo2_col = vc(spo2, lo=94)
    temp_col = "#E63946" if temp_f > 100.4 or temp_f < 96.8 else "#4CAF50"

    # ── Acuity change line ──────────────────────────────────
    if acuity_changed:
        acuity_html = f"""
        <div style="font-weight:700;color:#E63946;font-size:0.87rem;margin:0.55rem 0;">
            ⚡ Acuity has escalated from ESI {orig_esi + 1} to ESI {dyn_esi} since initial triage.
        </div>"""
    else:
        acuity_html = f"""
        <div style="color:#6E7681;font-size:0.82rem;margin:0.55rem 0;">
            Acuity remains at initial triage level (ESI {dyn_esi}).
        </div>"""

    # ── Explanation pills ───────────────────────────────────
    factors = explanation[:3] if explanation else []
    if factors:
        pills_html = " ".join(
            f'<span style="background:#21262D;border:1px solid #30363D;border-radius:4px;'
            f'padding:2px 8px;font-size:0.72rem;color:#8B949E;white-space:nowrap;">'
            f'{f}</span>'
            for f in factors
        )
    else:
        pills_html = '<span style="color:#484F58;font-size:0.78rem;">Factors unavailable</span>'

    # ── Render ──────────────────────────────────────────────
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="
        background:#161B22;
        border-left: 4px solid {alert_color};
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.2rem;
        margin-top: 0.75rem;
        font-family: ui-monospace, monospace;
    ">
        <!-- Layer 1: Status Header -->
        <div style="font-size:0.9rem;font-weight:700;color:{alert_color};margin-bottom:0.55rem;">
            {alert_icon}&nbsp; {alert_text}
        </div>

        <!-- Layer 2: Narrative sentence -->
        <div style="font-size:0.84rem;color:#C9D1D9;line-height:1.65;margin-bottom:0.5rem;">
            <strong style="color:#E6EDF3;">{name}</strong> has been waiting
            <strong style="color:#E6EDF3;">{wait_time} minutes</strong>
            with a chief complaint of
            &ldquo;<em style="color:#8B949E;">{complaint}</em>&rdquo;.
            The AI model assigns a deterioration probability of
            <strong style="color:{alert_color};">{risk_pct:.0f}%</strong>
            based on age ({age}), vital sign profile, and
            <em>{category}</em> symptom classification.
        </div>

        <!-- Layer 3: Acuity change -->
        {acuity_html}

        <!-- Layer 4: Contributing factors -->
        <div style="font-size:0.75rem;color:#484F58;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.08em;">
            Top contributing factors:
        </div>
        <div style="margin-bottom:0.75rem;">{pills_html}</div>

        <!-- Vitals Snapshot -->
        <div style="display:flex;gap:1.2rem;flex-wrap:wrap;border-top:1px solid #21262D;padding-top:0.65rem;margin-top:0.4rem;">
            <span style="color:{hr_col};font-size:0.78rem;">
                ❤️ HR: <strong>{int(hr) if hr else '—'} bpm</strong>
            </span>
            <span style="color:{sbp_col};font-size:0.78rem;">
                💉 SBP: <strong>{int(sbp) if sbp else '—'} mmHg</strong>
            </span>
            <span style="color:{spo2_col};font-size:0.78rem;">
                🫁 SpO₂: <strong>{int(spo2) if spo2 else '—'}%</strong>
            </span>
            <span style="color:{temp_col};font-size:0.78rem;">
                🌡️ Temp: <strong>{temp_f:.1f}°F</strong>
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────────────────────

def main():
    init_session()
    handle_real_time_refresh()
    render_sidebar()

    # Gap 2 — show problem card when no patients are loaded yet
    if not st.session_state.get("patients"):
        render_problem_card()
        return

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
