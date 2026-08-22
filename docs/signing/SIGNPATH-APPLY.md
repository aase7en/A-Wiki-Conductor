# สมัคร SignPath Foundation (code signing ฟรีสำหรับ OSS) — คู่มือสำหรับคุณ

ทำไม: exe ที่ไม่เซ็นทำให้ SmartScreen เตือน "Windows protected your PC" ตอนคนอื่นดาวน์โหลดไปเปิด
ทางที่ถูกที่สุดสำหรับ repo สาธารณะ (2026): **SignPath Foundation** — ฟรี สำหรับ open source โดยเฉพาะ
(ข่าวปี 2026: EV cert ไม่ bypass SmartScreen แล้ว · Azure Artifact Signing ไม่รับบุคคลไทย)

## ข้อมูลที่ต้องใช้ตอนสมัคร (ผมเตรียมให้แล้ว)

| ช่อง | ใส่ค่านี้ |
|---|---|
| Project name | A-Sunday Conductor |
| Repository | https://github.com/aase7en/A-Wiki-Conductor |
| License | ดูหน้า repo (ปัจจุบัน pyproject ประกาศ Proprietary — **ถ้าโปรแกรมฟรี/open ควรเปลี่ยนเป็น MIT/Apache-2.0 ก่อนสมัคร** เพราะ Foundation รับเฉพาะ OSS) |
| Website / description | Local autonomous control plane for coordinating AI agents (Windows desktop app, Python stdlib) |
| CI | GitHub Actions |

## ขั้นตอน (ใช้เวลา ~10 นาที + รออนุมัติ 1-2 สัปดาห์)

1. เปิด **https://signpath.org** → เมนู Foundation → Apply
2. กรอกข้อมูลจากตารางข้างบน (ยืนยันตัวตนด้วยบัญชี GitHub ของคุณ)
3. รออีเมลอนุมัติ — เมื่อได้สิทธิ์ จะได้: organization บน SignPath + code signing project
4. สร้าง **API token** ใน SignPath แล้วเก็บเป็น GitHub secret ชื่อ `SIGNPATH_API_TOKEN`
5. บอกผม/Agent ตัวถัดไปว่า "ได้ SignPath แล้ว" — สคริปต์และ workflow พร้อมอยู่ที่:
   - `scripts/sign.py` (เรียก SignPath REST API เซ็น exe)
   - `.github/workflows/sign.yml` (เซ็นอัตโนมัติเมื่อ release)
   ระบบทั้งหมดทำงานทันทีที่ secret `SIGNPATH_API_TOKEN` ถูกตั้งค่า

## หลังเซ็นแล้วคาดหวังอะไร

- SmartScreen อาจยังเตือนช่วงแรก (reputation ต้องสะสม — เป็นธรรมชาติของปี 2026 ทุกเจ้า แม้ซื้อ cert ราคาแพง)
- ใช้ cert ตัวเดิมต่อเนื่องทุก release → reputation สะสมที่ publisher และหายเร็วขึ้น
- ระหว่างรอ: คู่มือมีคำแนะนำ "More info → Run anyway" อยู่แล้ว

## ถ้าไม่อนุมัติ (fallback)

ซื้อ SSL.com IV (บุคคล) ~$129/ปี + eSigner/YubiKey — ผมจะสลับ `scripts/sign.py` เป็น signtool ธรรมดาให้
