import type { Severity, DetectionStatus } from './dashboard'

/* ── Extended threat detection for detail view ────────────── */

export interface ThreatDetectionDetail {
  id: string
  timestamp: string
  organization: string
  organizationId: string
  threatType: string
  severity: Severity
  confidence: number
  status: DetectionStatus
  modelVersion: string
  sourceIP: string
  destinationIP: string
  protocol: string
  port: number
  description: string
  rawFeatures: Record<string, number>
  detectionMethod: 'federated' | 'local'
}

/* ── Threat page summary ──────────────────────────────────── */

export interface ThreatPageSummary {
  total: number
  critical: number
  high: number
  medium: number
  low: number
  blocked: number
  investigating: number
  avgConfidence: number
}

/* ── Timeline data point ──────────────────────────────────── */

export interface ThreatTimelinePoint {
  hour: string
  critical: number
  high: number
  medium: number
  low: number
}

/* ── Distribution entry ───────────────────────────────────── */

export interface ThreatTypeCount {
  type: string
  count: number
  color: string
}
