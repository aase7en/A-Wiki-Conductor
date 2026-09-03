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

**Fix:** each new execution temp tree holds an OS lock marker for its active lifetime. New trees also use a versioned basename `a-conductor-exec-v2-<created-epoch>-...`, so their creation age survives directory mtime/ctime refresh after partial cleanup. Before a new run, a best-effort sweep inspects only exact `a-conductor-exec-*` directories, skips symlinks and active locks, uses the encoded creation epoch for v2 trees (legacy pre-v2 residue falls back to the older mtime/ctime), and attempts at most 32 single-shot deletions. Primary command cleanup keeps its existing PermissionError retry budget.

**Lesson:** deferred hygiene needs both durable ownership evidence and stable provenance. Age is a filter, not proof of inactivity; active work needs an exclusion signal, and cleanup attempts must not rewrite the age authority used by the next sweep. Background-style cleanup must remain bounded so residue cannot turn into startup latency or alter command semantics.

**Verify:** deterministic tests cover stale/recent/unrelated/symlink boundaries, fail-soft locks, active owner locks, bounded no-wait sweep, runner-held lease, versioned temp creation, and metadata-refresh recovery using the encoded creation epoch. Native suite = 30 passed; broader native/supervised/job/Claude + installer composition = 219 passed. Local stale residue remains reduced to two legacy directories ~9h old, intentionally preserved below the 24h threshold.


## #19: PowerShell 5.1 default text encoding corrupts UTF-8 Markdown (2026-08-29)

**Symptom:** a release-gate documentation checkpoint changed valid em dashes in tracked UTF-8 Markdown into mojibake such as `โ€”` without the edit command failing. A separate release audit also found three historical `?` separators in `CHANGELOG.md` where em dashes were intended.

**Root cause:** Windows PowerShell 5.1 text read/write paths can decode or re-encode UTF-8 content using legacy code-page defaults. A successful shell command therefore does not prove byte-preserving Markdown mutation.

**Fix:** restore affected files from the clean branch HEAD, reapply only intended substitutions with an explicit UTF-8 writer, repair the three proven CHANGELOG separators, and re-run remote diff/CI from the corrected head.

**Lesson:** do not use implicit PowerShell 5.1 text encoding for repository Markdown containing non-ASCII text. Use an explicit UTF-8-capable writer (for example Python `Path.read_text/write_text(encoding="utf-8")`) and treat encoding preservation as part of the mutation contract.

**Verify:** run `git diff --check`, inspect the complete diff, scan release-facing text for replacement/mojibake markers, and confirm only intended lines changed before commit/push. CI must run again after any encoding repair.

---

## #20: User-level Claude settings can override a task's declared provider endpoint (2026-08-30)

**Symptom:** a supervised direct-Z.ai GLM task carried the intended `ANTHROPIC_BASE_URL`, yet Claude Code attempted the user's local CCR endpoint and failed `ConnectionRefused`.

**Root cause:** bare/safe provider jobs still loaded user settings; the user's valid interactive Claude configuration defines `ANTHROPIC_BASE_URL=http://127.0.0.1:3456`, which conflicted with the task's provider binding.

**Fix:** supervised harness invocations now add `--setting-sources project,local`, excluding unrelated user-level settings while preserving explicit provider endpoint/credential bindings and read-only safe mode.

**Lesson:** provider identity is part of execution authority. Ambient user configuration must not silently rewrite the provider selected by a durable task.

**Verify:** harness regression checks the setting-source boundary; live retry changed from localhost `ConnectionRefused` to an actual Z.ai HTTP 429 entitlement response, proving the declared endpoint became authoritative.

---

## #21: CLI timeout without process-tree ownership can outlive the caller budget (2026-08-30)

**Symptom:** a raw Python `subprocess.run(..., timeout=30)` probe around Claude/GLM reported timeout only after roughly 181 seconds because a descendant process kept inherited capture handles alive.

**Root cause:** caller timeout killed/wound only the direct subprocess relationship; it did not provide durable ownership/reconciliation for the spawned CLI process tree.

**Fix:** AHA-5 provider execution uses the accepted `WindowsOwnedProcessController` + `SupervisedExecutionService` + durable execution records/artifacts. Raw subprocess probes are not a production provider path.

**Lesson:** timeout is not process ownership. Long-horizon agent CLIs need supervised identity, durable PID/evidence and recovery semantics before retry or cleanup.

**Verify:** supervised GLM attempts produced durable execution IDs/PIDs and terminal states; failures were classified as controlled provider/tool errors rather than orphaned execution claims.


---

## #22: Safety-authority refactors must migrate test callers before claiming GREEN (2026-08-30)

**Symptom:** AHA-5 continuity files claimed the file bridge GREEN, but a fresh related regression run found seven tests still constructing `AgentChangeApplier` with the retired direct-lease calling convention.

**Root cause:** production correctly moved mutation authority to `lease_store.inspect_health(lease_id)`, while older test helpers still injected `WorkerLease` objects directly. The checkpoint summary advanced before the whole affected caller set was re-run.

**Fix:** keep the production lease-health boundary; migrate test callers to a health-reader/lease-id contract and rerun both the related suite and the CI-equivalent full suite.

**Lesson:** when an authority-bearing API changes, compile success or a narrow new test is insufficient. Search/migrate all callers and verify the affected regression set before durable SSoT says GREEN.

**Verify:** related AHA-5/lease/supervised suite = 122 passed; CI-equivalent full suite with project dependencies = 1687 passed, 1 environment skip, 0 failed.


---

## #23: One parallel runner exception must not erase sibling batch outcomes (2026-08-30)

**Symptom:** the first AHA-6 executor draft called `future.result()` directly while collecting a parallel batch. One runner exception would raise out of the entire batch collector even though sibling tasks had already been leased/dispatched, making the returned batch state incomplete and tempting a caller to replay work blindly.

