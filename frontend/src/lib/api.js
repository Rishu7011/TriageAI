import axios from 'axios'

const API = axios.create({ baseURL: '/api', timeout: 15000 })

export const getHealth    = ()                               => API.get('/health').then(r => r.data)
export const loadDemo     = (simOffset = 0)                  => API.post(`/patients/load-demo?sim_offset_minutes=${simOffset}`).then(r => r.data)
export const rescore      = (simOffset = 0)                  => API.get(`/patients/rescore?sim_offset_minutes=${simOffset}`).then(r => r.data)
export const addPatient   = (intake)                         => API.post('/patients', intake).then(r => r.data)
export const clearPatients= ()                               => API.delete('/patients').then(r => r.data)
export const simulate     = (totalMinutes = 90)              => API.get(`/patients/simulate?total_minutes=${totalMinutes}`).then(r => r.data)
export const whatIf       = (futureMin, simOffset = 0)       => API.get(`/patients/whatif?future_minutes=${futureMin}&sim_offset_minutes=${simOffset}`).then(r => r.data)
export const timelapse    = (step = 10, total = 120)         => API.get(`/patients/timelapse?step_minutes=${step}&total_minutes=${total}`).then(r => r.data)
export const getCategories= ()                               => API.get('/categories').then(r => r.data)
