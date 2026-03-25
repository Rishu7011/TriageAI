import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import AlertBannerComp from './AlertBanner'
import PatientCard from './PatientCard'
import PatientIntake from './PatientIntake'
import WhatIfMode from './WhatIfMode'
import TimeLapse from './TimeLapse'
import { PlayCircle, PlusCircle, RotateCcw, Zap, BeakerIcon } from 'lucide-react'

const TAB_STYLE = (active) => ({
  background: active ? '#E63946' : 'transparent',
  border: active ? 'none' : '1px solid #30363D',
  color: active ? '#fff' : '#8B949E',
  borderRadius: 8, padding: '0.4rem 1rem',
  cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600,
  fontFamily: 'inherit', transition: 'all 0.2s',
})

export default function QueueDashboard({
  patients, loading, simOffset, setSimOffset,
  whatIfPatients, onRescore, onSimulate, onRunWhatIf,
  onAddPatient, onClear, onLoadDemo,
  isTimeLapsing, setIsTimeLapsing,
}) {
  const [tab, setTab] = useState('queue')
  const [simRunning, setSimRunning] = useState(false)

  const handleSimulate = async () => {
    setSimRunning(true)
    try { await onSimulate(90) }
    finally { setSimRunning(false) }
  }

  const critCount  = patients.filter(p => p.alert_level === 'CRITICAL').length
  const highCount  = patients.filter(p => p.alert_level === 'WARNING').length
  const avgWait    = patients.length
    ? Math.round(patients.reduce((s, p) => s + p.wait_time_min, 0) / patients.length)
    : 0

  return (
    <div style={{ padding: '1rem 1.5rem', maxWidth: 1280, margin: '0 auto' }}>
      {/* Metrics strip */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)',
        gap: '0.75rem', marginBottom: '1rem',
      }}>
        {[
          { label: 'TOTAL PATIENTS', val: patients.length, sub: 'in queue', color: '#E6EDF3' },
          { label: 'CRITICAL', val: critCount, sub: 'risk ≥ 70%', color: '#E63946' },
          { label: 'WARNING', val: highCount, sub: 'risk 50–70%', color: '#FF8C00' },
          { label: 'AVG WAIT', val: `${avgWait}m`, sub: 'all patients', color: '#FFD700' },
          { label: 'MODEL', val: 'GBM', sub: 'AUC 0.837', color: '#4CAF50' },
        ].map((m, i) => (
          <div key={i} style={{
            background: '#161B22', border: '1px solid #30363D',
            borderRadius: 10, padding: '0.75rem 1rem', textAlign: 'center',
          }}>
            <div style={{ fontWeight: 800, fontSize: '1.6rem', color: m.color }}>{m.val}</div>
            <div style={{ fontSize: '0.65rem', color: '#8B949E', letterSpacing: '0.08em', marginTop: 2 }}>{m.label}</div>
            <div style={{ fontSize: '0.65rem', color: '#475569', marginTop: 1 }}>{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Action bar */}
      <div style={{
        display: 'flex', gap: '0.6rem', flexWrap: 'wrap',
        marginBottom: '1rem', alignItems: 'center',
      }}>
        <button
          onClick={handleSimulate}
          disabled={simRunning || loading}
          style={{
            background: simRunning ? '#21262D' : 'linear-gradient(135deg,#E63946,#c1121f)',
            border: 'none', borderRadius: 8, padding: '0.55rem 1.1rem',
            color: '#fff', fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit',
            fontSize: '0.83rem', display: 'flex', alignItems: 'center', gap: '0.4rem',
          }}
        >
          <PlayCircle size={16} />
          {simRunning ? 'Simulating…' : '⏩ Simulate 90 Minutes'}
        </button>

        <button
          onClick={() => setTab(tab === 'intake' ? 'queue' : 'intake')}
          style={TAB_STYLE(tab === 'intake')}
        >
          <PlusCircle size={13} style={{ display: 'inline', marginRight: 4 }} />
          Add Patient
        </button>

        <button
          onClick={() => setTab(tab === 'whatif' ? 'queue' : 'whatif')}
          style={TAB_STYLE(tab === 'whatif')}
        >
          <Zap size={13} style={{ display: 'inline', marginRight: 4 }} />
          What-If Mode
        </button>

        <button
          onClick={() => { setTab('lapse'); setIsTimeLapsing(true); }}
          style={TAB_STYLE(tab === 'lapse')}
        >
          ▶ Time-Lapse
        </button>

        <button
          onClick={onLoadDemo}
          disabled={loading}
          style={{ ...TAB_STYLE(false), marginLeft: 'auto' }}
        >
          <RotateCcw size={13} style={{ display: 'inline', marginRight: 4 }} />
          Reload Demo
        </button>

        <button
          onClick={onClear}
          style={{ ...TAB_STYLE(false), borderColor: '#E6394633', color: '#E63946' }}
        >
          Clear Queue
        </button>
      </div>

      {/* Alert banners */}
      <AlertBannerComp patients={patients} />

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {tab === 'queue' && (
          <motion.div key="queue" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <AnimatePresence>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                {patients.map((p, i) => (
                  <PatientCard key={p.patient_id} patient={p} index={i} />
                ))}
              </div>
            </AnimatePresence>
          </motion.div>
        )}

        {tab === 'intake' && (
          <motion.div key="intake" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <PatientIntake onSubmit={async (data) => { await onAddPatient(data); setTab('queue'); }} loading={loading} />
          </motion.div>
        )}

        {tab === 'whatif' && (
          <motion.div key="whatif" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <WhatIfMode
              currentPatients={patients}
              whatIfPatients={whatIfPatients}
              onRunWhatIf={onRunWhatIf}
              loading={loading}
            />
          </motion.div>
        )}

        {tab === 'lapse' && (
          <motion.div key="lapse" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <TimeLapse
              onClose={() => { setTab('queue'); setIsTimeLapsing(false); }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
