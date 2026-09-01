"""Localized help/guidance strings; action button labels stay canonical English."""

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
    "err.footer": {
        "th": "อ่านเพิ่ม: ปุ่ม คู่มือ มุมขวาบนของโปรแกรม",
        "en": "Learn more: the Guide button, top-right of the app",
    },
    "dlg.rename.connector.title": {"th": "แก้ชื่อตัวเชื่อม", "en": "Rename connector"},
    "dlg.rename.header": {"th": "แก้ชื่อ", "en": "Rename"},
    "dlg.edit.connector.title": {"th": "แก้ไขตัวเชื่อม", "en": "Edit connector"},
    "dlg.edit.connector.header": {"th": "แก้ไขตัวเชื่อม", "en": "Edit connector"},
    "dlg.edit.connector.tunnel": {
        "th": "Tunnel ID (ถ้าไม่เปลี่ยน ปล่อยว่างไว้ — ขึ้นต้นด้วย tunnel_ ตามด้วย 32 ตัวอักษร)",
        "en": "Tunnel ID (leave blank to keep the current one — starts with tunnel_ plus 32 chars)",
    },
    "dlg.edit.connector.project": {
        "th": "พาธโปรเจกต์ (เปลี่ยนแล้วมีผลหลัง restart ตัวเชื่อม)",
        "en": "Project path (applies after the connector restarts)",
    },
    "btn.close": {"th": "ปิด", "en": "Close"},
    "prefs.shutdown": {
        "th": "ปิดโปรแกรมแล้วหยุดทุกตัวเชื่อม (เครียร์เครื่อง)",
        "en": "Stop all connectors when the app closes (clean machine)",
    },
    "prefs.shutdown.help": {
        "th": "ON = ทุกครั้งที่ปิดโปรแกรม จะสั่งหยุดตัวเชื่อมทุกตัวที่กำลังรันและเก็บกวาด process ค้างให้\nOFF = ตัวเชื่อมที่รันอยู่จะเปิดต่อ (เหมาะถ้าอยากให้แชทใช้งานได้แม้ปิดโปรแกรม)",
        "en": "ON = closing the app stops every running connector and reaps stale processes\nOFF = running connectors keep serving even after the app closes",
    },
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
    # setup wizard
    "wiz.title": {"th": "Setup Wizard — ติดตั้งทุกอย่างอัตโนมัติ", "en": "Setup Wizard"},
    "wiz.welcome": {
        "th": "ยินดีต้อนรับ! ตัวช่วยนี้จะติดตั้งทุกอย่างที่จำเป็น:\n\n  1. uv (package manager)\n  2. Python 3.13\n  3. Serena engine\n  4. tunnel-client (เชื่อมต่อ ChatGPT)\n  5. Connector แรกของคุณ\n\nกด Next เพื่อเริ่ม",
        "en": "Welcome! This wizard installs everything you need:\n\n  1. uv (package manager)\n  2. Python 3.13\n  3. Serena engine\n  4. tunnel-client (ChatGPT connection)\n  5. Your first connector\n\nPress Next to begin",
    },
    "wiz.check": {"th": "ตรวจสอบระบบ", "en": "System Check"},
    "wiz.install": {"th": "กำลังติดตั้ง...", "en": "Installing..."},
    "wiz.instance": {"th": "สร้าง Connector แรก", "en": "Create First Connector"},
    "wiz.credentials": {"th": "ตั้งค่า OpenAI", "en": "OpenAI Configuration"},
    "wiz.finish": {"th": "เสร็จสิ้น!", "en": "Done!"},
    "wiz.next": {"th": "ถัดไป", "en": "Next"},
    "wiz.back": {"th": "ย้อนกลับ", "en": "Back"},
    "prefs.language": {"th": "ภาษาคำอธิบาย / Help language", "en": "Help language"},
    "prefs.language.help": {
        "th": "เลือกภาษาไทย/中文/English สำหรับคำอธิบายและ tooltip — ปุ่มคำสั่งยังเป็น English เสมอ",
        "en": "Choose Thai/Chinese/English for help and tooltips — action buttons always stay in English",
    },
    "prefs.language.restart": {
        "th": "เปลี่ยนคำอธิบายทันที และจำค่าไว้สำหรับครั้งถัดไป",
        "en": "Help text updates immediately and the choice is saved for next launch",
    },
    "prefs.models_agents.header": {"th": "> MODELS & AGENTS", "en": "> MODELS & AGENTS"},
    "prefs.models_agents.loading": {"th": "กำลังโหลดสถานะ provider...", "en": "Loading provider status..."},
    "prefs.models_agents.empty": {"th": "NO PROVIDERS — ยังไม่มี provider ที่ตั้งค่าไว้", "en": "NO PROVIDERS - no providers are configured yet"},
    "prefs.models_agents.error": {"th": "Provider status unavailable", "en": "Provider status unavailable"},
}

