import type { OrgStatus } from './dashboard'

/* ── Training Pipeline Status ─────────────────────────────── */

export type TrainingPhase =
  | 'idle'
  | 'distributing'      // Sending global model to clients
  | 'local_training'    // Clients training locally
  | 'collecting'        // Collecting model updates
  | 'aggregating'       // Server aggregating updates
  | 'evaluating'        // Evaluating new global model
  | 'complete'

export type RoundStatus = 'completed' | 'in_progress' | 'failed' | 'skipped'

/* ── Per-client status within a round ─────────────────────── */

export type ClientTrainingStatus =
  | 'waiting'
  | 'downloading'
  | 'training'
  | 'uploading'
  | 'completed'
  | 'failed'
  | 'offline'

export interface ClientRoundStatus {
  orgId: string
  orgName: string
  orgStatus: OrgStatus
  clientStatus: ClientTrainingStatus
  localAccuracy: number | null
  localLoss: number | null
  samplesUsed: number
  duration: string | null
  updateSize: string | null
}

/* ── Round History Entry ──────────────────────────────────── */

export interface TrainingRound {
  round: number
  status: RoundStatus
  startedAt: string
  completedAt: string | null
  duration: string
  participatingClients: number
  totalClients: number
  globalAccuracy: number
  globalLoss: number
  globalF1: number
  globalModelVersion: string
  aggregationMethod: string
}

/* ── Client Participation (for chart) ─────────────────────── */

export interface ClientParticipation {
  round: number
  participating: number
  total: number
}

/* ── Training Page Summary ────────────────────────────────── */

export interface TrainingPageSummary {
  currentRound: number
  totalRounds: number
  trainingPhase: TrainingPhase
  globalModelVersion: string
  globalAccuracy: number
  globalLoss: number
  globalF1: number
  participatingClients: number
  totalClients: number
  avgRoundDuration: string
  aggregationMethod: string
  totalEpochsCompleted: number
}
