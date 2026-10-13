/**
 * Dashboard service — fetches GET /api/dashboard and maps to frontend types.
 * All KPI values come from the latest CICIDS2017 experiment via the backend.
 */
import { apiClient } from '@/lib/apiClient'
import type { ApiDashboardResponse } from '@/types/api'
import type {
  DashboardSummary,
  TrainingRoundMetric,
  ModelComparisonMetric,
  ThreatCategory,
  OrganizationActivity,
  ThreatDetection,
  SystemComponent,
} from '@/types/dashboard'

export interface DashboardData {
  summary:             DashboardSummary
  trainingRounds:      TrainingRoundMetric[]
  modelComparison:     ModelComparisonMetric[]
  threatDistribution:  ThreatCategory[]
  orgActivity:         OrganizationActivity[]
  recentThreats:       ThreatDetection[]
  systemHealth:        SystemComponent[]
}

export const dashboardService = {
  async getDashboard(): Promise<DashboardData> {
    const r = await apiClient.get<ApiDashboardResponse>('/dashboard')
    return {
      summary: {
        totalOrganizations:  r.total_organizations,
        activeOrganizations: r.active_organizations,
        experimentClients:   r.experiment_clients,
        currentRound:        r.current_round,
        totalRounds:         r.total_rounds,
        threatsDetected:     r.threats_detected,
        globalAccuracy:      r.global_model_accuracy,
        f1Score:             r.f1_score,
        falsePositiveRate:   r.false_positive_rate,
        privacyStatus:       r.privacy_status,
        privacyDetail:       r.privacy_detail ?? null,
        experimentId:        r.experiment_id ?? null,
      },
      trainingRounds: r.training_rounds.map(t => ({
        round:    t.round,
        accuracy: t.accuracy,
        fpr:      t.fpr,
        f1Score:  t.f1,
      })),
      modelComparison: r.model_comparison.map(m => ({
        metric:    m.metric,
        local:     m.local,
        federated: m.federated,
      })),
      threatDistribution: r.threat_categories.map(c => ({
        category: c.name,
        count:    c.count,
        color:    c.color,
      })),
      orgActivity: r.org_activity.map(o => ({
        id:                      o.org_id,
        name:                    o.name,
        status:                  o.status as OrganizationActivity['status'],
        currentRound:            o.current_round,        // null for non-participants
        datasetSize:             null,
        lastUpdate:              o.last_update,
        contribution:            null,
        isExperimentParticipant: o.is_experiment_participant,
      })),
      recentThreats: r.recent_threats.map(t => ({
        id:           t.id,
        timestamp:    t.timestamp,
        organization: t.organization,
        threatType:   t.threat_type,
        severity:     t.severity as ThreatDetection['severity'],
        confidence:   t.confidence,
        status:       t.status as ThreatDetection['status'],
        modelVersion: t.model_version,
      })),
      systemHealth: r.system_components.map(c => ({
        name:   c.name,
        status: c.status as SystemComponent['status'],
        detail: c.detail,
      })),
    }
  },
}
