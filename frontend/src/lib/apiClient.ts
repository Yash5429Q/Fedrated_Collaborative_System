/**
 * Central HTTP client for all backend API calls.
 *
 * All requests go through /api which Vite proxies to http://localhost:8000.
 * Do NOT call fetch() directly in components or hooks — use this client.
 */

function resolveUrl(path: string): string {
  const rawBase = (import.meta.env.VITE_API_BASE_URL || '/api').trim()
  const base = rawBase.replace(/\/+$/, '')
  const normPath = path.startsWith('/') ? path : `/${path}`

  if (base.endsWith('/api')) {
    if (normPath === '/api') {
      return base
    }
    if (normPath.startsWith('/api/')) {
      return `${base}${normPath.slice(4)}`
    }
    return `${base}${normPath}`
  }

  if (normPath === '/api' || normPath.startsWith('/api/')) {
    return `${base}${normPath}`
  }
  return `${base}/api${normPath}`
}

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


export type AccessRole = 'viewer' | 'operator'
let role: AccessRole | null = null
export function getAccessRole() { return role }
export function setAccessRole(value: AccessRole) { role = value }
let accessToken = ''
export function setAccessToken(token: string) { accessToken = token.trim() }
export function clearAccessToken() { accessToken = ''; role = null }

/* ── Core request helper ──────────────────────────────────── */

async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = resolveUrl(path)
  const token = accessToken
  const headers = new Headers(options?.headers)
  headers.set('Content-Type', 'application/json')
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  let res: Response
  try {
    res = await fetch(url, {
      ...options, headers, cache: 'no-store', redirect: 'error',
    })
  } catch {
    throw new ApiError(0, `Network error — could not reach ${url}`)
  }

  if (!res.ok) {
    if (res.status === 401 && token === accessToken) {
      clearAccessToken()
      window.dispatchEvent(new Event('cyber20-access-denied'))
    }
    let body: unknown
    try { body = await res.json() } catch { body = null }
    const msg =
      (typeof body === 'object' && body !== null && 'message' in body)
        ? String((body as { message: unknown }).message)
        : (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string')
        ? body.detail
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
