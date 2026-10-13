import { apiClient } from '@/lib/apiClient'

export interface PredictRequest {
  features: number[]
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
}

export interface PredictHealthResponse {
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
  async predict(features: number[]): Promise<PredictResponse> {
    return apiClient.post<PredictResponse>('/predict', { features })
  },

  async health(): Promise<PredictHealthResponse> {
    return apiClient.get<PredictHealthResponse>('/predict/health')
  },
}
