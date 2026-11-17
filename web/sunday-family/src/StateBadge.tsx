// WO-P1-774 slice A: shared truthful status component.
// Accepts the UX-1/WO-P1-750 state vocabulary plus fleet/work states.
// Code + Thai meaning always render together (never color-only); any
// unrecognized code fails closed to UNKNOWN and never renders healthy.
export type KnownState =
  | 'READY' | 'AVAILABLE' | 'RUNNING' | 'WAITING'
  | 'STALE' | 'DEGRADED' | 'BLOCKED' | 'DISCONNECTED' | 'UNKNOWN';

const STATE_META: Record<KnownState, { meaning: string; tone: string }> = {
  READY: { meaning: 'พร้อมตามหลักฐาน', tone: 'verified' },
  AVAILABLE: { meaning: 'พบใน registry', tone: 'verified' },
  RUNNING: { meaning: 'กำลังทำงาน', tone: 'running' },
  WAITING: { meaning: 'รอค้างอยู่', tone: 'waiting' },
  STALE: { meaning: 'หลักฐานเก่า ไม่ใช่สถานะปกติ', tone: 'waiting' },
  DEGRADED: { meaning: 'ข้อมูลหรือการตรวจมีปัญหา', tone: 'degraded' },
  BLOCKED: { meaning: 'ติดบล็อก', tone: 'blocked' },
  DISCONNECTED: { meaning: 'ขาดการเชื่อมต่อ', tone: 'blocked' },
  UNKNOWN: { meaning: 'ยังไม่มีหลักฐานยืนยัน', tone: 'unknown' },
};

const isKnownState = (value: string): value is KnownState => value in STATE_META;

export function StateBadge({ state, note }: { state: string; note?: string | null }) {
  const known = isKnownState(state);
  const meta = known ? STATE_META[state] : STATE_META.UNKNOWN;
  return <span className={`sf-badge sf-badge--${meta.tone}`} data-state={known ? state : 'UNKNOWN'}>
    <span className="sf-badge-code">{known ? state : 'UNKNOWN'}</span>
    <span className="sf-badge-meaning">{known ? meta.meaning : `รหัสสถานะไม่รู้จัก: ${state || '(ว่าง)'}`}</span>
    {note && <span className="sf-badge-note">{note}</span>}
  </span>;
}
