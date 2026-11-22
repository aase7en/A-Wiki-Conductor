# WO-P1-784: Docs-hygiene — แก้ resume instruction ที่ข้าม gate + README current-state snapshot

Identity schema: GITHUB_ISSUE_V1
Issue: #784
Status: MERGED / POST_MAIN_VERIFIED / CLAIM_RELEASED (PR #785 cdc5b25 -> main@7f52cb5; CI 44961189948 SUCCESS 4/4; #784 c7071041487)
Lane/files: `docs/work-orders/README.md`, `README.md`, `docs/work-orders/WO-P1-784-docs-hygiene.md` (ไฟล์นี้) — ห้ามแตะอย่างอื่น
Branch: `docs/wo-p1-784-docs-hygiene` (isolated worktree `A:\GitHub\_worktrees\AWC-wo784-docs-hygiene`)
Model tier: primary-only (GLM-5.3 MAX, Kilo Code CLI)

## Goal + Acceptance criteria

แก้ drift ที่ audit ยืนยันแล้ว 2 จุด (Issue #784; #771 audit D1+D2):

- **D1** `docs/work-orders/README.md`: resume prompt เดิมสั่ง "เสร็จแล้ว merge เข้า main + set done" โดยไม่มี review/CI/integrator gate — ขัดกับ binding policy ปัจจุบัน (exact-SHA review → exact-head CI → GPT/integrator expected-head merge → post-main verify)
- **D2** `README.md`: บรรยาย current product เป็น Serena/tunnel/Tk ล้วน + อ้าง "no server" — ต้องเป็น dated snapshot ที่แยก v0.6.0 published release / 0.7.0 development source / Tk desktop (legacy-supported) / SundayFamily Web read-only candidate (#776 OPEN ยังไม่ release) / SunDayRemoteMCP substrate + SundayMCP-first (#725)

Acceptance (วัดได้):

1. ไม่เหลือ instruction แบบ merge-โดยไม่ผ่าน gate ใน active docs (grep คำเดิมใน resume prompt ต้องไม่เจอ)
2. README ไม่ claim UX-2/#776 ว่า delivered/installed/live; แยกเวอร์ชันทั้งสี่ตามจริง; install/download instructions และ historical references ที่ valid ยังใช้ได้ครบ
3. diff = allowlist 3 ไฟล์เท่านั้น; UTF-8 + trailing newline; `git diff --check` สะอาด; ไม่มี secret
4. `tests/test_work_order_identity.py` และ `tests/test_agent_context_economy_config.py` ผ่าน (py -3.13)
5. exact-head hosted CI + nonauthoring R2 review ก่อน merge; merge เป็นสิทธิ์ของ GPT/integrator เท่านั้น (ไม่ self-merge/self-approve)

## Reference pattern

- `docs/work-orders/WO-P1-782-sdlc-virtual-flow-docs.md` — โครง WO/claim/verdict ล่าสุดบน main
- `docs/work-orders/WO-TEMPLATE.md` — โครงหลักของ repo

## Steps

1. Bootstrap: worktree จาก `origin/main@be162763` + ไฟล์นี้ + claim comment บน Issue #784 (เสร็จแล้ว ดู Checkpoint log)
2. D1: แก้ resume prompt ใน `docs/work-orders/README.md` เป็นลำดับ claim → implement → deterministic verify → freeze SHA → risk-appropriate nonauthoring review + exact-head CI → integrator expected-head merge → post-main verify → set done/release claim
3. D2: bounded rewrite เฉพาะส่วน stale ของ `README.md` (บรรทัด tagline-support, Overview, Project Status, Quick Start, Architecture, Credits) + รักษา Install/Docs/Data/Development sections
4. รัน deterministic checks + targeted tests ตาม Verify commands
5. freeze candidate SHA, push branch, เปิด PR, checkpoint บน Issue #784 และ #771 — ส่ง review/CI/merge ต่อให้ integrator

## Forbidden

- `AGENTS.md` — WO-P1-782 claim ยัง active ระหว่าง post-main closeout (D8 เลื่อนไป lane แยกหลัง claim release)
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, `PROJECT-GRAPH.yaml`, `CHANGELOG.md`, `src/`, `tests/`, `web/`, runtime/CI config, secrets, ปุ่ม version bump
- ข้าม repo (A-Wiki/SRM), แตะ branch ของ #749/#776/#222/#238/#754, แตะ dirty root ทั้ง Windows/macOS
- self-merge, self-approve, อ้าง #776/release ผิดจริง, สร้าง claim/WO store ซ้ำ

## Verify commands

- `py -3.13 -m pytest tests/test_work_order_identity.py -q` (ต้องผ่าน — WO นี้ต้องมี Issue line เดียวตรงกับ 784)
- `py -3.13 -m pytest tests/test_agent_context_economy_config.py -q`
- `git -C <worktree> diff --check` และ `git -C <worktree> status --short` (ต้องเห็นเฉพาะ 3 ไฟล์ใน allowlist)
- grep หาข้อความ merge ข้าม gate เดิมใน `docs/work-orders/README.md` ต้องไม่เจอ
- ตรวจ README relative links ทุกลิงก์ที่แก้/ที่อ้าง ต้อง resolve ใน tree นี้

## Checkpoint log (append-only — ทุกครั้งที่หยุด/ส่งต่อ)

- [2026-11-21] kilo-glm-5.3: bootstrap ที่ `origin/main@be162763` (post-#783 merge, post-main CI 44921208957 success แล้ว); gate: ไม่มี open PR/branch/claim อื่นแตะสอง path นี้; SAFE_TO_MUTATE=YES สำหรับ allowlist 3 ไฟล์; claim comment โพสต์บน Issue #784 ก่อนเริ่ม edit
