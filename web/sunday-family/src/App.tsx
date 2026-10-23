import { useEffect, useState } from 'react';
import { errorMessage, getSnapshot, type Snapshot } from './api';
import { HealthIndicator } from './HealthIndicator';
import { LiveStream } from './LiveStream';
import { SnapshotView } from './SnapshotView';
import { TokenGate } from './TokenGate';
import { MetricsPanel } from './MetricsPanel';

function Monitor({ token, disconnect }: { token: string; disconnect: () => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    void getSnapshot(token, controller.signal).then(view => {
      if (!controller.signal.aborted) { setSnapshot(view); setReady(true); }
    }).catch(cause => {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    });
    return () => controller.abort();
  }, [token, attempt]);

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to monitor</a>
    <aside className="sidebar">
      <div><p className="eyebrow">SUNDAY FAMILY</p><p className="brand">A-Sunday<br />Conductor<span className="brand-dot">.</span></p>
        <p className="muted">Orchestrate. Execute. Observe.</p></div>
      <nav aria-label="Monitor sections"><a href="#snapshot">01 / Execution lanes</a><a href="#connectors">02 / Connectors</a><a href="#activity">03 / Activity</a></nav>
      <div className="sidebar-footer"><p className="eyebrow">HEADLESS / LOCAL</p><p className="muted">Session metadata controls.<br />No process execution authority.</p><button onClick={disconnect}>Disconnect &amp; clear token</button></div>
    </aside>
    <main id="main" className="workspace">
      <header className="workspace-header"><div><p className="eyebrow">CONTROL PLANE / LOCAL MONITOR</p><h1>System overview</h1></div><HealthIndicator token={token} /></header>
      {ready && <LiveStream token={token} onSnapshot={setSnapshot} />}
      <MetricsPanel token={token} />
      {error && <section className="notice" role="alert"><p>{error}</p><button onClick={() => setAttempt(value => value + 1)}>Retry snapshot</button></section>}
      {snapshot ? <SnapshotView snapshot={snapshot} token={token} /> : !error && <p role="status" className="empty">Loading monitor snapshot...</p>}
      <footer className="workspace-footer">SF-WEB / Monitor v1 <span>Local data. Explicit limitations. No fabricated state.</span></footer>
    </main>
  </div>;
}

export default function App() {
  return <TokenGate>{(token, disconnect) => <Monitor key={token} token={token} disconnect={disconnect} />}</TokenGate>;
}
