import {
  Building2,
  Users,
  GitBranch,
  ShieldAlert,
  Target,
  BarChart3,
  AlertTriangle,
  Lock,
  FlaskConical,
} from 'lucide-react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  PieChart,
  Pie,
} from 'recharts'

import { StatCard, ChartCard, StatusBadge, DataTable, SectionHeader, LoadingSpinner, ErrorState } from '@/components/common'
import type { Column } from '@/components/common'
import type { ThreatDetection, OrganizationActivity, SystemComponent } from '@/types/dashboard'
import { useDashboard } from '@/hooks/useDashboard'

/* ── Recharts custom tooltip style ────────────────────────── */

const tooltipStyle = {
  contentStyle: {
    backgroundColor: '#131b2e',
    border: '1px solid rgba(26,37,64,0.7)',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#d1d5db',
  },
  itemStyle: { color: '#d1d5db' },
  labelStyle: { color: '#9ca3af', fontWeight: 600, marginBottom: '4px' },
}




/* ── Recent threats table column definitions ──────────────── */

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
}

const threatColumns: Column<ThreatDetection>[] = [
  {
    key: 'time',
    header: 'Time',
    render: (r) => <span className="whitespace-nowrap font-mono text-xs text-gray-400">{formatTime(r.timestamp)}</span>,
  },
  {
    key: 'org',
    header: 'Organization',
    render: (r) => <span className="text-gray-300">{r.organization}</span>,
  },
  {
    key: 'threat',
    header: 'Threat',
    render: (r) => <span className="font-medium text-gray-200">{r.threatType}</span>,
  },
  {
    key: 'severity',
    header: 'Severity',
    render: (r) => <StatusBadge variant={r.severity} />,
  },
  {
    key: 'confidence',
    header: 'Confidence',
    align: 'right',
    render: (r) => <span className="font-mono text-gray-300">{r.confidence.toFixed(1)}%</span>,
  },
  {
    key: 'status',
    header: 'Status',
    render: (r) => <StatusBadge variant={r.status} />,
  },
]

/* ── Organization activity table columns ──────────────────── */

