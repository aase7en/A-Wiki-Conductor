# Agent Task Assignments

> งานปัจจุบันของแต่ละ agent — อัปเดตทุกครั้งที่มีการเปลี่ยนแปลง
> อ่าน COLLAB.md เพื่อดู claims แบบละเอียด

## ปัจจุบัน (2026-08-25)

### GPT-5.6 Sol (SunDay-Worker 1)
**สถานะ: 🟢 กำลังทำงาน**

| Task | Branch | ไฟล์ | Status |
|---|---|---|---|
| WO-P1-063: UI Redesign | `feat/terminal-command-center-redesign` | desktop_ui.py, system_metrics.py, gpu_particle_logo.py | 🔄 In progress |
| Build Pipeline v0.6.0 | (รอ claim ใน COLLAB.md) | build_portable.py, build_installer.py, installer_main.py, ci.yml | 🔄 Starting |

### GLM 5.3 Max (ZCode session)
**สถานะ: 🟢 กำลังทำงาน**

| Task | Branch | ไฟล์ | Status |
|---|---|---|---|
| Agent Collaboration System | `docs/agent-collab-system` | docs/agent-collab/ (ทั้งหมด) | ✅ Done |
| Documentation updates | — | README, CHANGELOG (ถ้าไม่ชน GPT) | ⏳ Pending |

## Backlog (ยังไม่มีคน claim)

| Task | Priority | เหมาะกับ | หมายเหตุ |
|---|---|---|---|
| Cross-platform packaging (B-3) | 🟡 Medium | GLM | macOS/Linux exe builds |
| RPi support (P3) | 🟢 Low | GLM | ARM64 builds |
| Umbrel headless (P4) | 🟢 Low | GLM | Web UI daemon |
| SignPath application | 🟡 Medium | **User** | ต้องสมัครด้วยตนเอง |
| Sponsor tiers setup | 🟡 Medium | **User** | ตั้งบน GitHub |
| PromptPay QR code | 🟡 Medium | **User** | ใส่รูปใน assets/ |
| Deep i18n (40+ Thai strings) | 🟢 Low | GLM | แปล remaining strings |
| MCP Gateway (per ADR-0001) | 🔴 Deferred | — | Reopen conditions ใน ADR |

## วิธี Claim งานใหม่

```
1. สร้าง work order: docs/work-orders/WO-P1-XXX-<name>.md
2. ระบุ scope (ไฟล์ที่จะแตะทั้งหมด)
3. เพิ่ม claim ใน COLLAB.md
4. สร้าง branch: chunk/<name> หรือ feat/<name>
5. ทำงาน + TDD + CI เขียว
6. PR + merge
7. Update AGENT_TASKS.md + CURRENT-WORK.md + handoff.md
```

## วิธี Release งาน

```
1. Mark WO as DONE + evidence
2. ลบ claim ออกจาก COLLAB.md (หรือ mark released)
3. Update AGENT_TASKS.md (ย้ายจาก active → done)
4. Commit + push
```

---

*Last updated: 2026-08-25 by GLM 5.3 Max*
