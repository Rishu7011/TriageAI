import { useState, useCallback } from 'react'
import * as api from '../lib/api'

export function usePatients() {
  const [patients, setPatients]         = useState([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [simOffset, setSimOffset]       = useState(0)
  const [whatIfPatients, setWhatIfPts]  = useState([])

  const wrap = async (fn) => {
    setLoading(true); setError(null)
    try { return await fn() }
    catch (e) { setError(e?.response?.data?.detail || e.message || 'API error') }
    finally   { setLoading(false) }
  }

  const loadDemo = useCallback(() =>
    wrap(async () => {
      const data = await api.loadDemo(simOffset)
      setPatients(data)
      return data
    }), [simOffset])

  const addPatient = useCallback((intake) =>
    wrap(async () => {
      const data = await api.addPatient(intake)
      setPatients(prev => [...prev, data])
      return data
    }), [])

  const clearPatients = useCallback(() =>
    wrap(async () => {
      await api.clearPatients()
      setPatients([])
      setWhatIfPts([])
    }), [])

  const rescore = useCallback((offset = simOffset) =>
    wrap(async () => {
      const data = await api.rescore(offset)
      setPatients(data)
      return data
    }), [simOffset])

  const simulate = useCallback((minutes = 90) =>
    wrap(async () => {
      const result = await api.simulate(minutes)
      if (result.patients) setPatients(result.patients)
      return result
    }), [])

  const runWhatIf = useCallback((futureMin) =>
    wrap(async () => {
      const data = await api.whatIf(futureMin, simOffset)
      setWhatIfPts(data)
      return data
    }), [simOffset])

  return {
    patients, loading, error, simOffset, setSimOffset,
    whatIfPatients, loadDemo, addPatient,
    clearPatients, rescore, simulate, runWhatIf,
  }
}
