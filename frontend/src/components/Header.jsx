import React, { useEffect, useState } from 'react'
import { Activity, Users, Zap } from 'lucide-react'

export default function Header({ patientCount = 0, simOffset = 0 }) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const timeStr = time.toLocaleTimeString('en-US', { hour12: false })

  return (
    <header style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      background: 'rgba(13,17,23,0.97)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid #30363D',
      height: 64,
      display: 'flex', alignItems: 'center',
      padding: '0 1.5rem',
      gap: '1rem',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flex: 1 }}>
        <span style={{ fontSize: '1.4rem' }}>🏥</span>
        <div>
          <div style={{
            fontWeight: 700, fontSize: '1.1rem', letterSpacing: '0.05em',
            color: '#E6EDF3',
          }}>
            Triage<span style={{ color: '#E63946' }}>AI</span>
          </div>
          <div style={{ fontSize: '0.65rem', color: '#8B949E', letterSpacing: '0.12em', marginTop: -2 }}>
            EMERGENCY DEPARTMENT INTELLIGENCE
          </div>
        </div>
      </div>

      {/* Centre badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          background: '#161B22', border: '1px solid #30363D',
          borderRadius: 8, padding: '0.3rem 0.75rem',
          fontSize: '0.78rem', color: '#8B949E',
        }}>
          <Activity size={13} color="#4CAF50" />
          <span>AI-Powered Continuous Re-evaluation</span>
        </div>

        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          background: '#161B22', border: '1px solid #30363D',
          borderRadius: 8, padding: '0.3rem 0.75rem',
          fontSize: '0.78rem', color: '#8B949E',
        }}>
          <Zap size={13} color="#FFD700" />
          <span>Dynamic Risk Scoring</span>
        </div>
      </div>

      {/* Right side */}
      <div style={{
        flex: 1, display: 'flex', alignItems: 'center',
        justifyContent: 'flex-end', gap: '1rem',
      }}>
        {/* Patient count */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          background: '#161B22', border: '1px solid #30363D',
          borderRadius: 8, padding: '0.3rem 0.75rem',
          fontSize: '0.78rem',
        }}>
          <Users size={13} color="#8B949E" />
          <span style={{ color: '#E6EDF3', fontWeight: 700 }}>{patientCount}</span>
          <span style={{ color: '#8B949E' }}>patients</span>
        </div>

        {/* Live indicator */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.4rem',
          background: '#161B22', border: '1px solid #30363D',
          borderRadius: 8, padding: '0.3rem 0.75rem',
          fontSize: '0.78rem',
        }}>
          <span
            className="blink"
            style={{ width: 8, height: 8, borderRadius: '50%', background: '#4CAF50', display: 'inline-block' }}
          />
          <span style={{ color: '#4CAF50', fontWeight: 700 }}>LIVE</span>
        </div>

        {/* Clock */}
        <div style={{
          fontFamily: 'monospace', fontSize: '0.9rem',
          color: '#E6EDF3', fontWeight: 600,
          background: '#161B22', border: '1px solid #30363D',
          borderRadius: 8, padding: '0.3rem 0.75rem',
        }}>
          {timeStr}
        </div>
      </div>
    </header>
  )
}
