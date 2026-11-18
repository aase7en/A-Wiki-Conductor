import { useEffect, useState } from 'react';
import { errorMessage, getSnapshot, type Snapshot } from './api';
import { HealthIndicator } from './HealthIndicator';
import { LiveStream } from './LiveStream';
import { SnapshotView } from './SnapshotView';
import { TokenGate } from './TokenGate';
import { MetricsPanel } from './MetricsPanel';
import { DEFAULT_SECTION, SECTIONS, sectionMeta, type SectionId } from './sections';
import { ActivityView } from './ActivityView';
import { FleetView } from './FleetView';
import { JevView } from './JevView';
import { SettingsView } from './SettingsView';
import { ToolsView } from './ToolsView';
import { WorkView } from './WorkView';

function Monitor({ token, disconnect }: { token: string; disconnect: () => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [section, setSection] = useState<SectionId>(DEFAULT_SECTION);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    void getSnapshot(token, controller.signal).then(view => {
      if (!controller.signal.aborted) { setSnapshot(view); setReady(true); }
    }).catch(cause => {
      if (!controller.signal.aborted) {
        setError(errorMessage(cause));
        // The last successful projection is no longer safe to present as current.
        setSnapshot(previous => previous ? {
          ...previous, stale: true, stale_reason: 'SNAPSHOT_REFRESH_FAILED',
        } : null);
      }
    });
    return () => controller.abort();
  }, [token, attempt]);

  const meta = sectionMeta(section);
  // A failed authenticated refresh invalidates the freshness claim of any
  // retained frame, even if an SSE message races with the failed request.
  const displayedSnapshot = snapshot && error
    ? { ...snapshot, stale: true, stale_reason: 'SNAPSHOT_REFRESH_FAILED' }
    : snapshot;

  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to monitor</a>
    <aside className="sidebar">
      <div><p className="eyebrow">SUNDAY FAMILY</p><p className="brand">A-Sunday<br />Conductor<span className="brand-dot">.</span></p>
        <p className="muted">อ่านอย่างเดียว — Orchestrate. Observe.</p></div>
      <nav aria-label="ส่วนงานหลัก / Primary sections">
        {SECTIONS.map(item => <button key={item.id} type="button" className="nav-item"
          aria-current={section === item.id ? 'page' : undefined} onClick={() => setSection(item.id)}>
          <span className="nav-thai">{item.thai}</span>
          <span className="nav-english">{item.english}</span>
        </button>)}
      </nav>
      <div className="sidebar-footer"><p className="eyebrow">HEADLESS / LOCAL</p><p className="muted">Session metadata controls.<br />No process execution authority.</p><button onClick={disconnect}>Disconnect &amp; clear token</button></div>
    </aside>
    <main id="main" className="workspace">
      <header className="workspace-header"><div><p className="eyebrow">CONTROL PLANE / LOCAL MONITOR</p><h1>{meta.thai} / {meta.english}</h1>
        <button type="button" onClick={() => setAttempt(value => value + 1)}>Refresh snapshot</button>
      </div><HealthIndicator token={token} /></header>
      {error && <section className="notice" role="alert">
        <p>อ่าน Snapshot ใหม่ไม่สำเร็จ — ข้อมูลที่ค้างอยู่เป็น STALE (ข้อมูลเก่า). {error}</p>
        <button onClick={() => setAttempt(value => value + 1)}>Retry snapshot</button>
      </section>}
      {displayedSnapshot?.stale && !error && <p role="status" className="notice">Snapshot is STALE — {displayedSnapshot.stale_reason ?? 'freshness not verified'}.</p>}
      {section === 'overview' ? <>
        {ready && <LiveStream token={token} onSnapshot={setSnapshot} />}
        <MetricsPanel token={token} />
        {displayedSnapshot ? <SnapshotView snapshot={displayedSnapshot} token={token} /> : !error && <p role="status" className="empty">Loading monitor snapshot...</p>}
      </> : section === 'work' ? <WorkView snapshot={displayedSnapshot} error={error} onRetry={() => setAttempt(value => value + 1)} />
        : section === 'fleet' ? <FleetView token={token} />
        : section === 'tools' ? <ToolsView snapshot={displayedSnapshot} />
        : section === 'settings' ? <SettingsView token={token} />
        : section === 'jev' ? <JevView />
        : <ActivityView snapshot={displayedSnapshot} />}
      <footer className="workspace-footer">SF-WEB / Monitor v1 <span>Local data. Explicit limitations. No fabricated state.</span></footer>
    </main>
  </div>;
}

export default function App() {
  return <TokenGate>{(token, disconnect) => <Monitor key={token} token={token} disconnect={disconnect} />}</TokenGate>;
}
