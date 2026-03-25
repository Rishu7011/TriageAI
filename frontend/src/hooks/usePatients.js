/**
 * usePatients.js — Core state hook for TriageAI
 * Manages patient queue, simulation offset, demo loading, and rescoring.
 */
import { useState, useCallback } from 'react'
import { api } from '../lib/api'

export function usePatients() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [simOffset, setSimOffset] = useState(0)
  const [whatIfPatients, setWhatIfPatients] = useState([])

  const handleError = (e, fallback = 'API error') => {
    console.error(fallback, e)
    setError(e?.response?.data?.detail || e?.message || fallback)
  }

  const loadDemo = useCallback(async (offset = 0) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.loadDemo(offset)
      setPatients(res.data)
      setSimOffset(offset)
      setWhatIfPatients([])
    } catch (e) {
      handleError(e, 'Failed to load demo patients')
    } finally {
      setLoading(false)
    }
  }, [])

  const rescore = useCallback(async (offset = simOffset) => {
    if (!patients.length) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.getQueue(offset)
      setPatients(res.data)
    } catch (e) {
      handleError(e, 'Failed to rescore queue')
    } finally {
      setLoading(false)
    }
  }, [patients.length, simOffset])

  const simulate = useCallback(async (totalMinutes = 90) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.simulate(totalMinutes)
      const { patients: updated } = res.data
      setPatients(updated)
      setSimOffset(prev => prev + totalMinutes)
    } catch (e) {
      handleError(e, 'Simulation failed')
    } finally {
      setLoading(false)
    }
  }, [])

  const runWhatIf = useCallback(async (futureMinutes = 60) => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.whatif(futureMinutes, simOffset)
      setWhatIfPatients(res.data)
    } catch (e) {
      handleError(e, 'What-If analysis failed')
      setWhatIfPatients([])
    } finally {
      setLoading(false)
    }
  }, [simOffset])

  const addPatient = useCallback(async (patientData) => {
    setLoading(true)
    setError(null)
    try {
      await api.addPatient(patientData)
      // Refresh queue after adding
      const res = await api.getQueue(simOffset)
      setPatients(res.data)
    } catch (e) {
      handleError(e, 'Failed to admit patient')
      throw e  // re-throw so form can show error
    } finally {
      setLoading(false)
    }
  }, [simOffset])

  const clearPatients = useCallback(async () => {
    setLoading(true)
    try {
      await api.clearPatients()
      setPatients([])
      setWhatIfPatients([])
      setSimOffset(0)
      setError(null)
    } catch (e) {
      handleError(e, 'Failed to clear patients')
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    patients,
    loading,
    error,
    simOffset,
    setSimOffset,
    whatIfPatients,
    loadDemo,
    rescore,
    simulate,
    runWhatIf,
    addPatient,
    clearPatients,
  }
}