**Root cause:** execution fan-out was concurrent, but fan-in error collection still used all-or-nothing exception semantics instead of per-task recovery semantics.

**Fix:** collect each future independently. A failed runner becomes `RUNNER_RECOVERY_REQUIRED` with a bounded reason code; no internal retry occurs, and the active lease remains authoritative for later reconciliation. Successful siblings still return their own outcomes.

**Lesson:** parallel fan-out requires failure-isolated fan-in. Once work may have started, a collector exception is not permission to forget sibling state or retry the batch. Preserve per-task evidence/ownership and reconcile uncertain lanes individually.

**Verify:** focused AHA-6 tests cover runner exception -> recovery-required, exactly one runner call, active lease retention, stable sibling outcomes, plus real two-task concurrent dispatch. Focused suite = 13 passed; related scheduler/dispatch/chaos/lease/provider/harness regression = 193 passed.


---

## #24: Generated agent task packets must be re-read before dispatch (2026-08-30)

**Symptom:** the first ignored AHA-6 GLM review task was generated through a PowerShell double-quoted here-string. Markdown backticks altered interpolation/escape behavior: identity variables were written literally and the result path was split, even though the shell command itself succeeded.

**Root cause:** task generation trusted shell-template success instead of treating the generated packet as an execution-authority artifact requiring deterministic post-write verification.

**Fix:** discard the malformed packet before dispatch; regenerate it with an explicit UTF-8 writer; re-read the packet and verify literal worktree, branch, exact HEAD, source/test SHA256 values and result destination. Keep task/result under ignored `runs/` and leave tracked SSoT unchanged by the external reviewer.

**Lesson:** generated prompts/task packets are code-like authority, not prose. Never dispatch merely because generation returned exit code 0. Re-read exact fields, hash the packet, and fail closed on unresolved placeholders, broken paths or encoding damage.

**Verify:** the corrected `aha6-glm-review-001` packet contains exact identity values and SHA256 preconditions, has a stable packet SHA256, is gitignored, and the worktree remains clean before human/provider dispatch.

---

## #25: Defensive lease invariant raises can erase sibling batch evidence (2026-08-30)

**Symptom:** independent GLM-5.3 review found that a malformed `LEASED` broker outcome could raise from the AHA-6 acquisition loop after earlier sibling leases were already acquired. The whole batch then returned no structured result for those siblings.

**Root cause:** impossible-by-contract lease states were handled with batch-wide exceptions inside fan-out admission instead of the same per-task recovery vocabulary used for runner uncertainty.

**Fix:** `LEASED` without a lease now becomes `LEASE_RECOVERY_REQUIRED / LEASE_RECORD_MISSING`; selected-worker drift becomes `LEASE_RECOVERY_REQUIRED / LEASE_WORKER_DRIFT`. Both retain the broker outcome and continue fan-in so valid siblings still execute. Unknown future lease outcome kinds fail closed as `LEASE_OUTCOME_UNSUPPORTED` rather than raw `KeyError`.

**Lesson:** defensive checks inside a parallel admission loop must preserve already-acquired ownership/evidence. An invariant violation may prove the current lane unsafe, but it must not erase sibling state or silently create replay pressure.

**Verify:** RED tests reproduced both batch-wide raises. Repair focused suite = 16 passed; related scheduler/dispatch/chaos/lease/provider/harness/AHA-5 regression = 196 passed. Full local suite after repair = 1698 passed, 5 skipped, with only the two pre-existing GPU/OpenGL/Tcl environment failures outside AHA-6 scope.


## #26: Malformed private path config must not escape as a decoder exception (2026-08-30)

**Symptom:** WO-P1-114 adversarial test wrote invalid UTF-8 to A-Wiki `.drive-path`; provider runtime setup leaked raw `UnicodeDecodeError` instead of falling through to the next approved Drive locator.

**Root cause:** the new path resolver treated filesystem I/O failure as untrusted configuration input but caught only `OSError`; text decoding failure was left outside the fail-closed boundary.

**Fix:** catch `UnicodeError` together with `OSError` when reading `.drive-path`. A malformed locator contributes no path authority, so resolution continues to the next approved source/fallback without exposing file contents.

**Lesson:** configuration-file readability includes decoding. Any external/private locator used as execution authority must convert both I/O and decoding failures into bounded fail-closed behavior rather than leaking parser/codec exceptions.

**Verify:** `test_malformed_drive_path_file_falls_through_without_decode_leak`; WO-P1-114 focused suite `15 passed` and related regression `211 passed`.

## #27: Explicit private-source intent and persisted provider corruption must fail closed (2026-08-30)

**Symptom:** GPT trust-boundary review found two silent-authority hazards in WO-P1-114: an invalid explicit `A_WIKI_DRIVE_PATH` could fall through to another source, and a corrupted provider row could leak a raw configuration `ValueError`.

**Root cause:** ordered fallback logic did not distinguish an explicit operator override from discovery candidates, while the SQLite runtime resolver assumed persisted rows would always decode into valid typed provider objects.

**Fix:** an explicit Drive override is authoritative—invalid means `AWIKI_DRIVE_ROOT_UNAVAILABLE`, never fallback. Provider/endpoint decode errors from persisted state become unusable provider state (`None`) so execution fails closed through the existing provider gate.

**Lesson:** explicit configuration intent outranks discovery fallback, and persisted control-plane data is untrusted at decode time. Neither source-selection drift nor corrupt durable metadata may silently become execution authority.

**Verify:** `test_invalid_explicit_drive_override_fails_closed_instead_of_falling_back` and `test_corrupt_provider_row_fails_closed_as_unusable_state`; focused WO-P1-114 `17 passed`, related regression `224 passed`.

