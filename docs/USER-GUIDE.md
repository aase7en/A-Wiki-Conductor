# คู่มือการใช้งาน A-Sunday Conductor (User Guide)

เวอร์ชันล่าสุด: 2026-08-26 (v0.7.0) · ระบบปฏิบัติการที่รองรับ: **Windows 10/11** (ฟีเจอร์เต็ม) · Python 3.11+ (ถ้าติดตั้งแบบนักพัฒนา)

---

## อภิธานศัพท์ (อ่านก่อนถ้าไม่เข้าใจคำศัพท์)

| คำศัพท์ | คืออะไร (ภาษาง่าย ๆ) |
|---|---|
| **Project** | โฟลเดอร์ที่เก็บโค้ด/ไฟล์งานของคุณในเครื่อง เช่น `A:\GitHub\my-app` — เปรียบเสมือน "ห้องทำงาน" ที่ AI จะเข้าไปทำงาน |
| **Connector** | "สะพาน" ที่เชื่อม ChatGPT เข้ากับโปรเจกต์ในเครื่องคุณ — แต่ละตัวมีชื่อ + พอร์ต + โปรเจกต์ที่ผูกไว้ตายตัว |
| **Tunnel ID** | รหัสผ่านของสะพาน (ขึ้นต้น `tunnel_` ตามด้วย 32 ตัวอักษร) — สร้างใน OpenAI Platform แล้วนำมาใส่ในโปรแกรม เพื่อให้ ChatGPT หาเครื่องคุณเจอ |
| **Worker** | ช่องที่จะรับงานในอนาคต (เหมือนเก้าอี้พนักงาน) — ตอนนี้ยังไม่ได้ใช้งานจริง รอระบบกราฟเสร็จ |
| **Serena** | โปรแกรมภายในที่เป็น "มือ" ให้ AI — ทำให้ AI อ่าน/แก้ไขไฟล์ในโปรเจกต์ได้ |
| **MCP** | มาตรฐานการสื่อสารที่ให้ AI เรียกใช้เครื่องมือต่าง ๆ (เช่น อ่านไฟล์ รันคำสั่ง) |
| **Plugin** | สิ่งที่คุณสร้างใน ChatGPT เพื่อเชื่อมกับ Tunnel — คุณตั้งชื่อเองได้ (เช่น Sunday-Worker-1) |
| **Port** | หมายเลขประตำ (เช่น 18011) ที่แต่ละ Connector ใช้สื่อสารภายในเครื่อง — แต่ละตัวไม่ซ้ำกัน |
| **Second Brain** | ความรู้/กฎ/ความจำที่ AI ต้องอ่านก่อนทำงาน — เช่น ไฟล์ AGENTS.md ของ A-Wiki |
| **Active Project** | โปรเจกต์ที่ AI กำลังทำงานด้วยอยู่ตอนนี้ — แต่ละ Connector ผูกกับ 1 โปรเจกต์เท่านั้น |
| **Instance** | อีกชื่อของ Connector (ใช้สลับกันได้) — หมายถึง "ตัวเชื่อม 1 ชุด" ในโฟลเดอร์ `C:\AI\serena-instances\` |

---

## ภาพรวม: ทุกอย่างเชื่อมกันยังไง

```
┌─────────────────── ChatGPT (ฝั่งอินเทอร์เน็ต) ───────────────────┐
│                                                                    │
│   แชท 1 [Plugin: Sunday-Worker-1]  ──── Tunnel ID: tunnel_abc123 │
│   แชท 2 [Plugin: Sunday-Worker-2]  ──── Tunnel ID: tunnel_def456 │
│   แชท 3 [Plugin: Sunday-Worker-3]  ──── Tunnel ID: tunnel_ghi789 │
│                                                                    │
└────────┬──────────────────┬──────────────────┬─────────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌─── A-Sunday Conductor (โปรแกรมในเครื่องคุณ) ─────────────────────┐
│                                                                    │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ Connector 1 │   │ Connector 2 │   │ Connector 3 │              │
│  │ :18011     │   │ :18012     │   │ :18013     │              │
│  │ tunnel_abc │   │ tunnel_def │   │ tunnel_ghi │              │
│  └──────┬─────┘   └──────┬─────┘   └──────┬─────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ Project A  │   │ Project B  │   │ Project C  │              │
│  │ A:\GitHub\ │   │ A:\GitHub\ │   │ A:\GitHub\ │              │
│  │ my-app     │   │ other-app  │   │ third-app  │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                    │
│  กฎสำคัญ: 1 Plugin = 1 Tunnel ID = 1 Connector = 1 Project       │
│  เปลี่ยนโปรเจกต์ = กดปุ่ม "Change Project" แล้ว Stop → Start      │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## เริ่มต้นใช้งานครั้งแรก (5 ขั้นตอน)

