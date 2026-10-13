import { useState } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  AlertOctagon,
  Info,
  X,
  Search,
  ExternalLink,
  Clock,
  Server,
  Fingerprint,
  Network,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts'

import { StatCard, StatusBadge, ChartCard, DataTable, LoadingSpinner, ErrorState } from '@/components/common'
import type { Column } from '@/components/common'
import type { ThreatDetectionDetail } from '@/types/threats'
import { useThreats } from '@/hooks/useThreats'

/* ── Static filter option lists ─────────────────────────────── */

const threatOrganizations = ['Organization Alpha', 'Organization Beta', 'Organization Gamma', 'Organization Delta', 'Organization Epsilon']
const threatTypes          = ['DoS/DDoS', 'Brute Force', 'Port Scan', 'Malware', 'SQL Injection', 'XSS', 'Data Exfiltration', 'Privilege Escalation']
const severityLevels       = ['critical', 'high', 'medium', 'low']
const statusOptions        = ['detected', 'blocked', 'investigating', 'resolved']


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

/* ── Filter state type ────────────────────────────────────── */

interface Filters {
  search: string
  organization: string
  threatType: string
  severity: string
  status: string
}

const defaultFilters: Filters = {
  search: '',
  organization: '',
  threatType: '',
  severity: '',
  status: '',
}

/* ── Table columns ────────────────────────────────────────── */

