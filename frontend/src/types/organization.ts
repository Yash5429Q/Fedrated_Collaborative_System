import type { OrgStatus } from './dashboard'

/* ── Data Distribution ────────────────────────────────────── */

export interface DataDistributionSlice {
  threatType: string
  percentage: number
  count: number
  color: string
}

/* ── Local Model Info ─────────────────────────────────────── */

export type ModelStatus = 'trained' | 'training' | 'pending' | 'failed'

export interface LocalModelInfo {
  status: ModelStatus
  version: string
  accuracy: number | null
  loss: number | null       // null when not available from API
  lastTrained: string
  epochs: number
}

/* ── Training History Entry ───────────────────────────────── */

export interface OrgTrainingRound {
  round: number
  participated: boolean
  localAccuracy: number
  localLoss: number | null  // null when not available from API
  samplesUsed: number
  duration: string
}

/* ── Full Organization Detail ─────────────────────────────── */

export interface Organization {
  id: string
  name: string
  description: string
  status: OrgStatus
  datasetSize: number
  datasetSplit: string            // e.g. "Train 80% / Test 20%"
  localModel: LocalModelInfo
  currentRound: number | null
  totalRounds: number | null
  lastUpdate: string
  joinedAt: string
  contribution: number            // percentage of rounds participated
  threatsDetected: number | null  // null when not yet tracked per-org
  dataDistribution: DataDistributionSlice[]
  trainingHistory: OrgTrainingRound[]
  privacyMode: string
  networkLatency: string
}

/* ── Organization Summary (for top-level stats) ───────────── */

export interface OrgPageSummary {
  total: number
  active: number
  training: number
  idle: number
  offline: number
  totalDataPoints: number
  avgAccuracy: number
  avgContribution: number
}
