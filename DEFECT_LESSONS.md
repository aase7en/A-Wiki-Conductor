# DEFECT LESSONS — บทเรียนจากข้อผิดพลาด (ทุก Agent ต้องอ่านก่อนแก้โค้ด)

> ไฟล์นี้บันทึกข้อผิดพลาดที่เคยเกิดขึ้นจริง เพื่อไม่ให้เกิดซ้ำ
> ทุกครั้งที่พบ defect ใหม่ ต้องบันทึกที่นี่ พร้อม root cause และวิธีป้องกัน

---

## #1: Monitor ยิง PowerShell 60 ครั้ง/นาที (2026-08-24)

**อาการ:** CMD windows เด้งเปิด-ปิดตลอดเวลา + คอมช้าลง

**Root cause:** `process_memory_mb()` spawn `powershell.exe Get-Process` ทุก 5 วินาที
ต่อ connector instance (5 instances × 12/min = 60 spawns/นาที)

**แก้:** เปลี่ยนเป็น `ctypes.windll.psapi.GetProcessMemoryInfo()` (native API,
zero process spawn) + ลด tick จาก 5s → 15s

**Lesson:** ห้าม spawn process (cmd/powershell) ใน code path ที่ทำงานซ้ำ
(periodic timer, event handler) — ใช้ native API หรือ file I/O แทนเสมอ

**ตรวจสอบ:** `grep -rn "subprocess\.\(run\|Popen\)" src/a_conductor/` แล้วดูว่า
code path ไหนถูกเรียกซ้ำ (timer/event) — ถ้าใช่ ห้ามใช้ subprocess

---

## #2: Dialog destroy ก่อนอ่าน widget (2026-08-24)

**อาการ:** กด "+ Worker" → กรอกชื่อ → กด "เพิ่ม" → worker ไม่ถูกเพิ่ม
ไม่มี error แสดง

**Root cause:** `submit()` เรียก `dialog.destroy()` ก่อน `entry.get()` —
widget ถูกทำลายแล้ว TclError ถูกกลืนเงียบๆ โดย Tk callback handler

**แก้:** อ่านค่าจาก entry ก่อน → เก็บในตัวแปร → แล้วค่อย destroy → ใช้ค่าที่เก็บ

**Lesson:** ใน Tkinter ทุก dialog ที่มี submit — อ่านค่าจาก widget ทั้งหมด
**ก่อน** เรียก destroy() เสมอ

---

## #3: Splash สร้าง Tk ที่สอง → main window invisible (2026-08-24)

**อาการ:** เปิดโปรแกรม → splash โผล่ 3 วินาที → ดับ → หน้าหลักไม่โผล่
(process รันอยู่แต่ window invisible)

**Root cause:** `SplashScreen` สร้าง `tk.Tk()` ใหม่ (มี mainloop ของตัวเอง)
→ เมื่อ splash ปิด event loop ของ root หลักพัง → `deiconify()` ไม่ทำงาน

**แก้:** เปลี่ยนเป็น `Toplevel(parent)` + ใช้ `parent.after()` สำหรับ timing
+ callback `on_done` แทนการ block ด้วย mainloop แยก

**Lesson:** ห้ามสร้าง `tk.Tk()` มากกว่าหนึ่งตัวในแอปเดียว — ใช้ `Toplevel`
สำหรับหน้าต่างรองทั้งหมด

---

## #4: GPU บอก READY แต่ Sunday Family logo เป็นภาพดำ/หาย (2026-08-25)

**อาการ:** renderer รายงาน `gpu-opengl`, มี particle หลายพันจุด และไม่มี exception
แต่ผู้ใช้มองไม่เห็นโลโก้ครอบครัวใน header

**Root cause:** WGL compatibility context ต้องเปิด `GL_POINT_SPRITE` จึงจะใช้
`gl_PointCoord` ใน fragment shader ได้ ขณะเดียวกัน readiness เดิมพิสูจน์เพียงว่า
สร้าง context/buffer สำเร็จ ไม่ได้พิสูจน์ว่ามี pixel จริงใน back buffer

**แก้:** เปิด point-sprite เฉพาะ compatibility profile, render แล้วอ่าน `GL_BACK`
หนึ่งครั้ง, กำหนด minimum visible-pixel ratio ที่มีนัยสำคัญ และสลับไป Canvas
fallback ทันทีเมื่อ framebuffer ว่าง/ไม่ครบ โดยไม่เพิ่ม loop แยก

