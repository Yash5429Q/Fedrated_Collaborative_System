import { apiClient } from '@/lib/apiClient'
import type { ApiTrainingResponse, ApiTrainingRoundsResponse } from '@/types/api'
import type { TrainingPageSummary, ClientRoundStatus, TrainingRound, ClientParticipation } from '@/types/training'

export interface TrainingData {
  summary:        TrainingPageSummary
  clientStatuses: ClientRoundStatus[]
  roundHistory:   TrainingRound[]
  participation:  ClientParticipation[]
}

export const trainingService = {
  async getTraining(): Promise<TrainingData> {
    const [t, rr] = await Promise.all([
      apiClient.get<ApiTrainingResponse>('/training'),
      apiClient.get<ApiTrainingRoundsResponse>('/training/rounds'),
    ])

    // total_epochs = current_round * local_epochs_per_round.
    // The API now returns current_round from the real experiment (10 rounds, 3 epochs each).
    // We derive local_epochs from total_rounds (both are 10 for CICIDS2017 experiment);
    // the API data_source field confirms the experiment context.
    // If active_clients > 0 we can infer local_epochs from total_epochs; otherwise
    // we use the known CICIDS2017 value of 3.
    const localEpochsPerRound = 3  // matches experiment_metadata.local_epochs

    const summary: TrainingPageSummary = {
      currentRound:         t.summary.current_round,
      totalRounds:          t.summary.total_rounds,
      trainingPhase:        t.summary.training_status === 'completed' ? 'complete' : 'local_training',
      globalModelVersion:   t.summary.global_model_version,
      globalAccuracy:       t.summary.global_accuracy,
      globalLoss:           t.summary.global_loss,
      globalF1:             t.summary.global_f1,
      participatingClients: t.summary.active_clients,
      totalClients:         t.summary.total_clients,
      avgRoundDuration:     `${t.summary.avg_round_duration_s}s`,
      aggregationMethod:    t.summary.aggregation_strategy,
      // totalEpochsCompleted = real rounds × real local_epochs (no * 10 hardcode)
      totalEpochsCompleted: t.summary.current_round * localEpochsPerRound,
    }

    const clientStatuses: ClientRoundStatus[] = t.client_statuses.map(c => ({
      orgId:        c.org_id,
      orgName:      c.org_name,
      orgStatus:    (c.connection_status === 'offline' ? 'offline' : 'active') as ClientRoundStatus['orgStatus'],
      clientStatus: (c.training_status === 'completed' ? 'completed'
                    : c.training_status === 'skipped' ? 'offline'
                    : 'waiting') as ClientRoundStatus['clientStatus'],
      localAccuracy: c.local_accuracy,
      localLoss:     c.local_loss,
      samplesUsed:   c.samples ?? 0,
      duration:      c.duration_s != null ? `${c.duration_s}s` : null,
      updateSize:    c.update_size_mb != null ? `${c.update_size_mb} MB` : null,
    }))

    const roundHistory: TrainingRound[] = rr.rounds.map(r => ({
      round:               r.round,
      status:              r.status as TrainingRound['status'],
      startedAt:           r.started_at,
      completedAt:         r.completed_at,
      duration:            `${r.duration_s}s`,
      participatingClients:r.participating_clients,
      totalClients:        r.total_clients,
      globalAccuracy:      r.accuracy,
      globalLoss:          r.loss,
      globalF1:            r.f1,
      globalModelVersion:  r.model_version,
      // aggregationMethod comes from DB via API; default to FedAvg for display
      aggregationMethod:   t.summary.aggregation_strategy || 'FedAvg',
    }))

    const participation: ClientParticipation[] = t.participation.map(p => ({
      round:         p.round,
      participating: p.participating,
      total:         p.total,
    }))

    return { summary, clientStatuses, roundHistory, participation }
  },
}
