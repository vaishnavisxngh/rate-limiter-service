/**
 * StatsBar.jsx
 * ------------
 * Four summary cards shown at the top of the dashboard:
 *   1. Total Requests
 *   2. Blocked Requests
 *   3. Active Users
 *   4. Block Rate %
 *
 * Props
 * -----
 * metrics  object  – the live metrics payload from /metrics/live
 * loading  bool    – show skeleton placeholders while first fetch completes
 */

import { Activity, ShieldOff, Users, TrendingUp } from 'lucide-react'
import { motion } from 'framer-motion'

const CARDS = [
  {
    key: 'total_requests',
    label: 'Total Requests',
    icon: Activity,
    color: 'blue',
    format: v => v?.toLocaleString() ?? '—',
  },
  {
    key: 'blocked_requests',
    label: 'Blocked Requests',
    icon: ShieldOff,
    color: 'red',
    format: v => v?.toLocaleString() ?? '—',
  },
  {
    key: 'active_users',
    label: 'Active Users',
    icon: Users,
    color: 'green',
    format: v => v?.toLocaleString() ?? '—',
  },
  {
    key: 'block_rate_percent',
    label: 'Block Rate',
    icon: TrendingUp,
    color: 'yellow',
    format: v => v != null ? `${v.toFixed(1)} %` : '—',
  },
]

const COLOR_MAP = {
  blue:   { border: 'border-blue-500',   icon: 'text-blue-400',   bg: 'bg-blue-500/10' },
  red:    { border: 'border-red-500',    icon: 'text-red-400',    bg: 'bg-red-500/10' },
  green:  { border: 'border-green-500',  icon: 'text-green-400',  bg: 'bg-green-500/10' },
  yellow: { border: 'border-yellow-500', icon: 'text-yellow-400', bg: 'bg-yellow-500/10' },
}

function StatCard({ card, value, loading, index }) {
  const { border, icon: iconColor, bg } = COLOR_MAP[card.color]
  const Icon = card.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className={`bg-gray-900 rounded-xl border-l-4 ${border} p-5 flex items-center gap-4`}
    >
      {/* Icon circle */}
      <div className={`${bg} rounded-lg p-3 flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>

      {/* Numbers */}
      <div>
        {loading ? (
          <div className="h-7 w-20 bg-gray-700 rounded animate-pulse mb-1" />
        ) : (
          <p className="text-2xl font-bold text-white">{card.format(value)}</p>
        )}
        <p className="text-gray-400 text-sm">{card.label}</p>
      </div>
    </motion.div>
  )
}

export default function StatsBar({ metrics, loading }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {CARDS.map((card, i) => (
        <StatCard
          key={card.key}
          card={card}
          value={metrics?.[card.key]}
          loading={loading}
          index={i}
        />
      ))}
    </div>
  )
}
