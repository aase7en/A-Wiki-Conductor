# Agent Collaboration Protocol — GPT + GLM

> วิธีทำงานร่วมกันบนโปรเจกต์เดียวกันแบบคู่ขนาน โดยไม่ชนกัน

## 1. กติกาหลัก (อ่านก่อนเริ่มทุกครั้ง)

### Entry Sequence (บังคับ)
```
1. COLLAB.md — เช็ค claims/lanes ปัจจุบัน
2. CURRENT-WORK.md — สถานะล่าสุด + WO ที่ active
3. handoff.md — resume state
4. DEFECT_LESSONS.md — บทเรียนจากบั๊กเก่า (ก่อนแตะ src/)
5. docs/agent-collab/AGENT_TASKS.md — งานของตัวเอง
```

### Claim ก่อนแก้ (บังคับ)
- ทุกไฟล์ที่จะแก้ **ต้องไม่อยู่ใน claim ของอีกฝ่าย** (ดู COLLAB.md)
- ถ้าต้องการไฟล์ที่อีกฝ่าย claim:
  1. จดใน work order ของตัวเองว่าต้องการอะไร
  2. รออีกฝ่าย release หรือ
  3. ถาม user ให้ตัดสินใจ
- **ห้ามแก้ไฟล์ที่อีกฝ่าย claim โดยไม่ได้รับอนุญาต**

### Evidence หลังเสร็จ (บังคับ)
- Commit SHA + ผล test + CI status
- Update CURRENT-WORK.md + handoff.md
- Release claim ใน COLLAB.md

## 2. การแบ่งเขตปัจจุบัน (2026-08-25)

### GPT-5.6 Sol (SunDay-Worker 1)
**WO-P1-063 (UI Redesign)** + **Build Pipeline (v0.6.0)**

| ไฟล์ | งาน |
|---|---|
| `src/a_conductor/desktop_ui.py` | Terminal command center redesign |
| `src/a_conductor/gpu_particle_logo.py` | GPU particle logo |
| `src/a_conductor/system_metrics.py` | System metrics |
| `src/a_conductor/i18n.py` | i18n updates |
| `scripts/build_portable.py` | Retry loop + clean build |
| `scripts/build_installer.py` | Version stamp |
| `scripts/installer_main.py` | DisplayVersion + non-silent failures |
| `tests/test_build_installer.py` | TDD for retry + version |
| `.github/workflows/ci.yml` | Build+archive verification |
| `INSTALL.md` | Version update + naming fix |
| `assets/` | Logo + images |
| `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `AGENTS.md` | Hotspot files |

### GLM 5.3 Max (ZCode session)
**Collaboration System** + **Backend** + **Docs**

| ไฟล์ | งาน |
|---|---|
| `docs/agent-collab/` (ทั้งหมด) | สร้าง collaboration infrastructure |
| `src/a_conductor/control_center.py` | Backend logic |
| `src/a_conductor/registry.py` | Registry |
| `src/a_conductor/local_instances.py` | Instance discovery |
| `src/a_conductor/platform_support.py` | Cross-platform |
| `src/a_conductor/instance_*.py` | Instance CRUD |
| `src/a_conductor/setup_wizard.py` | Setup wizard engine |
| `tests/` (ยกเว้น test_build_installer) | Tests |

### ไม่มีใคร claim (เป็นส่วนกลาง)
- `PROJECT-PLAN.md` (อ่านอย่างเดียว — แก้ต้องปรึกษากัน)
- `DEFECT_LESSONS.md` (เพิ่มได้ — ไม่ต้อง claim)
- `CHANGELOG.md` (เพิ่มได้ — ไม่ต้อง claim)
- `README.md` (แก้ได้ถ้าไม่กระทบ GPT)

## 3. Communication Protocol

### ผ่าน Git (primary)
```
Agent แต่ละตัวทำงานบน branch ของตัวเอง
→ commit พร้อมข้อความชัดเจน
→ PR เมื่อพร้อม merge
→ merge เฉพาะเมื่อ CI เขียว
```

### ผ่าน Work Orders
```
สร้าง docs/work-orders/WO-P1-XXX.md
→ ระบุ scope (ไฟล์ที่จะแตะ)
→ checkpoint ทุกขั้นตอน
→ mark DONE เมื่อเสร็จ + evidence
```

### ผ่าน SSoT Files
```
CURRENT-WORK.md — สถานะรวม
handoff.md — resume state
DEFECT_LESSONS.md — บทเรียนใหม่
COLLAB.md — claims ปัจจุบัน
```

## 4. Conflict Resolution

| สถานการณ์ | วิธีแก้ |
|---|---|
| ต้องการไฟล์ที่อีกฝ่าย claim | จดใน WO + รอ release หรือถาม user |
| ทั้งคู่ต้องการไฟล์เดียวกัน | User ตัดสินใจ |
| Merge conflict | ฝ่ายที่ claim ไว้ก่อนมีสิทธิ์ก่อน |
| Hotspot file (SSoT) | ใช้ PR + review โดยเสมอ |

## 5. Best Practices

- อ่าน `git log --oneline -5` ก่อน push เพื่อเช็คว่าอีกฝ่าย push อะไรไปแล้ว
- ใช้ `git fetch origin` ก่อนเริ่มงานทุกครั้ง
- Commit เล็กๆ บ่อยๆ (ไม่รวมหลาย feature ใน commit เดียว)
- PR description ระบุไฟล์ที่แตะทั้งหมด
- ถ้าไม่แน่ใจ → ถาม user ก่อน

---

*Last updated: 2026-08-25 by GLM 5.3 Max*
