# SundayFamily UX-1 Design Packet

Date: 2026-11-10 | Issue: #739 | Base: `16b897a` (supplied)
Status: TARGET-STATE PROPOSAL / OPERATOR GREEN-LIGHT PENDING
Claim: `UX1-739-DESIGN-001`, comment 6770451351.
WO: [UX-1 work order](../work-orders/WO-P1-739-UX1-sunday-family-dashboard.md).
Preview: [offline mockup](sunday-family-ux1-mockup.html).

## 1. Executive Summary

SundayFamily คือเป้าหมายโปรแกรมเดียวที่เปิดง่าย ติดตั้งง่าย และใช้ทรัพยากรอย่างประหยัด ให้ผู้ใช้สั่งงานด้วยภาษาธรรมชาติแล้วติดตามผลผ่าน dashboard ภาษาไทย ไม่ต้องจำชื่อ tool เอกสารนี้เสนอ IA เจ็ดส่วน ระบบสีสถานะและหลักฐานร่วมกัน wireframes และแนวทางย้ายความสามารถจาก Tk มาสู่ React ภายใน popup-browser shell โดยคง A-Sunday Conductor เป็น control plane เดียว แนะนำ launcher + WebView เป็นรูปแบบแพ็กเมื่อผ่าน feasibility/security gates พร้อม PWA เป็นทางเลือกสำรอง ทั้งหมดเป็นแบบเพื่อขอ operator green-light ไม่ใช่ฟีเจอร์ที่ทำงานแล้ว ไม่อนุมัติการเปลี่ยน runtime หรือเลิกใช้ Tk

## 2. Binding Inputs And Constraints

