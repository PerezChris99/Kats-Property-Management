import { useEffect, useState } from 'react';
import { Download, MonitorCheck } from 'lucide-react';

/** Browser-mediated installation; no prompts or cached privileged state. */
export function PwaInstallButton({ role }) {
  const [offer, setOffer] = useState(null);
  const [installed, setInstalled] = useState(() =>
    window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true);
  useEffect(() => {
    const media = window.matchMedia('(display-mode: standalone)');
    const detect = () => setInstalled(media.matches || window.navigator.standalone === true);
    const available = event => {
      event.preventDefault();
      setOffer(event);
    };
    const done = () => { setInstalled(true); setOffer(null); };
    window.addEventListener('beforeinstallprompt', available);
    window.addEventListener('appinstalled', done);
    media.addEventListener?.('change', detect);
    return () => {
      window.removeEventListener('beforeinstallprompt', available);
      window.removeEventListener('appinstalled', done);
      media.removeEventListener?.('change', detect);
    };
  }, []);
  if (role !== 'OWNER') return null;
  if (installed) return <span className="kats-installed-indicator">
    <MonitorCheck size={16} aria-hidden="true"/> Desktop app</span>;
  if (!offer) return null;
  async function install() {
    const event = offer;
    setOffer(null);
    try {
      await event.prompt();
      const choice = await event.userChoice;
      if (choice?.outcome === 'accepted') setInstalled(true);
    } catch {
      // Browser owns install eligibility. Never impersonate success.
    }
  }
  return <button type="button" className="kats-install-trigger" onClick={install}>
    <Download size={16} aria-hidden="true"/> Install desktop app
  </button>;
}
