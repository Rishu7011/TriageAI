/**
 * QueueDashboard.jsx — Main dashboard view showing patient queue + controls.
 * Handles: queue display, alerts, simulation controls, tabs (Queue/WhatIf/TimeLapse).
 */
import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCcw, FastForward, UserPlus, Trash2, Play } from 'lucide-react'
import PatientCard from './PatientCard'
import AlertBanner from './AlertBanner'
import PatientIntake from './PatientIntake'
import WhatIfMode from './WhatIfMode'
import TimeLapse from './TimeLapse'
import { useAutoRescore } from '../hooks/useAutoRescore'
import { api } from '../lib/api'

const TABS = ['Queue', 'What-If', 'Time Lapse']

export default function QueueDashboard({
  patients, loading, simOffset, setSimOffset,
  whatIfPatients, onRescore, onSimulate, onRunWhatIf,
  onAddPatient, onClear, onLoadDemo,
  isTimeLapsing, setIsTimeLapsing,
}) {
  const [activeTab, setActiveTab] = useState('Queue')
  const [showIntake, setShowIntake] = useState(false)
  const [alerts, setAlerts] = useState([])

  // Auto-rescore every 60 seconds
  useAutoRescore(() => onRescore(simOffset), 60000, !showIntake)

  // Collect active alerts from current patients
  const activeAlerts = patients.filter(p => p.alert_level === 'CRITICAL' || p.alert_level === 'WARNING')
  const criticalCount = patients.filter(p => p.alert_level === 'CRITICAL').length

  const ackAlert = async (alertId) => {
    try { await api.acknowledgeAlert(alertId) } catch (e) { /* ignore */ }
    setAlerts(prev => prev.filter(a => a.alert_id !== alertId))
  }

  const handleSimulate = async () => {
    setActiveTab('Queue')
    await onSimulate(90)
    setSimOffset(prev => prev + 90)
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '1.25rem 1rem' }}>
      {/* ── Alert banners ─────────────────────────────────── */}
      <AlertBanner
        alerts={activeAlerts.map(p => ({
          alert_id: p.patient_id,
          severity: p.alert_level,
          patient_name: p.name,
          alert_text: p.explanation?.[0] || `Risk ${(p.risk_probability*10).toFixed(1)}/10`,
        }))}
        onAcknowledge={ackAlert}
      />

      {/* ── Stats row ─────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Total', value: patients.length },
          { label: 'Critical', value: criticalCount, color: '#E63946' },
          { label: 'Warning',  value: patients.filter(p => p.alert_level === 'WARNING').length, color: '#FF8C00' },
          { label: 'Stable',   value: patients.filter(p => p.alert_level === 'STABLE').length, color: '#4CAF50' },
          { label: 'Sim +',    value: `${Math.round(simOffset)}m` },
        ].map(({ label, value, color }) => (
          <div key={label} style={{
            background: '#161B22', border: '1px solid #30363D',
            borderRadius: 8, padding: '0.5rem 0.9rem', flex: '1 1 0',
            minWidth: 70,
          }}>
            <div style={{ color: color || '#8B949E', fontSize: '0.68rem', marginBottom: 1 }}>{label}</div>
            <div style={{ color: color || '#E6EDF3', fontWeight: 700, fontSize: '1rem' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* ── Action bar ────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <Btn icon={<RotateCcw size={14} />} label="Rescore"
          onClick={() => onRescore(simOffset)} loading={loading} />
        <Btn icon={<FastForward size={14} />} label="Simulate 90min"
          onClick={handleSimulate} loading={loading} highlight />
        <Btn icon={<UserPlus size={14} />} label="Admit Patient"
          onClick={() => setShowIntake(s => !s)} />
        <Btn icon={<Trash2 size={14} />} label="Clear"
          onClick={onClear} danger />
        <Btn icon={<Play size={14} />} label="Reload Demo"
          onClick={() => onLoadDemo(simOffset)} loading={loading} />
      </div>

      {/* ── Intake Form (toggle) ───────────────────────────── */}
      <AnimatePresence>
        {showIntake && (
          <motion.div
            key="intake"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{ overflow: 'hidden', marginBottom: '1rem' }}
          >
            <PatientIntake
              onSubmit={async (data) => { await onAddPatient(data); setShowIntake(false) }}
              onClose={() => setShowIntake(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Tabs ──────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1rem', borderBottom: '1px solid #30363D', paddingBottom: '0.5rem' }}>
        {TABS.map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} style={{
            background: activeTab === tab ? '#E63946' : 'transparent',
            color: activeTab === tab ? '#fff' : '#8B949E',
            border: 'none', borderRadius: 6, padding: '0.35rem 0.85rem',
            fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
            transition: 'all 0.15s',
          }}>
            {tab}
            {tab === 'Queue' && criticalCount > 0 && (
              <span style={{
                marginLeft: 4, background: '#E63946', borderRadius: 10,
                padding: '0 5px', fontSize: '0.65rem', color: '#fff',
              }}>
                {criticalCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab content ───────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {activeTab === 'Queue' && (
          <motion.div key="queue" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {patients.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#8B949E', padding: '3rem' }}>
                No patients in queue. Load demo or admit a patient.
              </div>
            ) : (
              patients.map((p, i) => <PatientCard key={p.patient_id} patient={p} rank={i + 1} />)
            )}
          </motion.div>
        )}

        {activeTab === 'What-If' && (
          <motion.div key="whatif" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <WhatIfMode
              currentPatients={patients}
              whatIfPatients={whatIfPatients}
              onRun={onRunWhatIf}
              loading={loading}
            />
          </motion.div>
        )}

        {activeTab === 'Time Lapse' && (
          <motion.div key="timelapse" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <TimeLapse patients={patients} simOffset={simOffset} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ── Helper: tidy action button ─────────────────────────────
function Btn({ icon, label, onClick, loading, highlight, danger }) {
  const bg = highlight ? '#E63946' : danger ? 'rgba(230,57,70,0.12)' : '#161B22'
  const border = highlight ? '#E63946' : danger ? '#E63946' : '#30363D'
  const color  = highlight ? '#fff' : danger ? '#E63946' : '#E6EDF3'

  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        display: 'flex', alignItems: 'center', gap: '0.35rem',
        background: bg, border: `1px solid ${border}`,
        borderRadius: 8, padding: '0.42rem 0.8rem',
        color, fontSize: '0.78rem', fontWeight: 600,
        cursor: loading ? 'not-allowed' : 'pointer',
        opacity: loading ? 0.6 : 1,
        transition: 'all 0.15s',
      }}
    >
      {icon}
      {label}
    </button>
  )
}
