import {
  GitBranch,
  Globe,
  Users,
  Timer,
  Layers,
  ArrowDown,
  CheckCircle2,
  Cpu,
  Merge,
  Target,
  Shield,
  Lock,
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
} from 'recharts'

import { StatCard, StatusBadge, ChartCard, DataTable, LoadingSpinner, ErrorState } from '@/components/common'
import type { Column } from '@/components/common'
import type { TrainingRound, ClientRoundStatus } from '@/types/training'
import { useTraining } from '@/hooks/useTraining'


/* ── Recharts tooltip style ───────────────────────────────── */

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

/* ── Round history table columns ──────────────────────────── */

const roundColumns: Column<TrainingRound>[] = [
  {
    key: 'round',
    header: 'Round',
    render: (r) => <span className="font-mono font-medium text-gray-200">R{r.round}</span>,
  },
  {
    key: 'status',
    header: 'Status',
    render: (r) => <StatusBadge variant={r.status} label={r.status.replace('_', ' ')} />,
  },
  {
    key: 'clients',
    header: 'Clients',
    align: 'center',
    render: (r) => (
      <span className="font-mono text-gray-300">
        {r.participatingClients}/{r.totalClients}
      </span>
    ),
  },
  {
    key: 'accuracy',
    header: 'Accuracy',
    align: 'right',
    render: (r) => <span className="font-mono text-gray-300">{r.globalAccuracy.toFixed(1)}%</span>,
  },
  {
    key: 'loss',
    header: 'FPR (%)',
    align: 'right',
    render: (r) => <span className="font-mono text-gray-400">{r.globalLoss.toFixed(2)}%</span>,
  },
  {
    key: 'f1',
    header: 'F1',
    align: 'right',
    render: (r) => <span className="font-mono text-gray-300">{r.globalF1.toFixed(1)}%</span>,
  },
  {
    key: 'duration',
    header: 'Duration',
    align: 'right',
    render: (r) => <span className="text-xs text-gray-500">{r.duration}</span>,
  },
  {
    key: 'model',
    header: 'Model',
    align: 'right',
    render: (r) => <span className="font-mono text-xs text-accent-cyan">{r.globalModelVersion}</span>,
  },
]

/* ── Client status table columns ──────────────────────────── */

const clientColumns: Column<ClientRoundStatus>[] = [
  {
    key: 'org',
    header: 'Organization',
    render: (r) => <span className="font-medium text-gray-200">{r.orgName}</span>,
  },
  {
    key: 'connection',
    header: 'Connection',
    render: (r) => (
      <StatusBadge
        variant={r.orgStatus}
        pulse={r.orgStatus === 'active' || r.orgStatus === 'training'}
      />
    ),
  },
  {
    key: 'training',
    header: 'Training',
    render: (r) => <StatusBadge variant={r.clientStatus} />,
  },
  {
    key: 'accuracy',
    header: 'Local Acc',
    align: 'right',
    render: (r) => (
      <span className="font-mono text-gray-300">
        {r.localAccuracy !== null ? `${r.localAccuracy}%` : '—'}
      </span>
    ),
  },
  {
    key: 'loss',
    header: 'Local Loss',
    align: 'right',
    render: (r) => (
      <span className="font-mono text-gray-400">
        {r.localLoss !== null ? r.localLoss.toFixed(3) : '—'}
      </span>
    ),
  },
  {
    key: 'samples',
    header: 'Samples',
    align: 'right',
    render: (r) => (
      <span className="text-gray-400">
        {r.samplesUsed > 0 ? r.samplesUsed.toLocaleString() : '—'}
      </span>
    ),
  },
  {
    key: 'update',
    header: 'Update',
    align: 'right',
    render: (r) => (
      <span className="text-xs text-gray-500">{r.updateSize ?? '—'}</span>
    ),
  },
  {
    key: 'duration',
    header: 'Time',
    align: 'right',
    render: (r) => (
      <span className="text-xs text-gray-500">{r.duration ?? '—'}</span>
    ),
  },
]

/* ═══════════════════════════════════════════════════════════
   Training Page
   ═══════════════════════════════════════════════════════════ */

