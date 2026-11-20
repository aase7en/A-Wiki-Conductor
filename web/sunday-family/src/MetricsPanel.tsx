import { useEffect, useState } from 'react';
import { errorMessage, getMetrics, type SystemMetrics } from './api';

export function MetricsPanel({ token }: { token: string }) {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setMetrics(null);
    void getMetrics(token, controller.signal).then(value => {
      if (!controller.signal.aborted) setMetrics(value);
    }).catch(cause => {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [token, attempt]);

  const memory = metrics?.memory_used_bytes != null && metrics.memory_total_bytes != null && metrics.memory_total_bytes > 0
    ? `${(metrics.memory_used_bytes / 1024 ** 3).toFixed(1)} / ${(metrics.memory_total_bytes / 1024 ** 3).toFixed(1)} GiB`
    : 'Unavailable';
  return <section className="panel" aria-labelledby="metrics-title" id="metrics">
    <div className="panel-heading"><h2 id="metrics-title">System metrics</h2>
      <button disabled={loading} onClick={() => setAttempt(value => value + 1)}>Refresh metrics</button></div>
    {loading && <p role="status">Reading system metrics...</p>}
    {error && <p role="alert">{error}</p>}
    <dl className="metrics-grid" aria-live="polite">
      <div><dt>CPU</dt><dd>{metrics?.cpu_percent != null ? `${metrics.cpu_percent.toFixed(1)}%` : 'Unavailable'}</dd></div>
      <div><dt>RAM</dt><dd>{memory}</dd></div>
    </dl>
    <p className="muted">API host metrics. CPU is sampled between reads; unsupported readings remain unavailable.</p>
  </section>;
}
