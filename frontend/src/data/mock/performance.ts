/**
 * Mock data for the Performance & Analytics page.
 *
 * ⚠ ALL VALUES ARE DEMO/MOCK DATA — placeholder until real experiment
 *   results are produced by the ML training pipeline.
 *
 * Planned API mapping:
 *   mockPerfSummary          → GET /api/performance/summary
 *   mockMetricComparisons    → GET /api/performance/comparison
 *   mockOrgPerformance       → GET /api/performance/organizations
 *   mockNonIIDResults        → GET /api/performance/noniid
 *   mockPerfRounds           → GET /api/performance/rounds
 *   mockCollaborationBenefit → GET /api/performance/benefit
 *   mockConfusionMatrices    → GET /api/performance/confusion
 */

import type {
  PerformancePageSummary,
  MetricComparison,
  OrgPerformanceRow,
  NonIIDResult,
  PerfRoundMetric,
  CollaborationBenefit,
  ConfusionMatrix,
} from '@/types/performance'

/* ── Page summary ─────────────────────────────────────────── */

export const mockPerfSummary: PerformancePageSummary = {
  federatedAccuracy:  94.7,
  localAvgAccuracy:   84.7,
  accuracyGain:       10.0,
  federatedF1:        92.3,
  localAvgF1:         81.5,
  f1Gain:             10.8,
  federatedFPR:        3.2,
  localAvgFPR:         8.6,
  fprReduction:        5.4,
  bestOrgName:        'Organization Alpha',
  bestOrgGain:        6.5,
}

/* ── Metric comparisons (local avg vs federated) ──────────── */

export const mockMetricComparisons: MetricComparison[] = [
  { label: 'Accuracy',               local: 84.7, federated: 94.7, unit: '%',    higherIsBetter: true  },
  { label: 'Precision',              local: 82.1, federated: 92.8, unit: '%',    higherIsBetter: true  },
  { label: 'Recall',                 local: 80.4, federated: 91.9, unit: '%',    higherIsBetter: true  },
  { label: 'F1 Score',               local: 81.5, federated: 92.3, unit: '%',    higherIsBetter: true  },
  { label: 'False-Positive Rate',    local:  8.6, federated:  3.2, unit: '%',    higherIsBetter: false },
  { label: 'Attack Detection Rate',  local: 79.2, federated: 93.1, unit: '%',    higherIsBetter: true  },
  { label: 'Non-IID Robustness',     local: 61.3, federated: 87.4, unit: 'score',higherIsBetter: true  },
  { label: 'Collaboration Benefit',  local:  0.0, federated: 10.0, unit: '%',    higherIsBetter: true  },
]

/* ── Per-organization performance ─────────────────────────── */

export const mockOrgPerformance: OrgPerformanceRow[] = [
  {
    orgId:              'org-alpha',
    orgName:            'Organization Alpha',
    localAccuracy:      88.2,
    localF1:            86.3,
    localPrecision:     87.1,
    localRecall:        85.6,
    federatedAccuracy:  94.7,
    federatedF1:        92.3,
    gain:                6.5,
  },
  {
    orgId:              'org-beta',
    orgName:            'Organization Beta',
    localAccuracy:      83.7,
    localF1:            81.9,
    localPrecision:     82.4,
    localRecall:        81.4,
    federatedAccuracy:  94.7,
    federatedF1:        92.3,
    gain:               11.0,
  },
  {
    orgId:              'org-gamma',
    orgName:            'Organization Gamma',
    localAccuracy:      85.9,
    localF1:            83.7,
    localPrecision:     84.2,
    localRecall:        83.2,
    federatedAccuracy:  94.7,
    federatedF1:        92.3,
    gain:                8.8,
  },
  {
    orgId:              'org-delta',
    orgName:            'Organization Delta',
    localAccuracy:      81.3,
    localF1:            79.4,
    localPrecision:     80.1,
    localRecall:        78.7,
    federatedAccuracy:  94.7,
    federatedF1:        92.3,
    gain:               13.4,
  },
  {
    orgId:              'org-epsilon',
    orgName:            'Organization Epsilon',
    localAccuracy:      79.2,
    localF1:            77.1,
    localPrecision:     77.8,
    localRecall:        76.4,
    federatedAccuracy:  94.7,
    federatedF1:        92.3,
    gain:               15.5,
  },
]

