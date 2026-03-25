import axios from 'axios'

const BASE = ''  // proxied by vite dev server

export const api = {
  // ── Demo / Patients ────────────────────────────────────────
  loadDemo: (simOffsetMinutes = 0) =>
    axios.post(`/api/patients/load-demo?sim_offset_minutes=${simOffsetMinutes}`),

  getQueue: (simOffsetMinutes = 0) =>
    axios.get(`/api/patients/rescore?sim_offset_minutes=${simOffsetMinutes}`),

  addPatient: (data) =>
    axios.post('/admit', data),

  clearPatients: () =>
    axios.delete('/api/patients'),

  // ── Simulation ─────────────────────────────────────────────
  simulate: (totalMinutes = 90) =>
    axios.get(`/api/patients/simulate?total_minutes=${totalMinutes}`),

  whatif: (futureMinutes = 60, simOffset = 0) =>
    axios.get(`/api/patients/whatif?future_minutes=${futureMinutes}&sim_offset_minutes=${simOffset}`),

  timelapse: (stepMinutes = 10, totalMinutes = 120) =>
    axios.get(`/api/patients/timelapse?step_minutes=${stepMinutes}&total_minutes=${totalMinutes}`),

  // ── Alerts ────────────────────────────────────────────────
  getAlerts: () =>
    axios.get('/api/alerts'),

  acknowledgeAlert: (alertId) =>
    axios.patch(`/api/alerts/${alertId}/acknowledge`),

  // ── Categories ────────────────────────────────────────────
  getCategories: () =>
    axios.get('/api/categories'),

  // ── Health ────────────────────────────────────────────────
  health: () =>
    axios.get('/api/health'),
}
