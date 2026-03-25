import React, { useState, useEffect } from 'react'
import { getCategories } from '../lib/api'

const FIELD = ({ label, children }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
    <label style={{ fontSize: '0.75rem', color: '#8B949E', fontWeight: 600 }}>{label}</label>
    {children}
  </div>
)

const INPUT = (props) => (
  <input {...props} style={{
    background: '#0D1117', border: '1px solid #30363D', borderRadius: 6,
    color: '#E6EDF3', padding: '0.5rem 0.75rem', fontSize: '0.83rem',
    fontFamily: 'inherit', outline: 'none', width: '100%',
    transition: 'border-color 0.2s',
    ...(props.style || {}),
  }} />
)

const SELECT = ({ children, ...props }) => (
  <select {...props} style={{
    background: '#0D1117', border: '1px solid #30363D', borderRadius: 6,
    color: '#E6EDF3', padding: '0.5rem 0.75rem', fontSize: '0.83rem',
    fontFamily: 'inherit', outline: 'none', width: '100%',
  }}>
    {children}
  </select>
)

const DEFAULTS = {
  name: '', age: 45, sex: 'Unknown', symptom_category: 'Abdominal Pain',
  chief_complaint: '', hr: 88, sbp: 128, dbp: 78, rr: 16, spo2: 97,
  temp: 98.6, has_comorbidity: false,
}

export default function PatientIntake({ onSubmit, loading }) {
  const [form, setForm] = useState(DEFAULTS)
  const [categories, setCategories] = useState([])

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {})
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit({ ...form, age: Number(form.age), hr: Number(form.hr), sbp: Number(form.sbp),
      dbp: Number(form.dbp), rr: Number(form.rr), spo2: Number(form.spo2), temp: Number(form.temp) })
  }

  return (
    <form onSubmit={handleSubmit} style={{
      background: '#161B22', border: '1px solid #30363D', borderRadius: 12,
      padding: '1.5rem', maxWidth: 640,
    }}>
      <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: '1.25rem', color: '#E6EDF3' }}>
        🏥 New Patient Intake
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
        <FIELD label="Full Name *">
          <INPUT required value={form.name} onChange={e => set('name', e.target.value)} placeholder="e.g. John Smith" />
        </FIELD>
        <FIELD label="Age *">
          <INPUT required type="number" min={1} max={120} value={form.age} onChange={e => set('age', e.target.value)} />
        </FIELD>
        <FIELD label="Sex">
          <SELECT value={form.sex} onChange={e => set('sex', e.target.value)}>
            {['Unknown', 'Male', 'Female'].map(s => <option key={s}>{s}</option>)}
          </SELECT>
        </FIELD>
        <FIELD label="Symptom Category *">
          <SELECT value={form.symptom_category} onChange={e => set('symptom_category', e.target.value)}>
            {(categories.length ? categories : [
              'Abdominal Pain', 'Chest Pain / Cardiac', 'Respiratory',
              'Stroke / Neurological', 'Trauma / Injury', 'Sepsis / Infection',
              'Minor Injury / Low Acuity', 'GI / GU', 'Allergic Reaction', 'Psychiatric / Behavioral',
            ]).map(c => <option key={c} value={c}>{c}</option>)}
          </SELECT>
        </FIELD>
      </div>

      <FIELD label="Chief Complaint *">
        <INPUT required value={form.chief_complaint} onChange={e => set('chief_complaint', e.target.value)} placeholder="Describe presenting complaint…" />
      </FIELD>

      <div style={{ margin: '1rem 0 0.5rem', fontSize: '0.75rem', color: '#8B949E', fontWeight: 600, letterSpacing: '0.1em' }}>
        VITAL SIGNS
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.6rem', marginBottom: '0.75rem' }}>
        {[
          ['HR (bpm)', 'hr', 40, 220],
          ['SBP (mmHg)', 'sbp', 60, 250],
          ['DBP (mmHg)', 'dbp', 30, 150],
          ['RR (/min)', 'rr', 4, 60],
          ['SpO₂ (%)', 'spo2', 50, 100],
          ['Temp (°F)', 'temp', 90, 110],
        ].map(([label, key, min, max]) => (
          <FIELD key={key} label={label}>
            <INPUT type="number" min={min} max={max} step={key === 'temp' ? 0.1 : 1}
              value={form[key]} onChange={e => set(key, e.target.value)} />
          </FIELD>
        ))}
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', color: '#8B949E', marginBottom: '1rem', cursor: 'pointer' }}>
        <input type="checkbox" checked={form.has_comorbidity} onChange={e => set('has_comorbidity', e.target.checked)} />
        Known comorbidities (diabetes, COPD, heart disease, immunocompromised)
      </label>

      <button
        type="submit" disabled={loading}
        style={{
          width: '100%', padding: '0.75rem',
          background: loading ? '#21262D' : 'linear-gradient(135deg,#E63946,#c1121f)',
          border: 'none', borderRadius: 8, color: '#fff',
          fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: '0.88rem', fontFamily: 'inherit',
        }}
      >
        {loading ? '⏳ Registering…' : '➕ Register & Score Patient'}
      </button>
    </form>
  )
}
