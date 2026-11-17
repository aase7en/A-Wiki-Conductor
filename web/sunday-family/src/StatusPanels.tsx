import type { SectionMeta } from './sections';
import { StateBadge } from './StateBadge';

// WO-P1-774 slice A: shared truth panels. Missing sources render explicit
// unavailable states — never fabricated zeros, totals, or healthy badges.

export function EmptyState({ reason, source }: { reason?: string | null; source?: string | null }) {
  return <div className="sf-empty">
    <StateBadge state="UNKNOWN" />
    <p>ไม่มีหลักฐาน{reason ? ` — ${reason}` : ''}</p>
    {source && <p className="sf-source">source: {source}</p>}
  </div>;
}

export function ReasonLine({ reason, source, observedAt }: {
  reason?: string | null; source?: string | null; observedAt?: string | null;
}) {
  return <p className="sf-reason">
    {reason && <span className="sf-reason-code">{reason}</span>}
    {source && <span>source: {source}</span>}
    <span>observed-at: {observedAt ?? 'ไม่ทราบเวลา'}</span>
  </p>;
}

export function TruncatedNote({ retained, dropped, truncated }: {
  retained: number; dropped?: number | null; truncated: boolean;
}) {
  return <p className="sf-truncated" data-truncated={String(truncated)}>
    แสดง {retained} รายการที่คงไว้{truncated ? ` — truncated=true; dropped=${dropped ?? 'ไม่ทราบ'}` : ''}
  </p>;
}

export function UnavailablePanel({ section }: { section: SectionMeta }) {
  return <section className="panel sf-unavailable" aria-labelledby={`section-${section.id}`}>
    <div className="panel-heading">
      <h2 id={`section-${section.id}`}>{section.thai} / {section.english}</h2>
      <span className="status">SECTION_UNAVAILABLE</span>
    </div>
    <EmptyState reason={section.reason} />
    <ReasonLine reason={section.reasonCode} observedAt={null} />
    <p className="sf-boundary">{section.boundary}</p>
  </section>;
}
