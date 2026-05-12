/**
 * services/api.js
 * ---------------
 * Single source of truth for all backend API calls.
 * Every component imports from here — nowhere else talks to the backend directly.
 *
 * BASE_URL reads from the Vite environment variable VITE_API_URL.
 * - Locally:      set in .env.local  →  http://localhost:8001
 * - In Docker:    the Vite dev proxy handles /api, /metrics, /admin
 * - In production (Vercel): set VITE_API_URL to your Render backend URL
 */

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

// Read operations

/** Full metrics snapshot — used for initial load */
export const fetchMetrics = () =>
  api.get('/metrics/live').then(r => r.data)

/** Historical snapshots for the line chart */
export const fetchHistory = () =>
  api.get('/metrics/history').then(r => r.data)

/** Current algorithm configuration */
export const fetchConfig = () =>
  api.get('/admin/config').then(r => r.data)

/** Health check — used to determine if backend is reachable */
export const fetchHealth = () =>
  api.get('/health').then(r => r.data)

//Test request helpers

/**
 * Fire a single test request at the rate-limited endpoint.
 * @param {'token_bucket'|'sliding_window'} algorithm
 * @returns Promise resolving to { status, allowed, data }
 */
export const testRequest = async (algorithm = 'token_bucket') => {
  const endpoint = algorithm === 'sliding_window' ? '/api/data/sliding' : '/api/data'
  try {
    const response = await api.get(endpoint)
    return { status: response.status, allowed: true, data: response.data }
  } catch (error) {
    if (error.response?.status === 429) {
      return {
        status: 429,
        allowed: false,
        retryAfter: error.response.data?.detail?.retry_after ?? 0,
      }
    }
    throw error
  }
}

// ── Admin operations ───────────────────────────────────────────────────────

/**
 * Reset a single user's rate limit state.
 * @param {string} identifier  IP address string
 */
export const resetUser = (identifier) =>
  api.post(`/admin/reset/${identifier}`).then(r => r.data)

/** Wipe all rate-limit and metrics data. */
export const resetAll = () =>
  api.delete('/admin/reset-all').then(r => r.data)

/**
 * Push new algorithm config to all instances (stored in Redis).
 * @param {{ max_tokens: number, refill_rate: number, max_requests: number, window_seconds: number }} config
 */
export const updateConfig = (config) =>
  api.post('/admin/config', config).then(r => r.data)
