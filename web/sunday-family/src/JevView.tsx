import { sectionMeta } from './sections';
import { EmptyState, ReasonLine } from './StatusPanels';

// WO-P1-774 slice D: Jev corner. No advisory contract/DTO exists yet
// (UX-3), so the corner renders explicit unavailable with UNKNOWN —
// advice is never authorization and no Execute/Auto-approve/Retry exists.
// Wording settled with Jev 2026-11-18 (authorization-misread noul 0.28).
export function JevView() {
  const meta = sectionMeta('jev');
  return <section className="panel" aria-labelledby="jev-title">
    <div className="panel-heading"><h2 id="jev-title">{meta.thai} / {meta.english}</h2>
      <span className="status">READ_ONLY advisory</span></div>
    <EmptyState reason={meta.reason} source="advisory contract (UX-3, pending)" />
    <ReasonLine reason={meta.reasonCode} source="advisory contract" observedAt={null} />
    <p className="sf-boundary">คำแนะนำไม่ใช่คำอนุมัติ — {meta.boundary}</p>
  </section>;
}
