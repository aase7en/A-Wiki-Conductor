// WO-P1-774 slice A: the seven accepted Thai-first primary sections
// (DESIGN_LOCKED_FOR_CARD_04 / UX-1 seven-domain IA). Order is canonical;
// Projects/Claims/Roadmap live inside Work & Lanes, never as new top-level menus.
export type SectionId = 'overview' | 'fleet' | 'work' | 'tools' | 'settings' | 'jev' | 'activity';

export interface SectionMeta {
  id: SectionId;
  thai: string;
  english: string;
  // Placeholder truth until the section's accepted read model is wired
  // (slices B-D). Reason codes are plain sanitized codes, never exceptions.
  reasonCode: string;
  reason: string;
  boundary: string;
}

export const SECTIONS: readonly SectionMeta[] = [
  {
    id: 'overview',
    thai: 'ภาพรวม',
    english: 'Overview',
    reasonCode: 'OVERVIEW_FROM_SNAPSHOT',
    reason: 'มุมมองรวมมาจาก normalized snapshot ของ Monitor API เท่านั้น',
    boundary: 'อ่านอย่างเดียว — ไม่มี start/retry และไม่อนุมานความสำเร็จ',
  },
  {
    id: 'fleet',
    thai: 'ทีมเครื่อง',
    english: 'Fleet',
    reasonCode: 'FLEET_PROJECTION_NOT_PROVIDED',
    reason: 'ยังไม่มี device projection จาก API นี้ — session connector ไม่ใช่ fleet device',
    boundary: 'อ่านอย่างเดียว — ไม่มี Start/Stop/Pair/Rebind/Delete',
  },
  {
    id: 'work',
    thai: 'งานและเลน',
    english: 'Work & Lanes',
    reasonCode: 'LANE_PROJECTION_FROM_COCKPIT',
    reason: 'มุมมองเลนมาจาก cockpit snapshot — project/claim/roadmap joins ยังไม่มี DTO',
    boundary: 'หน้านี้อ่านอย่างเดียว — แก้การถือครองงาน (claims) หรือตารางเวลา (schedule) ไม่ได้ ข้อมูลที่ขาดแสดงเป็น ไม่ทราบ',
  },
  {
    id: 'tools',
    thai: 'เครื่องมือและการใช้งาน',
    english: 'Tools & Usage',
    reasonCode: 'INSPECTOR_FROM_MONITOR_VIEWS',
    reason: 'มาจาก monitor-views inspector projection — usage events ยังไม่มีแหลังงาน',
    boundary: 'อ่านอย่างเดียว — ไม่มี Run/Rename/Invoke',
  },
  {
    id: 'settings',
    thai: 'ตั้งค่า',
    english: 'Settings',
    reasonCode: 'SETTINGS_READ_MODEL_PENDING',
    reason: 'ยังไม่มี safe settings projection — ค่าที่แสดงต้องมาจาก server policy เท่านั้น',
    boundary: 'อ่านอย่างเดียว — ไม่มี Save/Install หรือ browser policy authority',
  },
  {
    id: 'jev',
    thai: 'มุมตัดสินใจ',
    english: 'Jev',
    reasonCode: 'JEV_ADVISORY_UNAVAILABLE',
    reason: 'ยังไม่มีคำแนะนำที่มีหลักฐาน — คำแนะนำไม่ใช่คำอนุมัติ',
    boundary: 'READ_ONLY advisory — ไม่มี Execute/Auto-approve/Retry',
  },
  {
    id: 'activity',
    thai: 'บันทึกกิจกรรม',
    english: 'Activity & Logs',
    reasonCode: 'ACTIVITY_READER_UNAVAILABLE',
    reason: 'ยังไม่มี activity feed จาก API นี้ — stream snapshot ไม่ใช่ activity log',
    boundary: 'อ่าน sanitized records เท่านั้น — SSE connected ไม่ใช่ progress/ผลลัพธ์',
  },
];

export const DEFAULT_SECTION: SectionId = 'overview';

export function sectionMeta(id: SectionId): SectionMeta {
  const meta = SECTIONS.find(section => section.id === id);
  if (!meta) throw new Error('Unknown section.');
  return meta;
}
