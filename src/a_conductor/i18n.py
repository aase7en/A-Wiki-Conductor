"""Tiny bilingual string table (TH default, EN opt-in via preferences)."""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # header buttons + hint bar
    "btn.guide": {"th": "คู่มือ", "en": "Guide"},
    "btn.settings": {"th": "ตั้งค่า", "en": "Settings"},
    "tip.guide": {
        "th": "เปิดคู่มือการใช้งาน (ในหน้าต่างโปรแกรม)",
        "en": "Open the user guide (inside the app window)",
    },
    "tip.settings": {
        "th": "การตั้งค่ารวมของโปรแกรม (สวิตช์เปิด/ปิด)",
        "en": "Program-wide settings (toggle switches)",
    },
    "hint.three.steps": {
        "th": "เริ่มต้นใช้งาน 3 ขั้น  ① Add Project เพิ่มโปรเจกต์  ② เลือกโปรเจกต์แล้วกด Assign ไปยัง Worker  ③ กด Start (โปรเจกต์ที่มี Connector จะเริ่ม tunnel ทันที)",
        "en": "Get started in 3 steps  ① Add Project  ② select it and press Assign to a Worker  ③ press Start (projects with a Connector start the tunnel immediately)",
    },
    # worker toolbar tooltips
    "tip.release": {
        "th": "ปล่อย Worker คืน (ถอดโปรเจกต์ออกจาก Worker ที่เลือก)",
        "en": "Release the selected Worker (unassign its project)",
    },
    "tip.refresh": {"th": "โหลดสถานะล่าสุดใหม่", "en": "Reload the latest state"},
    "tip.start": {
        "th": "เริ่มงานของ Worker ที่เลือก — ถ้าโปรเจกต์มี Connector จะเริ่ม tunnel ให้อัตโนมัติ",
        "en": "Start the selected Worker — if its project has a Connector, the tunnel starts automatically",
    },
    "tip.stop": {"th": "หยุด Worker ที่เลือก", "en": "Stop the selected Worker"},
    "tip.restart": {"th": "หยุดแล้วเริ่มใหม่", "en": "Stop then start again"},
    "tip.setup": {
        "th": "ตั้งค่า runtime ของ Worker (จำเป็นสำหรับโปรเจกต์ที่ไม่มี Connector)",
        "en": "Configure the Worker runtime (needed for projects without a Connector)",
    },
    "tip.config": {
        "th": "ตั้งค่า engine ของ Worker: ภาษา / เปิด-ปิด tools / project",
        "en": "Configure the Worker engine: language / tool toggles / project",
    },
    "tip.add.worker": {
        "th": "เพิ่มช่อง Worker ใหม่ (a-worker-04, 05, ...) — สำหรับงานขนานหรือ sub-agent ที่ซ้อนกัน",
        "en": "Add a new Worker slot (a-worker-04, 05, ...) — for parallel work or nested sub-agents",
    },
    "tip.rename.worker": {
        "th": "เปลี่ยนชื่อที่แสดงของ Worker ที่เลือก",
        "en": "Rename the selected Worker's display name",
    },
    "tip.delete.worker": {
        "th": "ลบช่อง Worker ที่เลือก — ทำได้เฉพาะ Worker ที่หยุดและไม่มีโปรเจกต์แล้วเท่านั้น",
        "en": "Delete the selected Worker slot — only when stopped and unassigned",
    },
    # connector toolbar
    "btn.add.connector": {"th": "+ ตัวเชื่อม", "en": "+ Connector"},
    "btn.rename.connector": {"th": "แก้ชื่อ", "en": "Rename"},
    "btn.delete.connector": {"th": "ลบ", "en": "Delete"},
    "btn.brain": {"th": "สมอง + folder", "en": "Brain folders"},
    "tip.instance.start": {
        "th": "เริ่มตัวเชื่อม (tunnel) ที่เลือก — agent ใน ChatGPT จะเชื่อมเข้ามาทางนี้",
        "en": "Start the selected connector (tunnel) — agents in ChatGPT connect through it",
    },
    "tip.instance.stop": {
        "th": "หยุดตัวเชื่อมที่เลือก (ปลอดภัย — ตรวจ PID ก่อนหยุดเสมอ)",
        "en": "Stop the selected connector (safe — always PID-checked)",
    },
    "tip.instance.startall": {
        "th": "เปิดทุกตัวเชื่อมที่ยังไม่ READY ในคลิกเดียว",
        "en": "Start every connector that is not READY, in one click",
    },
    "tip.instance.auto": {
        "th": "ตั้งให้ตัวเชื่อมนี้เปิดเองทุกครั้งที่เปิดโปรแกรม",
        "en": "Auto-start this connector whenever the app opens",
    },
    "tip.instance.rescan": {
        "th": "ค้นหาตัวเชื่อมที่เพิ่มเข้ามาใหม่",
        "en": "Discover newly added connectors",
    },
    "tip.add.connector": {
        "th": "สร้างตัวเชื่อมใหม่จากแม่แบบที่ผ่านการตรวจสอบ — ตั้งชื่อ + เลือกโปรเจกต์\n(พอร์ตจัดให้อัตโนมัติ / หน้าต่างจะชื่อ Sunday-works ถัดไป)\nจะได้แชท ChatGPT ทำงานขนานกันได้อีกช่อง",
        "en": "Create a new connector from the validated template — name + project\n(port auto-assigned / window titled the next Sunday-works N)\ngives you another parallel ChatGPT chat",
    },
    "tip.rename.connector": {
        "th": "เปลี่ยนชื่อที่แสดงของตัวเชื่อมที่เลือก (ชื่อโฟลเดอร์จริงไม่ถูกแตะ)",
        "en": "Rename the selected connector's display name (the real folder is untouched)",
    },
    "tip.delete.connector": {
        "th": "ลบตัวเชื่อมที่เลือก — จะหยุดให้ก่อน บีบอัดสำรองเป็น zip แล้วจึงลบ\n(กู้คืนได้จากโฟลเดอร์ instance-backups)",
        "en": "Delete the selected connector — stops it first, zips a backup, then removes\n(restorable from the instance-backups folder)",
    },
    # copy menu
    "menu.copy.path": {"th": "คัดลอก path (Copy path)", "en": "Copy path"},
    "btn.close": {"th": "ปิด", "en": "Close"},
    # dialogs (worker)
    "dlg.add.worker.title": {"th": "เพิ่ม Worker", "en": "Add Worker"},
    "dlg.add.worker.header": {"th": "> เพิ่มช่อง Worker ใหม่", "en": "> Add a new Worker slot"},
    "dlg.add.worker.name": {
        "th": "ชื่อที่แสดง (ไม่กรอก = ตั้งอัตโนมัติ เช่น A-Worker 4)",
        "en": "Display name (blank = auto, e.g. A-Worker 4)",
    },
    "dlg.add.worker.submit": {"th": "เพิ่ม", "en": "Add"},
    "dlg.rename.worker.name": {
        "th": "ชื่อใหม่ที่จะแสดงในตาราง WORKERS",
        "en": "New name to show in the WORKERS table",
    },
    "dlg.rename.worker.submit": {"th": "บันทึก", "en": "Save"},
    "dlg.confirm.title": {"th": "ยืนยัน", "en": "Confirm"},
    "dlg.confirm.ok": {"th": "ยืนยัน", "en": "Confirm"},
    "dlg.confirm.cancel": {"th": "ยกเลิก", "en": "Cancel"},
    "dlg.delete.worker.message": {
        "th": "ลบช่อง Worker {worker_id} ออกจากระบบ?\n(ทำได้เฉพาะ Worker ที่หยุดและไม่มีโปรเจกต์)",
        "en": "Remove the Worker slot {worker_id}?\n(only stopped, unassigned Workers can be deleted)",
    },
    # dialogs (connector)
    "dlg.add.connector.title": {"th": "เพิ่มตัวเชื่อม", "en": "Add Connector"},
    "dlg.add.connector.header": {
        "th": "> เพิ่มตัวเชื่อมใหม่ (แชท ChatGPT ช่องเพิ่ม)",
        "en": "> Add a new connector (an extra ChatGPT chat lane)",
    },
    "dlg.add.connector.name": {
        "th": "ชื่อ (ภาษาอังกฤษคำเดียว เช่น Research)",
        "en": "Name (one English word, e.g. Research)",
    },
    "dlg.add.connector.project": {
        "th": "พาธโปรเจกต์เต็ม (เช่น A:\\GitHub\\my-project)",
        "en": "Full project path (e.g. A:\\GitHub\\my-project)",
    },
    "dlg.add.connector.tunnel": {
        "th": "Tunnel ID (ไม่บังคับ — ข้ามได้แล้วใส่ภายหลังด้วยปุ่ม Tunnel ID)",
        "en": "Tunnel ID (optional — skip and set later via the Tunnel ID button)",
    },
    "dlg.add.connector.submit": {"th": "สร้าง", "en": "Create"},
    "dlg.delete.connector.message": {
        "th": "ลบตัวเชื่อม {name}?\nจะหยุดตัวเชื่อมให้ก่อน บีบอัดสำรองเป็น zip แล้วจึงลบโฟลเดอร์\n(กู้คืนได้จากโฟลเดอร์ instance-backups)",
        "en": "Delete connector {name}?\nIt will be stopped first, zipped as a backup, then removed\n(restorable from the instance-backups folder)",
    },
    # misc
    "win.error": {"th": "แจ้งเตือน", "en": "Notice"},
    "win.guide": {"th": "คู่มือการใช้งาน", "en": "User Guide"},
    "win.settings": {"th": "ตั้งค่า", "en": "Settings"},
    "prefs.language": {"th": "ภาษา / Language", "en": "Language / ภาษา"},
    "prefs.language.help": {
        "th": "สลับภาษาของโปรแกรม (ไทย/English) — บันทึกแล้วปิด-เปิดโปรแกรมใหม่เพื่อให้มีผล",
        "en": "Switch the app language (Thai/English) — save, then restart the app to apply",
    },
    "prefs.language.restart": {
        "th": "บันทึกแล้ว — ปิดและเปิดโปรแกรมใหม่เพื่อเปลี่ยนภาษา",
        "en": "Saved — restart the app to apply the new language",
    },
}

_language = "th"


def set_language(language: str) -> None:
    global _language
    if language in ("th", "en"):
        _language = language


def get_language() -> str:
    return _language


def tr(key: str) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(_language) or entry.get("th") or key
