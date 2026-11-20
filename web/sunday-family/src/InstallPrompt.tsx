import { useEffect, useState } from 'react';

interface InstallEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export function InstallPrompt() {
  const [prompt, setPrompt] = useState<InstallEvent | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => {
    const available = (event: Event) => {
      event.preventDefault();
      setPrompt(event as InstallEvent);
      setMessage('');
    };
    const installed = () => { setPrompt(null); setMessage('App installed.'); };
    window.addEventListener('beforeinstallprompt', available);
    window.addEventListener('appinstalled', installed);
    return () => {
      window.removeEventListener('beforeinstallprompt', available);
      window.removeEventListener('appinstalled', installed);
    };
  }, []);

  async function install() {
    if (!prompt || pending) return;
    setPending(true);
    setPrompt(null);
    try {
      await prompt.prompt();
      await prompt.userChoice;
    } catch {
      setMessage('Installation unavailable. Use your browser menu to install.');
    } finally {
      setPending(false);
    }
  }

  return <div className="install-prompt">
    {prompt && <button type="button" disabled={pending} onClick={() => void install()}>Install app</button>}
    {message && <p role="status">{message}</p>}
  </div>;
}
