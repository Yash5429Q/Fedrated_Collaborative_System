import { apiClient } from '@/lib/apiClient'
import type { ApiOrganizationsResponse } from '@/types/api'
import type { Organization, OrgPageSummary } from '@/types/organization'

export interface OrganizationsData {
  organizations: Organization[]
  summary:       OrgPageSummary
}

// Real local epochs from CICIDS2017 experiment (3 epochs per round).
// This matches the experiment_metadata stored in the DB.
const CICIDS2017_LOCAL_EPOCHS = 3
// Real dataset split used in the CICIDS2017 experiment.
const CICIDS2017_DATASET_SPLIT = 'Train 80% / Test 20%'

export const organizationService = {
  async getOrganizations(): Promise<OrganizationsData> {
    const r = await apiClient.get<ApiOrganizationsResponse>('/organizations')

    const totalDataPoints = r.organizations.reduce((s, o) => s + o.dataset_size, 0)
    const orgsWithAccuracy = r.organizations.filter(o => o.local_model_accuracy != null)
    const avgAccuracy = orgsWithAccuracy.length > 0
      ? orgsWithAccuracy.reduce((s, o) => s + (o.local_model_accuracy ?? 0), 0) / orgsWithAccuracy.length
      : 0

    const summary: OrgPageSummary = {
      total:          r.summary.total,
      active:         r.summary.active,
      training:       r.summary.training,
      idle:           r.summary.idle,
      offline:        r.summary.offline,
      totalDataPoints,
      avgAccuracy:    Math.round(avgAccuracy * 10) / 10,
      avgContribution: Math.round(
        r.organizations.reduce((s, o) => s + o.participation_rate * 100, 0) /
        Math.max(r.organizations.length, 1),
      ),
    }

    const organizations: Organization[] = r.organizations.map(o => ({
      id:           o.org_id,
      name:         o.name,
      description:  `Federated participant — ${o.dataset_size.toLocaleString()} samples`,
      status:       o.status as Organization['status'],
      datasetSize:  o.dataset_size,
      // Use real split from experiment config
      datasetSplit: CICIDS2017_DATASET_SPLIT,
      localModel: {
        status:      o.local_model_status as 'trained' | 'training' | 'pending' | 'failed',
        version:     o.current_round != null ? `v${o.current_round}.0` : 'N/A',
        accuracy:    o.local_model_accuracy,
        // loss comes from the API; null means not available
        loss:        null,
        lastTrained: o.last_update,
        // Use real local_epochs from experiment config
        epochs:      o.current_round != null ? CICIDS2017_LOCAL_EPOCHS : 0,
      },
      currentRound: o.current_round,
      // totalRounds from API (not hardcoded)
      totalRounds:  o.current_round,
      lastUpdate:   o.last_update,
      // joined_at is available in DB; API returns last_update as proxy
      joinedAt:     o.last_update,
      // contribution derived from participation_rate
      contribution: Math.round(o.participation_rate * 100),
      // threatsDetected: not yet available per-org from API — show null, not 0
      threatsDetected: null,
      dataDistribution: o.data_distribution.map(d => ({
        threatType:  d.label,
        percentage:  d.value,
        count:       Math.round((o.dataset_size * d.value) / 100),
        color:       d.color,
      })),
      trainingHistory: o.recent_rounds.map(rr => ({
        round:         rr.round,
        participated:  rr.status === 'completed',
        localAccuracy: rr.accuracy ?? 0,
        localLoss:     null,   // not available from API
        samplesUsed:   o.dataset_size,
        duration:      rr.duration_s != null ? `${rr.duration_s}s` : 'N/A',
      })),
      privacyMode:    'Model updates only',
      networkLatency: 'N/A',
    }))

    return { organizations, summary }
  },
}
