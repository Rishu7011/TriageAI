/**
 * ProblemCard.jsx — Landing state when no patients are in the queue.
 * Shows the project pitch + "Load Demo" button.
 */
import React from 'react'
import { motion } from 'framer-motion'
import { Activity, Play, AlertTriangle, TrendingUp, Brain } from 'lucide-react'

const FEATURES = [
  { icon: <Activity size={18} color="#E63946" />, title: 'Live Risk Scoring', body: 'Multiplicative composite formula: base_risk × time_decay × age_modifier × comorbidity × ML score' },
  { icon: <Brain    size={18} color="#3B82F6" />, title: 'SHAP Explanations', body: 'GradientBoostingClassifier + SHAP TreeExplainer — every risk score explained, not just a number' },
  { icon: <TrendingUp size={18} color="#FF8C00" />, title: 'Time-Lapse Simulation', body: 'Simulate 90 minutes of ED evolution and watch James Wilson escalate from ESI-3 → ESI-2' },
  { icon: <AlertTriangle size={18} color="#FFD700" />, title: 'Intelligent Alerting', body: 'Threshold-based alerts fire when risk ≥ 7.5 — before the patient crashes, not after' },
]

export default function ProblemCard({ onLoadDemo, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      style={{ maxWidth: 680, margin: '4rem auto', padding: '0 1rem' }}
    >
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
        <div style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 72, height: 72, borderRadius: 20,
          background: 'linear-gradient(135deg,#E63946 0%,#c1121f 100%)',
          marginBottom: '1.25rem',
        }}>
          <Activity size={36} color="#fff" />
        </div>
        <h1 style={{
          color: '#E6EDF3', fontFamily: '"Inter",sans-serif',
          fontSize: '2rem', fontWeight: 800, margin: '0 0 0.6rem',
          letterSpacing: '-0.02em',
        }}>
          TriageAI
        </h1>
        <p style={{ color: '#8B949E', fontSize: '0.95rem', lineHeight: 1.6, maxWidth: 480, margin: '0 auto' }}>
          AI-powered Emergency Department triage: continuously re-scoring every patient
          using vitals, time-in-ED, age, comorbidities, and a trained GBM model.
        </p>
      </div>

      {/* Features */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '2rem' }}>
        {FEATURES.map(({ icon, title, body }) => (
          <motion.div
            key={title}
            whileHover={{ scale: 1.02 }}
            style={{
              background: '#161B22', border: '1px solid #30363D',
              borderRadius: 12, padding: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.4rem' }}>
              {icon}
              <span style={{ color: '#E6EDF3', fontWeight: 600, fontSize: '0.85rem' }}>{title}</span>
            </div>
            <p style={{ color: '#8B949E', fontSize: '0.75rem', margin: 0, lineHeight: 1.5 }}>{body}</p>
          </motion.div>
        ))}
      </div>

      {/* CTA */}
      <div style={{ textAlign: 'center' }}>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => onLoadDemo(0)}
          disabled={loading}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
            background: loading ? '#30363D' : 'linear-gradient(135deg,#E63946 0%,#c1121f 100%)',
            border: 'none', borderRadius: 12, padding: '0.85rem 2.25rem',
            color: '#fff', fontWeight: 700, fontSize: '0.95rem',
            cursor: loading ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 20px rgba(230,57,70,0.35)',
            transition: 'all 0.2s',
          }}
        >
          <Play size={18} />
          {loading ? 'Loading Demo…' : 'Load 10-Patient Demo'}
        </motion.button>
        <div style={{ color: '#8B949E', fontSize: '0.75rem', marginTop: '0.75rem' }}>
          Includes James Wilson (ESI-3 → watch him escalate after 90min simulation)
        </div>
      </div>
    </motion.div>
  )
}
