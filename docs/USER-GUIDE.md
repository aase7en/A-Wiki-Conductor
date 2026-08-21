# คู่มือการใช้งาน A-Conductor (User Guide)

เวอร์ชันล่าสุด: 2026-08-21 · ระบบปฏิบัติการที่รองรับ: **Windows 10/11** (ฟีเจอร์เต็ม) · Python 3.11+ (ถ้าติดตั้งแบบนักพัฒนา)

---

## 1. โปรแกรมอยู่ที่ไหน

โปรแกรมคือ repository นี้ (`A-Wiki-Conductor`) — เป็น **แอป desktop ล้วน** ไม่ต้องมีเว็บเซิร์ฟเวอร์ ไม่ต้องต่ออินเทอร์เน็ตเพื่อรัน UI (ออนไลน์แค่ตอน push/pull GitHub)

| รูปแบบ | วิธีเปิด |
|---|---|
| ติดตั้งแบบนักพัฒนา (แนะนำตอนนี้) | เปิด terminal ที่โฟลเดอร์ repo แล้วพิมพ์ `a-conductor` |
| แบบไฟล์เดียว (portable) | รันไฟล์ `A-Conductor.exe` ที่ build ด้วย PyInstaller (ดูหัวข้อ 6) |

## 2. ติดตั้งครั้งแรก (สำหรับคนที่ fork/clone มา)

```powershell
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .[test]
a-conductor          # เปิดโปรแกรม
```

ตรวจสอบว่าใช้ได้: `a-conductor --smoke` → ต้องขึ้น `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`

## 3. หน้าจอหลักมีอะไร

```
┌ A-CONDUCTOR                                [คู่มือ]     ● ONLINE ┐
├ PROJECTS (ซ้าย)  │  WORKERS (ขวา) — ตาราง WORKER/STATE/PROJECT/PATH
│                  │  ปุ่ม: Add Project / Assign / Activate / Release / Refresh
│                  │        Start / Stop / Restart / Setup / Config
├ CONNECTORS — INSTANCE / PORT / STATE / PROJECT / AUTO
│  ปุ่ม: Start / Stop / Start All / Toggle Auto / Rescan
└ ACTIVITY / LOG — บันทึกเหตุการณ์ทุกคำสั่ง
```

**สีของสถานะ**: เขียว = READY · เหลือง = STARTING/BUSY/STOPPING · แดง = ERROR · เทา = STOPPED/ว่าง

## 4. งานประจำวันทำอะไรได้บ้าง

### 4.1 จัดการโปรเจ็คกับ worker (ฝั่ง Control Center)
1. **Add Project** → เลือกโฟลเดอร์โปรเจ็ค (การลงทะเบียน*ไม่แตะ*ไฟล์ในโปรเจ็คนั้น)
2. คลิกโปรเจ็คซ้าย + คลิก worker ขวา → **Assign**
3. **Start/Stop/Restart** ควบคุม lifecycle ของ worker

### 4.2 ตั้งค่า engine อ่านโค้ดของแต่ละ worker (ปุ่ม Config)
เลือก worker → **Config** → แก้ได้:
- **Language backend**: LSP หรือ JetBrains
- **Tool timeout**: เวลาเบติด tool (วินาที)
- **Excluded / Included optional / Fixed tools**: เปิด-ปิด tool ตามชุด (อย่างน้อยหนึ่งช่อง — Fixed ใช้เดี่ยวๆ เท่านั้น ห้ามรวมกับช่องอื่น)
- **Base modes**: เช่น interactive, editing
- ค่าที่เซฟจะ*มีผลตอน worker start ครั้งถัดไป* (โปรแกรมจะเตือนไว้ในหน้าจอ)

### 4.3 จัดการตัวเชื่อม ChatGPT (แถบ CONNECTORS)
- โปรแกรม**ค้นหาอัตโนมัติ**จาก `C:\AI\serena-instances\*` (อ่านไฟล์ `instance.ps1` ของแต่ละตัว)
- **Start / Stop**: สั่งผ่านสคริปต์มาตรฐานของ instance นั้น (ปลอดภัย — ตรวจ PID/tunnel ตามที่ validated ไว้)
- **Start All**: เปิดทุกตัวที่ยังไม่ READY ในคลิกเดียว
- **Toggle Auto**: ตั้งให้ instance เปิดเองทุกครั้งที่เปิดโปรแกรม
- **Rescan**: ค้นหา instance ใหม่ (เช่น เพิ่งสร้าง instance ใหม่)

