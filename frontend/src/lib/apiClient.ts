/**
 * Central HTTP client for all backend API calls.
 *
 * All requests go through /api which Vite proxies to http://localhost:8000.
 * Do NOT call fetch() directly in components or hooks — use this client.
 */

const BASE = '/api'

/* ── Custom error ─────────────────────────────────────────── */

export class ApiError extends Error {
  readonly status: number
  readonly body?: unknown
  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.name   = 'ApiError'
    this.status = status
    this.body   = body
  }
}


/* ── Core request helper ──────────────────────────────────── */

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${BASE}${path}`
  let res: Response
  try {
    res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      ...options,
    })
  } catch (err) {
    throw new ApiError(0, `Network error — could not reach ${url}`)
  }

  if (!res.ok) {
    let body: unknown
    try { body = await res.json() } catch { body = null }
    const msg =
      (typeof body === 'object' && body !== null && 'message' in body)
        ? String((body as { message: unknown }).message)
        : `HTTP ${res.status} ${res.statusText}`
    throw new ApiError(res.status, msg, body)
  }

  return res.json() as Promise<T>
}

/* ── Public client ────────────────────────────────────────── */

export const apiClient = {
  get:  <T>(path: string)                    => request<T>(path),
  post: <T>(path: string, body: unknown)     => request<T>(path, { method: 'POST',  body: JSON.stringify(body) }),
  put:  <T>(path: string, body: unknown)     => request<T>(path, { method: 'PUT',   body: JSON.stringify(body) }),
  del:  <T>(path: string)                    => request<T>(path, { method: 'DELETE' }),
}