# Chinese is intentionally concentrated on operator guidance/tooltips. Entries
# without a Chinese translation fall back to English so the UI never falls back
# to Thai unexpectedly for a Chinese-selected session.
_ZH_CN: dict[str, str] = {
    "menu.copy.path": "复制路径",
    "tip.add.project": "注册本机项目文件夹，不修改项目文件",
    "tip.assign": "把所选项目分配给所选 Worker",
    "btn.guide": "Guide",
    "btn.settings": "Settings",
    "tip.guide": "打开应用内使用指南",
    "tip.settings": "打开 A-Conductor 全局设置",
    "hint.three.steps": "开始：① Add Project  ② Assign 到 Worker  ③ Start",
    "tip.release": "释放所选 Worker 并取消项目分配",
    "tip.refresh": "重新加载最新状态",
    "tip.start": "启动所选 Worker；如有 Connector 会同时启动连接",
    "tip.stop": "停止所选 Worker",
    "tip.restart": "停止后重新启动所选 Worker",
    "tip.setup": "配置所选 Worker 的 Runtime",
    "tip.config": "配置 Worker 的语言、工具和项目设置",
    "tip.add.worker": "新增 Worker 工作槽，用于并行任务或子代理",
    "tip.rename.worker": "修改所选 Worker 的显示名称",
    "tip.delete.worker": "删除已停止且未分配项目的 Worker 工作槽",
    "tip.instance.start": "启动所选 Connector",
    "tip.instance.stop": "安全停止所选 Connector（会验证 PID）",
    "tip.instance.startall": "启动所有尚未 READY 的 Connector",
    "tip.instance.auto": "切换此 Connector 的自动启动",
    "tip.instance.rescan": "重新扫描新的 Connector",
    "tip.add.connector": "从已验证模板创建新的 Connector，并分配项目",
    "tip.rename.connector": "修改 Connector 显示名称，不改真实文件夹",
    "tip.delete.connector": "停止 Connector、创建 ZIP 备份后删除",
    "prefs.language": "帮助语言 / Help language",
    "prefs.language.help": "选择 Thai、中文或 English。按钮始终显示 English；帮助和提示按所选语言显示。",
    "prefs.language.restart": "语言帮助会立即更新，并保存用于下次启动。",
    "tip.activate": "复制 A-Conductor 项目激活指令，并粘贴到连接此 Conductor 的 AI 会话中",
    "tip.brain": "配置所有 Worker 共用的 Second Brain 索引和必读入口文件",
    "tip.connection": "ONLINE = A-Conductor 控制服务可用；OFFLINE = 控制服务无法访问",
    "tip.logo": "Sunday Family 粒子标志；移动鼠标可看到粒子和视线跟随",
    "tip.tunnel": "设置所选 Connector 的 Tunnel ID",
    "tip.rebind": "把所选 Connector 重新绑定到另一个项目；重启后生效",
    "tip.upstream": "只读检查底层 Runtime 引擎是否有上游更新",
    "tip.memory": "只读查看所选项目是否已有 Conductor/Worker 可用的项目记忆",
    "teach.step.1": "Step 1 · Add Project — register a project folder without modifying it.",
    "teach.step.2": "Step 2 · Assign — connect the selected project to a Worker.",
    "teach.step.3": "Step 3 · Start — start the selected Worker and its Connector when available.",
    "teach.step.4": "Tip · Hover any action for help in your selected language.",
}
for _key, _value in _ZH_CN.items():
    STRINGS.setdefault(_key, {})["zh-CN"] = _value