export default function TrainingPage() {
  const { data, loading, error, refetch } = useTraining()

  if (loading) return <LoadingSpinner label="Loading training data…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { summary, clientStatuses, roundHistory, participation } = data
  const reversedHistory = [...roundHistory].reverse()

  return (
    <div className="space-y-6">
      {/* ── Summary stat cards ────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <StatCard
          label="Current Round"
          value={`${summary.currentRound} / ${summary.totalRounds}`}
          icon={GitBranch}
          accent="text-accent-purple"
          bgAccent="bg-accent-purple/10"
        />
        <StatCard
          label="Global Model"
          value={summary.globalModelVersion}
          icon={Globe}
          accent="text-accent-cyan"
          bgAccent="bg-accent-cyan/10"
        />
        <StatCard
          label="Participants"
          value={`${summary.participatingClients} / ${summary.totalClients}`}
          icon={Users}
          accent="text-accent-blue"
          bgAccent="bg-accent-blue/10"
        />
        <StatCard
          label="Global Accuracy"
          value={`${summary.globalAccuracy}%`}
          icon={Target}
          accent="text-accent-green"
          bgAccent="bg-accent-green/10"
          trend={{ value: '+0.6%', direction: 'up' }}
        />
        <StatCard
          label="Avg Round Time"
          value={summary.avgRoundDuration}
          icon={Timer}
          accent="text-accent-amber"
          bgAccent="bg-accent-amber/10"
        />
        <StatCard
          label="Aggregation"
          value={summary.aggregationMethod}
          icon={Layers}
          accent="text-orange-400"
          bgAccent="bg-orange-400/10"
        />
      </div>

      {/* ── Federated Learning Workflow ────────────────── */}
      <FederatedWorkflow summary={summary} clientStatuses={clientStatuses} />

      {/* ── Row: Charts ───────────────────────────────── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Accuracy & F1 vs Round */}
        <ChartCard
          title="Accuracy & F1 per Round"
          subtitle="Global model performance across federated rounds"
          className="xl:col-span-2"
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={roundHistory}>
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
                label={{ value: '%', angle: -90, position: 'insideLeft', offset: 10, fill: '#6b7280', fontSize: 11 }}
              />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
              <Line type="monotone" dataKey="globalAccuracy" name="Accuracy" stroke="#22d3ee" strokeWidth={2} dot={{ fill: '#22d3ee', r: 3 }} activeDot={{ r: 5 }} />
              <Line type="monotone" dataKey="globalF1" name="F1 Score" stroke="#a78bfa" strokeWidth={2} dot={{ fill: '#a78bfa', r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Loss vs Round */}
        <ChartCard
          title="Loss per Round"
          subtitle="Global model loss convergence"
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={roundHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" />
              <XAxis
                dataKey="round"
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
              />
              <Tooltip {...tooltipStyle} />
              <Line type="monotone" dataKey="globalLoss" name="Loss" stroke="#f87171" strokeWidth={2} dot={{ fill: '#f87171', r: 3 }} activeDot={{ r: 5, fill: '#f87171' }} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ── Client Participation Chart ─────────────────── */}
      <ChartCard
        title="Client Participation per Round"
        subtitle="Number of organizations contributing to each federated round"
      >
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={participation}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" vertical={false} />
            <XAxis
              dataKey="round"
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
              label={{ value: 'Round', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }}
            />
            <YAxis
              domain={[0, 6]}
              tick={{ fill: '#6b7280', fontSize: 12 }}
              tickLine={false}
              axisLine={{ stroke: '#1a2540' }}
              allowDecimals={false}
            />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
            <Bar dataKey="participating" name="Participating" fill="#22d3ee" radius={[4, 4, 0, 0]} maxBarSize={28} />
            <Bar dataKey="total" name="Total" fill="#1a2540" radius={[4, 4, 0, 0]} maxBarSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Client Status for Current Round ────────────── */}
      <ChartCard
        title={`Client Status — Round ${summary.currentRound}`}
        subtitle="Per-organization training status, local metrics, and model update details"
      >
        <DataTable
          columns={clientColumns}
          data={clientStatuses}
          rowKey={(r) => r.orgId}
          compact
        />
      </ChartCard>

      {/* ── Round History Table ────────────────────────── */}
      <ChartCard
        title="Round History"
        subtitle="Complete record of all federated training rounds"
      >
        <DataTable
          columns={roundColumns}
          data={reversedHistory}
          rowKey={(r) => String(r.round)}
          compact
        />
      </ChartCard>

      {/* ── Mock data notice ──────────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-600">
        Training data is simulated — will connect to Flower server and backend API in a later phase.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Federated Learning Workflow Diagram
   ═══════════════════════════════════════════════════════════ */

function FederatedWorkflow({
  summary,
  clientStatuses,
}: {
  summary: import('@/types/training').TrainingPageSummary
  clientStatuses: import('@/types/training').ClientRoundStatus[]
}) {
  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-6">
      <h3 className="mb-1 text-sm font-semibold text-gray-200">
        Federated Learning Workflow
      </h3>
      <p className="mb-5 text-xs text-gray-500">
        Decentralized training pipeline — raw data never leaves organization boundaries
      </p>

      {/* Workflow steps */}
      <div className="flex flex-col items-center gap-2">
        {/* Step 1: Global Model */}
        <WorkflowNode
          icon={Globe}
          label="Global Model"
          detail={`${summary.globalModelVersion} — ${summary.globalAccuracy}% accuracy`}
          color="text-accent-cyan"
          bgColor="bg-accent-cyan/10"
          borderColor="border-accent-cyan/30"
          isActive
        />
        <WorkflowArrow label="Distribute to clients" />

        {/* Step 2: Organization Clients */}
        <div className="flex w-full max-w-3xl flex-wrap justify-center gap-3">
          {clientStatuses.map((client) => (
            <div
              key={client.orgId}
              className={`flex items-center gap-2 rounded-md border px-3 py-2 text-xs ${
                client.clientStatus === 'offline'
                  ? 'border-cyber-700/50 bg-cyber-800/30 text-gray-500'
                  : 'border-accent-blue/20 bg-accent-blue/5 text-gray-300'
              }`}
            >
              <Cpu className="h-3.5 w-3.5" />
              <span>{client.orgName}</span>
              <StatusBadge variant={client.clientStatus} />
            </div>
          ))}
        </div>
        <WorkflowArrow label="Local training on private data" />

        {/* Step 3: Local Training */}
        <WorkflowNode
          icon={Cpu}
          label="Local Training"
          detail={`${summary.totalEpochsCompleted} total epochs — data stays local`}
          color="text-accent-blue"
          bgColor="bg-accent-blue/10"
          borderColor="border-accent-blue/30"
        />
        <WorkflowArrow label="Extract model updates only" />

        {/* Step 4: Protected Model Updates */}
        <WorkflowNode
          icon={Lock}
          label="Protected Model Updates"
          detail="Only model weight updates transmitted — not raw data"
          color="text-accent-amber"
          bgColor="bg-accent-amber/10"
          borderColor="border-accent-amber/30"
        />
        <WorkflowArrow label="Send to aggregation server" />

        {/* Step 5: Aggregation */}
        <WorkflowNode
          icon={Merge}
          label={`Aggregation (${summary.aggregationMethod})`}
          detail={`${summary.participatingClients} client updates combined into global model`}
          color="text-accent-purple"
          bgColor="bg-accent-purple/10"
          borderColor="border-accent-purple/30"
        />
        <WorkflowArrow label="Evaluate and publish" />

        {/* Step 6: Updated Global Model */}
        <WorkflowNode
          icon={CheckCircle2}
          label="Updated Global Model"
          detail={`${summary.globalModelVersion} — F1: ${summary.globalF1}% | Loss: ${summary.globalLoss}`}
          color="text-accent-green"
          bgColor="bg-accent-green/10"
          borderColor="border-accent-green/30"
          isActive
        />
      </div>

      {/* Key differentiator callout */}
      <div className="mt-6 flex items-start gap-3 rounded-md border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-3">
        <Shield className="mt-0.5 h-4 w-4 shrink-0 text-accent-cyan" />
        <div>
          <p className="text-xs font-medium text-accent-cyan">
            Federated — Not Centralized
          </p>
          <p className="mt-0.5 text-xs text-gray-500">
            Each organization trains locally on its own data. Only model parameter
            updates are shared with the central server. Raw training data never
            crosses organizational boundaries.
          </p>
        </div>
      </div>
    </div>
  )
}

/* ── Workflow node ────────────────────────────────────────── */

function WorkflowNode({
  icon: Icon,
  label,
  detail,
  color,
  bgColor,
  borderColor,
  isActive,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  detail: string
  color: string
  bgColor: string
  borderColor: string
  isActive?: boolean
}) {
  return (
    <div
      className={`flex w-full max-w-md items-center gap-3 rounded-lg border px-4 py-3 ${borderColor} ${bgColor}`}
    >
      <div className={`rounded-md p-2 ${bgColor}`}>
        <Icon className={`h-5 w-5 ${color}`} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${color}`}>{label}</span>
          {isActive && (
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-50" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
          )}
        </div>
        <p className="truncate text-xs text-gray-500">{detail}</p>
      </div>
    </div>
  )
}

/* ── Workflow arrow ───────────────────────────────────────── */

function WorkflowArrow({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5 py-1">
      <ArrowDown className="h-4 w-4 text-cyber-500" />
      <span className="text-[10px] tracking-wide text-gray-600">{label}</span>
    </div>
  )
}