> ถ้าแถบนี้ว่างเปล่า = เครื่องยังไม่มี instance ตามโครงสร้าง `C:\AI\serena-instances\` — ดูหัวข้อ 7

### 4.4 Activate โปรเจกต์ใน AI chat
1. คลิกเลือกโปรเจกต์ในกล่อง **PROJECTS**
2. กด **Activate** → โปรแกรมจะคัดลอก prompt มาตรฐานของ Serena พร้อม path ของโปรเจกต์นั้น
3. ไปที่ AI chat ที่เชื่อม Serena แล้ววางข้อความที่คัดลอก เช่นบรรทัดแรกจะเป็น `Activate the current dir as project using serena`

> ปุ่มนี้ช่วยคัดลอกข้อความเท่านั้น — A-Conductor ไม่ activate Serena แทน agent และไม่แก้ไฟล์ในโปรเจกต์

### 4.5 ปุ่มคู่มือ
มุมขวาบนมีปุ่ม **คู่มือ** — เปิดคู่มือฉบับนี้ได้ทันทีจากในโปรแกรม (ไม่มีคีย์ลัดที่ต้องจำ ทุกอย่างกดปุ่มได้เลย)

## 5. ฐานข้อมูล/ไฟล์ของโปรแกรมอยู่ไหน

- ค่าเริ่มต้น: `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`
- ระบุเองได้: `a-conductor --database D:\path\my.sqlite`

## 6. แจกจ่าย/ติดตั้งแบบไหนได้บ้าง (ทั้งหมดทำได้ — ไม่ต้องทำผ่านเว็บ)

| แบบ | เหมาะกับ | วิธี |
|---|---|---|
| **pip (นักพัฒนา)** | คนที่มี Python | `python -m pip install -e .[test]` แล้วใช้คำสั่ง `a-conductor` |
| **PyInstaller (portable exe)** | ผู้ใช้ทั่วไป ไม่ต้องมี Python | สร้างไฟล์ `.exe` วิ่งได้เดี่ยวๆ — build ด้วย `python scripts/build_portable.py` |
| **Setup installer (A-Conductor-Setup.exe)** | เผยแพร่สาธารณะ | ติดตั้งแบบผู้ใช้เดียว (ไม่ต้อง admin): ไปที่ `%LOCALAPPDATA%\Programs\A-Conductor` + Start Menu + Desktop + ลงทะเบียนถอนการติดตั้งใน "Add or remove programs" |
| เว็บเวอร์ชัน | — | ไม่จำเป็นสำหรับโปรแกรมนี้ (เป็น local desktop app ตามดีไซน์) |

สร้าง exe เอง:

```powershell
python -m venv .build-venv
.build-venv\Scripts\pip install pyinstaller
.build-venv\Scripts\pyinstaller --noconfirm --windowed --onefile --name A-Conductor --paths src entry.py
# ได้ไฟล์ที่ dist\A-Conductor.exe
```

คำสั่งสร้าง installer: `python scripts/build_portable.py` สำหรับ exe หลัก แล้วสร้าง setup ด้วย `scripts/installer_main.py` (คู่มือนี้ถูกฝังใน setup.exe อัตโนมัติ)

> หมายเหตุ SmartScreen: setup.exe ยังไม่ได้เซ็นลายเซ็นดิจิทัล ครั้งแรกที่เปิด Windows อาจเตือน — กด **More info → Run anyway** ได้ (ปกติของแอปที่ยังไม่ sign) การถอนการติดตั้ง: ใช้ Add or remove programs หรือไฟล์ Uninstall ในโฟลเดอร์ที่ติดตั้ง

## 7. ของอะไรที่มากับเครื่องผู้ใช้เอง (ต้องเตรียมเอง)

แถบ CONNECTORS ทำงานกับ "ตัวเชื่อม (connector instance) ที่สร้างตามแบบแผน" เท่านั้น:
- โฟลเดอร์ instance ตามรูปแบบ `C:\AI\serena-instances\<ชื่อ>\` ที่มี `instance.ps1`, `Start-*.cmd`, `Stop-*.cmd`
- tunnel/connector ของ OpenAI (การสร้าง tunnel ใหม่ต้องทำใน OpenAI Platform — เป็นบัญชีส่วนตัวของผู้ใช้แต่ละคน)

ผู้ใช้ใหม่ที่ยังไม่มีส่วนนี้ ยังใช้ได้ครบส่วน: Projects/Workers registry, Config dialog, durable job control — แถบ CONNECTORS จะว่างจนกว่าจะมีตัวเชื่อม

## 8. แก้ปัญหาเบื้องต้น

| อาการ | ทางแก้ |
|---|---|
| เปิดแล้วขึ้น `A-CONDUCTOR_START_FAILED ...` | ดูว่า path `--database` เขียนได้ไหม |
| กด Start instance แล้วเป็น `STARTED_NOT_READY` | ดู log ของ instance นั้นที่ `C:\AI\serena-instances\<ชื่อ>\logs\` |
| กด Start เจอ `PORT_IN_USE` | มีอะไรแชร์ port อยู่ — หา PID เจ้าของ port ก่อนเสมอ อย่า kill มั่ว |
| แถบ CONNECTORS ว่าง | ยังไม่มี instance ตามโครงสร้างมาตรฐาน (หัวข้อ 7) หรือกด Rescan |

## 9. สำหรับผู้พัฒนาที่ fork มาต่อ

- รันเทส: `python -m pytest tests/ -q` (ครบทุกครั้งก่อน PR — CI บน GitHub ตรวจให้อัตโนมัติ)
- อ่าน `AGENTS.md` → `PROJECT-PLAN.md` → `COLLAB.md` → `CURRENT-WORK.md` → `handoff.md` ตามลำดับก่อนเริ่มงาน
- ทุกงานทำเป็น work order ใน `docs/work-orders/` + PR แยกตาม chunk


## เชื่อมต่อ AI แต่ละค่าย (สำหรับผู้ใช้ใหม่)

ก่อนเชื่อม ให้เปิดโปรแกรม → แถบ CONNECTORS → เลือกตัวเชื่อม → กด **ตั้ง Tunnel ID** แล้ววาง ID ที่ได้จากขั้นตอนของค่ายนั้นๆ

### ChatGPT / OpenAI (ระบบ tunnel)
1. เข้า OpenAI Platform → เมนู Tunnels → สร้าง tunnel ใหม่ (ตั้งชื่ออะไรก็ได้)
2. คัดลอก **Tunnel ID** (`tunnel_` ตามด้วย 32 ตัวอักษร) มาวางในโปรแกรม
3. วิธีเดิมแบบเปิดเผย (MCPO + Cloudflare): รัน `uvx mcpo --port 8000 --api-key <KEY> -- serena start-mcp-server --context chatgpt` แล้ว `cloudflared tunnel --url http://localhost:8000` → ใส่ URL ใน Custom GPT แบบ Bearer — อ่านละเอียด: https://oraios.github.io/serena/02-usage/030_chatgpt_connection.html (ปรับตามหน้าเอกสารจริง https://oraios.github.io/serena/ )