# New help keys are tri-lingual. Keeping them in the same table preserves the
# existing i18n single source of truth instead of creating a second help system.
_NEW_HELP: dict[str, dict[str, str]] = {
    "tip.add.project": {
        "th": "เพิ่มโฟลเดอร์โปรเจกต์เข้า A-Conductor โดยไม่แก้ไฟล์ภายในโปรเจกต์",
        "en": "Register a local project folder in A-Conductor without modifying project files",
    },
    "tip.assign": {
        "th": "ผูกโปรเจกต์ที่เลือกเข้ากับ Worker ที่เลือก",
        "en": "Assign the selected project to the selected Worker",
    },
    "tip.activate": {
        "th": "คัดลอกคำสั่งเปิดใช้งานโปรเจกต์ของ A-Conductor แล้วนำไปวางใน AI chat ที่เชื่อมกับ Conductor นี้",
        "en": "Copy the A-Conductor project activation instruction and paste it into an AI session connected to this Conductor",
    },
    "tip.brain": {
        "th": "ตั้งค่า Second Brain ส่วนกลาง: โฟลเดอร์ความรู้และไฟล์ทางเข้าที่ Worker ต้องอ่าน",
        "en": "Configure the shared Second Brain index and entry files that Workers should read",
    },
    "tip.connection": {
        "th": "ONLINE = บริการควบคุม A-Conductor พร้อมใช้งาน · OFFLINE = ติดต่อบริการควบคุมไม่ได้",
        "en": "ONLINE = the A-Conductor control service is reachable · OFFLINE = the control service is unavailable",
    },
    "tip.logo": {
        "th": "โลโก้ Sunday Family แบบอนุภาค — ขยับเมาส์เพื่อดูอนุภาคและสายตาติดตาม",
        "en": "Sunday Family particle logo — move the mouse to see particles and gaze tracking",
    },
    "tip.tunnel": {
        "th": "ตั้ง Tunnel ID ให้ Connector ที่เลือก",
        "en": "Set the Tunnel ID for the selected Connector",
    },
    "tip.rebind": {
        "th": "เปลี่ยนโปรเจกต์ที่ Connector ที่เลือกผูกอยู่ มีผลหลัง restart",
        "en": "Rebind the selected Connector to another project; takes effect after restart",
    },
    "tip.upstream": {
        "th": "ตรวจสอบแบบอ่านอย่างเดียวว่ารันไทม์ต้นแบบมีอัปเดต upstream หรือไม่",
        "en": "Read-only check for upstream updates to the underlying runtime engine",
    },
    "tip.memory": {
        "th": "ตรวจแบบอ่านอย่างเดียวว่าโปรเจกต์ที่เลือกมีความจำสำหรับ Conductor/Worker แล้วหรือไม่",
        "en": "Read-only check for project memory available to the Conductor/Worker workflow",
    },
    "teach.step.1": {
        "th": "ขั้นที่ 1 · Add Project — ลงทะเบียนโฟลเดอร์โปรเจกต์โดยไม่แก้ไฟล์ภายใน",
        "en": "Step 1 · Add Project — register a project folder without modifying it.",
    },
    "teach.step.2": {
        "th": "ขั้นที่ 2 · Assign — ผูกโปรเจกต์ที่เลือกเข้ากับ Worker",
        "en": "Step 2 · Assign — connect the selected project to a Worker.",
    },
    "teach.step.3": {
        "th": "ขั้นที่ 3 · Start — เริ่ม Worker และ Connector ของโปรเจกต์เมื่อมี",
        "en": "Step 3 · Start — start the selected Worker and its Connector when available.",
    },
    "teach.step.4": {
        "th": "เคล็ดลับ · วางเมาส์บนปุ่มเพื่อดูคำอธิบายตามภาษาที่เลือก",
        "en": "Tip · Hover any action for help in your selected language.",
    },
}
for _key, _entry in _NEW_HELP.items():
    target = STRINGS.setdefault(_key, {})
    target.update(_entry)
    target["zh-CN"] = _ZH_CN[_key]

