import { useState, useEffect } from 'react'
import { getAccessRole } from '@/lib/apiClient'
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
  const [recordAlert, setRecordAlert] = useState(false)
  const [sampleClass, setSampleClass] = useState('Normal')
  const [sampleNote, setSampleNote] = useState('')
  const [sampleLoading, setSampleLoading] = useState(false)
  const operator = getAccessRole() === 'operator' 

  useEffect(() => {
    predictService.health().then(setHealth).catch(e => setError(String(e)))
  }, [])

  const handlePredict = async () => {
    if (!operator || loading) return
    setError(null)
    setResult(null)
    setLoading(true)
    try {
      const parts = featuresText.split(',').map(s => s.trim())
      if (parts.some(s => !s)) throw new Error('Empty feature value')
      const features = parts.map(Number)

      if (features.some(v => !Number.isFinite(v))) {
        throw new Error('All values must be valid numbers separated by commas')
      }
      if (features.length !== 68) {
        throw new Error(`Expected 68 features, got ${features.length}`)
      }
      const res = await predictService.predict(features, recordAlert)
      setResult(res)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Prediction failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleSampleData = async () => {
    setSampleLoading(true); setError(null); setResult(null); setSampleNote(''); setFeaturesText(''); setRecordAlert(false)
    try {
      const data = await predictService.samples()
      const sample = data.samples.find(s => s.label === sampleClass)
      if (!sample) throw new Error('Sample unavailable')
      setFeaturesText(sample.features.join(', '))
      setSampleNote(`Held-out CICIDS2017 sample · seed ${data.seed} · test index ${sample.test_index} · reference label: ${sample.label}`)
    } catch (err) { setError(err instanceof Error ? err.message : 'Sample unavailable') }
    finally { setSampleLoading(false) }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Network Flow Prediction</h1>
        <p className="text-sm text-slate-400 mt-1">
          Classify submitted raw features using ThreatNet. No live packet capture or traffic blocking.
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
              {health.model_loaded && health.normalization_loaded ? 'Ready for inference' : 'Inference unavailable'}
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
          <div className="flex gap-2 items-center flex-wrap">
          <select aria-label="Benchmark class" value={sampleClass} disabled={!operator || loading || sampleLoading} onChange={e => setSampleClass(e.target.value)} className="bg-slate-900 text-slate-200 rounded p-2 text-sm">
            {Object.keys(CLASS_COLORS).map(c => <option key={c}>{c}</option>)}
          </select>
          <button
            disabled={!operator || loading || sampleLoading}
            onClick={handleSampleData}
            className="text-xs px-3 py-1 rounded bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
          >
            {sampleLoading ? 'Loading…' : 'Load held-out sample'}
          </button>
          </div>
        </div>
        <textarea
          value={featuresText}
          disabled={!operator || loading || sampleLoading}
          onChange={(e) => { setFeaturesText(e.target.value); setSampleNote(''); setResult(null) }}
          rows={4}
          className="w-full rounded bg-slate-900 border border-slate-600 text-slate-200 text-xs font-mono p-3 focus:outline-none focus:border-blue-500"
          placeholder="Enter 68 comma-separated numerical values..."
        />
        {sampleNote && <p className="text-xs text-cyan-300">{sampleNote}. Reference label is not sent to the classifier.</p>}
        {!operator && <p className="text-sm text-amber-300">Viewer access is read-only. Sign in as an operator to classify flows.</p>}
        <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={recordAlert} disabled={!operator || loading || sampleLoading} onChange={e => setRecordAlert(e.target.checked)} /> Record a predicted attack alert (no raw features stored)</label>
        <button
          onClick={handlePredict}
          disabled={!operator || loading || sampleLoading || !health?.model_loaded || !health?.normalization_loaded || !featuresText.trim()}
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
              Selected class probability: {(result.prediction.confidence * 100).toFixed(1)}%
            </p>
          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4 text-sm text-slate-300 space-y-2">
            <h3 className="font-semibold text-white">Decision and alert recording</h3>
            {result.attack_score != null && <p>Combined attack probability: {(result.attack_score * 100).toFixed(2)}%{result.attack_threshold != null && ` · Attack threshold: ${(result.attack_threshold * 100).toFixed(0)}%`}</p>}
            <p>Decision rule: {result.decision_rule ?? 'Not reported'}. The attack gate can change an attack argmax to Normal when the combined attack probability is below the threshold. Scores are not calibrated certainty.</p>
            <p>{result.alert_id ? `Saved prediction alert: ${result.alert_id}` : 'No alert saved.'} Predictions are not confirmed security incidents.</p>
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
                        style={{ width: `${prob * 100}%` }}
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
