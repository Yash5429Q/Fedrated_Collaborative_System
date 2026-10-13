import {
  TrendingUp,
  TrendingDown,
  Target,
  ShieldCheck,
  BarChart3,
  GitCompare,
  FlaskConical,
  Award,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts'

import { StatCard, ChartCard, LoadingSpinner, ErrorState } from '@/components/common'
import type { ConfusionMatrix, OrgPerformanceRow, NonIIDResult } from '@/types/performance'
import { usePerformance } from '@/hooks/usePerformance'


/* ── Shared Recharts tooltip style ───────────────────────── */

const TT = {
  contentStyle: {
    backgroundColor: '#131b2e',
    border: '1px solid rgba(26,37,64,0.7)',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#d1d5db',
  },
  itemStyle:  { color: '#d1d5db' },
  labelStyle: { color: '#9ca3af', fontWeight: 600, marginBottom: '4px' },
}

/* ═══════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════ */

export default function PerformancePage() {
  const { data, loading, error, refetch } = usePerformance()

  if (loading) return <LoadingSpinner label="Loading performance data…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const {
    summary: S,
    metricComparisons,
    orgPerformance,
    nonIIDResults,
    perfRounds,
    collaborationBenefit,
    localConfusionMatrix,
    federatedConfusionMatrix,
    experimentInfo,
  } = data

  const expParts = [
    experimentInfo.experimentId ? experimentInfo.experimentId : 'No active experiment',
    experimentInfo.alpha !== null ? `α=${experimentInfo.alpha}` : 'α=—',
    experimentInfo.totalSamples !== null ? `${experimentInfo.totalSamples.toLocaleString()} samples` : '— samples',
    experimentInfo.rounds !== null ? `${experimentInfo.rounds} rounds` : '— rounds',
    experimentInfo.epochs !== null ? `${experimentInfo.epochs} epochs/round` : '— epochs/round',
  ]

  return (
    <div className="space-y-8">
      {/* ── Experiment info banner ─────────────────────── */}
      <div className="flex items-center gap-2 rounded-md border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-2.5">
        <FlaskConical className="h-4 w-4 shrink-0 text-accent-cyan" />
        <p className="text-xs text-gray-400">
          <span className="font-semibold text-accent-cyan">
            {experimentInfo.dataset ? `${experimentInfo.dataset} · ` : 'Dataset: — · '}
          </span>
          {expParts.join(' · ')}
        </p>
      </div>

      {/* ── Summary cards ─────────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Federated vs Local Accuracy"
          value={`+${S.accuracyGain.toFixed(1)}%`}
          icon={TrendingUp}
          accent="text-accent-green"
          bgAccent="bg-accent-green/10"
          trend={{ value: `${S.federatedAccuracy}% fed · ${S.localAvgAccuracy}% local avg`, direction: 'up' }}
        />
        <StatCard
          label="F1 Score Improvement"
          value={`+${S.f1Gain.toFixed(1)}%`}
          icon={Target}
          accent="text-accent-cyan"
          bgAccent="bg-accent-cyan/10"
          trend={{ value: `${S.federatedF1}% fed · ${S.localAvgF1}% local avg`, direction: 'up' }}
        />
        <StatCard
          label="False-Positive Rate Reduction"
          value={`−${S.fprReduction.toFixed(1)}%`}
          icon={ShieldCheck}
          accent="text-accent-purple"
          bgAccent="bg-accent-purple/10"
          trend={{ value: `${S.federatedFPR}% fed · ${S.localAvgFPR}% local avg`, direction: 'up' }}
        />
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 1: Local vs Federated comparison cards
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={GitCompare} title="Local vs Federated — Head-to-Head" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Local card */}
        <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-5">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded bg-amber-500/15 px-2 py-0.5 text-xs font-semibold text-amber-400">
              LOCAL MODELS
            </span>
            <span className="text-xs text-gray-500">Average across all 5 organizations</span>
          </div>
          <div className="space-y-3">
            {metricComparisons.map((m) => (
              <MetricRow
                key={m.label}
                label={m.label}
                value={m.local}
                unit={m.unit}
                max={m.higherIsBetter ? 100 : 20}
                barColor="bg-amber-500/60"
                higherIsBetter={m.higherIsBetter}
              />
            ))}
          </div>
        </div>

        {/* Federated card */}
        <div className="rounded-lg border border-accent-cyan/20 bg-cyber-900 p-5 ring-1 ring-accent-cyan/10">
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded bg-accent-cyan/15 px-2 py-0.5 text-xs font-semibold text-accent-cyan">
              FEDERATED MODEL
            </span>
            <span className="text-xs text-gray-500">Global collaborative model (FedAvg)</span>
          </div>
          <div className="space-y-3">
            {metricComparisons.map((m) => (
              <MetricRow
                key={m.label}
                label={m.label}
                value={m.federated}
                unit={m.unit}
                max={m.higherIsBetter ? 100 : 20}
                barColor="bg-accent-cyan/70"
                higherIsBetter={m.higherIsBetter}
                delta={m.federated - m.local}
                higherDeltaGood={m.higherIsBetter}
              />
            ))}
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 2: Comparison bar chart
          ═══════════════════════════════════════════════ */}
      <ChartCard
        title="Local vs Federated — Metric Comparison"
        subtitle="Grouped bar chart: local model average (orange) vs federated global model (cyan) — CICIDS2017 experiment"
      >
        <ResponsiveContainer width="100%" height={300}>
          <BarChart
            data={metricComparisons.filter((m) => m.unit === '%')}
            margin={{ left: 0, right: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
            />
            <YAxis
              domain={[50, 100]}
              tick={{ fill: '#6b7280', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
              unit="%"
            />
            <Tooltip {...TT} formatter={(v) => [`${Number(v).toFixed(1)}%`]} />
            <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
            <Bar dataKey="local"     name="Local Avg"  fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={32} fillOpacity={0.75} />
            <Bar dataKey="federated" name="Federated"  fill="#22d3ee" radius={[4, 4, 0, 0]} maxBarSize={32} fillOpacity={0.85} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ═══════════════════════════════════════════════
          SECTION 3: Training-round performance chart
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={BarChart3} title="Training-Round Performance" />

      <ChartCard
        title="Accuracy — Local Avg vs Federated per Round"
        subtitle="Per-round IID accuracy from CICIDS2017 experiment (10 rounds, FedAvg, α=0.1)"
      >
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={perfRounds}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" />
            <XAxis
              dataKey="round"
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
              label={{ value: 'Round', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              domain={[55, 100]}
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
              unit="%"
            />
            <Tooltip {...TT} formatter={(v) => [`${Number(v).toFixed(1)}%`]} />
            <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
            <ReferenceLine y={84.7} stroke="#f59e0b" strokeDasharray="4 4" strokeOpacity={0.5} label={{ value: 'Local plateau', fill: '#9ca3af', fontSize: 10 }} />
            <Line type="monotone" dataKey="localAvgAccuracy"   name="Local Avg Accuracy"   stroke="#f59e0b" strokeWidth={2} dot={{ fill: '#f59e0b', r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="federatedAccuracy"  name="Federated Accuracy"   stroke="#22d3ee" strokeWidth={2} dot={{ fill: '#22d3ee', r: 3 }} activeDot={{ r: 5 }} />
            <Line type="monotone" dataKey="localAvgF1"         name="Local Avg F1"         stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
            <Line type="monotone" dataKey="federatedF1"        name="Federated F1"         stroke="#a78bfa" strokeWidth={1.5} strokeDasharray="4 2" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ═══════════════════════════════════════════════
          SECTION 4: Confusion matrices
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={Target} title="Confusion Matrix Comparison" />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ConfusionMatrixViz matrix={localConfusionMatrix} />
        <ConfusionMatrixViz matrix={federatedConfusionMatrix} />
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 5: Organization-wise performance
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={Award} title="Organization-wise Performance" />

      <div className="overflow-hidden rounded-lg border border-cyber-700/50 bg-cyber-900">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-700/50 bg-cyber-800/30">
                {['Organization', 'Local Acc', 'Local F1', 'Local Prec', 'Local Rec', 'Federated Acc', 'Federated F1', 'Gain'].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-700/30">
              {orgPerformance.map((row) => (
                <OrgPerfRow key={row.orgId} row={row} />
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-cyber-700/30 px-4 py-2 text-xs text-gray-600">
          Per-organization metrics from CICIDS2017 experiment (exp_20261005_071403_79eccaf1 · IID run).
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 6: Non-IID robustness experiment
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={FlaskConical} title="Non-IID Robustness Experiment" />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <ChartCard
          title="Non-IID Accuracy vs Distribution Skew"
          subtitle="Dirichlet α controls data heterogeneity (lower α = more heterogeneous) — CICIDS2017 experiment"
        >
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={nonIIDResults} margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" vertical={false} />
              <XAxis
                dataKey="scenario"
                tick={{ fill: '#6b7280', fontSize: 10 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
              />
              <YAxis domain={[50, 100]} tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1a2540' }} unit="%" />
              <Tooltip {...TT} formatter={(v) => [`${Number(v).toFixed(1)}%`]} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
              <Bar dataKey="localAvgAccuracy"    name="Local Avg"  fill="#f59e0b" radius={[4, 4, 0, 0]} maxBarSize={28} fillOpacity={0.75} />
              <Bar dataKey="federatedAccuracy"   name="Federated"  fill="#22d3ee" radius={[4, 4, 0, 0]} maxBarSize={28} fillOpacity={0.85} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Non-IID result cards */}
        <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
            Robustness Score by Scenario
          </p>
          <div className="space-y-3">
            {nonIIDResults.map((r) => (
              <NonIIDScoreRow key={r.scenario} result={r} />
            ))}
          </div>
          <p className="mt-4 text-xs text-gray-600">
            Robustness score = normalized federated accuracy under non-IID conditions (0–100 scale).
          </p>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 7: Collaboration benefit summary
          ═══════════════════════════════════════════════ */}
      <SectionTitle icon={TrendingUp} title="Collaboration Benefit Summary" />

      <div className="overflow-hidden rounded-lg border border-cyber-700/50 bg-cyber-900">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-cyber-700/50 bg-cyber-800/30">
                {['Metric', 'Local Avg', 'Federated', 'Δ Absolute', 'Δ Relative'].map((h) => (
                  <th key={h} className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-700/30">
              {collaborationBenefit.map((row) => (
                <tr key={row.metric} className="hover:bg-cyber-800/20">
                  <td className="px-5 py-3 text-sm font-medium text-gray-200">{row.metric}</td>
                  <td className="px-5 py-3 font-mono text-sm text-amber-400">{row.localAvg.toFixed(1)}{row.metric === 'FPR Reduction' ? '%' : '%'}</td>
                  <td className="px-5 py-3 font-mono text-sm text-accent-cyan">{row.federated.toFixed(1)}%</td>
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1 font-mono text-sm font-semibold text-accent-green">
                      <TrendingUp className="h-3 w-3" />
                      +{row.improvement.toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <span className="rounded-full bg-accent-green/10 px-2 py-0.5 font-mono text-xs font-medium text-accent-green">
                      +{row.improvementPct.toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="border-t border-cyber-700/30 px-5 py-2 text-xs text-gray-600">
          Δ values compare federated global model vs local model average · CICIDS2017 experiment.
        </div>
      </div>

      {/* ── Data source attribution ────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-600">
        All metrics sourced from CICIDS2017 experiment · exp_20261005_071403_79eccaf1 · FedAvg · α=0.1
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Sub-components
   ═══════════════════════════════════════════════════════════ */

function SectionTitle({
  icon: Icon,
  title,
}: {
  icon: React.ComponentType<{ className?: string }>
  title: string
}) {
  return (
    <div className="flex items-center gap-2 border-b border-cyber-700/40 pb-2">
      <Icon className="h-4 w-4 text-accent-cyan" />
      <h3 className="text-sm font-semibold text-gray-200">{title}</h3>
      <span className="ml-2 rounded bg-accent-cyan/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-accent-cyan">
        CICIDS2017
      </span>
    </div>
  )
}

/* ── Single metric row inside comparison card ─────────────── */

function MetricRow({
  label,
  value,
  unit,
  max,
  barColor,
  higherIsBetter: _higherIsBetter,
  delta,
  higherDeltaGood,
}: {
  label: string
  value: number
  unit: string
  max: number
  barColor: string
  higherIsBetter: boolean
  delta?: number
  higherDeltaGood?: boolean
}) {
  const fillPct = Math.min((value / max) * 100, 100)
  const isGood = delta !== undefined
    ? (higherDeltaGood ? delta > 0 : delta < 0)
    : true

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-gray-400">{label}</span>
        <div className="flex items-center gap-2">
          {delta !== undefined && (
            <span className={`flex items-center gap-0.5 text-xs font-medium ${isGood ? 'text-accent-green' : 'text-red-400'}`}>
              {isGood ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {delta > 0 ? '+' : ''}{delta.toFixed(1)}{unit === '%' ? '%' : ''}
            </span>
          )}
          <span className="w-16 text-right font-mono text-sm font-semibold text-gray-200">
            {value.toFixed(1)}{unit === '%' ? '%' : ''}
          </span>
        </div>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-cyber-700">
        <div
          className={`h-full rounded-full transition-all ${barColor}`}
          style={{ width: `${fillPct}%` }}
        />
      </div>
    </div>
  )
}

/* ── Per-org table row ────────────────────────────────────── */

function OrgPerfRow({ row }: { row: OrgPerformanceRow }) {
  const gainColor = row.gain >= 12 ? 'text-accent-green' : row.gain >= 8 ? 'text-cyan-400' : 'text-amber-400'
  return (
    <tr className="hover:bg-cyber-800/20">
      <td className="px-4 py-3 text-sm font-medium text-gray-200">{row.orgName}</td>
      <td className="px-4 py-3 font-mono text-sm text-amber-400">{row.localAccuracy.toFixed(1)}%</td>
      <td className="px-4 py-3 font-mono text-sm text-amber-400">{row.localF1.toFixed(1)}%</td>
      <td className="px-4 py-3 font-mono text-sm text-amber-400">{row.localPrecision.toFixed(1)}%</td>
      <td className="px-4 py-3 font-mono text-sm text-amber-400">{row.localRecall.toFixed(1)}%</td>
      <td className="px-4 py-3 font-mono text-sm text-accent-cyan">{row.federatedAccuracy.toFixed(1)}%</td>
      <td className="px-4 py-3 font-mono text-sm text-accent-cyan">{row.federatedF1.toFixed(1)}%</td>
      <td className="px-4 py-3">
        <span className={`flex items-center gap-1 font-mono text-sm font-bold ${gainColor}`}>
          <TrendingUp className="h-3.5 w-3.5" />
          +{row.gain.toFixed(1)}%
        </span>
      </td>
    </tr>
  )
}

/* ── Non-IID robustness score row ─────────────────────────── */

function NonIIDScoreRow({ result }: { result: NonIIDResult }) {
  const color =
    result.robustnessScore >= 85 ? 'bg-accent-green text-accent-green' :
    result.robustnessScore >= 70 ? 'bg-accent-cyan text-accent-cyan' :
    result.robustnessScore >= 55 ? 'bg-accent-amber text-accent-amber' :
                                   'bg-red-400 text-red-400'
  const [bgCls, textCls] = color.split(' ')

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs text-gray-400">{result.scenario}</span>
        <span className={`font-mono text-sm font-semibold ${textCls}`}>
          {result.robustnessScore}/100
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-cyber-700">
        <div
          className={`h-full rounded-full ${bgCls}/60`}
          style={{ width: `${result.robustnessScore}%` }}
        />
      </div>
    </div>
  )
}

/* ── Confusion matrix visualization ──────────────────────── */

function ConfusionMatrixViz({ matrix }: { matrix: ConfusionMatrix }) {
  const isFed = matrix.modelType === 'federated'
  const labels = matrix.labels

  // Build a 2D lookup: rows = actual, cols = predicted
  const lookup: Record<string, Record<string, number>> = {}
  matrix.cells.forEach(({ actual, predicted, value }) => {
    if (!lookup[actual]) lookup[actual] = {}
    lookup[actual][predicted] = value
  })

  // Find max value for intensity scaling
  const max = Math.max(...matrix.cells.map((c) => c.value))

  return (
    <div className={`rounded-lg border p-5 ${isFed ? 'border-accent-cyan/20 bg-cyber-900 ring-1 ring-accent-cyan/10' : 'border-cyber-700/50 bg-cyber-900'}`}>
      <div className="mb-3 flex items-center gap-2">
        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${isFed ? 'bg-accent-cyan/15 text-accent-cyan' : 'bg-amber-500/15 text-amber-400'}`}>
          {isFed ? 'FEDERATED MODEL' : 'LOCAL MODEL (avg)'}
        </span>
        <span className="text-xs text-gray-600">CICIDS2017</span>
      </div>
      <p className="mb-4 text-xs text-gray-500">Rows = Actual class · Columns = Predicted class</p>

      <div className="overflow-x-auto">
        <table className="w-full text-center">
          <thead>
            <tr>
              <th className="pb-2 pr-2 text-left text-[10px] text-gray-600">Actual ↓ / Pred →</th>
              {labels.map((l) => (
                <th key={l} className="pb-2 text-[11px] font-semibold text-gray-400">{l}</th>
              ))}
            </tr>
          </thead>
          <tbody className="space-y-1">
            {labels.map((actual) => (
              <tr key={actual}>
                <td className="pr-2 text-left text-[11px] font-semibold text-gray-400">{actual}</td>
                {labels.map((predicted) => {
                  const val = lookup[actual]?.[predicted] ?? 0
                  const intensity = val / max
                  const isCorrect = actual === predicted
                  return (
                    <td
                      key={predicted}
                      className="relative p-1"
                      title={`Actual: ${actual} → Predicted: ${predicted}: ${val}`}
                    >
                      <div
                        className={`flex h-12 w-full items-center justify-center rounded text-xs font-mono font-medium transition-all ${
                          isCorrect
                            ? isFed ? 'text-accent-cyan' : 'text-amber-400'
                            : 'text-gray-500'
                        }`}
                        style={{
                          backgroundColor: isCorrect
                            ? isFed
                              ? `rgba(34,211,238,${0.1 + intensity * 0.5})`
                              : `rgba(245,158,11,${0.1 + intensity * 0.5})`
                            : `rgba(239,68,68,${intensity * 0.25})`,
                        }}
                      >
                        {val.toLocaleString()}
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

