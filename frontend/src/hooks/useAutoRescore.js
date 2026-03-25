import { useState, useEffect, useRef } from 'react'
import { rescore } from '../lib/api'

/**
 * Polls /api/patients/rescore every `intervalMs` (default 30 s).
 * Polling pauses when isTimeLapsing is true.
 */
export function useAutoRescore({
  simOffset = 0,
  intervalMs = 30_000,
  isTimeLapsing = false,
  enabled = true,
} = {}) {
  const [patients, setPatients]       = useState([])
  const [isLoading, setIsLoading]     = useState(false)
  const [error, setError]             = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const timerRef = useRef(null)

  const fetchOnce = async () => {
    if (isTimeLapsing) return
    setIsLoading(true)
    try {
      const data = await rescore(simOffset)
      setPatients(data)
      setLastUpdated(new Date())
      setError(null)
    } catch (e) {
      setError(e?.response?.data?.detail || e.message || 'Rescore failed')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!enabled || isTimeLapsing) {
      clearInterval(timerRef.current)
      return
    }
    timerRef.current = setInterval(fetchOnce, intervalMs)
    return () => clearInterval(timerRef.current)
  }, [simOffset, intervalMs, isTimeLapsing, enabled])

  return { patients, isLoading, error, lastUpdated, refresh: fetchOnce }
}
