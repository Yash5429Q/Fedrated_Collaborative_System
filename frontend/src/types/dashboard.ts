import type { LucideIcon } from 'lucide-react'

/* ── Summary / Stat Cards ────────────────────────────────── */

export interface StatCardData {
  label: string
  value: string | number
  icon: LucideIcon
  accent: string      // Tailwind text color class
  bgAccent: string    // Tailwind bg color class
  trend?: {
    value: string
    direction: 'up' | 'down' | 'flat'
  }
}

/* ── Training Performance ─────────────────────────────────── */

export interface TrainingRoundMetric {
  round: number
  accuracy: number
  /** False Positive Rate per round — stored as federated_fpr in the DB (no cross-entropy loss is stored) */
  fpr: number
  f1Score: number
}

/* ── Local vs Federated Comparison ────────────────────────── */

export interface ModelComparisonMetric {
  metric: string
  local: number
  federated: number
}

/* ── Threat Distribution ──────────────────────────────────── */

export interface ThreatCategory {
  category: string
  count: number
  color: string
}

/* ── Organization Activity ────────────────────────────────── */

export type OrgStatus = 'active' | 'training' | 'idle' | 'offline'

export interface OrganizationActivity {
  id: string
  name: string
  status: OrgStatus
  /** Round within the selected experiment; null when org was not an experiment participant */
  currentRound: number | null
  datasetSize: number | null    // null when not available from org_activity API
  lastUpdate: string
  contribution: number | null   // null when not available from org_activity API
  /** True if org participated in the selected experiment */
  isExperimentParticipant: boolean
}

/* ── Recent Threat Detections ─────────────────────────────── */

export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type DetectionStatus = 'detected' | 'blocked' | 'investigating' | 'resolved'

export interface ThreatDetection {
  id: string
  timestamp: string
  organization: string
  threatType: string
  severity: Severity
  confidence: number
  status: DetectionStatus
  modelVersion: string
}

/* ── System Health ────────────────────────────────────────── */

export type HealthStatus = 'operational' | 'degraded' | 'down' | 'unknown'

export interface SystemComponent {
  name: string
  status: HealthStatus
  latency?: string
  uptime?: string
  detail: string
}

/* ── Dashboard Summary ────────────────────────────────────── */

export interface DashboardSummary {
  totalOrganizations: number
  activeOrganizations: number
  /** Clients that participated in the selected experiment (may differ from totalOrganizations) */
  experimentClients: number
  currentRound: number
  totalRounds: number
  threatsDetected: number
  globalAccuracy: number
  f1Score: number
  falsePositiveRate: number
  privacyStatus: string
  privacyDetail: string | null
  experimentId: string | null
}
