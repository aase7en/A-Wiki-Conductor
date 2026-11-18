import type { Snapshot } from './api';
import { sectionMeta } from './sections';
import { EmptyState, ReasonLine } from './StatusPanels';

// WO-P1-774 slice D: Activity & Logs. The only accepted source is the
// monitor-views timeline (sanitized monitor events). It is never a work
// activity log: SSE connected is not progress and not an accepted result.
// The work-activity region stays explicitly unavailable until a separate
// safe event/log DTO WO exists. Wording settled with Jev 2026-11-18
// (timeline disclaimer clarity noul 0.78).
function text(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback;
}

export function ActivityView({ snapshot }: { snapshot: Snapshot | null }) {
  const meta = sectionMeta('activity');
  if (!snapshot) return <section className="panel" aria-labelledby="activity-missing-title">
    <div className="panel-heading"><h2 id="activity-missing-title">{meta.thai} / {meta.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span></div>
    <EmptyState reason="ยังไม่มี snapshot ที่โหลดแล้ว — ไม่แสดงรายการสมมติ" source="Monitor API" />
    <ReasonLine reason="SNAPSHOT_NOT_LOADED" source="Monitor API" observedAt={null} />
    <p className="sf-boundary">{meta.boundary}</p>
  </section>;
  const live = 'error' in snapshot.monitor ? null : snapshot.monitor;
  return <>
    {live ? <section className="panel" aria-labelledby="activity-timeline-title">
      <div className="panel-heading"><h2 id="activity-timeline-title">{meta.thai} / Monitor events</h2>
        <span>{live.timeline.length} events</span></div>
      <p className="muted">timeline นี้เป็นเหตุการณ์ของ monitor เท่านั้น — SSE connected ไม่ใช่ความคืบหน้าหรือผลลัพธ์ที่ยอมรับแล้ว</p>
      <p className="sf-reason">จำนวนแถวที่ได้รับ: {live.timeline.length} (ขีดจำกัด API 64 แถว)</p>
      <ReasonLine reason={meta.reasonCode} source="monitor-views timeline" observedAt={null} />
      {live.timeline.length === 0 ? <p className="empty">ไม่มีเหตุการณ์ใน timeline นี้</p>
        : <div className="table-scroll"><table>
          <thead><tr><th scope="col">Event</th><th scope="col">Class</th><th scope="col">เวลา / Time</th><th scope="col">Note</th></tr></thead>
          <tbody>{live.timeline.map((row: Record<string, unknown>, index: number) => <tr key={`${text(row.event_id, 'unknown')}-${index}`}>
            <td>{text(row.event_type, 'ไม่ทราบประเภท')}<div className="muted">{text(row.event_id, 'ไม่ทราบ id')}</div></td>
            <td>{text(row.hook_class, 'ไม่ทราบ class')}</td>
            <td>{text(row.occurred_at, 'ไม่ทราบเวลา')}</td>
            <td>{text(row.note, '—')}</td>
          </tr>)}</tbody>
        </table></div>}
    </section> : <section className="panel" aria-labelledby="activity-timeline-unavailable-title">
      <div className="panel-heading"><h2 id="activity-timeline-unavailable-title">{meta.thai} / Monitor events</h2>
        <span className="status">SECTION_UNAVAILABLE</span></div>
      <EmptyState reason="monitor projection ไม่พร้อมใช้งาน — ไม่มี timeline ให้แสดง" source="monitor-views timeline" />
      <ReasonLine reason="TIMELINE_NOT_PROVIDED" source="monitor-views" observedAt={null} />
      <ReasonLine reason={meta.reasonCode} source="monitor-views timeline" observedAt={null} />
    </section>}
    <section className="panel" aria-labelledby="activity-worklog-title">
      <div className="panel-heading"><h2 id="activity-worklog-title">Activity log ของงาน / Work activity</h2>
        <span className="status">SECTION_UNAVAILABLE</span></div>
      <EmptyState reason="ยังไม่มี activity feed ของงานจาก API นี้ — stream snapshot ไม่ใช่ activity log" source="safe event/log DTO (separate WO)" />
      <ReasonLine reason="ACTIVITY_READER_UNAVAILABLE" source="monitor API" observedAt={null} />
      <p className="sf-boundary">{meta.boundary}</p>
    </section>
  </>;
}
