/**
 * Mock data for the CYBER-20 Dashboard.
 *
 * All data in this file is fabricated for UI development and demonstration.
 * It will be replaced by real API responses from the FastAPI backend in a
 * later phase.  Every export maps 1-to-1 with a planned API endpoint so the
 * swap is straightforward.
 *
 * Planned API mapping:
 *   mockDashboardSummary     → GET /api/dashboard
 *   mockTrainingPerformance  → GET /api/training/rounds
 *   mockModelComparison      → GET /api/performance
 *   mockThreatDistribution   → GET /api/threats/distribution
 *   mockOrganizationActivity → GET /api/organizations
 *   mockRecentThreats        → GET /api/threats?limit=8
 *   mockSystemHealth         → GET /api/system/health
 */

import type {
  DashboardSummary,
  TrainingRoundMetric,
  ModelComparisonMetric,
  ThreatCategory,
  OrganizationActivity,
  ThreatDetection,
  SystemComponent,
} from '@/types/dashboard'

/* ── Dashboard Summary ────────────────────────────────────── */

export const mockDashboardSummary: DashboardSummary = {
  totalOrganizations: 5,
  activeOrganizations: 4,
  experimentClients: 3,
  currentRound: 10,
  totalRounds: 10,
  threatsDetected: 5,
  globalAccuracy: 65.53,
  f1Score: 47.52,
  falsePositiveRate: 8.99,
  privacyStatus: 'Data Local · Update Clipping · Gaussian Noise · Server Validation',
  privacyDetail: 'Configured: clip_norm=1.0, noise_std=0.1, ε≈48.45/round, δ=1e-5. Secure aggregation: not implemented.',
  experimentId: 'exp_20261005_071403_79eccaf1',
}

/* ── Training Performance (per round) ─────────────────────── */

export const mockTrainingPerformance: TrainingRoundMetric[] = [
  { round: 1,  accuracy: 28.77, fpr: 18.53, f1Score: 16.07 },
  { round: 2,  accuracy: 30.73, fpr: 18.04, f1Score: 16.68 },
  { round: 3,  accuracy: 53.93, fpr: 12.04, f1Score: 40.96 },
  { round: 4,  accuracy: 62.40, fpr: 9.81,  f1Score: 48.40 },
  { round: 5,  accuracy: 62.30, fpr: 9.81,  f1Score: 48.01 },
  { round: 6,  accuracy: 65.80, fpr: 8.89,  f1Score: 53.96 },
  { round: 7,  accuracy: 74.47, fpr: 6.65,  f1Score: 61.24 },
  { round: 8,  accuracy: 77.03, fpr: 6.00,  f1Score: 63.24 },
  { round: 9,  accuracy: 71.97, fpr: 7.32,  f1Score: 57.56 },
  { round: 10, accuracy: 65.53, fpr: 8.99,  f1Score: 47.52 },
]

/* ── Local vs Federated Model Comparison ──────────────────── */

export const mockModelComparison: ModelComparisonMetric[] = [
  { metric: 'Accuracy',  local: 82.4, federated: 94.7 },
  { metric: 'Precision', local: 79.1, federated: 93.2 },
  { metric: 'Recall',    local: 76.8, federated: 91.5 },
  { metric: 'F1 Score',  local: 77.9, federated: 92.3 },
]

/* ── Threat Distribution ──────────────────────────────────── */

export const mockThreatDistribution: ThreatCategory[] = [
  { category: 'DDoS',            count: 423, color: '#f87171' },
  { category: 'Intrusion',       count: 387, color: '#fb923c' },
  { category: 'Malware',         count: 312, color: '#fbbf24' },
  { category: 'Phishing',        count: 278, color: '#a78bfa' },
  { category: 'Data Exfiltration', count: 195, color: '#60a5fa' },
  { category: 'Reconnaissance',  count: 156, color: '#22d3ee' },
  { category: 'Privilege Escalation', count: 96, color: '#34d399' },
]

/* ── Organization Activity ────────────────────────────────── */

