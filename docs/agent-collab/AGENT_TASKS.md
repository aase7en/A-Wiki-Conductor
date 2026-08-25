# Agent Task Assignments

> งานปัจจุบันของแต่ละ agent — อัปเดตทุกครั้งที่มีการเปลี่ยนแปลง
> อ่าน COLLAB.md เพื่อดู claims แบบละเอียด

## ปัจจุบัน (2026-08-25)

### GPT-5.6 Sol (SunDay-Worker 1)
**สถานะ: 🟠 ติด Weekly limit (2026-08-25) — คิวรอกลับมา**

| Task | Branch | ไฟล์ | Status |
|---|---|---|---|
| WO-P1-063: UI Redesign (PR #79) | `fix/terminal-command-center-completion` | desktop_ui.py, system_metrics.py, gpu_particle_logo.py | ✅ Merged `acd77b4` |
| Build Pipeline v0.6.0 | — | build_*.py, installer_main.py, ci.yml | ✅ ตก main ผ่าน PR #79 (CI build+archive+frozen-smoke เขียว) |
| GPU-unbind tests salvage | `fix/gpu-context-ui-repaint` (`ffff853`, ยังไม่มี PR) | tests/test_gpu_particle_logo.py (+192 บรรทัด unique) | ⏳ รอ GPT: core fix ถูกแทนด้วย `12ce7ba` แล้ว เหลือแค่ tests — เปิด PR กู้ได้เลย |
| v0.6.0 GitHub Release publish | — | — | ⏳ รอ GPT (code ครบที่ main `f4ecf9a` แล้ว) |
| GE fan-in (WO-GE-001) | PR #83 `docs/ge-contracts-drafts` | docs/adr/GE-0001..0005 | ⏳ ตัดสิน D1-D5 → แล้ว GLM เริ่ม GE-1a |

### GLM 5.3 Max (ZCode session)
**สถานะ: 🟢 กำลังทำงาน**

| Task | Branch | ไฟล์ | Status |
|---|---|---|---|
| Agent Collaboration System | `docs/agent-collab-system` | docs/agent-collab/ (ทั้งหมด) | ✅ Done |
| WO-P1-065: Donate QR asset | `assets/donate-promptpay-qr` | assets/QR + DONATE.md | ✅ **Merged PR #80** (`f4ecf9a`) |
| WO-P1-066: Inline row buttons | `feat/inline-row-buttons` | desktop_ui.py, i18n.py, tests, WO + DESIGN.md | ✅ **Merged PR #81** (`d20cb70`) |
| WO-P1-067: Brain E2E + restart warning | `fix/brain-restart-note` | desktop_ui.py, test_desktop_ui.py, WO-067 | 🔄 PR #82 รอ CI |
| GE prep (fan-in input) | `docs/ge-contracts-drafts` | docs/adr/GE-*.md, WO-GE-001 | 🔄 PR #83 รอ GPT ตัดสิน D1-D5 |
| Docs/repo-health sync | `docs/repo-health-sync` | README/CHANGELOG/PRIVACY/NOTICES/INSTALL + SSoT | 🔄 PR นี้ |
| Branch hygiene | — | ลบ 37 branch ตาย (guardrail contained-in-main) | ✅ Done — เหลือ 4 branches |

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
