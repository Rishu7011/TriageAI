/**
 * AlertBanner.jsx — Dismissible alert notification strip.
 * Appears at the top of the queue listing when risk thresholds are exceeded.
 */
import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X, Zap } from 'lucide-react'

export default function AlertBanner({ alerts = [], onAcknowledge }) {
  if (!alerts.length) return null

  const topAlert = alerts[0]
  const count = alerts.length

  const bg = topAlert.severity === 'CRITICAL'
    ? 'rgba(230,57,70,0.18)'
    : 'rgba(255,140,0,0.15)'
  const border = topAlert.severity === 'CRITICAL' ? '#E63946' : '#FF8C00'
  const color  = topAlert.severity === 'CRITICAL' ? '#ff6b6b' : '#FF8C00'

  return (
    <AnimatePresence>
      <motion.div
        key={topAlert.alert_id}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        style={{
          background: bg,
          border: `1px solid ${border}`,
          borderRadius: 10,
          padding: '0.65rem 1rem',
          marginBottom: '0.75rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
        }}
      >
        <Zap size={16} color={color} />
        <div style={{ flex: 1 }}>
          <span style={{ color, fontWeight: 700, fontSize: '0.82rem' }}>
            {topAlert.severity}
          </span>
          <span style={{ color: '#E6EDF3', fontSize: '0.82rem', marginLeft: '0.5rem' }}>
            {topAlert.patient_name} — {topAlert.alert_text?.slice(0, 90)}
          </span>
          {count > 1 && (
            <span style={{ color: '#8B949E', fontSize: '0.75rem', marginLeft: '0.5rem' }}>
              (+{count - 1} more)
            </span>
          )}
        </div>
        {onAcknowledge && (
          <button
            onClick={() => onAcknowledge(topAlert.alert_id)}
            style={{
              background: 'none', border: `1px solid ${border}`,
              borderRadius: 6, padding: '0.2rem 0.5rem',
              color, cursor: 'pointer', fontSize: '0.72rem',
              fontWeight: 600,
            }}
          >
            ACK
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
