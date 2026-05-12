/**
 * AdminPanel.jsx
 * --------------
 * Two sections:
 *   1. Rate Limit Config  – live-update algorithm parameters via /admin/config
 *   2. Danger Zone        – reset all users via /admin/reset-all
 *
 * Props
 * -----
 * onRefresh  function  – called after a reset so parent re-fetches metrics
 */

import { useEffect, useState } from 'react'
import { Settings, Trash2, Save, AlertTriangle } from 'lucide-react'
import { fetchConfig, updateConfig, resetAll } from '../services/api'

export default function AdminPanel({ onRefresh }) {
  const [config, setConfig] = useState({
    max_tokens: 10,
    refill_rate: 0.1,
    max_requests: 10,
    window_seconds: 60,
  })
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [resetting, setResetting] = useState(false)
  const [resetMsg, setResetMsg] = useState('')

  // Load current config on mount
  useEffect(() => {
    fetchConfig()
      .then(data => setConfig(data))
      .catch(console.error)
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setSaveMsg('')
    try {
      await updateConfig(config)
      setSaveMsg('✓ Config applied to all instances')
    } catch {
      setSaveMsg('✗ Failed to save config')
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMsg(''), 3000)
    }
  }

  const handleResetAll = async () => {
    const confirmed = window.confirm(
      '⚠️  This will delete ALL rate-limit data and metrics.\n\nAre you sure?'
    )
    if (!confirmed) return

    setResetting(true)
    setResetMsg('')
    try {
      const result = await resetAll()
      setResetMsg(`✓ Cleared ${result.keys_deleted} keys`)
      if (onRefresh) onRefresh()
    } catch {
      setResetMsg('✗ Reset failed')
    } finally {
      setResetting(false)
      setTimeout(() => setResetMsg(''), 3000)
    }
  }

  const field = (label, key, step = 1, min = 0) => (
    <div>
      <label className="block text-gray-400 text-xs mb-1">{label}</label>
      <input
        type="number"
        step={step}
        min={min}
        value={config[key]}
        onChange={e => setConfig(prev => ({ ...prev, [key]: parseFloat(e.target.value) }))}
        className="w-full bg-gray-800 border border-gray-700 text-white text-sm
                   rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
      />
    </div>
  )

  return (
    <div className="grid md:grid-cols-2 gap-4">

      {/* ── Config section ──────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-4 h-4 text-blue-400" />
          <h2 className="text-white font-semibold text-base">Rate Limit Config</h2>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-4">
          {field('Max Tokens (bucket)', 'max_tokens', 1, 1)}
          {field('Refill Rate (tokens/s)', 'refill_rate', 0.01, 0.01)}
          {field('Max Requests (window)', 'max_requests', 1, 1)}
          {field('Window Seconds', 'window_seconds', 1, 1)}
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white
                     text-sm font-semibold px-4 py-2 rounded-lg transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Applying…' : 'Apply Config'}
        </button>

        {saveMsg && (
          <p className={`mt-2 text-sm ${saveMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
            {saveMsg}
          </p>
        )}
      </div>

      {/* ── Danger Zone ─────────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl border border-red-900/50 p-5">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <h2 className="text-red-400 font-semibold text-base">Danger Zone</h2>
          <span className="text-xs bg-red-900/40 text-red-400 border border-red-800 px-2 py-0.5 rounded">
            ADMIN
          </span>
        </div>

        <p className="text-gray-500 text-sm mb-4">
          Permanently deletes all rate-limit counters and metrics from Redis.
          All instances are affected immediately.
        </p>

        <button
          onClick={handleResetAll}
          disabled={resetting}
          className="flex items-center gap-2 bg-red-700 hover:bg-red-600 text-white
                     text-sm font-semibold px-4 py-2 rounded-lg transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 className="w-4 h-4" />
          {resetting ? 'Resetting…' : 'Reset All Users'}
        </button>

        {resetMsg && (
          <p className={`mt-2 text-sm ${resetMsg.startsWith('✓') ? 'text-green-400' : 'text-red-400'}`}>
            {resetMsg}
          </p>
        )}
      </div>
    </div>
  )
}
