import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, Clock, Activity } from 'lucide-react'

const STATS = [
  { label: 'deaths/yr from triage delays', target: 500, suffix: '+', color: '#E63946' },
  { label: 'avg ER wait time (US)', target: 4.2, suffix: 'hrs', decimals: 1, color: '#FF8C00' },
  { label: 'hospitals with AI re-scoring', target: 0, suffix: '', color: '#FFD700' },
]

function Counter({ target, suffix, decimals = 0, color }) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    let start = 0; const dur = 1600
    const tick = setInterval(() => {
      start += dur / 60
      const progress = Math.min(start / dur, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setVal(+(target * eased).toFixed(decimals))
      if (progress >= 1) clearInterval(tick)
    }, 16)
    return () => clearInterval(tick)
  }, [target, decimals])
  return (
    <span style={{ color, fontWeight: 800, fontSize: '2.8rem', lineHeight: 1 }}>
      {decimals > 0 ? val.toFixed(decimals) : val}{suffix}
    </span>
  )
}

export default function ProblemCard({ onLoadDemo, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      style={{
        minHeight: 'calc(100vh - 64px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '2rem',
      }}
    >
      <div style={{
        maxWidth: 720, width: '100%',
        background: 'linear-gradient(135deg, #1a0a0c 0%, #161B22 60%)',
        border: '1px solid rgba(230,57,70,0.4)',
        borderRadius: 16,
        padding: '2.5rem',
        boxShadow: '0 0 60px rgba(230,57,70,0.15)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <AlertTriangle size={28} color="#E63946" />
          <div>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#E6EDF3' }}>
              The Problem We're Solving
            </div>
            <div style={{ color: '#8B949E', fontSize: '0.85rem', marginTop: 2 }}>
              Emergency departments score patients once — then forget them
            </div>
          </div>
        </div>

        {/* Stats grid */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3,1fr)',
          gap: '1.5rem', marginBottom: '2rem',
        }}>
          {STATS.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 + i * 0.15, duration: 0.4 }}
              style={{
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid #30363D', borderRadius: 12,
                padding: '1.25rem', textAlign: 'center',
              }}
            >
              <Counter target={s.target} suffix={s.suffix} decimals={s.decimals || 0} color={s.color} />
              <div style={{ color: '#8B949E', fontSize: '0.72rem', marginTop: 6 }}>{s.label}</div>
            </motion.div>
          ))}
        </div>

        {/* Narrative */}
        <div style={{
          background: 'rgba(255,255,255,0.03)', border: '1px solid #30363D',
          borderRadius: 12, padding: '1.25rem', marginBottom: '2rem',
          fontSize: '0.9rem', color: '#8B949E', lineHeight: 1.7,
        }}>
          <p style={{ margin: 0 }}>
            A patient arrives, gets triaged, and waits. Over the next 90 minutes, their condition silently
            deteriorates — but the triage tag never changes. TriageAI continuously re-scores every patient
            using machine learning, firing escalation alerts <strong style={{ color: '#E6EDF3' }}>before</strong> the deterioration becomes a crisis.
          </p>
          <div style={{
            marginTop: '1rem', display: 'flex', gap: '1.5rem',
            fontSize: '0.8rem',
          }}>
            {[
              ['📊', 'GBM Model', 'AUC 0.837'],
              ['🧠', 'SHAP Explain', 'per patient'],
              ['⚡', 'Re-scores', 'every 60s'],
            ].map(([icon, label, sub], i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#E6EDF3' }}>
                <span>{icon}</span>
                <span style={{ fontWeight: 600 }}>{label}</span>
                <span style={{ color: '#8B949E' }}>— {sub}</span>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onLoadDemo}
          disabled={loading}
          style={{
            width: '100%', padding: '1rem',
            background: 'linear-gradient(135deg, #E63946, #c1121f)',
            border: 'none', borderRadius: 10,
            color: '#fff', fontSize: '1rem', fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
            fontFamily: 'inherit',
          }}
        >
          {loading ? (
            <><Activity size={18} style={{ animation: 'spin 1s linear infinite' }} /> Loading…</>
          ) : (
            <><Clock size={18} /> Load 10 Demo Patients → Watch James Wilson Escalate</>
          )}
        </motion.button>

        <div style={{ textAlign: 'center', marginTop: '0.75rem', fontSize: '0.72rem', color: '#8B949E' }}>
          ✓ Prototype — not for clinical use &nbsp;|&nbsp; ESI v5 (AHRQ, 2020) &nbsp;|&nbsp; MIMIC-IV distributions
        </div>
      </div>
    </motion.div>
  )
}
