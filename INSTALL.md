# ติดตั้ง A-Sunday Conductor (Install Guide)

> เวอร์ชันล่าสุด: v0.4.3 · รองรับ: Windows 10/11 · ไม่ต้องมีสิทธิ์ admin

## วิธีที่ 1: Setup Installer (แนะนำสำหรับผู้ใช้ทั่วไป)

### ขั้นตอน

1. ไปที่ **[GitHub Releases](https://github.com/aase7en/A-Wiki-Conductor/releases)**
2. ดาวน์โหลด **`A-Sunday-Conductor-Setup.exe`**
3. ดับเบิลคลิกไฟล์ที่ดาวน์โหลด

### ถ้า Windows เตือน SmartScreen

> ⚠️ **"Windows protected your PC"**

คลิก **More info** → **Run anyway** (เป็นเรื่องปกติของแอปที่ยังไม่ได้เซ็นลายเซ็นดิจิทัล — กำลังอยู่ในระหว่างสมัคร code signing)

### หลังติดตั้งเสร็จ

- โปรแกรมจะอยู่ใน **Start Menu** ชื่อ **A-Sunday Conductor**
- มี shortcut บน **Desktop** ด้วย
- ถอนการติดตั้งผ่าน **Add or remove programs** ได้ปกติ

### ติดตั้งไว้ที่ไหน

```
%LOCALAPPDATA%\Programs\A-Sunday Conductor\
```

(ไม่แตะ system32 / registry ของเครื่อง ปลอดภัย 100%)

---

## วิธีที่ 2: Portable (ไม่ต้องติดตั้ง)

1. ดาวน์โหลด **`A-Sunday-Conductor-Portable.exe`**
2. รันได้เลยจากที่ไหนก็ได้ (ใส่ USB ก็ได้)

---

## วิธีที่ 3: สำหรับนักพัฒนา (pip)

```powershell
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .[test]
a-conductor          # เปิดโปรแกรม
```

ตรวจสอบ: `a-conductor --smoke` → `A-CONDUCTOR_SMOKE_OK`

---

## เริ่มใช้งานครั้งแรก (Quick Start)

### A. จัดการโปรเจกต์กับ Worker (ฝั่ง Control Center)

```
① กด [Add Project] → เลือกโฟลเดอร์โปรเจกต์
② คลิกโปรเจกต์ (ซ้าย) + คลิก Worker (ขวา) → กด [Assign]
③ กด [Start] — โปรเจกต์ที่มี Connector จะเริ่ม tunnel ให้อัตโนมัติ
```

### B. เชื่อมต่อกับ ChatGPT (สร้าง Connector ใหม่)

**ข้อกำหนดเบื้องต้น:**
- มีบัญชี OpenAI (API Key เดียวใช้ได้หลาย Tunnel)
- สร้าง Tunnel ใน [OpenAI Platform](https://platform.openai.com) → Settings → Tunnels

**ขั้นตอน:**
1. ในโปรแกรม กดปุ่ม **[+ Connector]** ในแถบ CONNECTORS
2. กรอก:
   - **ชื่อ** (ภาษาอังกฤษคำเดียว เช่น `research`)
   - **พาธโปรเจกต์** (เช่น `A:\GitHub\my-project`)
   - **Tunnel ID** (วางจาก OpenAI Platform — ขึ้นต้นด้วย `tunnel_`)
3. กด **[Create]** → ตัวเชื่อมใหม่จะปรากฏในตาราง
4. กด **[Start]** → รอสถานะเป็น **READY**
5. ไปที่ **ChatGPT** → สร้าง connector/plugin ใหม่ ชี้มาที่ tunnel นั้น

> ⚠️ สร้าง plugin ใน ChatGPT **หลังจาก** ตัวเชื่อม READY เท่านั้น ไม่งั้น ChatGPT จะสร้างไม่ได้

### C. สลับภาษา (Thai ↔ English)

1. กดปุ่ม **[Settings/ตั้งค่า]** มุมขวาบน
2. ติ๊ก/เลิกติ๊ก **ภาษา / Language**
3. ปิดและเปิดโปรแกรมใหม่

---

## ฟีเจอร์หลัก

| ปุ่ม | ทำอะไร |
|---|---|
| **+ Connector** | สร้างตัวเชื่อม ChatGPT ใหม่ (แชทขนานเพิ่ม) |
| **Rename** | เปลี่ยนชื่อที่แสดง (โฟลเดอร์จริงไม่ถูกแตะ) |
| **Delete** | ลบแบบปลอดภัย: หยุด → zip สำรอง → ลบ |
| **Set Tunnel ID** | ใส่/เปลี่ยน Tunnel ID ของตัวเชื่อม |
| **Change Project** | สลับโปรเจกต์ของตัวเชื่อม (ไม่ต้องสร้างใหม่) |
| **Start All** | เปิดทุกตัวเชื่อมที่ยังไม่ READY ในคลิกเดียว |
| **Toggle Auto** | ตั้งให้เปิดอัตโนมัติทุกครั้งที่เปิดโปรแกรม |
| **MONITOR panel** | ดูสถานะ/PID/หน่วยความจำ/log ของตัวเชื่อมที่เลือก |
| **+ Worker** | เพิ่มช่อง Worker ใหม่ (ไม่จำกัด 3 ตัว) |
| **Config** | ตั้งค่า engine ของ Worker (hover ดูคำอธิบายทุกช่อง) |

---

## ข้อมูลอยู่ที่ไหน

| อะไร | ที่ไหน |
|---|---|
| ฐานข้อมูลโปรแกรม | `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` |
| Tunnel IDs (ความลับ) | `L:\My Drive\A-Wiki-Data\secrets\a-conductor-tunnels.md` |
| สำรองตัวเชื่อม (zip) | `L:\My Drive\A-Wiki-Data\backups\a-conductor-instances\` |
| คู่มือฉบับเต็ม | กดปุ่ม **คู่มือ** ในโปรแกรม (ไทย/อังกฤษ) |

---

## แก้ปัญหาเบื้องต้น

| ปัญหา | วิธีแก้ |
|---|---|
| SmartScreen เตือน | More info → Run anyway |
| สร้าง plugin ใน ChatGPT ไม่ได้ | ตรวจว่าตัวเชื่อม READY ในแอปก่อน |
| ตัวเชื่อมไม่ขึ้นในตาราง | กด Rescan หรือรีสตาร์ทโปรแกรม |
| พอร์ตชนกัน | โปรแกรมจัดพอร์ตให้อัตโนมัติ — ถ้าเกิดจากโปรแกรมอื่น ปิดโปรแกรมนั้นก่อน |
| อยากให้แชทใช้ต่อแม้ปิดโปรแกรม | Settings → เลิกติ๊ก "ปิดโปรแกรมแล้วหยุดทุกตัวเชื่อม" |

---

## สำหรับนักพัฒนาที่ fork มาต่อ

```bash
# รันเทสต์ (ประมาณ 1000 ตัว)
python -m pytest tests/ -q

# build portable exe
python scripts/build_portable.py

# build setup installer
python scripts/build_installer.py

# sign ตอน release (ต้องมี SIGNPATH_API_TOKEN)
python scripts/sign.py dist/A-Sunday-Conductor-Setup.exe
```

CI: Windows + Ubuntu + macOS · ทุก PR ต้องเขียวครบทั้ง 3 OS

---

*สร้างโดยมนุษย์ + AI "A" ร่วมกัน · ใช้ [Serena](https://github.com/oraios/serena) (MIT) เป็น engine ภายใน*