function formatTimestamp(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function buildColumns(onSelect: (t: ThreatDetectionDetail) => void): Column<ThreatDetectionDetail>[] {
  return [
    {
      key: 'timestamp',
      header: 'Time',
      render: (r) => (
        <span className="whitespace-nowrap font-mono text-xs text-gray-400">
          {formatTimestamp(r.timestamp)}
        </span>
      ),
    },
    {
      key: 'org',
      header: 'Organization',
      render: (r) => <span className="text-gray-300">{r.organization}</span>,
    },
    {
      key: 'type',
      header: 'Threat Type',
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
      render: (r) => (
        <div className="flex items-center justify-end gap-2">
          <div className="h-1.5 w-12 overflow-hidden rounded-full bg-cyber-700">
            <div
              className={`h-full rounded-full ${r.confidence >= 90 ? 'bg-accent-green' : r.confidence >= 80 ? 'bg-accent-amber' : 'bg-accent-red'}`}
              style={{ width: `${r.confidence}%` }}
            />
          </div>
          <span className="w-12 text-right font-mono text-xs text-gray-300">
            {r.confidence.toFixed(1)}%
          </span>
        </div>
      ),
    },
    {
      key: 'model',
      header: 'Model',
      align: 'center',
      render: (r) => (
        <span className="font-mono text-xs text-accent-cyan">{r.modelVersion}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (r) => <StatusBadge variant={r.status} />,
    },
    {
      key: 'action',
      header: '',
      align: 'center',
      render: (r) => (
        <button
          onClick={(e) => { e.stopPropagation(); onSelect(r) }}
          className="rounded p-1 text-gray-500 transition-colors hover:bg-cyber-800 hover:text-accent-cyan"
          title="View details"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </button>
      ),
    },
  ]
}

/* ═══════════════════════════════════════════════════════════
   Threats Page
   ═══════════════════════════════════════════════════════════ */

export default function ThreatsPage() {
  const [filters, setFilters] = useState<Filters>(defaultFilters)
  const [selectedThreat, setSelectedThreat] = useState<ThreatDetectionDetail | null>(null)

  const { data, loading, error, refetch } = useThreats({
    organization: filters.organization || undefined,
    threatType:   filters.threatType   || undefined,
    severity:     filters.severity     || undefined,
    status:       filters.status       || undefined,
    search:       filters.search       || undefined,
  })

  if (loading) return <LoadingSpinner label="Loading threat detections…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { summary, detections, distribution, timeline } = data

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }))
  }

  const clearFilters = () => setFilters(defaultFilters)

  const hasActiveFilters = Object.values(filters).some((v) => v !== '')

  const filteredThreats = detections

  const columns = buildColumns(setSelectedThreat)

  return (
    <div className="space-y-6">
      {/* ── Severity summary cards ────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Total Detections"
          value={summary.total.toLocaleString()}
          icon={ShieldAlert}
          accent="text-accent-cyan"
          bgAccent="bg-accent-cyan/10"
        />
        <StatCard
          label="Critical"

          value={summary.critical}
          icon={AlertOctagon}
          accent="text-red-400"
          bgAccent="bg-red-400/10"
        />
        <StatCard
          label="High"
          value={summary.high}
          icon={AlertTriangle}
          accent="text-orange-400"
          bgAccent="bg-orange-400/10"
        />
        <StatCard
          label="Medium"
          value={summary.medium}
          icon={AlertTriangle}
          accent="text-amber-400"
          bgAccent="bg-amber-400/10"
        />
        <StatCard
          label="Low"
          value={summary.low}
          icon={Info}
          accent="text-blue-400"
          bgAccent="bg-blue-400/10"
        />
      </div>

      {/* ── Charts row: Timeline + Distribution ───────── */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <ChartCard
          title="Threat Timeline (24h)"
          subtitle="Detection volume by severity over the last 24 hours"
          className="xl:col-span-2"
        >
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" />
              <XAxis
                dataKey="hour"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
                interval={2}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 12 }}
                tickLine={false}
                axisLine={{ stroke: '#1a2540' }}
              />
              <Tooltip {...tooltipStyle} />
              <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} iconType="circle" iconSize={8} />
              <Area type="monotone" dataKey="critical" name="Critical" stackId="1" stroke="#f87171" fill="#f87171" fillOpacity={0.3} />
              <Area type="monotone" dataKey="high" name="High" stackId="1" stroke="#fb923c" fill="#fb923c" fillOpacity={0.25} />
              <Area type="monotone" dataKey="medium" name="Medium" stackId="1" stroke="#fbbf24" fill="#fbbf24" fillOpacity={0.2} />
              <Area type="monotone" dataKey="low" name="Low" stackId="1" stroke="#60a5fa" fill="#60a5fa" fillOpacity={0.15} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title="Threat Distribution"
          subtitle="Detections by attack category"
        >
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={distribution} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(26,37,64,0.6)" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={{ stroke: '#1a2540' }} />
              <YAxis type="category" dataKey="type" tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} axisLine={false} width={120} />
              <Tooltip {...tooltipStyle} formatter={(value) => [`${value} detections`, 'Count']} />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={16}>
                {distribution.map((entry) => (
                  <Cell key={entry.type} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* ── Filter bar ────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative max-w-xs flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search threats…"
            value={filters.search}
            onChange={(e) => updateFilter('search', e.target.value)}
            className="w-full rounded-md border border-cyber-700/50 bg-cyber-800/50 py-2 pl-9 pr-3 text-sm text-gray-200 placeholder-gray-500 outline-none transition-colors focus:border-accent-cyan/50 focus:ring-1 focus:ring-accent-cyan/20"
          />
        </div>

        {/* Dropdowns */}
        <FilterSelect
          label="Organization"
          value={filters.organization}
          options={threatOrganizations}
          onChange={(v) => updateFilter('organization', v)}
        />
        <FilterSelect
          label="Threat Type"
          value={filters.threatType}
          options={threatTypes}
          onChange={(v) => updateFilter('threatType', v)}
        />
        <FilterSelect
          label="Severity"
          value={filters.severity}
          options={[...severityLevels]}
          onChange={(v) => updateFilter('severity', v)}
        />
        <FilterSelect
          label="Status"
          value={filters.status}
          options={[...statusOptions]}
          onChange={(v) => updateFilter('status', v)}
        />

        {hasActiveFilters && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 rounded-md px-3 py-2 text-xs font-medium text-gray-500 transition-colors hover:bg-cyber-800 hover:text-gray-300"
          >
            <X className="h-3 w-3" />
            Clear
          </button>
        )}

        <span className="ml-auto text-xs text-gray-500">
          {filteredThreats.length} result{filteredThreats.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* ── Detections table ──────────────────────────── */}
      <div className="overflow-hidden rounded-lg border border-cyber-700/50 bg-cyber-900">
        {filteredThreats.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12">
            <ShieldAlert className="h-8 w-8 text-cyber-600" />
            <p className="mt-3 text-sm text-gray-500">
              No detections match the current filters.
            </p>
          </div>
        ) : (
          <DataTable
            columns={columns}
            data={filteredThreats}
            rowKey={(r) => r.id}
            compact
          />
        )}
      </div>

      {/* ── Detail slide-over panel ───────────────────── */}
      {selectedThreat && (
        <ThreatDetailPanel
          threat={selectedThreat}
          onClose={() => setSelectedThreat(null)}
        />
      )}

      {/* ── Notice ────────────────────────────────────── */}
      <div className="rounded-lg border border-accent-cyan/20 bg-accent-cyan/5 px-4 py-3">
        <p className="text-xs text-gray-400">
          <span className="font-semibold text-accent-cyan">Architecture & Detection Note: </span>
          Threat detection predictions evaluate features using the integrated CICIDS2017 benchmark dataset and the trained ThreatNet neural network model. Supported threat classes are{' '}
          <span className="font-medium text-gray-200">Normal</span>,{' '}
          <span className="font-medium text-gray-200">DoS</span>,{' '}
          <span className="font-medium text-gray-200">Brute Force</span>,{' '}
          <span className="font-medium text-gray-200">Port Scan</span>, and{' '}
          <span className="font-medium text-gray-200">Malware</span>.
          Live network packet capture (e.g., PCAP/promiscuous tap) is not implemented; recorded threat events reflect benchmark evaluation vectors and database security logs rather than raw live network traffic.
        </p>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Filter dropdown
   ═══════════════════════════════════════════════════════════ */

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (v: string) => void
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border border-cyber-700/50 bg-cyber-800/50 px-3 py-2 text-xs text-gray-300 outline-none transition-colors focus:border-accent-cyan/50 capitalize"
    >
      <option value="">All {label}s</option>
      {options.map((opt) => (
        <option key={opt} value={opt} className="capitalize">
          {opt}
        </option>
      ))}
    </select>
  )
}

