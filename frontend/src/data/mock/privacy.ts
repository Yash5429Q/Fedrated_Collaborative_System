/**
 * Mock data for the Privacy & Security page.
 *
 * ⚠ IMPORTANT DISCLAIMER:
 * This data describes the INTENDED privacy architecture of the system.
 * Privacy-preserving mechanisms such as differential privacy, secure
 * aggregation, and homomorphic encryption have NOT been implemented yet.
 * The statuses below reflect the current design state, not a deployed system.
 *
 * Planned API mapping:
 *   mockPrivacySummary    → GET /api/privacy/summary
 *   mockPrivacyProperties → GET /api/privacy/properties
 *   mockOrgUpdateStatuses → GET /api/privacy/updates
 *   mockSecurityEvents    → GET /api/security/events
 */

import type {
  PrivacyPageSummary,
  PrivacyProperty,
  OrgUpdateStatus,
  SecurityEvent,
} from '@/types/privacy'

/* ── Page summary ─────────────────────────────────────────── */

export const mockPrivacySummary: PrivacyPageSummary = {
  rawDataShared:                   false,
  modelUpdatesOnly:                true,
  privacyMechanismsImplemented:    1,    // data locality only (by FL design)
  privacyMechanismsPlanned:        3,    // DP, SecAgg, validation
  securityEventsLast24h:           4,
  unauthorizedAttemptsBlocked:     2,
}

/* ── Privacy properties / principles ─────────────────────── */

export const mockPrivacyProperties: PrivacyProperty[] = [
  {
    id: 'data-locality',
    label: 'Raw Data Locality',
    category: 'data_locality',
    description: 'Organization raw training data never leaves the local environment.',
    status: 'enforced',
    detail: 'Enforced by the federated learning architecture itself — only model weight updates are transmitted, never the underlying dataset.',
    planned: false,
  },
  {
    id: 'model-updates-only',
    label: 'Model Updates Only',
    category: 'model_update',
    description: 'Only gradient/weight updates are sent to the aggregation server.',
    status: 'enforced',
    detail: 'Flower client sends only model parameter deltas. No feature vectors, no labels, no raw traffic data.',
    planned: false,
  },
  {
    id: 'differential-privacy',
    label: 'Differential Privacy (DP)',
    category: 'model_update',
    description: 'Noise added to model updates to provide formal privacy guarantees.',
    status: 'planned',
    detail: 'NOT YET IMPLEMENTED. Planned: Gaussian noise mechanism with configurable ε/δ budget via Opacus or Flower DP plugin.',
    planned: true,
  },
  {
    id: 'secure-aggregation',
    label: 'Secure Aggregation',
    category: 'aggregation',
    description: 'Cryptographic protocol to aggregate updates without the server seeing individual client updates.',
    status: 'planned',
    detail: 'NOT YET IMPLEMENTED. Planned: Flower secure aggregation strategy or custom SecAgg+ implementation.',
    planned: true,
  },
  {
    id: 'update-validation',
    label: 'Update Validation',
    category: 'aggregation',
    description: 'Server-side checks to detect and reject anomalous or malicious model updates.',
    status: 'planned',
    detail: 'NOT YET IMPLEMENTED. Planned: statistical validation of update norms, cosine similarity checks, and Byzantine-robust aggregation (e.g. Krum or Median).',
    planned: true,
  },
  {
    id: 'access-control',
    label: 'Client Authentication',
    category: 'access_control',
    description: 'Only registered organization clients can participate in federated rounds.',
    status: 'planned',
    detail: 'NOT YET IMPLEMENTED. Planned: mutual TLS (mTLS) between Flower server and clients, with certificate pinning per organization.',
    planned: true,
  },
]

/* ── Per-org model update status (current round) ─────────── */

export const mockOrgUpdateStatuses: OrgUpdateStatus[] = [
  {
    orgId:            'org-alpha',
    orgName:          'Organization Alpha',
    round:            12,
    updateStatus:     'submitted',
    updateSize:       '2.4 MB',
    submittedAt:      '2026-08-31T11:22:10Z',
    validationPassed: true,
    notes:            'Update accepted. Norm within expected range.',
  },
  {
    orgId:            'org-beta',
    orgName:          'Organization Beta',
    round:            12,
    updateStatus:     'submitted',
    updateSize:       '2.4 MB',
    submittedAt:      '2026-08-31T11:19:44Z',
    validationPassed: true,
    notes:            'Update accepted. Norm within expected range.',
  },
  {
    orgId:            'org-gamma',
    orgName:          'Organization Gamma',
    round:            12,
    updateStatus:     'submitted',
    updateSize:       '2.4 MB',
    submittedAt:      '2026-08-31T11:24:01Z',
    validationPassed: true,
    notes:            'Update accepted. Norm within expected range.',
  },
  {
    orgId:            'org-delta',
    orgName:          'Organization Delta',
    round:            12,
    updateStatus:     'submitted',
    updateSize:       '2.4 MB',
    submittedAt:      '2026-08-31T11:05:38Z',
    validationPassed: true,
    notes:            'Update accepted — submitted from round 11 checkpoint.',
  },
  {
    orgId:            'org-epsilon',
    orgName:          'Organization Epsilon',
    round:            12,
    updateStatus:     'not_sent',
    updateSize:       null,
    submittedAt:      null,
    validationPassed: null,
    notes:            'Client offline — did not participate in round 12.',
  },
]

/* ── Security events ──────────────────────────────────────── */

export const mockSecurityEvents: SecurityEvent[] = [
  {
    id:           'sec-001',
    timestamp:    '2026-08-31T11:30:00Z',
    organization: null,
    event:        'Unknown client connection attempt',
    category:     'Access Control',
    severity:     'warning',
    status:       'resolved',
    detail:       'Unregistered client ID attempted to connect to the Flower server. Connection refused. Source: 10.99.0.55.',
  },
  {
    id:           'sec-002',
    timestamp:    '2026-08-31T11:15:22Z',
    organization: 'Organization Epsilon',
    event:        'Client disconnected mid-round',
    category:     'Availability',
    severity:     'info',
    status:       'resolved',
    detail:       'Epsilon client lost connection during round 12 training. Server continued with 4/5 clients. Round completed normally.',
  },
  {
    id:           'sec-003',
    timestamp:    '2026-08-31T10:44:18Z',
    organization: null,
    event:        'Large model update rejected (norm outlier)',
    category:     'Update Validation',
    severity:     'warning',
    status:       'resolved',
    detail:       'An update with unusually high L2 norm (12.4× expected) was received and discarded before aggregation. Source organization not identified.',
  },
  {
    id:           'sec-004',
    timestamp:    '2026-08-31T09:22:05Z',
    organization: 'Organization Delta',
    event:        'Round participation delay — late submission',
    category:     'Availability',
    severity:     'info',
    status:       'resolved',
    detail:       'Delta submitted round 11 update 8 minutes after deadline. Server accepted late submission within grace period.',
  },
  {
    id:           'sec-005',
    timestamp:    '2026-08-30T22:11:44Z',
    organization: null,
    event:        'Repeated connection probe from external IP',
    category:     'Access Control',
    severity:     'critical',
    status:       'monitoring',
    detail:       'External IP 203.0.113.77 probed Flower server port 8080 fourteen times over 10 minutes. All connections refused. IP flagged for monitoring.',
  },
  {
    id:           'sec-006',
    timestamp:    '2026-08-30T14:05:30Z',
    organization: null,
    event:        'Server startup — no prior state',
    category:     'System',
    severity:     'info',
    status:       'resolved',
    detail:       'Flower server initialized. Global model version v0 created. Awaiting client connections.',
  },
]
