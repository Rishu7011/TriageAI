import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight, Clock, Heart, Activity } from 'lucide-react'
import ShapChart from './ShapChart'

const ACUITY_COLOR = { 1: '#E63946', 2: '#FF8C00', 3: '#FFD700', 4: '#4CAF50', 5: '#388BFD' }
const LEVEL_COLOR  = { CRITICAL: '#E63946', WARNING: '#FF8C00', WATCH: '#FFD700', STABLE: '#4CAF50' }

function RiskBar({ value }) {
  return (
    <div style={{
      height: 6, borderRadius: 3, overflow: 'hidden',
      background: 'rgba(255,255,255,0.08)', width: '100%',
    }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.round(value * 100)}%` }}
        transition={{ duration: 0.8, ease: [0.34, 1.56, 0.64, 1] }}
        style={{
          height: '100%', borderRadius: 3,
          background: value >= 0.7 ? '#E63946' : value >= 0.5 ? '#FF8C00' : value >= 0.3 ? '#FFD700' : '#4CAF50',
        }}
      />
    </div>
  )
}

export default function PatientCard({ patient, index }) {
  const [open, setOpen] = useState(false)
  const acuityColor = ACUITY_COLOR[patient.dynamic_acuity] || '#8B949E'
  const levelColor  = LEVEL_COLOR[patient.alert_level] || '#8B949E'
  const isCritical  = patient.alert_level === 'CRITICAL'

  return (
    <>
      <motion.div
        layout
        layoutId={patient.patient_id}
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 30, scale: 0.95 }}
        transition={{ delay: index * 0.06, duration: 0.35, layout: { duration: 0.4 } }}
        onClick={() => setOpen(true)}
        className={isCritical ? 'pulse-critical' : ''}
        style={{
          background: '#161B22',
          border: `1px solid ${isCritical ? '#E63946' : '#30363D'}`,
          borderLeft: `4px solid ${acuityColor}`,
          borderRadius: 10,
          padding: '0.85rem 1rem',
          cursor: 'pointer',
          position: 'relative',
          overflow: 'hidden',
        }}
        whileHover={{ scale: 1.01, borderColor: levelColor }}
      >
        {/* Rank indicator */}
        <div style={{
          position: 'absolute', top: 8, right: 8,
          background: 'rgba(255,255,255,0.05)', borderRadius: 4,
          padding: '0.1rem 0.4rem', fontSize: '0.68rem', color: '#8B949E',
        }}>
          #{index + 1} <ChevronRight size={10} style={{ display: 'inline' }} />
        </div>

        {/* Top row: name + badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: 6 }}>
          <span style={{
            background: acuityColor, color: '#000',
            borderRadius: 6, padding: '0.1rem 0.5rem',
            fontSize: '0.72rem', fontWeight: 700,
          }}>
            ESI {patient.dynamic_acuity}
          </span>
          <span style={{ fontWeight: 700, fontSize: '0.95rem', color: '#E6EDF3', flex: 1 }}>
            {patient.name}
          </span>
          <span style={{
            background: `${levelColor}22`, color: levelColor,
            border: `1px solid ${levelColor}55`,
            borderRadius: 6, padding: '0.1rem 0.5rem',
            fontSize: '0.7rem', fontWeight: 600,
          }}>
            {patient.alert_level}
          </span>
          {patient.acuity_changed && (
            <span style={{
              background: '#E63946', color: '#fff',
              borderRadius: 6, padding: '0.1rem 0.4rem',
              fontSize: '0.65rem', fontWeight: 700,
            }}>
              ↑ ESCALATED
            </span>
          )}
        </div>

        {/* Middle row: complaint + vitals */}
        <div style={{ fontSize: '0.78rem', color: '#8B949E', marginBottom: 8, display: 'flex', gap: '1rem' }}>
          <span style={{ flex: 1 }}>
            <em>"{patient.chief_complaint}"</em>
          </span>
          <span style={{ whiteSpace: 'nowrap' }}>{patient.age}y &nbsp;·&nbsp;</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 3, whiteSpace: 'nowrap' }}>
            <Clock size={11} /> {patient.wait_time_min}m
          </span>
        </div>

        {/* Vitals chips */}
        <div style={{
          display: 'flex', gap: '0.6rem', fontSize: '0.72rem', marginBottom: 8,
          flexWrap: 'wrap',
        }}>
          {[
            ['❤️', 'HR', `${patient.hr} bpm`],
            ['🫁', 'SpO₂', `${patient.spo2}%`],
            ['🩸', 'BP', `${patient.sbp}/${patient.dbp}`],
            ['🌡️', 'T', `${patient.temp}°F`],
          ].map(([icon, label, val]) => (
            <span key={label} style={{
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid #30363D', borderRadius: 6,
              padding: '0.1rem 0.4rem', color: '#94a3b8',
            }}>
              {icon} {label}: <b style={{ color: '#E6EDF3' }}>{val}</b>
            </span>
          ))}
        </div>

        {/* Risk bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <RiskBar value={patient.risk_probability} />
          <span style={{ color: levelColor, fontWeight: 700, fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
            {(patient.risk_probability * 100).toFixed(0)}%
          </span>
        </div>
      </motion.div>

      {/* Detail Sheet */}
      <AnimatePresence>
        {open && (
          <DetailSheet patient={patient} onClose={() => setOpen(false)} acuityColor={acuityColor} levelColor={levelColor} />
        )}
      </AnimatePresence>
    </>
  )
}

function DetailSheet({ patient, onClose, acuityColor, levelColor }) {
  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 200,
        }}
      />
      {/* Panel */}
      <motion.div
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
        transition={{ type: 'spring', stiffness: 320, damping: 36 }}
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: 520,
          background: '#0D1117', borderLeft: '1px solid #30363D',
          zIndex: 300, overflowY: 'auto', padding: '1.5rem',
        }}
      >
        <button
          onClick={onClose}
          style={{
            background: 'none', border: '1px solid #30363D', borderRadius: 6,
            color: '#8B949E', cursor: 'pointer', padding: '0.3rem 0.6rem',
            marginBottom: '1rem', fontFamily: 'inherit', fontSize: '0.8rem',
          }}
        >
          ← Close
        </button>

        <div style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: 4 }}>
            <span style={{ background: acuityColor, color: '#000', borderRadius: 6, padding: '0.2rem 0.6rem', fontSize: '0.8rem', fontWeight: 700 }}>
              ESI {patient.dynamic_acuity}
            </span>
            <h2 style={{ margin: 0, fontSize: '1.2rem', color: '#E6EDF3' }}>{patient.name}</h2>
            <span style={{ color: levelColor, fontWeight: 700, marginLeft: 'auto', fontSize: '0.9rem' }}>
              {patient.alert_level}
            </span>
          </div>
          <div style={{ color: '#8B949E', fontSize: '0.82rem' }}>
            {patient.age}y · {patient.sex || 'Unknown'} · {patient.symptom_category} · Wait: {patient.wait_time_min}min
          </div>
          <div style={{ color: '#94a3b8', fontSize: '0.83rem', marginTop: 4, fontStyle: 'italic' }}>
            "{patient.chief_complaint}"
          </div>
        </div>

        {/* Risk score */}
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: '0.8rem', color: '#8B949E' }}>
            <span>Risk Probability</span>
            <span style={{ color: levelColor, fontWeight: 700, fontSize: '1.1rem' }}>
              {(patient.risk_probability * 100).toFixed(1)}%
            </span>
          </div>
          <div style={{ height: 10, background: 'rgba(255,255,255,0.08)', borderRadius: 5, overflow: 'hidden' }}>
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${patient.risk_probability * 100}%` }}
              transition={{ duration: 0.9, ease: [0.34, 1.56, 0.64, 1] }}
              style={{ height: '100%', background: levelColor, borderRadius: 5 }}
            />
          </div>
        </div>

        {/* SHAP Chart */}
        <ShapChart
          shapLabels={patient.shap_labels || []}
          shapValues={patient.shap_values || []}
          explanation={patient.explanation || []}
          alertLevel={patient.alert_level}
          patientName={patient.name}
        />
      </motion.div>
    </>
  )
}