| ขั้น | ทำอะไร | กดปุ่มไหน |
|---|---|---|
| 1 | เปิดโปรแกรม → Setup Wizard จะเปิดอัตโนมัติ | (อัตโนมัติ) |
| 2 | ติดตั้งทุกอย่างตาม Wizard บอก (uv, Python, Serena, tunnel-client) | [Next] ตามขั้นตอน |
| 3 | สร้าง Tunnel ID ใน OpenAI Platform (Settings → Tunnels → New) | กดลิงก์จาก Wizard |
| 4 | ใส่ชื่อ Connector + เลือกโฟลเดอร์โปรเจกต์ + วาง Tunnel ID | Wizard ขั้นสุดท้าย |
| 5 | ไป ChatGPT → สร้าง Plugin ที่ชี้ไปที่ Tunnel ของคุณ | ในเบราว์เซอร์ |

## ใช้งานประจำวัน (3 ขั้นตอน)

| ขั้น | ทำอะไร | กดปุ่มไหน |
|---|---|---|
| 1 | เปิดโปรแกรม → ดูว่า Connector ไหน READY | (ดูตาราง CONNECTORS) |
| 2 | ไปที่ ChatGPT → เปิดแชทที่มี Plugin ของ Connector นั้น | ในเบราว์เซอร์ |
| 3 | คุยกับ AI ได้เลย — AI เห็นโปรเจกต์ผ่าน Connector อัตโนมัติ | (แชท) |

## เพิ่มแชทใหม่ (4 ขั้นตอน)

| ขั้น | ทำอะไร | กดปุ่มไหน |
|---|---|---|
| 1 | สร้าง Tunnel ID ใหม่ใน OpenAI Platform | ในเบราว์เซอร์ |
| 2 | กด `+ Add Connector` ในตาราง CONNECTORS (หรือกดแถว `+ Add` ถ้ายังว่าง) | ในโปรแกรม |
| 3 | ใส่ชื่อ + เลือกโปรเจกต์ + วาง Tunnel ID → Save | ใน dialog |
| 4 | ไป ChatGPT → สร้าง Plugin ใหม่ที่ชี้ไป Tunnel ID นั้น | ในเบราว์เซอร์ |

---

## 1. โปรแกรมอยู่ที่ไหน

โปรแกรมคือ repository นี้ (`A-Wiki-Conductor`) — เป็น **แอป desktop ล้วน** ไม่ต้องมีเว็บเซิร์ฟเวอร์ ไม่ต้องต่ออินเทอร์เน็ตเพื่อรัน UI (ออนไลน์แค่ตอน push/pull GitHub)

