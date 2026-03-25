/**
 * TimeLapse.jsx — Risk trajectory chart over time for all patients.
 * Uses Recharts LineChart to show parallel risk curves.
 */
import React, { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer } from 'recharts'
import { api } from '../lib/api'

const PATIENT_COLORS = [
  '#E63946', '#FF8C00', '#FFD700', '#4CAF50', '#3B82F6',
  '#A78BFA', '#F472B6', '#34D399', '#FB923C', '#60A5FA',
]

export default function TimeLapse({ patients, simOffset }) {
  const [steps, setSteps] = useState(null)
  const [loading, setLoading] = useState(false)
  const [horizon, setHorizon] = useState(120)

  const run = async () => {
    if (!patients.length) return
    setLoading(true)
    try {
      const res = await api.timelapse(10, horizon)
      setSteps(res.data)
    } catch (e) {
      console.error('Timelapse error', e)
    } finally {
      setLoading(false)
    }
  }

  // Build chart data: [{t: 0, "James Wilson": 5.5, ...}, ...]
  const chartData = steps?.map(snap => {
    const row = { t: snap.t }
    snap.patients.forEach(p => { row[p.name] = p.risk })
    return row
  }) || []

  const patientNames = patients.map(p => p.name)

  return (
    <div>
      <div style={{ color: '#8B949E', fontSize: '0.82rem', marginBottom: '0.85rem' }}>
        Visualise how patient risk trajectories evolve over time.
        The red dashed line at 7.5 is the alert threshold.
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        <span style={{ color: '#8B949E', fontSize: '0.78rem' }}>Horizon:</span>
        {[60, 90, 120, 180].map(h => (
          <button key={h} onClick={() => setHorizon(h)} style={{
            background: h === horizon ? '#E63946' : '#161B22',
            border: `1px solid ${h === horizon ? '#E63946' : '#30363D'}`,
            borderRadius: 6, padding: '0.3rem 0.6rem',
            color: h === horizon ? '#fff' : '#8B949E',
            fontSize: '0.75rem', fontWeight: 600, cursor: 'pointer',
          }}>{h}m</button>
        ))}
        <button
          onClick={run}
          disabled={loading || !patients.length}
          style={{
            background: '#E63946', border: 'none', borderRadius: 8,
            padding: '0.38rem 0.9rem', color: '#fff', fontSize: '0.78rem',
            fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Generating…' : 'Generate Curves'}
        </button>
      </div>

      {!steps ? (
        <div style={{ color: '#8B949E', textAlign: 'center', padding: '3rem', fontSize: '0.82rem' }}>
          Click "Generate Curves" to render risk trajectories.
        </div>
      ) : (
        <div style={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 12, padding: '1rem' }}>
          <ResponsiveContainer width="100%" height={340}>
            <LineChart data={chartData} margin={{ top: 8, right: 20, bottom: 8, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#30363D" />
              <XAxis dataKey="t" stroke="#8B949E" tick={{ fontSize: 11 }}
                label={{ value: 'Minutes', position: 'insideBottom', offset: -2, fill: '#8B949E', fontSize: 11 }} />
              <YAxis stroke="#8B949E" tick={{ fontSize: 11 }} domain={[0, 10]}
                label={{ value: 'Risk', angle: -90, position: 'insideLeft', fill: '#8B949E', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#8B949E' }}
                formatter={(v, name) => [`${parseFloat(v).toFixed(1)}/10`, name]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <ReferenceLine y={7.5} stroke="#E63946" strokeDasharray="6 3"
                label={{ value: 'ALERT', fill: '#E63946', fontSize: 10, position: 'right' }} />
              {patientNames.map((name, i) => (
                <Line
                  key={name} type="monotone" dataKey={name}
                  stroke={PATIENT_COLORS[i % PATIENT_COLORS.length]}
                  strokeWidth={2} dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