STRINGS["tip.connector.column"] = {
    "th": "Worker Registry เป็นสถานะเชิงตรรกะของ scheduler ไม่ใช่สถานะ Connector แบบ live · ดู AI EXECUTION SLOTS สำหรับการเชื่อมต่อและ Active Project จริง",
    "zh-CN": "Worker Registry 是调度器的逻辑状态，不是实时 Connector 状态；实时连接和 Active Project 请看 AI EXECUTION SLOTS。",
    "en": "Worker Registry is scheduler/logical state, not live connector state. Use AI EXECUTION SLOTS for live connection and Active Project.",
}
STRINGS["tip.execution.slots"] = {
    "th": "Live ≤15s: CONNECTION มาจาก /readyz · ACTIVE PROJECT มาจาก Serena runtime activation log · BOUND PROJECT คือโปรเจกต์ตอนสร้าง Connector · [DRIFT] หมายถึง Chat เปลี่ยน Active Project ไปจากที่ Connector ผูกไว้",
    "zh-CN": "实时≤15秒：CONNECTION 来自 /readyz；ACTIVE PROJECT 来自 Serena 运行时激活日志；BOUND PROJECT 是 Connector 绑定项目；[DRIFT] 表示聊天已切换到其他 Active Project。",
    "en": "Live ≤15s: CONNECTION comes from /readyz; ACTIVE PROJECT comes from Serena runtime activation logs; BOUND PROJECT is the connector binding. [DRIFT] means the chat switched to a different active project.",
}
STRINGS["tip.worker.registry"] = {
    "th": "Advanced: logical Worker Registry สำหรับ scheduler/CRUD ไม่ใช่สถานะการเชื่อมต่อแบบ live · เปิดเมื่อจำเป็นต้องจัดการ Worker ภายใน",
    "zh-CN": "高级：逻辑 Worker Registry 用于调度器/CRUD，不代表实时连接状态；仅在需要管理内部 Worker 时展开。",
    "en": "Advanced: the logical Worker Registry is for scheduler/CRUD state, not live connection health. Expand it only when managing internal workers.",
}
STRINGS["tip.project.disk"] = {
    "th": "จุดสีขาวเทาเป็นเพียงสเกลขนาดแบบลอการิทึมโดยประมาณ ไม่ใช่เปอร์เซ็นต์พื้นที่ดิสก์ที่ใช้; ตัวเลข PROJECT DISK คือค่าหลักที่เชื่อถือได้",
    "zh-CN": "灰白粒子仅表示近似的对数级大小，不是磁盘已用百分比；PROJECT DISK 的精确数字才是权威值。",
    "en": "The monochrome dots show relative logarithmic size only, not percent disk used. The exact PROJECT DISK number is authoritative.",
}
STRINGS["confirm.replace.assignment"] = {
    "th": "Worker นี้มีโปรเจกต์อยู่แล้ว\n\nCurrent: {current}\nNew: {new}\n\nแทนที่ assignment เดิมหรือไม่?",
    "zh-CN": "此 Worker 已分配项目。\n\nCurrent: {current}\nNew: {new}\n\n是否替换现有分配？",
    "en": "This Worker already has a project.\n\nCurrent: {current}\nNew: {new}\n\nReplace the current assignment?",
}
STRINGS["tip.copy.log"] = {
    "th": "เลือกข้อความแล้วกด Ctrl+C หรือคลิกขวาเพื่อ Copy Selection / Copy All",
    "zh-CN": "选择文本后按 Ctrl+C，或右键选择 Copy Selection / Copy All。",
    "en": "Select text and press Ctrl+C, or right-click for Copy Selection / Copy All.",
}
STRINGS.update(
    {
        "prefs.header": {
            "th": "> การตั้งค่ารวม  (เปลี่ยนแล้วมีผลทันที)",
            "zh-CN": "> 全局设置（更改立即生效）",
            "en": "> Global settings  (changes apply immediately)",
        },
        "prefs.supervised": {
            "th": "โหมด Supervised  (คุมงานเบื้องหลัง: บันทึกทุกคำสั่ง · กันสั่งซ้ำ · เก็บผลแม้ timeout)",
            "zh-CN": "Supervised mode（记录命令、防止重复执行，并保留超时任务结果）",
            "en": "Supervised mode  (record commands, prevent duplicates, preserve timed-out results)",
        },
        "prefs.supervised.help": {
            "th": "ON = คุมคำสั่ง native ตั้งแต่เริ่มจนจบ พร้อมบันทึกและกันงานซ้ำ\nOFF = เร็วขึ้นเล็กน้อย แต่ไม่มีการบันทึก/กันซ้ำ\n(แนะนำ: ON)",
            "zh-CN": "ON = 全程记录 native 命令并防止重复任务\nOFF = 略快，但不记录或去重\n（推荐：ON）",
            "en": "ON = supervise native commands end to end, record them, and prevent duplicates\nOFF = slightly faster, without recording or duplicate protection\n(Recommended: ON)",
        },
        "prefs.supervised.summary": {
            "th": "ON: ปลอดภัยกว่า บันทึกทุกงาน กันสั่งซ้ำอัตโนมัติ · OFF: เร็วกว่า เหมาะกับงานสั้นๆ ไม่สำคัญ",
            "zh-CN": "ON：更安全、记录任务并自动去重 · OFF：更快，适合短期非关键任务",
            "en": "ON: safer, records work and prevents duplicates · OFF: faster for short non-critical tasks",
        },
        "monitor.select": {
            "th": "  เลือกตัวเชื่อมในตาราง CONNECTORS เพื่อดูสถานะ · PID · หน่วยความจำ · log ล่าสุด",
            "zh-CN": "  在 CONNECTORS 表中选择连接，以查看状态、PID、内存和最新日志",
            "en": "  Select a row in CONNECTORS to view state, PID, memory, and the latest log",
        },
        "monitor.select.detail": {
            "th": "  (เปิด/ปิดผ่านปุ่มในแอปได้เลย — start จากแอปไม่มีหน้าต่าง CMD)",
            "zh-CN": "  （可用应用内按钮启动或停止；启动不会打开 CMD 窗口）",
            "en": "  (start or stop it with the app buttons; starting does not open a CMD window)",
        },
        "monitor.missing": {
            "th": "  {name}: ไม่พบ instance",
            "zh-CN": "  {name}：未找到 Connector instance",
            "en": "  {name}: instance not found",
        },
        "monitor.errors": {
            "th": "  errors ล่าสุด: {count}",
            "zh-CN": "  最新 errors：{count}",
            "en": "  recent errors: {count}",
        },
        "memory.select": {
            "th": "สมองโปรเจกต์: เลือกโปรเจกต์เพื่อดูสถานะ",
            "zh-CN": "项目记忆：选择项目以查看状态",
            "en": "Project memory: select a project to view status",
        },
        "memory.unknown": {
            "th": "สมองโปรเจกต์: —",
            "zh-CN": "项目记忆：—",
            "en": "Project memory: —",
        },
        "memory.ready": {
            "th": "สมองโปรเจกต์: พร้อม ({count} ไฟล์)",
            "zh-CN": "项目记忆：READY（{count} 个文件）",
            "en": "Project memory: READY ({count} files)",
        },
        "memory.path.missing": {
            "th": "สมองโปรเจกต์: ไม่พบ path โปรเจกต์",
            "zh-CN": "项目记忆：未找到项目路径",
            "en": "Project memory: project path not found",
        },
        "memory.empty": {
            "th": "สมองโปรเจกต์: ยังไม่มีความจำ — onboarding จะทำงานเมื่อ agent เข้าครั้งแรก · หลังจบเริ่มบทสนทนาใหม่",
            "zh-CN": "项目记忆：尚无记忆；Agent 首次进入时会执行 onboarding，完成后请开始新会话",
            "en": "Project memory: none yet; onboarding runs when an agent first enters, then start a new conversation",
        },
    }
)

_language = "th"


def set_language(language: str) -> None:
    global _language
    if language in ("th", "zh-CN", "en"):
        _language = language


def get_language() -> str:
    return _language


def tr(key: str) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(_language) or entry.get("en") or entry.get("th") or key


_BUTTON_ALIASES: dict[str, str] = {
    "ปิด": "Close",
    "เปิดไฟล์ภายนอก": "Open External File",
    "เลือก...": "Browse...",
    "เลือกโฟลเดอร์...": "Browse Folder...",
    "ใช้ค่า default (A-Wiki)": "Use Default (A-Wiki)",
    "เปลี่ยนเลย": "Apply Change",
    "ยกเลิก": "Cancel",
    "บันทึก": "Save",
    "ตั้ง Tunnel ID": "Set Tunnel ID",
    "เปลี่ยนโปรเจกต์": "Change Project",
    "เช็คอัปเดท engine": "Check Engine Update",
}


def canonical_button_label(text: str) -> str:
    """Return the stable English action label for any localized/legacy button text."""
    value = str(text)
    if value in _BUTTON_ALIASES:
        return _BUTTON_ALIASES[value]
    for entry in STRINGS.values():
        english = entry.get("en")
        if english and value in entry.values():
            return english
    return value