Charter, [#739 comment 6759816854](https://github.com/aase7en/A-Wiki-Conductor/issues/739#issuecomment-6759816854):

> เปิดเลน UX/UI เป็นการออกแบบ Sunday family 1 ตัวที่คล้าย dashboard จัดการโดยรวมของทุกอย่างในโปรเจ็ค และติดตามการทำงานของ SundayMCP การใช้ tool การตั้งค่า hook + skill + batch และ AI ตัวเล็กๆ ช่วยตัดสินใจเร็วๆ อย่าง Jev AI

Usage philosophy (verbatim operator input):

> ผู้ใช้ทั่วไปมีหน้าที่สั่งงานเป็นภาษาธรรมชาติแล้วรอผลลัพธ์สมบูรณ์ — เครื่องมือทั้งหมด (รวมถึง sunday_semantic_rename) เป็นความสามารถฝั่ง AI Agent ที่ผู้ใช้ไม่ควรต้องเรียกหรือจำชื่อเอง หน้า UI ต้องสะท้อนสิ่งนี้: แสดงสถานะ/หลักฐาน/การตั้งค่า ไม่ใช่การ invocate เครื่องมือ

Addendum 2, [comment 6765523868](https://github.com/aase7en/A-Wiki-Conductor/issues/739#issuecomment-6765523868):

> ฉันต้องการรวมเป็นแค่ 1 โปรแกรมแบบใช้งานง่าย ติดตั้งง่าย ถ้าอนาคตฉันเผยแพร่ผ่าน GitHub เป็นแพ็กรวมชื่อ SundayFamily ให้หน้าโปรแกรมเปิดได้ง่าย ทำงานเร็ว เบาเครื่อง อาจจะเป็นรูปแบบ popup browser เหมือนของ Serena (ระบบเว็บใน desktop)

- Read-only-first: สถานะ/หลักฐานมาก่อน controls; UX-1 ไม่มี Run Tool หรือ arbitrary command box
- Natural-language intent ในอนาคตต้องใช้ authority path เดิม; ไม่สร้าง chat executor/store ใหม่ใน browser
- ไม่แสดง secrets รวม tunnel IDs; อนุญาตเพียง `tunnel_configured` boolean
- UNKNOWN/STALE/DEGRADED ไม่ใช่ healthy; timestamp/provenance/reason ต้องไม่ถูกซ่อน
- Actions ใน slice ภายหลังผ่าน Command Gateway + current claim/identity/version/safety/replay checks เท่านั้น
- `accepted` ไม่เท่ากับ executed/completed; ไม่ยืนยันผลก่อน authoritative receipt
- JEV เป็น READ_ONLY advisory ไม่อนุมัติ claim, retry, merge หรือ completion
- Browser/shell ไม่เป็น SSoT ไม่เรียก SRM mutation ตรง และไม่เป็น control plane ที่สอง
- Runtime boundary [contract](../contracts/sunday-family-web-runtime-boundary-v1.md): roles `:10-20`, read/command/evidence `:47-78`, auth/cache `:80-100`, packaging/retirement `:102-117`
- Token ไม่อยู่ใน page bytes/URL/log/error; mockup ไม่มี token จริงหรือช่องรับ token

Visual continuity: รักษา near-black, thin borders, dense diagnostics และ monospaced
identifiers ตาม `DESIGN.md:14-23,158-165`. ข้อจำกัด Tk-only/English-only ใน
`DESIGN.md:8,102-120` เป็นบริบทเดิม; ทิศทาง web ระยะยาวมาจาก roadmap
`2026-09-26-sunday-family-web-pwa-roadmap.md:10-23,183` และ Thai-first/single-app
จาก operator ข้างต้น ไม่แก้ authority ของเอกสารเดิมในเลนนี้

## 3. Current State Synthesis

หลักฐานอ้าง [surface audits](2026-11-10-ux1-surface-audits.md) รหัส T/M/W;
รหัสเหล่านี้ชี้กลับไปยัง file:line หรือ file-level anchors ของ audit ไม่ใช่ runtime checks ใหม่

| Surface | มีแล้ว | ช่องว่างที่ห้ามกลบ | Anchor |
|---|---|---|---|
| Tk desktop | OS onboarding, diagnostics, lifecycle, help | Worker-era UI + Tk-only OS capabilities; retirement ยังไม่ผ่าน | Audit T1-T5; `desktop_ui.py:1287-2349,3066-3354` |
| Monitor + Inspector | Bounded pure projections, real read-only collectors, legacy HTML | ไม่มี production provider wiring / Inspector route | Audit M1-M3; `monitor_page.py:137-174`, `inspector_sources.py`, `web_api.py` |
| React | Lanes, session connectors, metrics, SSE, PWA | ไม่มี production static serving; fleet/usage/settings/Jev ยังไม่มี | Audit W1-W4; `web/sunday-family/src/`, `web_api.py` |

ห้ามนำ session connector list มาแสดงว่าเป็น persisted Tk registry หรือ fleet
(audit W2/W3; `web_api.py` GET `/connectors`). พร้อมใช้งานทั้งระบบต้องไม่สรุป
จาก health chip ตัวเดียว (`web_api.py` GET `/api/v1/health`, audit W3)

## 4. Target Information Architecture

Legend: EXISTING = มี seam บางส่วนจริง; PARTIAL = ต้องต่อข้อมูล/ปรับ UI;
NEW = target ยังไม่มี. “หลัง slice 2” ไม่ได้หมายความว่า source อื่นเกิดขึ้นอัตโนมัติ
สถานะทุกหน้าเป็น target; operator ไม่ต้องรู้ชื่อ tool เพื่อใช้งานประจำวัน

| Thai-first nav / status | Purpose + key blocks | Data today → หลัง slice-2 wiring | v1 read-only boundary |
|---|---|---|---|
| ภาพรวม (Overview), PARTIAL | เห็นงานค้าง/ติดขัดและหลักฐานล่าสุด; fleet strip, lane summary, Inspector summary, metrics, activity, Jev preview | Snapshot lanes/metrics/SSE (W3) → Inspector provider + sanitized notes; activity/Jev absent ยัง UNKNOWN | อ่าน normalized snapshots; ไม่มี start/retry หรือ infer completion |
| ทีมเครื่อง (Fleet), NEW | SundayMCP Windows/Mac; per-device identity, observation time, transport state, capability evidence, recovery reason | Session connectors ไม่ใช่ fleet (W3) → ต้องมี accepted device DTO/aggregation seam แยกจาก local Inspector; Mac ไม่มี source ให้ UNKNOWN | แสดงสถานะเท่านั้น; ไม่ start/stop, rebind, pairing หรือ delete |
| งานและเลน (Work & Lanes), PARTIAL | Project grouping, lanes, owner/claim/HEAD, blocker, gates, evidence receipt | Cockpit lanes identity/state/markers/blocker/gates/origin_display (W3) → ใช้เดิม; project/claim/roadmap joins ต้อง child DTO | Missing owner/HEAD/claim = ไม่ทราบ; ไม่แก้ claims/schedule |
| เครื่องมือและการใช้งาน (Tools & Usage), NEW UI / EXISTING seam | Inspector Tools/Hooks/Skills, phase/class/routing metadata, provenance, timestamps, retained counts, truncation; usage region | Collectors ยัง test-only (M2/M3) → wire provider + proposed versioned Inspector endpoint; usage event source ยังไม่มี | Read-only diagnostics; no Run/Rename/Invoke; inventory ไม่ใช่ usage history |
| ตั้งค่า (Settings), NEW web | Hooks/skills/batch/allowedDirectories/Second Brain/language; provider admission panel | Tk preferences/brain (T3), no web settings (W2) → slice 2 ไม่สร้าง settings DTO; UX-3 ค่อยอ่าน safe effective config | Preview effective policy/provenance; ไม่มี Save/Install หรือ local browser policy authority |
| Jev (มุมตัดสินใจเร็ว), NEW | Evidence-grounded short advice, alternatives, missing evidence, confidence เฉพาะที่ source ให้ | ไม่มี Jev UI/source (W2) → ยังรอ advisory contract/DTO ใน UX-3 | READ_ONLY; ไม่ให้ authorization; unavailable แสดง UNKNOWN |
| บันทึกกิจกรรม (Activity & Logs), PARTIAL | Timeline, filtered safe log projection, source + timestamp, recovery/unknown outcomes | React placeholder; mutation audit route มีแต่ UI ไม่เรียก (W2/W3); Tk logs (T2) → safe event/log DTO ยังต้องแยก WO | อ่าน sanitized records; SSE connected ไม่ใช่ progress/accepted result |

Projects/Executions/Roadmap/Claims จาก prior roadmap `:82` รวมใน Work & Lanes;
Hooks/Providers/Runtime รวม Inspector/Settings/Fleet แทนเพิ่มเมนูย่อยแยกมากเกินไป
นี่คือ grouping proposal ไม่ใช่การลบ authority หรือ roadmap responsibilities

## 5. Text Wireframes (Target-State)

ตัวเลขและข้อความใน wireframes/mockup เป็น SAMPLE DATA เท่านั้น
ทุก panel จริงต้องมี source + observed-at; ไม่มี timestamp ให้แสดง “ไม่ทราบเวลา”
Parent failure ต้องแสดง badge + reason ไม่ซ่อน child cached state ว่าเป็นข้อมูลสด

### Overview

```text
+ Nav 7 items + SundayFamily / ภาพรวม + session status (not token) +
| SAMPLE DATA: ยังไม่ใช่ข้อมูลจริง                                  |
| ทีมเครื่อง: Windows [READY] | Mac [READY] | เวลา/แหล่งหลักฐาน       |
| งานและเลน                       | Inspector                      |
| count by authoritative state    | Tools / Hooks / Skills         |
| lane / blocker / gates / source | retained counts + dropped note |
| UNKNOWN if source absent        | [UNKNOWN] no inspector evidence|
| การใช้งาน tool: ยังไม่มี source | Jev: READ_ONLY / ยังไม่มีคำแนะนำ |
| กิจกรรมล่าสุด: timestamp + source + sample label                 |
+----------------------------------------------------------------+
```

### Fleet

```text
ทีมเครื่อง / Fleet                      [อ่านอย่างเดียว]
Windows  [READY]         Mac [UNKNOWN]
source: health evidence source: ยังไม่มี device projection
observed-at: <time>     observed-at: ไม่ทราบเวลา
tunnel_configured: yes reason: ไม่มีหลักฐานการเชื่อมต่อ
capabilities: evidence reference, not inferred readiness
Recovery: sanitized reason / next safe observation
ไม่มี Start / Stop / Pair / Rebind / Delete buttons ใน v1
```

### Tools & Usage

```text
เครื่องมือและการใช้งาน                    [อ่านอย่างเดียว]
[UNKNOWN] ไม่มีหลักฐาน Inspector / INSPECTOR_NOT_PROVIDED
หรือเมื่อมี projection ที่ valid:
Tools  name | [READY] | phase: CONNECTED (metadata) | provenance
Hooks  name | [UNKNOWN] | contract-only | source + observed-at
Skills name | [AVAILABLE] | registry-only | deprecated/duplicate
แสดง 128 รายการที่คงไว้; truncated=true; dropped=12 (ตัวอย่าง)
counts = retained rows เท่านั้น; ทั้งหมดในระบบ: ไม่ทราบ
Usage: ยังไม่มี event source; ไม่สร้างกราฟจำนวน calls จาก inventory
Failure: [DEGRADED] INSPECTOR_PROJECTION_INVALID (ไม่ render healthy)
```

### Settings

```text
ตั้งค่า                               [effective config / read-only]
Hooks | Skills | Batch | Allowed directories | Second Brain | Language
ค่า: ไม่ทราบ   source: ยังไม่มี safe settings projection
Allowed directories: safe approved paths only / hidden if sensitive
คำอธิบาย: เส้นทางที่อนุญาตต้องมาจาก server policy ไม่ใช่ browser
Models & Agents: trust class / egress / concurrency / evidence
ไม่มี API key, Tunnel ID หรือ credential reveal/copy
UX-3 แสดง preview; editor ต้อง separate Gateway + claim review
```

### Jev Corner

```text
Jev / มุมตัดสินใจเร็ว                   [READ_ONLY advisory]
[UNKNOWN] ยังไม่มีคำแนะนำที่มีหลักฐาน
เมื่อ source พร้อม: ข้อเสนอ / เหตุผล / evidence refs / observed-at
ทางเลือก + missing evidence + confidence (เฉพาะจาก source)
คำแนะนำไม่ใช่คำอนุมัติ และไม่เปลี่ยน task/claim/completion
ไม่มี Execute / Auto-approve / Retry buttons
```

## 6. Design System

### Tokens And Typography

| Token | Value | Usage |
|---|---|---|
| `bg` / `surface` / `surface-raised` | `#0b0f14` / `#111820` / `#17212c` | Canvas / cards / table heads |
| `border` / `text` / `muted` | `#2b3948` / `#edf2f7` / `#a5b4c3` | Thin separators / body / helper |
| `accent` / `focus` | `#9bc5ff` / `#b8d7ff` | Navigation/link/focus, never health |
| `ready` / `available` | `#8f8` / `#8f8` | EXACT monitor semantic foreground |
| `unknown` / `stale` | `#fc6` / `#f96` | EXACT monitor semantic foreground |
| `degraded` / `disconnected` | `#f66` / `#c9f` | EXACT monitor semantic foreground |

StateBadge background = `surface`; foreground/border = exact state token.
ไม่มีลด opacity ที่ทำให้ semantic foreground เปลี่ยนสี; ไม่ใช้ green กับ sample/auth/gate chip
Typeface: `system-ui, 'Segoe UI', 'Leelawadee UI', sans-serif`;
identifiers/logs: `ui-monospace, Consolas, monospace`. Thai body 15px/1.65,
helper 13px/1.6; H1 24-28px/1.4, H2 18px/1.5, H3 16px/1.5 ตาม mockup CSS;
ไม่ใส่ letter-spacing กับข้อความไทย
Spacing 4/8/12/16/24/32px; card padding 20-24px; radius 8px; border 1px
ไม่มี GPU logo/continuous animation/external font; performance claims ต้องวัดภายหลัง

### Components

| Component | Specification |
|---|---|
| StateBadge | Enum + Thai meaning + reason nearby; never color-only; READY กับ AVAILABLE label ต่างกันแม้สีเดียวกัน |
| Card | H2/H3, source/observed-at, optional failure strip; whole card ไม่ clickable ถ้าไม่มี destination |
| DataTable | Semantic caption/th scope; identity wraps; status/reason visible; horizontal scroll เฉพาะตารางไม่ใช่ทั้งหน้า |
| NavItem | Thai first + English helper, `aria-current=page`, focus outline; no fake active interaction |
| EmptyState | UNKNOWN + “ไม่มีหลักฐาน” + source/reason; empty list ไม่เท่ากับศูนย์ inventory |
| TruncatedNote | Retained count + dropped + `truncated`; sticky ต่อ section ไม่หายเมื่อ filter; missing dropped = ไม่ทราบ |
| ReasonLine | Sanitized code/plain-text explanation; provenance + observation time; never raw exception/HTML |

Desktop ≥1280px: 224px nav + 2-column cards; 900-1279px: compact nav/grid;
<900px: nav อยู่ด้านบน cards stack; 390px ต้องไม่ clip Thai/gates/status
Keyboard order ตาม DOM, visible focus, 44px navigation hit area; text selection ได้;
reduced-motion default; future updates use polite announcements for meaningful changes only

### State Matrix

| State | Exact color | Operator label | When shown / restriction |
|---|---|---|---|
| READY | `#8f8` | พร้อมตามหลักฐาน | Valid health observation; scope+time visible, not whole-project completion |
| AVAILABLE | `#8f8` | พบ skill ใน registry และ path | Skills only; ไม่ใช่ runtime READY/permission |
| UNKNOWN | `#fc6` | ยังไม่มีหลักฐานยืนยัน | Missing source/time/unknown enum, hook contract-only, unavailable Inspector |
| STALE | `#f96` | หลักฐานเก่า | Source freshness exceeded; cached READY must not retain a live-green badge |
| DEGRADED | `#f66` | ข้อมูลหรือการตรวจมีปัญหา | Invalid projection/nontransport probe failure; code-only reason |
| DISCONNECTED | `#c9f` | ขาดการเชื่อมต่อ | Supported transport-error evidence, not any exception |

Bounds/state provenance: audit M1-M3 (`monitor_page.py:137-174`,
`inspector_projection.py`, `inspector_sources.py`). ToolPhase
REGISTERED/STARTED/CONNECTED/INJECTED/UNKNOWN เป็น plain metadata เท่านั้น;
INJECTED ไม่ให้สิทธิ์และไม่พิสูจน์ READY. Hook contract presence = UNKNOWN
Skill freshness ใช้ registry mtime default 7d ไม่ใช่ generated_at (audit M2)

Redaction: whole field แสดง literal `[REDACTED]` เป็น plain text ไม่มี tooltip,
DOM data attribute, hidden original หรือ copy-raw. ไม่ส่ง token/tunnel IDs ลง DTO
ก่อน redaction/truncation; collector notes ต้อง code-only และ safe display cap
128 rows/section, retained-only counts, explicit dropped/truncated; 4096 raw/200
display chars และ safe-int bounds คงตาม source contract (audit M3)

## 7. Shell And Packaging Feasibility

เป้าหมายคือแพ็กเดียวชื่อ SundayFamily ไม่ใช่บริการ/หน้าจอสามชุดแยกกัน
สิ่งที่มีจริง: React build ยัง unserved (`web_api.py`, audit W1);
portable/installer/frozen verification scripts ตาม `AGENTS.md:81-82` ไม่ใช่หลักฐานว่า
scripts ปัจจุบัน bundle web assets หรือ WebView runtime แล้ว

| Option | ประโยชน์ / ข้อจำกัด | Gate |
|---|---|---|
| A: WebView2/pywebview popup launcher over local `web_api` URL | ใกล้ popup-browser brief; ใช้ React ชุดเดียว; WebView2 เป็น Windows path, platform webviews ต้องพิสูจน์แยก; dependency/startup/RAM ยังไม่วัด | Launcher only start/attach, bounded readiness, exact service identity; no JS-native execution bridge; dependency/license/OS review |
| B: static `dist/` hosting in `web_api` | Necessary serving seam for bundled same-origin UI, not a shell by itself; no implementation today (W1) | จำกัด public carve-out เฉพาะ non-sensitive static shell; API/SSE ยัง authenticated; Host/Origin/CSP/asset traversal/cache tests ก่อนใช้ |
| C: installed PWA | Native-wrapper fallback และ browser-first experience; install UX/service worker มี seam (W1) แต่ไม่แก้ service lifecycle/static hosting | No API/auth/claim cache, clear offline state, manual token re-entry respected |

Recommendation: UX-4 ทดลอง B + A เป็น single-pack experience; C เป็น fallback
ถ้า WebView feasibility ไม่ผ่านให้ใช้ launcher เปิด URL/PWA แทน ไม่เพิ่ม native dashboard
WebView2/pywebview เป็น candidates ยังไม่เลือก library/version/dependency หรืออ้างรองรับ OS แล้ว
ห้าม bundled runtime ออกนอก accepted service boundary (`contract:102-104`)

Token handoff เป็น SECURITY-REVIEWED FOLLOW-UP ไม่ใช่ส่วนที่อนุมัติด้วย mockup:
current React `TokenGate` ใช้ sessionStorage แยกตาม origin/top-level browsing context;
fresh context ที่ storage ว่างจะแสดง prompt แต่ opener อาจคัดลอก sessionStorage มาเริ่มต้น
จึงไม่รับประกันว่า new window จะ re-prompt (audit W2);
legacy Monitor fragment auth เป็นคนละ flow (M1) ห้ามยกมาใช้กับ shell
ไม่ใช้ URL/file/stdout/HTML injection token handoff; ก่อนมี reviewed mechanism ให้คง
manual entry ใน auth gate เดิม ห้ามโฆษณา auto-connect หรือเก็บ token ใน mockup

Proposed pack checklist: web production build/assets + backend entrypoint + optional
launcher; frozen resource paths, licenses, exact-origin port handling, bounded service
recovery/shutdown, installer/portable upgrade+rollback, offline+OS smoke ต้องทดสอบจริง
GitHub-publishable เป็นเป้าหมาย ไม่อนุมัติ public repo/release หรือแนบ private Drive data

Naming slices: (1) visible app/window/shortcut/installer labels “SundayFamily”;
(2) web manifest/assets/help/update metadata alignment; (3) legacy launcher safety;
(4) internal entrypoint compatibility review. ไม่ rename `a_conductor` หรือ
`%LOCALAPPDATA%\A-Conductor\` โดยไม่มี migration decision (`AGENTS.md:3`)
Single app ไม่แปลว่า auto-start Serena workers จาก legacy path (audit T2)

“เบาเครื่อง”: เสนอเลิก GPU/interactive decoration ~1,830 LOC (~18% cosmetic estimate,
audit T1) ไม่รับรอง RAM saving ตาม LOC; ใช้ system fonts, no continuous animation,
reuse SSE/single-flight bounded polling, no recursive disk scan ใน render path
UX-4 ต้องวัด cold/warm startup, idle/active memory และ package size บน OS targets
ก่อนกำหนด/ประกาศ performance budget; ไม่สมมติว่าฝัง browser เบากว่า PWA เสมอ

## 8. Tk Carry-Over Versus Retirement Matrix

ทุก verdict เป็น DESIGN PROPOSAL; “retire with Tk” ไม่ใช่ลบทันที
Class + anchors อ้าง audit T2/T3/T4/T5 ตาม feature; parity gate ครอบทุกแถว

| Feature / audit class + anchor | Design verdict | IA / destination |
|---|---|---|
| Setup OS wizard, A; T3 `desktop_ui.py:3066-3354` | Carry later UX-4; trim Serena steps | First-run Settings; OS privileged work ไม่อยู่ใน browser |
| Guide+i18n, A; T1/T3 `i18n.py`, `desktop_ui.py:5199-5355` | Carry into v1 Thai-first labels/help; full translations later | Settings/help |
| Language preference, A; T3 `:4285-5198` | Carry into v1 display; persistence later | Settings |
| Shutdown preference/stop-all confirm, A; T3 `desktop_ui.py` | Carry later UX-4 lifecycle safety | Shell; no silent stop-all |
| Second Brain, A; T3 `:6366-6519` | Carry later UX-3 read-only config | Settings |
| Project registry diagnostics, A; T2 `:1447-1500,2887-2949` | Carry later when project DTO exists | Work & Lanes |
| Activity/log, A; T2 `:1853-1884` | Carry into v1 safe evidence; absent source remains UNKNOWN | Activity & Logs |
| Cockpit, A; T2 `:1886-2349` | Carry into v1 lane projection | Overview / Work & Lanes |
| Graph, A; T2 `:1886-2349` | Carry later read-only snapshot | Work & Lanes |
| Metrics, A; T2 `:1508-1605,2730-2885` | Carry into v1; null not zero | Overview |
| Error explanations, A; T3 `desktop_ui.py` | Carry into v1 sanitized reason/help | All ReasonLine surfaces |
| Self-update, A; T2 `:1828-1851` | Carry later reviewed UX-4 update path | Settings/about |
| Donate, A; T2 `:1828-1851` | Carry later optional passive link | Settings/about |
| Worker slots/scheduler/Add-Rename-Release, B; T2 `:1411-1440,1607-1849` | Retire with Tk worker-era UI | Replace mental model with Work & Lanes, not scheduler authority |
| Start/Stop/Restart Worker, B; T2 `:1700-1849,5628-5855` | Retire with Tk worker controls | No v1 equivalent |
| Copy Activate, B; T2 `:2887-2949` | Retire with Tk | No operator tool-prompt clipboard flow |
| Runtime Setup, B; T3 `:3910-4063` | Retire Serena-specific dialog | General OS onboarding handled separately |
| Worker Config, B; T3 `:5357-5627` | Retire with Tk | No ENGINE_TOOLS grid in v1 |
| ACTIVE PROJECT drift, B; T2 `:1700-1849` | Retire Serena-specific display | Do not invent replacement fleet binding evidence |
| Check Engine Update / supervised flag, B; T3 `desktop_ui.py` | Retire with Tk Serena-era paths | No equivalent |
| Connector lifecycle, C; T2 `:1700-1849`, T5 `desktop_control.py` | Carry into v1 status only; control later Gateway slice | Fleet; SundayMCP tunnel runtime still live |
| Models & Agents, C; T3 `:4285-5198` | Needs operator decision: recommend read-only v1 | Settings provider admission summary |
| Tunnel-ID management, C; T3 `desktop_ui.py` | Carry later secure setup, never display raw IDs | Settings/shell reviewed flow; bool only in Fleet |
| Rebind, C; T3 `desktop_ui.py` | Carry later separate Gateway+claim slice | Fleet; no v1 action |
| Delete + Drive backup, C; T3 `desktop_ui.py` | Carry later safety/backup parity | Settings/Fleet; no backup paths/secrets in UI |
| Connector log tail, C; T2 `:1886-2349` | Carry later safe log projection | Activity & Logs |
| Decoration, C; T1 logo modules | Needs operator decision: recommend retire animation/GPU dependency | Text identity in header; approved static identity later |
| Native picker / DPAPI / package install, Tk-only; T3/T5 | Carry later outside browser through reviewed OS seams | Settings/shell; do not expose native execution bridge |
| Disk-size / memory-presence probes, Tk-only; T2/T5 | Carry later bounded diagnostics, not render scans | Work & Lanes |

Required gate remains [runtime boundary](../contracts/sunday-family-web-runtime-boundary-v1.md)
`:112-117`: Web/PWA parity, Monitor truth, Command Gateway, recovery/unknown-outcome
visibility, Windows/macOS/Linux + required Pi/headless smoke, rollback documentation
One unresolved required Tk-only capability keeps Tk supported; no big-bang rewrite

## 9. Proposed Implementation Slices

นี่เป็น proposals สำหรับ future WOs เท่านั้น ไม่มี source/runtime/dependency authority
Operator green-light ของ mockup ต้องบันทึกบน #739 ก่อน UX-2 พร้อมข้อยุติ open decisions

| Slice | Proposed scope | Dependencies / contract gates |
|---|---|---|
| UX-2 | Wire `collect_local_*` → running provider → snapshot + proposed GET `/api/v1/inspector`; Overview/Fleet React build-out; sanitized collector notes | Existing Inspector seam (M2/M3); accepted DTO/schema/source freshness; device aggregation identity + Mac evidence separately required; auth/origin/redaction/128-row tests; no direct SRM calls; endpoint name remains proposal |
| UX-3 | Settings effective read-only projections + Jev corner with evidence refs | UX-2 truth semantics; safe config DTO (incl. allowlist), JEV READ_ONLY contract; missing sources UNKNOWN; editing config not authorized, future Gateway claim required |
| UX-4 | Production static hosting, launcher/WebView feasibility, portable/installer, visible SundayFamily rebrand | UX-2/3 UI review; serving seam B can be separately claimed prerequisite to local release, never presumed existing; dependency/license review, auth handoff R3 review, OS/recovery/upgrade/rollback/frozen tests |

UX-2 can develop in existing dev-server workflow (audit W1); shipped UX requires
production hosting. Fleet source work must not assume local discovery sees Mac;
if execution-local seams truly needed, use separately pinned CROSS_REPO WO
per contract `:72-78`. No SRM mutation is authorized by these proposals
Tk removal remains a separate acceptance decision after UX-4 parity, not an automatic step
Controls remain future Command Gateway slice; no reuse of accepted web stub as real execution

## 10. Open Operator Decisions

1. ยอมรับให้เอา GPU/interactive decoration ออกจาก SundayFamily และใช้ header เรียบตาม mockup หรือไม่? ข้อนี้ไม่เลิก Tk ทันที
2. ยอมรับ grouping เจ็ดเมนู โดย Projects/Claims/Roadmap อยู่ใน Work & Lanes ตามแถบนำทางหรือไม่?
3. Models & Agents ใน Settings ให้เป็น read-only panel ใน v1 ตามข้อเสนอ หรือเลื่อนทั้ง panel ไปภายหลัง?
4. รูปแบบหน้าต่างที่ต้องการคือ popup WebView ไม่มี browser chrome ตาม mockup หรือ launcher เปิด PWA? การเลือกยังต้องผ่าน feasibility/security review
5. ยอมรับ Fleet v1 แสดงเฉพาะ status/evidence ไม่มี Start/Stop/Pair/Rebind/Delete และ Jev เป็นคำแนะนำอย่างเดียวหรือไม่?

Approval record: PENDING #739 operator comment. ไม่มีคำตอบใดในเอกสารนี้ถูกถือเป็น
operator approval; ผู้เขียนยังไม่ได้เปิด browser/ทดสอบ mockup และไม่อ้าง visual PASS