/* ── Non-IID experiment results ───────────────────────────── */

export const mockNonIIDResults: NonIIDResult[] = [
  { scenario: 'Uniform (IID)',         alpha: 100.0, localAvgAccuracy: 88.4, federatedAccuracy: 94.7, robustnessScore: 96 },
  { scenario: 'Mild Skew (α = 1.0)',   alpha:   1.0, localAvgAccuracy: 85.9, federatedAccuracy: 93.8, robustnessScore: 89 },
  { scenario: 'Moderate (α = 0.5)',    alpha:   0.5, localAvgAccuracy: 84.7, federatedAccuracy: 92.4, robustnessScore: 83 },
  { scenario: 'Heavy Skew (α = 0.1)', alpha:   0.1, localAvgAccuracy: 78.3, federatedAccuracy: 89.1, robustnessScore: 74 },
  { scenario: 'Extreme (α = 0.01)',   alpha:  0.01, localAvgAccuracy: 68.1, federatedAccuracy: 84.6, robustnessScore: 61 },
]

/* ── Round-by-round metrics ───────────────────────────────── */

export const mockPerfRounds: PerfRoundMetric[] = [
  { round:  1, localAvgAccuracy: 64.3, federatedAccuracy: 68.2, localAvgF1: 61.1, federatedF1: 62.1 },
  { round:  2, localAvgAccuracy: 68.7, federatedAccuracy: 73.5, localAvgF1: 65.8, federatedF1: 69.8 },
  { round:  3, localAvgAccuracy: 72.4, federatedAccuracy: 78.1, localAvgF1: 69.7, federatedF1: 74.5 },
  { round:  4, localAvgAccuracy: 75.1, federatedAccuracy: 81.4, localAvgF1: 72.8, federatedF1: 78.2 },
  { round:  5, localAvgAccuracy: 77.8, federatedAccuracy: 84.6, localAvgF1: 75.3, federatedF1: 81.9 },
  { round:  6, localAvgAccuracy: 79.6, federatedAccuracy: 87.0, localAvgF1: 77.4, federatedF1: 84.3 },
  { round:  7, localAvgAccuracy: 81.2, federatedAccuracy: 89.2, localAvgF1: 79.0, federatedF1: 86.8 },
  { round:  8, localAvgAccuracy: 82.4, federatedAccuracy: 90.8, localAvgF1: 80.2, federatedF1: 88.6 },
  { round:  9, localAvgAccuracy: 83.3, federatedAccuracy: 92.1, localAvgF1: 81.1, federatedF1: 89.9 },
  { round: 10, localAvgAccuracy: 84.0, federatedAccuracy: 93.3, localAvgF1: 81.8, federatedF1: 91.0 },
  { round: 11, localAvgAccuracy: 84.4, federatedAccuracy: 94.1, localAvgF1: 82.1, federatedF1: 91.8 },
  { round: 12, localAvgAccuracy: 84.7, federatedAccuracy: 94.7, localAvgF1: 81.5, federatedF1: 92.3 },
]

/* ── Collaboration benefit breakdown ──────────────────────── */

export const mockCollaborationBenefit: CollaborationBenefit[] = [
  { metric: 'Accuracy',            localAvg: 84.7, federated: 94.7, improvement: 10.0, improvementPct: 11.8 },
  { metric: 'F1 Score',            localAvg: 81.5, federated: 92.3, improvement: 10.8, improvementPct: 13.3 },
  { metric: 'Precision',           localAvg: 82.1, federated: 92.8, improvement: 10.7, improvementPct: 13.0 },
  { metric: 'Recall',              localAvg: 80.4, federated: 91.9, improvement: 11.5, improvementPct: 14.3 },
  { metric: 'Attack Detection',    localAvg: 79.2, federated: 93.1, improvement: 13.9, improvementPct: 17.6 },
  { metric: 'FPR Reduction',       localAvg:  8.6, federated:  3.2, improvement:  5.4, improvementPct: 62.8 },
]

/* ── Simplified confusion matrices ───────────────────────── */

const cmLabels = ['DoS', 'Brute Force', 'Port Scan', 'Malware', 'Normal']

