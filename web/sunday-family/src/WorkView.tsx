import type { Snapshot } from './api';
import { LanesTable } from './LanesTable';
import { sectionMeta } from './sections';
import { EmptyState, ReasonLine } from './StatusPanels';

// WO-P1-774 slice B: Work & Lanes per-section view. Cockpit lanes are the
// only accepted lane projection; Projects/Claims/Roadmap joins have no DTO
// yet and render explicit unavailable panels — never fabricated counts.
// Thai wording settled with Jev consultation 2026-11-18 (claims label
// การถือครองงาน 0.77; roadmap label not overpromising 0.23; explicit
// boundary form chosen in code after an unsettled 0.34/0.59 probe pair).
const WORK_SUBPANELS = [
  { thai: 'โปรเจกต์ / Projects', reasonCode: 'PROJECT_DTO_NOT_PROVIDED', reason: 'ยังไม่มี project DTO จาก API นี้' },
  { thai: 'การถือครองงาน / Claims', reasonCode: 'CLAIM_PROJECTION_NOT_PROVIDED', reason: 'ยังไม่มี claim projection จาก API นี้' },
  { thai: 'โรดแมป / Roadmap', reasonCode: 'ROADMAP_DTO_NOT_PROVIDED', reason: 'ยังไม่มี roadmap join จาก API นี้ — ไม่ใช่โรดแมปที่สมบูรณ์' },
] as const;

export function WorkView({ snapshot, error, onRetry }: {
  snapshot: Snapshot | null; error: string; onRetry: () => void;
}) {
  const meta = sectionMeta('work');
  if (!snapshot) return <section className="panel" aria-labelledby="work-missing-title">
    <div className="panel-heading"><h2 id="work-missing-title">{meta.thai} / {meta.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span></div>
    <EmptyState reason="ยังไม่มี snapshot ที่โหลดแล้ว — ไม่แสดงจำนวนสมมติ" source="Monitor API" />
    <ReasonLine reason="SNAPSHOT_NOT_LOADED" source="Monitor API" observedAt={null} />
    {error && <p role="alert" className="notice">{error}</p>}
    <button onClick={onRetry}>Retry snapshot</button>
    <p className="sf-boundary">{meta.boundary}</p>
  </section>;
  return <>
    <LanesTable lanes={snapshot.cockpit.lanes} generatedAt={snapshot.generated_at}
      stale={snapshot.stale} staleReason={snapshot.stale_reason} streamDegraded={snapshot.monitor_stream_degraded} />
    <ReasonLine reason={meta.reasonCode} source="cockpit snapshot" observedAt={snapshot.generated_at} />
    <p className="sf-boundary">{meta.boundary}</p>
    <div className="secondary-grid">
      {WORK_SUBPANELS.map(panel => <section key={panel.reasonCode} className="panel" aria-labelledby={`work-${panel.reasonCode}`}>
        <div className="panel-heading"><h2 id={`work-${panel.reasonCode}`}>{panel.thai}</h2></div>
        <EmptyState reason={panel.reason} source="cockpit snapshot" />
        <ReasonLine reason={panel.reasonCode} source="cockpit snapshot" observedAt={null} />
        <p className="muted">เจ้าของ / HEAD / claim: ไม่ทราบ</p>
      </section>)}
    </div>
  </>;
}
