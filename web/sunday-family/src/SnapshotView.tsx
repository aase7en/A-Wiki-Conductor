import type { Snapshot } from './api';
import { ConnectorsPanel } from './ConnectorsPanel';

export function SnapshotView({ snapshot, token }: { snapshot: Snapshot; token?: string }) {
  return <>
    <section className="panel" id="snapshot" aria-labelledby="snapshot-title">
      <div className="panel-heading"><h2 id="snapshot-title">Execution lanes</h2><span>{snapshot.cockpit.lanes.length} observed</span></div>
      <div className="snapshot-meta">
        <span>Generated: {snapshot.generated_at ?? 'unknown'}</span>
        <span className={`status ${snapshot.stale ? 'warning' : ''}`}>{snapshot.stale ? `Stale: ${snapshot.stale_reason ?? 'reason unavailable'}` : 'Current at source'}</span>
      </div>
      {snapshot.monitor_stream_degraded && <p role="alert" className="notice">Stream degraded: updates may have been dropped.</p>}
      {snapshot.cockpit.lanes.length === 0 ? <p className="empty">No execution lanes in this snapshot.</p>
        : <div className="table-scroll"><table>
          <thead><tr><th scope="col">Lane / work order</th><th scope="col">Observed state</th><th scope="col">Blocker / next action</th><th scope="col">Gates</th></tr></thead>
          <tbody>{snapshot.cockpit.lanes.map((lane, index) => <tr key={`${lane.identity.execution_id ?? lane.identity.lease_id ?? lane.identity.lane}-${index}`}>
            <td><strong>{lane.identity.lane ?? 'Unknown lane'}</strong><br />{lane.identity.work_order_ref ?? lane.identity.task_ref ?? 'No task reference'}
              <div className="muted">{lane.identity.execution_id ?? 'Execution unknown'}</div></td>
            <td><span className="status">{lane.state}</span><div>{lane.state_markers.join(' / ')}</div>
              <small>Progress: {lane.last_meaningful_progress ?? 'unknown'}</small></td>
            <td>{lane.blocker_code ?? 'No blocker reported'}<div className="muted">{lane.next_safe_action ?? 'Next action unavailable'}</div></td>
            <td>{Object.entries(lane.gates).filter(([name]) => name !== 'provenance').map(([name, value]) => <div key={name}>{name}: {value ?? 'UNKNOWN'}</div>)}</td>
          </tr>)}</tbody>
        </table></div>}
    </section>
    <div className="secondary-grid">
      {token ? <ConnectorsPanel token={token} /> : <section id="connectors" className="panel" aria-labelledby="connectors-title">
        <div className="panel-heading"><h2 id="connectors-title">Connectors</h2><span className="status warning">Unavailable</span></div>
        <p>No connector health projection is provided by this API.</p>
        <p className="muted">{snapshot.monitor.gate} / {snapshot.monitor.error}</p>
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