### Claude (Claude Code / Claude Desktop)
- คำสั่งเดียวจบ: `serena setup claude-code`
- หรือเพิ่มเอง: `claude mcp add --scope user serena -- serena start-mcp-server --context claude-code --project-from-cwd`
- Claude Desktop (แบบ global): ต้องใช้ tool `activate_project` — พิมพ์กับ agent ว่า "Activate the current dir as project using serena"
- เอกสาร: https://oraios.github.io/serena/02-usage/010_connecting_an_mcp_client.html

### Codex
- `~/.codex/config.toml` เพิ่ม entry พร้อม `startup_timeout_sec = 15` หรือรัน `serena setup codex`

### Grok / อื่นๆ
- `serena setup grok` · context ของแต่ละแอปฝังมากับ engine แล้ว (`--context grok`, `--context ide`, ...)

### Antigravity
- ใช้ได้ผ่าน MCP ปกติ (ใน dashboard จะแสดงเป็น client `none`)

> ความปลอดภัย: การเปิด tunnel = เปิด shell/ไฟล์สู่ภายนอก — พิจารณาปิด `execute_shell_command` หรือตั้ง `read_only: true` ใน Config ของ worker ถ้าไม่จำเป็น

## เครดิต (Credits)

A-Conductor ใช้ [Serena](https://github.com/oraios/serena) เป็น semantic code engine ภายใน (MIT License) — ขอบคุณทีมพัฒนา Serena สำหรับ engine อันยอดเยี่ยม
