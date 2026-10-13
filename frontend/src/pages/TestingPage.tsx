import { useState } from 'react'
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  TestTube,
  FlaskConical,
  Filter,
  ChevronDown,
  ChevronUp,
  Info,
  ShieldAlert,
  Target,
} from 'lucide-react'

import { ChartCard, LoadingSpinner, ErrorState } from '@/components/common'
import type {
  TestCase,
  TestResult,
  TestExecutionState,
  TestCategory,
} from '@/types/testing'
import { useTesting } from '@/hooks/useTesting'


/* ── Result config ────────────────────────────────────────── */

const resultConfig: Record<TestResult, {
  icon: React.ComponentType<{ className?: string }>
  label: string
  badgeCls: string
  dotCls: string
}> = {
  pass:    { icon: CheckCircle2,  label: 'Pass',    badgeCls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20', dotCls: 'bg-emerald-400' },
  fail:    { icon: XCircle,       label: 'Fail',    badgeCls: 'bg-red-500/15     text-red-400     border-red-500/20',     dotCls: 'bg-red-400'     },
  warning: { icon: AlertTriangle, label: 'Warning', badgeCls: 'bg-amber-500/15   text-amber-400   border-amber-500/20',   dotCls: 'bg-amber-400'   },
  pending: { icon: Clock,         label: 'Pending', badgeCls: 'bg-slate-500/15   text-slate-400   border-slate-500/20',   dotCls: 'bg-slate-500'   },
}

/* ── Execution state config ───────────────────────────────── */

const execConfig: Record<TestExecutionState, { label: string; cls: string; tip: string }> = {
  not_run:  { label: 'Configured',    cls: 'text-gray-500   bg-cyber-800      border-cyber-700/50', tip: 'Test is defined but has not been executed' },
  mock_run: { label: 'Mock Run',      cls: 'text-amber-400  bg-amber-500/10   border-amber-500/20', tip: 'Run with mock/simulated data only — NOT on live system' },
  executed: { label: 'Executed',      cls: 'text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20', tip: 'Run against the live integrated system' },
}

/* ── Category filter options ──────────────────────────────── */

const allCategories: TestCategory[] = [
  'AC-1 Representative Operation',
  'AC-2 Boundary & Failure',
  'AC-3 Independent Acceptance',
  'AC-4 Frozen Resource Envelope',
]

type StatusFilter = 'all' | TestResult
type ExecFilter   = 'all' | TestExecutionState

/* ═══════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════ */

export default function TestingPage() {
  const { data, loading, error, refetch } = useTesting()
  const [selectedCategory, setSelectedCategory] = useState<TestCategory | 'all'>('all')
  const [statusFilter,     setStatusFilter]     = useState<StatusFilter>('all')
  const [execFilter,       setExecFilter]       = useState<ExecFilter>('all')
  const [expandedTest,     setExpandedTest]     = useState<string | null>(null)

  if (loading) return <LoadingSpinner label="Loading test results…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { summary, testCases: mockTestCases, acceptanceCriteria: mockAcceptanceCriteria } = data

  // Compute acceptance criterion summaries locally (client-side, lightweight)
  const computeTestSummary = (tests: typeof mockTestCases) => ({
    total:    tests.length,
    executed: tests.filter(t => t.executionState === 'executed').length,
    mockRun:  tests.filter(t => t.executionState === 'mock_run').length,
    notRun:   tests.filter(t => t.executionState === 'not_run').length,
    passed:   tests.filter(t => t.status === 'pass').length,
    failed:   tests.filter(t => t.status === 'fail').length,
    warnings: tests.filter(t => t.status === 'warning').length,
    pending:  tests.filter(t => t.status === 'pending').length,
    passRate: tests.filter(t => t.executionState !== 'not_run').length > 0
      ? Math.round(tests.filter(t => t.status === 'pass').length / tests.filter(t => t.executionState !== 'not_run').length * 100)
      : 0,
  })

  const filtered = mockTestCases.filter((t) => {
    if (selectedCategory !== 'all' && t.category !== selectedCategory) return false
    if (statusFilter     !== 'all' && t.status !== statusFilter)       return false
    if (execFilter       !== 'all' && t.executionState !== execFilter) return false
    return true
  })

  const toggleExpand = (id: string) =>
    setExpandedTest((p) => (p === id ? null : id))

  return (
    <div className="space-y-8">

      {/* ── Execution state legend & banner ────────────── */}
      <div className="flex items-start gap-3 rounded-lg border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-3.5">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent-cyan" />
        <div className="space-y-1.5 text-xs text-gray-400">
          <p className="font-semibold text-accent-cyan">Verification Architecture & Test Execution Scope</p>
          <div className="flex flex-wrap gap-4 pt-0.5">
            <ExecLegendItem state="not_run"  />
            <ExecLegendItem state="mock_run" />
            <ExecLegendItem state="executed" />
          </div>
          <p className="pt-1 text-gray-300 leading-relaxed">
            <span className="font-semibold text-emerald-400">Automated Backend Regression Suite:</span> 199 automated unit, repository, and service tests pass continuously in pytest with SQLite transactions and isolated mocks.
          </p>
          <p className="text-gray-400 leading-relaxed">
            <span className="font-semibold text-gray-200">System Test Matrix Scope:</span> The 12 acceptance test cases cataloged below represent the formal system and integration test specifications. Individual test items maintain their exact database execution states: <span className="text-gray-300 font-medium">Configured</span> (defined specifications awaiting live execution), <span className="text-amber-400 font-medium">Mock Run</span> (tested with synthetic benchmark data), and <span className="text-accent-cyan font-medium">Executed</span> (verified against live runtime endpoints). Browser end-to-end user flows and live network tap evaluations remain separate from backend automated passes.
          </p>
        </div>
      </div>

      {/* ── Summary cards ─────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <SummaryCard label="Total Tests" value={summary.total} color="text-gray-300" />
        <SummaryCard label="Configured"  value={summary.notRun}   icon={Clock}         color="text-gray-500" />
        <SummaryCard label="Mock Run"    value={summary.mockRun}  icon={FlaskConical}   color="text-amber-400" />
        <SummaryCard label="Executed"    value={summary.executed} icon={TestTube}       color="text-accent-cyan" />
        <SummaryCard label="Pass"        value={summary.passed}   icon={CheckCircle2}   color="text-emerald-400" />
        <SummaryCard label="Fail"        value={summary.failed}   icon={XCircle}        color="text-red-400" />
      </div>

      {/* ── Pass rate bar ─────────────────────────────── */}
      <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 px-5 py-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Overall Pass Rate (mock/executed tests only)
          </span>
          <span className="font-mono text-lg font-bold text-gray-100">
            {summary.passRate}%
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-cyber-700">
          <div
            className="h-full rounded-full bg-emerald-500/70 transition-all"
            style={{ width: `${summary.passRate}%` }}
          />
        </div>
        <p className="mt-1.5 text-xs text-gray-600">
          {summary.mockRun} mock-run tests · {summary.executed} live-executed tests ·{' '}
          {summary.notRun} configured but not yet run
        </p>
      </div>

      {/* ── AC criterion cards ─────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {mockAcceptanceCriteria.map((ac) => {
          const acTests   = mockTestCases.filter(t => ac.tests.includes(t.id))
          const acSummary = computeTestSummary(acTests)
          return <AcceptanceCriterionCard key={ac.code} ac={ac} summary={acSummary} />
        })}
      </div>

      {/* ── Filter bar ────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Category */}
        <select
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value as TestCategory | 'all')}
          className="rounded-md border border-cyber-700/50 bg-cyber-800/50 px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent-cyan/50"
        >
          <option value="all">All Categories</option>
          {allCategories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        {/* Status */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
          className="rounded-md border border-cyber-700/50 bg-cyber-800/50 px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent-cyan/50"
        >
          <option value="all">All Statuses</option>
          <option value="pass">Pass</option>
          <option value="fail">Fail</option>
          <option value="warning">Warning</option>
          <option value="pending">Pending</option>
        </select>

        {/* Execution state */}
        <select
          value={execFilter}
          onChange={(e) => setExecFilter(e.target.value as ExecFilter)}
          className="rounded-md border border-cyber-700/50 bg-cyber-800/50 px-3 py-2 text-xs text-gray-300 outline-none focus:border-accent-cyan/50"
        >
          <option value="all">All Execution States</option>
          <option value="not_run">Configured Only</option>
          <option value="mock_run">Mock Run</option>
          <option value="executed">Live Executed</option>
        </select>

        <span className="ml-auto text-xs text-gray-500">
          {filtered.length} of {mockTestCases.length} tests
        </span>
      </div>

      {/* ── Test results table ────────────────────────── */}
      <ChartCard
        title="Test Results"
        subtitle="Click any row to expand detail. Execution state shows whether each test was actually run."
      >
        <div className="divide-y divide-cyber-700/30">
          {/* Header */}
          <div className="grid grid-cols-[80px_1fr_160px_110px_110px] gap-3 bg-cyber-800/30 px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-gray-500">
            <span>ID</span>
            <span>Test Name</span>
            <span>Execution State</span>
            <span className="text-center">Result</span>
            <span className="text-right">Time</span>
          </div>

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 text-gray-500">
              <Filter className="mb-2 h-6 w-6" />
              <p className="text-sm">No tests match current filters.</p>
            </div>
          )}

          {filtered.map((test) => (
            <TestRow
              key={test.id}
              test={test}
              expanded={expandedTest === test.id}
              onToggle={() => toggleExpand(test.id)}
            />
          ))}
        </div>

        {/* Table footer */}
        <div className="border-t border-cyber-700/30 px-4 py-2 text-xs text-gray-600">
          ⚠ Tests without a timestamp have never been executed. "Warning" status means
          run with mock data only — results are not acceptance evidence.
        </div>
      </ChartCard>

      {/* ── Mock data notice ──────────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-600">
        All test data is mock/configured only — no tests have been executed against the live system.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Test row (expandable)
   ═══════════════════════════════════════════════════════════ */

function TestRow({
  test,
  expanded,
  onToggle,
}: {
  test: TestCase
  expanded: boolean
  onToggle: () => void
}) {
  const rc = resultConfig[test.status]
  const ec = execConfig[test.executionState]
  const Icon = rc.icon

  return (
    <>
      <button
        onClick={onToggle}
        className="grid w-full grid-cols-[80px_1fr_160px_110px_110px] items-center gap-3 px-4 py-3 text-left hover:bg-cyber-800/20"
      >
        {/* ID */}
        <span className="font-mono text-xs font-medium text-accent-cyan">{test.id}</span>

        {/* Name */}
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-gray-200">{test.name}</p>
          <p className="truncate text-xs text-gray-500">{test.category}</p>
        </div>

        {/* Execution state */}
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${ec.cls}`} title={ec.tip}>
          {ec.label}
        </span>

        {/* Result badge */}
        <span className={`inline-flex items-center justify-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${rc.badgeCls}`}>
          <Icon className="h-3 w-3" />
          {rc.label}
        </span>

        {/* Timestamp */}
        <div className="flex items-center justify-end gap-1">
          {test.timestamp ? (
            <span className="font-mono text-[11px] text-gray-500">
              {new Date(test.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          ) : (
            <span className="text-xs text-gray-600">—</span>
          )}
          {expanded ? <ChevronUp className="h-3.5 w-3.5 text-gray-500" /> : <ChevronDown className="h-3.5 w-3.5 text-gray-500" />}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-cyber-700/30 bg-cyber-800/20 px-6 py-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <DetailField label="Description" value={test.description} />
              <DetailField label="Expected Result" value={test.expectedResult} highlight="green" />
              <DetailField
                label="Actual Result"
                value={test.actualResult ?? '— Not yet executed —'}
                highlight={test.actualResult ? 'amber' : 'none'}
              />
            </div>
            <div className="space-y-3">
              <DetailField label="Execution State" value={execConfig[test.executionState].tip} />
              <DetailField label="Notes" value={test.notes} />
              {test.timestamp && (
                <DetailField
                  label="Last Run"
                  value={new Date(test.timestamp).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' })}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/* ── Detail field in expanded row ────────────────────────── */

function DetailField({
  label,
  value,
  highlight = 'none',
}: {
  label: string
  value: string
  highlight?: 'green' | 'amber' | 'none'
}) {
  const textCls = highlight === 'green' ? 'text-emerald-400/90' : highlight === 'amber' ? 'text-amber-400/90' : 'text-gray-400'
  return (
    <div>
      <p className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-600">{label}</p>
      <p className={`text-xs leading-relaxed ${textCls}`}>{value}</p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Acceptance criterion card
   ═══════════════════════════════════════════════════════════ */

function AcceptanceCriterionCard({
  ac,
  summary,
}: {
  ac: import('@/types/testing').AcceptanceCriterion
  summary: import('@/types/testing').TestSuiteSummary
}) {
  const ran   = summary.mockRun + summary.executed
  const allPending = ran === 0
  const pct   = allPending ? 0 : summary.passRate

  const statusCls = allPending
    ? 'text-gray-500 bg-cyber-800 border-cyber-700/50'
    : pct >= ac.passingThreshold
      ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
      : 'text-amber-400 bg-amber-500/10 border-amber-500/20'

  const statusLabel = allPending
    ? 'Not Yet Executed'
    : pct >= ac.passingThreshold ? 'On Track' : 'Needs Attention'

  const acIcon = ac.code === 'AC-1' ? Target
               : ac.code === 'AC-2' ? ShieldAlert
               : ac.code === 'AC-3' ? TestTube
               : FlaskConical

  const AcIcon = acIcon

  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-5">
      {/* Header */}
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="rounded-md bg-accent-purple/10 p-1.5">
            <AcIcon className="h-4 w-4 text-accent-purple" />
          </div>
          <div>
            <span className="font-mono text-xs font-bold text-accent-purple">{ac.code}</span>
            <p className="text-sm font-semibold text-gray-200">{ac.title}</p>
          </div>
        </div>
        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-xs font-medium ${statusCls}`}>
          {statusLabel}
        </span>
      </div>

      <p className="mb-4 text-xs text-gray-500">{ac.description}</p>

      {/* Test count pills */}
      <div className="mb-3 flex flex-wrap gap-2">
        <Pill label={`${summary.total} Tests`} cls="text-gray-400 bg-cyber-800 border-cyber-700/50" />
        <Pill label={`${summary.notRun} Configured`} cls="text-gray-500 bg-cyber-800 border-cyber-700/50" />
        {summary.mockRun > 0 && <Pill label={`${summary.mockRun} Mock Run`} cls="text-amber-400 bg-amber-500/10 border-amber-500/20" />}
        {summary.passed  > 0 && <Pill label={`${summary.passed} Pass`}    cls="text-emerald-400 bg-emerald-500/10 border-emerald-500/20" />}
        {summary.failed  > 0 && <Pill label={`${summary.failed} Fail`}    cls="text-red-400 bg-red-500/10 border-red-500/20" />}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-cyber-700">
        <div
          className={`h-full rounded-full transition-all ${allPending ? 'bg-cyber-600' : pct >= ac.passingThreshold ? 'bg-emerald-500/70' : 'bg-amber-500/70'}`}
          style={{ width: allPending ? '0%' : `${pct}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-gray-600">
        <span>{allPending ? 'No tests run yet' : `${pct}% pass rate`}</span>
        <span>Target: {ac.passingThreshold}%</span>
      </div>
    </div>
  )
}

/* ── Small helpers ────────────────────────────────────────── */

function Pill({ label, cls }: { label: string; cls: string }) {
  return (
    <span className={`rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      {label}
    </span>
  )
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: number
  icon?: React.ComponentType<{ className?: string }>
  color: string
}) {
  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 px-4 py-3 text-center">
      {Icon && <Icon className={`mx-auto mb-1 h-4 w-4 ${color}`} />}
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-[10px] uppercase tracking-wider text-gray-600">{label}</p>
    </div>
  )
}

function ExecLegendItem({ state }: { state: TestExecutionState }) {
  const cfg = execConfig[state]
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium ${cfg.cls}`}>
        {cfg.label}
      </span>
      <span className="text-gray-600">= {cfg.tip}</span>
    </span>
  )
}
