/**
 * Raw API response types — snake_case, matching FastAPI backend schemas.
 * These are internal to the service layer.
 * Components always receive the mapped frontend types, never these raw types.
 */

/* ── Common ───────────────────────────────────────────────── */
export interface ApiBase { data_source: string }

/* ── Dashboard ────────────────────────────────────────────── */
export interface ApiTrainingRound { round: number; accuracy: number; fpr: number; f1: number }
export interface ApiModelComparison { metric: string; local: number; federated: number }
export interface ApiThreatCategory  { name: string; count: number; color: string }
export interface ApiOrgActivity     { org_id: string; name: string; status: string; current_round: number | null; last_update: string; is_experiment_participant: boolean }
export interface ApiRecentThreat    { id: string; timestamp: string; organization: string; threat_type: string; severity: string; confidence: number; status: string; model_version: string }
export interface ApiSystemComponent { name: string; status: string; detail: string }

export interface ApiDashboardResponse extends ApiBase {
  total_organizations:  number
  active_organizations: number
  experiment_clients:   number
  current_round:        number
  total_rounds:         number
  threats_detected:     number
  global_model_accuracy:number
  f1_score:             number
  false_positive_rate:  number
  privacy_status:       string
  privacy_detail:       string | null
  training_rounds:      ApiTrainingRound[]
  model_comparison:     ApiModelComparison[]
  threat_categories:    ApiThreatCategory[]
  org_activity:         ApiOrgActivity[]
  recent_threats:       ApiRecentThreat[]
  system_components:    ApiSystemComponent[]
  experiment_id:        string | null
}

/* ── Organizations ────────────────────────────────────────── */
export interface ApiDataSlice       { label: string; value: number; color: string }
export interface ApiOrgRound        { round: number; status: string; accuracy: number | null; duration_s: number | null }
export interface ApiOrganization {
  org_id:               string
  name:                 string
  status:               string
  dataset_size:         number
  local_model_status:   string
  local_model_accuracy: number | null
  current_round:        number | null
  last_update:          string
  data_distribution:    ApiDataSlice[]
  participation_rate:   number
  recent_rounds:        ApiOrgRound[]
}
export interface ApiOrgSummary { total: number; active: number; training: number; idle: number; offline: number }
export interface ApiOrganizationsResponse extends ApiBase {
  summary:       ApiOrgSummary
  organizations: ApiOrganization[]
}

/* ── Training ─────────────────────────────────────────────── */
export interface ApiClientStatus {
  org_id:             string
  org_name:           string
  connection_status:  string
  training_status:    string
  local_accuracy:     number | null
  local_loss:         number | null
  samples:            number | null
  update_size_mb:     number | null
  duration_s:         number | null
}
export interface ApiTrainingRoundHistory {
  round:                number
  status:               string
  participating_clients:number
  total_clients:        number
  accuracy:             number
  loss:                 number
  f1:                   number
  duration_s:           number
  model_version:        string
  started_at:           string
  completed_at:         string | null
}
export interface ApiParticipation { round: number; participating: number; total: number }
export interface ApiTrainingSummary {
  current_round:          number
  total_rounds:           number
  global_model_version:   string
  training_status:        string
  global_accuracy:        number
  global_f1:              number
  global_loss:            number
  avg_round_duration_s:   number
  aggregation_strategy:   string
  active_clients:         number
  total_clients:          number
}
export interface ApiTrainingResponse extends ApiBase {
  summary:         ApiTrainingSummary
  client_statuses: ApiClientStatus[]
  participation:   ApiParticipation[]
}
export interface ApiTrainingRoundsResponse extends ApiBase {
  rounds: ApiTrainingRoundHistory[]
  total:  number
}

/* ── Threats ──────────────────────────────────────────────── */
export interface ApiThreatDetection {
  id:               string
  timestamp:        string
  organization:     string
  organization_id:  string
  threat_type:      string
  severity:         string
  confidence:       number
  status:           string
  model_version:    string
  source_ip:        string
  destination_ip:   string
  protocol:         string
  port:             number
  description:      string
  raw_features:     Record<string, number>
  detection_method: string
}
export interface ApiThreatSummary { total: number; critical: number; high: number; medium: number; low: number; blocked: number; investigating: number; avg_confidence: number }
export interface ApiThreatTimeline { hour: string; critical: number; high: number; medium: number; low: number }
export interface ApiThreatTypeCount { type: string; count: number; color: string }
export interface ApiThreatsResponse extends ApiBase {
  summary:      ApiThreatSummary
  detections:   ApiThreatDetection[]
  distribution: ApiThreatTypeCount[]
  timeline:     ApiThreatTimeline[]
  total:        number
  page:         number
  page_size:    number
}

