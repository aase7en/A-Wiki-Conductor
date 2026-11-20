import { useEffect, useState } from 'react';
import { errorMessage, getHealth, type Health } from './api';

export function HealthIndicator({ token }: { token: string }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    async function check() {
      try {
        const result = await getHealth(token, controller.signal);
        if (!controller.signal.aborted) { setHealth(result); setError(''); }
      } catch (cause) {
        if (!controller.signal.aborted) { setHealth(null); setError(errorMessage(cause)); }
      }
    }
    void check();
    const timer = window.setInterval(() => void check(), 30_000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [token]);

  return <section aria-label="API health" className="health">
    <span className={`status ${error || health?.degraded || health?.status !== 'ok' ? 'warning' : 'healthy'}`}>
      API: {error ? 'unavailable' : !health ? 'checking' : health.status !== 'ok' ? health.status : health.degraded ? 'degraded' : 'healthy'}
    </span>
    {error && <p role="alert">{error}</p>}
    {health && <details><summary>Health details</summary>
      <p>{health.profile} / {health.version}</p>
      <ul>{health.conditions.map(condition => <li key={condition}>{condition}</li>)}</ul>
    </details>}
  </section>;
}
