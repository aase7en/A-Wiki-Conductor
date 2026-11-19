import { useCallback, useEffect, useRef, useState } from 'react';
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
  const [streamDisconnected, setStreamDisconnected] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [section, setSection] = useState<SectionId>(DEFAULT_SECTION);
  // A late HTTP response (including failure) cannot supersede a newer SSE event.
  const streamRevision = useRef(0);
  useEffect(() => {
    const controller = new AbortController();
    const requestRevision = streamRevision.current;
    setError('');
    void getSnapshot(token, controller.signal).then(view => {
      if (!controller.signal.aborted && streamRevision.current === requestRevision) { setSnapshot(view); setReady(true); }
    }).catch(cause => {
      if (!controller.signal.aborted && streamRevision.current === requestRevision) {
        setError(errorMessage(cause));
        // The last successful projection is no longer safe to present as current.
        setSnapshot(previous => previous ? {
          ...previous, stale: true,
          stale_reason: previous.stale ? previous.stale_reason : 'SNAPSHOT_REFRESH_FAILED',
        } : null);
      }
    });
    return () => controller.abort();
  }, [token, attempt]);

  const onStreamSnapshot = useCallback((view: Snapshot) => {
    streamRevision.current += 1;
    setSnapshot(view);
    setStreamDisconnected(false);
    // An authenticated, validated stream snapshot can restore freshness.
    setError('');
  }, []);
  const onStreamDisconnect = useCallback(() => {
    setStreamDisconnected(true);
  }, []);

  const meta = sectionMeta(section);
  // Do not claim stale data is current when SSE drops or a refresh fails.
  // The stream loss remains visible even if a later HTTP refresh succeeds.
  const displayedSnapshot = snapshot && (error || streamDisconnected)
    ? {
        ...snapshot, stale: true,
        stale_reason: error
          ? (snapshot.stale ? snapshot.stale_reason : 'SNAPSHOT_REFRESH_FAILED')
          : snapshot.stale ? snapshot.stale_reason ?? 'STREAM_DISCONNECTED' : 'STREAM_DISCONNECTED',
        monitor_stream_degraded: snapshot.monitor_stream_degraded || streamDisconnected,
      }
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
        <p>อ่าน Snapshot ใหม่ไม่สำเร็จ — SNAPSHOT_REFRESH_FAILED. ข้อมูลที่ค้างอยู่เป็น STALE (ข้อมูลเก่า). {error}</p>
        <button onClick={() => setAttempt(value => value + 1)}>Retry snapshot</button>
      </section>}
      {displayedSnapshot?.stale && !error && <p role="status" className="notice">Snapshot is STALE — {displayedSnapshot.stale_reason ?? 'freshness not verified'}.</p>}
      {ready && <LiveStream token={token} onSnapshot={onStreamSnapshot} onDisconnect={onStreamDisconnect} />}
      {section === 'overview' ? <>
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