| รูปแบบ | วิธีเปิด |
|---|---|
| ติดตั้งแบบนักพัฒนา (แนะนำตอนนี้) | เปิด terminal ที่โฟลเดอร์ repo แล้วพิมพ์ `a-conductor` |
| แบบไฟล์เดียว (portable) | รันไฟล์ `A-Sunday Conductor.exe` ที่ build ด้วย PyInstaller (ดูหัวข้อ 6) |

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
┌ A-SUNDAY CONDUCTOR                         [คู่มือ]     ● ONLINE ┐
├ PROJECTS (ซ้าย)  │  WORKERS (ขวา) — ตาราง WORKER/STATE/PROJECT/PATH
│                  │  ปุ่ม: Add Project / Assign / Activate / Release / Refresh
│                  │        Start / Stop / Restart / Setup / Config / + Worker / Rename / Delete
├ CONNECTORS — INSTANCE / PORT / STATE / PROJECT / TUNNEL / AUTO
│  ปุ่ม: Start / Stop / Start All / Toggle Auto / Rescan / + ตัวเชื่อม / แก้ชื่อ / ลบ
│        ตั้ง Tunnel ID / เปลี่ยนโปรเจกต์ / สมอง + folder / เช็คอัปเดท
├ MONITOR — สถานะ/PID/หน่วยความจำ/บรรทัดท้าย log ของตัวเชื่อมที่เลือก (รีเฟรชอัตโนมัติ)
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
- **+ ตัวเชื่อม**: สร้างตัวเชื่อมใหม่จากแม่แบบที่ผ่านการตรวจสอบ (ตั้งชื่อ + พาธโปรเจกต์ + Tunnel ID ถ้ามี — พอร์ตจัดให้อัตโนมัติ หน้าต่าง CMD ตั้งชื่อ Sunday-works ถัดไปให้เลย)
- **แก้ชื่อ / ลบ**: เปลี่ยนชื่อที่แสดง (โฟลเดอร์จริงไม่ถูกแตะ) / ลบแบบปลอดภัย (หยุดให้ก่อน → สำรอง zip → ค่อยลบ)
- ชี้เมาส์ค้างที่แถวตาราง = ดู path เต็มในกล่องลอย · คลิกขวาที่แถว = **คัดลอก path** · เลื่อนตารางแนวนอนได้เมื่อ path ยาว
- ชื่อมาตรฐานของระบบ: `Sunday-Worker-N` พอร์ต `1801N` (ตัวอย่าง: worker 3 = พอร์ต 18013) — ชื่อ**ไม่ได้ล็อกกับโปรเจกต์** สลับโปรเจกต์ได้ตลอดด้วยปุ่ม **เปลี่ยนโปรเจกต์**

