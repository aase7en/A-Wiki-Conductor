# Work Orders — หน่วยงานที่ agent ไหนก็หยิบทำต่อได้

ทุก chunk มีไฟล์ WO ของตัวเอง (copy `WO-TEMPLATE.md`) สถานะ:
`open` → `claimed(<agent>)` → (`⏸ paused`) → `done`

**Pause protocol (ใกล้ 5-hr limit / ต้องสลับ agent):**
commit งานค้าง (build ผ่าน → branch ปกติ; ไม่ผ่าน → `wip/<id>`) → append
Checkpoint (commit hash + เหลืออะไร + กับดัก) → Status `⏸ paused` →
อัปเดตตาราง claim ใน `COLLAB.md` → push — **ห้ามทิ้ง uncommitted**

**Resume prompt (user ใช้กับ agent ตัวไหนก็ได้ — Claude/Codex/Cursor/ZCode/Hermes/...):**

```
อ่าน COLLAB.md + docs/work-orders/<id>.md ของ repo นี้
ทำต่อจาก Checkpoint ล่าสุด เฉพาะใน Lane/files ที่ระบุ
เริ่มจาก branch ที่ work order ระบุ และทำงานให้จบใน branch นั้น:
1) deterministic verify ตาม Verify commands + freeze exact candidate SHA
2) R2/R3 ตาม risk: nonauthoring review + hosted exact-head CI ที่ SHA นั้น
3) GPT/integrator เท่านั้น merge expected head นี้เข้า main
4) post-main verify ผ่าน จึง set done + release claim
ห้าม self-merge หรือข้าม review/CI — เจอ blocker ให้ checkpoint แล้วหยุด
```

**Model tier ต่อ WO (ประหยัด credit):** `cheap-ok` (GLM/Sonnet-tier — mechanical
มี Reference pattern ครบ) · `mid` (Opus-tier — spec ปิดช่องแล้ว) ·
`primary-only` (frontier — design/security/protocol + ตรวจงาน tier ล่าง)
— WO ระดับถูกต้องมี Reference pattern + Forbidden + Verify commands ครบ
(เกณฑ์ "junior test": อ่านแล้วทำได้โดยไม่ถามเพิ่ม)

Protocol เต็ม + กติกา 8 ข้อ: `COLLAB.md` ใน repo นี้ และ A-Wiki
`docs/protocols/cross-agent-work-orders.md`
