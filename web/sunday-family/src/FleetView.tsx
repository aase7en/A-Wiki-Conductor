import { useEffect, useState } from 'react';
import { errorMessage, getConnectors, type Connector } from './api';
import { sectionMeta } from './sections';
import { StateBadge } from './StateBadge';
import { EmptyState, ReasonLine } from './StatusPanels';

// WO-P1-774 slice C: Fleet monitor-only view. No accepted fleet device DTO
// exists, so every device row renders UNKNOWN with explicit missing
// evidence — never a fabricated READY. Session connectors appear only as
// clearly-labeled evidence; this section contains no control actions.
// (Jev meta-judgment on boundary-sentence clarity proved unreliable
// (0.29 → 0.04 against more explicit wording); decided structurally:
// no control buttons exist here at all.)
const FLEET_DEVICES = ['Windows (SundayMCP)', 'Mac (SundayMCP)'] as const;
const CONNECTORS_INTRO = 'connector ของ session นี้เท่านั้น — ไม่ใช่อุปกรณ์ในทีมเครื่อง';

export function FleetView({ token }: { token: string }) {
  const meta = sectionMeta('fleet');
  const [connectors, setConnectors] = useState<Connector[] | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    void getConnectors(token, controller.signal).then(value => {
      if (!controller.signal.aborted) setConnectors(value);
    }).catch(cause => {
      if (!controller.signal.aborted) setError(errorMessage(cause));
    });
    return () => controller.abort();
  }, [token, attempt]);

  return <>
    <section className="panel" aria-labelledby="fleet-devices-title">
      <div className="panel-heading"><h2 id="fleet-devices-title">อุปกรณ์ / Devices</h2>
        <span className="status">MONITOR_ONLY</span></div>
      <EmptyState reason="ยังไม่มี device projection — สถานะอุปกรณ์ทุกเครื่องคือ UNKNOWN" source="accepted fleet device DTO (absent)" />
      <ReasonLine reason={meta.reasonCode} source="fleet read model" observedAt={null} />
      <div className="table-scroll"><table>
        <thead><tr><th scope="col">อุปกรณ์ / Device</th><th scope="col">สถานะ / State</th><th scope="col">เวลา / หลักฐาน</th></tr></thead>
        <tbody>{FLEET_DEVICES.map(device => <tr key={device}>
          <td><strong>{device}</strong></td>
          <td><StateBadge state="UNKNOWN" /></td>
          <td>observed-at: ไม่ทราบเวลา — ยังไม่มีหลักฐาน</td>
        </tr>)}</tbody>
      </table></div>
      <p className="sf-boundary">{meta.boundary}</p>
    </section>
    <section className="panel" aria-labelledby="fleet-connectors-title">
      <div className="panel-heading"><h2 id="fleet-connectors-title">Session connectors (หลักฐานประกอบ)</h2>
        <button onClick={() => setAttempt(value => value + 1)}>Refresh connectors</button></div>
      <p className="muted">{CONNECTORS_INTRO}</p>
      {error && <div role="alert" className="notice">
        <p>ไม่สามารถอ่าน connectors ได้ — ไม่มีหลักฐานให้แสดง</p>
        <ReasonLine reason="CONNECTORS_READ_FAILED" source="app-session connectors" observedAt={null} />
      </div>}
      {!error && connectors && (connectors.length === 0
        ? <p className="empty">ไม่มี connector ใน session นี้</p>
        : <div className="table-scroll"><table>
          <thead><tr><th scope="col">Connector</th><th scope="col">State</th></tr></thead>
          <tbody>{connectors.map(connector => <tr key={connector.connector_id}>
            <td><strong>{connector.name}</strong><div className="muted">{connector.connector_id}</div></td>
            <td><span className="status">{connector.state}</span><div className="muted">Session metadata only</div></td>
          </tr>)}</tbody>
        </table></div>)}
    </section>
  </>;
}
