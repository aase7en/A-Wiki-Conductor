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
│                  │  ปุ่ม: Add Project / Assign / Release / Refresh
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

### 4.4 ปุ่มคู่มือ
มุมขวาบนมีปุ่ม **คู่มือ** — เปิดคู่มือฉบับนี้ได้ทันทีจากในโปรแกรม (ไม่มีคีย์ลัดที่ต้องจำ ทุกอย่างกดปุ่มได้เลย)

## 5. ฐานข้อมูล/ไฟล์ของโปรแกรมอยู่ไหน

- ค่าเริ่มต้น: `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`
- ระบุเองได้: `a-conductor --database D:\path\my.sqlite`

## 6. แจกจ่าย/ติดตั้งแบบไหนได้บ้าง (ทั้งหมดทำได้ — ไม่ต้องทำผ่านเว็บ)

| แบบ | เหมาะกับ | วิธี |
|---|---|---|
| **pip (นักพัฒนา)** | คนที่มี Python | `python -m pip install -e .[test]` แล้วใช้คำสั่ง `a-conductor` |
| **PyInstaller (portable exe)** | ผู้ใช้ทั่วไป ไม่ต้องมี Python | สร้างไฟล์ `.exe` วิ่งได้เดี่ยวๆ (ดืองเบาลงของ dev) |
| **Installer (setup .exe/.msi)** | เผยแพร่สาธารณะ | เอาผลจาก PyInstaller ไปทำ setup ด้วย Inno Setup / WiX (ขั้นถัดไป) |
| เว็บเวอร์ชัน | — | ไม่จำเป็นสำหรับโปรแกรมนี้ (เป็น local desktop app ตามดีไซน์) |

สร้าง exe เอง:

```powershell
python -m venv .build-venv
.build-venv\Scripts\pip install pyinstaller
.build-venv\Scripts\pyinstaller --noconfirm --windowed --onefile --name A-Conductor --paths src entry.py
# ได้ไฟล์ที่ dist\A-Conductor.exe
```

(ไฟล์ `entry.py` ตัวอย่างอยู่ใน repo — 2 บรรทัดเรียก main ของแอป)

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


## เครดิต (Credits)

A-Conductor ใช้ [Serena](https://github.com/oraios/serena) เป็น semantic code engine ภายใน (MIT License) — ขอบคุณทีมพัฒนา Serena สำหรับ engine อันยอดเยี่ยม
