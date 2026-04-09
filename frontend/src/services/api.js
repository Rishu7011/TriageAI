import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || (import.meta.env.PROD ? 'https://triageai-backend.onrender.com' : 'http://localhost:8000'),
  timeout: 10000,
});

// Generic simulate function called by the UI
export const simulateTime = async (minutes) => {
  return await api.post(`/api/simulate?minutes=${minutes}`);
};

// Load demo patients into the queue
export const loadDemoData = async () => {
  return await api.post('/api/patients/load-demo');
};

// Admit a single patient
export const admitPatient = async (patientData) => {
  return await api.post('/api/patients', patientData);
};

export default api;