export const mockLocalConfusionMatrix: ConfusionMatrix = {
  labels: cmLabels,
  modelType: 'local',
  cells: [
    // Each row = actual class, each column = predicted class
    // DoS (actual)
    { actual: 'DoS',         predicted: 'DoS',         value: 841 },
    { actual: 'DoS',         predicted: 'Brute Force',  value:  24 },
    { actual: 'DoS',         predicted: 'Port Scan',    value:  18 },
    { actual: 'DoS',         predicted: 'Malware',      value:   9 },
    { actual: 'DoS',         predicted: 'Normal',       value:  12 },
    // Brute Force (actual)
    { actual: 'Brute Force', predicted: 'DoS',          value:  31 },
    { actual: 'Brute Force', predicted: 'Brute Force',  value: 758 },
    { actual: 'Brute Force', predicted: 'Port Scan',    value:  22 },
    { actual: 'Brute Force', predicted: 'Malware',      value:  14 },
    { actual: 'Brute Force', predicted: 'Normal',       value:  19 },
    // Port Scan (actual)
    { actual: 'Port Scan',   predicted: 'DoS',          value:  15 },
    { actual: 'Port Scan',   predicted: 'Brute Force',  value:  28 },
    { actual: 'Port Scan',   predicted: 'Port Scan',    value: 779 },
    { actual: 'Port Scan',   predicted: 'Malware',      value:  11 },
    { actual: 'Port Scan',   predicted: 'Normal',       value:  21 },
    // Malware (actual)
    { actual: 'Malware',     predicted: 'DoS',          value:  10 },
    { actual: 'Malware',     predicted: 'Brute Force',  value:  18 },
    { actual: 'Malware',     predicted: 'Port Scan',    value:  14 },
    { actual: 'Malware',     predicted: 'Malware',      value: 741 },
    { actual: 'Malware',     predicted: 'Normal',       value:  41 },
    // Normal (actual)
    { actual: 'Normal',      predicted: 'DoS',          value:  29 },
    { actual: 'Normal',      predicted: 'Brute Force',  value:  22 },
    { actual: 'Normal',      predicted: 'Port Scan',    value:  18 },
    { actual: 'Normal',      predicted: 'Malware',      value:  16 },
    { actual: 'Normal',      predicted: 'Normal',       value: 864 },
  ],
}

export const mockFederatedConfusionMatrix: ConfusionMatrix = {
  labels: cmLabels,
  modelType: 'federated',
  cells: [
    // DoS (actual)
    { actual: 'DoS',         predicted: 'DoS',         value: 891 },
    { actual: 'DoS',         predicted: 'Brute Force',  value:   8 },
    { actual: 'DoS',         predicted: 'Port Scan',    value:   4 },
    { actual: 'DoS',         predicted: 'Malware',      value:   2 },
    { actual: 'DoS',         predicted: 'Normal',       value:   3 },
    // Brute Force (actual)
    { actual: 'Brute Force', predicted: 'DoS',          value:   7 },
    { actual: 'Brute Force', predicted: 'Brute Force',  value: 823 },
    { actual: 'Brute Force', predicted: 'Port Scan',    value:   8 },
    { actual: 'Brute Force', predicted: 'Malware',      value:   3 },
    { actual: 'Brute Force', predicted: 'Normal',       value:   3 },
    // Port Scan (actual)
    { actual: 'Port Scan',   predicted: 'DoS',          value:   5 },
    { actual: 'Port Scan',   predicted: 'Brute Force',  value:   6 },
    { actual: 'Port Scan',   predicted: 'Port Scan',    value: 836 },
    { actual: 'Port Scan',   predicted: 'Malware',      value:   2 },
    { actual: 'Port Scan',   predicted: 'Normal',       value:   5 },
    // Malware (actual)
    { actual: 'Malware',     predicted: 'DoS',          value:   3 },
    { actual: 'Malware',     predicted: 'Brute Force',  value:   5 },
    { actual: 'Malware',     predicted: 'Port Scan',    value:   4 },
    { actual: 'Malware',     predicted: 'Malware',      value: 807 },
    { actual: 'Malware',     predicted: 'Normal',       value:   5 },
    // Normal (actual)
    { actual: 'Normal',      predicted: 'DoS',          value:   6 },
    { actual: 'Normal',      predicted: 'Brute Force',  value:   4 },
    { actual: 'Normal',      predicted: 'Port Scan',    value:   3 },
    { actual: 'Normal',      predicted: 'Malware',      value:   2 },
    { actual: 'Normal',      predicted: 'Normal',       value: 934 },
  ],
}
