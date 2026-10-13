import { apiClient } from '@/lib/apiClient'
import type { ApiPerformanceResponse, ApiExperimentSummary } from '@/types/api'
import type {
  MetricComparison,
  OrgPerformanceRow,
  NonIIDResult,
  PerfRoundMetric,
  CollaborationBenefit,
  ConfusionMatrix,
  PerformancePageSummary,
  PerformanceExperimentInfo,
} from '@/types/performance'

export interface PerformanceData {
  summary:               PerformancePageSummary
  metricComparisons:     MetricComparison[]
  orgPerformance:        OrgPerformanceRow[]
  nonIIDResults:         NonIIDResult[]
  perfRounds:            PerfRoundMetric[]
  collaborationBenefit:  CollaborationBenefit[]
  localConfusionMatrix:  ConfusionMatrix
  federatedConfusionMatrix: ConfusionMatrix
  experimentInfo:        PerformanceExperimentInfo
}

export const performanceService = {
  async getPerformance(): Promise<PerformanceData> {
    const [r, latestExp] = await Promise.all([
      apiClient.get<ApiPerformanceResponse>('/performance'),
      apiClient.get<ApiExperimentSummary>('/experiments/latest').catch(() => null),
    ])

    let expMeta = latestExp
    if (r.experiment_id && (!latestExp || latestExp.experiment_id !== r.experiment_id)) {
      try {
        expMeta = await apiClient.get<ApiExperimentSummary>(`/experiments/${r.experiment_id}`)
      } catch {
        // Fallback to latestExp if specific experiment lookup fails
      }
    }

    const experimentInfo: PerformanceExperimentInfo = {
      experimentId: r.experiment_id ?? expMeta?.experiment_id ?? null,
      dataset: expMeta?.dataset ?? (r.data_source.includes('experiment:') ? 'CICIDS2017' : null),
      alpha: expMeta?.dirichlet_alpha ?? null,
      totalSamples: expMeta?.total_samples ?? null,
      rounds: expMeta?.number_of_rounds ?? (r.round_metrics.length > 0 ? r.round_metrics.length : null),
      epochs: expMeta?.local_epochs ?? null,
    }

    return {
      summary: {
        federatedAccuracy:  r.summary.federated_accuracy,
        localAvgAccuracy:   r.summary.local_avg_accuracy,
        accuracyGain:       r.summary.accuracy_gain,
        federatedF1:        r.summary.federated_f1,
        localAvgF1:         r.summary.local_avg_f1,
        f1Gain:             r.summary.f1_gain,
        federatedFPR:       r.summary.federated_fpr,
        localAvgFPR:        r.summary.local_avg_fpr,
        fprReduction:       r.summary.fpr_reduction,
        bestOrgName:        r.org_performance.length > 0
          ? r.org_performance.reduce((best, o) => o.gain > best.gain ? o : best, r.org_performance[0]).org_name
          : 'N/A',
        bestOrgGain:        r.org_performance.length > 0
          ? Math.max(...r.org_performance.map(o => o.gain))
          : 0,
      },
      metricComparisons: r.metric_comparisons.map(m => ({
        label:          m.label,
        local:          m.local,
        federated:      m.federated,
        unit:           m.unit,
        higherIsBetter: m.higher_is_better,
      })),
      orgPerformance: r.org_performance.map(o => ({
        orgId:              o.org_id,
        orgName:            o.org_name,
        localAccuracy:      o.local_accuracy,
        localF1:            o.local_f1,
        localPrecision:     o.local_precision,
        localRecall:        o.local_recall,
        federatedAccuracy:  o.federated_accuracy,
        federatedF1:        o.federated_f1,
        gain:               o.gain,
      })),
      nonIIDResults: r.non_iid_results.map(n => ({
        scenario:         n.scenario,
        alpha:            n.alpha,
        localAvgAccuracy: n.local_avg_accuracy,
        federatedAccuracy:n.federated_accuracy,
        robustnessScore:  n.robustness_score,
      })),
      perfRounds: r.round_metrics.map(p => ({
        round:              p.round,
        localAvgAccuracy:   p.local_avg_accuracy,
        federatedAccuracy:  p.federated_accuracy,
        localAvgF1:         p.local_avg_f1,
        federatedF1:        p.federated_f1,
      })),
      collaborationBenefit: r.collaboration_benefit.map(c => ({
        metric:          c.metric,
        localAvg:        c.local_avg,
        federated:       c.federated,
        improvement:     c.improvement,
        improvementPct:  c.improvement_pct,
      })),
      localConfusionMatrix: {
        labels:    r.local_confusion_matrix.labels,
        cells:     r.local_confusion_matrix.cells,
        modelType: r.local_confusion_matrix.model_type as 'local' | 'federated',
      },
      federatedConfusionMatrix: {
        labels:    r.federated_confusion_matrix.labels,
        cells:     r.federated_confusion_matrix.cells,
        modelType: r.federated_confusion_matrix.model_type as 'local' | 'federated',
      },
      experimentInfo,
    }
  },
}
