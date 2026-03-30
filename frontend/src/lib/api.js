import axios from 'axios'

/**
 * Single source of truth for the API base URL.
 *
 * Vite automatically loads:
 *   .env.development  → used by `vite dev`   (VITE_API_BASE_URL=http://localhost:8000)
 *   .env              → used by `vite build`  (VITE_API_BASE_URL=https://triageai-backend.onrender.com)
 *
 * You can also override at any time by setting VITE_API_BASE_URL in a .env.local file.
 */
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'https://triageai-backend.onrender.com'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

export const api = {
  // ── Demo / Patients ────────────────────────────────────────
  loadDemo: (simOffsetMinutes = 0) =>
    apiClient.post(`/api/patients/load-demo?sim_offset_minutes=${simOffsetMinutes}`),

  getQueue: (simOffsetMinutes = 0) =>
    apiClient.get(`/api/patients/rescore?sim_offset_minutes=${simOffsetMinutes}`),

  addPatient: (data) =>
    apiClient.post('/admit', data),

  clearPatients: () =>
    apiClient.delete('/api/patients'),

  // ── Simulation ─────────────────────────────────────────────
  simulate: (totalMinutes = 90) =>
    apiClient.get(`/api/patients/simulate?total_minutes=${totalMinutes}`),

  whatif: (futureMinutes = 60, simOffset = 0) =>
    apiClient.get(`/api/patients/whatif?future_minutes=${futureMinutes}&sim_offset_minutes=${simOffset}`),

  timelapse: (stepMinutes = 10, totalMinutes = 120) =>
    apiClient.get(`/api/patients/timelapse?step_minutes=${stepMinutes}&total_minutes=${totalMinutes}`),

  // ── Alerts ────────────────────────────────────────────────
  getAlerts: () =>
    apiClient.get('/api/alerts'),

  acknowledgeAlert: (alertId) =>
    apiClient.patch(`/api/alerts/${alertId}/acknowledge`),

  // ── Categories ────────────────────────────────────────────
  getCategories: () =>
    apiClient.get('/api/categories'),

  // ── Health ────────────────────────────────────────────────
  health: () =>
    apiClient.get('/api/health'),
}
