import type { Severity, DetectionStatus, OrgStatus, HealthStatus } from '@/types/dashboard'
import type { ModelStatus } from '@/types/organization'
import type { ClientTrainingStatus, RoundStatus, TrainingPhase } from '@/types/training'

type BadgeVariant =
  | Severity | DetectionStatus | OrgStatus | HealthStatus
  | ModelStatus | ClientTrainingStatus | RoundStatus | TrainingPhase

const variantStyles: Record<string, string> = {
  // Severity
  critical:         'bg-red-500/15 text-red-400 border-red-500/20',
  high:             'bg-orange-500/15 text-orange-400 border-orange-500/20',
  medium:           'bg-amber-500/15 text-amber-400 border-amber-500/20',
  low:              'bg-blue-500/15 text-blue-400 border-blue-500/20',

  // Detection status
  detected:         'bg-red-500/15 text-red-400 border-red-500/20',
  blocked:          'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  investigating:    'bg-amber-500/15 text-amber-400 border-amber-500/20',
  resolved:         'bg-slate-500/15 text-slate-400 border-slate-500/20',

  // Org status
  active:           'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  training:         'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
  idle:             'bg-amber-500/15 text-amber-400 border-amber-500/20',
  offline:          'bg-slate-500/15 text-slate-400 border-slate-500/20',

  // Health status
  operational:      'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  degraded:         'bg-amber-500/15 text-amber-400 border-amber-500/20',
  down:             'bg-red-500/15 text-red-400 border-red-500/20',
  unknown:          'bg-slate-500/15 text-slate-400 border-slate-500/20',

  // Model status
  trained:          'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  pending:          'bg-slate-500/15 text-slate-400 border-slate-500/20',
  failed:           'bg-red-500/15 text-red-400 border-red-500/20',

  // Client training status
  waiting:          'bg-slate-500/15 text-slate-400 border-slate-500/20',
  downloading:      'bg-blue-500/15 text-blue-400 border-blue-500/20',
  uploading:        'bg-blue-500/15 text-blue-400 border-blue-500/20',
  completed:        'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',

  // Round status
  in_progress:      'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
  skipped:          'bg-slate-500/15 text-slate-400 border-slate-500/20',

  // Training phase
  distributing:     'bg-blue-500/15 text-blue-400 border-blue-500/20',
  local_training:   'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
  collecting:       'bg-purple-500/15 text-purple-400 border-purple-500/20',
  aggregating:      'bg-purple-500/15 text-purple-400 border-purple-500/20',
  evaluating:       'bg-amber-500/15 text-amber-400 border-amber-500/20',
  complete:         'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
}

interface StatusBadgeProps {
  variant: BadgeVariant
  label?: string
  pulse?: boolean
}

export default function StatusBadge({ variant, label, pulse }: StatusBadgeProps) {
  const displayLabel = label ?? variant

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${variantStyles[variant] ?? variantStyles.unknown}`}
    >
      {pulse && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-50" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {displayLabel}
    </span>
  )
}
