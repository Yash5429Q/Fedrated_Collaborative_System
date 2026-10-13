import { useState } from 'react'
import {
  Building2,
  Users,
  Wifi,
  WifiOff,
  Database,
  Search,
  ChevronDown,
  ChevronUp,
  Clock,
  Cpu,
  Shield,
  Network,
  BarChart3,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

import { StatCard, StatusBadge, ChartCard, LoadingSpinner, ErrorState } from '@/components/common'
import type { Organization } from '@/types/organization'
import { useOrganizations } from '@/hooks/useOrganizations'


/* ── Recharts tooltip style (reused from dashboard) ───────── */

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

/* ── Status filter options ────────────────────────────────── */

type StatusFilter = 'all' | 'active' | 'training' | 'idle' | 'offline'

const statusFilters: { value: StatusFilter; label: string }[] = [
  { value: 'all',      label: 'All' },
  { value: 'active',   label: 'Active' },
  { value: 'training', label: 'Training' },
  { value: 'idle',     label: 'Idle' },
  { value: 'offline',  label: 'Offline' },
]

/* ── Page Component ───────────────────────────────────────── */

export default function OrganizationsPage() {
  const { data, loading, error, refetch } = useOrganizations()
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [expandedOrg, setExpandedOrg] = useState<string | null>(null)

  if (loading) return <LoadingSpinner label="Loading organizations…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { organizations, summary } = data
  const totalDataPoints = organizations.reduce((sum, o) => sum + o.datasetSize, 0)

  const filteredOrgs = organizations.filter((org) => {
    const matchesSearch =
      searchQuery === '' ||
      org.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      org.id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus =
      statusFilter === 'all' || org.status === statusFilter
    return matchesSearch && matchesStatus
  })

  const toggleExpand = (orgId: string) => {
    setExpandedOrg((prev) => (prev === orgId ? null : orgId))
  }

  return (
    <div className="space-y-6">
      {/* ── Summary stat cards ────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Organizations"
          value={summary.total}
          icon={Building2}
          accent="text-accent-blue"
          bgAccent="bg-accent-blue/10"
        />
        <StatCard
          label="Connected"
          value={`${summary.active + summary.training} / ${summary.total}`}
          icon={Users}
          accent="text-accent-green"
          bgAccent="bg-accent-green/10"
          trend={{ value: `${summary.offline} offline`, direction: 'down' }}
        />
        <StatCard
          label="Total Data Points"
          value={`${(totalDataPoints / 1000).toFixed(1)}k`}
          icon={Database}
          accent="text-accent-cyan"
          bgAccent="bg-accent-cyan/10"
        />
        <StatCard
          label="Offline"
          value={summary.offline}
          icon={BarChart3}
          accent="text-accent-purple"
          bgAccent="bg-accent-purple/10"
        />
      </div>


      {/* ── Search & filter bar ───────────────────────── */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search organizations…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-md border border-cyber-700/50 bg-cyber-800/50 py-2 pl-9 pr-3 text-sm text-gray-200 placeholder-gray-500 outline-none transition-colors focus:border-accent-cyan/50 focus:ring-1 focus:ring-accent-cyan/20"
          />
        </div>

        <div className="flex gap-1.5">
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                statusFilter === f.value
                  ? 'bg-accent-cyan/15 text-accent-cyan'
                  : 'text-gray-500 hover:bg-cyber-800 hover:text-gray-300'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Organization cards ────────────────────────── */}
      <div className="space-y-3">
        {filteredOrgs.length === 0 ? (
          <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-12 text-center">
            <Building2 className="mx-auto h-8 w-8 text-cyber-600" />
            <p className="mt-3 text-sm text-gray-500">
              No organizations match the current filters.
            </p>
          </div>
        ) : (
          filteredOrgs.map((org) => (
            <OrganizationCard
              key={org.id}
              org={org}
              isExpanded={expandedOrg === org.id}
              onToggle={() => toggleExpand(org.id)}
            />
          ))
        )}
      </div>

      {/* ── Mock data notice ──────────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-600">
        Organization data is simulated — will connect to backend API in a later phase.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Organization Card (collapsed + expandable detail)
   ═══════════════════════════════════════════════════════════ */

function OrganizationCard({
  org,
  isExpanded,
  onToggle,
}: {
  org: Organization
  isExpanded: boolean
  onToggle: () => void
}) {
  const isConnected = org.status === 'active' || org.status === 'training'

  return (
    <div className="overflow-hidden rounded-lg border border-cyber-700/50 bg-cyber-900">
      {/* ── Collapsed row ──────────────────────────── */}
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-4 px-5 py-4 text-left transition-colors hover:bg-cyber-800/30"
      >
        {/* Connection indicator */}
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${isConnected ? 'bg-accent-cyan/10' : 'bg-cyber-800'}`}>
          {isConnected ? (
            <Wifi className="h-5 w-5 text-accent-cyan" />
          ) : (
            <WifiOff className="h-5 w-5 text-gray-600" />
          )}
        </div>

        {/* Name + description */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-gray-100">{org.name}</span>
            <StatusBadge
              variant={org.status}
              pulse={org.status === 'training'}
            />
          </div>
          <p className="mt-0.5 truncate text-xs text-gray-500">
            {org.description}
          </p>
        </div>

        {/* Quick stats */}
        <div className="hidden items-center gap-6 lg:flex">
          <QuickStat label="Dataset" value={`${(org.datasetSize / 1000).toFixed(1)}k`} />
          <QuickStat label="Round" value={org.currentRound !== null ? `${org.currentRound}/${org.totalRounds ?? org.currentRound}` : '—'} />
          <QuickStat label="Model" value={org.localModel.version} />
          <QuickStat label="Accuracy" value={org.localModel.accuracy !== null ? `${org.localModel.accuracy}%` : '—'} />
          <QuickStat label="Updated" value={org.lastUpdate} />
        </div>

        {/* Expand chevron */}
        <div className="shrink-0 text-gray-500">
          {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </div>
      </button>

      {/* ── Expanded detail ────────────────────────── */}
      {isExpanded && <OrganizationDetail org={org} />}
    </div>
  )
}

/* ── Quick stat in collapsed row ──────────────────────────── */

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-right">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-medium text-gray-300">{value}</p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Organization Detail (expanded view)
   ═══════════════════════════════════════════════════════════ */

function OrganizationDetail({ org }: { org: Organization }) {
  return (
    <div className="border-t border-cyber-700/50 bg-cyber-900/50 px-5 py-5">
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* ── Column 1: Info + Model ──────────────── */}
        <div className="space-y-5">
          {/* Organization info */}
          <DetailSection title="Organization Details" icon={Building2}>
            <DetailRow label="ID" value={org.id} mono />
            <DetailRow label="Status" badge={org.status} />
            <DetailRow label="Joined" value={formatDate(org.joinedAt)} />
            <DetailRow label="Latency" value={org.networkLatency} />
            <DetailRow label="Privacy" value={org.privacyMode} />
            <DetailRow label="Threats Found" value={org.threatsDetected != null ? org.threatsDetected.toLocaleString() : 'N/A'} />
          </DetailSection>

          {/* Local model info */}
          <DetailSection title="Local Model" icon={Cpu}>
            <DetailRow label="Status" badge={org.localModel.status} />
            <DetailRow label="Version" value={org.localModel.version} mono />
            <DetailRow label="Accuracy" value={org.localModel.accuracy !== null ? `${org.localModel.accuracy}%` : 'N/A'} />
            <DetailRow label="Loss" value={org.localModel.loss != null ? org.localModel.loss.toFixed(3) : 'N/A'} />
            <DetailRow label="Epochs" value={org.localModel.epochs > 0 ? String(org.localModel.epochs) : 'N/A'} />
            <DetailRow label="Last Trained" value={formatDate(org.localModel.lastTrained)} />
          </DetailSection>

          {/* Dataset info */}
          <DetailSection title="Dataset" icon={Database}>
            <DetailRow label="Total Samples" value={org.datasetSize.toLocaleString()} />
            <DetailRow label="Split" value={org.datasetSplit} />
          </DetailSection>
        </div>

        {/* ── Column 2: Data Distribution ─────────── */}
        <div className="space-y-5">
          <ChartCard
            title="Data Distribution (Non-IID)"
            subtitle="Local threat-type distribution — varies per organization"
          >
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={org.dataDistribution}
                layout="vertical"
                margin={{ left: 10, right: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" horizontal={false} />
                <XAxis
                  type="number"
                  domain={[0, 40]}
                  tick={{ fill: '#6b7280', fontSize: 11 }}
                  tickLine={false}
                  axisLine={{ stroke: '#1a2540' }}
                  unit="%"
                />
                <YAxis
                  type="category"
                  dataKey="threatType"
                  tick={{ fill: '#9ca3af', fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  width={110}
                />
                <Tooltip
                  {...tooltipStyle}
                  formatter={(value) => [`${value}%`, 'Share']}
                />
                <Bar dataKey="percentage" radius={[0, 4, 4, 0]} maxBarSize={18}>
                  {org.dataDistribution.map((entry) => (
                    <Cell key={entry.threatType} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Distribution legend / breakdown */}
          <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Distribution Breakdown
            </p>
            <div className="space-y-2">
              {org.dataDistribution.map((slice) => (
                <div key={slice.threatType} className="flex items-center gap-3">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: slice.color }}
                  />
                  <span className="flex-1 text-sm text-gray-400">{slice.threatType}</span>
                  <span className="font-mono text-xs text-gray-500">
                    {slice.count.toLocaleString()}
                  </span>
                  <span className="w-10 text-right font-mono text-xs text-gray-300">
                    {slice.percentage}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── Column 3: Training Participation ────── */}
        <div className="space-y-5">
          {/* Participation summary */}
          <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
            <div className="mb-3 flex items-center gap-2">
              <Shield className="h-4 w-4 text-accent-purple" />
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                Training Participation
              </p>
            </div>
            <div className="flex items-end gap-3">
              <span className="text-3xl font-bold text-gray-100">
                {org.contribution}%
              </span>
              <span className="mb-1 text-xs text-gray-500">
                of rounds participated
              </span>
            </div>
            {/* Visual progress ring approximation */}
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-cyber-700">
              <div
                className="h-full rounded-full bg-accent-purple transition-all"
                style={{ width: `${org.contribution}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-500">
              <span>Round 1</span>
              <span>Round {org.totalRounds}</span>
            </div>
          </div>

          {/* Recent training rounds table */}
          <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
            <div className="mb-3 flex items-center gap-2">
              <Network className="h-4 w-4 text-accent-cyan" />
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                Recent Rounds
              </p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-cyber-700/40">
                    <th className="pb-2 text-left text-xs font-semibold text-gray-500">Round</th>
                    <th className="pb-2 text-left text-xs font-semibold text-gray-500">Status</th>
                    <th className="pb-2 text-right text-xs font-semibold text-gray-500">Acc</th>
                    <th className="pb-2 text-right text-xs font-semibold text-gray-500">Loss</th>
                    <th className="pb-2 text-right text-xs font-semibold text-gray-500">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyber-700/30">
                  {org.trainingHistory.map((rnd) => (
                    <tr key={rnd.round}>
                      <td className="py-2 font-mono text-sm text-gray-300">
                        R{rnd.round}
                      </td>
                      <td className="py-2">
                        {rnd.participated ? (
                          <span className="inline-flex items-center gap-1 text-xs text-emerald-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                            Participated
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                            <span className="h-1.5 w-1.5 rounded-full bg-gray-600" />
                            Skipped
                          </span>
                        )}
                      </td>
                      <td className="py-2 text-right font-mono text-sm text-gray-300">
                        {rnd.participated ? `${rnd.localAccuracy}%` : '—'}
                      </td>
                      <td className="py-2 text-right font-mono text-sm text-gray-400">
                        {rnd.participated ? (rnd.localLoss != null ? rnd.localLoss.toFixed(3) : 'N/A') : '—'}
                      </td>
                      <td className="py-2 text-right text-xs text-gray-500">
                        {rnd.duration}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Connection info */}
          <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
            <div className="mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-500" />
              <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                Connection
              </p>
            </div>
            <div className="space-y-2">
              <DetailRow label="Round" value={`${org.currentRound} / ${org.totalRounds}`} />
              <DetailRow label="Last Update" value={org.lastUpdate} />
              <DetailRow label="Network" value={org.networkLatency} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Shared helper sub-components
   ═══════════════════════════════════════════════════════════ */

function DetailSection({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}) {
  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-accent-cyan" />
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-500">
          {title}
        </p>
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function DetailRow({
  label,
  value,
  badge,
  mono,
}: {
  label: string
  value?: string
  badge?: string
  mono?: boolean
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-gray-500">{label}</span>
      {badge ? (
        <StatusBadge variant={badge as never} />
      ) : (
        <span className={`text-sm text-gray-300 ${mono ? 'font-mono' : ''}`}>
          {value}
        </span>
      )}
    </div>
  )
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
