import type { LucideIcon } from 'lucide-react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string | number
  icon: LucideIcon
  accent: string
  bgAccent: string
  trend?: {
    value: string
    direction: 'up' | 'down' | 'flat'
  }
}

const trendConfig = {
  up:   { icon: TrendingUp,   color: 'text-accent-green' },
  down: { icon: TrendingDown, color: 'text-accent-red' },
  flat: { icon: Minus,        color: 'text-gray-500' },
} as const

export default function StatCard({
  label,
  value,
  icon: Icon,
  accent,
  bgAccent,
  trend,
}: StatCardProps) {
  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-gray-500">
          {label}
        </span>
        <div className={`rounded-md p-1.5 ${bgAccent}`}>
          <Icon className={`h-4 w-4 ${accent}`} />
        </div>
      </div>
      <div className="mt-2 flex items-end gap-2">
        <p className="text-2xl font-semibold text-gray-100">{value}</p>
        {trend && (
          <span className={`mb-0.5 flex items-center gap-0.5 text-xs font-medium ${trendConfig[trend.direction].color}`}>
            {(() => {
              const TrendIcon = trendConfig[trend.direction].icon
              return <TrendIcon className="h-3 w-3" />
            })()}
            {trend.value}
          </span>
        )}
      </div>
    </div>
  )
}
