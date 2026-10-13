/**
 * Mock data for the Testing & Validation page.
 *
 * ⚠ CRITICAL DISCLAIMER:
 * - Tests marked executionState: 'not_run'   → CONFIGURED ONLY. Never executed.
 * - Tests marked executionState: 'mock_run'  → Run against MOCK DATA, not live system.
 * - Tests marked executionState: 'executed'  → Would mean run against real system (none yet).
 *
 * No tests have been executed against the live integrated system.
 * Mock results shown for 'mock_run' tests are illustrative only.
 *
 * Planned API mapping:
 *   mockTestSummary          → GET /api/testing/summary
 *   mockTestCases            → GET /api/testing/cases
 *   mockAcceptanceCriteria   → GET /api/testing/criteria
 */

import type {
  TestCase,
  AcceptanceCriterion,
  TestSuiteSummary,
} from '@/types/testing'

/* ── Test cases ───────────────────────────────────────────── */

export const mockTestCases: TestCase[] = [

  // ─── AC-1: Representative Operation ─────────────────────

  {
    id: 'TC-101',
    name: 'Federated Training Convergence',
    category: 'AC-1 Representative Operation',
    description: 'Verify the global model converges to ≥ 90% accuracy over 12 federated rounds with 5 participating organizations.',
    expectedResult: 'Global model accuracy ≥ 90% at round 12',
    actualResult: 'Mock: 94.7% accuracy at round 12 (MOCK DATA — not executed on live system)',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-08-31T11:30:00Z',
    notes: 'Run against mock training data only. Must be re-executed once Flower + PyTorch pipeline is integrated.',
  },
  {
    id: 'TC-102',
    name: 'Multi-Organization Participation',
    category: 'AC-1 Representative Operation',
    description: 'Confirm all registered organizations can join, train locally, and submit updates within a single federated round.',
    expectedResult: '≥ 4 of 5 organizations complete training and submit updates in each round',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires live Flower server + 5 active client connections.',
  },
  {
    id: 'TC-103',
    name: 'Threat Detection Accuracy',
    category: 'AC-1 Representative Operation',
    description: 'Evaluate the trained global model on a held-out test set. Measure accuracy, precision, recall, and F1.',
    expectedResult: 'Accuracy ≥ 90%, F1 ≥ 88%',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires trained model and real dataset split. Will run via evaluation script.',
  },
  {
    id: 'TC-104',
    name: 'Collaboration Benefit Verification',
    category: 'AC-1 Representative Operation',
    description: 'Compare federated global model accuracy to the average of local-only models trained independently.',
    expectedResult: 'Federated model accuracy ≥ 5% above local average',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Must train both local-only and federated variants on the real dataset.',
  },
  {
    id: 'TC-105',
    name: 'False-Positive Rate',
    category: 'AC-1 Representative Operation',
    description: 'Verify the global model false-positive rate (normal traffic classified as threat) stays below threshold.',
    expectedResult: 'FPR ≤ 5% on held-out benign traffic',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires balanced test set with known-benign samples.',
  },
  {
    id: 'TC-106',
    name: 'Attack Detection Rate',
    category: 'AC-1 Representative Operation',
    description: 'Verify the model detects known attack categories at an acceptable rate.',
    expectedResult: 'Detection rate ≥ 90% across all attack categories in test set',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Per-class analysis required. Must cover all threat categories in the final dataset.',
  },

  // ─── AC-2: Boundary and Failure Operation ───────────────

  {
    id: 'TC-201',
    name: 'Non-IID Degradation',
    category: 'AC-2 Boundary & Failure',
    description: 'Measure model performance degradation as data distribution heterogeneity increases (Dirichlet α → 0).',
    expectedResult: 'Federated model retains ≥ 80% accuracy even at α = 0.1 (heavy skew)',
    actualResult: 'Mock: 89.1% at α = 0.1 (MOCK DATA)',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-08-31T10:00:00Z',
    notes: 'Simulated with mock distribution data. Real experiment requires dataset partitioned via Dirichlet sampling.',
  },
  {
    id: 'TC-202',
    name: 'Single Organization Dropout',
    category: 'AC-2 Boundary & Failure',
    description: 'Simulate one organization going offline mid-round. Verify training continues and global model updates correctly.',
    expectedResult: 'Round completes with ≥ 3 clients; global model still improves from previous round',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires live Flower environment with simulated client failure injection.',
  },
  {
    id: 'TC-203',
    name: 'Majority Dropout Failure',
    category: 'AC-2 Boundary & Failure',
    description: 'Simulate all but one organization going offline. Verify server handles gracefully without corrupting global model.',
    expectedResult: 'Server aborts or holds round; global model not updated with insufficient clients',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Edge case boundary test — requires minimum-client threshold configuration.',
  },
  {
    id: 'TC-204',
    name: 'Oversized Update Rejection',
    category: 'AC-2 Boundary & Failure',
    description: 'Submit an update with L2 norm far exceeding the expected range. Verify server detects and rejects it.',
    expectedResult: 'Update rejected; round proceeds with remaining valid updates',
    actualResult: 'Mock: Rejected (norm 12.4× threshold) — MOCK DATA from security event log',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-08-31T10:44:18Z',
    notes: 'Mock security event only. Must be formally tested with configurable norm threshold in place.',
  },
  {
    id: 'TC-205',
    name: 'Recovery After Server Restart',
    category: 'AC-2 Boundary & Failure',
    description: 'Restart the Flower server mid-experiment. Verify clients reconnect and training resumes from last checkpoint.',
    expectedResult: 'Server resumes from latest checkpoint; no round is duplicated or lost',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires checkpoint persistence in the Flower strategy configuration.',
  },

  // ─── AC-3: Independent Acceptance Evidence ───────────────

  {
    id: 'TC-301',
    name: 'Privacy Boundary — Data Locality',
    category: 'AC-3 Independent Acceptance',
    description: 'Verify by code inspection and network monitoring that no raw training data leaves any organization client.',
    expectedResult: 'Network capture shows only model weight tensors transmitted; no feature vectors or labels',
    actualResult: 'Code inspection: Flower client sends model state_dict only. Network test: NOT YET RUN.',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-09-01T09:00:00Z',
    notes: 'Partial: code inspection done. Full network-level verification pending.',
  },
  {
    id: 'TC-302',
    name: 'Unauthorized Update Rejection',
    category: 'AC-3 Independent Acceptance',
    description: 'Attempt to submit a model update from an unregistered/unauthorized client. Verify rejection.',
    expectedResult: 'Unauthorized client connection refused; no update accepted',
    actualResult: 'Mock: Unknown client connection refused (security event sec-001) — MOCK EVENT',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-08-31T11:30:00Z',
    notes: 'Based on mock security event only. Formal penetration test required with real auth system.',
  },
  {
    id: 'TC-303',
    name: 'Invalid/Revoked Update Handling',
    category: 'AC-3 Independent Acceptance',
    description: 'Submit a syntactically invalid model update tensor (wrong shape/dtype). Verify server handles without crash.',
    expectedResult: 'Server rejects update with error; training round continues',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Negative/adversarial test — requires integration with live Flower server.',
  },
  {
    id: 'TC-304',
    name: 'Dashboard Accuracy — Live Data Match',
    category: 'AC-3 Independent Acceptance',
    description: 'Verify dashboard metrics match backend API values within acceptable tolerance.',
    expectedResult: 'Dashboard values match API responses ± 0.1%',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires backend API integration (Phase to be implemented).',
  },
  {
    id: 'TC-305',
    name: 'Confusion Matrix Reproducibility',
    category: 'AC-3 Independent Acceptance',
    description: 'Run model evaluation twice on the same test set. Verify identical confusion matrices (deterministic inference).',
    expectedResult: 'Both evaluations produce bit-identical confusion matrices',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Requires random seed pinning in PyTorch evaluation script.',
  },

  // ─── AC-4: Frozen Resource Envelope ─────────────────────

  {
    id: 'TC-401',
    name: 'Model Size Constraint',
    category: 'AC-4 Frozen Resource Envelope',
    description: 'Verify the global model parameter count and file size remain within agreed limits.',
    expectedResult: 'Model ≤ 50 MB on disk; parameter count within architecture specification',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Measurable once final model architecture is frozen.',
  },
  {
    id: 'TC-402',
    name: 'Inference Latency',
    category: 'AC-4 Frozen Resource Envelope',
    description: 'Measure single-sample inference latency on CPU. Must meet response-time requirement.',
    expectedResult: 'Inference latency ≤ 100 ms per sample on CPU',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Benchmark with torch.inference_mode() on representative hardware.',
  },
  {
    id: 'TC-403',
    name: 'Training Round Time Budget',
    category: 'AC-4 Frozen Resource Envelope',
    description: 'Verify average federated round completes within the configured time budget.',
    expectedResult: 'Average round duration ≤ 120 seconds across 5 clients',
    actualResult: 'Mock: ~38s average (MOCK DATA)',
    status: 'warning',
    executionState: 'mock_run',
    timestamp: '2026-08-31T11:00:00Z',
    notes: 'Mock timing from simulated round durations. Must be verified on target hardware.',
  },
  {
    id: 'TC-404',
    name: 'Memory Usage — Server',
    category: 'AC-4 Frozen Resource Envelope',
    description: 'Monitor Flower server peak memory during aggregation of 5 client updates.',
    expectedResult: 'Server peak RAM ≤ 4 GB during aggregation',
    actualResult: null,
    status: 'pending',
    executionState: 'not_run',
    timestamp: null,
    notes: 'Measurable with memory profiler once Flower server is running with real clients.',
  },
]

