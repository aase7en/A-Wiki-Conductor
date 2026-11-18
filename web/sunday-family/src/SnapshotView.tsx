import type { Snapshot } from './api';
import { ConnectorsPanel } from './ConnectorsPanel';
import { LanesTable } from './LanesTable';

// WO-P1-750: accepted UX-1 state tokens, coarse per-section counts only.
const STATE_TOKENS = ['READY', 'AVAILABLE', 'STALE', 'DEGRADED', 'DISCONNECTED', 'UNKNOWN'] as const;

function SectionCounts({ counts }: { counts: Record<string, number> }) {
  const visible = STATE_TOKENS.filter(token => (counts[token] ?? 0) > 0);
  if (visible.length === 0) return <span className="status">UNKNOWN 0</span>;
  return <>{visible.map(token => <span key={token} className="status">{token} {counts[token]}</span>)}</>;
}

export function SnapshotView({ snapshot, token }: { snapshot: Snapshot; token?: string }) {
  const live = 'error' in snapshot.monitor ? null : snapshot.monitor;
  const sections: Array<{ name: string; counts: Record<string, number> }> = [];
  if (live && 'summary' in live.inspector) {
    for (const section of ['tools', 'hooks', 'skills'] as const) {
      sections.push({ name: section, counts: live.inspector.summary[section].counts });
    }
  }
  return <>
    <LanesTable lanes={snapshot.cockpit.lanes} generatedAt={snapshot.generated_at}
      stale={snapshot.stale} staleReason={snapshot.stale_reason} streamDegraded={snapshot.monitor_stream_degraded} />
    <div className="secondary-grid">
      {live && <section id="monitor" className="panel" aria-labelledby="monitor-title">
        <div className="panel-heading"><h2 id="monitor-title">Monitor</h2>
          <span className={`status ${live.health.degraded ? 'warning' : ''}`}>{live.health.degraded ? 'DEGRADED' : 'READY'}</span></div>
        <div className="snapshot-meta">{sections.map(section => <p key={section.name}>
          <strong>{section.name[0].toUpperCase() + section.name.slice(1)}</strong>{' '}
          <SectionCounts counts={section.counts} />
        </p>)}</div>
      </section>}
      {token ? <ConnectorsPanel token={token} /> : <section id="connectors" className="panel" aria-labelledby="connectors-title">
        <div className="panel-heading"><h2 id="connectors-title">Connectors</h2><span className="status warning">Unavailable</span></div>
        <p>No connector health projection is provided by this API.</p>
        {'error' in snapshot.monitor && <p className="muted">{snapshot.monitor.gate} / {snapshot.monitor.error}</p>}
      </section>}
      <section id="activity" className="panel" aria-labelledby="activity-title">
        <div className="panel-heading"><h2 id="activity-title">Activity</h2><span className="status warning">Unavailable</span></div>
        <p>No activity feed is provided by this API. Stream snapshots are not an activity log.</p>
      </section>
    </div>
    {snapshot.degraded_observability.length > 0 && <section className="panel" aria-labelledby="conditions-title">
      <h2 id="conditions-title">Observability conditions</h2>
      <ul className="conditions">{snapshot.degraded_observability.map(condition => <li key={condition}>{condition}</li>)}</ul>
    </section>}
  </>;
}
