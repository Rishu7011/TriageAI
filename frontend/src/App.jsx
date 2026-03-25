import React, { useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import { usePatients } from './hooks/usePatients'
import Header from './components/Header'
import ProblemCard from './components/ProblemCard'
import QueueDashboard from './components/QueueDashboard'

export default function App() {
  const [isTimeLapsing, setIsTimeLapsing] = useState(false)

  const {
    patients, loading, error, simOffset, setSimOffset,
    whatIfPatients, loadDemo, addPatient,
    clearPatients, rescore, simulate, runWhatIf,
  } = usePatients()

  return (
    <div style={{ minHeight: '100vh', background: '#0D1117' }}>
      <Header
        patientCount={patients.length}
        simOffset={simOffset}
      />

      <main style={{ paddingTop: '72px' }}>
        {error && (
          <div style={{
            background: 'rgba(230,57,70,0.15)',
            border: '1px solid #E63946',
            borderRadius: 8, padding: '0.75rem 1.25rem',
            margin: '1rem', color: '#fca5a5', fontSize: '0.85rem',
          }}>
            ⚠️ {error}
          </div>
        )}

        <AnimatePresence mode="wait">
          {patients.length === 0 ? (
            <ProblemCard key="problem" onLoadDemo={loadDemo} loading={loading} />
          ) : (
            <QueueDashboard
              key="queue"
              patients={patients}
              loading={loading}
              simOffset={simOffset}
              setSimOffset={setSimOffset}
              whatIfPatients={whatIfPatients}
              onRescore={rescore}
              onSimulate={simulate}
              onRunWhatIf={runWhatIf}
              onAddPatient={addPatient}
              onClear={clearPatients}
              onLoadDemo={loadDemo}
              isTimeLapsing={isTimeLapsing}
              setIsTimeLapsing={setIsTimeLapsing}
            />
          )}
        </AnimatePresence>
      </main>
    </div>
  )
}
