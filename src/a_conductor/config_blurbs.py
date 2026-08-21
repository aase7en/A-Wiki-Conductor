"""Thai one-line explanations for every engine config surface (WO-P1-059 PR-D).

Single source of truth so the UI never requires the user to read the engine's
own documentation: each blurb states what the setting does and its effect.
"""

from __future__ import annotations

LANGUAGE_BACKEND_BLURBS: dict[str, str] = {
    "LSP": "ฟรี · ติดตั้งอัตโนมัติ · ครอบคลุมภาษาส่วนใหญ่ (แนะนำ)",
    "JetBrains": "ต้องมี IDE ของ JetBrains + plugin · rename/move แรงกว่า · บางภาษาเท่านั้น",
}

TOOL_BLURBS: dict[str, str] = {
    "read_file": "อ่านไฟล์ — agent ดูโค้ด/เอกสารในโปรเจกต์",
    "write_file": "เขียนไฟล์ — agent แก้โค้ด/สร้างไฟล์ใหม่ (ปิดได้ถ้ากลัวแก้พลาด)",
    "open_file": "เปิดไฟล์ใน editor ที่เชื่อมกับ agent",
    "get_dir_tree": "ดูโครงสร้างโฟลเดอร์ — agent เข้าใจ layout โปรเจกต์",
    "find_file": "หาไฟล์ตามชื่อ — เร็วกว่า search ทั่วไป",
    "search_for_pattern": "ค้นหาข้อความ/regex ในโค้ดทั้งโปรเจกต์",
    "find_symbol": "หา class/function/ตัวแปร แบบเข้าใจภาษา (ไม่ใช่แค่ text)",
    "get_symbols_overview": "ภาพรวม symbol ของไฟล์ — agent อ่านโครงสร้างเร็วขึ้น",
    "get_references_overview": "ดูว่ามีใครเรียกใช้ symbol นี้บ้าง",
    "find_referencing_symbols": "ไล่ทุกจุดที่เรียกใช้ — สำคัญมากตอน refactor",
    "replace_regex": "แทนที่ข้อความแบบ regex ทั้งโปรเจกต์ — ระวังใช้ผิดพลาด",
    "insert_after_symbol": "แทรกโค้ดหลัง symbol ที่เลือก",
    "replace_symbol_body": "เขียนทับเนื้อหา function/class ทั้งก้อน",
    "execute_shell": "รันคำสั่ง shell — อันตรายสุด ปิดได้ถ้าไม่จำเป็น",
    "read_memory": "อ่านความจำที่เก็บไว้ของโปรเจกต์",
    "write_memory": "บันทึกความจำใหม่ — agent จำได้ข้าม session",
    "create_memory": "สร้างไฟล์ความจำใหม่",
    "list_memories": "ดูรายการความจำทั้งหมด",
    "activate_project": "สลับโปรเจกต์ที่กำลังทำงาน — จำเป็นถ้าใช้หลายโปรเจกต์",
    "get_current_config": "ดู config ปัจจุบันของ engine",
    "restart_language_server": "รีสตาร์ท language server — ใช้เมื่อ index เพี้ยน",
}

MODE_BLURBS: dict[str, str] = {
    "planning": "โหมดวางแผน — agent คิดก่อนทำ เหมาะงานใหญ่",
    "editing": "โหมดแก้โค้ด — เปิด tools ด้านการเขียน",
    "interactive": "โหมดสนทนา — agent ถามกลับเมื่อไม่ชัด",
    "one-shot": "งานเดี่ยวจบ — ไม่ถามกลับ ทำเลย",
    "onboarding": "สอนโปรเจกต์ให้ agent ตอนเข้าครั้งแรก",
    "no-onboarding": "ปิดการสอนโปรเจกต์ — ข้ามขั้นตอน onboarding",
    "no-memories": "ปิดความจำ — agent ไม่อ่าน/ไม่เขียนความจำ",
    "query-projects": "อ่านข้ามโปรเจกต์ — ค้นได้แบบ read-only",
}

LANGUAGE_BLURBS: dict[str, str] = {
    "python": "Python — สนับสนุนเต็มรูปแบบ ติดตั้งอัตโนมัติ",
    "typescript": "TypeScript/JavaScript — ติดตั้งอัตโนมัติ",
    "javascript": "JavaScript — ติดตั้งอัตโนมัติ",
    "html": "HTML — เปิดใช้เมื่อทำงานกับหน้าเว็บ",
    "css": "CSS — จำเป็นเมื่อแก้สไตล์",
    "scss": "SCSS/Sass — ต้องมีโปรเจกต์ใช้ Sass",
    "json": "JSON — ไฟล์ config ต่างๆ",
    "yaml": "YAML — ไฟล์ config/Docker/K8s",
    "markdown": "Markdown — เอกสาร/README",
    "toml": "TOML — config ของ Python",
    "rust": "Rust — ต้องติดตั้ง rust-analyzer เอง",
    "go": "Go — ต้องติดตั้ง gopls เอง",
    "cpp": "C/C++ — ต้องมี compile_commands.json",
    "c": "C — ต้องมี compile_commands.json",
    "csharp": "C# — ต้องมี .NET 10+",
    "java": "Java — ต้องติดตั้ง Eclipse JDT LS เอง",
    "kotlin": "Kotlin — ต้องมี Kotlin LS",
    "php": "PHP — ติดตั้งอัตโนมัติ",
    "ruby": "Ruby — ต้องมี Ruby LS",
    "swift": "Swift — ต้องมี Xcode/LLVM",
    "vue": "Vue.js — ติดตั้งอัตโนมัติ",
    "svelte": "Svelte — ติดตั้งอัตโนมัติ",
    "solidity": "Solidity — smart contracts",
    "bash": "Bash/Shell scripts",
}

FIELD_BLURBS: dict[str, str] = {
    "tool_timeout": "เวลาสูงสุดต่อคำสั่ง (วินาที) — ค่าสูงคือใจเย็นขึ้นแต่ค้างนานขึ้น",
    "project_path": "โปรเจกต์ที่ engine ทำงานด้วย — เว้นว่าง = ใช้ค่าที่ Assign ไว้",
    "included_optional_tools": "เปิด optional tools เพิ่ม (CSV) — ปกติไม่ต้องแตะ",
    "fixed_tools": "ล็อกเฉพาะ tools เหล่านี้ (CSV) — ใช้เมื่อต้องการควบคุมสูงสุด · ห้ามใช้ร่วมกับการปิด tools ด้านบน",
    "base_modes": "โหมดพื้นฐาน (CSV) — ปกติใช้ interactive + editing",
    "brain_folder_1": "โฟลเดอร์สมองหลัก — ทุก agent ต้องอ่านกฎในนี้ก่อนทำงาน",
    "brain_folder_2": "สมองเสริม (ถ้ามี) — เช่น กฎองค์กร/ทีม",
    "brain_entry_1": "ไฟล์แรกที่ต้องอ่าน — เช่น AGENTS.md",
    "brain_entry_2": "ไฟล์ที่สองที่ต้องอ่าน — เช่น wiki-overview.md",
}