/* ── Performance ──────────────────────────────────────────── */
export interface ApiMetricComparison  { label: string; local: number; federated: number; unit: string; higher_is_better: boolean }
export interface ApiOrgPerformance    { org_id: string; org_name: string; local_accuracy: number; local_f1: number; local_precision: number; local_recall: number; federated_accuracy: number; federated_f1: number; gain: number }
export interface ApiNonIIDResult      { scenario: string; alpha: number; local_avg_accuracy: number; federated_accuracy: number; robustness_score: number }
export interface ApiPerfRound         { round: number; local_avg_accuracy: number; federated_accuracy: number; local_avg_f1: number; federated_f1: number }
export interface ApiCollabBenefit     { metric: string; local_avg: number; federated: number; improvement: number; improvement_pct: number }
export interface ApiConfusionCell     { actual: string; predicted: string; value: number }
export interface ApiConfusionMatrix   { labels: string[]; cells: ApiConfusionCell[]; model_type: string }
export interface ApiPerfSummary       { federated_accuracy: number; local_avg_accuracy: number; accuracy_gain: number; federated_f1: number; local_avg_f1: number; f1_gain: number; federated_fpr: number; local_avg_fpr: number; fpr_reduction: number }
export interface ApiPerformanceResponse extends ApiBase {
  summary:                    ApiPerfSummary
  metric_comparisons:         ApiMetricComparison[]
  org_performance:            ApiOrgPerformance[]
  non_iid_results:            ApiNonIIDResult[]
  round_metrics:              ApiPerfRound[]
  collaboration_benefit:      ApiCollabBenefit[]
  local_confusion_matrix:     ApiConfusionMatrix
  federated_confusion_matrix: ApiConfusionMatrix
  experiment_id?:             string | null
}

/* ── Experiments ──────────────────────────────────────────── */
export interface ApiExperimentSummary {
  experiment_id:      string
  dataset?:           string | null
  total_samples?:     number | null
  number_of_rounds?:  number | null
  number_of_clients?: number | null
  local_epochs?:      number | null
  dirichlet_alpha?:   number | null
  random_seed?:       number | null
  is_latest?:         boolean
}

/* ── Privacy ──────────────────────────────────────────────── */
export interface ApiPrivacyProperty   { id: string; label: string; category: string; description: string; status: string; detail: string; planned: boolean }
export interface ApiOrgUpdateStatus   { org_id: string; org_name: string; round: number; update_status: string; update_size: string | null; submitted_at: string | null; validation_passed: boolean | null; notes: string }
export interface ApiSecurityEvent     { id: string; timestamp: string; organization: string | null; event: string; category: string; severity: string; status: string; detail: string }
export interface ApiPrivacySummary    { raw_data_shared: boolean; model_updates_only: boolean; privacy_mechanisms_implemented: number; privacy_mechanisms_planned: number; security_events_last_24h: number; unauthorized_attempts_blocked: number }
export interface ApiPrivacyResponse extends ApiBase {
  summary:             ApiPrivacySummary
  properties:          ApiPrivacyProperty[]
  org_update_statuses: ApiOrgUpdateStatus[]
  security_events:     ApiSecurityEvent[]
}

/* ── Testing ──────────────────────────────────────────────── */
export interface ApiTestCase {
  id:               string
  name:             string
  category:         string
  description:      string
  expected_result:  string
  actual_result:    string | null
  status:           string
  execution_state:  string
  timestamp:        string | null
  notes:            string
}
export interface ApiAcceptanceCriterion { code: string; title: string; description: string; tests: string[]; passing_threshold: number }
export interface ApiTestSuiteSummary    { total: number; executed: number; mock_run: number; not_run: number; passed: number; failed: number; warnings: number; pending: number; pass_rate: number }
export interface ApiTestingResponse extends ApiBase {
  summary:             ApiTestSuiteSummary
  test_cases:          ApiTestCase[]
  acceptance_criteria: ApiAcceptanceCriterion[]
}

/* ── System ───────────────────────────────────────────────── */
export interface ApiSystemResponse extends ApiBase {
  status:        string
  version:       string
  environment:   string
  uptime_s:      number
  fl_connected:  boolean
  ml_connected:  boolean
  db_connected:  boolean
  components:    Array<{ name: string; status: string; detail: string; last_checked: string }>
}
