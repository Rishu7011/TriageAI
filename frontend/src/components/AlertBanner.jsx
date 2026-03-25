import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, XCircle } from 'lucide-react'

const LEVEL_STYLE = {
  CRITICAL: { bg: 'rgba(230,57,70,0.15)',  border: '#E63946', icon: '🚨', color: '#E63946', label: 'CRITICAL' },
  WARNING:  { bg: 'rgba(255,140,0,0.12)',   border: '#FF8C00', icon: '⚠️', color: '#FF8C00', label: 'WARNING'  },
}

export default function AlertBanner({ patients = [] }) {
  const alerts = patients.filter(p =>
    p.alert_level === 'CRITICAL' || p.alert_level === 'WARNING'
  )

  return (
    <AnimatePresence>
      {alerts.map((p) => {
        const s = LEVEL_STYLE[p.alert_level] || LEVEL_STYLE.WARNING
        return (
          <motion.div
            key={p.patient_id}
            initial={{ opacity: 0, y: -48, scaleY: 0.6 }}
            animate={{ opacity: 1, y: 0, scaleY: 1 }}
            exit={{ opacity: 0, y: -24, scaleY: 0.6 }}
            transition={{ type: 'spring', stiffness: 340, damping: 28 }}
            style={{
              background: s.bg, border: `1px solid ${s.border}`,
              borderRadius: 8, padding: '0.6rem 1rem',
              display: 'flex', alignItems: 'center', gap: '0.75rem',
              fontSize: '0.82rem', marginBottom: '0.5rem',
            }}
          >
            <span style={{ fontSize: '1.1rem' }}>{s.icon}</span>
            <strong style={{ color: s.color }}>{s.label}</strong>
            <span style={{ color: '#E6EDF3', fontWeight: 600 }}>{p.name}</span>
            <span style={{ color: '#8B949E' }}>
              Risk {(p.risk_probability * 100).toFixed(0)}% ·
              ESI {p.dynamic_acuity} ·
              Wait {p.wait_time_min}min
            </span>
            {p.explanation?.[0] && (
              <span style={{ color: s.color, marginLeft: 'auto', fontSize: '0.75rem' }}>
                {p.explanation[0]}
              </span>
            )}
            {p.acuity_changed && (
              <span style={{
                background: s.color, color: '#000', borderRadius: 4,
                padding: '0.1rem 0.5rem', fontSize: '0.7rem', fontWeight: 700,
              }}>
                ESI ESCALATED
              </span>
            )}
          </motion.div>
        )
      })}
    </AnimatePresence>
  )
}