**Lesson:** สำหรับ GPU/Canvas/preview งานที่ผู้ใช้ต้อง “มองเห็น” — resource creation
ไม่ใช่ health check; ต้องตรวจ observable output จริงแบบ bounded และมี fallback

**ตรวจสอบ:** real-context test ต้องยืนยัน non-black pixels, renderer identity,
frame-verified state และ destroy context/callback ได้สะอาด ไม่ใช่เช็คเฉพาะ particle count

---

## #5: หน้าต่างปิดแล้วแต่ EXE ค้างระหว่าง connector autostart (2026-08-25)

**อาการ:** ปิดหน้าต่างแล้ว แต่ frozen parent/child process ยังอยู่ต่ออีกหลายสิบวินาที
ถ้าปิดระหว่าง start อาจมี connector ที่ launcher เริ่มแล้วแต่ health ยังตอบ `STOPPED`;
ผล stop ที่ล้มเหลวยังเคยถูก log ว่า `OK` และบางเส้นทางส่งคำสั่ง `start-w` /
`start-inst` ไปยัง service ที่รับเฉพาะ `start` / `stop`

**Root cause:** `Future.cancel()` และ `ThreadPoolExecutor.shutdown(wait=False)` หยุดงานที่
กำลังรันไม่ได้ ขณะที่ Python รอ worker thread ตอน process exit; readiness แบบ transport
ยังแยก “ไม่เคย launch” ออกจาก “launch แล้วแต่ยังไม่ ready” ไม่ได้ และ UI log label
รั่วข้าม boundary ไปเป็น command

**แก้:** ส่ง cooperative cancellation ถึง orchestrator, ตรวจ cancel ก่อน launcher,
serialize launcher handoff กับ forced stop ต่อ instance, จำ launch ที่ cancelled/not-ready,
รอ handoff แบบ bounded ก่อน stop-all, ตรวจ `result_code` ก่อนรายงาน `OK`, normalize
command เป็น `start` / `stop`, ล้าง completed Future references และข้าม health probe
ก่อน stop เมื่อ instance อยู่ใน pending-launched set อยู่แล้ว เพราะ forced stop เป็นผลลัพธ์
ที่ต้องทำแน่นอน (ยังคง post-stop verification เพื่อยืนยันผลจริง)

**Lesson:** shutdown ของงาน async ต้อง cancel ถึง operation จริง ไม่ใช่แค่ Future;
state ที่ยังไม่ ready ไม่ได้พิสูจน์ว่าไม่มี process ถูก launch และ display label ห้ามใช้เป็น
service command โดยตรง

**ตรวจสอบ:** ใช้ concurrent regression ที่ block อยู่ใน launcher แล้วสั่ง close/forced stop;
stop script ต้องเกิดหลัง launcher handoff, process ต้องออกแบบ bounded, failed stop ต้องเป็น
`False`, และ repeated starts ต้องไม่สะสม Future

---

## #6: WORKERS ตารางแสดง auto id แทนชื่อที่ผู้ใช้ตั้ง (2026-08-26)

**อาการ:** กด Add Worker พิมพ์ชื่อเอง → ตารางยังแสดง `a-worker-04` (auto)
ไม่แสดงชื่อที่พิมพ์ — ผู้ใช้คิดว่าชื่อไม่ถูกบันทึก

**Root cause:** `desktop_ui.py` refresh() ใส่ `worker.worker_id` (auto) ในคอลัมน์แรก
แทนที่จะใส่ `worker.display_name` (ชื่อที่ผู้ใช้ตั้ง) — ข้อมูลถูกบันทึกถูกต้อง
แต่ตาราง render ผิด field

**แก้:** เปลี่ยน `worker.worker_id` → `worker.display_name` ในคอลัมน์แรกของ WORKERS

**Lesson:** เมื่อมีทั้ง `id` (ระบบใช้ภายใน) และ `display_name` (ผู้ใช้เห็น)
**ต้อง render display_name ใน UI เสมอ** — อย่าใช้ id ภายในแสดงต่อผู้ใช้

**ตรวจสอบ:** `test_worker_display.py::test_add_worker_with_custom_name_shows_in_table`

---

## #7: Dialog เปิดซ้อนกันเมื่อกดปุ่มซ้ำ (2026-08-26)

**อาการ:** กด Donate/Guide/Settings หลายครั้ง → หน้าต่างเดิมซ้อนกันเป็นชั้น ๆ

**Root cause:** ทุก dialog method สร้าง `Toplevel` ใหม่ทุกครั้งที่ถูกเรียก
ไม่มี check ว่ามี dialog เปิดอยู่แล้วหรือไม่

