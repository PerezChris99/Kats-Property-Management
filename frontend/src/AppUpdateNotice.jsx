import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowDownToLine, CheckCircle2, RefreshCw, X } from 'lucide-react';

// The build defines this constant from the exact artifact version used to
// serve this JS. Do not derive updates from a GitHub branch that may not
// have been deployed yet.
const CURRENT_RELEASE = typeof __KATS_BUILD_ID__ === 'string'
  ? __KATS_BUILD_ID__ : null;
const REFRESH_MS = 120000;

/** Shared update discovery for ordinary browser tabs and installed PWAs. */
export function AppUpdateNotice() {
  const [ready, setReady] = useState(false);
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');
  const inFlight = useRef(false);
  const messageTimer = useRef(0);

  const check = useCallback(async (manual = false) => {
    if (inFlight.current) return;
    if (!navigator.onLine) {
      if (manual) setMessage('You are offline. Updates will be checked when the connection returns.');
      return;
    }
    if (!import.meta.env.PROD || !CURRENT_RELEASE) {
      if (manual) setMessage('Update checks are available in deployed builds.');
      return;
    }
    inFlight.current = true;
    if (manual) setChecking(true);
    try {
      // Every navigation loads fresh HTML, but already-open tabs require an
      // explicit deployment marker to discover later releases.
      const response = await fetch('/app-version.json', {
        cache: 'no-store', credentials: 'same-origin',
        headers: { 'Accept': 'application/json' },
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Version manifest unavailable');
      }
      const body = await response.json();
      if (typeof body.version !== 'string' || !/^[A-Za-z0-9._-]{7,150}$/.test(body.version)) {
        throw new Error('Invalid release metadata');
      }
      const newer = body.version !== CURRENT_RELEASE;
      setReady(newer);
      if (manual && !newer) {
        setMessage('You are already using the latest deployed version.');
      }
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        await registration?.update().catch(() => {});
      }
    } catch {
      if (manual) setMessage('Could not check right now. Try again once connected.');
    } finally {
      inFlight.current = false;
      if (manual) setChecking(false);
    }
  }, []);

  useEffect(() => {
    function wake() {
      if (navigator.onLine && !document.hidden) void check(false);
    }
    function manually() { void check(true); }
    wake();
    const timer = window.setInterval(wake, REFRESH_MS);
    window.addEventListener('online', wake);
    window.addEventListener('focus', wake);
    document.addEventListener('visibilitychange', wake);
    window.addEventListener('kats:check-update', manually);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('online', wake);
      window.removeEventListener('focus', wake);
      document.removeEventListener('visibilitychange', wake);
      window.removeEventListener('kats:check-update', manually);
    };
  }, [check]);

  useEffect(() => {
    if (!message) return undefined;
    window.clearTimeout(messageTimer.current);
    messageTimer.current = window.setTimeout(() => setMessage(''), 5200);
    return () => window.clearTimeout(messageTimer.current);
  }, [message]);
  async function apply() {
    if (!navigator.onLine) {
      setMessage('Reconnect to install the latest version.');
      return;
    }
    setChecking(true);
    try {
      if ('serviceWorker' in navigator) {
        const registration = await navigator.serviceWorker.getRegistration();
        await registration?.update().catch(() => {});
      }
    } finally {
      // Deliberate user action: never discard in-progress forms automatically.
      // HTML is network-first, fingerprinted assets load from the new release.
      window.location.reload();
    }
  }
  if (!ready && !message) return null;
  return <aside className="kats-update-notice" aria-label="App version updates"
    role="status" aria-live="polite">
    {ready ? <>
      <span className="kats-update-mark"><ArrowDownToLine size={20} aria-hidden="true"/></span>
      <div><strong>A fresh version of KATS is ready.</strong>
        <p>Get the latest changes across your browser and installed app.</p>
        <div className="kats-update-actions">
          <button type="button" disabled={checking} onClick={apply}
            className="kats-update-apply">
            <RefreshCw size={15} aria-hidden="true"/> Get new update
          </button>
          <button type="button" disabled={checking} onClick={()=>void check(true)}
            className="kats-update-recheck">Check again</button>
        </div>
      </div>
    </> : <>
      <CheckCircle2 size={18} aria-hidden="true"/>
      <span>{message}</span>
      <button className="kats-update-dismiss" type="button" onClick={()=>setMessage('')}
        aria-label="Dismiss update message"><X size={16} aria-hidden="true"/></button>
    </>}
  </aside>;
}

/** Small manual trigger; the alert itself remains globally mounted. */
export function CheckAppUpdatesButton() {
  return <button type="button" className="kats-check-updates"
    aria-label="Check for app updates" title="Check for app updates"
    onClick={()=>window.dispatchEvent(new Event('kats:check-update'))}>
    <RefreshCw size={16} aria-hidden="true"/>
  </button>;
}
