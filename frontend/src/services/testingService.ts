import { apiClient } from '@/lib/apiClient'
import type { ApiTestingResponse } from '@/types/api'
import type { TestCase, AcceptanceCriterion, TestSuiteSummary } from '@/types/testing'

export interface TestingData {
  summary:             TestSuiteSummary
  testCases:           TestCase[]
  acceptanceCriteria:  AcceptanceCriterion[]
}

export const testingService = {
  async getTesting(): Promise<TestingData> {
    const r = await apiClient.get<ApiTestingResponse>('/tests')
    return {
      summary: {
        total:    r.summary.total,
        executed: r.summary.executed,
        mockRun:  r.summary.mock_run,
        notRun:   r.summary.not_run,
        passed:   r.summary.passed,
        failed:   r.summary.failed,
        warnings: r.summary.warnings,
        pending:  r.summary.pending,
        passRate: r.summary.pass_rate,
      },
      testCases: r.test_cases.map(t => ({
        id:             t.id,
        name:           t.name,
        category:       t.category as TestCase['category'],
        description:    t.description,
        expectedResult: t.expected_result,
        actualResult:   t.actual_result ?? null,
        status:         t.status as TestCase['status'],
        executionState: t.execution_state as TestCase['executionState'],
        timestamp:      t.timestamp ?? null,
        notes:          t.notes,
      })),
      acceptanceCriteria: r.acceptance_criteria.map(ac => ({
        code:              ac.code,
        title:             ac.title,
        description:       ac.description,
        tests:             ac.tests,
        passingThreshold:  ac.passing_threshold,
      })),
    }
  },
}
