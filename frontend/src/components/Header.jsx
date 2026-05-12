/**
 * Header.jsx
 * ----------
 * Top navigation bar showing:
 *   - Project name + icon
 *   - Live/Offline status indicator (polls /health every 5 s)
 *   - Instance switcher dropdown (Instance 1 vs Instance 2)
 *
 * The instance switcher changes the VITE_API_URL used by all subsequent
 * API calls by reloading the page with a different base URL stored in
 * sessionStorage.  This lets interviewers see that BOTH instances are
 * enforcing the same limits via shared Redis.
 */

import { useEffect, useState } from 'react'
import { Zap, Wifi, WifiOff, ChevronDown } from 'lucide-react'
import { fetchHealth } from '../services/api'

const INSTANCES = [
  { label: 'Instance 1', url: 'http://localhost:8001' },
  { label: 'Instance 2', url: 'http://localhost:8002' },
]

export default function Header({ onInstanceChange }) {
  const [isOnline, setIsOnline] = useState(true)
  const [instanceIndex, setInstanceIndex] = useState(0)
  const [dropdownOpen, setDropdownOpen] = useState(false)

  // Poll /health every 5 seconds to update the status indicator
  useEffect(() => {
    const check = async () => {
      try {
        await fetchHealth()
        setIsOnline(true)
      } catch {
        setIsOnline(false)
      }
    }

    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleInstanceSwitch = (index) => {
    setInstanceIndex(index)
    setDropdownOpen(false)
    if (onInstanceChange) onInstanceChange(INSTANCES[index].url)
  }

  return (
    <header className="w-full bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">

      {/* ── Left: brand ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="bg-blue-600 rounded-lg p-2">
          <Zap className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-white font-bold text-lg leading-none">RateLimiter</h1>
          <p className="text-gray-400 text-xs mt-0.5">Distributed Service Dashboard</p>
        </div>
      </div>

      {/* ── Right: status + instance switcher ───────────────────────── */}
      <div className="flex items-center gap-4">

        {/* Live / Offline pill */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold
          ${isOnline ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'}`}>
          {isOnline ? (
            <>
              {/* Pulsing green dot */}
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
              <Wifi className="w-3 h-3" />
              LIVE
            </>
          ) : (
            <>
              <span className="h-2 w-2 rounded-full bg-red-500" />
              <WifiOff className="w-3 h-3" />
              OFFLINE
            </>
          )}
        </div>

        {/* Instance dropdown */}
        <div className="relative">
          <button
            onClick={() => setDropdownOpen(v => !v)}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-white
                       text-sm px-3 py-1.5 rounded-lg border border-gray-700 transition-colors"
          >
            {INSTANCES[instanceIndex].label}
            <ChevronDown className="w-4 h-4 text-gray-400" />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-36 bg-gray-800 border border-gray-700
                            rounded-lg shadow-xl z-50 overflow-hidden">
              {INSTANCES.map((inst, idx) => (
                <button
                  key={inst.label}
                  onClick={() => handleInstanceSwitch(idx)}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors
                    ${idx === instanceIndex
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-700'}`}
                >
                  {inst.label}
                  <span className="block text-xs opacity-60">{inst.url.split('//')[1]}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