/* ── Acceptance criteria definitions ─────────────────────── */

export const mockAcceptanceCriteria: AcceptanceCriterion[] = [
  {
    code:              'AC-1',
    title:             'Representative Operation',
    description:       'Demonstrates the system performs its primary function correctly under normal operating conditions.',
    tests:             ['TC-101', 'TC-102', 'TC-103', 'TC-104', 'TC-105', 'TC-106'],
    passingThreshold:  90,
  },
  {
    code:              'AC-2',
    title:             'Boundary and Failure Operation',
    description:       'Demonstrates the system handles edge cases, partial failures, and invalid inputs gracefully.',
    tests:             ['TC-201', 'TC-202', 'TC-203', 'TC-204', 'TC-205'],
    passingThreshold:  80,
  },
  {
    code:              'AC-3',
    title:             'Independent Acceptance Evidence',
    description:       'Independently verifiable evidence that key security and correctness properties hold.',
    tests:             ['TC-301', 'TC-302', 'TC-303', 'TC-304', 'TC-305'],
    passingThreshold:  100,
  },
  {
    code:              'AC-4',
    title:             'Frozen Resource Envelope',
    description:       'Demonstrates the system operates within defined resource constraints (size, latency, memory).',
    tests:             ['TC-401', 'TC-402', 'TC-403', 'TC-404'],
    passingThreshold:  100,
  },
]

/* ── Test suite summary ───────────────────────────────────── */

export function computeTestSummary(tests: TestCase[]): TestSuiteSummary {
  const executed  = tests.filter(t => t.executionState === 'executed').length
  const mockRun   = tests.filter(t => t.executionState === 'mock_run').length
  const notRun    = tests.filter(t => t.executionState === 'not_run').length
  const passed    = tests.filter(t => t.status === 'pass').length
  const failed    = tests.filter(t => t.status === 'fail').length
  const warnings  = tests.filter(t => t.status === 'warning').length
  const pending   = tests.filter(t => t.status === 'pending').length
  const ran       = executed + mockRun
  return {
    total:    tests.length,
    executed,
    mockRun,
    notRun,
    passed,
    failed,
    warnings,
    pending,
    passRate: ran === 0 ? 0 : Math.round((passed / ran) * 100),
  }
}
