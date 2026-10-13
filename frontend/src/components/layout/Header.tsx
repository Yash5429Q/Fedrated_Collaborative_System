import { useLocation } from 'react-router-dom'
import { Activity, Bell } from 'lucide-react'
import { navigationItems } from '@/config/navigation'

export default function Header() {
  const location = useLocation()

  const currentPage = navigationItems.find(
    (item) => item.path === location.pathname
  )

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-cyber-700/50 bg-cyber-900/80 px-6 backdrop-blur-sm">
      {/* Page title */}
      <div>
        <h1 className="text-lg font-semibold text-gray-100">
          {currentPage?.label ?? 'CYBER-20'}
        </h1>
        {currentPage?.description && (
          <p className="text-xs text-gray-500">{currentPage.description}</p>
        )}
      </div>

      {/* Right section — system status indicators */}
      <div className="flex items-center gap-4">
        {/* System status indicator */}
        <div className="flex items-center gap-2 rounded-md border border-cyber-700/50 bg-cyber-800/50 px-3 py-1.5">
          <Activity className="h-3.5 w-3.5 text-accent-green" />
          <span className="text-xs font-medium text-gray-400">
            System Idle
          </span>
        </div>

        {/* Notifications placeholder */}
        <button
          className="relative rounded-md p-2 text-gray-500 transition-colors hover:bg-cyber-800 hover:text-gray-300"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
        </button>
      </div>
    </header>
  )
}
