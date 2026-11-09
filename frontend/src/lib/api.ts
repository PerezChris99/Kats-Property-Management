/** KATS API transport: same-origin, non-cacheable and CSRF protected.
 *
 * Concurrent identical GET calls are coalesced only while pending. We do
 * not store completed tenant/account data in memory or browser storage.
 */
function cookie(name: string): string {
  return document.cookie.split('; ').find(c => c.startsWith(name + '='))?.split('=').slice(1).join('=') || ''
}

export function csrfToken(): string {
  return cookie('csrf_access_token')
}

let refreshing: Promise<boolean> | null = null
const inflight = new Map<string, Promise<unknown>>()

function validatePath(path: string): void {
  // Caller must pass an application-relative path, never a user-controlled URL.
  if (!path || path.startsWith('/') || path.includes('\\') ||
      path.split('?')[0].split('/').includes('..') || /[\u0000-\u001f]/.test(path)) {
    throw new Error('Invalid API path')
  }
}

async function refreshAccess(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const token = cookie('csrf_refresh_token')
      if (!token) return false
      try {
        const response = await fetch('/api/v1/auth/refresh', {
          method: 'POST', credentials: 'same-origin', cache: 'no-store',
          headers: {'X-CSRF-TOKEN': token},
          signal: AbortSignal.timeout(12000)
        })
        return response.ok
      } catch {
        return false
      }
    })().finally(() => { refreshing = null })
  }
  return refreshing
}

async function performApi(path: string, options: RequestInit, method: string): Promise<unknown> {
  const perform = () => {
    const headers = new Headers(options.headers)
    if (options.body && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }
    if (method !== 'GET' && method !== 'HEAD') {
      headers.set('X-CSRF-TOKEN', csrfToken())
    }
    return fetch('/api/v1/' + path, {
      ...options,
      method,
      headers,
      credentials: 'same-origin',
      cache: 'no-store',
      signal: options.signal || AbortSignal.timeout(15000)
    })
  }
  let response: Response
  try {
    response = await perform()
    if (response.status === 401 &&
        !['auth/login', 'auth/refresh', 'auth/recover', 'auth/complete-token'].includes(path)) {
      if (await refreshAccess()) {
        response = await perform()
      } else {
        inflight.clear()
        window.dispatchEvent(new Event('kats:session-expired'))
      }
    }
  } catch (reason) {
    if (reason instanceof DOMException && reason.name === 'TimeoutError') {
      throw new Error('Request timed out. Check your connection and retry.')
    }
    throw new Error('Unable to connect. Check your network and try again.')
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 429) {
      throw new Error('Too many requests. Please try again shortly.')
    }
    const serverMessage = payload?.error?.message
    throw new Error(
      typeof serverMessage === 'string' && serverMessage.length <= 300
        ? serverMessage
        : 'Request failed (' + response.status + ')'
    )
  }
  return payload
}

export async function api(path: string, options: RequestInit = {}): Promise<any> {
  validatePath(path)
  const method = (options.method || 'GET').toUpperCase()
  if (method !== 'GET') {
    inflight.clear()
    return performApi(path, options, method)
  }
  // Only coalesce plain GETs; preserve distinct abort signals or headers.
  if (options.signal || options.headers || options.body) {
    return performApi(path, options, method)
  }
  const key = path
  const existing = inflight.get(key)
  if (existing) return existing
  const pending = performApi(path, options, method).finally(() => {
    if (inflight.get(key) === pending) inflight.delete(key)
  })
  inflight.set(key, pending)
  return pending
}
