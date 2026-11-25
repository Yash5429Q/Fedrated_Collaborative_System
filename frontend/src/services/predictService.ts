import { apiClient } from '@/lib/apiClient'

export interface PredictRequest {
  features: number[]
  record_alert?: boolean
}

export interface PredictionResult {
  class_id: number
  label: string
  confidence: number
}

export interface ModelInfo {
  name: string
  input_features: number
  classes: number
  experiment_id: string
  checkpoint_path: string | null
}

export interface PredictResponse {
  prediction: PredictionResult
  probabilities: Record<string, number>
  model: ModelInfo
  attack_score: number | null
  attack_threshold: number | null
  decision_rule: string | null
  alert_id: string | null
  latency_ms: number | null
}

export interface PredictHealthResponse {
  normalization_loaded: boolean
  model_loaded: boolean
  model_name: string
  input_features: number
  num_classes: number
  class_names: string[]
  experiment_id: string | null
  checkpoint_path: string | null
  error: string | null
}

export const predictService = {
  async predict(features: number[], record_alert = false): Promise<PredictResponse> {
    return apiClient.post<PredictResponse>('/predict', { features, record_alert })
  },

  async samples() { return apiClient.get<{experiment_id: string; seed: number; feature_names: string[]; samples: {label: string; test_index: number; features: number[]}[]}>('/predict/samples') },
  async health(): Promise<PredictHealthResponse> {
    return apiClient.get<PredictHealthResponse>('/predict/health')
  },
}
