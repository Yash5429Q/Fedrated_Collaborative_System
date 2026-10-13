import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  message:   string
  onRetry?:  () => void
  detail?:   string
}

/** Shown when an API call fails — displays error message with optional retry button. */
export default function ErrorState({ message, onRetry, detail }: Props) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20">
      <div className="rounded-full bg-red-500/10 p-4">
        <AlertTriangle className="h-7 w-7 text-red-400" />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold text-red-400">{message}</p>
        {detail && <p className="mt-1 text-xs text-gray-500">{detail}</p>}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-md border border-cyber-600 bg-cyber-800 px-4 py-2 text-xs font-medium text-gray-300 transition hover:border-accent-cyan/50 hover:text-accent-cyan"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Retry
        </button>
      )}
    </div>
  )
}
