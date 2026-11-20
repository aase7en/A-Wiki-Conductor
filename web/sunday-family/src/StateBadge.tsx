// WO-P1-774 slice A: shared truthful status component.
// Accepts the UX-1/WO-P1-750 state vocabulary plus fleet/work states.
// Code + Thai meaning always render together (never color-only); any
// unrecognized code fails closed to UNKNOWN and never renders healthy.
export type KnownState =
  | 'READY' | 'AVAILABLE' | 'RUNNING' | 'WAITING'
  | 'STALE' | 'DEGRADED' | 'BLOCKED' | 'DISCONNECTED' | 'UNKNOWN'
  | 'NOT_DISPATCHED' | 'PENDING_SCOPE' | 'BORROWED_ACTIVE'
  | 'WAITING_APPROVAL' | 'WAITING_CI' | 'WAITING_GLM' | 'WAITING_JEV'
  | 'WAITING_EXTERNAL' | 'COOLDOWN' | 'PARKED_CAPACITY'
  | 'HUMAN_REQUIRED' | 'STALLED_RECONCILE' | 'TERMINAL_UNHARVESTED'
  | 'OUTCOME_UNKNOWN' | 'FAILED_VERIFIED' | 'COMPLETED_VERIFIED';

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
  NOT_DISPATCHED: { meaning: 'ยังไม่ส่งงาน', tone: 'unknown' },
  PENDING_SCOPE: { meaning: 'รอยืนยันขอบเขตงาน', tone: 'waiting' },
  BORROWED_ACTIVE: { meaning: 'เลนที่ยืมกำลังทำงาน', tone: 'running' },
  WAITING_APPROVAL: { meaning: 'รอการอนุมัติ', tone: 'waiting' },
  WAITING_CI: { meaning: 'รอ CI', tone: 'waiting' },
  WAITING_GLM: { meaning: 'รอ GLM', tone: 'waiting' },
  WAITING_JEV: { meaning: 'รอ Jev', tone: 'waiting' },
  WAITING_EXTERNAL: { meaning: 'รอระบบภายนอก', tone: 'waiting' },
  COOLDOWN: { meaning: 'พักตามข้อจำกัดเวลา', tone: 'waiting' },
  PARKED_CAPACITY: { meaning: 'พักเพื่อรอความจุ', tone: 'waiting' },
  HUMAN_REQUIRED: { meaning: 'ต้องให้มนุษย์ตัดสินใจ', tone: 'blocked' },
  STALLED_RECONCILE: { meaning: 'ค้างและต้องตรวจสอบ', tone: 'degraded' },
  TERMINAL_UNHARVESTED: { meaning: 'จบแล้วแต่ยังไม่รับผล', tone: 'waiting' },
  OUTCOME_UNKNOWN: { meaning: 'ผลลัพธ์ยังไม่ทราบ', tone: 'unknown' },
  FAILED_VERIFIED: { meaning: 'ตรวจยืนยันว่าล้มเหลว', tone: 'blocked' },
  COMPLETED_VERIFIED: { meaning: 'ตรวจยืนยันว่าเสร็จแล้ว', tone: 'verified' },
};

const isKnownState = (value: string): value is KnownState => Object.prototype.hasOwnProperty.call(STATE_META, value);

export function StateBadge({ state, note }: { state: string; note?: string | null }) {
  const known = isKnownState(state);
  const meta = known ? STATE_META[state] : STATE_META.UNKNOWN;
  return <span className={`sf-badge sf-badge--${meta.tone}`} data-state={known ? state : 'UNKNOWN'}>
    <span className="sf-badge-code">{known ? state : 'UNKNOWN'}</span>
    <span className="sf-badge-meaning">{known ? meta.meaning : `รหัสสถานะไม่รู้จัก: ${state || '(ว่าง)'}`}</span>
    {note && <span className="sf-badge-note">{note}</span>}
  </span>;
}
