import axios from 'axios';
import { resolveApiRoot } from './api-url.js';

export const apiRootUrl = resolveApiRoot(
  import.meta.env.VITE_API_URL,
  typeof window !== 'undefined' ? window.location.href : 'http://127.0.0.1:5173',
  import.meta.env.DEV,
);
export const apiBaseUrl = `${apiRootUrl}/api`;

// Only the CSRF token lives in memory. The session credential is an HttpOnly cookie.
let csrfToken = null;
const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 15000,
  withCredentials: true,
  headers: { 'X-ResearchOS-Client': 'web' },
});
api.interceptors.request.use((config) => {
  if (csrfToken && !['get', 'head', 'options'].includes(config.method)) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

export async function checkApiHealth(options = {}) {
  const response = await axios.get(`${apiRootUrl}/`, { timeout: 5000, ...options });
  return response.data;
}
export async function runResearch(payload) {
  return (await api.post('/research', payload)).data;
}
export async function getHistory(options = {}) {
  return (await api.get('/research/history', options)).data;
}
export async function getResearchById(id, options = {}) {
  return (await api.get(`/research/${encodeURIComponent(id)}`, options)).data;
}
async function authenticate(path, payload) {
  const { data } = await api.post(path, payload);
  csrfToken = data.csrf_token;
  return data;
}
export const signupUser = (payload) => authenticate('/auth/signup', payload);
export const signinUser = (payload) => authenticate('/auth/signin', payload);
export async function getCurrentUser(options = {}) {
  const { data } = await api.get('/auth/me', options);
  csrfToken = data.csrf_token;
  return data;
}
export async function signoutUser() {
  await api.post('/auth/signout');
  csrfToken = null;
}
export async function resetUserPassword(payload) {
  return (await api.post('/auth/reset-password', payload)).data;
}
export function apiErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(' ');
  return fallback;
}

export async function getIntelligence(id, options = {}) {
  return (await api.get(`/research/${encodeURIComponent(id)}/intelligence`, options)).data;
}
export async function generateIntelligence(id, options = {}) {
  return (await api.post(`/research/${encodeURIComponent(id)}/intelligence`, {}, { timeout: 90000, ...options })).data;
}

export async function exportResearchReport(id, format) {
  const response = await api.get(`/research/${encodeURIComponent(id)}/report/export/${format}`, { responseType: 'blob', timeout: 60000 });
  return response.data;
}