export const mockOrganizationActivity: OrganizationActivity[] = [
  {
    id: 'org-alpha',
    name: 'Organization Alpha',
    status: 'active',
    currentRound: 10,
    datasetSize: 14000,
    lastUpdate: '2026-08-31T11:24:12Z',
    contribution: null,
    isExperimentParticipant: true,
  },
  {
    id: 'org-beta',
    name: 'Organization Beta',
    status: 'active',
    currentRound: 10,
    datasetSize: 14000,
    lastUpdate: '2026-08-31T11:19:44Z',
    contribution: null,
    isExperimentParticipant: true,
  },
  {
    id: 'org-gamma',
    name: 'Organization Gamma',
    status: 'active',
    currentRound: 10,
    datasetSize: 14002,
    lastUpdate: '2026-08-31T11:24:01Z',
    contribution: null,
    isExperimentParticipant: true,
  },
  {
    id: 'org-delta',
    name: 'Organization Delta',
    status: 'active',
    currentRound: null,
    datasetSize: null,
    lastUpdate: '2026-08-31T11:05:38Z',
    contribution: null,
    isExperimentParticipant: false,
  },
  {
    id: 'org-epsilon',
    name: 'Organization Epsilon',
    status: 'offline',
    currentRound: null,
    datasetSize: null,
    lastUpdate: '2026-08-31T09:48:22Z',
    contribution: null,
    isExperimentParticipant: false,
  },
]

/* ── Recent Threat Detections ─────────────────────────────── */

export const mockRecentThreats: ThreatDetection[] = [
  {
    id: 'td-001',
    timestamp: '2026-08-31T11:24:12Z',
    organization: 'Organization 01',
    threatType: 'DDoS',
    severity: 'critical',
    confidence: 97.3,
    status: 'blocked',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-002',
    timestamp: '2026-08-31T11:21:45Z',
    organization: 'Organization 03',
    threatType: 'Intrusion',
    severity: 'high',
    confidence: 94.1,
    status: 'detected',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-003',
    timestamp: '2026-08-31T11:18:33Z',
    organization: 'Organization 02',
    threatType: 'Malware',
    severity: 'high',
    confidence: 91.8,
    status: 'investigating',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-004',
    timestamp: '2026-08-31T11:15:07Z',
    organization: 'Organization 01',
    threatType: 'Phishing',
    severity: 'medium',
    confidence: 88.5,
    status: 'blocked',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-005',
    timestamp: '2026-08-31T11:10:52Z',
    organization: 'Organization 04',
    threatType: 'Data Exfiltration',
    severity: 'critical',
    confidence: 96.2,
    status: 'detected',
    modelVersion: 'v11.0',
  },
  {
    id: 'td-006',
    timestamp: '2026-08-31T11:06:19Z',
    organization: 'Organization 03',
    threatType: 'Reconnaissance',
    severity: 'low',
    confidence: 82.7,
    status: 'resolved',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-007',
    timestamp: '2026-08-31T11:01:44Z',
    organization: 'Organization 02',
    threatType: 'Privilege Escalation',
    severity: 'high',
    confidence: 90.4,
    status: 'blocked',
    modelVersion: 'v12.0',
  },
  {
    id: 'td-008',
    timestamp: '2026-08-31T10:55:31Z',
    organization: 'Organization 01',
    threatType: 'DDoS',
    severity: 'medium',
    confidence: 85.9,
    status: 'resolved',
    modelVersion: 'v12.0',
  },
]

/* ── System Health ────────────────────────────────────────── */

export const mockSystemHealth: SystemComponent[] = [
  {
    name: 'Federated Server',
    status: 'operational',
    latency: '12ms',
    uptime: '99.9%',
    detail: 'Flower server aggregating updates',
  },
  {
    name: 'Organization Clients',
    status: 'operational',
    latency: '45ms',
    uptime: '98.7%',
    detail: '4 of 5 clients connected',
  },
  {
    name: 'Global Model',
    status: 'operational',
    latency: '—',
    uptime: '—',
    detail: 'v12.0 — 94.7% accuracy',
  },
  {
    name: 'Database',
    status: 'operational',
    latency: '3ms',
    uptime: '99.99%',
    detail: 'SQLite — development mode',
  },
  {
    name: 'Privacy Module',
    status: 'degraded',
    latency: '—',
    uptime: '—',
    detail: 'Basic model-update isolation only',
  },
]
