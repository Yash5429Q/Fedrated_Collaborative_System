/**
 * TypeScript interfaces for the Performance & Analytics page.
 * Planned API mapping documented on each interface.
 */

/* ── Single metric comparison (local vs federated) ────────── */

export interface MetricComparison {
  label: string
  local: number          // average across all orgs
  federated: number      // global model
  unit: string           // '%' | 'rate' | 'ms'
  higherIsBetter: boolean
}

/* ── Per-org performance row ─────────────────────────────── */

export interface OrgPerformanceRow {
  orgId: string
  orgName: string
  localAccuracy: number
  localF1: number
  localPrecision: number
  localRecall: number
  federatedAccuracy: number
  federatedF1: number
  gain: number           // federated - local accuracy
}

/* ── Non-IID experiment result ───────────────────────────── */

export interface NonIIDResult {
  scenario: string       // e.g. "Uniform (α=1.0)", "Skewed (α=0.1)"
  alpha: number          // Dirichlet concentration parameter
  localAvgAccuracy: number
  federatedAccuracy: number
  robustnessScore: number // 0–100
}

/* ── Confusion matrix cell ───────────────────────────────── */

export interface ConfusionCell {
  actual: string
  predicted: string
  value: number
}

export interface ConfusionMatrix {
  labels: string[]
  cells: ConfusionCell[]
  modelType: 'local' | 'federated'
}

/* ── Training-round metric (already in dashboard.ts, re-exported here for clarity) */

export interface PerfRoundMetric {
  round: number
  localAvgAccuracy: number   // average across orgs for that round's local models
  federatedAccuracy: number
  localAvgF1: number
  federatedF1: number
}

/* ── Collaboration benefit summary ───────────────────────── */

export interface CollaborationBenefit {
  metric: string
  localAvg: number
  federated: number
  improvement: number     // absolute delta
  improvementPct: number  // relative % improvement
}

/* ── Page-level summary ───────────────────────────────────── */

export interface PerformancePageSummary {
  federatedAccuracy: number
  localAvgAccuracy: number
  accuracyGain: number
  federatedF1: number
  localAvgF1: number
  f1Gain: number
  federatedFPR: number
  localAvgFPR: number
  fprReduction: number
  bestOrgName: string
  bestOrgGain: number
}

/* ── Experiment banner metadata ──────────────────────────── */

export interface PerformanceExperimentInfo {
  experimentId: string | null
  dataset: string | null
  alpha: number | null
  totalSamples: number | null
  rounds: number | null
  epochs: number | null
}
