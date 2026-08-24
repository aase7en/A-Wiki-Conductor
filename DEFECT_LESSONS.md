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

## กติกาการเพิ่ม lesson ใหม่:

1. บันทึกเมื่อ: พบ defect ที่ผู้ใช้จริงรายงาน (ไม่ใช่แค่ test fail)
2. รูปแบบ: อาการ → root cause → วิธีแก้ → lesson → วิธีตรวจสอบ
3. ทุก Agent ต้องอ่านไฟล์นี้ก่อนแก้โค้ดใน `src/a_conductor/`
