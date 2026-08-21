# Plan — Second Brain Phase 1 (WO-P1-052)

Date: 2026-08-21 · Status: approved (user) · Author: GLM 5.3/ZCode session 5
Source-of-truth rule: this file is the plan of record; chat/session memory is transport only.

## Goal (user, verbatim intent)

ให้ A-Wiki เป็นสมองควบคุมการทำงานใน A-Conductor: UI มีฟังก์ชัน "second brain" เลือก folder ได้ 1-2 อัน แล้ว Agent ใดๆ ที่เชื่อมผ่าน plugin เข้ามาสั่งงาน ต้องผ่านการอ่านสมอง/กฎก่อน — แบบประหยัด context window (Index+Pull) พร้อมทำงานค้างที่เหลือของ A-Conductor ต่อ

## Findings grounding this plan

1. `A:\GitHub\A-Wiki-vnext-clean` **no longer exists** (worktree removed mid-2026-08-21); the real brain repo is `A:\GitHub\A-Wiki` — used as the default.
2. Injection point verified from our captured engine reference notes: global config supports a `system_prompt` template field, and A-Conductor already generates that file (WO-P1-048 renderer) — no gateway needed for Phase 1.
3. Real brain files (verified on disk): `AGENTS.md`, `wiki/context/wiki-overview.md`, `wiki/context/session-memory.md`, `wiki/A-ROUTER.md`, `wiki/SKILL-INDEX.md`, `docs/protocols/` (43 files).
4. Standing leftover closed by this plan: `apply_worker_serena_settings` exists and is tested but nothing calls it — settings never materialize into a real `SERENA_HOME`.

## Design decisions

- **Global Brain Profile** (not per-worker): the brain gates every connected agent — one shared profile stored in the settings store under key `global-brain` (passes existing worker-id pattern).
- Model: `WorkerSerenaSettings` += `brain_folders: tuple[str, ...]` (max 2, absolute paths) and `brain_entry_files: tuple[str, ...]` (max 2, files the agent must read first).
- Renderer: when brain fields are set, the generated config gains a `system_prompt` block containing a ~10-line brain **index** (paths + rules) — **never file contents** (Index+Pull only; token-cheap mandate).
- Defaults offered in UI: folder `A:\GitHub\A-Wiki`; entries `AGENTS.md`, `wiki/context/wiki-overview.md`.
- Materialize-on-start: `LocalInstanceOrchestrator.start()` applies the global brain profile to the instance's `serena-home` (confined applier) before launching the validated start script — every connector gets the same brain automatically.
- Honesty note: prompt injection teaches but does not cage — a lazy agent can skip reading. Mitigations: short load-bearing rules ("before write/execute, quote the rule you are following") + future Phase 2 enforcement via the MCP gateway (DECISION_REQUIRED).

## Delivery (TDD, CI-green before every merge)

1. PR #18 — this plan file + WO-P1-052 (docs first, SSoT).
2. PR #19 — model+renderer brain fields + `system_prompt` block + store migration (PRAGMA-guarded ALTER, legacy DBs upgrade in place).
3. PR #20 — UI: Config dialog gains a minimal "SECOND BRAIN" section (2 folder + 2 entry-file fields, browse buttons, "~index only" note) editing the global profile.
4. PR #21 — materialize-on-start wiring (orchestrator + applier + facade); real verification against a **temp copy** of a real instance (live instance untouched).
5. Final — full regression + checkpoint + push.

## Success criteria

- Unit: brain settings → renderer emits `system_prompt` with index and rules; **no file contents embedded**; migration upgrades legacy DBs.
- Real: start on a temp-copied instance writes `serena_config.yml` with the brain block into its serena-home; live instances untouched during tests.
- Full suite green; CI green on every PR.

## Remaining backlog (separate WOs, not this plan)

- MCP gateway Phase 2 — hard enforcement + brain-read evidence in execution records (DECISION_REQUIRED).
- CONNECTORS project rebind via UI; supervised default flip (user decision); DR-P1-003 (user-gated); code signing to remove SmartScreen friction.
