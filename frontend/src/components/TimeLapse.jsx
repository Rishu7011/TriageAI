import React, { useState, useRef, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Legend } from 'recharts'
import { motion } from 'framer-motion'
import { timelapse } from '../lib/api'

const PATIENT_COLORS = ['#E63946','#FF8C00','#4CAF50','#4488FF','#FFD700','#9C59D1','#20C997','#FD7E14']
const LEVEL_COLOR = { CRITICAL: '#E63946', WARNING: '#FF8C00', WATCH: '#FFD700', STABLE: '#4CAF50' }

export default function TimeLapse({ onClose }) {
  const [snapshots, setSnapshots] = useState([])
  const [loading, setLoading]     = useState(false)
  const [playing, setPlaying]     = useState(false)
  const [cursor, setCursor]       = useState(0)
  const [names, setNames]         = useState([])
  const intervalRef = useRef(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const data = await timelapse(10, 120)
      setSnapshots(data)
      // Extract patient names for legend
      if (data.length > 0) {
        setNames(data[0].patients.map(p => ({ id: p.patient_id, name: p.name })))
      }
      setCursor(0)
    } catch (e) {
      console.error('TimeLapse fetch failed:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  // Build flat chart data: each row has t + one key per patient
  const chartData = snapshots.map(snap => {
    const row = { t: snap.t }
    snap.patients.forEach(p => { row[p.patient_id] = p.risk })
    return row
  })

  // Get current queue state at cursor
  const currentSnap = snapshots[cursor] || null

  const togglePlay = () => {
    if (playing) {
      clearInterval(intervalRef.current); setPlaying(false)
    } else {
      setPlaying(true)
      intervalRef.current = setInterval(() => {
        setCursor(c => {
          if (c >= snapshots.length - 1) { clearInterval(intervalRef.current); setPlaying(false); return c }
          return c + 1
        })
      }, 600)
    }
  }

  useEffect(() => () => clearInterval(intervalRef.current), [])

  return (
    <div style={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 12, padding: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
        <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#E6EDF3', flex: 1 }}>
          📈 Risk Trajectory Time-Lapse (T+0 → T+120 min)
        </div>
        <button onClick={togglePlay} disabled={loading || snapshots.length === 0}
          style={{
            background: playing ? '#FF8C00' : '#4CAF50', border: 'none', borderRadius: 8,
            padding: '0.45rem 1rem', color: '#000', fontWeight: 700,
            cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.82rem',
          }}>
          {playing ? '⏸ Pause' : '▶ Play'}
        </button>
        <button onClick={fetchData} disabled={loading}
          style={{
            background: 'transparent', border: '1px solid #30363D', borderRadius: 8,
            padding: '0.45rem 0.8rem', color: '#8B949E', cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.82rem',
          }}>
          ↺ Refresh
        </button>
        <button onClick={onClose}
          style={{
            background: 'transparent', border: '1px solid #30363D', borderRadius: 8,
            padding: '0.45rem 0.8rem', color: '#8B949E', cursor: 'pointer', fontFamily: 'inherit', fontSize: '0.82rem',
          }}>
          ✕ Close
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#8B949E' }}>
          ⏳ Fetching risk trajectories from ML engine…
        </div>
      ) : snapshots.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#8B949E' }}>
          No patients loaded. Please load demo patients first.
        </div>
      ) : (
        <>
          {/* Time scrubber */}
          <div style={{ marginBottom: '0.75rem' }}>
            <input type="range" min={0} max={snapshots.length - 1} value={cursor}
              onChange={e => setCursor(Number(e.target.value))}
              style={{ width: '100%', accentColor: '#E63946' }} />
            <div style={{ textAlign: 'center', fontSize: '0.8rem', color: '#FFD700', fontWeight: 700 }}>
              T + {currentSnap?.t ?? 0} minutes
            </div>
          </div>

          {/* Line chart */}
          <div style={{ width: '100%', height: 280, marginBottom: '1rem' }}>
            <ResponsiveContainer>
              <LineChart data={chartData} margin={{ top: 8, right: 20, left: 0, bottom: 8 }}>
                <XAxis dataKey="t" tick={{ fill: '#8B949E', fontSize: 10 }} tickLine={false}
                  label={{ value: 'Minutes in ED', position: 'insideBottom', offset: -2, fill: '#8B949E', fontSize: 10 }} />
                <YAxis domain={[0, 1]} tickFormatter={v => `${(v*100).toFixed(0)}%`}
                  tick={{ fill: '#8B949E', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip contentStyle={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 8, fontSize: '0.75rem' }}
                  formatter={(v, name) => [`${(v*100).toFixed(1)}%`, names.find(n => n.id === name)?.name || name]} />
                <ReferenceLine y={0.70} stroke="#E63946" strokeDasharray="5 3"
                  label={{ value: 'CRITICAL', fill: '#E63946', fontSize: 9, position: 'insideTopRight' }} />
                <ReferenceLine y={0.50} stroke="#FF8C00" strokeDasharray="5 3"
                  label={{ value: 'WARNING', fill: '#FF8C00', fontSize: 9, position: 'insideTopRight' }} />
                {/* Cursor line */}
                {currentSnap && (
                  <ReferenceLine x={currentSnap.t} stroke="#FFD700" strokeWidth={2} />
                )}
                {names.map((n, i) => (
                  <Line key={n.id} type="monotone" dataKey={n.id}
                    stroke={PATIENT_COLORS[i % PATIENT_COLORS.length]}
                    strokeWidth={2} dot={false}
                    strokeDasharray={cursor < snapshots.length - 1 ? '' : undefined}
                    name={n.name} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
            {names.map((n, i) => (
              <span key={n.id} style={{
                background: `${PATIENT_COLORS[i % PATIENT_COLORS.length]}22`,
                border: `1px solid ${PATIENT_COLORS[i % PATIENT_COLORS.length]}55`,
                borderRadius: 6, padding: '0.15rem 0.5rem',
                fontSize: '0.72rem', color: PATIENT_COLORS[i % PATIENT_COLORS.length],
                fontWeight: 600,
              }}>
                ● {n.name}
              </span>
            ))}
          </div>

          {/* Current state at cursor */}
          {currentSnap && (
            <motion.div key={cursor} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div style={{ fontSize: '0.75rem', color: '#8B949E', fontWeight: 700, marginBottom: '0.5rem', letterSpacing: '0.08em' }}>
                QUEUE AT T+{currentSnap.t} MIN
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {currentSnap.patients.map((p, i) => {
                  const color = LEVEL_COLOR[p.alert] || '#8B949E'
                  return (
                    <div key={p.patient_id} style={{
                      background: '#0D1117', border: `1px solid ${color}55`,
                      borderLeft: `3px solid ${color}`,
                      borderRadius: 8, padding: '0.4rem 0.75rem', fontSize: '0.75rem',
                    }}>
                      <div style={{ fontWeight: 600, color: '#E6EDF3' }}>{p.name}</div>
                      <div style={{ color }}>{(p.risk * 100).toFixed(0)}% · {p.alert}</div>
                    </div>
                  )
                })}
              </div>
            </motion.div>
          )}
        </>
      )}
    </div>
  )
}
