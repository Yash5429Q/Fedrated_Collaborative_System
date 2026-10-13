import {
  LayoutDashboard,
  Building2,
  GitBranch,
  ShieldAlert,
  BarChart3,
  Lock,
  TestTube,
  Crosshair,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  description: string
}

export const navigationItems: NavItem[] = [
  {
    label: 'Dashboard',
    path: '/',
    icon: LayoutDashboard,
    description: 'System overview and key metrics',
  },
  {
    label: 'Organizations',
    path: '/organizations',
    icon: Building2,
    description: 'Simulated organization clients',
  },
  {
    label: 'Federated Training',
    path: '/training',
    icon: GitBranch,
    description: 'Training rounds and model aggregation',
  },
  {
    label: 'Threat Detection',
    path: '/threats',
    icon: ShieldAlert,
    description: 'Threat classification results',
  },
  {
    label: 'Performance',
    path: '/performance',
    icon: BarChart3,
    description: 'Model metrics and analytics',
  },
  {
    label: 'Privacy & Security',
    path: '/privacy',
    icon: Lock,
    description: 'Privacy mechanisms and validation',
  },
  {
    label: 'Testing',
    path: '/testing',
    icon: TestTube,
    description: 'Validation and negative testing',
  },
  {
    label: 'Real-Time Predict',
    path: '/predict',
    icon: Crosshair,
    description: 'Real-time threat detection inference (Phase 16)',
  },
]