## #28: Provider admission boundaries must isolate malformed authority results per task (2026-08-30)

**Symptom:** adversarial WO-P1-115 tests showed that an injected admission authority could raise an unexpected exception, return a malformed object/future outcome kind, emit a control-character reason code, or return `ADMITTED` with an invalid record. Several variants could crash the batch or let a runner start before the malformed admission was rejected.

**Root cause:** admission acquisition was atomic, but the consumer trusted adapter result shape/reason/record after the call returned. Defensive validation happened too late or not at all.

**Fix:** convert acquire/release exceptions to bounded typed recovery, validate `ProviderAdmissionResult` and enum kind before use, validate admission-record type before lease/runner, sanitize reason codes, and continue collecting sibling outcomes. Unknown/malformed authority state is never replay permission.

**Lesson:** an authority interface is untrusted at both exception and return-value boundaries. In parallel fan-out, every malformed authority result must fail closed for that lane while preserving sibling evidence.

**Verify:** focused tests cover unexpected acquire/release exceptions, malformed object, future kind, unsafe reason code, invalid record and sibling preservation; final focused suite `59 passed`, related regression `253 passed`.

## #29: Durable expiry must be parsed before provider capacity is computed (2026-08-30)

**Symptom:** corrupt `expires_at='not-a-time'` in an ACTIVE provider admission did not raise; SQLite lexical comparison left it active and the next task received `PROVIDER_CAPACITY_EXHAUSTED`, hiding durable-state corruption as ordinary load.

**Root cause:** expiry reconciliation compared raw TEXT timestamps inside SQL before typed decode. A malformed timestamp therefore participated in capacity calculation without proving valid time authority.

**Fix:** inside the same `BEGIN IMMEDIATE` transaction, read and decode every ACTIVE admission first, fail typed on corrupt/naive time, then expire validated records and calculate remaining active capacity from parsed UTC datetimes.

**Lesson:** persisted timestamps that control ownership/capacity are untrusted data. Parse and validate before ordering/comparison; never let lexical storage representation become lifecycle authority.

**Verify:** corrupt active expiry now raises `PROVIDER_ADMISSION_RECORD_INVALID`; normal expiry and concurrent admission tests remain green.

## #30: Secret-bearing quota probes require exact origin pinning and bounded evidence semantics (2026-08-30)

**Symptom:** RED tests proved three credential/evidence hazards in the initial Z.ai quota adapter: urllib followed a 302 while carrying Authorization, `/api/anthropic-evil` and non-default TLS port were accepted as route lookalikes, and `NaN` quota values could become an `OK` snapshot.

**Root cause:** endpoint recognition used a prefix, default urllib redirect behavior was left enabled, and numeric validation checked only type/non-negativity rather than finiteness.

**Fix:** exact first-party hostname + Anthropic path subtree + default 443 only; redirects disabled; no credential resolution for unsupported routes; finite-number validation; incomplete/no-reset quota remains unavailable.

**Lesson:** once a probe carries a secret, hostname resemblance and HTTP convenience behavior are insufficient. Pin the intended origin/route, forbid credential-bearing redirects, and treat remote numeric evidence as untrusted until structurally complete and finite.

**Verify:** local redirect server receives Authorization only on the original request; lookalike path/8443 never resolve the secret; non-finite quota fails closed; final focused/related suites are green.

## #31: Ambiguous quota-window evidence must not be promoted to a five-hour snapshot (2026-08-30)

**Symptom:** independent WO-P1-115 GLM review found that a unitless legacy TOKENS_LIMIT item could be selected before an explicit 5h item, and internally contradictory limit/used/remaining values could still become an OK quota observation.

**Root cause:** the first parser returned the first legacy-compatible TOKENS_LIMIT candidate and validated quota fields independently rather than proving one unambiguous 5h window and a self-consistent tuple.

**Fix:** prefer exactly one explicit `unit=3, number=5` candidate; reject multiple explicit or multiple unitless legacy candidates; allow the legacy shape only when it is the sole TOKENS_LIMIT candidate; reject used/remaining values that exceed the limit or disagree with the limit outside a small rounding tolerance.

**Lesson:** remote quota evidence is execution authority. A compatibility fallback may be used only when it is unambiguous; independently plausible fields are insufficient if the tuple contradicts itself.

**Verify:** RED tests reproduce explicit-vs-legacy misselection, ambiguous unitless candidates and inconsistent tuples; repaired focused suite `62 passed`, related regression `256 passed`, full local `1753 passed / 4 skipped / 2 known GPU dependency failures`.

## #32: Elastic expansion must consume scheduler eligibility evidence before capacity classification (2026-08-31)

**Symptom:** a production composition could see zero available workers and classify the plan as capacity exhaustion even when the task's gate/provider evidence was absent, allowing provisioning before the downstream executor rejected the task.

**Root cause:** elastic composition accepted the scheduler capacity output without proving the same gate/provider eligibility inputs that make that output authoritative.

**Fix:** `ProductionElasticWorkerExecutor` requires typed `NodeEligibility` evidence for every ready node before scheduling; missing/malformed evidence is typed recovery and dispatch-gate denial is folded into scheduler eligibility before capacity expansion is considered.

**Lesson:** capacity is meaningful only after non-capacity admission gates are proven. Autoscaling/elastic layers must never infer ?need more workers? from a plan assembled without the scheduler's complete eligibility evidence.

**Verify:** RED reproduced provisioning with missing eligibility; repaired focused/related suite is green and the provisioner receives zero calls for the missing-evidence path.

## #33: Provisioning reservations must be visible to worker candidate assembly with owner-scoped re-observation (2026-08-31)

**Symptom:** after a worker was provisioned but before its lease was acquired, generic candidate assembly could report the new worker as free, creating a race where another session might lease it first.

