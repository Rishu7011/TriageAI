/**
 * PatientIntake.jsx — Form for manually admitting a new patient.
 * Sends POST /admit with Pydantic-validated vital signs.
 */
import React, { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { api } from '../lib/api'

const DEFAULTS = {
  name: '', age: '', sex: 'Male', symptom_category: '',
  chief_complaint: '',
  hr: '', sbp: '', dbp: '', rr: '', spo2: '', temp: '',
  has_comorbidity: false,
}

export default function PatientIntake({ onSubmit, onClose }) {
  const [form, setForm] = useState(DEFAULTS)
  const [categories, setCategories] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getCategories().then(r => setCategories(r.data)).catch(() => {})
  }, [])

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        name: form.name, age: parseInt(form.age), sex: form.sex,
        symptom_category: form.symptom_category,
        chief_complaint: form.chief_complaint,
        hr: parseFloat(form.hr),   sbp: parseFloat(form.sbp),
        dbp: parseFloat(form.dbp), rr: parseFloat(form.rr),
        spo2: parseFloat(form.spo2), temp: parseFloat(form.temp),
        has_comorbidity: form.has_comorbidity,
      })
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'Admission failed')
    } finally {
      setSubmitting(false)
    }
  }

  const inputStyle = {
    background: '#0D1117', border: '1px solid #30363D',
    borderRadius: 6, padding: '0.42rem 0.6rem',
    color: '#E6EDF3', fontSize: '0.82rem', width: '100%', boxSizing: 'border-box',
  }

  const labelStyle = { color: '#8B949E', fontSize: '0.72rem', marginBottom: 3, display: 'block' }

  const Field = ({ label, name, type='text', placeholder='' }) => (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type} value={form[name]} placeholder={placeholder}
        onChange={e => set(name, type === 'number' ? e.target.value : e.target.value)}
        style={inputStyle} required
      />
    </div>
  )

  return (
    <form onSubmit={handleSubmit} style={{
      background: '#161B22', border: '1px solid #30363D',
      borderRadius: 12, padding: '1.1rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.85rem' }}>
        <span style={{ color: '#E6EDF3', fontWeight: 600, fontSize: '0.9rem' }}>Admit New Patient</span>
        <button type="button" onClick={onClose} style={{ background: 'none', border: 'none', color: '#8B949E', cursor: 'pointer' }}>
          <X size={16} />
        </button>
      </div>

      {error && (
        <div style={{ background: 'rgba(230,57,70,0.12)', border: '1px solid #E63946', borderRadius: 6, padding: '0.5rem 0.75rem', marginBottom: '0.75rem', color: '#ff6b6b', fontSize: '0.78rem' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.6rem', marginBottom: '0.65rem' }}>
        <Field label="Patient Name *"     name="name" />
        <Field label="Age *"              name="age" type="number" />
        <div>
          <label style={labelStyle}>Sex</label>
          <select value={form.sex} onChange={e => set('sex', e.target.value)} style={inputStyle}>
            <option>Male</option><option>Female</option><option>Other</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem', marginBottom: '0.65rem' }}>
        <div>
          <label style={labelStyle}>Symptom Category *</label>
          <select value={form.symptom_category} onChange={e => set('symptom_category', e.target.value)} style={inputStyle} required>
            <option value="">Select…</option>
            {categories.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
        <Field label="Chief Complaint *" name="chief_complaint" />
      </div>

      <div style={{ color: '#8B949E', fontSize: '0.72rem', marginBottom: 6 }}>Vital Signs *</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem', marginBottom: '0.65rem' }}>
        <Field label="HR (bpm)"  name="hr"  />
        <Field label="SBP"       name="sbp" />
        <Field label="DBP"       name="dbp" />
        <Field label="RR"        name="rr"  />
        <Field label="SpO₂ (%)"  name="spo2"/>
        <Field label="Temp (°F)" name="temp"/>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
        <input type="checkbox" id="comorbid" checked={form.has_comorbidity}
          onChange={e => set('has_comorbidity', e.target.checked)} />
        <label htmlFor="comorbid" style={{ color: '#8B949E', fontSize: '0.78rem', cursor: 'pointer' }}>
          Known comorbidities (HTN, T2DM, COPD, etc.) — adds 1.15× risk multiplier
        </label>
      </div>

      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <button type="submit" disabled={submitting} style={{
          flex: 1, background: '#E63946', border: 'none', borderRadius: 8,
          padding: '0.55rem', color: '#fff', fontWeight: 700, fontSize: '0.85rem',
          cursor: submitting ? 'not-allowed' : 'pointer', opacity: submitting ? 0.7 : 1,
        }}>
          {submitting ? 'Admitting…' : 'Admit & Score'}
        </button>
        <button type="button" onClick={onClose} style={{
          background: '#161B22', border: '1px solid #30363D', borderRadius: 8,
          padding: '0.55rem 1rem', color: '#8B949E', fontSize: '0.82rem', cursor: 'pointer',
        }}>
          Cancel
        </button>
      </div>
    </form>
  )
}
