/**
 * PatientCard.jsx — Individual patient row card in the queue.
 * Shows: risk score, alert level, vitals, SHAP top factors, trending arrows.
 */
import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Heart, Thermometer, Wind, Activity } from 'lucide-react'
import ShapChart from './ShapChart'

// ── Alert colour palette ─────────────────────────────────────
const COLORS = {
  CRITICAL: { bg: 'rgba(230,57,70,0.12)',  border: '#E63946', text: '#ff6b6b',  badge: '#E63946' },
  WARNING:  { bg: 'rgba(255,140,0,0.10)',  border: '#FF8C00', text: '#FF8C00',  badge: '#FF8C00' },
  WATCH:    { bg: 'rgba(255,215,0,0.08)',  border: '#FFD700', text: '#FFD700',  badge: '#FFD700' },
  STABLE:   { bg: 'rgba(76,175,80,0.08)', border: '#4CAF50', text: '#4CAF50',  badge: '#4CAF50' },
}

const ESI_LABELS = { 1: 'IMMEDIATE', 2: 'EMERGENT', 3: 'URGENT', 4: 'LESS URGENT', 5: 'NON-URGENT' }

function RiskBar({ value }) {
  const pct = Math.min(Math.round((value / 10) * 100), 100)
  const color = value >= 7.5 ? '#E63946' : value >= 5.5 ? '#FF8C00' : value >= 3.5 ? '#FFD700' : '#4CAF50'
  return (
    <div style={{ flex: 1, height: 6, background: '#30363D', borderRadius: 3, overflow: 'hidden' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        style={{ height: '100%', background: color, borderRadius: 3 }}
      />
    </div>
  )
}

function VitalChip({ label, value, warn }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      background: warn ? 'rgba(230,57,70,0.12)' : 'rgba(48,54,61,0.5)',
      border: `1px solid ${warn ? '#E63946' : '#30363D'}`,
      borderRadius: 8, padding: '0.3rem 0.55rem', minWidth: 52,
    }}>
      <span style={{ color: warn ? '#ff6b6b' : '#E6EDF3', fontWeight: 700, fontSize: '0.82rem' }}>{value}</span>
      <span style={{ color: '#8B949E', fontSize: '0.62rem', marginTop: 1 }}>{label}</span>
    </div>
  )
}

export default function PatientCard({ patient, rank }) {
  const [expanded, setExpanded] = useState(false)
  const alert = patient.alert_level || 'STABLE'
  const colors = COLORS[alert] || COLORS.STABLE
  const risk = patient.risk_probability * 10  // convert 0-1 to 0-10 display

  const v = patient  // vitals are top-level in API response
  const hrWarn  = v.hr > 120 || v.hr < 50
  const bpWarn  = v.sbp < 90 || v.sbp > 180
  const spo2Warn = v.spo2 < 94
  const tempWarn = v.temp > 101.5
  const rrWarn  = v.rr > 25 || v.rr < 10

  const esiColor = v.acuity_changed ? '#FF8C00' : '#8B949E'

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.3 }}
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 12,
        marginBottom: '0.65rem',
        overflow: 'hidden',
        cursor: 'pointer',
      }}
      onClick={() => setExpanded(e => !e)}
    >
      {/* ── Main Row ─────────────────────────────────────────── */}
      <div style={{ padding: '0.8rem 1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        {/* Rank */}
        <div style={{
          width: 28, height: 28, borderRadius: 14,
          background: rank <= 2 ? colors.badge : '#30363D',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '0.72rem', color: rank <= 2 ? '#fff' : '#8B949E', fontWeight: 700,
          flexShrink: 0,
        }}>
          {rank}
        </div>

        {/* Name + info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <span style={{ color: '#E6EDF3', fontWeight: 600, fontSize: '0.93rem', whiteSpace: 'nowrap' }}>
              {patient.name}
            </span>
            <span style={{ color: '#8B949E', fontSize: '0.75rem' }}>
              {patient.age}y {patient.sex}
            </span>
            <span style={{
              fontSize: '0.68rem', padding: '0.1rem 0.45rem', borderRadius: 10,
              border: `1px solid ${esiColor}`, color: esiColor, fontWeight: 700,
            }}>
              ESI-{v.esi_level}{v.acuity_changed && ' ↑'}
            </span>
            {patient.has_comorbidity && (
              <span style={{
                fontSize: '0.65rem', padding: '0.1rem 0.4rem', borderRadius: 10,
                background: 'rgba(255,140,0,0.12)', border: '1px solid #FF8C00',
                color: '#FF8C00',
              }}>
                comorbid
              </span>
            )}
          </div>
          <div style={{ color: '#8B949E', fontSize: '0.73rem', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {patient.chief_complaint}
          </div>
        </div>

        {/* Risk score */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.15rem' }}>
            <span style={{ color: colors.text, fontWeight: 800, fontSize: '1.3rem', lineHeight: 1 }}>
              {(patient.risk_probability * 10).toFixed(1)}
            </span>
            <span style={{ color: '#8B949E', fontSize: '0.65rem' }}>/10</span>
          </div>
          <span style={{
            fontSize: '0.65rem', padding: '0.1rem 0.45rem', borderRadius: 10,
            background: colors.badge + '33', border: `1px solid ${colors.badge}`,
            color: colors.badge, fontWeight: 700,
          }}>
            {alert}
          </span>
        </div>

        {/* Chevron */}
        <div style={{ color: '#8B949E', flexShrink: 0 }}>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {/* Risk bar */}
      <div style={{ padding: '0 1rem 0.7rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <RiskBar value={patient.risk_probability * 10} />
        <span style={{ color: '#8B949E', fontSize: '0.68rem', flexShrink: 0 }}>
          {patient.wait_time_min}m wait
        </span>
      </div>

      {/* ── Expanded Detail ───────────────────────────────────── */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{
              borderTop: '1px solid #30363D',
              padding: '0.8rem 1rem',
              display: 'flex', flexDirection: 'column', gap: '0.8rem',
            }}>
              {/* Vitals grid */}
              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                <VitalChip label="HR"    value={v.hr}        warn={hrWarn} />
                <VitalChip label="BP"    value={`${v.sbp}/${v.dbp}`} warn={bpWarn} />
                <VitalChip label="SpO₂"  value={`${v.spo2}%`}  warn={spo2Warn} />
                <VitalChip label="RR"    value={v.rr}        warn={rrWarn} />
                <VitalChip label="Temp"  value={`${v.temp}°`} warn={tempWarn} />
                <VitalChip label="GCS"   value={v.gcs}       warn={v.gcs < 14} />
              </div>

              {/* SHAP / Explanation */}
              {patient.shap_labels?.length > 0 ? (
                <ShapChart labels={patient.shap_labels} values={patient.shap_values} />
              ) : patient.explanation?.length > 0 ? (
                <div>
                  <div style={{ color: '#8B949E', fontSize: '0.72rem', marginBottom: 4 }}>Key risk factors:</div>
                  {patient.explanation.slice(0, 4).map((txt, i) => (
                    <div key={i} style={{ color: '#E6EDF3', fontSize: '0.77rem', marginBottom: 2 }}>
                      • {txt}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
