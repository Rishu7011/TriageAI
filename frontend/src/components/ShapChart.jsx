import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts'

const LEVEL_COLOR = { CRITICAL: '#E63946', WARNING: '#FF8C00', WATCH: '#FFD700', STABLE: '#4CAF50' }

export default function ShapChart({ shapLabels, shapValues, explanation, alertLevel, patientName }) {
  const levelColor = LEVEL_COLOR[alertLevel] || '#8B949E'

  // Build chart data
  const data = shapLabels.map((label, i) => ({
    name: label.length > 30 ? label.slice(0, 28) + '…' : label,
    value: shapValues[i] || 0,
  })).sort((a, b) => Math.abs(b.value) - Math.abs(a.value)).slice(0, 8)

  return (
    <div>
      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#E6EDF3', marginBottom: '0.75rem' }}>
        🧠 Why This Risk Score?
      </div>

      {data.length === 0 ? (
        <div style={{
          background: 'rgba(255,255,255,0.03)', border: '1px solid #30363D',
          borderRadius: 8, padding: '1.5rem', textAlign: 'center',
          color: '#8B949E', fontSize: '0.82rem',
        }}>
          ⏳ Calculating SHAP explanations…
        </div>
      ) : (
        <>
          <div style={{ width: '100%', height: 240 }}>
            <ResponsiveContainer>
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 4, right: 20, left: 8, bottom: 4 }}
              >
                <XAxis
                  type="number"
                  tick={{ fill: '#8B949E', fontSize: 10 }}
                  tickLine={false}
                  axisLine={{ stroke: '#30363D' }}
                  label={{ value: '← Decreases Risk | Increases Risk →', position: 'insideBottom', offset: -2, fill: '#8B949E', fontSize: 9 }}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={160}
                  tick={{ fill: '#8B949E', fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                  contentStyle={{ background: '#161B22', border: '1px solid #30363D', borderRadius: 8, fontSize: '0.78rem' }}
                  formatter={(val) => [val > 0 ? `+${val.toFixed(4)}` : val.toFixed(4), 'SHAP contribution']}
                />
                <ReferenceLine x={0} stroke="#30363D" />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {data.map((entry, i) => (
                    <Cell key={i} fill={entry.value >= 0 ? '#E63946' : '#4488FF'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Legend */}
          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.72rem', marginBottom: '1rem' }}>
            <span style={{ color: '#E63946' }}>■ Increases risk</span>
            <span style={{ color: '#4488FF' }}>■ Decreases risk</span>
          </div>
        </>
      )}

      {/* Plain-English Interpretation */}
      {explanation?.length > 0 && (
        <div style={{
          background: `${levelColor}11`, border: `1px solid ${levelColor}33`,
          borderRadius: 10, padding: '1rem', marginTop: '0.75rem',
        }}>
          <div style={{ fontWeight: 700, color: levelColor, fontSize: '0.8rem', marginBottom: '0.5rem' }}>
            📋 Clinical Interpretation — {alertLevel}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {explanation.slice(0, 4).map((line, i) => (
              <div key={i} style={{ fontSize: '0.78rem', color: '#8B949E', display: 'flex', gap: '0.4rem' }}>
                <span style={{ color: levelColor }}>•</span>
                <span>{line}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
