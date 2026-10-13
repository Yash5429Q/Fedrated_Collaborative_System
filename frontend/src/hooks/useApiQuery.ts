/**
 * Generic data-fetching hook with loading, error, and retry state.
 * All domain hooks are built on top of this.
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { ApiError } from '@/lib/apiClient'

export interface ApiQueryState<T> {
  data:     T | null
  loading:  boolean
  error:    string | null
  refetch:  () => void
}

export function useApiQuery<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): ApiQueryState<T> {
  const [data,    setData]    = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState<string | null>(null)

  // Stable ref so `execute` doesn't depend on `fetcher` identity
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const execute = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetcherRef.current()
      setData(result)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(
          err.status === 0
            ? 'Cannot reach the backend server. Make sure it is running on port 8000.'
            : `Server error ${err.status}: ${err.message}`,
        )
      } else {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
      }
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => { execute() }, [execute])

  return { data, loading, error, refetch: execute }
}
