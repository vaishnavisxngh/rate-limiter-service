/**
 * UsersTable.jsx
 * --------------
 * Table showing every IP address that has made requests, with:
 *   - Total requests made
 *   - How many were blocked
 *   - Current token count remaining
 *   - ALLOWED / BLOCKED status badge
 *   - Per-row Reset button
 *
 * Props
 * -----
 * metrics      object    – live metrics payload
 * onRefresh    function  – called after a reset so parent re-fetches
 */

import { useState } from 'react'
import { Search, RotateCcw, ShieldCheck, ShieldOff } from 'lucide-react'
import { resetUser } from '../services/api'

function StatusBadge({ status }) {
  const isBlocked = status === 'BLOCKED'
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold
      ${isBlocked
        ? 'bg-red-900/50 text-red-400 border border-red-800'
        : 'bg-green-900/50 text-green-400 border border-green-800'}`}>
      {isBlocked
        ? <ShieldOff className="w-3 h-3" />
        : <ShieldCheck className="w-3 h-3" />}
      {status}
    </span>
  )
}

export default function UsersTable({ metrics, onRefresh }) {
  const [search, setSearch] = useState('')
  const [resettingId, setResettingId] = useState(null)
  const [resetFeedback, setResetFeedback] = useState({})   // { ip: 'Reset!' }

  const users = metrics?.users ?? []

  // Filter rows by search term
  const filtered = users.filter(u =>
    u.identifier.toLowerCase().includes(search.toLowerCase())
  )

  const handleReset = async (identifier) => {
    setResettingId(identifier)
    try {
      await resetUser(identifier)
      setResetFeedback(prev => ({ ...prev, [identifier]: '✓ Reset' }))
      setTimeout(() => {
        setResetFeedback(prev => { const n = { ...prev }; delete n[identifier]; return n })
      }, 2000)
      if (onRefresh) onRefresh()
    } catch (err) {
      setResetFeedback(prev => ({ ...prev, [identifier]: '✗ Error' }))
    } finally {
      setResettingId(null)
    }
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5">

      {/* Header row */}
      <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
        <h2 className="text-white font-semibold text-base">
          Active Users
          <span className="ml-2 text-xs text-gray-500 font-normal">({filtered.length} shown)</span>
        </h2>

        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Filter by IP…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-white text-sm rounded-lg
                       pl-9 pr-4 py-2 w-48 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-gray-400 text-left">
              <th className="pb-3 pr-4 font-medium">IP Address</th>
              <th className="pb-3 pr-4 font-medium text-right">Total</th>
              <th className="pb-3 pr-4 font-medium text-right">Blocked</th>
              <th className="pb-3 pr-4 font-medium text-right">Tokens Left</th>
              <th className="pb-3 pr-4 font-medium">Status</th>
              <th className="pb-3 font-medium">Action</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-600">
                  No users yet — fire some requests to see them appear here.
                </td>
              </tr>
            ) : (
              filtered.map(user => {
                const isBlocked = user.status === 'BLOCKED'
                return (
                  <tr
                    key={user.identifier}
                    className={`border-b border-gray-800/50 transition-colors
                      ${isBlocked ? 'bg-red-950/20' : 'hover:bg-gray-800/30'}`}
                  >
                    <td className="py-3 pr-4 font-mono text-gray-300">{user.identifier}</td>
                    <td className="py-3 pr-4 text-right text-white">{user.total_requests.toLocaleString()}</td>
                    <td className="py-3 pr-4 text-right text-red-400">{user.blocked_requests.toLocaleString()}</td>
                    <td className="py-3 pr-4 text-right">
                      <span className={isBlocked ? 'text-red-400' : 'text-green-400'}>
                        {user.tokens_remaining}
                      </span>
                    </td>
                    <td className="py-3 pr-4">
                      <StatusBadge status={user.status} />
                    </td>
                    <td className="py-3">
                      {resetFeedback[user.identifier] ? (
                        <span className="text-green-400 text-xs font-semibold">
                          {resetFeedback[user.identifier]}
                        </span>
                      ) : (
                        <button
                          onClick={() => handleReset(user.identifier)}
                          disabled={resettingId === user.identifier}
                          className="flex items-center gap-1 text-xs text-gray-400 hover:text-white
                                     bg-gray-800 hover:bg-gray-700 px-2 py-1 rounded transition-colors
                                     disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <RotateCcw className="w-3 h-3" />
                          Reset
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