/* ═══════════════════════════════════════════════════════════
   Threat Detail Panel (slide-over)
   ═══════════════════════════════════════════════════════════ */

function ThreatDetailPanel({
  threat,
  onClose,
}: {
  threat: ThreatDetectionDetail
  onClose: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 flex h-full w-full max-w-lg flex-col border-l border-cyber-700/50 bg-cyber-900 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-cyber-700/50 px-6 py-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-100">
              Threat Detail
            </h3>
            <span className="font-mono text-xs text-gray-500">{threat.id}</span>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-gray-500 transition-colors hover:bg-cyber-800 hover:text-gray-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 space-y-5 overflow-y-auto p-6">
          {/* Severity + status row */}
          <div className="flex items-center gap-3">
            <StatusBadge variant={threat.severity} />
            <StatusBadge variant={threat.status} />
            <span className="ml-auto rounded-md bg-cyber-800 px-2 py-0.5 text-xs font-medium text-accent-cyan">
              {threat.detectionMethod === 'federated' ? 'Federated Model' : 'Local Model'}
            </span>
          </div>

          {/* Description */}
          <div>
            <p className="text-sm leading-relaxed text-gray-300">
              {threat.description}
            </p>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3">
            <DetailField icon={Clock} label="Timestamp" value={formatDate(threat.timestamp)} />
            <DetailField icon={ShieldAlert} label="Threat Type" value={threat.threatType} />
            <DetailField icon={Server} label="Organization" value={threat.organization} />
            <DetailField icon={Fingerprint} label="Confidence" value={`${threat.confidence.toFixed(1)}%`} />
            <DetailField icon={Network} label="Source IP" value={threat.sourceIP} mono />
            <DetailField icon={Network} label="Dest IP" value={threat.destinationIP} mono />
            <DetailField icon={Info} label="Protocol" value={`${threat.protocol}:${threat.port}`} />
            <DetailField icon={Info} label="Model" value={threat.modelVersion} />
          </div>

          {/* Raw features */}
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Raw Features
            </p>
            <div className="rounded-md border border-cyber-700/50 bg-cyber-800/30 p-3">
              <div className="space-y-1.5">
                {Object.entries(threat.rawFeatures).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between">
                    <span className="font-mono text-xs text-gray-500">
                      {key}
                    </span>
                    <span className="font-mono text-xs text-gray-300">
                      {typeof val === 'number' ? val.toLocaleString() : val}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Detail field ─────────────────────────────────────────── */

function DetailField({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="rounded-md border border-cyber-700/50 bg-cyber-800/30 p-3">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3 w-3 text-gray-600" />
        <span className="text-[10px] uppercase tracking-wider text-gray-600">{label}</span>
      </div>
      <p className={`mt-1 text-sm text-gray-200 ${mono ? 'font-mono' : ''}`}>
        {value}
      </p>
    </div>
  )
}