**แก:** เพิ่ม singleton guard ที่ head ของทุก dialog method —
ถ้ามี dialog เปิดอยู่ให้ `lift()` + `focus_force()` แล้ว return ตัวเดิม

**Lesson:** ทุก dialog ใน Tk ต้องมี singleton guard — `lift + focus` แทนการสร้างใหม่

**ตรวจสอบ:** `test_dialog_singleton.py` (6 tests)

---

## #8: PS1 ไฟล์ไม่มี BOM → พาธภาษาไทยเพี้ยน (2026-08-26)

**อาการ:** สร้าง connector ที่ path มีภาษาไทย → connector เริ่มไม่ได้
เพราะ PowerShell อ่านไฟล์ .ps1 ด้วย ANSI แทน UTF-8

**Root cause:** `write_text(encoding="utf-8")` ไม่ใส่ BOM —
Windows PowerShell 5.1 ต้องมี BOM ถึงอ่านเป็น UTF-8

**แก:** เปลี่ยนเป็น `encoding="utf-8-sig"` ในทุกจุดที่เขียนไฟล์ .ps1

**Lesson:** ไฟล์ .ps1 ที่มีเนื้อหา non-ASCII ต้องเขียนด้วย `utf-8-sig` เสมอ

**ตรวจสอบ:** `test_ps1_encoding_and_quoting.py` (4 tests ตรวจ BOM bytes)

---

## #9: ปิดโปรแกรมหยุด connector เงียบ ๆ → แชทหลุด (2026-08-26)

**อาการ:** ผู้ใช้ปิดโปรแกรม → connector ทุกตัวถูกหยุด → แชท GPT ที่กำลังใช้งานหลุดหมด
ตารางยังโชว์ READY ค้างไว้จนกด Rescan จึงเห็น STOPPED (เข้าใจผิดว่า Rescan ทำ)

**Root cause:** preference `shutdown_stops_instances` (default ON) สั่งหยุดทุกตัว
ตอนปิดหน้าต่างโดยไม่ถาม + ตาราง CONNECTORS ไม่รีเฟรชสด (ต้องกด Rescan เอง)

**แก:** (1) ปิดโปรแกรมถามก่อนหยุด RUNNING connectors (2) ตารางรีเฟรชสดทุก 15 วิ

**Lesson:** การหยุด process ที่ผู้ใช้กำลังใช้งานต้อง**ถามก่อนเสมอ** +
ตารางสถานะต้องรีเฟรชสด ไม่รอให้ผู้ใช้กด

**ตรวจสอบ:** `test_connector_clarity.py` (close-confirm + live-refresh tests)

---

## #10: Test ผูกพอร์ต 18011 = พอร์ต connector จริง (2026-08-26)

**อาการ:** `test_instance_monitor` fail บนเครื่องที่มี connector จริงรันอยู่
(health probe วิ่งไปโดน connector จริงบนพอร์ต 18011 → ได้ READY แทน STOPPED)

**Root cause:** test fixture ใช้พอร์ต 18011 ซึ่งเป็นพอร์ตจริงของ sunday-worker-1

**แก:** ย้าย test ไปใช้พอร์ต 18901+ (ช่วง test-only)

**Lesson:** test fixture ห้ามใช้พอร์ตที่ตรงกับ production (18011-18015) —
ใช้ช่วง 18900+ สำหรับ test เท่านั้น

---

## #11: GitHub Actions Windows runner: GC faulthandler flake (2026-08-26)

**อาการ:** CI Windows `test` job fail ด้วย `Windows fatal exception: code 0x80000003`
ระหว่าง Garbage Collection ใน `pathlib casefold_parts` — fail 5 ครั้งติดต่อกัน

**Root cause:** hosted runner มี instability ใน GC + faulthandler interaction
(known issue ใน repo ตั้งแต่ v0.2.2 — เคยแก้ด้วยการแยก GUI/core suite)