**Root cause:** lease evidence and provisioning-capacity evidence shared one SQLite file but candidate assembly consumed only active worker leases.

**Fix:** provisioning reservations are now part of the existing `SQLiteWorkerLeaseStore` authority and production candidate assembly reads them. `PROVISIONED`/`RECOVERY_REQUIRED` reserve the worker for generic observers; only the exact owner `(session_id, task_id)` may re-observe its own `PROVISIONED` worker. Successful handoff transitions to `CAPACITY`, which continues counting bounded extra capacity without permanently reserving the worker.

**Lesson:** a reservation that is invisible to the next admission layer is not an ownership boundary. Preserve reservation visibility across provision ? observe ? lease, with a narrow owner-scoped bypass rather than a global ignore.

**Verify:** owner/generic observation RED tests plus realistic fixed-pool E2E prove the worker is hidden from competing sessions yet schedulable by its exact provisioning owner.

## #34: Typed recovery output is insufficient unless ambiguous provisioning state is durably marked (2026-08-31)

**Symptom:** post-provision observation or broker failure returned `RECOVERY_REQUIRED`, while the durable reservation remained `PROVISIONED`, making operator/restart state indistinguishable from a healthy owner handoff.

**Root cause:** recovery vocabulary existed at the return boundary but was not reconciled into the SQLite capacity authority on every post-create failure path.

**Fix:** post-provision observation and broker failures best-effort transition the reservation to durable `RECOVERY_REQUIRED`; ambiguous state remains capacity-consuming and is never blindly retried.

**Lesson:** recovery is a durable state transition, not only a return code. If a process can restart between failure and operator action, the persisted authority must still explain why replay is unsafe.

**Verify:** RED tests assert both returned recovery code and persisted reservation state after observation/broker failure; cross-process capacity limits remain enforced.

## #35: Provider capacity must follow durable execution evidence, not elapsed time or return shape (2026-08-31)

**Symptom:** WO-P1-117 RED tests proved that a normal typed `GraphDispatchResult(RECONCILE)` was reported as `RUN_COMPLETED`, provider admission TTL alone freed capacity while execution outcome was unknown, malformed `EXECUTED` results without valid execution evidence were accepted, `EXISTING + FAILED` was reported as success, and `BLOCKED`/`OFFERED` action-state drift could release capacity without proving a non-executing state.

**Root cause:** the parallel executor treated every normal runner return as completion, while provider admission expiry treated elapsed wall-clock time as proof that no provider execution remained active. Typed graph-dispatch action/state/evidence consistency was not revalidated at the consumer boundary.

**Fix:** classify typed dispatch results into success, terminal non-success, or uncertainty; release provider admission only when durable evidence proves no active execution; retain uncertain admissions. ACTIVE or legacy EXPIRED rows continue consuming bounded provider capacity until exact-identity explicit release/reconciliation.

**Lesson:** timeouts and typed return objects are not completion authority. Capacity may be released only from durable, identity-bound post-execution evidence or a proven non-executing/terminal state; uncertainty must remain capacity-consuming and fail closed.

**Verify:** RED reproduced all four defects; spawned-process stale-capacity fencing stayed single-owner; impact-expanded provider/harness/lease/elastic regression = 210 passed before source freeze.

## #36: Credential-bearing child output must be sanitized before durable persistence (2026-08-31)

**Symptom:** a provider child could echo its credential to stdout/stderr. The returned `ClaudeCodeRunnerResult` was redacted, but durable `stdout.log` / `stderr.log` already contained plaintext bytes.

**Root cause:** the detached helper inherited durable file handles directly, while redaction existed only after artifact collection. The first streaming repair also used buffered `read(64 KiB)`, delaying output until EOF for long-running children. A later adversarial test proved another lifecycle hazard: a descendant can inherit the target pipe handles after the direct child exits, so an unbounded drain can wait forever for EOF.

**Fix:** credential-bearing children now use in-memory stdout/stderr pipes in `supervised_child.py`; a bounded streaming redactor handles cross-chunk matches and forwards only sanitized bytes to durable handles. `read1()` consumes available pipe bytes without waiting for EOF. After the direct child exits, drain completion has a finite budget; inherited descendant pipe-holds become `OUTPUT_CAPTURE_DRAIN_TIMEOUT` with no terminal result, and daemon capture threads cannot pin the helper process after fail-closed return. Oversized redaction values fail before launch.

**Lesson:** return-time redaction is not a persistence boundary. Secret-bearing subprocess output must be sanitized before the first durable write, with chunk-boundary tests and live-child/timeout evidence proving no write-then-scrub window.

**Verify:** real Windows child echo test, held-live durable-log test, timeout -> reattach test, fragmented-stream unit test, capture-failure no-result test; related supervised/native regression 120 passed after bounded-drain hardening.

## #37: Durable completion evidence must bind to the exact dispatched task and lease (2026-08-31)

**Symptom:** an independent post-merge WO117 review proved seven normal-return cases could release provider admission while the actual job remained `EXECUTING`: unsupported `None`/dictionary returns, internally consistent evidence for another job, and non-executing actions carrying contradictory nested execution evidence.

**Root cause:** the consumer validated parts of the typed result internally but did not bind the returned job to the current dispatch request and acquired worker lease. While provider capacity was held, non-`GraphDispatchResult` values also bypassed typed refusal and fell through to completion/release; the separate no-admission generic-runner seam was not provider-capacity authority.

**Fix:** every provider-admitted normal return now passes one fail-closed consumer policy. Unsupported shapes while provider capacity is held are recovery and keep that admission reserved; typed evidence must match job/project/work-order/max-attempt identity and canonical worker ownership; `EXECUTED` requires a real attempt plus successful matching execution evidence; `EXISTING`/`BLOCKED`/`OFFERED` reject any nested execution payload. When no provider admission authority exists, the older injected generic-runner contract still permits a non-`GraphDispatchResult` normal return to mean only that the runner stage completed; it is not durable lifecycle completion authority.

