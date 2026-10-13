/**
 * TypeScript interfaces for the Privacy & Security page.
 *
 * IMPORTANT: These types describe the *intended* privacy architecture.
 * No privacy mechanism (differential privacy, secure aggregation, etc.)
 * has been implemented yet. All status values are illustrative.
 *
 * Planned API mapping documented on each interface.
 */

/* ── Privacy principle / property ────────────────────────── */

export type PrivacyPropertyStatus = 'enforced' | 'planned' | 'not_implemented' | 'n/a'

export interface PrivacyProperty {
  id: string
  label: string
  category: 'data_locality' | 'model_update' | 'aggregation' | 'access_control'
  description: string
  status: PrivacyPropertyStatus
  detail: string           // honest detail about current implementation state
  planned: boolean         // true = will be implemented; false = already present by design
}

/* ── Per-org model update status ─────────────────────────── */

export type UpdateStatus = 'submitted' | 'pending' | 'rejected' | 'not_sent'

export interface OrgUpdateStatus {
  orgId: string
  orgName: string
  round: number
  updateStatus: UpdateStatus
  updateSize: string | null
  submittedAt: string | null
  validationPassed: boolean | null
  notes: string
}

/* ── Security event ───────────────────────────────────────── */

export type SecurityEventSeverity = 'info' | 'warning' | 'critical'
export type SecurityEventStatus   = 'resolved' | 'monitoring' | 'open'

export interface SecurityEvent {
  id: string
  timestamp: string
  organization: string | null   // null = system-level
  event: string
  category: string
  severity: SecurityEventSeverity
  status: SecurityEventStatus
  detail: string
}

/* ── Privacy flow step ───────────────────────────────────── */

export interface PrivacyFlowStep {
  id: string
  label: string
  sublabel: string
  implemented: boolean   // false = designed but not yet coded
  icon: string           // lucide icon name — resolved in component
}

/* ── Page summary ─────────────────────────────────────────── */

export interface PrivacyPageSummary {
  rawDataShared: boolean
  modelUpdatesOnly: boolean
  privacyMechanismsImplemented: number
  privacyMechanismsPlanned: number
  securityEventsLast24h: number
  unauthorizedAttemptsBlocked: number
}
