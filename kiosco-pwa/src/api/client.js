/**
 * Axios instance configured for the Frappe backend.
 *
 * In dev mode, Vite proxies /api → http://localhost:8080.
 * In production, the PWA is served from the same origin.
 *
 * CSRF is disabled server-side for gcma_kiosco endpoints via
 * a before_request hook (the PWA is served from a different origin).
 */
import axios from 'axios'

const client = axios.create({
  baseURL: '/',
  headers: {
    Accept: 'application/json',
    'Cache-Control': 'no-store, no-cache, must-revalidate',
    Pragma: 'no-cache',
  },
  withCredentials: true,
  timeout: 15_000,
})

// Frappe whitelist endpoints expect application/x-www-form-urlencoded for POST.
// Convert plain objects to URLSearchParams automatically.
client.interceptors.request.use((config) => {
  if (config.data && typeof config.data === 'object' && !(config.data instanceof URLSearchParams)) {
    config.data = new URLSearchParams(config.data).toString()
    config.headers['Content-Type'] = 'application/x-www-form-urlencoded'
  }
  return config
})

// Unwrap Frappe's { message: {...} } envelope
client.interceptors.response.use(
  (res) => res.data?.message ?? res.data,
  (err) => {
    const payload = err.response?.data?.message ?? err.response?.data
    return Promise.reject(payload ?? err)
  },
)

export default client