**Lesson:** internal consistency is not provenance. Provider-capacity completion/release authority must bind evidence to the exact operation being consumed; foreign-but-valid evidence and unknown return shapes while an admission is held remain uncertainty and keep capacity reserved. A no-admission generic runner may still report stage completion without becoming durable lifecycle authority.

**Verify:** current-main RED = 10 failures/1 positive control; after compatibility repair, full parallel suite = 57 passed and broader provider/store/runtime/graph/lease/candidate/elastic/Claude supervised regression = 284 passed; compileall/diff/UTF-8 gates PASS.

## #38: Recovery assertions are not decommission authority (2026-08-31)

**Symptom:** bounded elastic capacity could be freed without lifecycle evidence through three generic escape hatches: a caller boolean `worker_decommissioned=True`, `RECOVERY_REQUIRED -> RELEASED`, or `release_unstarted()` applied to a successful `CAPACITY` reservation. None proved the worker/capacity had actually been retired.

**Root cause:** recovery cleanup exposed assertion-shaped inputs and a generic state transition where the capacity authority required evidence. The API encoded intent to release, not provenance that release was safe.

**Fix:** ambiguous provisioning residue now remains consuming under stale reconciliation whether a worker id is bound or not. A bound worker requires typed decommission evidence; unbound ambiguous states require typed runtime-absence evidence because the worker may have been created before identity was durably persisted. New reservations use `PRE_PROVISION`, then atomically persist `PROVISIONING` before the provisioner is invoked. Only `PRE_PROVISION -> RELEASED` is a valid `release_unstarted()` path. Historical `ACTIVE`, `PROVISIONING`, `RECOVERY_REQUIRED`, and `CAPACITY` cannot be released through that generic path. The boolean escape was removed.

**Lesson:** booleans, elapsed time, missing worker ids, caller claims, and an `ACTIVE` label that spans both pre-start and post-create crash windows are not ownership/decommission evidence. Persist the lifecycle boundary *before* invoking side effects: only a durable `PRE_PROVISION` state proves provisioning has not started; once `PROVISIONING` is recorded, capacity remains fail-closed until stronger evidence exists.

**Verify:** prior RED tests prove the boolean escape, generic recovery-release bypass, and CAPACITY-retirement bypass. A later failover review reproduced `release_unstarted()` freeing an ambiguous unbound crash-window row while an orphan-worker marker still existed. The tracked RED failed before repair; after introducing `PRE_PROVISION -> PROVISIONING`, legacy `ACTIVE` and started `PROVISIONING` both refuse release while the true pre-provision positive control still releases. Current focused/related/frontier counts: 58 / 257 / 312 passed; full local = 1888 passed / 5 skipped / 2 known GPU environment failures. Exact-head independent review/CI remain required after commit.

## #39: Provider execution authority must remain identity-bound across every external-effect boundary (2026-09-01)

**Symptom:** WO-P1-118B adversarial review found multiple individually reasonable checks that did not compose into one execution authority: callers could supply security/generation directly instead of deriving them from the durable Task Contract; a second SQLite provider store could present the same provider/generation; Claude dedup identity omitted generation/security; admission records/releases were trusted by shape; provider configuration could change between checks and elastic provisioning; and one policy-denied sibling could prevent an otherwise eligible capacity-blocked node from expanding.

**Root cause:** policy, generation, provider-store identity, admission ownership and dedup identity were validated at separate seams but were not carried as one durable requirement/fence through admission -> provision -> lease -> credential resolution -> launch. Repeated reloads reduced stale windows but were not a linearization boundary.

**Fix:** derive `ProviderExecutionRequirement` from exact Task Contract bytes and canonical provider-DB identity; bind its digest/generation into operation and supervised runtime identity; require it in production parallel/elastic/Claude assembly; validate exact admission identity/status/expiry/generation and exact RELEASED evidence; ACTIVE provider admission fences profile/endpoint generation mutation; reserve that admission before elastic provisioning and reuse it through lease/runner; revalidate before secret and native launch; select eligible capacity-blocked siblings independently from policy-denied siblings without creating a second scheduler.

**Lesson:** repeated validation is not a fence. Security/configuration authority that crosses side effects needs one non-forgeable durable identity plus an ownership record whose lifetime spans the side effect. Dedup keys must include the same authority identity, and mixed scheduler outcomes must preserve eligible siblings rather than collapsing the whole batch to the strongest denial.

**Verify:** Task Contract/security/generation/DB identity tests, forged admission/release tests, generation mutation during provisioning, secret-time/launch-time drift, mixed denied+capacity sibling, runtime-profile dedup separation, and canonical Claude provider-DB mismatch all reproduce the unsafe boundary or fail closed after repair. Focused provider/parallel/elastic/Claude frontier reached 301 passing tests before the final full-suite/exact-head review gate.

## #40: Stable agent mailbox metadata is a prompt boundary, not ordinary display text (2026-09-01)

**Symptom:** WO-P1-122 deep audit proved that `task_id`, `provider_id`, and `model_id` could contain newline/backtick content and escape their Markdown inline-code fields in the stable external-agent mailbox, even though path fields and some other metadata were already hardened.

**Root cause:** mailbox rendering reused generic scalar validation for identity fields. Generic task/result data may tolerate broader text, but a value embedded into a human/agent instruction envelope has a stricter grammar and therefore a different trust boundary.

**Fix:** every Markdown-bearing mailbox scalar uses `_mailbox_text()` to reject CR/LF/backtick; agent IDs remain bounded slugs, absolute task/result/worktree paths are separately validated, task SHA is re-hashed before atomic replacement, and failed preflight preserves the previous mailbox bytes.

