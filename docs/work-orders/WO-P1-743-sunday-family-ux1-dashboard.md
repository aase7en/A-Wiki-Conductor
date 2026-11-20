# WO-P1-743 SundayFamily Unified Dashboard Design

Issue: #743
Identity note: UX-1 design lane; charter and operator directives live on #739
(comments 6759816854 / 6760564625 / 6765523868). Created as its own issue per
the work-order identity policy (numeric ids unique + Issue line must match);
supersedes the provisional name WO-P1-739-UX1 used in the claim comment.
Status: DESIGN_PREVIEW / AUTHORING_COMPLETE / ACCEPTANCE_PENDING
Classification: R0 DOCS proposal; no binding runtime/security contract change.
Topology: CONTROL_PLANE_ONLY documentation.
Base: `main@16b897a` (orchestrator supplied; no executor Git verification).
Worktree: `A:\GitHub\_worktrees\AWC-739-ux1`
Branch: `docs/739-ux1-design` (orchestrator supplied, clean at dispatch).
Claim: `UX1-739-DESIGN-001`.
Owner/scope: https://github.com/aase7en/A-Wiki-Conductor/issues/739#issuecomment-6770451351

## 1. Objective And Context

ออกแบบ SundayFamily โปรแกรมเดียวสำหรับดูสถานะ หลักฐาน และการตั้งค่า
โดยผู้ใช้สั่งงานด้วยภาษาธรรมชาติ ไม่ต้องรู้ชื่อหรือเรียก tool เอง
Charter: #739 comment 6759816854; single-app addendum: 6765523868.
ต้อง audit Tk, Monitor+Inspector, React แล้วสรุป IA, wireframes,
design system, Tk migration matrix และ packaging feasibility ให้ operator พิจารณา
เอกสารชุดนี้เสนอ target-state ไม่ยืนยันว่าหน้าจอหรือ integration ทำงานแล้ว

## 2. Exact Mutable Scope

1. `docs/design/2026-11-10-ux1-surface-audits.md`
2. `docs/work-orders/WO-P1-743-sunday-family-ux1-dashboard.md`
3. `docs/design/2026-11-10-sunday-family-ux1-design.md`
4. `docs/design/sunday-family-ux1-mockup.html`

ห้ามแก้ไฟล์อื่น รวม `CURRENT-WORK.md`, `handoff.md`, shared claim tables
ผู้เขียนใช้ read/glob/grep และ write/edit เท่านั้น ไม่ใช้ shell/Git/GitHub
Orchestrator เป็นผู้ตรวจ identity/claim/non-overlap และ fold continuity หลังรับงาน

## 3. Failure Model And Non-Goals

- ไม่แก้ `src/`, tests, frontend production, dependencies หรือ config
- ไม่เปิด service, ไม่ probe runtime, ไม่เปลี่ยน connector/process state
- ไม่สร้าง scheduler/control plane/claim authority ใหม่
- ไม่เสนอ browser → SRM mutation หรือ direct tool invocation UI
- ไม่แสดง token, tunnel IDs, raw secrets หรือ raw exception text
- ไม่เรียกสถานะ UNKNOWN/STALE/DEGRADED ว่า healthy
- ไม่ถือ ToolPhase หรือ hook contract presence เป็น readiness
- ไม่อ้างว่า accepted command stub คือ execution สำเร็จ
- ไม่ประกาศ Tk retired; runtime boundary `:112-117` ยังบังคับใช้
- Packaging เป็น feasibility proposal ไม่ใช่ dependency/release/security approval

## 4. Acceptance Criteria

- [x] สาม surface audits ถูกรวมพร้อม anchors, A/B/C classes และ wiring gaps
- [x] IA Thai-first 7 รายการ ระบุ purpose/blocks/today/after-wiring/read-only scope
- [x] Text wireframes ครบ Overview, Fleet, Tools & Usage, Settings, Jev
- [x] Design tokens/components/state matrix รวม AVAILABLE skills-only และ redaction
- [x] Tk per-feature verdict + IA destination; connector controls deferred
- [x] Shell A/B/C analysis + recommendation + token security follow-up
- [x] Existing pack-build seam, web hosting gap และ naming/migration slices ระบุชัด
- [x] Offline single-file HTML มี SAMPLE DATA banner และไม่มี external resources
- [x] Proposed UX-2/3/4 dependency/gates ไม่ให้ implementation authority
- [ ] Orchestrator ตรวจ exact 4-file diff, UTF-8, links, anchors และ HTML
- [ ] Operator ดู mockup และบันทึก green-light พร้อม decision answers บน #739 ก่อน UX-2
- [ ] PR ผ่าน exact-head review/CI/merge/post-main gate และ checkpoint บน #739

เครื่องหมายครบด้านเนื้อหาหมายถึง authored ไม่ใช่ verified runtime/accepted design

## 5. Evidence Plan

Inputs read: reference WO-P1-739, prior SF-web roadmap, runtime boundary, AGENTS;
entry/graph/CURRENT-WORK, DESIGN และ delivery/collaboration protocol อ่านเป็นบริบท
Audits: orchestrator-supplied delegated code audit at `16b897a`, 2026-11-10;
source provenance/line-level vs file-level distinction อยู่ใน surface-audits doc
No fabricated line anchors when an audit supplied only a file/module identifier

Orchestrator verification checklist:
- ตรวจ branch/HEAD/dirty/claim และ non-overlap จากสถานะจริง
- ตรวจว่ามีเพียง 4 outputs และไม่มี source/dependency/generated artifacts
- ตรวจ UTF-8 Thai, relative links, exact truth colors และ sample labels
- เปิด HTML offline; ตรวจ 390/900/1280px, keyboard focus, Thai wrapping, no overflow
- ตรวจไม่มี fetch/storage/auth inputs, external resources หรือ executable action UI
- ตรวจ state counts จาก retained rows, truncated/dropped note และ empty-state semantics
- ตรวจไม่มี token/tunnel IDs/secrets และไม่มี READY จาก absence
- บันทึก evidence ของ visual check; ผู้เขียนยังไม่ได้รัน browser/HTML validator

## 6. Delivery Gates

`exact reviewed head -> CI run ID on that exact head -> merge expected-head only`
`-> post-main CI run ID -> checkpoint on #739`

Review head: PENDING orchestrator.
Exact-head CI: PENDING orchestrator.
PR / merge / post-main CI: PENDING orchestrator.
Operator mockup green-light: PENDING #739 comment; author does not grant it.
All Git/PR/CI/merge operations belong to orchestrator, not this executor.

## 7. Exit Criteria And Handoff

Authoring exit: all four files readable with coherent cross-links and truthful labels
Lane delivery exit: scoped docs accepted through the gate sequence above
UX-2 start gate: operator green-light recorded + separate WO/claim/dependencies reviewed
UX-3/4 require their own WOs; auth/installer mutations need appropriate risk escalation
Exact next safe action: orchestrator reviews the four-file packet and renders mockup
Forbidden next action: infer source mutation, runtime activation, Tk retirement,
auto-token handoff, or release authority from this packet
Shared continuity updates remain orchestrator-owned because outside executor scope
