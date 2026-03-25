/**
 * Header.jsx — TriageAI dashboard top navigation bar.
 * Shows: logo, patient count, sim offset badge, alert dots.
 * Uses lucide-react icons, Framer Motion for entrance.
 */
import React from 'react'
import { motion } from 'framer-motion'
import { Activity, Clock, Users, AlertTriangle } from 'lucide-react'

export default function Header({ patientCount = 0, simOffset = 0, alertCount = 0 }) {
  const hours = Math.floor(simOffset / 60)
  const mins  = Math.round(simOffset % 60)
  const timeLabel = simOffset > 0
    ? (hours > 0 ? `+${hours}h ${mins}m` : `+${mins}m`)
    : 'Live'

  return (
    <motion.header
      initial={{ y: -64, opacity: 0 }}
      animate={{ y: 0,  opacity: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      style={{
        position: 'fixed',
        top: 0, left: 0, right: 0,
        zIndex: 100,
        height: 64,
        background: 'rgba(13,17,23,0.92)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid #30363D',
        display: 'flex',
        alignItems: 'center',
        padding: '0 1.5rem',
        gap: '1.25rem',
      }}
    >
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flex: '0 0 auto' }}>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: 'linear-gradient(135deg,#E63946 0%,#c1121f 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Activity size={20} color="#fff" />
        </div>
        <span style={{
          fontFamily: '"Inter",sans-serif',
          fontWeight: 700, fontSize: '1.05rem',
          color: '#E6EDF3', letterSpacing: '-0.01em',
        }}>
          Triage<span style={{ color: '#E63946' }}>AI</span>
        </span>
      </div>

      <div style={{ flex: 1 }} />

      {/* Sim offset badge */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        background: simOffset > 0 ? 'rgba(255,140,0,0.15)' : 'rgba(76,175,80,0.12)',
        border: `1px solid ${simOffset > 0 ? '#FF8C00' : '#4CAF50'}`,
        borderRadius: 20, padding: '0.3rem 0.75rem',
        color: simOffset > 0 ? '#FF8C00' : '#4CAF50',
        fontSize: '0.78rem', fontWeight: 600,
      }}>
        <Clock size={13} />
        <span>{timeLabel}</span>
      </div>

      {/* Patient count */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.4rem',
        color: '#8B949E', fontSize: '0.82rem',
      }}>
        <Users size={14} />
        <span>{patientCount} patients</span>
      </div>

      {/* Alert badge */}
      {alertCount > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          background: 'rgba(230,57,70,0.15)',
          border: '1px solid #E63946',
          borderRadius: 20, padding: '0.3rem 0.75rem',
          color: '#E63946', fontSize: '0.78rem', fontWeight: 600,
        }}>
          <AlertTriangle size={13} />
          <span>{alertCount} alert{alertCount > 1 ? 's' : ''}</span>
        </div>
      )}

      {/* Model indicator */}
      <div style={{
        fontSize: '0.72rem', color: '#8B949E',
        background: '#161B22', border: '1px solid #30363D',
        borderRadius: 6, padding: '0.25rem 0.6rem',
      }}>
        GBM + SHAP
      </div>
    </motion.header>
  )
}
