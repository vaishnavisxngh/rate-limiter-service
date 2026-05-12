/**
 * App.jsx
 * -------
 * Root component. Owns the data-fetching loop and passes data down
 * to every child component as props.
 *
 * Data flow
 * ---------
 * App → fetches /metrics/live every 2 s → passes `metrics` to children
 * App → fetches /metrics/history every 2 s → passes `history` to LiveChart
 *
 * Layout (top to bottom)
 * -----------------------
 * <Header />
 * <StatsBar />
 * <LiveChart />   <TestPanel />      (two-column grid)
 * <UsersTable />
 * <AdminPanel />
 */

import { useEffect, useState, useCallback } from 'react'
import Header from './components/Header'
import StatsBar from './components/StatsBar'
import LiveChart from './components/LiveChart'
import UsersTable from './components/UsersTable'
import AdminPanel from './components/AdminPanel'
import TestPanel from './components/TestPanel'
import { fetchMetrics, fetchHistory } from './services/api'

const POLL_INTERVAL_MS = 2000   // how often the dashboard refreshes

export default function App() {
  const [metrics, setMetrics] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // ── Data fetching ────────────────────────────────────────────────────────
  const refresh = useCallback(async () => {
    try {
      const [m, h] = await Promise.all([fetchMetrics(), fetchHistory()])
      setMetrics(m)
      setHistory(h.history ?? [])
      setError(null)
    } catch (err) {
      setError('Cannot reach backend. Is Docker running?')
      console.error('Fetch error:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, POLL_INTERVAL_MS)
    // Cleanup: stop polling when component unmounts
    return () => clearInterval(interval)
  }, [refresh])

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gray-950 text-white">

      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-4">

        {/* Error banner */}
        {error && (
          <div className="bg-red-900/40 border border-red-800 text-red-300 rounded-xl px-5 py-3 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* ── Row 1: Stats cards ──────────────────────────────────────── */}
        <StatsBar metrics={metrics} loading={loading} />

        {/* ── Row 2: Chart + Test Panel ───────────────────────────────── */}
        <div className="grid lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <LiveChart history={history} />
          </div>
          <div>
            <TestPanel onFired={refresh} />
          </div>
        </div>

        {/* ── Row 3: Users table ──────────────────────────────────────── */}
        <UsersTable metrics={metrics} onRefresh={refresh} />

        {/* ── Row 4: Admin panel ──────────────────────────────────────── */}
        <AdminPanel onRefresh={refresh} />

      </main>

      {/* Footer */}
      <footer className="text-center text-gray-700 text-xs py-6">
        Distributed Rate Limiter Service · Built with FastAPI + Redis + React
      </footer>
    </div>
  )
}