const orgColumns: Column<OrganizationActivity>[] = [
  {
    key: 'name',
    header: 'Organization',
    render: (r) => (
      <span className="font-medium text-gray-200">
        {r.name}
        {r.isExperimentParticipant && (
          <span className="ml-2 rounded px-1 py-0.5 text-[10px] font-semibold bg-accent-cyan/10 text-accent-cyan">
            Participant
          </span>
        )}
      </span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (r) => <StatusBadge variant={r.status} pulse={r.status === 'active' || r.status === 'training'} />,
  },
  {
    key: 'round',
    header: 'Exp. Round',
    align: 'center',
    render: (r) => (
      r.currentRound !== null
        ? <span className="font-mono text-gray-400">{r.currentRound}</span>
        : <span className="text-xs text-gray-600 italic">Not participant</span>
    ),
  },
  {
    key: 'update',
    header: 'Last Update',
    align: 'right',
    render: (r) => <span className="text-xs text-gray-500">{r.lastUpdate}</span>,
  },
]


/* ── Health status dot color ──────────────────────────────── */

const healthDotColor: Record<string, string> = {
  operational: 'bg-emerald-400',
  degraded: 'bg-amber-400',
  down: 'bg-red-400',
  unknown: 'bg-slate-400',
}

/* ── Dashboard Page ───────────────────────────────────────── */

export default function DashboardPage() {
  const { data, loading, error, refetch } = useDashboard()

  if (loading) return <LoadingSpinner label="Loading dashboard…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { summary, trainingRounds, modelComparison, threatDistribution, orgActivity, recentThreats, systemHealth } = data

  // Local vs Federated chart: determine correct domain to show full range
  const allCompValues = modelComparison.flatMap(m => [m.local, m.federated]).filter(v => v > 0)
  const compMin = allCompValues.length > 0 ? Math.max(0, Math.floor(Math.min(...allCompValues) / 10) * 10) : 0
  const compMax = allCompValues.length > 0 ? Math.min(100, Math.ceil(Math.max(...allCompValues) / 10) * 10 + 5) : 100

  const statCards = [
    {
      label: 'Registered Orgs',
      value: summary.totalOrganizations,
      icon: Building2,
      accent: 'text-accent-blue',
      bgAccent: 'bg-accent-blue/10',
    },
    {
      label: 'Experiment Clients',
      value: `${summary.experimentClients} / ${summary.totalOrganizations}`,
      icon: Users,
      accent: 'text-accent-cyan',
      bgAccent: 'bg-accent-cyan/10',
      // No trend: participation count comes from experiment metadata, not live status
    },
    {
      label: 'Federated Round',
      value: `${summary.currentRound} / ${summary.totalRounds}`,
      icon: GitBranch,
      accent: 'text-accent-purple',
      bgAccent: 'bg-accent-purple/10',
    },
    {
      label: 'Threats Detected',
      value: summary.threatsDetected.toLocaleString(),
      icon: ShieldAlert,
      accent: 'text-accent-red',
      bgAccent: 'bg-accent-red/10',
      // No daily trend: all 5 threat records share the same date; no valid comparison period.
    },
    {
      label: 'Global Accuracy',
      value: `${summary.globalAccuracy}%`,
      icon: Target,
      accent: 'text-accent-green',
      bgAccent: 'bg-accent-green/10',
      // No trend: single final-round value from experiment; no prior experiment for delta.
    },
    {
      label: 'F1 Score',
      value: `${summary.f1Score}%`,
      icon: BarChart3,
      accent: 'text-accent-amber',
      bgAccent: 'bg-accent-amber/10',
    },
    {
      label: 'False-Positive Rate',
      value: `${summary.falsePositiveRate}%`,
      icon: AlertTriangle,
      accent: 'text-orange-400',
      bgAccent: 'bg-orange-400/10',
      // No trend: single final-round value; no prior experiment for delta.
    },
    {
      label: 'Privacy Status',
      value: summary.privacyStatus,
      icon: Lock,
      accent: 'text-accent-green',
      bgAccent: 'bg-accent-green/10',
    },
  ]

  return (
    <div className="space-y-6">
      {/* ── Experiment context banner ─────────────────────── */}
      {summary.experimentId && (
        <div className="flex items-center gap-2 rounded-lg border border-cyber-700/50 bg-cyber-900/60 px-4 py-2 text-xs text-gray-500">
          <FlaskConical className="h-3.5 w-3.5 shrink-0 text-accent-cyan" />
          <span>
            Source experiment: <span className="font-mono text-gray-400">{summary.experimentId}</span>
            {' '}· CICIDS2017 · {summary.experimentClients} clients · {summary.totalRounds} rounds
          </span>
        </div>
      )}

      {/* ── Top summary row ─────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {statCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* ── Privacy detail notice ─────────────────────── */}
      {summary.privacyDetail && (
        <div className="rounded-lg border border-accent-green/20 bg-accent-green/5 px-4 py-2 text-xs text-gray-400">
          <span className="font-semibold text-accent-green">Privacy config: </span>
          {summary.privacyDetail}
        </div>
      )}


      {/* ── Row 1: Training Performance + Local vs Federated ── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard
          title="Federated Training Performance"
          subtitle={`Accuracy, F1 & FPR across ${summary.totalRounds} rounds — ${summary.experimentId ?? 'latest experiment'}`}
          className="xl:col-span-2"
        >
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trainingRounds}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" />
              <XAxis
                dataKey="round"
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
                label={{ value: 'Round', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
              />
              <YAxis
                yAxisId="accuracy"
                domain={[0, 100]}
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
                label={{ value: 'Accuracy / F1 / FPR (%)', angle: -90, position: 'insideLeft', offset: 10, fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip {...tooltipStyle} />
              <Legend
                wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }}
                iconType="circle"
                iconSize={8}
              />
              <Line
                yAxisId="accuracy"
                type="monotone"
                dataKey="accuracy"
                name="Accuracy %"
                stroke="#22d3ee"
                strokeWidth={2}
                dot={{ fill: '#22d3ee', r: 3 }}
                activeDot={{ r: 5, fill: '#22d3ee' }}
              />
              <Line
                yAxisId="accuracy"
                type="monotone"
                dataKey="f1Score"
                name="F1 Score %"
                stroke="#a78bfa"
                strokeWidth={2}
                dot={{ fill: '#a78bfa', r: 3 }}
                activeDot={{ r: 5, fill: '#a78bfa' }}
              />
              <Line
                yAxisId="accuracy"
                type="monotone"
                dataKey="fpr"
                name="FPR %"
                stroke="#f87171"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ fill: '#f87171', r: 3 }}
                activeDot={{ r: 5, fill: '#f87171' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Local vs Federated Model"
          subtitle="Performance comparison across key metrics"
        >
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={modelComparison} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" vertical={false} />
              <XAxis
                dataKey="metric"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
              />
              <YAxis
                domain={[compMin, compMax]}
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
                label={{ value: '%', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip {...tooltipStyle} />
              <Legend
                wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }}
                iconType="circle"
                iconSize={8}
              />
              <Bar dataKey="local" name="Local Model (avg)" fill="#4a6fa5" radius={[4, 4, 0, 0]} maxBarSize={32} />
              <Bar dataKey="federated" name="Federated Model" fill="#22d3ee" radius={[4, 4, 0, 0]} maxBarSize={32} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ── Row 2: Threat Distribution + Organization Activity ── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard
          title="Threat Distribution"
          subtitle={`Detected threat categories across all organizations (${summary.threatsDetected} total)`}
        >
          {threatDistribution.length === 0 ? (
            <p className="py-16 text-center text-sm text-gray-600">No threat detections recorded</p>
          ) : (
            <div className="flex flex-col items-center">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={threatDistribution}
                    dataKey="count"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={90}
                    paddingAngle={2}
                    stroke="none"
                  >
                    {threatDistribution.map((entry) => (
                      <Cell key={entry.category} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip {...tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              {/* Legend below the donut */}
              <div className="mt-2 grid w-full grid-cols-2 gap-x-4 gap-y-1.5">
                {threatDistribution.map((t) => (
                  <div key={t.category} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: t.color }} />
                    <span className="text-xs text-gray-400">{t.category}</span>
                    <span className="ml-auto font-mono text-xs text-gray-500">{t.count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Organization Activity"
          subtitle={`${summary.experimentClients} of ${summary.totalOrganizations} orgs participated in experiment`}
          className="xl:col-span-2"
        >
          <DataTable
            columns={orgColumns}
            data={orgActivity}
            rowKey={(r) => r.id}
            compact
          />
        </ChartCard>
      </div>

      {/* ── Row 3: Recent Threats + System Health ──────────── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard
          title="Recent Threat Detections"
          subtitle="Latest detections across all organizations"
          className="xl:col-span-2"
        >
          {recentThreats.length === 0 ? (
            <p className="py-16 text-center text-sm text-gray-600">No threat detections recorded</p>
          ) : (
            <DataTable
              columns={threatColumns}
              data={recentThreats}
              rowKey={(r) => r.id}
              compact
            />
          )}
        </ChartCard>

        <div className="space-y-4">
          <SectionHeader title="System Health" subtitle="Component status overview" />
          <div className="space-y-2">
            {systemHealth.map((comp) => (
              <SystemHealthRow key={comp.name} component={comp} />
            ))}
          </div>
        </div>
      </div>

      {/* ── Data source notice ──────────────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-600">
        Dashboard sourced from backend API · Experiment: {summary.experimentId ?? 'none'} ·{' '}
        Threat distribution reflects the {summary.threatsDetected} stored detection records.
      </p>

    </div>
  )
}

/* ── System Health Row ────────────────────────────────────── */

function SystemHealthRow({ component }: { component: SystemComponent }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-cyber-700/50 bg-cyber-900 px-4 py-3">
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${healthDotColor[component.status]}`} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-200">{component.name}</span>
          <StatusBadge variant={component.status} />
        </div>
        <p className="mt-0.5 truncate text-xs text-gray-500">{component.detail}</p>
      </div>
    </div>
  )
}
