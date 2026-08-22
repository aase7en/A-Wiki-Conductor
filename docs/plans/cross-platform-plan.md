# Cross-Platform Plan — macOS / Linux / Raspberry Pi OS / Umbrel OS

Created: 2026-08-22 (user request; assessment + plan, not yet implemented)

## Feasibility verdict

| Platform | Verdict | Why |
|---|---|---|
| **macOS** (desktop) | ✅ ทำได้ (งานกลาง) | โปรแกรมหลักคือ Python stdlib ล้วน + Tk (รัน native ได้) — ต้อง abstract ส่วน Windows |
| **Linux** (desktop) | ✅ ทำได้ (งานกลาง) | เหมือน macOS (แชร์ abstraction เดียวกัน) |
| **Raspberry Pi OS** | ✅ ทำได้ (งานกลาง+) | Tk มีใน python3-tk; Serena รันบน ARM64 ได้; เช็ค tunnel-client linux-arm64 |
| **Umbrel OS** | ⚠️ ได้แต่คนละรูปแบบ | Umbrel ไม่มีจอ (headless Docker server) — แอป Tk รันไม่ได้ ต้องทำ headless daemon + **Web UI** เป็น milestone ใหญ่แยกทีหลัง |

## Hard dependency (GATE-0 — ตรวจก่อนเริ่มทุก phase)

**tunnel-client ต้องมี build สำหรับ linux-amd64 / linux-arm64 / macOS (darwin-amd64/arm64)**
- ปัจจุบันเครื่องนี้มีแค่ `tunnel-client.exe` (Windows)
- ตรวจจาก releases ของ OpenAI apps/tunnel ว่ามี binary อื่นไหม + วิธี auth ต่าง platform (ปัจจุบันใช้ DPAPI = Windows-only → ต้องหา keychain/ไฟล์ secret แทน)
- ถ้าไม่มี build ตรงไหน → platform นั้นเลื่อนจนกว่าจะมี

## Windows-isms ที่ต้อง abstract (Phase 1 — แกนกลาง)

| ส่วน | ปัจจุบัน (Windows) | เป้าหมายข้าม platform |
|---|---|---|
| Instance scripts | start/stop.ps1 + Start/Stop .cmd + PowerShell | เทมเพลตคู่ขนาน `.sh` (bash) + ตัวจัดการ per-OS ใน `LocalInstanceOrchestrator` |
| Process control | `CREATE_NO_WINDOW` + PowerShell Stop-Process | POSIX: `os.killpg`/SIGTERM + `start_new_session` |
| Instances root | `C:\AI\serena-instances` | platformdirs: `~/AI/serena-instances` (mac/linux/pi) + env override `A_CONDUCTOR_INSTANCES_ROOT` |
| Credentials | DPAPI (`api-key.dpapi`) | keychain (mac) / ไฟล์ 0600 (linux) — ตามที่ tunnel-client ต้องการ |
| Window titles | `title` ใน .cmd | ไม่มีหน้าต่างบน POSIX (no-op) — สถานะดูในแอป (MONITOR panel) |
| Paths | backslash/`ntpath` | `pathlib` ทั่วไป + ทดสอบ POSIX path |
| Installer | PyInstaller Setup.exe (HKCU) | macOS: `.app` bundle + DMG; Linux/Pi: AppImage หรือ `install.sh` + `.desktop` |
| CI | windows-latest | เพิ่ม matrix: `ubuntu-latest`, `macos-latest`, `arm64` (GH Actions มี mac-arm + ubuntu-arm) |

## Phases

- **P1 Platform abstraction** (~3-4 PRs): OS-detect module + POSIX process controller + `.sh` instance templates + per-OS paths + tests รันบนทั้ง windows/ubuntu/macos CI matrix (ตัว Windows ยังผ่านเหมือนเดิม)
- **P2 macOS + Linux desktop builds** (~2 PRs): PyInstaller onefile บนแต่ละ OS + packaging (.app/DMG, AppImage/install.sh) + docs
- **P3 Raspberry Pi** (~1-2 PRs): linux-arm64 build + python3-tk ตรวจ perf (Serena บน Pi ช้ากว่า — จำกัดจำนวน instance แนะนำ 2-3) + คู่มือ
- **P4 Umbrel / headless** (milestone แยก): daemon mode (ไม่มี Tk) + Web UI (เล็ก: status/start/stop/logs ผ่าน HTTP localhost) + umbrel-app manifest (Docker) — ต้องการ work order เฉพาะ

## สิ่งที่ไม่ต้องแก้ (พร้อมอยู่แล้ว)

- โค้ดหลักทั้งหมดเป็น Python **stdlib ล้วน** (ไม่มี dependency ภายนอก) — จุดแข็งสำคัญ
- Tk UI ข้าม platform; SQLite, i18n, registry/DB logic, tests ส่วนใหญ่ (CI matrix จะเผยจุดพังจริง)
- Serena engine เองรันได้ทุก platform (เป็น Python)

## ลำดับที่แนะนำ

1. วันนี้: ข้อ 2 (MONITOR) + ข้อ 3 (ปิดโปรแกรมแล้วหยุดทุก server) ก่อน — ใช้ได้ทันทีบน Windows และเป็นฐานให้ทุก platform (สถานะในแอป = ไม่ต้องพึ่งหน้าต่าง CMD)
2. GATE-0 ตรวจ tunnel-client builds
3. P1 → P2 → P3 ตามลำดับ; P4 (Umbrel) เปิด work order แยกเมื่อพร้อม