**Lesson:** prompt envelopes are executable coordination surfaces. Validate for the destination syntax, not only the source data type. Stable pointers may change contents atomically, but untrusted metadata must never be able to rewrite the instructions surrounding the pointer.

**Verify:** RED reproduced metadata injection; focused mailbox suite = 24 passed, integrator focused matrix = 115 passed, GLM adversarial review blocked 12 injection attempts and re-proved failed-publish preservation, exact-head CI `33495011125` and post-main CI `33498867661` are green.


## #41: Post-termination observation uncertainty may be re-observed, but termination authority must not be retried (2026-09-01)

**Symptom:** unrelated hosted-Windows CI runs intermittently returned `RECOVERY_REQUIRED` from a real owned-process stop even after exact-PID termination had succeeded; immediate re-runs passed without product changes.

**Root cause:** the stop path treated one post-termination `UNKNOWN` process observation as final ownership uncertainty. Windows CIM/process inspection can transiently fail or return incomplete facts after the exact target has already been terminated.

**Fix:** only after the exact-PID terminator returns success, remember `UNKNOWN` and continue re-observing inside the existing stop deadline. Never invoke termination a second time. `MISMATCH` remains immediate `PROCESS_EXIT_OWNERSHIP_UNCERTAIN`; persistent UNKNOWN remains recovery; unchanged exact PID metadata is still required before cleanup and is preserved on uncertainty.

**Lesson:** a transient observation failure after an already-authorized side effect is not permission to repeat the side effect. Re-observe boundedly when observation is side-effect free, but keep ownership-transition evidence fail closed and retain durable metadata until absence is proven.

**Verify:** RED reproduced `UNKNOWN -> STALE` failing too early; repaired focused suite = 28 passed, related matrices = 117 passed before commit and 90 passed recheck, real Windows lifecycle = 10/10 locally; GLM independently reran the real test 3/3 plus 9/9 adversarial cases; exact-head CI `33503763313` and post-main CI `33509029840` are green.


## #42: Operator reads must not inherit migration writes, lexical DB identity, or raw persistence payloads (2026-09-01)

**Symptom:** WO125 Ultra review and RED probes found four boundaries that could make a read-only Models & Agents view lie or leak: a relative control-DB path could drift after cwd change into a second empty SQLite authority; the existing snapshot read ran schema DDL plus `BEGIN IMMEDIATE`; malformed persisted JSON/URL/scalars escaped as raw exceptions; and raw observation provenance could carry endpoint/credential-like text into the operator row/repr.

**Root cause:** execution-oriented persistence helpers were reused as if they were a pure presentation read contract. Bootstrap/migration, database identity, typed corruption decoding, and UI-safe data minimization were separate concerns but had not been separated at the facade boundary.

**Fix:** canonicalize the control DB once at `DesktopControlService.open()`, retain one provider store, initialize it once, and make bulk provider listing use an existing-file read-only deferred transaction with fixed-count SELECTs. Single/list reads share a strict snapshot decoder; invalid generations keep their specific typed code, other participating corruption becomes code-only `PROVIDER_CONFIGURATION_CORRUPT` with raw decoder causes suppressed. Cross-DB injected facades are refused, and raw provenance is reduced to a safe category before crossing the operator facade.

**Lesson:** a screen that only reads data still participates in control-plane authority. Read paths must not create/migrate databases, acquire writer intent, reconstruct mixed-time state, silently collapse corruption to empty, or carry raw persistence text into UI/loggable objects. Canonical identity + one coherent read transaction + typed decoding + sink-safe projection are one boundary.

**Verify:** initial WO125 RED = 8 intended failures; deep bug hunt added cross-DB and cause-chain REDs plus strict nested integer validation; focused current suite = 92 passed; impact-expanded provider/runtime/elastic/Claude matrix = 267 passed; WAL interleaving proves all-old then all-new snapshots, never mixed; full local source checkpoint = 1966 passed / 4 skipped / 2 known optional-GPU dependency failures only. Exact-head external review/CI still gate merge.

## #43: Truthful operator UI must preserve invalid-but-observed scalar values (2026-09-01)

**Symptom:** WO126 deep bug hunt showed a provider row carrying `configuration_generation=0` and `PROVIDER_GENERATION_INVALID` was displayed as `generation=-`.

**Root cause:** presentation formatting used truthiness (`generation or '-'`) instead of distinguishing missing (`None`) from an observed invalid numeric value (`0`). That erased evidence precisely when the operator needed it most.

**Fix:** only `None` maps to the missing-value marker. Numeric values, including invalid zero, remain visible while `configured=False`, `runtime_ready=False`, and the typed readiness reason explain why they are invalid.

**Lesson:** presentation layers must not normalize invalid observed state into missing state. `missing`, `invalid`, and `not evaluated` are separate truths and must remain separate through the final UI sink.

**Verify:** RED reproduced `generation=0 -> generation=-`; repaired focused WO126 panel matrix passed with the zero value preserved and authorization/readiness still separated.
## #44: UI tests that mutate global language must restore it (2026-09-01)

**Symptom:** the new WO126 language-refresh test passed by itself but caused the later guide test to open `USER-GUIDE-EN.md` instead of the expected Thai guide.

**Root cause:** the test changed process-global i18n state to English and did not restore the previous language. The failure appeared only in the ordered impact suite, not the focused file.

**Fix:** capture `get_language()` before mutation and restore it in `finally`. The repaired impact matrix passes with the guide test after the new panel tests.

**Lesson:** deterministic tests must clean up process-global state. Focused green is insufficient when a test mutates language, environment, registries, caches, clocks, or other shared singletons.

**Verify:** ordered impact matrix reproduced the pollution as 1 failure / 117 passes; after repair the same matrix is **118/118 PASS**.

