import type { Snapshot } from './api';
import { StateBadge } from './StateBadge';

// WO-P1-774 slice B: shared lane projection table used by Overview and
// Work & Lanes. Markup kept verbatim from the accepted UX-1 lane panel;
// the lane state now renders through the fail-closed StateBadge so an
// unrecognized state code can never look healthy.
export function LanesTable({ lanes, generatedAt, stale, staleReason, streamDegraded }: {
  lanes: Snapshot['cockpit']['lanes'];
  generatedAt: string | null;
  stale: boolean;
  staleReason: string | null;
  streamDegraded: boolean;
}) {
  return <section className="panel" id="snapshot" aria-labelledby="snapshot-title">
    <div className="panel-heading"><h2 id="snapshot-title">Execution lanes</h2><span>{lanes.length} observed</span></div>
    <div className="snapshot-meta">
      <span>Generated: {generatedAt ?? 'unknown'}</span>
      <span className={`status ${stale ? 'warning' : ''}`}>{stale ? `Stale: ${staleReason ?? 'reason unavailable'}` : 'Current at source'}</span>
    </div>
    {streamDegraded && <p role="alert" className="notice">Stream degraded: updates may have been dropped.</p>}
    {lanes.length === 0 ? <p className="empty">No execution lanes in this snapshot.</p>
      : <div className="table-scroll"><table>
        <thead><tr><th scope="col">Lane / work order</th><th scope="col">Observed state</th><th scope="col">Blocker / next action</th><th scope="col">Gates</th></tr></thead>
        <tbody>{lanes.map((lane, index) => <tr key={`${lane.identity.execution_id ?? lane.identity.lease_id ?? lane.identity.lane}-${index}`}>
          <td><strong>{lane.identity.lane ?? 'Unknown lane'}</strong><br />{lane.identity.work_order_ref ?? lane.identity.task_ref ?? 'No task reference'}
            <div className="muted">{lane.identity.execution_id ?? 'Execution unknown'}</div></td>
          <td><StateBadge state={stale ? 'STALE' : lane.state}
            note={stale ? `Last reported: ${lane.state} (unverified)` : undefined} />
            <div>{lane.state_markers.join(' / ')}</div>
            <small>Progress: {lane.last_meaningful_progress ?? 'unknown'}</small></td>
          <td>{lane.blocker_code ?? 'No blocker reported'}<div className="muted">{lane.next_safe_action ?? 'Next action unavailable'}</div></td>
          <td>{Object.entries(lane.gates).filter(([name]) => name !== 'provenance').map(([name, value]) => <div key={name}>{name}: {value ?? 'UNKNOWN'}</div>)}</td>
        </tr>)}</tbody>
      </table></div>}
  </section>;
}
