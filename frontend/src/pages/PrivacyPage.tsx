import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Database,
  Lock,
  Server,
  Cpu,
  ArrowDown,
  CheckCircle2,
  Clock,
  Building2,
  AlertTriangle,
  Info,
  XCircle,
  FlaskConical,
} from 'lucide-react'

import { StatCard, ChartCard, DataTable, LoadingSpinner, ErrorState } from '@/components/common'
import type { Column } from '@/components/common'
import type {
  PrivacyProperty,
  PrivacyPropertyStatus,
  OrgUpdateStatus,
  UpdateStatus,
  SecurityEvent,
  SecurityEventSeverity,
  SecurityEventStatus,
} from '@/types/privacy'
import { usePrivacy } from '@/hooks/usePrivacy'


/* ── Helpers ──────────────────────────────────────────────── */

function formatTs(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  })
}

/* ── Update status styling ────────────────────────────────── */

const updateStatusStyle: Record<UpdateStatus, { label: string; cls: string }> = {
  submitted:  { label: 'Submitted',  cls: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20' },
  pending:    { label: 'Pending',    cls: 'bg-amber-500/15   text-amber-400   border-amber-500/20'   },
  rejected:   { label: 'Rejected',   cls: 'bg-red-500/15     text-red-400     border-red-500/20'     },
  not_sent:   { label: 'Not Sent',   cls: 'bg-slate-500/15   text-slate-400   border-slate-500/20'   },
}

/* ── Security severity styling ────────────────────────────── */

const secSeverityStyle: Record<SecurityEventSeverity, { icon: React.ComponentType<{className?: string}>; cls: string }> = {
  info:     { icon: Info,          cls: 'text-blue-400'   },
  warning:  { icon: AlertTriangle, cls: 'text-amber-400'  },
  critical: { icon: ShieldAlert,   cls: 'text-red-400'    },
}

const secStatusStyle: Record<SecurityEventStatus, string> = {
  resolved:   'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  monitoring: 'bg-amber-500/15   text-amber-400   border-amber-500/20',
  open:       'bg-red-500/15     text-red-400     border-red-500/20',
}

/* ── Privacy property status chip ────────────────────────── */

const propStatusConfig: Record<PrivacyPropertyStatus, { label: string; cls: string; dot: string }> = {
  enforced:        { label: 'Enforced',        cls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', dot: 'bg-emerald-400' },
  planned:         { label: 'Planned',         cls: 'text-amber-400   bg-amber-500/10   border-amber-500/20',   dot: 'bg-amber-400'   },
  not_implemented: { label: 'Not Implemented', cls: 'text-slate-400   bg-slate-500/10   border-slate-500/20',   dot: 'bg-slate-500'   },
  'n/a':           { label: 'N/A',             cls: 'text-gray-500    bg-cyber-800      border-cyber-700/50',   dot: 'bg-gray-600'    },
}

/* ── Security event table columns ────────────────────────── */

const eventColumns: Column<SecurityEvent>[] = [
  {
    key: 'time',
    header: 'Time',
    render: (r) => (
      <span className="whitespace-nowrap font-mono text-xs text-gray-400">
        {formatTs(r.timestamp)}
      </span>
    ),
  },
  {
    key: 'org',
    header: 'Source',
    render: (r) => (
      <span className="text-sm text-gray-300">
        {r.organization ?? <span className="text-gray-500 italic">System</span>}
      </span>
    ),
  },
  {
    key: 'event',
    header: 'Event',
    render: (r) => <span className="text-sm font-medium text-gray-200">{r.event}</span>,
  },
  {
    key: 'category',
    header: 'Category',
    render: (r) => (
      <span className="rounded bg-cyber-800 px-2 py-0.5 text-xs text-gray-400">{r.category}</span>
    ),
  },
  {
    key: 'severity',
    header: 'Severity',
    render: (r) => {
      const cfg = secSeverityStyle[r.severity]
      const Icon = cfg.icon
      return (
        <span className={`inline-flex items-center gap-1 text-xs font-medium capitalize ${cfg.cls}`}>
          <Icon className="h-3.5 w-3.5" />{r.severity}
        </span>
      )
    },
  },
  {
    key: 'status',
    header: 'Status',
    render: (r) => (
      <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${secStatusStyle[r.status]}`}>
        {r.status}
      </span>
    ),
  },
]

/* ═══════════════════════════════════════════════════════════
   Page
   ═══════════════════════════════════════════════════════════ */

export default function PrivacyPage() {
  const { data, loading, error, refetch } = usePrivacy()

  if (loading) return <LoadingSpinner label="Loading privacy data…" />
  if (error || !data)
    return <ErrorState message={error ?? 'No data returned'} onRetry={refetch} detail="Ensure the backend is running on port 8000." />

  const { summary: S, properties: mockPrivacyProperties, orgUpdateStatuses: mockOrgUpdateStatuses, securityEvents: mockSecurityEvents } = data

  return (
    <div className="space-y-8">


      {/* ── Honest disclaimer banner ───────────────────── */}
      <div className="flex items-start gap-3 rounded-lg border border-accent-amber/30 bg-accent-amber/8 px-4 py-3">
        <Lock className="mt-0.5 h-4 w-4 shrink-0 text-accent-amber" />
        <div>
          <p className="text-xs font-semibold text-accent-amber">
            Privacy & Security Architecture
          </p>
          <p className="mt-0.5 text-xs text-gray-300">
            Raw training data remains strictly local on client organization devices during federated training; only parameter updates are transmitted. Implemented update-level defenses include <span className="text-gray-100 font-medium">L2 update clipping (clip_norm=1.0)</span>, <span className="text-gray-100 font-medium">Gaussian noise injection (noise_std=0.1)</span>, and <span className="text-gray-100 font-medium">server-side validation (NaN/Inf & structural integrity checks)</span>.
          </p>
          <p className="mt-1 text-xs text-gray-400">
            <span className="font-medium text-accent-amber">Limitations: </span>
            <span className="font-medium text-gray-300">Secure Aggregation is not implemented</span> (the central server processes individual updates directly). Client authentication (such as mTLS) is not implemented. Although Gaussian noise is injected, formal end-to-end (ε,δ)-differential privacy guarantees cannot be guaranteed without full composition accounting (per-round ε≈48.45 from experiment metadata).
          </p>
        </div>
      </div>

      {/* ── Summary cards ─────────────────────────────── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Raw Data Shared"
          value={S.rawDataShared ? 'Yes — Risk' : 'No — Local Only'}
          icon={Database}
          accent={S.rawDataShared ? 'text-red-400' : 'text-accent-green'}
          bgAccent={S.rawDataShared ? 'bg-red-400/10' : 'bg-accent-green/10'}
        />
        <StatCard
          label="Transmission Type"
          value="Model Updates Only"
          icon={Shield}
          accent="text-accent-cyan"
          bgAccent="bg-accent-cyan/10"
        />
        <StatCard
          label="Mechanisms Active"
          value={`${S.privacyMechanismsImplemented} / ${S.privacyMechanismsImplemented + S.privacyMechanismsPlanned}`}
          icon={ShieldCheck}
          accent="text-accent-amber"
          bgAccent="bg-accent-amber/10"
          trend={{ value: `${S.privacyMechanismsPlanned} planned`, direction: 'flat' }}
        />
        <StatCard
          label="Security Events (24h)"
          value={S.securityEventsLast24h}
          icon={ShieldAlert}
          accent="text-orange-400"
          bgAccent="bg-orange-400/10"
          trend={{ value: `${S.unauthorizedAttemptsBlocked} blocked`, direction: 'up' }}
        />
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 1 — Privacy flow diagram
          ═══════════════════════════════════════════════ */}
      <PrivacyFlow />

      {/* ═══════════════════════════════════════════════
          SECTION 2 — Privacy properties
          ═══════════════════════════════════════════════ */}
      <div>
        <SectionTitle icon={ShieldCheck} title="Privacy Architecture" />
        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-2">
          {mockPrivacyProperties.map((prop) => (
            <PrivacyPropertyCard key={prop.id} prop={prop} />
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 3 — Model update status per org
          ═══════════════════════════════════════════════ */}
      <div>
        <SectionTitle icon={Server} title={`Model Update Status — Round ${mockOrgUpdateStatuses[0]?.round ?? 10}`} />
        <div className="mt-4 space-y-2">
          {mockOrgUpdateStatuses.map((row) => (
            <OrgUpdateRow key={row.orgId} row={row} />
          ))}
        </div>
        <p className="mt-2 text-xs text-gray-500">
          Only model parameter updates are transmitted; raw training samples remain on client devices.
          Server-side update validation enforces structural schema integrity, NaN/Inf rejection, and L2 clipping bounds.
        </p>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 4 — Privacy validation checklist
          ═══════════════════════════════════════════════ */}
      <div>
        <SectionTitle icon={FlaskConical} title="Privacy Validation" />
        <div className="mt-4 rounded-lg border border-cyber-700/50 bg-cyber-900">
          <div className="divide-y divide-cyber-700/30">
            {validationChecks.map((check) => (
              <ValidationRow key={check.label} check={check} />
            ))}
          </div>
          <div className="border-t border-cyber-700/30 px-5 py-2 text-xs text-gray-600">
            Validation items marked "Planned" will be verified when the corresponding
            privacy mechanism is implemented and integrated.
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════
          SECTION 5 — Security events table
          ═══════════════════════════════════════════════ */}
      <div>
        <SectionTitle icon={ShieldAlert} title="Security Events" />
        <ChartCard
          title="Recent Security Events"
          subtitle="System-level and organization-level security notifications from active security logs"
          className="mt-4"
        >
          <DataTable
            columns={eventColumns}
            data={mockSecurityEvents}
            rowKey={(r) => r.id}
            compact
          />
        </ChartCard>
      </div>

      {/* ── Bottom notice ─────────────────────────────── */}
      <p className="pb-2 text-center text-xs text-gray-500">
        Differential privacy parameters and model update statuses are sourced from the backend experiment database and security repositories.
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Privacy flow diagram
   ═══════════════════════════════════════════════════════════ */

function PrivacyFlow() {
  return (
    <div className="rounded-lg border border-cyber-700/50 bg-cyber-900 p-6">
      <h3 className="mb-1 text-sm font-semibold text-gray-200">
        Data Privacy Flow
      </h3>
      <p className="mb-5 text-xs text-gray-500">
        Illustrates what is shared and what stays local in the federated system
      </p>

      <div className="flex flex-col items-center gap-2">
        {/* Step 1: Org Data */}
        <FlowNode
          icon={Database}
          label="Organization Data"
          sublabel="Raw traffic logs, network flows — stays local"
          tag="LOCAL ONLY"
          tagColor="text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
          iconColor="text-accent-green"
          iconBg="bg-accent-green/10"
        />
        <FlowArrow label="Fed into local model only — never transmitted" safe />

        {/* Step 2: Local Training */}
        <FlowNode
          icon={Cpu}
          label="Local Training"
          sublabel="Model trained entirely on local data within organization boundary"
          tag="LOCAL ONLY"
          tagColor="text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
          iconColor="text-accent-blue"
          iconBg="bg-accent-blue/10"
        />
        <FlowArrow label="Extract model weight updates only" safe />

        {/* Step 3: Model update */}
        <FlowNode
          icon={Shield}
          label="Model Update"
          sublabel="Gradient/weight delta — no raw data included"
          tag="TRANSMITTED"
          tagColor="text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20"
          iconColor="text-accent-cyan"
          iconBg="bg-accent-cyan/10"
        />
        <FlowArrow label="Privacy protection applied before sending (planned)" warn />

        {/* Step 4: Privacy protection */}
        <FlowNode
          icon={Lock}
          label="Privacy Protection Layer"
          sublabel="Differential privacy + secure aggregation — PLANNED, not yet active"
          tag="PLANNED"
          tagColor="text-accent-amber bg-accent-amber/10 border-accent-amber/20"
          iconColor="text-accent-amber"
          iconBg="bg-accent-amber/10"
          dimmed
        />
        <FlowArrow label="Protected update sent to server" warn />

        {/* Step 5: Federated server */}
        <FlowNode
          icon={Server}
          label="Federated Aggregation Server"
          sublabel="Combines updates from all clients — sees updates, not raw data"
          tag="SERVER"
          tagColor="text-accent-purple bg-accent-purple/10 border-accent-purple/20"
          iconColor="text-accent-purple"
          iconBg="bg-accent-purple/10"
        />
        <FlowArrow label="Publish new global model" safe />

        {/* Step 6: Global model */}
        <FlowNode
          icon={CheckCircle2}
          label="Updated Global Model"
          sublabel="Distributed back to all clients for next round"
          tag="GLOBAL"
          tagColor="text-accent-cyan bg-accent-cyan/10 border-accent-cyan/20"
          iconColor="text-accent-cyan"
          iconBg="bg-accent-cyan/10"
        />
      </div>

      {/* Legend */}
      <div className="mt-5 flex flex-wrap gap-4 border-t border-cyber-700/40 pt-4">
        <LegendItem color="bg-emerald-400" label="Enforced by FL design (data never leaves org)" />
        <LegendItem color="bg-accent-amber" label="Planned privacy mechanism (not yet implemented)" />
        <LegendItem color="bg-accent-cyan"  label="Model updates only — transmitted to server" />
      </div>
    </div>
  )
}

function FlowNode({
  icon: Icon, label, sublabel, tag, tagColor, iconColor, iconBg, dimmed,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  sublabel: string
  tag: string
  tagColor: string
  iconColor: string
  iconBg: string
  dimmed?: boolean
}) {
  return (
    <div className={`flex w-full max-w-lg items-center gap-3 rounded-lg border border-cyber-700/50 bg-cyber-800/40 px-4 py-3 ${dimmed ? 'opacity-70' : ''}`}>
      <div className={`shrink-0 rounded-md p-2 ${iconBg}`}>
        <Icon className={`h-5 w-5 ${iconColor}`} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-200">{label}</span>
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${tagColor}`}>
            {tag}
          </span>
        </div>
        <p className="truncate text-xs text-gray-500">{sublabel}</p>
      </div>
    </div>
  )
}

function FlowArrow({ label, safe, warn }: { label: string; safe?: boolean; warn?: boolean }) {
  return (
    <div className="flex flex-col items-center gap-0.5 py-1">
      <ArrowDown className={`h-4 w-4 ${safe ? 'text-emerald-500' : warn ? 'text-amber-500' : 'text-cyber-500'}`} />
      <span className="text-[10px] tracking-wide text-gray-600">{label}</span>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`h-2 w-2 rounded-full ${color}`} />
      <span className="text-xs text-gray-500">{label}</span>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Privacy property card
   ═══════════════════════════════════════════════════════════ */

function PrivacyPropertyCard({ prop }: { prop: PrivacyProperty }) {
  const cfg = propStatusConfig[prop.status]
  return (
    <div className={`rounded-lg border bg-cyber-900 p-4 ${prop.status === 'enforced' ? 'border-emerald-500/20' : 'border-cyber-700/50'}`}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-gray-200">{prop.label}</span>
        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.cls}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
          {cfg.label}
        </span>
      </div>
      <p className="mt-1.5 text-xs text-gray-400">{prop.description}</p>
      <p className={`mt-2 text-xs ${prop.status === 'enforced' ? 'text-emerald-400/80' : 'text-amber-400/80'}`}>
        {prop.detail}
      </p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Org update row
   ═══════════════════════════════════════════════════════════ */

function OrgUpdateRow({ row }: { row: OrgUpdateStatus }) {
  const cfg = updateStatusStyle[row.updateStatus]
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-cyber-700/50 bg-cyber-900 px-4 py-3">
      {/* Org name */}
      <div className="flex items-center gap-2 min-w-[180px]">
        <Building2 className="h-4 w-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-200">{row.orgName}</span>
      </div>

      {/* Status badge */}
      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.cls}`}>
        {cfg.label}
      </span>

      {/* Validation */}
      {row.validationPassed !== null && (
        row.validationPassed
          ? <span className="flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 className="h-3.5 w-3.5" />Validation passed</span>
          : <span className="flex items-center gap-1 text-xs text-red-400"><XCircle className="h-3.5 w-3.5" />Validation failed</span>
      )}

      {/* Size + time */}
      {row.updateSize && (
        <span className="ml-auto font-mono text-xs text-gray-500">{row.updateSize}</span>
      )}
      {row.submittedAt && (
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="h-3 w-3" />{formatTs(row.submittedAt)}
        </span>
      )}

      {/* Notes — full width */}
      <p className="w-full text-xs text-gray-600">{row.notes}</p>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   Privacy validation checklist
   ═══════════════════════════════════════════════════════════ */

const validationChecks: { label: string; state: 'pass' | 'planned' | 'fail'; detail: string }[] = [
  {
    label:  'Raw data does not leave organization boundary',
    state:  'pass',
    detail: 'Verified by FL architecture — only model updates are sent via Flower client.',
  },
  {
    label:  'Model updates contain no raw feature vectors',
    state:  'pass',
    detail: 'Flower client transmits parameter diffs only. Confirmed by code inspection.',
  },
  {
    label:  'Model update norm validation',
    state:  'pass',
    detail: 'Update clipping (L2 norm bound ≤ 1.0) and structural validation (NaN/Inf checks) are enforced on client updates.',
  },
  {
    label:  'Differential privacy noise injection',
    state:  'pass',
    detail: 'Gaussian noise addition (noise_std=0.1) is applied to updates during training. Formal composition accounting remains limited.',
  },
  {
    label:  'Secure aggregation (server cannot see individual updates)',
    state:  'planned',
    detail: 'Not implemented. Central aggregation receives updates directly without cryptographic masking.',
  },
  {
    label:  'Unauthorized clients cannot submit updates',
    state:  'planned',
    detail: 'Not implemented. Client authentication and mTLS verification are planned for future phases.',
  },
  {
    label:  'Membership inference resistance verified',
    state:  'planned',
    detail: 'Planned: empirical privacy leakage audit (MIA attack simulations) to be conducted in future verification phase.',
  },
  {
    label:  'Model inversion attack resistance verified',
    state:  'planned',
    detail: 'Planned: reconstruction and inversion attack resilience testing scheduled for future phase.',
  },
]

function ValidationRow({ check }: { check: (typeof validationChecks)[0] }) {
  const icon =
    check.state === 'pass'    ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> :
    check.state === 'planned' ? <Clock className="h-4 w-4 text-amber-400" /> :
                                <XCircle className="h-4 w-4 text-red-400" />

  const labelCls =
    check.state === 'pass'    ? 'text-gray-200' :
    check.state === 'planned' ? 'text-gray-400' :
                                'text-red-300'

  return (
    <div className="flex items-start gap-3 px-5 py-3 hover:bg-cyber-800/20">
      <div className="mt-0.5 shrink-0">{icon}</div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-medium ${labelCls}`}>{check.label}</p>
        <p className="mt-0.5 text-xs text-gray-600">{check.detail}</p>
      </div>
      <span className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-semibold uppercase ${
        check.state === 'pass' ? 'bg-emerald-500/10 text-emerald-400' :
        check.state === 'planned' ? 'bg-amber-500/10 text-amber-400' :
        'bg-red-500/10 text-red-400'
      }`}>
        {check.state === 'pass' ? 'Verified' : check.state === 'planned' ? 'Planned' : 'Failed'}
      </span>
    </div>
  )
}

/* ── Shared section title ─────────────────────────────────── */

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
    </div>
  )
}
