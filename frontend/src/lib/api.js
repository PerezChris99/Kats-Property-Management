/** KATS API transport: same-origin, non-cacheable and CSRF protected.
 *
 * Concurrent identical GET calls are coalesced only while pending. We do
 * not store completed tenant/account data in memory or browser storage.
 */
function cookie(name) {
    return document.cookie.split('; ').find(c => c.startsWith(name + '='))?.split('=').slice(1).join('=') || '';
}
export function csrfToken() {
    return cookie('csrf_access_token');
}
let refreshing = null;
const inflight = new Map();
function validatePath(path) {
    // Caller must pass an application-relative path, never a user-controlled URL.
    if (!path || /^[a-z][a-z0-9+.-]*:/i.test(path) || path.startsWith('/') || path.includes('\\') ||
        path.split('?')[0].split('/').includes('..') || /[\u0000-\u001f]/.test(path)) {
        throw new Error('Invalid API path');
    }
}
async function refreshAccess() {
    if (!refreshing) {
        refreshing = (async () => {
            const token = cookie('csrf_refresh_token');
            if (!token)
                return false;
            try {
                const response = await fetch('/api/v1/auth/refresh', {
                    method: 'POST', credentials: 'same-origin', cache: 'no-store',
                    headers: { 'X-CSRF-TOKEN': token },
                    signal: AbortSignal.timeout(12000)
                });
                return response.ok;
            }
            catch {
                return false;
            }
        })().finally(() => { refreshing = null; });
    }
    return refreshing;
}
// Transient mobile-network faults are retried only for safe reads. Writes,
// payments and account actions are NEVER blindly replayed: doing so can
// duplicate side effects when the first response was lost.
function networkAvailable() {
    return typeof navigator === 'undefined' || navigator.onLine !== false;
}
function retryPause(ms, signal) {
    return new Promise((resolve, reject) => {
        if (signal?.aborted) {
            reject(signal.reason || new DOMException('Request aborted', 'AbortError'));
            return;
        }
        const finish = () => {
            signal?.removeEventListener('abort', aborted);
            resolve();
        };
        const timer = setTimeout(finish, ms);
        function aborted() {
            clearTimeout(timer);
            signal?.removeEventListener('abort', aborted);
            reject(signal.reason || new DOMException('Request aborted', 'AbortError'));
        }
        signal?.addEventListener('abort', aborted, { once: true });
    });
}

async function performApi(path, options, method) {
    const perform = () => {
        const headers = new Headers(options.headers);
        if (options.body && !(options.body instanceof FormData)) {
            headers.set('Content-Type', 'application/json');
        }
        if (method !== 'GET' && method !== 'HEAD') {
            headers.set('X-CSRF-TOKEN', csrfToken());
        }
        return fetch('/api/v1/' + path, {
            ...options,
            method,
            headers,
            credentials: 'same-origin',
            cache: 'no-store',
            signal: options.signal || AbortSignal.timeout(15000)
        });
    };
    let response;
    const attempts = method === 'GET' ? 3 : 1;
    for (let attempt = 0; attempt < attempts; attempt++) {
        try {
            if (options.signal?.aborted)
                throw options.signal.reason || new DOMException('Request aborted', 'AbortError');
            response = await perform();
            if (response.status === 401 &&
                !['auth/login', 'auth/refresh', 'auth/recover', 'auth/complete-token'].includes(path)) {
                if (await refreshAccess()) {
                    response = await perform();
                } else {
                    inflight.clear();
                    window.dispatchEvent(new Event('kats:session-expired'));
                }
            }
        } catch (reason) {
            if (reason instanceof DOMException && reason.name === 'AbortError')
                throw reason;
            if (attempt + 1 < attempts && networkAvailable() && !options.signal?.aborted) {
                await retryPause(180 * (2 ** attempt), options.signal);
                continue;
            }
            if (!networkAvailable()) {
                throw new Error('You are offline. Reconnect and retry the request.');
            }
            if (reason instanceof DOMException && reason.name === 'TimeoutError')
                throw new Error('Request timed out. Check your connection and retry.');
            throw new Error('Unable to connect. Check your network and try again.');
        }
        // Service unavailable / gateway timeout may be temporary, but do not
        // retry 401/403/409/429 or any financial/other mutation.
        if (attempt + 1 < attempts && [502, 503, 504].includes(response.status)
            && networkAvailable() && !options.signal?.aborted) {
            await retryPause(180 * (2 ** attempt), options.signal);
            continue;
        }
        break;
    }
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
        if (response.status === 429) {
            throw new Error('Too many requests. Please try again shortly.');
        }
        const serverMessage = payload?.error?.message;
        throw new Error(typeof serverMessage === 'string' && serverMessage.length <= 300
            ? serverMessage
            : 'Request failed (' + response.status + ')');
    }
    return payload;
}
export async function api(path, options = {}) {
    validatePath(path);
    const method = (options.method || 'GET').toUpperCase();
    if (method !== 'GET') {
        inflight.clear();
        return performApi(path, options, method);
    }
    // Only coalesce plain GETs; preserve distinct abort signals or headers.
    if (options.signal || options.headers || options.body) {
        return performApi(path, options, method);
    }
    const key = path;
    const existing = inflight.get(key);
    if (existing)
        return existing;
    const pending = performApi(path, options, method).finally(() => {
        if (inflight.get(key) === pending)
            inflight.delete(key);
    });
    inflight.set(key, pending);
    return pending;
}
