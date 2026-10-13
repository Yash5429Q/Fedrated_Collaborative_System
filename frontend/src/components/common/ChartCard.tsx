import type { ReactNode } from 'react'

interface ChartCardProps {
  title: string
  subtitle?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}

export default function ChartCard({
  title,
  subtitle,
  children,
  action,
  className = '',
}: ChartCardProps) {
  return (
    <div className={`rounded-lg border border-cyber-700/50 bg-cyber-900 ${className}`}>
      <div className="flex items-start justify-between border-b border-cyber-700/30 px-5 py-4">
        <div>
          <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>
          )}
        </div>
        {action && <div>{action}</div>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  )
}