> ถ้าแถบนี้ว่างเปล่า = เครื่องยังไม่มี instance ตามโครงสร้าง `C:\AI\serena-instances\` — ดูหัวข้อ 7

### 4.3.1 1 API Key ใช้หลาย Tunnel ได้ (ทำงานหลายแชทขนานกัน)

**ได้ — บัญชี OpenAI/API Key เดียวสร้าง Tunnel ได้หลายตัว** แต่ละ Tunnel = ตัวเชื่อม 1 ตัว = แชท ChatGPT ทำงานขนานได้ 1 ห้อง (เครื่องนี้ใช้อยู่ 5 ตัว: SunDay-Worker 1-5)

ขั้นตอนเพิ่มแชทใหม่:
1. สร้าง Tunnel ใหม่ใน **OpenAI Platform (เว็บ)** — ตั้งชื่อให้ตรงกับชื่อ plugin ที่จะสร้าง
2. ในโปรแกรมกด **+ ตัวเชื่อม** → กรอกชื่อ + พาธโปรเจกต์ + วาง Tunnel ID → สร้าง
3. กด **Start** ให้สถานะเป็น READY (ถ้ายังไม่มี Tunnel ID กดปุ่ม Tunnel ID ใส่ภายหลังได้)
4. ไปที่ ChatGPT → สร้าง connector/plugin ใหม่ชี้มาที่ tunnel นั้น (ต้องทำตอนตัวเชื่อม READY อยู่เท่านั้น ไม่งั้น ChatGPT จะสร้างไม่ได้)

### 4.3.2 1 ห้องแชท ใช้หลาย Worker ได้

**ได้ — ในแชทเดียวเปิดหลาย connector พร้อมกันได้** (ใน ChatGPT: เปิดหลาย apps/tools ในห้องแชทเดียวกัน) แต่ละตัวชี้มาที่ Sunday-Worker คนละตัว → หนึ่งแชทสั่งงานหลายโปรเจกต์ได้ เช่น ให้ worker อ่านโค้ด repo หลัก ขณะที่อีกตัวค้นข้อมูลในโปรเจกต์งานเอกสาร

ข้อควรระวัง:
- หลาย connector พร้อมกัน = ใช้ token สูงขึ้นและ context อาจปนกัน — เหมาะกับงานที่ต้องข้อมูลจาก 2 โปรเจกต์จริงๆ
- งานปกติแนะนำ **1 แชท = 1 worker หลัก** แล้วเปิดเพิ่มเมื่อจำเป็น (ปิด-เปิด connector ในแชทได้ทุกเมื่อ)
- แชทแยกหลายห้อง (ห้องละ worker) จะคุมเนื้อหาชัดกว่า — ใช้วิธีไหนก็ได้ตามสไตล์งาน

### 4.4 Activate โปรเจกต์ใน AI chat
1. คลิกเลือกโปรเจกต์ในกล่อง **PROJECTS**
2. กด **Activate** → โปรแกรมจะคัดลอก prompt มาตรฐานของ Serena พร้อม path ของโปรเจกต์นั้น
3. ไปที่ AI chat ที่เชื่อม Serena แล้ววางข้อความที่คัดลอก เช่นบรรทัดแรกจะเป็น `Activate the current dir as project using serena`

> ปุ่มนี้ช่วยคัดลอกข้อความเท่านั้น — A-Sunday Conductor ไม่ activate Serena แทน agent และไม่แก้ไฟล์ในโปรเจกต์

### 4.5 ปุ่มคู่มือ + สลับภาษา
มุมขวาบนมีปุ่ม **คู่มือ** — เปิดคู่มือฉบับนี้ได้ทันทีจากในโปรแกรม (ไม่มีคีย์ลัดที่ต้องจำ ทุกอย่างกดปุ่มได้เลย) และปุ่ม **ตั้งค่า** มีสวิตช์ **ภาษา / Language** สำหรับเลือก ไทย / 中文 / English (3 ภาษา — คำอธิบายเปลี่ยนทันทีไม่ต้องปิด-เปิดใหม่ ส่วนป้ายปุ่มคงเป็นภาษาอังกฤษตามมาตรฐาน) ชื่อหน้าต่างโปรแกรมแสดงเลขเวอร์ชันเสมอ เช่น `A-Sunday Conductor v0.7.0` เพื่อยืนยันว่าเปิดตัวล่าสุด สวิตช์ **ปิดโปรแกรมแล้วหยุดทุกตัวเชื่อม** (เปิดไว้เป็นค่าเริ่มต้น) จะสั่งหยุดตัวเชื่อมทุกตัวและเก็บกวาด process ค้างให้ตอนปิดหน้าต่าง — เครื่องเคลียร์เสมอ

### 4.6 จับมือทำ: แชท ChatGPT ตัวไหนคือ Connector/พอร์ต/โปรเจกต์ตัวไหน?

**ความจริงสำคัญ:** ชื่อปลั๊กอินที่คุณตั้งใน ChatGPT (เช่น `Sunday-Worker-1..5`) เป็นชื่อฝั่ง OpenAI เท่านั้น — โปรแกรมนี้**ไม่เห็นและไม่ผูกอะไรกับชื่อนั้นเลย** ตัวชี้ขาดที่เชื่อมแชทเข้ากับเครื่องคุณคือ **Tunnel ID** ของปลั่กอินนั้น

ห่วงโซ่ที่เชื่อมกันจริง:

```
แชทใน ChatGPT → ปลั๊กอินถือ Tunnel ID → ในเครื่อง: connector ที่มี tunnel-id.txt ตรงกัน
→ connector นั้น pin "โปรเจกต์ 1 ตัว" (คอลัมน์ PROJECT ในตาราง CONNECTORS) + มีพอร์ตของตัวเอง (คอลัมน์ PORT)
```

กฎที่ต้องจำ: **1 ปลั๊กอิน = 1 connector = 1 โปรเจกต์ตายตัว** ตลอดอายุแชท เปลี่ยนโปรเจกต์ต้องใช้ปุ่ม **Change Project** ที่ connector ตัวนั้น แล้ว **Stop → Start ใหม่** จึงมีผล (แชทที่ค้างอยู่จะไม่เห็นโปรเจกต์เปลี่ยนแบบสด ๆ)

ไล่ทีละ step ว่า "แชทนี้คือแถวไหน":

1. ใน ChatGPT เปิดการตั้งค่าปลั๊กอิน/connector แล้วดู **Tunnel ID** ของเจ้านั้น
2. ในโปรแกรม ดูคอลัมน์ **TUNNEL** ของตาราง CONNECTORS — แต่ละแถวโชว์ **4 ตัวท้ายของ Tunnel ID** (เช่น `...e3f1`) ให้เทียบกับ 4 ตัวท้ายของ ID ที่เห็นใน ChatGPT ได้ทันที (โปรแกรมไม่แสดง ID เต็ม เพราะถือเป็นข้อมูลลับ) · กด **Edit** ในแถวจะเห็น "ปัจจุบัน: ...xxxx" และแก้ ID ได้จากที่นี่
3. เมื่อเจอตัวที่ตรง: อ่านคอลัมน์ **PROJECT** และ **PORT** ของแถวนั้น = แชทนี้กำลังทำงานกับโปรเจกต์นั้น ผ่านพอร์ตนั้น
4. ในตาราง WORKERS คอลัมน์ **CONNECTOR (?)**: worker ใดที่ถูก assign โปรเจกต์เดียวกับ connector ตัวนั้น (path ตรงกันเป๊ะ) จะโชว์ชื่อ connector; ขีด `-` = ยังไม่มี connector ไหนผูกกับโปรเจกต์ของ worker นั้น (ไม่ใช่ error) — **คอลัมน์นี้เป็นแค่การแสดงผลที่คำนวณอัตโนมัติ ไม่ใช่การลงทะเบียน และไม่มีปุ่มตั้งค่า** ไม่ต้องตั้งค่าอะไรที่นี่

   > 💡 อีกนัยหนึ่ง: ตาราง CONNECTORS คือ "ความจริง" ของอุโมงค์ (พอร์ต+โปรเจกต์+สถานะ รีเฟรชสดทุก 15 วินาที) ส่วนตาราง WORKERS เป็นมุมมองการจัดคิวงาน — สองอย่างนี้เชื่อมกันผ่าน path ของโปรเจกต์เท่านั้น
5. อยากให้ "แชทตัวที่ 2" ไปทำงานกับโปรเจกต์ B: เลือก connector ของแชทที่ 2 → **Change Project** → ใส่ path โปรเจกต์ B → **Stop** → **Start** → เช็คว่าคอลัมน์ PROJECT เปลี่ยนแล้ว = เสร็จ

## 5. ฐานข้อมูล/ไฟล์ของโปรแกรมอยู่ไหน

- ค่าเริ่มต้น: `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` (โฟลเดอร์ข้อมูลคงชื่อเดิมจากก่อนเปลี่ยนชื่อโปรแกรม เพื่อให้อัปเกรดแล้วข้อมูลเดิมใช้ต่อได้)
- ระบุเองได้: `a-conductor --database D:\path\my.sqlite`

## 6. แจกจ่าย/ติดตั้งแบบไหนได้บ้าง (ทั้งหมดทำได้ — ไม่ต้องทำผ่านเว็บ)

| แบบ | เหมาะกับ | วิธี |
|---|---|---|
| **pip (นักพัฒนา)** | คนที่มี Python | `python -m pip install -e .[test]` แล้วใช้คำสั่ง `a-conductor` |
| **PyInstaller (portable exe)** | ผู้ใช้ทั่วไป ไม่ต้องมี Python | สร้างไฟล์ `.exe` วิ่งได้เดี่ยวๆ — build ด้วย `python scripts/build_portable.py` |
| **Setup installer (A-Sunday-Conductor-Setup.exe)** | เผยแพร่สาธารณะ | ติดตั้งแบบผู้ใช้เดียว (ไม่ต้อง admin): ไปที่ `%LOCALAPPDATA%\Programs\A-Sunday Conductor` + Start Menu + Desktop + ลงทะเบียนถอนการติดตั้งใน "Add or remove programs" |
| เว็บเวอร์ชัน | — | ไม่จำเป็นสำหรับโปรแกรมนี้ (เป็น local desktop app ตามดีไซน์) |

สร้าง exe เอง:

```powershell
python -m venv .build-venv
.build-venv\Scripts\pip install pyinstaller
.build-venv\Scripts\pyinstaller --noconfirm --windowed --onefile --name "A-Sunday Conductor" --paths src entry.py
# ได้ไฟล์ที่ dist\A-Sunday Conductor.exe
```

สร้างตัวติดตั้ง (Setup) เอง — 2 คำสั่งเรียงกัน:

```powershell
python scripts/build_portable.py     # ได้ dist\A-Sunday Conductor.exe
python scripts/build_installer.py    # ได้ dist\A-Sunday-Conductor-Setup.exe (ฝังคู่มือ + ประกาศเครดิต Serena อัตโนมัติ)
```

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

A-Sunday Conductor ใช้ [Serena](https://github.com/oraios/serena) เป็น semantic code engine ภายใน (MIT License) — ขอบคุณทีมพัฒนา Serena สำหรับ engine อันยอดเยี่ยม
