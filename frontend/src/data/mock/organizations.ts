/**
 * Mock data for the Organizations page.
 *
 * All data is fabricated for UI development and demonstration.
 * It will be replaced by real API responses from the FastAPI backend.
 *
 * Planned API mapping:
 *   mockOrgSummary    → GET /api/organizations/summary
 *   mockOrganizations → GET /api/organizations
 *   org by id         → GET /api/organizations/:id
 */

import type { Organization, OrgPageSummary } from '@/types/organization'

/* ── Shared color palette for threat-type distribution ────── */

const threatColors = {
  DDoS:                   '#f87171',
  Intrusion:              '#fb923c',
  Malware:                '#fbbf24',
  Phishing:               '#a78bfa',
  'Data Exfiltration':    '#60a5fa',
  Reconnaissance:         '#22d3ee',
  'Privilege Escalation': '#34d399',
}

/* ── Page-level summary ───────────────────────────────────── */

export const mockOrgSummary: OrgPageSummary = {
  total: 5,
  active: 2,
  training: 1,
  idle: 1,
  offline: 1,
  totalDataPoints: 109600,
  avgAccuracy: 84.6,
  avgContribution: 90.4,
}

/* ── Organizations ────────────────────────────────────────── */

export const mockOrganizations: Organization[] = [
  {
    id: 'org-alpha',
    name: 'Organization Alpha',
    description: 'Primary research facility — high-volume network traffic data with emphasis on DDoS and intrusion patterns.',
    status: 'active',
    datasetSize: 31000,
    datasetSplit: 'Train 70% / Val 15% / Test 15%',
    localModel: {
      status: 'trained',
      version: 'v12.0',
      accuracy: 88.2,
      loss: 0.28,
      lastTrained: '2026-08-31T11:20:00Z',
      epochs: 15,
    },
    currentRound: 12,
    totalRounds: 12,
    lastUpdate: '2 min ago',
    joinedAt: '2026-06-15T09:00:00Z',
    contribution: 100,
    threatsDetected: 512,
    dataDistribution: [
      { threatType: 'DDoS',                percentage: 32, count: 9920, color: threatColors.DDoS },
      { threatType: 'Intrusion',            percentage: 25, count: 7750, color: threatColors.Intrusion },
      { threatType: 'Malware',              percentage: 15, count: 4650, color: threatColors.Malware },
      { threatType: 'Phishing',             percentage: 10, count: 3100, color: threatColors.Phishing },
      { threatType: 'Data Exfiltration',    percentage: 8,  count: 2480, color: threatColors['Data Exfiltration'] },
      { threatType: 'Reconnaissance',       percentage: 6,  count: 1860, color: threatColors.Reconnaissance },
      { threatType: 'Privilege Escalation', percentage: 4,  count: 1240, color: threatColors['Privilege Escalation'] },
    ],
    trainingHistory: [
      { round: 10, participated: true,  localAccuracy: 86.5, localLoss: 0.33, samplesUsed: 21700, duration: '42s' },
      { round: 11, participated: true,  localAccuracy: 87.4, localLoss: 0.30, samplesUsed: 21700, duration: '41s' },
      { round: 12, participated: true,  localAccuracy: 88.2, localLoss: 0.28, samplesUsed: 21700, duration: '40s' },
    ],
    privacyMode: 'Model updates only',
    networkLatency: '12ms',
  },
  {
    id: 'org-beta',
    name: 'Organization Beta',
    description: 'Financial services branch — dataset skewed toward phishing and data exfiltration attacks.',
    status: 'training',
    datasetSize: 24500,
    datasetSplit: 'Train 70% / Val 15% / Test 15%',
    localModel: {
      status: 'training',
      version: 'v11.0',
      accuracy: 83.7,
      loss: 0.38,
      lastTrained: '2026-08-31T11:05:00Z',
      epochs: 12,
    },
    currentRound: 12,
    totalRounds: 12,
    lastUpdate: '8 min ago',
    joinedAt: '2026-06-15T09:00:00Z',
    contribution: 95,
    threatsDetected: 398,
    dataDistribution: [
      { threatType: 'Phishing',             percentage: 35, count: 8575, color: threatColors.Phishing },
      { threatType: 'Data Exfiltration',    percentage: 28, count: 6860, color: threatColors['Data Exfiltration'] },
      { threatType: 'Intrusion',            percentage: 15, count: 3675, color: threatColors.Intrusion },
      { threatType: 'Malware',              percentage: 10, count: 2450, color: threatColors.Malware },
      { threatType: 'DDoS',                 percentage: 5,  count: 1225, color: threatColors.DDoS },
      { threatType: 'Reconnaissance',       percentage: 4,  count: 980,  color: threatColors.Reconnaissance },
      { threatType: 'Privilege Escalation', percentage: 3,  count: 735,  color: threatColors['Privilege Escalation'] },
    ],
    trainingHistory: [
      { round: 10, participated: true,  localAccuracy: 82.1, localLoss: 0.42, samplesUsed: 17150, duration: '36s' },
      { round: 11, participated: true,  localAccuracy: 83.0, localLoss: 0.40, samplesUsed: 17150, duration: '35s' },
      { round: 12, participated: true,  localAccuracy: 83.7, localLoss: 0.38, samplesUsed: 17150, duration: '35s' },
    ],
    privacyMode: 'Model updates only',
    networkLatency: '28ms',
  },
  {
    id: 'org-gamma',
    name: 'Organization Gamma',
    description: 'Healthcare network — diverse attack surface with strong malware and ransomware representation.',
    status: 'active',
    datasetSize: 18200,
    datasetSplit: 'Train 70% / Val 15% / Test 15%',
    localModel: {
      status: 'trained',
      version: 'v12.0',
      accuracy: 85.9,
      loss: 0.34,
      lastTrained: '2026-08-31T11:22:00Z',
      epochs: 15,
    },
    currentRound: 12,
    totalRounds: 12,
    lastUpdate: '1 min ago',
    joinedAt: '2026-06-20T14:00:00Z',
    contribution: 98,
    threatsDetected: 341,
    dataDistribution: [
      { threatType: 'Malware',              percentage: 30, count: 5460, color: threatColors.Malware },
      { threatType: 'Intrusion',            percentage: 22, count: 4004, color: threatColors.Intrusion },
      { threatType: 'Reconnaissance',       percentage: 18, count: 3276, color: threatColors.Reconnaissance },
      { threatType: 'Phishing',             percentage: 12, count: 2184, color: threatColors.Phishing },
      { threatType: 'DDoS',                 percentage: 8,  count: 1456, color: threatColors.DDoS },
      { threatType: 'Data Exfiltration',    percentage: 6,  count: 1092, color: threatColors['Data Exfiltration'] },
      { threatType: 'Privilege Escalation', percentage: 4,  count: 728,  color: threatColors['Privilege Escalation'] },
    ],
    trainingHistory: [
      { round: 10, participated: true,  localAccuracy: 84.2, localLoss: 0.38, samplesUsed: 12740, duration: '28s' },
      { round: 11, participated: true,  localAccuracy: 85.1, localLoss: 0.36, samplesUsed: 12740, duration: '27s' },
      { round: 12, participated: true,  localAccuracy: 85.9, localLoss: 0.34, samplesUsed: 12740, duration: '27s' },
    ],
    privacyMode: 'Model updates only',
    networkLatency: '18ms',
  },
  {
    id: 'org-delta',
    name: 'Organization Delta',
    description: 'Government infrastructure — emphasis on privilege escalation and reconnaissance threats.',
    status: 'idle',
    datasetSize: 15800,
    datasetSplit: 'Train 70% / Val 15% / Test 15%',
    localModel: {
      status: 'trained',
      version: 'v11.0',
      accuracy: 81.3,
      loss: 0.42,
      lastTrained: '2026-08-31T10:40:00Z',
      epochs: 10,
    },
    currentRound: 11,
    totalRounds: 12,
    lastUpdate: '22 min ago',
    joinedAt: '2026-07-01T10:00:00Z',
    contribution: 87,
    threatsDetected: 276,
    dataDistribution: [
      { threatType: 'Privilege Escalation', percentage: 28, count: 4424, color: threatColors['Privilege Escalation'] },
      { threatType: 'Reconnaissance',       percentage: 25, count: 3950, color: threatColors.Reconnaissance },
      { threatType: 'Intrusion',            percentage: 18, count: 2844, color: threatColors.Intrusion },
      { threatType: 'DDoS',                 percentage: 12, count: 1896, color: threatColors.DDoS },
      { threatType: 'Malware',              percentage: 8,  count: 1264, color: threatColors.Malware },
      { threatType: 'Phishing',             percentage: 5,  count: 790,  color: threatColors.Phishing },
      { threatType: 'Data Exfiltration',    percentage: 4,  count: 632,  color: threatColors['Data Exfiltration'] },
    ],
    trainingHistory: [
      { round: 10, participated: true,  localAccuracy: 80.1, localLoss: 0.45, samplesUsed: 11060, duration: '24s' },
      { round: 11, participated: true,  localAccuracy: 81.3, localLoss: 0.42, samplesUsed: 11060, duration: '24s' },
      { round: 12, participated: false, localAccuracy: 81.3, localLoss: 0.42, samplesUsed: 0,     duration: '—'  },
    ],
    privacyMode: 'Model updates only',
    networkLatency: '35ms',
  },
  {
    id: 'org-epsilon',
    name: 'Organization Epsilon',
    description: 'Cloud services provider — broad threat coverage, currently offline for maintenance.',
    status: 'offline',
    datasetSize: 20100,
    datasetSplit: 'Train 70% / Val 15% / Test 15%',
    localModel: {
      status: 'trained',
      version: 'v10.0',
      accuracy: 79.2,
      loss: 0.48,
      lastTrained: '2026-08-31T08:15:00Z',
      epochs: 10,
    },
    currentRound: 10,
    totalRounds: 12,
    lastUpdate: '3 hr ago',
    joinedAt: '2026-07-10T11:00:00Z',
    contribution: 72,
    threatsDetected: 320,
    dataDistribution: [
      { threatType: 'DDoS',                 percentage: 20, count: 4020, color: threatColors.DDoS },
      { threatType: 'Intrusion',            percentage: 18, count: 3618, color: threatColors.Intrusion },
      { threatType: 'Malware',              percentage: 16, count: 3216, color: threatColors.Malware },
      { threatType: 'Phishing',             percentage: 15, count: 3015, color: threatColors.Phishing },
      { threatType: 'Data Exfiltration',    percentage: 12, count: 2412, color: threatColors['Data Exfiltration'] },
      { threatType: 'Reconnaissance',       percentage: 10, count: 2010, color: threatColors.Reconnaissance },
      { threatType: 'Privilege Escalation', percentage: 9,  count: 1809, color: threatColors['Privilege Escalation'] },
    ],
    trainingHistory: [
      { round: 10, participated: true,  localAccuracy: 79.2, localLoss: 0.48, samplesUsed: 14070, duration: '30s' },
      { round: 11, participated: false, localAccuracy: 79.2, localLoss: 0.48, samplesUsed: 0,     duration: '—'  },
      { round: 12, participated: false, localAccuracy: 79.2, localLoss: 0.48, samplesUsed: 0,     duration: '—'  },
    ],
    privacyMode: 'Model updates only',
    networkLatency: '—',
  },
]
