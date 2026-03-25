/**
 * WhatIfMode.jsx — Side-by-side current vs. future risk comparison.
 * User picks a future horizon (30/60/90/120 min) and sees predicted queue state.
 */
import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'

const HORIZONS = [30, 60, 90, 120]

const alert_color = {
  CRITICAL: '#E63946', WARNING: '#FF8C00', WATCH: '#FFD700', STABLE: '#4CAF50'
}

export default function WhatIfMode({ currentPatients, whatIfPatients, onRun, loading }) {
  const [horizon, setHorizon] = useState(60)

  const futureById = Object.fromEntries((whatIfPatients || []).map(p => [p.patient_id, p]))

  return (
    <div>
      <div style={{ color: '#8B949E', fontSize: '0.82rem', marginBottom: '0.85rem' }}>
        Choose a future time horizon and see how the queue risk distribution shifts.
        Key demo point: watch ESI-3 patients escalate based on ML predictions.
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <span style={{ color: '#8B949E', fontSize: '0.78rem' }}>Simulate +</span>
        {HORIZONS.map(h => (
          <button key={h} onClick={() => setHorizon(h)} style={{
            background: h === horizon ? '#E63946' : '#161B22',
            border: `1px solid ${h === horizon ? '#E63946' : '#30363D'}`,
            borderRadius: 6, padding: '0.3rem 0.65rem',
            color: h === horizon ? '#fff' : '#8B949E',
            fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
          }}>
            {h}m
          </button>
        ))}
        <button
          onClick={() => onRun(horizon)}
          disabled={loading || !currentPatients.length}
          style={{
            display: 'flex', alignItems: 'center', gap: '0.35rem',
            background: loading ? '#30363D' : '#E63946',
            border: 'none', borderRadius: 8,
            padding: '0.38rem 0.9rem', color: '#fff',
            fontSize: '0.78rem', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          <Zap size={13} />
          {loading ? 'Running…' : 'Run What-If'}
        </button>
      </div>

      {/* Comparison rows */}
      {!whatIfPatients?.length ? (
        <div style={{ color: '#8B949E', fontSize: '0.82rem', padding: '2rem', textAlign: 'center' }}>
          Click "Run What-If" to see predicted future patient states.
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <div style={{ color: '#8B949E', fontSize: '0.72rem', textAlign: 'center' }}>NOW</div>
            <div style={{ color: '#8B949E', fontSize: '0.72rem', textAlign: 'center' }}>+{horizon}min (predicted)</div>
          </div>
          {currentPatients.map((cur, i) => {
            const fut = futureById[cur.patient_id]
            const nowRisk  = cur.risk_probability * 10
            const futRisk  = fut ? fut.risk_probability * 10 : nowRisk
            const delta    = futRisk - nowRisk
            const escal    = fut && fut.alert_level !== cur.alert_level && alert_color[fut.alert_level]

            return (
              <motion.div
                key={cur.patient_id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04 }}
                style={{
                  display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem',
                  marginBottom: '0.45rem',
                }}
              >
                {/* Current */}
                <div style={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 8, padding: '0.55rem 0.75rem' }}>
                  <div style={{ color: '#E6EDF3', fontWeight: 600, fontSize: '0.82rem' }}>{cur.name}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: 2 }}>
                    <span style={{ color: alert_color[cur.alert_level] || '#E6EDF3', fontWeight: 700 }}>
                      {nowRisk.toFixed(1)}/10
                    </span>
                    <span style={{ color: '#8B949E', fontSize: '0.68rem' }}>{cur.alert_level}</span>
                  </div>
                </div>

                {/* Future */}
                <div style={{
                  background: escal ? `${alert_color[fut.alert_level]}1A` : '#161B22',
                  border: `1px solid ${escal || '#30363D'}`,
                  borderRadius: 8, padding: '0.55rem 0.75rem',
                }}>
                  {fut ? (
                    <>
                      <div style={{ color: '#E6EDF3', fontWeight: 600, fontSize: '0.82rem' }}>
                        {delta > 0 ? '▲' : delta < 0 ? '▼' : '—'}{' '}
                        {futRisk.toFixed(1)}/10
                        {escal && (
                          <span style={{ color: alert_color[fut.alert_level], fontSize: '0.7rem', marginLeft: 4 }}>
                            → {fut.alert_level}
                          </span>
                        )}
                      </div>
                      <div style={{ color: delta > 1 ? '#E63946' : delta < -1 ? '#4CAF50' : '#8B949E', fontSize: '0.72rem' }}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)} pts in {horizon}min
                      </div>
                    </>
                  ) : (
                    <span style={{ color: '#8B949E', fontSize: '0.78rem' }}>—</span>
                  )}
                </div>
              </motion.div>
            )
          })}
        </>
      )}
    </div>
  )
}
