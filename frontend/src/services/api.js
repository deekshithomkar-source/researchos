import axios from 'axios';

export const apiBaseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
export const apiRootUrl = apiBaseUrl.replace(/\/api\/?$/, '');

const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000,
});

export async function checkApiHealth() {
  const response = await axios.get(`${apiRootUrl}/`, { timeout: 5000 });
  return response.data;
}

export async function runResearch(payload) {
  const response = await api.post('/research/run', payload);
  return response.data;
}

export async function getHistory() {
  const response = await api.get('/research/history');
  return response.data;
}

export async function getResearchById(id) {
  const response = await api.get(`/research/${id}`);
  return response.data;
}
