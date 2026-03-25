/**
 * ShapChart.jsx — Horizontal bar SHAP waterfall chart using Recharts.
 * Renders sorted feature contributions with positive=red, negative=green.
 */
import React from 'react'
import { BarChart, Bar, XAxis, YAxis, Cell, Tooltip, ResponsiveContainer } from 'recharts'

export default function ShapChart({ labels = [], values = [] }) {
  if (!labels.length || !values.length) return null

  // Sort by absolute magnitude, take top 8
  const pairs = labels
    .map((l, i) => ({ label: l, value: values[i] || 0 }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, 8)

  const data = pairs.map(p => ({
    name: p.label.length > 32 ? p.label.slice(0, 30) + '…' : p.label,
    value: parseFloat(p.value.toFixed(3)),
  }))

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]
    return (
      <div style={{
        background: '#161B22', border: '1px solid #30363D',
        borderRadius: 6, padding: '0.4rem 0.7rem', fontSize: '0.75rem',
      }}>
        <div style={{ color: '#E6EDF3', fontWeight: 600 }}>{d.payload.name}</div>
        <div style={{ color: d.value > 0 ? '#E63946' : '#4CAF50' }}>
          SHAP: {d.value > 0 ? '+' : ''}{d.value.toFixed(3)}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{
        color: '#8B949E', fontSize: '0.68rem', marginBottom: 6,
        display: 'flex', alignItems: 'center', gap: '0.5rem',
      }}>
        <span>SHAP feature importance</span>
        <span style={{ color: '#E63946' }}>■ increases risk</span>
        <span style={{ color: '#4CAF50' }}>■ decreases risk</span>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(160, data.length * 26)}>
        <BarChart data={data} layout="vertical" margin={{ left: 4, right: 20, top: 0, bottom: 0 }}>
          <XAxis type="number" hide tickLine={false} axisLine={false} domain={['dataMin', 'dataMax']} />
          <YAxis
            type="category" dataKey="name" width={180}
            tick={{ fill: '#E6EDF3', fontSize: 11 }}
            tickLine={false} axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" radius={[3, 3, 3, 3]} maxBarSize={14}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.value > 0 ? '#E63946' : '#4CAF50'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
