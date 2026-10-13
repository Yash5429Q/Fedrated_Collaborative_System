import { useState, useEffect } from 'react'
import { predictService, type PredictResponse, type PredictHealthResponse } from '@/services/predictService'

const CLASS_COLORS: Record<string, string> = {
  Normal: 'bg-green-500',
  DoS: 'bg-red-500',
  'Brute Force': 'bg-orange-500',
  'Port Scan': 'bg-yellow-500',
  Malware: 'bg-purple-500',
}

const CLASS_TEXT_COLORS: Record<string, string> = {
  Normal: 'text-green-400',
  DoS: 'text-red-400',
  'Brute Force': 'text-orange-400',
  'Port Scan': 'text-yellow-400',
  Malware: 'text-purple-400',
}

export default function PredictPage() {
  const [featuresText, setFeaturesText] = useState('')
  const [result, setResult] = useState<PredictResponse | null>(null)
  const [health, setHealth] = useState<PredictHealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    predictService.health().then(setHealth).catch(() => {})
  }, [])

  const handlePredict = async () => {
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const features = featuresText
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
        .map(Number)

      if (features.some(isNaN)) {
        throw new Error('All values must be valid numbers separated by commas')
      }
      if (features.length !== 68) {
        throw new Error(`Expected 68 features, got ${features.length}`)
      }
      const res = await predictService.predict(features)
      setResult(res)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Prediction failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleSampleData = () => {
    // Deterministic sample: 68 zeros (will predict something based on model)
    const sample = Array(68).fill(0).map((_, i) => (Math.sin(i) * 0.5).toFixed(4)).join(', ')
    setFeaturesText(sample)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Real-Time Threat Detection</h1>
        <p className="text-sm text-slate-400 mt-1">
          Classify network flows using the trained ThreatNet model (Phase 16)
        </p>
      </div>

      {/* Model Health Status */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
        <h2 className="text-sm font-semibold text-slate-300 mb-2">Model Status</h2>
        {health ? (
          <div className="flex items-center gap-3">
            <span
              className={`inline-block h-3 w-3 rounded-full ${health.model_loaded ? 'bg-green-500' : 'bg-red-500'}`}
            />
            <span className="text-sm text-slate-300">
              {health.model_loaded ? 'Model Loaded' : 'Model Not Loaded'}
            </span>
            {health.model_loaded && health.experiment_id && (
              <span className="text-xs text-slate-500 ml-2">
                Experiment: {health.experiment_id}
              </span>
            )}
            {!health.model_loaded && health.error && (
              <span className="text-xs text-red-400 ml-2">{health.error}</span>
            )}
          </div>
        ) : (
          <span className="text-sm text-slate-500">Checking...</span>
        )}
      </div>

      {/* Input */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-300">
            Network Flow Features (68 values, comma-separated)
          </h2>
          <button
            onClick={handleSampleData}
            className="text-xs px-3 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
          >
            Load Sample Data
          </button>
        </div>
        <textarea
          value={featuresText}
          onChange={(e) => setFeaturesText(e.target.value)}
          rows={4}
          className="w-full rounded bg-slate-900 border border-slate-600 text-slate-200 text-xs font-mono p-3 focus:outline-none focus:border-blue-500"
          placeholder="Enter 68 comma-separated numerical values..."
        />
        <button
          onClick={handlePredict}
          disabled={loading || !featuresText.trim()}
          className="px-4 py-2 rounded bg-blue-600 text-white text-sm font-medium hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {loading ? 'Classifying...' : 'Classify Flow'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-4">
          {/* Prediction Card */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-6 text-center">
            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Prediction</p>
            <p className={`text-3xl font-bold ${CLASS_TEXT_COLORS[result.prediction.label] || 'text-white'}`}>
              {result.prediction.label}
            </p>
            <p className="text-sm text-slate-400 mt-1">
              Confidence: {(result.prediction.confidence * 100).toFixed(1)}%
            </p>
          </div>

          {/* Probability Distribution */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">
              Class Probabilities
            </h3>
            <div className="space-y-2">
              {Object.entries(result.probabilities)
                .sort(([, a], [, b]) => b - a)
                .map(([cls, prob]) => (
                  <div key={cls} className="flex items-center gap-3">
                    <span className="text-xs text-slate-400 w-24">{cls}</span>
                    <div className="flex-1 h-4 bg-slate-900 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${CLASS_COLORS[cls] || 'bg-blue-500'}`}
                        style={{ width: `${Math.max(prob * 100, 0.5)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-300 w-16 text-right">
                      {(prob * 100).toFixed(2)}%
                    </span>
                  </div>
                ))}
            </div>
          </div>

          {/* Model Info */}
          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-2">Model Info</h3>
            <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
              <span>Model:</span><span className="text-slate-300">{result.model.name}</span>
              <span>Features:</span><span className="text-slate-300">{result.model.input_features}</span>
              <span>Classes:</span><span className="text-slate-300">{result.model.classes}</span>
              <span>Experiment:</span><span className="text-slate-300">{result.model.experiment_id}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
