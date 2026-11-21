import { useEffect, useState } from 'react';
import { Download, MonitorCheck } from 'lucide-react';

// Chrome can fire the event while a user is still signing in. Capture it at
// app-module load, not only after the protected workspace component mounts.
let pendingInstall = null;
if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    pendingInstall = event;
    window.dispatchEvent(new Event('kats:pwa-install-available'));
  });
}

/** Browser-mediated installation; no prompts or cached privileged state. */
export function PwaInstallButton() {
  const [offer, setOffer] = useState(pendingInstall);
  const [installed, setInstalled] = useState(() =>
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true);
  useEffect(() => {
    const media = window.matchMedia('(display-mode: standalone)');
    const detect = () => setInstalled(media.matches || window.navigator.standalone === true);
    const available = () => setOffer(pendingInstall);
    const done = () => { pendingInstall = null; setInstalled(true); setOffer(null); };
    window.addEventListener('kats:pwa-install-available', available);
    window.addEventListener('appinstalled', done);
    media.addEventListener?.('change', detect);
    return () => {
      window.removeEventListener('kats:pwa-install-available', available);
      window.removeEventListener('appinstalled', done);
      media.removeEventListener?.('change', detect);
    };
  }, []);
  if (installed) return <span className="kats-installed-indicator">
    <MonitorCheck size={16} aria-hidden="true"/> Installed app</span>;
  if (!offer) {
    const appleMobile = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
      (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    return appleMobile ? <details className="kats-install-help"><summary>Install app</summary>
      <p>In Safari, open Share, choose Add to Home Screen, then tap Add.</p>
    </details> : null;
  }
  async function install() {
    const event = offer;
    pendingInstall = null;
    setOffer(null);
    try {
      await event.prompt();
      await event.userChoice;
    } catch {
      // Browser owns install eligibility. Never impersonate success.
    }
  }
  return <button type="button" className="kats-install-trigger" onClick={install}>
    <Download size={16} aria-hidden="true"/> Install app
  </button>;
}
