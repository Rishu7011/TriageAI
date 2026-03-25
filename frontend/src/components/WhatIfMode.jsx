import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const LEVEL_COLOR = { CRITICAL: '#E63946', WARNING: '#FF8C00', WATCH: '#FFD700', STABLE: '#4CAF50' }

function MiniCard({ patient, highlight, index }) {
  const color = LEVEL_COLOR[patient.alert_level] || '#8B949E'
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      style={{
        background: '#0D1117',
        border: `1px solid ${highlight ? color : '#30363D'}`,
        borderLeft: `3px solid ${color}`,
        borderRadius: 8, padding: '0.6rem 0.75rem',
        fontSize: '0.78rem', marginBottom: '0.4rem',
        position: 'relative',
      }}
    >
      {highlight && (
        <span style={{
          position: 'absolute', top: 6, right: 6,
          background: '#E63946', color: '#fff', fontSize: '0.6rem',
          padding: '0.05rem 0.35rem', borderRadius: 4, fontWeight: 700,
        }}>
          CHANGED
        </span>
      )}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <strong style={{ color: '#E6EDF3' }}>{patient.name}</strong>
        <span style={{ color }}>ESI {patient.dynamic_acuity} · {patient.alert_level}</span>
      </div>
      <div style={{ color: '#8B949E' }}>Risk: {(patient.risk_probability * 100).toFixed(0)}% &nbsp;·&nbsp; Wait: {patient.wait_time_min}min</div>
    </motion.div>
  )
}

export default function WhatIfMode({ currentPatients, whatIfPatients, onRunWhatIf, loading }) {
  const [minutes, setMinutes] = useState(60)
  const [ran, setRan] = useState(false)

  const handleRun = async () => {
    await onRunWhatIf(minutes)
    setRan(true)
  }

  // Determine which patients shifted alert level
  const changedIds = new Set(
    whatIfPatients.filter(wp => {
      const cur = currentPatients.find(cp => cp.patient_id === wp.patient_id)
      return cur && cur.alert_level !== wp.alert_level
    }).map(wp => wp.patient_id)
  )

  return (
    <div style={{
      background: '#161B22', border: '1px solid #30363D',
      borderRadius: 12, padding: '1.5rem',
    }}>
      <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: '1rem', color: '#E6EDF3' }}>
        ⚡ What-If Mode — Future Risk Projection
      </div>

      {/* Slider */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ fontSize: '0.8rem', color: '#8B949E', display: 'block', marginBottom: 6 }}>
          What if we wait <strong style={{ color: '#E6EDF3' }}>{minutes} more minutes</strong>?
        </label>
        <input
          type="range" min={0} max={180} step={5} value={minutes}
          onChange={e => setMinutes(Number(e.target.value))}
          style={{ width: '100%', accentColor: '#E63946' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#475569' }}>
          <span>0 min</span><span>90 min</span><span>180 min</span>
        </div>
      </div>

      <button
        onClick={handleRun} disabled={loading}
        style={{
          background: loading ? '#21262D' : 'linear-gradient(135deg,#FF8C00,#d97706)',
          border: 'none', borderRadius: 8, padding: '0.6rem 1.4rem',
          color: '#000', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
          fontSize: '0.85rem', marginBottom: '1.5rem',
        }}
      >
        {loading ? '⏳ Projecting…' : `▶ Project T+${minutes}min`}
      </button>

      {/* Comparison columns */}
      <AnimatePresence>
        {ran && whatIfPatients.length > 0 && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}
          >
            <div>
              <div style={{ fontSize: '0.75rem', color: '#8B949E', fontWeight: 700, marginBottom: '0.6rem', letterSpacing: '0.08em' }}>
                CURRENT QUEUE
              </div>
              {currentPatients.map((p, i) => <MiniCard key={p.patient_id} patient={p} highlight={false} index={i} />)}
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#FF8C00', fontWeight: 700, marginBottom: '0.6rem', letterSpacing: '0.08em' }}>
                AT T+{minutes} MIN
              </div>
              {whatIfPatients.map((p, i) => (
                <MiniCard key={p.patient_id} patient={p} highlight={changedIds.has(p.patient_id)} index={i} />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {ran && changedIds.size > 0 && (
        <div style={{
          background: 'rgba(230,57,70,0.1)', border: '1px solid rgba(230,57,70,0.3)',
          borderRadius: 8, padding: '0.75rem', marginTop: '1rem',
          fontSize: '0.8rem', color: '#fca5a5',
        }}>
          🚨 <strong>{changedIds.size} patient{changedIds.size > 1 ? 's' : ''}</strong> will escalate alert level if left untreated for {minutes} minutes.
        </div>
      )}
    </div>
  )
}
