/**
 * TypeScript interfaces for the Testing & Validation page.
 *
 * IMPORTANT: These types distinguish between tests that are CONFIGURED
 * (planned, defined) and tests that have been EXECUTED against the live system.
 *
 * Planned API mapping documented on each interface.
 */

/* ── Test execution state ─────────────────────────────────── */

/** Whether the test has been run against the real system */
export type TestExecutionState =
  | 'not_run'       // configured but never executed
  | 'mock_run'      // run with mock/simulated data (not real system)
  | 'executed'      // actually run against the live integrated system

/** Result of a test — only meaningful when executionState === 'executed' */
export type TestResult = 'pass' | 'fail' | 'warning' | 'pending'

export type TestCategory =
  | 'AC-1 Representative Operation'
  | 'AC-2 Boundary & Failure'
  | 'AC-3 Independent Acceptance'
  | 'AC-4 Frozen Resource Envelope'

/* ── Test case ────────────────────────────────────────────── */

export interface TestCase {
  id: string
  name: string
  category: TestCategory
  description: string
  expectedResult: string
  actualResult: string | null         // null if not yet executed
  status: TestResult
  executionState: TestExecutionState
  timestamp: string | null            // null if not yet executed
  notes: string
}

/* ── Acceptance criterion section ────────────────────────── */

export interface AcceptanceCriterion {
  code: string               // e.g. 'AC-1'
  title: string
  description: string
  tests: string[]            // test IDs belonging to this criterion
  passingThreshold: number   // % of tests that must pass
}

/* ── Test suite summary ───────────────────────────────────── */

export interface TestSuiteSummary {
  total: number
  executed: number
  notRun: number
  mockRun: number
  passed: number
  failed: number
  warnings: number
  pending: number
  passRate: number           // % of executed tests that passed
}