---

## #45: Opaque IDs are not chronology when millisecond timestamps tie (2026-09-02)

**Symptom:** WO131 reproduced an execution deduplication flake when two equivalent records had the same millisecond `created_at`; ordering by `created_at DESC, execution_id DESC` could select the older row solely because its opaque ID was lexically larger.

**Root cause:** the query used a deterministic but semantically false tie-break. Millisecond timestamps can collide, and an opaque execution identifier carries identity, not insertion chronology.

**Fix:** keep `created_at DESC` as the primary order and use same-table SQLite insertion chronology (`rowid DESC`) as the bounded tie-break where no durable monotonic sequence exists. The regression forces identical timestamps and deliberately reverses lexical execution-ID order so an ID-based repair cannot pass accidentally.

**Lesson:** deterministic ordering is not automatically truthful ordering. When selecting "newest," every tie-break must itself carry chronology authority; never substitute lexical order of UUIDs, hashes, opaque IDs, or names.

**Verify:** WO131 exact feature commit `554c2b1003d12cd211712393ecf61c034b1a8003` passed its focused/stress checks and exact-head CI before PR #180 merged. If future migrations, table rebuilds, copies, or other storage operations can make `rowid` unsuitable as durable chronology, introduce an explicit monotonic sequence instead of extending this workaround.

---

## #46: Missing review evidence must stay missing after an external merge (2026-09-02)

**Symptom:** PR #180 was merged externally before the planned independent GLM review result existed. Product evidence later remained strong, including green post-main CI, but the intended pre-merge review gate had not actually occurred.

**Root cause:** merge authority and review workflow were separate control surfaces. Once the PR merged outside the planned integrator sequence, later success could verify product state but could not retroactively create the missing review event.

**Fix:** reconcile durable SSoT to the facts: mark the change merged/post-main-green, explicitly record that the independent-review gate was missed, and continue from actual repository state. Never create, backdate, or paraphrase a nonexistent PASS result to make the process appear complete.

**Lesson:** evidence is historical authority, not a box to fill after the fact. A later test, review, or green main branch may reduce product risk, but it does not prove a prior gate happened. Preserve process deviations so future automation can distinguish "verified later" from "verified before merge."

**Verify:** PR #180 merged at main SHA `af7a933fe27d2a3e3f29360abf9214df1e5478c5`; post-main CI `33545560617` was green, while the prepared retrospective GLM result file did not exist. The closeout therefore recorded the missed gate instead of claiming GLM PASS.

---

## #47: Bounded evidence reads must order by canonical instants before LIMIT (2026-09-02)

**Symptom:** WO128 adversarial probes showed that recent-admission queries could return the wrong bounded window when timestamps differed by fractional seconds, timezone offset text, or sub-millisecond instants. Lexical ISO text and SQLite `julianday()` precision were both insufficient for exact newest-first evidence.

**Root cause:** LIMIT was being asked to choose rows before the persisted timestamp had been converted into the same semantic time domain used by the decoder. A deterministic SQL order can still be wrong when textual representation or numeric conversion loses instant authority.

**Fix:** register a connection-local deterministic SQLite function that decodes accepted aware timestamps through the canonical Python parser and emits fixed-width UTC microseconds before ORDER/LIMIT. Malformed or naive order-key timestamps receive a high sentinel so they enter the bounded window and fail typed instead of hiding beyond LIMIT. Same-instant ties use deterministic binary `admission_id` only after instant equality is established.

**Lesson:** a bounded evidence read is only truthful if semantic normalization happens before row selection. Do not apply `ORDER BY ... LIMIT` to timestamp text, coarse numeric conversions, or other storage encodings whose order is not identical to the domain order. Corrupt order keys must fail closed inside the selected window, not disappear behind it.

**Verify:** WO128 RED/GREEN covered whole/fractional seconds, timezone offsets, sub-millisecond ordering, same-instant offset ties, malformed/naive timestamps, bounded LIMIT behavior, and one-SELECT/read-only constraints. Repaired WO128 head `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad` passed focused `26`, provider/store/runtime `150`, broader execution/parallel `167`, exact-head CI `33586307363`, independent GLM review PASS, and post-main CI after PR #184 merge.

---

## #48: Persisted evidence decoders must revalidate writer invariants (2026-09-02)

**Symptom:** WO128 direct persistence probes inserted blank/whitespace `admission_id`, `provider_id`, `execution_id`, or `batch_id`, and an invalid persisted status. `list_provider_admissions()` decoded those rows as ordinary evidence instead of failing with a typed corruption error.

**Root cause:** the read decoder trusted constraints normally enforced by the writer/domain constructor. Persisted state can still be corrupted by old versions, manual SQL, disabled constraints, partial migrations, or external tooling; writer validation is not a durable read-time guarantee.

**Fix:** the canonical admission row decoder now revalidates all persisted identity fields with the same nonblank text contract and validates status against the exact durable enum set. Violations map to typed `PROVIDER_ADMISSION_RECORD_INVALID`; generation corruption keeps its more specific existing typed code. Projection code remains a consumer of store-typed records rather than duplicating persistence validation.

**Lesson:** durable storage is an untrusted boundary even when every current writer is strict. Any field whose invariant affects identity, ownership, authorization, ordering, or execution evidence must be revalidated while decoding persisted rows, with corruption mapped to stable typed errors. Database constraints and constructor checks are defense layers, not substitutes for read-boundary validation.

**Verify:** tracked RED added four blank-identity cases plus invalid persisted status and produced 5 expected failures before repair. After repair those 5 cases passed; focused WO128 = `26 passed`, provider/store/runtime impact = `150 passed`, broader execution/parallel consumers = `167 passed`, and the eventual merged tree remained green through exact-head and post-main CI.

---

