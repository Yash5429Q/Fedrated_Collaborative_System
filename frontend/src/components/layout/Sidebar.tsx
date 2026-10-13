import { NavLink } from 'react-router-dom'
import { Shield, PanelLeftClose, PanelLeft } from 'lucide-react'
import { navigationItems } from '@/config/navigation'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={`
        fixed left-0 top-0 z-40 flex h-screen flex-col
        border-r border-cyber-700/50 bg-cyber-900
        transition-[width] duration-300
        ${collapsed ? 'w-16' : 'w-60'}
      `}
    >
      {/* Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-cyber-700/50 px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-cyan/10">
          <Shield className="h-5 w-5 text-accent-cyan" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <span className="text-sm font-semibold tracking-wide text-gray-100">
              CYBER-20
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4">
        <ul className="space-y-1">
          {navigationItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                title={collapsed ? item.label : undefined}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent-cyan/10 text-accent-cyan'
                      : 'text-gray-400 hover:bg-cyber-800 hover:text-gray-200'
                  }`
                }
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-cyber-700/50 p-2">
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-md p-2 text-gray-500 transition-colors hover:bg-cyber-800 hover:text-gray-300"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <PanelLeft className="h-5 w-5" />
          ) : (
            <PanelLeftClose className="h-5 w-5" />
          )}
        </button>
      </div>
    </aside>
  )
}
