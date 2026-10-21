import { useEffect, useState } from 'react';
import { errorMessage, streamSnapshots, type Snapshot } from './api';

export function LiveStream({ token, onSnapshot }: { token: string; onSnapshot: (view: Snapshot) => void }) {
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState('connecting');
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    setStatus('connecting');
    setError('');
    void streamSnapshots(token, controller.signal, view => {
      if (!controller.signal.aborted) { onSnapshot(view); setStatus('receiving'); }
    }).then(() => {
      if (!controller.signal.aborted) setStatus('disconnected');
    }).catch(cause => {
      if (!controller.signal.aborted) { setStatus('disconnected'); setError(errorMessage(cause)); }
    });
    return () => controller.abort();
  }, [token, onSnapshot, attempt]);

  return <section className="stream-bar" aria-label="Live stream">
    <span role="status" className={`status ${status === 'receiving' ? 'healthy' : 'warning'}`}>Stream: {status}</span>
    <span className="muted">{status === 'disconnected' ? 'Last snapshot retained, not live.' : 'Authenticated SSE / read-only'}</span>
    {error && <p role="alert">{error}</p>}
    {status === 'disconnected' && <button onClick={() => setAttempt(value => value + 1)}>Reconnect stream</button>}
  </section>;
}
