import type { Snapshot } from './api';
import { sectionMeta } from './sections';
import { StateBadge } from './StateBadge';
import { EmptyState, ReasonLine, TruncatedNote } from './StatusPanels';

// WO-P1-774 slice C: Tools & Usage read-only view. Inspector inventory
// (tools/hooks/skills) renders only from the accepted monitor-views DTO;
// usage has no event source, so the usage region is explicitly unavailable
// — inventory is never usage history, and no Run/Rename/Invoke exists.
const INSPECTOR_SECTIONS = [
  { key: 'tools', thai: 'เครื่องมือ / Tools' },
  { key: 'hooks', thai: 'Hooks' },
  { key: 'skills', thai: 'Skills' },
] as const;

function text(value: unknown, fallback: string): string {
  return typeof value === 'string' && value.length > 0 ? value : fallback;
}

export function ToolsView({ snapshot }: { snapshot: Snapshot | null }) {
  const meta = sectionMeta('tools');
  if (!snapshot) return <section className="panel" aria-labelledby="tools-missing-title">
    <div className="panel-heading"><h2 id="tools-missing-title">{meta.thai} / {meta.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span></div>
    <EmptyState reason="ยังไม่มี snapshot ที่โหลดแล้ว — ไม่แสดงจำนวนสมมติ" source="Monitor API" />
    <ReasonLine reason="SNAPSHOT_NOT_LOADED" source="Monitor API" observedAt={null} />
    <p className="sf-boundary">{meta.boundary}</p>
  </section>;
  const live = 'error' in snapshot.monitor ? null : snapshot.monitor;
  if (!live) return <section className="panel" aria-labelledby="tools-unavailable-title">
    <div className="panel-heading"><h2 id="tools-unavailable-title">{meta.thai} / {meta.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span></div>
    <EmptyState reason="ยังไม่มีหลักฐาน Inspector สำหรับหน้านี้" source="monitor-views inspector" />
    <ReasonLine reason="INSPECTOR_NOT_PROVIDED" source="monitor-views" observedAt={null} />
    <p className="sf-boundary">{meta.boundary}</p>
  </section>;
  const inspector = live.inspector;
  if (!('summary' in inspector)) return <section className="panel" aria-labelledby="tools-unavailable-title">
    <div className="panel-heading"><h2 id="tools-unavailable-title">{meta.thai} / {meta.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span></div>
    <EmptyState reason={`ยังไม่มีหลักฐาน Inspector สำหรับหน้านี้ — ${inspector.reason}`} source="monitor-views inspector" />
    <ReasonLine reason={inspector.state} source="monitor-views" observedAt={null} />
    <p className="sf-boundary">{meta.boundary}</p>
  </section>;
  return <>
    <ReasonLine reason="INSPECTOR_FROM_MONITOR_VIEWS" source="monitor-views inspector" observedAt={inspector.summary.generated_at} />
    <p className="sf-boundary">{meta.boundary}</p>
    {INSPECTOR_SECTIONS.map(({ key, thai }) => {
      const summary = inspector.summary[key];
      const rows = inspector[key];
      const counts = (Object.entries(summary.counts) as Array<[string, number]>)
        .filter(([, count]) => count > 0)
        .map(([state, count]) => `${state} ${count}`)
        .join(' · ');
      return <section className="panel" key={key} aria-labelledby={`tools-${key}`}>
        <div className="panel-heading"><h2 id={`tools-${key}`}>{thai}</h2>
          <span className="status">{counts || 'UNKNOWN 0'}</span></div>
        <TruncatedNote retained={rows.length} truncated={summary.truncated} dropped={summary.dropped} />
        {rows.length === 0 ? <p className="empty">ไม่มีรายการที่เก็บไว้ใน snapshot นี้</p>
          : <div className="table-scroll"><table>
            <thead><tr><th scope="col">Name</th><th scope="col">State</th><th scope="col">Phase / category</th><th scope="col">Source / provenance</th><th scope="col">Evidence</th></tr></thead>
            <tbody>{rows.map((row: Record<string, unknown>, index: number) => <tr key={`${text(row.name, 'unknown')}-${index}`}>
              <td><strong>{text(row.name, 'ไม่ทราบชื่อ')}</strong><div className="muted">{text(row.device, 'ไม่ทราบอุปกรณ์')}</div></td>
              <td><StateBadge state={text(row.state, '')} /><div className="muted">{text(row.last_error, '') || '—'}</div></td>
              <td>{text(row.phase, 'ไม่ทราบ phase')}<div className="muted">{text(row.category, 'ไม่ทราบหมวด')}</div></td>
              <td>{text(row.source, 'ไม่ทราบแหล่ง')}<div className="muted">{text(row.provenance, 'ไม่ทราบ provenance')}</div></td>
              <td><div>{text(row.registration_evidence, 'ไม่ทราบหลักฐาน')}</div>
                <small>verified: {row.last_verified ? String(row.last_verified) : 'ไม่ทราบเวลา'}</small>
                <div className="muted">next: {text(row.next_safe_action, 'ไม่ทราบ')}</div></td>
            </tr>)}</tbody>
          </table></div>}
      </section>;
    })}
    <section className="panel" aria-labelledby="usage-title">
      <div className="panel-heading"><h2 id="usage-title">การใช้งาน / Usage</h2>
        <StateBadge state="UNKNOWN" /></div>
      <EmptyState reason="ยังไม่มีแหลังงาน usage events" source="usage event source (absent)" />
      <ReasonLine reason="USAGE_EVENT_SOURCE_NOT_PROVIDED" source="inspector inventory" observedAt={null} />
      <p className="muted">inventory ไม่ใช่ usage history — จำนวนที่เห็นข้างต้นเป็นสินค้าคงคลัง ไม่ใช่ประวัติการเรียกใช้</p>
    </section>
  </>;
}