## #49: UI helper-path tests do not prove real widget event wiring (2026-09-03)

**Symptom:** WO134 tests passed while an open Provider Evidence dialog stayed on the old provider after the operator changed the MODELS & AGENTS combobox. A pending old evidence read was invalidated, but no replacement read was submitted.

**Root cause:** the provider-switch test changed the combobox and then manually called the Evidence-opening helper. Production `<<ComboboxSelected>>` was wired only to generic action-control sync, so the test bypassed the actual event contract. Completed cache was never invalidated; pending state was invalidated without transferring evidence ownership or starting the new provider fetch.

**Fix:** bind the real provider selection event to a bounded handler that first syncs controls, then—only when the Evidence window is already open and the selected provider actually changed—invalidates stale request/cache state, transfers the dialog owner/title, renders loading, and submits one background replacement fetch. Existing request-generation guards discard late old futures; selecting the same provider does no extra I/O.

**Lesson:** interaction tests must enter through the same event surface the operator uses. Calling a downstream helper after manually changing widget state can hide missing bindings and stale async ownership. For stateful dialogs, selection identity, request generation, cache identity, and visible title/content must move together.

**Verify:** WO143 added three RED tests using real `event_generate("<<ComboboxSelected>>")`: completed-cache switch, pending-future replacement/late-result discard, and rapid switch latest-wins plus same-provider no-op. All three failed before production repair and passed after it; the related panel/control/i18n/graph matrix passed 145/145 and the real-event focused set passed 10 consecutive iterations.
---

## #50: A timed-out mutation wrapper is an ambiguous side-effect outcome, not proof that the target is still alive (2026-09-03)

**Symptom:** after WO140 added stop diagnostics, PR #195 Windows CI failed `test_real_dummy_process_start_idempotent_stop` with `RECOVERY_REQUIRED / PROCESS_STOP_FAILED`, `elapsed_ms=5266.0`, `pre_termination_ownership=OWNED`, `terminate_called=True`, `terminate_returned=False`, and zero post-termination observations. The exact rerun passed without a product change.

**Root cause:** `WindowsExactPidTerminator` uses bounded PowerShell `Stop-Process`. Timeout/OSError/nonzero are collapsed to boolean `False`, while `WindowsOwnedProcessController.stop()` treated every `False` as definitive termination failure and returned immediately. A wrapper timeout does not prove whether the already-authorized exact-PID side effect happened before the wrapper exceeded its wall-clock budget.

**Fix:** never retry termination. After a failed/ambiguous terminator result, re-observe the exact PID exactly once using the existing side-effect-free ownership observer. `OWNED` remains `PROCESS_STOP_FAILED`; `UNKNOWN` or `MISMATCH` remains fail-closed as `PROCESS_EXIT_OWNERSHIP_UNCERTAIN`; only proven `STALE` may continue through the existing unchanged exact-PID metadata check before cleanup.

**Lesson:** when a mutation transport/wrapper times out, separate “command outcome unknown” from “side effect definitely failed.” Never replay a non-idempotent side effect merely because the wrapper timed out. First use bounded observation to recover truth; cleanup still requires the original exact identity evidence.

**Verify:** RED = 4 intended failures before repair; repaired owned-process suite = 40 passed, observer/runtime matrix = 86 passed, supervisor lifecycle matrix = 74 passed. A real-Windows ambiguity probe used the real exact-PID terminator once and deliberately returned `False` after successful termination: 15/15 STOPPED with STALE proof and no second kill. Normal real-Windows lifecycle stress = 30/30. Exact-SHA independent review and hosted CI remain release gates.


---

## #51: Broad search over live ZCode state can lock `config.json` and break atomic provider writes (2026-09-03)

**Symptom:** ZCode repeatedly logged `EPERM: operation not permitted, rename ...tmp -> ...\.zcode\v2\config.json`, followed by `Timed out ... waiting for the ZCode file lock` / `EEXIST ... config.json.lock`. Provider/session reads degraded and the UI could appear stuck reconnecting.

**Root cause:** a separate Desktop Commander Node.js process held `%USERPROFILE%\.zcode\v2\config.json` open while ZCode was performing an atomic temp-file replacement. The incident timeline also showed a broad Desktop Commander content search traversing `.zcode\v2` and reading both `config.json` and ZCode temp files during the same failure window. Windows Restart Manager identified exact holder PID `15728` as `@wonderwhy-er/desktop-commander`. This was cross-process file-handle contention, not JSON corruption, Git state, or a ZCode read-only permission problem.

**Fix:** prove the exact holder first, stop only the identified Desktop Commander child PID, then re-observe the file before any other mutation. After the targeted stop, exclusive `ReadWrite` + `FileShare.None` open succeeded; no `config.json.lock` directory or orphan `config.json.*.tmp` remained; JSON parsing passed; and no new ZCode lock/rename error appeared in the following verification window. No broad `node.exe` or ZCode kill was used.

**Lesson:** mutable application state directories are live synchronization boundaries. Do not recursively search/index `%USERPROFILE%\.zcode\v2` while ZCode is running. A read-oriented tool can still create availability failures if it retains a Windows handle across another process's atomic replace. Prefer a direct single-file read, targeted log query, or a copied snapshot. Never infer that a `.lock`/`.tmp` artifact is stale merely because an operation timed out.

**Verify / recovery:** run `scripts/diagnose_zcode_config_lock.ps1`; if it reports `LOCKED`, identify the exact PID and owner before stopping anything. Re-run until `ZCODE_CONFIG_LOCK=UNLOCKED`, parse the JSON without printing it, then inspect the current ZCode log for new `EPERM` / `config.json.lock` errors. Full recovery procedure: `docs/runbooks/zcode-config-lock.md`; incident evidence: `docs/work-orders/WO-P1-153-zcode-config-lock-incident.md`.
