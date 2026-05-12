/**
 * TestPanel.jsx
 * -------------
 * Demo control panel — lets you fire N requests at the API with one click.
 * Perfect for live interview demos: show the dashboard live, fire 20 requests,
 * watch the chart update and users turn red in the table.
 *
 * Features
 * --------
 * - Choose number of requests to fire (default 15)
 * - Choose algorithm: Token Bucket or Sliding Window
 * - See allowed / blocked breakdown after firing
 * - Auto-Demo Mode: fires requests every 30 s automatically
 *
 * Props
 * -----
 * onFired  function  – called after requests complete so parent refreshes metrics
 */

import { useState, useEffect, useRef } from 'react'
import { Play, Zap, RefreshCw } from 'lucide-react'
import { testRequest } from '../services/api'

export default function TestPanel({ onFired }) {
  const [count, setCount] = useState(15)
  const [algorithm, setAlgorithm] = useState('token_bucket')
  const [firing, setFiring] = useState(false)
  const [result, setResult] = useState(null)       // { allowed, blocked }
  const [autoDemo, setAutoDemo] = useState(false)
  const autoDemoRef = useRef(null)

  // ── Auto-demo mode ──────────────────────────────────────────────────────
  useEffect(() => {
    if (autoDemo) {
      // Fire immediately, then every 30 s
      fireRequests()
      autoDemoRef.current = setInterval(() => fireRequests(), 30000)
    } else {
      clearInterval(autoDemoRef.current)
    }
    return () => clearInterval(autoDemoRef.current)
  }, [autoDemo, algorithm])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Core fire function ──────────────────────────────────────────────────
  const fireRequests = async () => {
    if (firing) return
    setFiring(true)
    setResult(null)

    let allowed = 0
    let blocked = 0

    // Fire all requests sequentially so the backend can track them per-IP
    for (let i = 0; i < count; i++) {
      try {
        const res = await testRequest(algorithm)
        if (res.allowed) allowed++
        else blocked++
      } catch {
        blocked++
      }
      // Small delay so the requests don't all arrive in one millisecond
      await new Promise(resolve => setTimeout(resolve, 50))
    }

    setResult({ allowed, blocked })
    setFiring(false)
    if (onFired) onFired()
  }

  const progress = result ? Math.round((result.allowed / (result.allowed + result.blocked)) * 100) : null

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Zap className="w-4 h-4 text-yellow-400" />
        <h2 className="text-white font-semibold text-base">Test Panel</h2>
        <span className="text-xs text-gray-500 ml-auto">Interview demo tool</span>
      </div>

      {/* Controls */}
      <div className="space-y-3 mb-4">

        {/* Request count */}
        <div>
          <label className="block text-gray-400 text-xs mb-1">Number of Requests</label>
          <input
            type="number"
            min={1}
            max={200}
            value={count}
            onChange={e => setCount(Math.max(1, parseInt(e.target.value) || 1))}
            disabled={firing}
            className="w-full bg-gray-800 border border-gray-700 text-white text-sm
                       rounded-lg px-3 py-2 focus:outline-none focus:border-yellow-500
                       disabled:opacity-50"
          />
        </div>

        {/* Algorithm selector */}
        <div>
          <label className="block text-gray-400 text-xs mb-1">Algorithm</label>
          <select
            value={algorithm}
            onChange={e => setAlgorithm(e.target.value)}
            disabled={firing}
            className="w-full bg-gray-800 border border-gray-700 text-white text-sm
                       rounded-lg px-3 py-2 focus:outline-none focus:border-yellow-500
                       disabled:opacity-50"
          >
            <option value="token_bucket">Token Bucket</option>
            <option value="sliding_window">Sliding Window</option>
          </select>
        </div>
      </div>

      {/* Fire button */}
      <button
        onClick={fireRequests}
        disabled={firing}
        className="w-full flex items-center justify-center gap-2
                   bg-yellow-600 hover:bg-yellow-500 text-black font-bold
                   py-2.5 rounded-lg transition-colors
                   disabled:opacity-50 disabled:cursor-not-allowed mb-3"
      >
        {firing ? (
          <>
            <RefreshCw className="w-4 h-4 animate-spin" />
            Firing {count} requests…
          </>
        ) : (
          <>
            <Play className="w-4 h-4" />
            Fire {count} Requests
          </>
        )}
      </button>

      {/* Auto-demo toggle */}
      <label className="flex items-center gap-2 cursor-pointer mb-4">
        <div
          onClick={() => setAutoDemo(v => !v)}
          className={`relative w-10 h-5 rounded-full transition-colors cursor-pointer
            ${autoDemo ? 'bg-yellow-600' : 'bg-gray-700'}`}
        >
          <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full
                          transition-transform ${autoDemo ? 'translate-x-5' : ''}`} />
        </div>
        <span className="text-gray-400 text-sm">
          Auto-Demo Mode {autoDemo && <span className="text-yellow-400">(every 30 s)</span>}
        </span>
      </label>

      {/* Result display */}
      {result && (
        <div className="bg-gray-800 rounded-lg p-4">
          <p className="text-gray-400 text-xs mb-2">Last batch result</p>
          <div className="flex gap-4 mb-3">
            <div className="text-center flex-1">
              <p className="text-2xl font-bold text-green-400">{result.allowed}</p>
              <p className="text-xs text-gray-500">✅ Allowed</p>
            </div>
            <div className="text-center flex-1">
              <p className="text-2xl font-bold text-red-400">{result.blocked}</p>
              <p className="text-xs text-gray-500">❌ Blocked</p>
            </div>
          </div>
          {/* Allowed vs blocked progress bar */}
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1 text-right">{progress}% allowed</p>
        </div>
      )}
    </div>
  )
}
