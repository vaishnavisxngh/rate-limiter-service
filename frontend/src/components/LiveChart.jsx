/**
 * LiveChart.jsx
 * -------------
 * Line chart showing Total vs Blocked requests over time.
 *
 * Data source: /metrics/history  (array of { timestamp, total, blocked })
 * Update frequency: every 2 seconds (driven by App.jsx interval)
 *
 * Props
 * -----
 * history  array  – list of snapshot objects, chronological order
 */

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// Format Unix timestamp → HH:MM:SS for the X-axis labels
function formatTime(ts) {
  const d = new Date(ts * 1000)
  return d.toLocaleTimeString('en-US', { hour12: false })
}

// Custom tooltip that appears on hover
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map(entry => (
        <p key={entry.name} style={{ color: entry.color }} className="font-semibold">
          {entry.name}: {entry.value?.toLocaleString()}
        </p>
      ))}
    </div>
  )
}

export default function LiveChart({ history }) {
  // Transform the history array so Recharts can consume it
  const chartData = (history ?? []).map(snap => ({
    time: formatTime(snap.timestamp),
    'Total Requests': snap.total,
    'Blocked Requests': snap.blocked,
  }))

  const isEmpty = chartData.length === 0

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 p-5 h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-white font-semibold text-base">Request Activity</h2>
        <span className="text-xs text-gray-500">Updates every 2 s</span>
      </div>

      {isEmpty ? (
        // Placeholder before any data arrives
        <div className="flex items-center justify-center h-64 text-gray-600">
          <p>Fire some requests to see the chart populate…</p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
            <XAxis
              dataKey="time"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ color: '#9ca3af', fontSize: 12 }}
            />
            <Line
              type="monotone"
              dataKey="Total Requests"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="Blocked Requests"
              stroke="#ef4444"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