**แก:** GPT แก้ด้วยการแยก `test_local_instances` เป็น CI step ใหม่ (PR #85)
เพิ่มล่าสุด: test directories เปลี่ยนเป็น ASCII-only (ลด non-ASCII pathlib)

**Lesson:** CI Windows flake คลาสนี้ถ้าเจอซ้ำ: (1) แยก suite เป็น step ใหม่
(2) ตรวจว่าไม่ใช่ real bug ก่อน rerun (3) ถ้า rerun 3 ครั้งแล้วยัง fail = ไม่ใช่ flake

---

## #12: Live telemetry ต้องพิสูจน์ provenance ไม่ใช่จับ keyword (2026-08-26)

**อาการ:** real-system E2E ของ AI EXECUTION SLOTS รายงาน Active Project ผิดได้ เพราะ runtime log มี tool/test output ที่ quote ข้อความ `Activating ...` ซึ่งหน้าตาเหมือน event จริง

**Root cause:** parser รุ่นแรก match keyword กว้างเกินไป และสมมติชื่อไฟล์ `conductor-runtime.stderr.log` + tail 256 KiB คงที่ ทั้งที่ connector ที่ rename ยังใช้ชื่อ legacy และ activation ล่าสุดอาจอยู่ลึกกว่านั้น

**แก:** ยอมรับเฉพาะ logger signature `serena.agent:_activate_project:<line> - Activating ...`; เลือก `*-runtime.stderr.log` ที่ใหม่สุด; อ่านย้อนหลังทีละ 64 KiB พร้อม hard cap 2 MiB และหยุดทันทีเมื่อเจอ event จริงล่าสุด

**Lesson:** ข้อมูลที่ UI เรียกว่า **LIVE / ACTIVE / REAL** ต้องมี provenance ที่เฉพาะเจาะจงและ fail-closed; ห้ามยกระดับข้อความที่ "ดูคล้าย event" เป็น runtime truth จาก keyword อย่างเดียว

**ตรวจสอบ:** `tests/test_serena_activity.py` pin กรณี deep-tail, legacy filename และ tool-output false positive + real-system read-only E2E กับ Sunday-Worker fleet

---

## #13: Embedded Markdown HTML must be sanitized with an allowlist (2026-08-27)

**Symptom:** the embedded Guide renderer disabled JavaScript/images/objects, but Python-Markdown still preserves raw HTML from the Markdown source. A future guide edit containing iframe, svg, style/event attributes, or a javascript link could cross the content boundary before renderer feature flags are applied.

**Root cause:** renderer capability flags are runtime controls, not an HTML content sanitizer; regex tag removal also leaves bypass classes and unsafe attributes.

**Fix:** generated Markdown HTML now passes through a stdlib HTMLParser allowlist. Only text/structural tags are emitted; attributes are dropped except safe title and http/https or fragment anchor targets. Active/resource containers are suppressed fail-closed.

**Lesson:** any Markdown-to-HTML surface must treat raw HTML as untrusted input even when Markdown files are repository-controlled. Sanitize with an explicit allowlist before handing content to an embedded renderer; renderer flags are defense-in-depth only.

**Verify:** tests/test_guide_html.py pins iframe/embed/object/video/audio/script/style content, image/svg resources, javascript links, style attributes, and safe HTTPS links.

---

## #14: MCP TTL/stdio failure closes connector CMD and there is no proven runtime auto-recovery (2026-08-28)

**อาการ:** CMD ของ Sunday-Worker หายไปเองระหว่างใช้งาน แล้วผู้ใช้ต้องกลับมากด Start ใน A-Sunday Conductor เอง. Activity log แสดง `START-INST` ตอน 16:24 จึงยืนยันว่าการเปิด Worker-5 รอบนั้นเป็น manual start ไม่ใช่ watchdog recovery.

**Root cause ที่พิสูจน์แล้ว:** live tunnel log ของ Worker-5 แสดง `MCP connection TTL reached; stopping response forwarding` ตามด้วย `stdio MCP command stdin write failed` / `write |1: file already closed`; tunnel-client จึงร้องขอ shutdown ทั้ง process. Launcher เป็น `cmd.exe /c -> powershell.exe -> tunnel-client.exe`, ดังนั้น tunnel-client ออก -> PowerShell จบ -> CMD ปิด. Serena log เป็น orderly shutdown และ Windows event log ไม่พบ native crash ที่ตรงเหตุการณ์.

**สิ่งที่ยังไม่พิสูจน์:** tunnel-client `0.0.11` แสดง default max TTL 10 นาทีและไม่พบ local TTL override แต่ failure สดเกิดที่ effective deadline สั้นกว่า; ห้ามสรุปว่า deadline สั้นมาจาก OpenAI control plane หรือ config ใดจนกว่าจะมี reproducer/upstream evidence.

**สถานะแก้:** ยังไม่ถือว่า FIXED. บันทึกเป็น P0 v0.7.0 stability gate ใน `WO-P1-096`. ต้องแก้ทั้ง (1) request/connection TTL ห้ามฆ่า long-lived connector และ (2) unexpected connector death ต้องมี bounded auto-recovery โดย explicit Stop ต้องไม่ถูก restart.

**Lesson:** transport/request lifetime กับ connector-service lifetime ต้องเป็นคนละ authority. CMD window ไม่ใช่ health authority. Recovery ต้องมี restart budget/backoff และต้องไม่ blind-replay งานที่ execution state ยัง unknown.

**ตรวจสอบ:** fault-injection ต้องทำ TTL/closed-stdio แล้ว connector ยังใช้ request ถัดไปได้หรือ recover กลับ READY; explicit Stop ไม่ restart; repeated crash เข้า DEGRADED ไม่เกิด restart storm; exit code/reason ต้องไม่ว่างและ log เก่าต้องยังอยู่; live isolated E2E ต้องผ่านโดยไม่กด Start เอง.

---

## 🔨 BUILD CHECKLIST (อ่านทุกครั้งก่อน build/release ใหม่)

บันทึก: 2026-08-26 — สรุปปัญหาที่เคยเจอทุกอย่างเพื่อไม่ให้เกิดซ้ำในเวอร์ชันใหม่

### ก่อน build:
- [ ] `pyproject.toml` version = `branding.py APP_VERSION` (test ตรวจอยู่)
- [ ] `CHANGELOG.md` มี section ของเวอร์ชันนี้
- [ ] `docs/USER-GUIDE.md` + `USER-GUIDE-EN.md` มีเวอร์ชันล่าสุดใน header
- [ ] `INSTALL.md` มีเวอร์ชันล่าสุด
- [ ] `tests/test_build_installer.py` version assertions อัปเดต

### ระหว่าง build:
- [ ] ESET ล็อก PE file สด → รอ 90 วินาทีแล้ว retry (เกิดเกือบทุกครั้ง)
- [ ] Build command: `python scripts/build_portable.py --distpath dist/<name>`
- [ ] ตรวจ archive ด้วย `pyi-archive_viewer` ว่ามี: sunday-family-particle.png,
      donate-promptpay-qr.png, gpu_particle_logo, system_metrics, moderngl, PIL, _tkinter

### หลัง build (ก่อนส่งมอบ):
- [ ] Frozen smoke: `./<exe> --smoke --database <temp>.sqlite` → exit 0
- [ ] ทดสอบ: เปิดโปรแกรม → กดทุกปุ่มหลัก (Guide, Settings, Donate, Add Worker, Edit)
- [ ] ทดสอบ: กดปุ่มเดิมซ้ำ 2-3 ครั้ง → หน้าต่างต้องไม่ซ้อน (singleton)
- [ ] ทดสอบ: ปิดโปรแกรมขณะ connector รัน → ต้องมี confirm dialog
- [ ] ทดสอบ: เลือกโปรเจกต์ → PROJECT DISK ต้องแสดงขนาด
- [ ] ทดสอบ: พิมพ์ชื่อ Add Worker → ตารางแสดงชื่อที่พิมพ์ (ไม่ใช่ a-worker-NN)
- [ ] ทดสอบ: กด Rescan → log สรุป "พบ N ตัวเชื่อม: X READY, Y STOPPED"

### ก่อน merge PR:
- [ ] CI 3-OS เขียว (Windows test + Ubuntu smoke + macOS smoke)
- [ ] ถ้า Windows fail ด้วย `0x80000003 GC faulthandler` → ดู #11 (อาจเป็น flake)
- [ ] ตรวจ diff ก่อน merge ทุกครั้ง

### ที่อยู่ไฟล์:
- Build output: `A:\GitHub\A-Sunday-Conductor-Builds\A-Sunday Conductor LATEST.exe`
- (ชื่อ LATEST เสมอ — ทับไฟล์เก่า ไม่สร้างไฟล์ใหม่)

---

## กติกาการเพิ่ม lesson ใหม่:

1. บันทึกเมื่อ: พบ defect ที่ผู้ใช้จริงรายงาน (ไม่ใช่แค่ test fail)
2. รูปแบบ: อาการ → root cause → วิธีแก้ → lesson → วิธีตรวจสอบ
3. ทุก Agent ต้องอ่านไฟล์นี้ก่อนแก้โค้ดใน `src/a_conductor/`

## #15: Caller timeout lost to slow supervisor inspection (2026-08-29)

**Symptom:** Windows hosted CI intermittently returned `timed_out=False` from a one-second supervised command timeout after the caller budget had elapsed. The result instead carried a supervisor recovery classification.

**Root cause:** `_poll_until_resolved()` checked `inspection.recovery_required` before re-checking the monotonic caller deadline. Windows inspection can spend material time in bounded CIM/PowerShell observation, so the deadline may expire inside `inspect()` and a late transient recovery classification could incorrectly win.

**Fix:** terminal durable result evidence remains authoritative first; immediately after inspection, re-check the caller deadline; only then accept a recovery classification. This adds no process, retry loop, scheduler, or execution-state authority.

**Lesson:** timeout budgets include latency inside blocking observations. After a bounded external inspection returns, re-check caller time before classifying a non-terminal/transient result.

**Verify:** deterministic fake-clock tests cover late recovery -> timeout, pre-deadline recovery -> recovery, and durable result -> result. Real Windows attach/timeout integration passed 20 consecutive runs after repair.

---

## #16: Native timeout result lost to transient temp-file cleanup lock (2026-08-29)

**Symptom:** after a native subprocess timeout was already known, Windows occasionally held `stderr.bin` long enough for temp cleanup to raise `WinError 32`; the runner converted that cleanup problem into `COMMAND_EXECUTION_FAILED` and lost the valid timeout result.

**Root cause:** execution result collection and temp-tree deletion shared one context-manager exit. `TemporaryDirectory` performed one immediate removal attempt, so a transient security/indexer file lock changed command semantics after output handles were already closed.

**Fix:** use an explicit private temp directory and finite in-process removal. Retry only `PermissionError`; `FileNotFoundError` is already-clean success; unrelated `OSError` fails immediately; a persistent lock ends as explicit `COMMAND_CLEANUP_FAILED`.

**Lesson:** cleanup after a completed/timeout operation is a separate failure boundary. Transient cleanup locks must not rewrite already-known execution semantics; retries must be bounded and exception-specific.

**Verify:** deterministic fault injection covers two transient locks then success, persistent budget exhaustion, unrelated OSError fail-fast, and temp-directory creation failure. Native and broader execution/supervisor/job suites remain green.

---

---

## #17: Requested graph run identity is not runtime evidence (2026-08-29)

**Symptom:** GE-11 Graph MONITOR could label any operator-entered RUN ID as runtime evidence even when no durable job or event existed for that run.

**Root cause:** `runtime_evidence` was derived from `graph_run_id is not None`, which proves only user input, not durable runtime provenance.

**Fix:** keep requested run identity visible, but set runtime evidence only when a matching durable `GraphDispatchKey` job or durable job event is actually observed. Unknown run IDs remain `RUNTIME: NO RUN EVIDENCE` and project nodes stay fail-closed through GE-9 missing-job semantics.

**Lesson:** an identifier supplied by an operator is selection context, not evidence that the identified runtime entity exists. UI labels such as LIVE/RUNNING/EVIDENCE require observed durable provenance.

**Verify:** deterministic GE-11 tests cover planning-only mode, unknown explicit run -> no evidence, and matching durable job -> durable run evidence.

---

## #18: Persistent native temp cleanup failure accumulates app-owned residue (2026-08-29)

**Symptom:** live audit found 17 `%TEMP%\a-conductor-exec-*` directories after persistent cleanup failures; 15 were older than 24 hours and several were 5-8 days old.

**Root cause:** WO-P1-107 correctly made exhausted cleanup retries explicit as `COMMAND_CLEANUP_FAILED`, but there was no later owner-bounded retry path. A naive age-only sweep also risks deleting a legitimately long-running execution, and failed partial deletion can refresh directory mtime so an old orphan appears recent.

**Fix:** each new execution temp tree holds an OS lock marker for its active lifetime. Before a new run, a best-effort sweep inspects only exact `a-conductor-exec-*` directories, skips symlinks and active locks, uses a 24h age threshold anchored to the older mtime/ctime, and attempts at most 32 single-shot deletions. Primary command cleanup keeps its existing PermissionError retry budget.

**Lesson:** deferred hygiene must retain durable ownership evidence. Age is a filter, not proof of inactivity; active work needs an exclusion signal, and background-style cleanup must be bounded so residue cannot turn into startup latency or alter command semantics.

**Verify:** deterministic tests cover stale/recent/unrelated/symlink boundaries, fail-soft locks, active owner locks, bounded no-wait sweep, mtime-refresh recovery, and runner-held lease. Native suite and broader supervised/job/Claude runtime regressions remain green; local stale residue was reduced to only two recent directories that stayed below the deletion threshold.
