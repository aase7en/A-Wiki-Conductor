# A-Sunday Conductor — Current Work

## 2026-10-11 (night) — SEM-4c diagnostics surfacing shipped after 2-round review; PILOT-FIRST steer re-verified — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079) + PILOT-FIRST acceleration steer (re-delivered 2026-10-11 at a verified idle boundary and re-absorbed; Track C runs as the independent autonomous lane while the Pilot critical path stays human-gated). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `d0a7a2728bc4676a04a9ee882042efe0084d2c96` (this checkpoint advances it); **SunDayRemoteMCP `8291fa03ef3df8c0b4ce769a0ff83c206d97d178`** (advanced by #341 SEM-4c). Post-main codespell green on both.
- **#341 SEM-4c** (claim on AWC #341 comment 6098850352; released 6099041658): SRM PR #19 merged expected-head `5989e6d` → main `8291fa0`. TypeScript diagnostics on the semantic surface: additive SEM-0 `SemanticDiagnostic` contract (range, severity error/warning/suggestion, bounded code + message, fail-closed validator, count bound 1000 typed); `TypeScriptSemanticAdapter.diagnostics` (syntactic + semantic merged, whole-body typed containment, breadth-forward message-chain flattening); `sunday_semantic_diagnostics` read-only MCP tool through the routed adapter (payload cap 200 + truncated + engineCode; per-call session; engine surface untouched by design). Review 2 exact-SHA rounds (r1 FAIL chain-flattening/containment/bound-assertions; r2 PASS @ `5989e6d`; record: SRM PR #19 comment 6099040895). 16/16 + full regression; tsc + codespell clean. Provenance: public typescript API + SEM contracts only.
- **Track C progress:** SEM-0 ✅ 1a ✅ 1b ✅ 2 ✅ 3a ✅ 3b ✅ 4a ✅ 4b ✅ **4c ✅** → NEXT_READY: **SEM-4d** — keyed session reuse (under the recorded constraints: byte-hash identity, authorized-transition snapshot contract, program/disk consistency) and/or diagnostics conformance coverage; folded: merged-declaration completeness, cross-file merged identity.
- **PILOT-FIRST status:** steer re-delivered at the SEM-4b→4c boundary and re-verified live: PR #67 OPEN @ c1bf7ea4; #285/#293 OPEN; #526 latest comment still Phase-0 (no ratification); no enrollment evidence. Pilot acceptance (2)(3)(5) sit behind human gates ③+④; (1)(4)(6) code paths exist, real-machine proof pending; (7) pending real-machine results.
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-11 (later) — SEM-4b conformance harness + efficiency evidence shipped after 4-round review — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079) + PILOT-FIRST acceleration steer (Track C runs as the independent autonomous lane while the Pilot critical path stays human-gated). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `3582add8f3c5f345fbf9351ae1e2e0988e38cafd` (this checkpoint advances it); **SunDayRemoteMCP `858ec990307288c02dc250c8baa25c9ca71a57ec`** (advanced by #341 SEM-4b). Post-main codespell green on both.
- **#341 SEM-4b** (claim on AWC #341 comment 6098172078; released 6098394126): SRM PR #18 merged expected-head `63b1e84` → main `858ec99`. Test + evidence only: `test/test-sunday-semantic-conformance.js` (9 contract-family rows mapping the pure-engine expectations onto the REAL adapter — reads incl. engine-level callersOf over real cross-file data via a test-local seam router; mutations incl. insertAfterSymbol over real disk, regex-special/dollar-laden rename through the locked editor, multi-op workflow with rebinds; typed drift zero-edit; capability-missing; authorized-transition POST fence; program/hash consistency with disk-span verification) + `docs/semantic-efficiency-evidence.md` (measured cost model: inclusive cold session ~0.8s, first-call ops ~0.5-1.4s; per-call construction = accepted v1 trade-off; keyed session reuse named as follow-up with byte-hash/authorized-transition/consistency constraints; captured-output provenance). Review 4 exact-SHA rounds (r2 first attempt = reviewer-side infra failure, re-dispatched once per infra-flake protocol; r4 PASS @ `63b1e84`; record: SRM PR #18 comment 6098393479). 9/9 + full regression; tsc + codespell clean.
- **Track C progress:** SEM-0 ✅ 1a ✅ 1b ✅ 2 ✅ 3a ✅ 3b ✅ 4a ✅ **4b ✅** → NEXT_READY: **SEM-4c** — diagnostics surfacing (typed TS diagnostics through the provider seam; own claim) and/or the efficiency follow-up (keyed session reuse under the recorded constraints); folded: merged-declaration completeness, cross-file merged identity.
- **PILOT-FIRST status:** unchanged — Pilot acceptance (2)(3)(5) sit behind human gates ③ enrollment + ④ WO-259/260 ratification; (1)(4)(6) code paths exist, real-machine proof pending; (7) pending real-machine results. Human gates verified unchanged across the SEM-4a/4b cycles.
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-11 — SEM-4a read-only semantic MCP tools shipped after 3-round review — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079) + PILOT-FIRST acceleration steer (Track C runs as the independent autonomous lane while the Pilot critical path stays human-gated). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `f744a8abd817387041ead3d6c31fdc6f3baa457b` (this checkpoint advances it); **SunDayRemoteMCP `90ccd277cdd6907ebc84bfe9d1cfd310244dc03b`** (advanced by #341 SEM-4a). Post-main codespell green on both.
- **#341 SEM-4a** (claim on AWC #341 comment 6096971351; released 6097686482): SRM PR #17 merged expected-head `35e39f1` → main `90ccd27`. Six READ-ONLY `sunday_semantic_*` MCP tools (symbols / find_symbol / read_symbol / references / callers / callees) over the SEM engine + real TypeScript adapter — semantic reads are now reachable from the MCP surface. `RoutedSemanticAdapter` composes per-file adapters (path-keyed routing; all-roots program seeding makes cross-file facts import-direction independent); `additionalFiles` roots (max 32, realpath PHYSICALLY validated — symlink/junction escape and target aliasing fail typed EWORKSPACE); exactly-one symbol resolution (ENOTFOUND/EAMBIGUOUS); bounded payloads with truncation flags; engine typed failures pass through with engineCode; disposal attempted-best-effort with constructor rollback. **SEM-2 mutation ops deliberately NOT wired** — gated on Track B canonical admission (CUTOVER-MUTATE); a regression row enforces the absence. Review 3 exact-SHA rounds (r1 FAIL disposal-fault-path/symlink-escape; r2 FAIL claim-overstate/skip-accounting; r3 PASS @ `35e39f1`; record: SRM PR #17 comment 6097685893). 14/14 exercised + 18/36/58 + types + engine + facade suites; tsc + codespell clean. Provenance: public typescript API + SEM contracts only — no Serena/SolidLSP (GPL) code.
- **Track C progress:** SEM-0 ✅ 1a ✅ 1b ✅ 2 ✅ 3a ✅ 3b ✅ **4a ✅** → NEXT_READY: **SEM-4b** — conformance harness (pure-engine expectation shapes over the real TS adapter) + efficiency evidence (per-call LS construction cost; evidence-driven reuse) + diagnostics surfacing; folded follow-ups: merged-declaration completeness, cross-file merged identity.
- **PILOT-FIRST status:** unchanged — Pilot acceptance (2)(3)(5) sit behind human gates ③ enrollment + ④ WO-259/260 ratification; (1)(4)(6) code paths exist, real-machine proof pending; (7) pending real-machine results. All four human gates verified unchanged across the SEM-3a/3b/4a cycles.
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-10 (night) — SEM-3b callees shipped after 3-round review — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079) + PILOT-FIRST acceleration steer (appended 2026-10-10; Track C runs as the independent autonomous lane while the Pilot critical path stays human-gated). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `10233b952768d43e5aed0e31c4321c44eb6810fd` (this checkpoint advances it); **SunDayRemoteMCP `af2941284efab4a2e7e0e9a39a749744384c7eb7`** (advanced by #341 SEM-3b). Post-main codespell green on both.
- **#341 SEM-3b** (claim on AWC #341 comment 6096293494; released 6096504442): SRM PR #16 merged expected-head `172d622` → main `af294128`. `TypeScriptSemanticAdapter.callees` implements the optional SEM-1b outgoing-call-hierarchy capability via prepareCallHierarchy + provideCallHierarchyOutgoingCalls — engine.calleesOf now returns real edges for TS files instead of typed CAPABILITY_MISSING. Same discipline as references (consumed-count bound incl. out-of-root skips; per-callee program-text/disk-byte consistency with byte-hash bindings; typed payload gates; JSON-identity dedupe). Review 3 exact-SHA rounds: r1 caught a factually WRONG cross-minor API claim (both TS 5.3.3 and 5.9.3 use fileName+position — fallback removed), merged-declaration edge loss, and a delimiter-collision dedupe key; r2 caught a fail-open undefined-outgoing path; r3 PASS @ `172d622` (record: SRM PR #16 comment 6096503957). **Documented limitation:** the TS navigation surface merges split declarations of one symbol into a single node, so merged symbols contribute edges only from the first surfaced declaration (pinned by regression row; cross-file merges out of single-file scope; revisit at SEM-4 conformance). 18/36/58 + types + engine suites green. Provenance: public typescript API + SEM contracts only — no Serena/SolidLSP (GPL) code.
- **Track C progress:** SEM-0 ✅ 1a ✅ 1b ✅ 2 ✅ 3a ✅ **3b ✅** → NEXT_READY: **SEM-4** — diagnostics surfacing + MCP tool wiring (expose semantic ops as SundayMCP tools) + conformance harness + efficiency evidence; folded follow-ups: merged-declaration completeness, cross-file merged identity.
- **PILOT-FIRST status:** unchanged from the SEM-3a checkpoint — Pilot acceptance (2)(3)(5) sit behind human gates ③ enrollment + ④ WO-259/260 ratification; (1)(4)(6) code paths exist, real-machine proof pending; (7) pending real-machine results. Human gates re-verified unchanged this cycle.
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-10 (evening) — SEM-3a real TypeScript provider shipped after 3-round review; PILOT-FIRST steer active — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079) **+ PILOT-FIRST acceleration steer appended 2026-10-10** (smallest usable SundayMCP Pilot, then full roadmap; Track C must not displace the Pilot critical path). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `a1d5e0a21d0f71e0d2c1800ea8e6995ad7a8326a` (this checkpoint advances it); **SunDayRemoteMCP `c5652024c35f0b75b1ed590102d74c33cf8c9822`** (advanced by #341 SEM-3a). Post-main codespell green on both.
- **#341 SEM-3a** (claim on AWC #341 comment 6095312788; released 6095629259): SRM PR #15 merged expected-head `ce23b31` → main `c565202`. First REAL provider: `TypeScriptSemanticAdapter` implementing context/provider/reader/editor seams over the real TypeScript LanguageService — lazy `typescript` load (dev-dep only, typed PROVIDER_UNAVAILABLE when absent; depdiet-compliant), symbols from navigation tree with typed payload gates, cross-file references with per-file byte-sha bindings + program-text/disk consistency checks, atomic editor with proper-lockfile verify-then-write INSIDE the lock, TS line-terminator offset math (LF/CRLF/lone CR), service rebuilt per edit. **Operation-context snapshot contract**: the adapter presents its single most-recent engine-authorized edit ({fromSha,toSha}, raw-byte hashes) as the pre-edit binding so engine fences flag only unauthorized drift. Review 3 exact-SHA rounds (r1 FAIL byte-hash/TOCTOU/truncation/count-bypass; r2 FAIL disclosure overclaim + span-less skip + weak stale-program tests; r3 PASS @ `ce23b31`; record: SRM PR #15 comment 6095628764). Documented residuals: byte-identical restore equivalence; non-cooperating-writer lost-update window between in-lock verify and rename. 16/36/58 + types + engine suites green. Provenance: public typescript API + SEM contracts only — no Serena/SolidLSP (GPL) code.
- **Track C progress:** SEM-0 ✅ 1a ✅ 1b ✅ 2 ✅ **3a ✅** → NEXT_READY: SEM-3b callees via TS call hierarchy (optional capability today: typed CAPABILITY_MISSING), then SEM-4 diagnostics + MCP wiring + conformance/efficiency.
- **PILOT-FIRST status:** Pilot acceptance 1–7 mapped against live truth — (1) ChatGPT entry point, (4) file listing/reading, (6) status/recovery: code paths exist via INSTALL-1 + SRM read tools but real-machine proof pending; (2)(3)(5) sit behind human gates ③ enrollment + ④ WO-259/260 ratification (exact routing + canonical admission); (7) documentation pending real-machine results. All four human gates re-verified UNCHANGED 2026-10-10 (PR #67 OPEN @ c1bf7ea4; #285/#293 OPEN; no ratification on #526; no enrollment evidence). Pilot critical path = human-gated; Track C continues as the independent autonomous lane per the steer.
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-10 (later) — SEM-2 guarded mutation ops shipped after 7-round review — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `6495567afe3b943b2f33f028993e4a267868e30e` (this checkpoint advances it); **SunDayRemoteMCP `60c8ebf184c892b20301f66dd1ada5e4d093e3c7`** (advanced by #341 SEM-2). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **#341 SEM-2** (claim `WO-341-SEM-2-GUARDED-MUTATION-WIN-001` 6090613860; released 6093376437): SRM PR #14 merged expected-head `df22bc5` → main `60c8ebf`. Guarded mutation ops at the pure layer: `SemanticFileEditor` injected seam (absent → SEMANTIC_CAPABILITY_MISSING) + `replaceSymbol`/`insertBeforeSymbol`/`insertAfterSymbol`/`renameSymbol` sharing one guard chain — validated+owned caller identity → PRE probe → re-resolve with EXACTLY-ONE identity match (ambiguous → drift, zero edits) → owned planned range/text → MID probe → ONE edit via a once-captured capability receiving a DETACHED owned target → POST probe against an untouched baseline. Zero edits on any pre-edit drift; typed failure always; rename = whole-identifier occurrences only. Review 7 exact-SHA rounds → r7 PASS (record: PR #14 comment 6093376272); residual documented: post-edit malformed/drift reports typed failure after an applied edit — rollback is the editor adapter's contract (SEM-3). 36+58+SEM-1a+types+6 INSTALL suites green.
- **Track C progress:** SEM-0 ✅ SEM-1a ✅ SEM-1b ✅ **SEM-2 ✅** → **NEXT_READY: SEM-3 real LSP provider** (TypeScript first; independent standard-LSP only — GPL guard: no Serena code, SolidLSP only after provenance review; injectable keeps pure layers provider-neutral). Then SEM-4 diagnostics + MCP wiring + conformance/efficiency evidence.
- Track A: INSTALL-1 A–G merged; CUTOVER-RO gated on HUMAN enrollment (+ exact routing review → Track B). Track B: Phase-0 done (#526 c6076837022); mutation gated on WO-P1-259/260 integrator ratification (requested once).
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.


## 2026-10-10 — SEM-1b call hierarchy shipped after 14-round review — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake `automation-c872bd35` active @30-min, Supervisor v3 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits).

- Mains: A-Wiki-Conductor `b91ff71830ced94b1df767bc058a1229b3a96472` (this checkpoint advances it); **SunDayRemoteMCP `7afdab0c960962227fce84c8ba203c016e7c5b45`** (advanced by #341 SEM-1b). Post-main codespell green. PR #67 human gate unchanged @ `c1bf7ea4`.
- **#341 SEM-1b** (claim `WO-341-SEM-1B-CALL-HIERARCHY-WIN-001` 6077654298 + amendments 6080111797; released 6089923391): SRM PR #13 merged expected-head `f533516` → main `7afdab0`. `callersOf`/`calleesOf` at the pure layer + the SHARED SEM-1a engine hardened under disclosed amendments (total identity-aware once-only ownership; index-only iteration w/ integer lengths + beyond-bound probes; single-capture envelopes/capabilities/targets; contained typed validations; detached cross-file targets w/ baseline/after drift checks). Review: 14 exact-SHA rounds, r14 PASS (record: PR #13 comment 6089923024). CI incident documented: PR codespell failed 2x on Docker Hub 504 (action-container outage, no findings); local codespell rc=0; post-main codespell SUCCESS. 58+SEM-1a+types+6 INSTALL suites green locally.
- **Track C plan (recovered, comment 6077279264):** SEM-1b ✅ → **NEXT_READY: SEM-2 guarded mutation ops** (replace/insert-before/insert-after/rename on the read core: re-resolve symbol → verify HEAD/file/symbol identity → mismatch = typed SEMANTIC_CONTEXT_DRIFT; never edit by stale range). Then SEM-3 real LSP provider (TS first; GPL guard: no Serena code, SolidLSP only after provenance review); SEM-4 diagnostics+MCP wiring+conformance.
- Track A: INSTALL-1 A–G merged; CUTOVER-RO gated on HUMAN enrollment (+ exact routing review → Track B). Track B: Phase-0 done (#526 c6076837022); mutation gated on WO-P1-259/260 integrator ratification (requested once).
- Human gates (all stated once, unchanged): ① PR #67 merge @ `c1bf7ea4` ② WO194→#285→#293 ③ CUTOVER-RO enrollment ④ Track B WO-259/260 ratification.
- Residuals tracked: physical/symlink confinement; OS-lock stale-reclaim + snapshot transactionality; minor read-count assertions on two r13 rows (cosmetic).


## 2026-10-09 (later) — INSTALL-1 slice G shipped (CUTOVER-RO procedure + real-machine evidence) — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake `automation-c872bd35` active @ 30-min, Supervisor v2 persisted (SELF_UPDATE_UNSUPPORTED for agent-side edits; prompt hints STALE_MINOR — recover live truth per §3).

- Mains: A-Wiki-Conductor `388975bf0f64d795d0c56758f8ce3ac73c1dc67a` (this checkpoint advances it); **SunDayRemoteMCP `4bbd682ee5faa528f1b1a7cf5486354ddcbf677a`** (advanced by INSTALL-1 slice G). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice G** (#607 claim `WO-P1-607-INSTALL1-SOURCE-G-WIN-001` 6074850454 + scope amendment 6074861771; released 6075812988): SRM PR #12 merged expected-head `21a3533` → main `4bbd682`. New `docs/cutover-ro-canary-procedure.md` (typed PASS criteria per step; enrollment HUMAN by design; evidence template; remaining gates + residuals stated precisely). Real-machine evidence (Windows 11, temp root): install `INSTALLED_PAIRING_REQUIRED` w/ upstream OK (exit 1 correct), `--no-upstream` → `DOCTOR_UNKNOWN` fail-closed, canary `READ_CANARY_PASS` exit 0 / `OUTSIDE_ALLOWLIST` exit 1. **Genuine defect found & fixed:** Windows libuv assertion crash when the CLI's undici fetch + AbortSignal.timeout raced hard `process.exit()` → `process.exitCode` + drain (both CLIs; contract re-verified). QA 2 rounds → PASS.
- **INSTALL-1 cumulative: A–G merged.** Full Windows-first path with procedure + machine-verified evidence: install → enroll(HUMAN) → verify → gated start → read canary.
- **CUTOVER-RO remaining:** ① steps 2–4 evidence on a real enrolled machine (**HUMAN action: enrollment browser consent + real token** — stated once, not re-asked); ② exact routing review (Track B); ③ #495 multi-device prerequisites.
- Human gates pending (do not re-ask): ① A-Wiki PR #67 merge @ `c1bf7ea4`; ② WO194→#285→#293 disposition.
- **NEXT_READY:** with INSTALL-1's automatable surface complete and CUTOVER-RO gated on human enrollment, open **Track B** convergence: #526 canonical mutation admission + exact worktree binding (recover accepted ACT-1 boundary on AWC main), then #495 generation/idempotency. Follow-ups tracked: physical/symlink confinement; OS-lock stale-reclaim + snapshot transactionality; drive-case/lastSlash canary rows.


## 2026-10-09 — INSTALL-1 slice F shipped (deterministic read canary); wake repaired (Supervisor v2 active) — CURRENT

> Cross-req projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake task `automation-c872bd35` REPAIRED via human UI action and verified live: **enabled/active, 30-minute cadence, Adaptive Roadmap Supervisor v2 prompt persisted (incl. self-update inheritance contract), no duplicate**. Session tool surface still exposes only CronList ⇒ SELF_UPDATE_UNSUPPORTED for agent-side edits (unchanged, documented).

- Mains: A-Wiki-Conductor `75365ad7fc88b06c5223a5f5063851e676adaa03` (this checkpoint advances it); **SunDayRemoteMCP `bb48822cc67506b9330fbd94b11774cde68955cd`** (advanced by INSTALL-1 slice F). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice F** (#607 claim `WO-P1-607-INSTALL1-SOURCE-F-WIN-001`, comment 6073618425; released 6074110782): SRM PR #11 merged expected-head `c59157d` → main `bb48822`. New `src/sunday/read-canary.ts` + `device:sunday:smoke` CLI — the CUTOVER-RO deterministic read canary: persisted policy-validated allowlist authority, strictly-inside target gating, both probe paths gated before real probe selection (zero real probes on every denial path), payload never in results, exit 0 only on PASS. Review 3 rounds (r1 inert gate-only ping; r2 platform-independent listDir derivation + supplied-ping validation + runner-safe CLI rows) → r3 PASS; residual: lexical-not-physical containment (frozen slice-A policy, tracked).
- **INSTALL-1 cumulative: A+B+C+D+E+F merged.** Windows-first path: `device:sunday:install` → pairing → `SUNDAY_AGENT=1 device:start` (gate + pid claim) → `device:sunday:smoke` (read canary). SRM baseline 82/89 (7 pre-existing; supervisor passed last run).
- Human gates pending (do not re-ask; packets posted): ① A-Wiki PR #67 merge @ `c1bf7ea4`; ② WO194→#285→#293 disposition.
- **NEXT_READY:** CUTOVER-RO prerequisites — canary procedure evidence on a real paired machine + exact routing review; then Track B convergence (#526 + #495 + ACT-1 integration → CUTOVER-MUTATE); Track C #341 after. Follow-ups tracked: physical/symlink confinement; OS-lock stale-reclaim + multi-file snapshot transactionality; drive-case/lastSlash canary rows.


## 2026-10-08 (evening) — INSTALL-1 slice E shipped (installer entry) — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake task `automation-c872bd35` verified PAUSED (enabled=false; SELF_UPDATE_UNSUPPORTED — this session's tool surface exposes only CronList; HUMAN_ACTION_REQUIRED stated once: re-enable the SAME task at 30-min in ZCode Automations UI; adaptive inheritance contract text lives in the 2026-10-08 slice-C section below and in this file's policy record).

- Mains: A-Wiki-Conductor `970aac58507d1ee3b9e26219d81dfd53615f98bd` (this checkpoint advances it); **SunDayRemoteMCP `9923635a114dada619177d8a0cc81f193cc9aa16`** (advanced by INSTALL-1 slice E). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice E** (#607 claim `WO-P1-607-INSTALL1-SOURCE-E-WIN-001`, comment 6063608081; released 6064384366): SRM PR #10 merged expected-head `b86c79e` → main `9923635`. New `src/sunday/installer.ts` (`runSundayInstaller`: idempotent validated writes → doctor/pairing over read-back policy-validated post-callback persisted evidence; typed outcomes; READY only on policy-valid config + valid install marker + upstream true + PAIRED; consent-first pairing next-actions) + `src/npm-scripts/sunday-install.ts` + `device:sunday:install` script; additive inert validators `persistedInstallValid`/`persistedInstallMarkerValid` in agent-lifecycle (pre-existing exports unchanged).
- **Review record (Codex gpt-6.1-sol exact-SHA, 5 rounds):** r1–r4 FAIL→real fixes (inert options incl. revoked proxies + accessor fields; evidence captured AFTER the caller's upstream callback; persisted config validated against the same install policy; inert exported validators; install.json recheck — deleted/corrupt marker → INSTALL_MARKER_INVALID matching the startup gate); r5 `b86c79e` **PASS** (no remaining deterministic bypass). Residual (reviewer-noted, documented): multi-file evidence reads are snapshot-limited (concurrent replacement not transactional; OS-lock class, tracked with the slice-D residual). Full table: SRM PR #10 comment 6064365457.
- **INSTALL-1 cumulative: A+B+C+D+E all merged.** The Windows-first path is now: `npm run device:sunday:install` (typed install/pairing/doctor) → pairing flow → `SUNDAY_AGENT=1 npm run device:start` (gate: doctor+pairing+autostart, pid-claim admission). SRM local baseline 81/88 (7 pre-existing + flake), zero new.
- Human gates pending (do not re-ask; packets posted): ① A-Wiki PR #67 merge decision @ `c1bf7ea4`; ② WO194→#285→#293 disposition. Wake re-enable (Automations UI) also human — stated once above.
- **NEXT_READY:** read-smoke integration + deterministic smoke wiring (slice F) toward CUTOVER-RO canary prerequisites; pairing-code transport UX; then Track B convergence (#526 + #495 + ACT-1 integration).


## 2026-10-08 (latest) — INSTALL-1 slice D shipped (agent write lifecycle) — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake task `automation-c872bd35` active (15-min); STEER self-maintenance upgrade BLOCKED_AT_TOOL_SURFACE (see prior section + this file's policy record).

- Mains: A-Wiki-Conductor `fc9af9e6802c68b91e07abc2bcf46766b064ba5e` (this checkpoint advances it); **SunDayRemoteMCP `aa47bb2a5d7cc1d472cc5ca63e9b66b3b650e5f9`** (advanced by INSTALL-1 slice D). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice D** (#607 claim `WO-P1-607-INSTALL1-SOURCE-D-WIN-001`, comment 6055042606; released 6058553015): SRM PR #9 merged expected-head `680765c` → main `aa47bb2`. New `src/sunday/agent-lifecycle.ts`: `initializeSundayInstall` (validated atomic config.json+install.json writes; allowlist clean-by-construction), `acquireAgentPid`/`releaseAgentPid`(+Sync) single-ownership pid claim (wx-exclusive create for MISSING; EEXIST loser typed-refused; verify-after-publish; own-only release), `createSundayAgentGateFactory` (admission ⇔ pid claim verifiably held) wired into `--sunday-agent`/`SUNDAY_AGENT=1` with `releaseSync` on exit. `MCPDevice` class unchanged.
- **Review record (Codex gpt-6.1-sol exact-SHA, 4 rounds):** r1–r3 FAIL→real fixes (inert-input discipline incl. revoked proxies; wx-exclusive acquisition; tmp self-cleanup; header accuracy); r4 `680765c` **PASS** within the stated cooperating-process threat model; 3 residuals ACCEPTED-AND-DOCUMENTED in the module header (simultaneous stale-dead-owner reclaim window; interrupted-create junk→typed manual recovery; rogue in-process writers out of model). Caveat: reviewer ran as static GitHub-source review (alpha Codex local sandbox/file tools broken); local suites at exact head are the execution evidence. Full table: SRM PR #9 comment 6058542211.
- **Codex binary moved again:** current `C:\Users\aase7en\AppData\Local\OpenAI\Codex\bin\9691020b546a15b2\codex.exe` (0.162.0-alpha.2; the previous 5ea220ae823df3d7 dir no longer exists). When its local tools fail, GitHub-source static review mode works.
- **INSTALL-1 cumulative:** slices A (doctor/read-smoke) + B (pairing/autostart) + C (startup gate) + D (write lifecycle) all merged. SRM local full-suite baseline 79/87 (7 pre-existing local failures reproduce on clean main + 1 known ESRCH flake); zero new failures introduced.
- Human gates pending (do not re-ask; packets posted): ① A-Wiki PR #67 merge decision @ `c1bf7ea4`; ② WO194→#285→#293 disposition.
- **NEXT_READY:** INSTALL-1 slice E — installer-entry UX surface (npm script/CLI wrapping `initializeSundayInstall` + pairing flow + first-run doctor), then read-smoke wiring toward CUTOVER-RO canary prerequisites; follow-up: OS-lock-based stale-reclaim exclusivity decision. Track B (#526 + #495 + ACT-1 integration) when a lane frees.


## 2026-10-08 (latest) — INSTALL-1 slice C shipped (agent-startup gate wired) — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079). Wake task `automation-c872bd35` active (15-min); STEER self-maintenance upgrade recorded below.

- Mains: A-Wiki-Conductor `a68887e8a04c91aa6013f38b8098d0d189cdb03d`; **SunDayRemoteMCP `29ff81609d9f0c5f923400c136cd937aea853277`** (advanced by INSTALL-1 slice C). Codespell green on main post-merge. PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice C** (#607 claim `WO-P1-607-INSTALL1-SOURCE-C-WIN-001`, comment 6050124177; released 6054006578): SRM PR #8 merged expected-head `733ae5b` → main `29ff816`. New `src/sunday/agent-gate.ts` (pure admission: pairing PAIRED + coherent-HEALTHY doctor + autostart START|ALREADY_RUNNING-HEALTHY-self only; typed fail-closed denies) + `src/sunday/agent-entry.ts` (read-only fs adapters: pairing store/config/install/agent.pid evidence, deadline-bounded upstream, fail-closed PID classification) + opt-in `MCPDeviceOptions.agentGate` in `device.ts` evaluated BEFORE spawn/network/auth (`--sunday-agent`/`SUNDAY_AGENT=1`). Legacy path unchanged.
- **Review record (Codex gpt-6.1-sol exact-SHA, 7 rounds):** r1–r6 FAIL→real defects fixed (getter split-brain, inherited fields, garbage-admit, invalid-PID-as-live, unbounded waits, forged aggregates, hiding iterators, transparent proxies, mid-loop truncation, accessor mutation family, mutating envelope); r7 `733ae5b` = **no source defect** (77 probes/0 caller-code invocations; 96-case matrix correct; producer outputs admit; sole FAIL row = reviewer sandbox EPERM on mkdtemp, environmental). Convergent invariant: gate validates only inert data-property evidence via `Object.getOwnPropertyDescriptor`. Full table: SRM PR #8 comment 6053954409.
- **Local test baseline (SRM):** 78/86; 7 failures reproduce identically on clean base `c9b161a` (pre-existing local, hosted CI is codespell-only); supervisor ESRCH flake passes on rerun. Slice-C suites (3 files, incl. all review regression rows) green at merge head.
- **STEER — adaptive self-maintaining wake (durable record):** `WAKE_POLICY: SELF_MAINTAINING=TRUE, SAME_SESSION_ONLY=TRUE, UPDATE_IN_PLACE=TRUE, CREATE_DUPLICATE=FALSE, MIN_INTERVAL_MINUTES=30, ROADMAP_DRIVEN=TRUE, SAFETY_INVARIANTS_IMMUTABLE=TRUE, SELF_UPDATE_INHERITS=TRUE` for task `automation-c872bd35` / session `sess_b82dd681-c3b1-49c6-990e-b1918b764209`. Hereditary clause (must appear in every future wake-prompt revision): "This Scheduled Task may update its own existing task/payload/cadence for this same session when stale against accepted roadmap truth, subject to the self-update safety/inheritance contract." Application status: **BLOCKED_AT_TOOL_SURFACE** — `CronUpdate` is not exposed in the current session tool surface (only `CronList`); the existing task remains active at 15-min cadence (safe, pre-existing), no duplicate created, no delete+recreate. Apply in place (30-min cadence + refreshed payload carrying this policy) as soon as the tool is available in a future session.
- Human gates pending (do not re-ask; packets posted): ① A-Wiki PR #67 merge decision @ `c1bf7ea4`; ② WO194→#285→#293 disposition.
- **NEXT_READY:** INSTALL-1 slice D — installer-entry write lifecycle (`config.json` agentVersion/allowlist write, `install.json` marker, `agent.pid` acquire/release on the wired path), then mutation smoke + Mac parity; Track B (#526 + #495 + ACT-1 integration) proceeds when a lane frees.


## 2026-10-08 (later) — INSTALL-1 slices A+B shipped — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary; 15-min wake active. Primary Goal = ONE SUNDAYMCP success path (operator reorder #495/6035553079).

- Mains: A-Wiki-Conductor `9dd3e4c729a965d6fcaa7e216946b0e6f29a55d4` (+ push CI green); **SunDayRemoteMCP `c9b161a71f7ed6cdc5ceb67b726424c6c2791717`** (advanced by slice B). A-Wiki main `16897b2d`; PR #67 human gate unchanged @ `c1bf7ea4`.
- **INSTALL-1 slice A** (#607): doctor + read-smoke — merged @ SRM `dc5e311`.
- **INSTALL-1 slice B** (#607; PR #7 head `17e28c9` -> `c9b161a`; post-main all suites green): `pairing-state.ts` (consent-gated UNPAIRED->PENDING->PAIRED; token REQUIRED — no fallback credential; digest-committed code; typed UNKNOWN never PAIRED) + `autostart.ts` (exactly-once planner; double-boot yields; UNKNOWN->recovery; pairing fail-closed). GLM 2-round review r2 PASS (4 info-P3 ledger on #607). Claim released.
- **NEXT_READY — slice C (wiring)**: integrate doctor probes + pairing store + autostart planner into the Device Agent entry/install path (`npm-scripts/setup.ts` / remote-device surfaces); pin {AWC@`9dd3e4c`+, SRM@`c9b161a`+}; fresh claim `WO-P1-607-INSTALL1-SOURCE-C-WIN-001` under WO-P1-607. Then installer-entry UX, mutation smoke, Mac parity.
- Human gates unchanged: (1) A-Wiki PR #67 merge; (2) WO194->#285->#293 stack disposition.
- Env notes: SRM supervisor fault-suite has intermittent `kill ESRCH` timing flake in the long-lived reference worktree (same-SHA differential = flake); Codex binary 5ea220ae823df3d7/codex.exe 0.160.1.

**Exact next safe action:** claim INSTALL-1 slice C per WO-P1-607 -> wire doctor/pairing/autostart into the setup/device-agent entry (RED-first against the frozen modules) -> review/CI/merge/post-main.

## 2026-10-08 — roadmap reorder active; INSTALL-1 slice A shipped — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary; 15-min wake automation active.

- Current mains: A-Wiki-Conductor `0c2ff17fb7ca586fbdbdeb1e6596f1e6efb96255` (push CI 37640116990 SUCCESS); SunDayRemoteMCP `dc5e311d2cf6542d68d4d440aa5f8f5774ceba75`. A-Wiki main `16897b2d` (PR #67 human gate unchanged @ c1bf7ea4).
- **Roadmap priority**: operator reorder #495/6035553079 — G0 (truth+drain, no removals) || TRACK A INSTALL-1 (highest) || TRACK B #526+#495+ACT-1 -> CUTOVER-RO -> CUTOVER-MUTATE || TRACK C #341 parity -> retirements || TRACK D UX only after core.
- **Shipped this lineage**: P8 ACT-1 slice A (admission authority, #603 closed, main 64e2f05 era; Sol 6-round review to PASS) — Track B consumable. **INSTALL-1 slice A** (#607; AWC bootstrap PR #608; SRM PR #6 @ dc5e311): pure doctor (UNKNOWN-never-HEALTHY) + read-smoke (deny-by-default component-boundary allowlist, dot-reject policy) — GLM 2-round review, claim released; P3 ledger on #607 (doctor dot-entry alignment, target-corrupt reason label, probes-object hardening).
- **NEXT_READY**: INSTALL-1 slice B = pairing/enrollment wiring (consume existing `DeviceAuthenticator`/remote-device surfaces) + autostart/restart skeleton + installer entry in SRM; re-pin compat set {AWC@0c2ff17-or-later, SRM@dc5e311-or-later}; WO-P1-607 governs; fresh claim per slice.
- Human gates unchanged: (1) A-Wiki PR #67 merge (unblocks #551 -> WO-P1-561 -> JEV chain); (2) WO194->#285->#293 stack disposition (folds #581/#583).
- Codex binary: 5ea220ae823df3d7/codex.exe (0.160.1). Known env note: SRM supervisor fault-suite has an intermittent `kill ESRCH` child-race flake in the long-lived reference worktree (same-SHA differential proved timing, not code).

**Exact next safe action:** fresh session/wake -> claim INSTALL-1 slice B per WO-P1-607 (SRM-side worktree, cross-repo pin) -> RED-first pairing-state + autostart modules.


## 2026-10-07 (later) — P8 ACT-1 slice A COMPLETE — CURRENT

> Cross-repo projection; live evidence overrides. Windows ZCode GLM-5.3 MAX primary; watchdog automation active (30-min, WATCHDOG_ONLY).

- Current main: `64e2f0552a659d6d8e39f1f26965f8d742fb1954` (post-main CI 37604652509 SUCCESS). A-Wiki main 16897b2d (PR #67 human gate unchanged).
- **P8 ACT-1 slice A COMPLETE/POST_MAIN_VERIFIED** (Issue #603 closed): bootstrap PR #604 (WO-P1-603) + source PR #605 (head `965f5a6` -> merge `64e2f05`): pure admission authority `command_gateway.py` — action-derived intent (no label escalation), universal scope coverage with component-boundary/traversal rejection, observed 4-field identity truth, exact-bool lease, UNKNOWN-dedupe never relaunch, fence-held-here for MUTATE, fully-validated collision-free evidence digest (22 enumerated inputs), contained authority errors (AUTHORITY_ERROR vs typed absent-evidence codes), zero side effects. **Codex Sol 6-round review to PASS 0/0/0/0** (each round found real gaps; final closure reviewer-enumerated); 51 focused + 117 related green.
- **Roadmap next**: ACT-1 slice B = dispatch wiring consuming admissions (separate claim; existing adapters); then #498B PRE_MUTATION / #498D PRE_MUTATION guard wiring against the admission digest; P9+ per live roadmap. P7 remainder (extension/desktop) optional.
- Human gates unchanged: (1) A-Wiki PR #67 merge (c1bf7ea4; unblocks #551/PR #552 -> WO-P1-561 -> JEV); (2) WO194->#285->#293 stack disposition (folds #581/#583).
- Codex binary: `C:\\Users\\aase7en\\AppData\\Local\\OpenAI\\Codex\\bin\\5ea220ae823df3d7\\codex.exe` (0.160.1).

**Exact next safe action:** fresh session -> recover live roadmap -> claim ACT-1 slice B (dispatch wiring) or #498B/D guard wiring per dependency truth; fold PR #67 merge instantly when decided.


## 2026-10-07 — overnight marathon: P6 MON-1 + P7 UI-1 COMPLETE — CURRENT

> **Cross-repo projection.** Actual Git/GitHub evidence overrides this section. Windows ZCode GLM-5.3 MAX primary; overnight goal 2026-10-06.

- Current A-Wiki-Conductor `origin/main`: `a4614b404052ac7f678566a5652573b531d7c53f` (post-main CI 37554312927 SUCCESS). A-Wiki main `16897b2d` (PR #67 human merge gate unchanged; packet PR #67 comment 6008933648).
- **P6 MON-1 COMPLETE/POST_MAIN_VERIFIED** (Issue #596 closed): contract WO-P1-596 (PR #597) + source PR #598 (head `d0d65e7` -> merge `08f4fa6`): loopback stdlib read-only monitor API (`monitor_api.py` + `monitor_projection.py`, 30 rows) — fail-closed token/Origin/Host authn (duplicate-header rejection, DNS-rebinding guard), per-subscriber bounded stream backpressure, generation-fenced poller lifecycle (STOP_INCOMPLETE/POLLER_TERMINATING), typed 503 boundaries. Codex Sol 3-round review (final PASS 0/0/0 after 2 repair cycles); two runtime-dependent duplicate-Host CI flakes root-caused + fixed.
- **P7 UI-1 slice A COMPLETE/POST_MAIN_VERIFIED** (Issue #599 closed): bootstrap PR #600 (WO-P1-599) + source PR #601 (head `d1aaa5a` -> merge `a4614b4`): constant self-contained read-only monitor page (`monitor_page.py`) + one authn-gated `GET /monitor` route — CSP, memory-only fragment token, UNKNOWN/STALE/DEGRADED truthful badges, fatal-403 halt + 503 backoff. GLM 3-round review (final PASS "acceptable to integrate"); 40 focused + 715 reviewer-side green.
- **Next roadmap node: P8 ACT-1 Command Gateway** — AUTHORITY SEAM, higher scrutiny (goal section 5): needs fresh dependency/readiness recovery + reuse audit + governance bootstrap before any implementation; R3 RED-first mandatory. P7 remainder (extension UI/desktop adapter) = optional later slices.
- Human gates unchanged: (1) A-Wiki PR #67 merge (c1bf7ea4, review PASS + CI PASS; unblocks #551/PR #552 -> WO-P1-561 -> JEV chain); (2) WO194->#285->#293 stack disposition (blocks #581/#583 DEFECT_LESSONS folds).
- Codex binary moved: use `C:\\Users\\aase7en\\AppData\\Local\\OpenAI\\Codex\\bin\\5ea220ae823df3d7\\codex.exe` (0.160.1). Reviews this cycle used separate GLM read-only lanes per quota policy.

**Exact next safe action:** fresh session -> recover P8 ACT-1 roadmap/WO state (does an accepted ACT-1 contract exist? roadmap P8 + #498B/C/D dependencies) -> bootstrap/claim under normal gates; fold PR #67 merge instantly if the human decision arrives.


## 2026-10-06 — authorized 3-lane cycle complete — CURRENT

> **Cross-repo projection.** Actual Git/GitHub/runtime/durable evidence overrides this section if it drifts. Windows ZCode GLM-5.3 MAX primary session; user authorizations: A-Wiki PR #67 comment 5997302206, #547 comment 5997303506, PR #293 comment 5997304803.

- Current A-Wiki-Conductor `origin/main`: `2e770f3f00670a7bd3ea1135bfec932aa445c15d`. A-Wiki `origin/main`: `16897b2d34f3ff0de0938f7f651cf19bbce106b43` (PR #67 unmerged).
- **LANE A — A-Wiki PR #67 bounded repair: REVIEW_AND_CI_COMPLETE_MERGE_AUTHORITY_REQUIRED (halted at authorized gate; NOT merged).** Candidate `c1bf7ea41648fcd16e2b753e75847c86a7d86648` on `fix/issue-58-claim-convergence` (worktree `A:\GitHub\_worktrees\A-Wiki-pr67-claim-repair`): P1 fail-closed durable COLLAB parse (`DurableClaimsUnavailable` → `DURABLE_CLAIMS_UNREADABLE` exit 2; absent-COLLAB isolation preserved) + P2 comma-scope writer rejection with writer/reader/hook parity. Targeted 97×2 + related 183 green; `conductor verify` + pre-commit AWiki gates pass. Independent review (separate GLM read-only lane; Codex quota-blocked → fallback): **PASS P0/P1/P2=0** with two recorded P3 hardening notes (override-missing semantics; tolerant-reader rows). Hosted CI on `c1bf7ea4`: Core verification + loop-contract + py38-smoke ALL PASS. Evidence: PR #67 comments 6000295930 / 6000436550. Windows TTL claim `79c57dbe9ffc` (zcode-glm-pr67) expires naturally ≤2h; durable COLLAB row (chatgpt-sol) governs. **Merge decision = user/integrator.**
- **LANE B — #285/#293 supersession audit: COMPLETE (READ_ONLY).** `PR285_DISPOSITION = PR293_DISPOSITION = HUMAN_DECISION_REQUIRED` with 9-question evidence: marker/classification logic NEVER on main (main still has the broad-substring guard at `instance_create.py:83-84` — defect family live); the stack sits on the UNMERGED WO194 base `8339e4c` (main@46f90b3 Sep-11 → WO194 → #285 → #293); DEFECT_LESSONS numbering collision (#15). DEFECT_LESSONS.md path lock therefore cannot be released by closing the drafts — #581/#583 folds stay queued behind the stack decision. Evidence: PR #293 comment 6000531474, PR #285 comment 6000531941.
- **LANE C — STM-1B: COMPLETE / POST_MAIN_VERIFIED / claim released.** WO-P1-592 / Issue #592 (closed) / bootstrap PR #593 / source PR #594 (exact reviewed head `7853755`, merge `2e770f3`, post-main run `37363409584` SUCCESS after one documented infra-flake rerun with zero failed steps). New `hook_producer_wiring.py` + 26-row focused suite; review round 1 CHANGES_REQUIRED → repair cycle 1 → round 2 **PASS 0/0/0** (separate GLM lanes). Deferred P3: unpaired-surrogate session_id typed-rejection wrap. Composition-root hookup = separate future scope.
- Codex 0.160 quota exhausted during this cycle (reset ~2:54 AM local); both independent reviews used the accepted separate-GLM-read-only-lane fallback. Working Codex review recipe: `codex exec -s read-only --ephemeral -o <file> -` (default model gpt-6.1-sol).
- Next SAFE_READY candidates: user/integrator merge decision on A-Wiki PR #67 (unblocks #551/PR #552 → WO-P1-561 → JEV chain); WO194→207→215 stack disposition; #580 lifecycle vNext hook implementation; #541 SRM compact receipts.

**Exact next safe action:** obtain the A-Wiki PR #67 merge decision (or merge it under integrator authority), then harvest #551/PR #552 claim-reader acceptance and resume the WO-P1-561 JEV SHADOW chain.


## 2026-10-05 — Windows ZCode primary topology / WO-P1-583 COMPLETE — CURRENT

> **Current cross-repo projection.** Actual Git/GitHub/runtime/durable evidence overrides this section if it drifts. Written by the Windows ZCode GLM-5.3 MAX primary marathon session (user topology recorded in Issue #580 comment, 2026-10-05).

- Current `origin/main`: `ece314530a05f12bd1f7bc4517dd6e287197fb4d`. Supervisor workspace `A:\GitHub\_worktrees\A-Wiki-Conductor-zcode-supervisor` was clean at `6ad9fdd` at session start.
- **WO-P1-583 queue-submission dedupe guard: COMPLETE / POST_MAIN_VERIFIED / claim `WO-P1-583-QUEUE-DEDUPE-GUARD-WIN-001` released** (Issue #583 closeout comment `5993506599`). Bootstrap PR #589 (WO contract v2) + source PR #590 (exact head `a08844f`, two new files: `codex_queue_submission_guard.py` + focused tests). Independent Codex GPT-6.1 Sol review round 1 CHANGES_REQUIRED (P1 partial-pagination PROCEED, P2 unbounded evidence) → contract v2 repair → round 2 PASS 0/0/0 → expected-head merge → post-main runs `37298845083`/`37300729945` both SUCCESS. Assurance: `runs/WO-P1-583/assurance/` in worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-wo583-queue-guard` (ignored).
- **#576 Phase C harvested**: post-main CI `37260168794` SUCCESS; claim `WO-P1-576C-APP-SERVER-0160-SOURCE-MAC-001` released (Issue #576 comment `5992112857`).
- **JEV production rollout (goal Phase 0) = BLOCKED_UPSTREAM, not forgotten**: JEV-2/3/4/5 core all merged/post-main; production OFF. Remaining live-SHADOW lane WO-P1-561 (Issue #508) is blocked by claim-reader #551/PR #552 ← A-Wiki PR #67 (two open review findings: P1 fail-closed COLLAB.md parse, P2 comma-glob mismatch) ← **A-Wiki mutation requires explicit user authority** (repo AGENTS.md; AUTHORIZATION_REQUIRED surfaced in marathon receipts). Mac-side WO-P1-561 claim stale since 2026-09-27; Windows may recover/transfer it only after the claim-reader prerequisite lands.
- **DEFECT_LESSONS fold queue**: #581 and #583 folds both `BLOCKED:DEFECT_LESSONS_PATH_COLLISION` by stale draft PR #293 (WO-215 launcher lane, unmerged, base not main; sibling stale draft #285). One user/integrator reconciliation decision unblocks both folds + the path.
- **Next SAFE_READY mutable lane candidates** (no active mutable lanes at this checkpoint): #547 STM-1B producer wiring on the merged Hook Bus (separate claim per WO-547 successor boundary); #580 lifecycle vNext hook implementation (candidate scope `.codex/hooks/a_sunday_lifecycle.py`); #541 SRM compact receipts (EXECUTION_SUBSTRATE); #555 PWA. GLM/ZCode preferred executor per capability matrix + 2026-10-05 topology.
- Codex escalation route proven this session: Desktop binary `...\OpenAI\Codexin\8aaf1547b825b104\codex.exe` 0.160.0; `codex exec -s read-only --ephemeral -o <file> -` works for bounded read-only reviews; default model = `gpt-6.1-sol`; `codex review --base` cannot combine with a custom prompt; review round-trip ≈ minutes and is quota-cheap for bounded diffs.

**Exact next safe action:** pick the next SAFE_READY lane from the candidates above through the normal entry/claim gate (STM-1B recommended if no newer live evidence changes it), or resolve the A-Wiki PR #67 authority gate to unblock the JEV chain.



## 2026-09-22 — WO473 DEPDIET-1 first removal slice COMPLETE / POST_MAIN_VERIFIED — CURRENT

> **Current cross-repo projection.** Actual Git/GitHub/runtime/durable evidence overrides this section if it drifts.

- Authority: Issue #473 / `docs/work-orders/WO-P1-473-srm-dependency-diet.md`; topology `EXECUTION_SUBSTRATE_ONLY`; risk R2.
- Canonical execution repo: local `A:\GitHub\SunDayRemoteMCP` with no configured Git remote.
- Accepted base: `2e6aeabd09a321232098187dba4c522e37e4b1de`.
- Accepted candidate and canonical SRM main after ff-only integration: `e3ec2e06baf464e68c4166faae65f51c60fd5477`.
- Exact mutation: `package.json` + `package-lock.json` only; removed direct roots `@tiptap/pm`, `remark`, `remark-gfm`, `remark-parse`, `unified`.
- Lock graph: 67 unreachable entries removed, 0 added, survivor semantics unchanged, and `@tiptap/pm` remains transitively reachable through retained Tiptap packages.
- Deterministic acceptance: build PASS; compact facade PASS; full-toolset facade PASS; focused supervisor PASS; atomic-write alternating BASE/CANDIDATE replay 3/3 each; UTF-8/diff/scope checks PASS.
- Full-run differential was base-compared: base 70/78 PASS vs candidate 69/78 PASS; no deterministic candidate-specific regression remained after targeted replays.
- Accepted independent GLM-5.3 MAX static/adjudicative R2 review: run `run:WO-P1-473:r2-static-review:a5:f05646ef0027`, PASS, P0/P1/P2/P3 = 0/0/0/3, exit 0, 2,620 security samples, no MCP descendant/scope violation.
- Earlier attempts 0001/0003 security-invalid, 0002 provenance-collision-invalid, 0004 prelaunch-invalid; none are acceptance authority.
- Post-main proof: canonical SRM HEAD matches the accepted SHA; protected `.serena` state hashes are unchanged; live Node runtime was not restarted.
- Claim `WO-P1-473-DEPDIET1-WINDOWS-001` is released by the #473 closeout. Parent #472 remains open for broader DEPDIET-1 feature-pack/audit scope.
- FRONTDOOR-1 remains gated on measured launch/setup friction. Issue #457 remains `HUMAN_DECISION_REQUIRED` and is not advanced by this closeout.

**Exact next safe action:** complete the A-Wiki closeout merge/Issue #473 closure, then keep #472 read-only until a new bounded dependency/feature-pack candidate is proven or launch-friction evidence makes FRONTDOOR-1 READY.


## 2026-09-21 — WO438 COMPLETE; WO205 §14 released — CURRENT

> **Current authoritative projection.** Actual Git/GitHub/runtime/durable evidence overrides this file if it drifts.

- Topology: `CONTROL_PLANE_ONLY`. Canonical authority: Issue #438 / WO-P1-438. Historical predecessor only: Issue #330 / WO-P1-246.
- WO438 merge SHA: `75d9e96e46e15cc8ef647d12194d677657689bde`; current remote `main` is `894c64d32ca63dd0bfaf9f23d97a3e1180ce09d7` after disjoint PR #440 continuity drift.
- PR #336 merged at 2026-09-21 06:20:49 +07 from exact candidate `f93e16377f500d16cbed66763058c2f4a2237790`.
- Independent GLM-5.3 MAX exact-SHA R3 review finished before merge: `PASS`, P0/P1/P2=0, P3=3 non-blocking. Durable result: `A:\GitHub\_worktrees\A-Wiki-Conductor-review-wo438-f93e163\runs\WO-P1-438\r3-review\attempt-0001\result.md`.
- Exact-head hosted CI #1102 / run `35529389831` finished before merge: `SUCCESS`; Windows, Ubuntu and macOS jobs all green.
- Detached post-main verification worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-post438-75d9e96`.
- Post-main local proof: all 11 WO438 blobs are byte-identical to the reviewed candidate; focused set 177 PASS; work-order identity 33 PASS; `git diff --check` PASS; `py_compile` PASS.
- The post-main wrapper returned exit 1 only after all gates because the PowerShell harness used unsupported three-argument `[Math]::Max`; this is harness-only, not a test/repo failure.
- Hosted post-main push CI run `35544371466` on exact `75d9e96...` is **SUCCESS** on Windows + Ubuntu + macOS, including core suites, Portable/Setup build, archive verification, Portable smoke, and Setup install/uninstall E2E.
- Issue #438 is **CLOSED / COMPLETE / POST_MAIN_VERIFIED**; claim released. Issue #214 comment `5753611455` releases WO205 §14 source-gate work only.
- Protected root `A:\GitHub\A-Wiki-Conductor` is stale at `1a5ea1b...`, 16 commits behind current main, with pre-existing untracked `$null`, `0`, and `docs/prompts/GLM-WO230-ZRA2-REVIEW-TASK-CONTRACT-AUTHORITY.md`; do not reset/clean/stash or use it for mutation.
- Session rollover checkpoint branch: `docs/wo-p1-438-session-handoff`; worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo438-session-handoff`.

**Exact next safe action:** in the new session re-pin actual main / Issue #214 / WO205, recover global WIP/collisions, create a fresh isolated Phase-D source worktree, execute WO205 §14 steps 1–7, freeze exact source/test scope, then RED-first implementation. `SAFE_TO_MUTATE_PHASE_D_SOURCE=NO` until that checklist completes.

## 2026-09-21 — WO433 RUNTIME-ACT-1 session rollover — CURRENT FRONTIER

> Projection only. Actual Git/GitHub/runtime/durable evidence overrides this section if it differs.

- Critical path: **#433 RUNTIME-ACT-1 -> #429 COCKPIT-1B -> LOCAL-USABLE-1**.
- Topology: `CONTROL_PLANE_ONLY`; source implementation has **not** started in this rollover session.
- Checkpoint remote main: `75d9e96e46e15cc8ef647d12194d677657689bde`.
- #215↔#433 bilateral split is durable: #433 owns explicit/manual activation; #215 exclusively retains automatic accepted-completion -> NEXT_READY continuation/provenance.
- Rollover claim/checkpoint: Issue #433 comment `5753493574`.
- Prior GLM-5.3-Flash source-scope assist was recovered as TERMINAL exit 0 on detached `d2ad5bd...`; it is advisory evidence only.
- Earlier source claim comment `5751797434` was based on `d2ad5bd...`; its old SAFE_TO_MUTATE verdict is stale and must be re-pinned before source mutation.
- Relevance diff `d2ad5bd... -> 75d9e96...` changes none of the frozen #433 source/test paths; related drift is only WO246 author-provenance wiring in `zcode_production_assembly.py`.
- Current main still has no `ZCodeJobBackend`; Claude durable job backend exists but the Claude harness rejects `PROJECT_MUTATION` with `HARNESS_MUTATION_NOT_READY`.
- First LOCAL-USABLE activation slice is therefore frozen as **explicit/manual READ_ONLY production activation** through the accepted supervised Claude durable backend.
- Mutation-capable harness support is successor scope; do not expand #433 implicitly.
- Frozen implementation scope: NEW `runtime_activation.py`; MODIFY `desktop_control.py`, `desktop_app.py`; `lifecycle_coordinator.py` only if a read-only observation seam is strictly required; NEW `test_runtime_activation.py`; MODIFY `test_desktop_control.py`; NEW `test_desktop_app.py` only if isolated CLI coverage is required.
- Hard forbidden: automatic NEXT_READY/successor selection, elastic provisioning, writable Graph Monitor/UI authority, new store/schema/task/request/retry/review/completion authority, Zero-Relay source, SunDayRemoteMCP, live installed DB mutation.
- A-Faster census found no matching live A-Wiki Kilo/Claude delegated process for #433. Windows and Mac RDC devices are online; chat-visible SunDay-Worker developer MCP remains unavailable in this harness.
- Legacy/stale execution pointers exist in old review worktrees; do not infer WIP occupancy from PID numbers. Reconstruct global WIP from exact pointer/process/Git/Issue evidence in the next session before dispatch.
- Next safe action: fresh-session ENTRY/recovery -> fetch/re-pin current main -> recover delegated runs/global WIP -> collision pulse -> create a clean isolated **R3 source implementation** worktree/claim -> RED-first manual READ_ONLY activation implementation -> deterministic verification -> frozen SHA -> independent MAX review/CI -> merge/post-main -> unblock #429.

## 2026-09-15 — R5 repair verified for freeze, R3 acceptance pending

Existing Kilo/cointh-glm/glm-5.3 MAX writer completed the packet at
`runs/WO-P1-223-RE2A/r5-task.md` from base
`779fcf5975e21d6891f63b94ad79893745776675`; result is in `r5-result.md`.
The R3 P1/P2 from Issue214 comment5683969698 drove four RED/GREEN cases:
true cross-dispatch loser/third contender, terminal-unusable cleanup,
legacy released-admission attribution, and prior-dispatch/successor cleanup.
Only execution source and its tests changed within the four-file source scope.
Integrator independently ran both focused suites: 109 passed; diff check passed.
Worker reports broader 222 focused +218 related tests; those counts are worker
claims pending acceptance evidence review, not independent reruns.

Freeze is for independent R3 review, not acceptance. Reviewer must challenge
whether ACTIVE admission actually proves the identity of the current owner-key
lease under release/recovery/expiry/reacquisition, and the newly retained lease
after partially completed cleanup. Do not dismiss those as out of scope merely
because the worker calls them theoretical. Existing authorities remain owners.
WO242/PR324 separately repairs the pre-existing SQLite initialization CI race.

`SAFE_TO_MUTATE_RE2A_SOURCE=NO` while frozen.
`SAFE_TO_MERGE_PR319=NO` pending fresh exact-SHA R3 and hosted CI.
Next: independently review the replacement commit; record exact SHA in the
ignored status packet and Issue214. Preserve root dirty work and other lanes.


Last updated: 2026-09-15 (GPT-5.6 Sol — WO223 RE2-A durable replay repair)

## WO223 RE2-A lost-handoff replay repair — authoritative

> **Single-authority rule:** this section is the ONLY current authoritative state in this file. Actual runtime/Git/GitHub and durable Issue state override this file if they differ. Historical evidence below the separator is evidence only.

- Driving durable authority: GitHub Issue #214. Active claim: `WO-P1-223-RE2A-LOST-HANDOFF-REPLAY-001`.
- Current critical-path task: `docs/work-orders/WO-P1-223-re2a-lost-handoff-replay.md`.
- Exact implementation base: `082705889e26023079e73deacb7f642eb122713b`; `origin/main` at claim = `67744e98e538b000579bff4a45616d3a178a824b`.
- Fresh isolated worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo223-re2a-replay`; branch `fix/wo-p1-223-re2a-lost-handoff-replay`.
- PR #319 remains OPEN/DRAFT at old head `42221020c02c507decfb396ac8c3b9da54d523bc`; DO NOT MERGE until replacement exact-SHA R3 review/CI/acceptance succeeds.
- RE2-A repairs only post-promotion lost-handoff replay: persist strict versioned exact resource identity in the existing execution promotion event, reconstruct exact historical lease/admission truth through existing APIs, keep zero second model effect, and preserve C1/legacy fail-closed semantics.
- Source/test scope is only `zero_relay_review_verification.py`, `zero_relay_review_execution.py`, and their two focused tests. No execution/job/provider/lease store/schema/state-machine/C1/Phase-D/WO227/A-Wiki/live-provider mutation.
- Pre-promotion `EXECUTING + VERIFICATION_REQUIRED` hard-crash liveness is separate RE2-B adjudication; RE2-A may not invent job lifecycle transitions.
- GLM-5.3 MAX is preferred bounded implementation engine after the continuity bootstrap commit; GPT-5.6 Sol retains trust/authority, fan-in, acceptance, PR/merge/post-main authority.
- File-first continuity is mandatory: tracked WO + this file + `handoff.md`; lane detail in ignored `runs/WO-P1-223-RE2A/{task.md,status.json,result.md}`; major boundaries mirrored to Issue #214.

One next safe action: commit the tracked continuity bootstrap, re-gate the clean exact worktree, then transfer the four-file RED-first RE2-A implementation to GLM-5.3 MAX while GPT runs independent read-only architecture/fault/integration lanes.
<!-- ================================================================== -->
<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->
<!-- Nothing below this separator is a current instruction.              -->
<!-- ================================================================== -->

## WO158 canonical authority final repair r6 — review 5560911492 — 2026-09-07 (GLM-1)

- r5 remains frozen at `0a123e8` (CI green). r6 closes the four fail-closed authority defects RED-first: (1) canonical admission status semantics — assembly requires `status='ACTIVE'` + released rule; REAL SQLiteProviderConfigStore integration evidence (save → acquire → ADMITTED kind → ACTIVE record accepted as-is; RELEASED/EXPIRED/wrong-provider/generation/batch/execution rejected); impossible `ADMITTED` fixtures removed; canonical store untouched. (2) dispatch project id REQUIRED (missing/blank ⇒ `ZCODE_DISPATCH_CONTEXT_MISSING`; mismatch ⇒ `ZCODE_PROJECT_MISMATCH`; identity uses the verified value). (3) explicit non-empty mutation scope REQUIRED, verified against allowed + lease-mutable + forbidden scopes via existing authority. (4) dispatch execution id REQUIRED with unconditional admission binding.
- Evidence: final-repair 30/30; authority 22/22; E2E 9/9; batteries 270/270 + 263/263; hygiene PASS; scope 1 production + 4 test files. Stop state READY_FOR_GPT1_EXACT_SHA_ACCEPTANCE at the r6 head; GLM1 does not merge.

## WO158 final targeted repair r5 — review 5560480061 — 2026-09-06 (GLM-1)

- Slices 1-4 remain frozen (`cf7ef9a`→`2de584a`, CI green). r5 closes every remaining item of binding review 5560480061, RED-first: derived `zcode-runtime-v1:<full sha>` runtime identity (no caller parameter; same-packet/two-model no-reuse proven live); admission bound to the independently-derived dispatch context (batch/execution); lease project identity into the durable record (hard-code removed), READ_ONLY rejection, and allowed/forbidden scope enforcement via the existing authority; bounded reader with typed `CHILD_OUTPUT_OVERFLOW` (deterministic flooding-child E2E); `finished_at` captured only at the real terminal-exit boundary (delayed-exit E2E); argv-evidence truth (Option B: launch evidence, not live-verified); `expected_base_url` assertion naming.
- Evidence: final-repair suite 19/19; E2E 9/9; focused battery 258/258 + 289/289; hygiene PASS. Stop state READY_FOR_GPT1_EXACT_SHA_ACCEPTANCE at the r5 head; GLM1 does not merge.

## WO158 final slice 4 - deep truth audit + source freeze - 2026-09-06 (GLM-1)

- Slices 1-3 frozen green (`cf7ef9a`, `958f051`, `c9e527a`; slice-2 CI green). Slice 4 = the full call-graph audit (20 steps, module/symbol/owner/evidence/fail-closed each) + dead/split-authority scan (16 candidate defects, all negative with closure evidence) + NEW real restart-after-complete E2E (fresh session reuses the durable execution, zero respawn) + full verification battery 245/245 + 263/263 + hygiene PASS. Honest declaration: ZCodeBackendAdapter remains a non-production seam (never constructed by the assembly).
- **Stop state: READY_FOR_GPT1_EXACT_SHA_ACCEPTANCE** at the final head (see WO repair-r4 checkpoint). PROOF_C NOT_RUN/GPT1_AUTH_REQUIRED; live dispatch separately gated; GLM1 does not merge.

## WO158 repair slice 3 — authority-bound assembly — 2026-09-06 (GLM-1)

- Slices 1-2 frozen with green exact-head CI (`cf7ef9a`, `958f051`).
- Slice 3 (review item 8, RED-first 21-test matrix): assembly consumes ONLY the canonical `WorkerLease` (worker/worktree-key/task/active/expiry bound; None/truthy fail closed) and canonical `ProviderAdmissionRecord` (provider/status/generation/expiry bound; None/truthy fail closed); worktree gate compares OBSERVED context vs the LEASE authority (caller expected-pair removed); endpoint truth = provider-snapshot `ProviderEndpointConfig` (caller defines only the request; `endpoint_base_url` param removed).
- Evidence: matrix 21/21; zcode+supervised 244/244; worker/provider 213/213; hygiene PASS. Remaining: PROOF_C + final call-graph truth audit (slice 4).

## WO158 repair slice 2 — full task identity + ATTACH_RUNNING + CAS truth — 2026-09-06 (GLM-1)

- Slice 1 (`cf7ef9a2334b203ffffc9f449c6d783e17c6a118`) is frozen with exact-head CI green (test 13m38s + ubuntu/macos smoke) and PR221 evidence comment 5560113468.
- Slice 2 (review 5558197043 items 5-7) executed RED-first: `zcode-task-v1:<full SHA-256>` domain-separated task identity (no `[:16]` truncation); `ATTACH_RUNNING` cross-process child reconciliation in the production launcher (exact live child ⇒ attach; reuse/mismatch/gone ⇒ recovery; result.json always wins); adapter SUCCEEDED-transition CAS failure now typed `ZCODE_DURABLE_STATE_TRANSITION_FAILED` — never apparent success; durable-first retry collects without duplicate execution.
- Evidence: new identity/attach/CAS suite 16/16; zcode+supervised battery 223/223; hygiene PASS. Remaining declared: authority-bound lease/admission/endpoint evidence (None passes consume gates), PROOF_C.

## WO158 / PR221 real specialized-helper happy path — 2026-09-06 (GLM-1, binding review 5558197043 slice 1)

- **PR #221 / WO-P1-158** was CHANGES_REQUIRED at `37ef020` (binding GPT1 review 5558197043): the real valid-helper happy path crashed pre-spawn (`NameError: Path`), production assembly still used the in-process adapter lifecycle, helper runtime handoff/identity/deadline were incomplete. Repair executed RED-first on branch `feat/wo-p1-158-zcode-zero-relay` (worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-wo158-zra1`).
- The REAL production chain now executes E2E and is proven by `tests/test_zcode_real_helper_e2e.py`: production assembly -> `SupervisedRunCoordinator` -> `SupervisedExecutionService` -> `ZCODE_APP_SERVER_V1` -> real `zcode_supervised_helper.py` subprocess -> exactly one fake app-server child -> protocol -> canonical artifacts -> durable collect, with all 14 acceptance points (packet re-verify TOCTOU, identity-before-send, exact OS child identity incl. creation time + helper parent PID, explicit-only credential child env, bounded deadline actually honored by `read_line(timeout)`, 64 KiB budget, report-before-result, six-key result only on real exit, no kill ladder, no traceback).
- NEW `zcode_process_truth.observe_child_process` (Windows kernel32 ctypes / Linux /proc / macOS ps, fail-closed). `assemble_zcode_execution` now REQUIRES real supervised-service authorities (typed `ZCODE_SERVICE_AUTHORITY_MISSING` otherwise); `ZCodeBackendAdapter` is no longer the production launcher.
- Verification: E2E + assembly + helper-execution 36/36 (deterministic re-run); zcode+supervised 247/247; provider/harness/claude 175/175; worker/lease 153/153; compileall / `git diff --check` / strict UTF-8 / added-line secret scan (0 hits) PASS. No live provider dispatch.
- Declared remaining (later slices): full collision-resistant task identity (packet SHA still truncated `[:16]`); cross-process ATTACH_RUNNING composition; typed launch-side CAS failure (adapter still swallows `SUCCEEDED` transition failure); authority-bound lease/admission/endpoint evidence (`None` still passes the consume gates); PROOF_C NOT_RUN/GPT1_AUTH_REQUIRED. GLM1 does not merge; GPT1 owns acceptance.

**One next safe action:** freeze this repair SHA on PR #221 -> GPT1 exact-SHA rereview -> (if accepted) Prompt-2 slices (task identity / ATTACH / CAS truth).

## Post-PR208 merge actual-state override - 2026-09-05 (HISTORICAL / SUPERSEDED BY WO162 2026-09-07)

- main = `f0ddd0b9245cef7a7525a670f470e1de595d4615`; PR #208 / WO154 is MERGED / RELEASED. Repaired head `5124ed18409d71df7b98e4455f0a4a2df6428695` passed independent rereview P0/P1/P2=0 and exact-head CI before merge.
- WO157 / PR #219 is the active workflow-successor lane. GPT-B recomposed it onto current main; new exact SHA still requires focused rereview + CI before acceptance.
- Formal ZRA-0 is NOT accepted/closed. Sacrificial migration mechanism/evidence is pre-proven with live DB untouched. WO155 `653eba9` remains preview/shaping evidence only.
- WO156 / PR #218 is MERGED / RELEASED on `main@aa257f47ac3d0979c9b749896745cab6ce197975` from accepted head `a1c37b03b3fad6e1485d4f925ac3fb7d018d236e`. Existing ConnectorRecovery remains source authority; installed exact-PID self-heal is still a separate GPT-A operational gate.
- PR #209 / incident-runbook evidence is MERGED / RELEASED on `main@f0ddd0b9245cef7a7525a670f470e1de595d4615` from accepted head `d0a2331fb5861e20c9ee26e32749aaf2f8bb11bf`; installed exact-PID self-heal E2E remains a separate operational acceptance gate.
- PR #211 coordination SSoT head is `053fa2a5cca6fbef701213d1684cb02290173327`. W1 0.0.14 canary remains protected.
- PR #204 / WO152 remains scope-blocked at `9c90c873493b657cced86652c09c0e19920d99c8`; consolidation analysis says no production source repair is needed. Defer mutation until after ZRA-0..4.
- Protected root checkout remains stale/dirty; use isolated worktrees only.

Canonical order: `WO157 binding -> formal ZRA-0 -> ZRA-1 -> ZRA-2 -> ZRA-3 -> ZRA-4 -> WO152/#204 -> ODP-1..8 -> ZRA-5 -> ODP-9 -> WO096/release`.

One next safe action: freeze/review/CI WO157 on current main, then GPT-A acceptance; installed self-heal E2E planning may proceed in parallel without live runtime mutation.

## WO154/WO155 execution override — 2026-09-04 (historical; sequencing superseded above)

- Authoritative remote main after WO153 / PR #205 merge: `68079e3d00047ca9432f0aefe3ad667f892614d0`; WO153 is RELEASED and its hotspot ownership is no longer active.
- PR #208 / WO154 is the active binding-process lane. Current branch is composed with `main@68079e3...`; it defines risk-tier R0-R3 execution, frozen-candidate review, progressive verification, WIP `3 mutable + 1 review`, and one-feature-PR-by-default policy.
- P0 accelerator is now `WO-P1-155` / `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md`: eliminate human GPT↔GLM/external-agent copy/paste before resuming non-required ODP feature expansion.
- Priority sequence: `WO154 accept/merge -> formal ZRA-0 acceptance/reconciliation using pre-proven migration mechanism -> ZRA-1 automatic one-task dispatch -> ZRA-2 automatic result/review/repair -> ZRA-3 automatic NEXT READY continuation -> ZRA-4 bounded parallel isolation -> broad ODP continuation`; ZRA-5 remains the later ODP routing/integration seam.
- ZRA target metric: `human relay actions per external-agent task = 0`. ZCode UI automation is not the preferred architecture; reuse the accepted provider-neutral Claude-style harness/provider authority where eligible.
- Current live Control Center DB must not be mutated blindly. Prior inspection showed the running DB lacked provider tables; ZRA-0 must prove migration on a copy/isolated DB before any live migration.
- PR #208 remains R2 and requires an independent exact-SHA read-only review before merge. Same-session self-review is not sufficient independence.
- WO096 remains an independent P0 v0.7.0 release blocker; zero-relay work does not bypass its live hosted remote MCP-after-TTL acceptance gate.
- Protected root checkout remains stale/dirty; all mutation stays in isolated worktrees.

### Immediate execution order (superseded by the PR208 review-repair override above)

1. Freeze/review/accept PR #208 from current main composition.
2. FORMAL ZRA-0 ACCEPTANCE REMAINS PENDING. Its prerequisite migration mechanism/evidence is pre-proven; do not treat that proof as node acceptance. Follow the authoritative override above.
3. Progress ZRA-1 -> ZRA-2 -> ZRA-3 -> ZRA-4 under R3 trust/provider gates and deterministic evidence.
4. Only after ZRA-4, resume broad ODP feature lanes not required by the zero-relay path; reconciliation/readiness work may proceed in parallel when it does not consume required mutable lanes.
5. Keep WO096 fail-closed until its separate live authorization/evidence gate is satisfied.

## WO153 operational reliability override — 2026-09-03

- ZCode `config.json` rename/lock failures were traced to external Windows file-handle contention, not repository corruption or malformed JSON.
- Exact observed holder was Desktop Commander Node.js PID 15728 (`@wonderwhy-er/desktop-commander`) after broad search activity traversed `%USERPROFILE%\.zcode\v2` during ZCode writes.
- Recovery stopped only the identity-verified child PID; afterwards exclusive open + JSON parse passed and the ZCode log produced no new lock/rename errors in the verification window.
- Prevention is now durable in `AGENTS.md`, `DEFECT_LESSONS.md` #51, `docs/runbooks/zcode-config-lock.md`, and the read-only `scripts/diagnose_zcode_config_lock.ps1`.
- This is an operational reliability lane only; it does not change AHA/AiPASS/product frontier ownership or authorize live provider/tunnel mutations.

## WO146 authoritative actual-state override — 2026-09-03 (HISTORICAL / SUPERSEDED)

Actual Git/GitHub evidence below supersedes older frontier/status text later in this file.

- `origin/main = 37039a0e1dceb6256e3ee384bd7fa6ffb2737997`; WO144 / PR #195 + closeout PR #196 remain RELEASED. WO145 / PR #198 exact head `93f9a4089526f70a39adc3b97d3db55d6c8c6b3e` passed independent GLM rereview P0/P1/P2=0, GPT 160/160 related tests, exact-head CI `33706012375`, merged as `37039a0e1dceb6256e3ee384bd7fa6ffb2737997`, and post-main CI `33708033393` SUCCESS.
- A-Wiki Review Bridge PR #50 exact head `b04761d580ddcdc7eb682e3a6036078b3b346953` passed Core CI `33682384067`, Loop Gate `33682383989`, independent GLM rereview PASS P0/P1/P2=0, merged as `588a907200e0d4998ec4fbb7fb2178b89d9700b2`, post-main `33704270521` SUCCESS. The adapter dependency is RELEASED; A-Conductor must still reuse ReviewBus via the approved CLI boundary and must not create a second lifecycle authority.
- PR #183 / WO132 AiPASS is the next shared-doc product-planning lane; reconcile it against current main before new CI. Live AiPASS automation remains `BLOCKED_EXTERNAL` under current Terms §3.4.
- WO145 / PR #198 is RELEASED on main `37039a0e1dceb6256e3ee384bd7fa6ffb2737997`; post-main `33708033393` is SUCCESS. This repair addresses the Windows `terminate_returned=False` / `PROCESS_STOP_FAILED` incident that caused PR #197 run `33707457065` to fail on the older main; PR #197 must therefore be re-composed and re-tested on current main rather than rerun unchanged on the stale base.
- WO147 thin review-mailbox adapter is CLAIMED / RED_FIRST in `A:\GitHub\A-Wiki-Conductor-wo147-review-mailbox-adapter`; mutable scope is only the new adapter, focused tests, and WO147. Shared SSoT/PR #183/WO145 are forbidden in that lane.
- WO096 remains the P0 operational release blocker and live maintenance remains `AUTHORIZATION_REQUIRED`.
- Protected root checkout remains stale/dirty; mutation stays in isolated worktrees.

### Immediate execution order

1. Reconcile and release PR #183 from current main with fresh exact-head CI/post-main proof.
2. Re-compose PR #197 on released WO145 main `37039a0e...`, refresh this five-doc SSoT delta, and require a fresh exact-head CI before merge.
3. Let claimed WO147 continue independently through RED?GREEN?verification?independent exact-SHA review; do not touch its mutable scope from this lane.
4. Claim AIP-1 after PR #183 acceptance; keep live AiPASS traffic disabled.
5. Keep WO096 fail-closed until explicit maintenance authority exists.

## Actual-state reconciliation — 2026-09-03

**Actual GitHub/repo/runtime evidence supersedes older frontier text below. WO140 and WO143 are released; PR #183/AiPASS is the next bounded product-planning lane, while WO096 remains the independent P0 operational release gate.**

- `origin/main = cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`: WO144 / PR #195 merged from exact docs head `f2d33ed2d63454e6b7f547a016abb07f058d89be`; post-main CI `33704062299` SUCCESS. WO144 coordination claim is released by this final closeout; PR #183 / WO132 is next.
- WO140 / PR #193 is RELEASED. GLM diagnosis candidate was independently reviewed by GPT; GPT found and repaired one P2 bounded-memory defect with `deque(maxlen=64)`. Final head `2238259e264991e1249d1439b206dc9b252c3051`; exact-head CI `33678036552` SUCCESS; merge `787e9be2f108ce3f323bebc20127eb03c2958bfc`; post-main CI `33679432865` SUCCESS.
- WO143 / WO134-R1 is RELEASED. Original reviewed feature head `9c41da768713e3ad1c6d948f420b1110ea49afe6`; after WO140 main drift, merge-composed exact head `720d0328c02f7068d34cc3a5ae31418a9b1ede4b` preserved all 7 reviewed feature blobs byte-identically. GLM exact-head rereview PASS P0/P1/P2/P3=0; exact-head CI `33680012267` SUCCESS; PR #194 merged as `272953a366f93a7f7dbd8e1e8060fc0f1bacdb88`; post-main CI `33681115738` SUCCESS, completing the release verification gate.
- PR #183 / WO132 AiPASS is next after WO144. Draft head `085a06cf6d2d1d1e4a3b5085ad51ad3444a8b337`; prior CI `33662059825` green. Fresh audit confirms `niawjunior/aipass-bridge@b1b8bab757d91c266410d58f505aeeaa218da102` and MIT LICENSE blob `17ddd0b8425c523d029917a1027d7e40a0916100`; official AiPASS Terms effective 2026-08-19 section 3.4 prohibit bot-emulation/unapproved software and direct API/API Key/Token access outside the provider-defined UI **unless explicitly authorized in writing by the project**. Live automation remains fail-closed until an official supported path or explicit written authorization covers the intended mode. Current PR #183 conflict is confined to `COLLAB.md`; roadmap text needs WO143/current-main reconciliation.
- WO096 remains the P0 v0.7.0 operational release blocker. Read-only fleet refresh: 18011/18013/18014 listening; 18012/18015 stopped; shared live tunnel-client remains 0.0.11. Stopped does not mean available: Worker2 retains pharmacy cycle `PO-2026-08-26-001` / `RECONCILE_RECEIPT`; Worker5 retains sunday-estate worktree/branch continuity. No live maintenance authority is inferred.
- A-Wiki Review Bridge remains dependency-blocked on independent acceptance only. Current candidate `b04761d580ddcdc7eb682e3a6036078b3b346953` / PR #50 is Draft, mergeable CLEAN; Core CI `33682384067`, Loop Gate `33682383989`, and py38 smoke are SUCCESS. The bridge repairs were GPT-authored, so a fresh independent exact-SHA rereview with P0/P1/P2=0 is still mandatory before Ready/Merge. Do not implement a parallel ReviewBus or bind to the Draft API as accepted authority.
- Protected root checkout remains stale/dirty; use isolated worktrees only.

### Immediate execution order

1. Reconcile PR #183 against current main `cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`, preserve released WO140/WO143/WO144 history, and refresh current AiPASS evidence before new exact-head CI.
2. After PR #183 acceptance, claim AIP-1 from then-current main with a fresh reuse/authorization gate and no live traffic.
3. Continue read-only A-Wiki Review Bridge polling; implement adapter only after accepted exact A-Wiki SHA/API.
4. Keep WO096 fail-closed until explicit maintenance authority exists; do not publish stable v0.7.0.

## Current phase (HISTORICAL snapshot, 2026-09-03 era — superseded by WO162; the undated "Active work orders"/"Immediate execution frontier" sections below are part of the same snapshot)

**AHA-7 Models & Agents remains the active product frontier. WO127 and WO128 are accepted/released. WO134 historical T2-T4 evidence detail merged, but post-merge WO134-R1 is now the active dependency-blocking product defect and requires a fresh bounded remediation SHA; historical review/CI cannot close it. GPT remains integrator/merge authority. P0 WO-P1-096 remains the v0.7.0 operational release blocker.**

Accepted / active frontier state:
- PR #174 / WO124 reviewed exact head `be97d313c748fe5fcce0e57ecf5dc304b863e230`; GLM review002 PASS with P0/P1/P2 = 0; task SHA-256 `abe750450dda09dbf423681811efd0110ecfa26914cc55828b133db48a9fcf2b`; exact-head CI `33497483113` attempt 2 SUCCESS; merged as `c1cfbe780e76d3a64fb692e91dde851824bd8033`; post-main CI `33504441646` attempt 2 SUCCESS.
- WO124 establishes the truthful read-only operator model: `CONFIGURED != READY`, `READY != AUTHORIZED`, existing readiness/quota authority is reused, invalid generations fail closed, and secret/endpoint values are excluded.
- PR #176 / WO129 reviewed exact head `661c86f9a30433006a01e996ed1ea46fde4a7e52`; GLM review001 PASS with P0/P1/P2 = 0; task SHA-256 `b211091c4bfdc6c063da1ad037dc2a340750a90a47d813443e27c0bfa9c26481`; exact-head CI `33503763313` SUCCESS; merged as `fae5c0d8a36a41eb172e2acb8dc88ca04658c4e9`; post-main CI `33509029840` SUCCESS including Windows Portable/Setup and Frozen install/uninstall E2E.
- WO129 permits bounded post-termination UNKNOWN re-observation only after exact-PID termination succeeds; it never retries termination, never tolerates MISMATCH, and preserves PID metadata when exit ownership remains uncertain.
- PR #178 / WO125 reviewed exact head `91f77731d472d23c624bef22891b9cd400e6c090`; GLM long-goal review PASS with P0/P1/P2=0; exact-head CI `33528331266` SUCCESS; merged as `23b988764a3529f0721375f5d0a0c885b715ad46`; post-main CI `33534118110` SUCCESS including Windows Portable/Setup/Frozen E2E. Ultra final review exhausted quota before writing a result and was not used as merge authority.
- PR #179 / WO126 reviewed exact head `eee3e0e202b27c685f63c222ff10646ae667987e`; GLM task `wo126-glm-review-001` (task SHA `5d5ce849018f42db9adb6043ae0457230abbaa4d0ee8ddab4684927fc877644f`) PASS with P0/P1/P2=0; exact-head CI `33540512066` SUCCESS; merged as `010ab4bdefbe54725388a5cea936117b8eb93b6b`; post-main CI `33544097620` SUCCESS including Windows packaging/Frozen Setup E2E.
- WO126 preserves `CONFIGURED != READY != AUTHORIZED`, async/single-flight Settings reads, typed empty/error truth, stale-dialog guards, safe provenance only, and zero endpoint/credential/raw-secret UI exposure.
- PR #182 / WO127 exact head `e91647a7ccaefe522b11ba867719b3186ed5b96d` passed GLM rereview002 with P0/P1/P2=0 and CI `33582451656`; merged as `b0eed29656cc54031b7442348449d57cf55d23be`; post-main `33585602021` SUCCESS.
- PR #184 / WO128 core exact head `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad` passed GLM review002 with P0/P1/P2=0 and CI `33586307363`; merged as `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`; post-main `33591789871` SUCCESS. Truth remains `SELECTION_REASON=UNKNOWN`, `FALLBACK_REASON=NOT_EVALUATED`.
- PR #186 / WO135 defect-memory exact head `a3f51ca6a403724a1b7228a239d4965ced28bfad` passed CI `33607169866`; merged as `0ac30eb3a452327e01e9a6bad18ce0676aadf1f3`; post-main `33608067520` SUCCESS.
- WO134 T2-T4 Provider Evidence Detail is CLAIMED in `A:\GitHub\A-Wiki-Conductor-wo134-provider-evidence-detail`, branch `feat/wo-p1-134-provider-evidence-detail`; GLM owns its declared UI/control/test scope and GPT must not overlap it.
- PR #180 / WO131 exact head `554c2b1003d12cd211712393ecf61c034b1a8003` passed exact-head CI `33543935682` and merged externally as `af7a933fe27d2a3e3f29360abf9214df1e5478c5` before the planned GLM review result existed; post-main CI `33545560617` is SUCCESS. This is accepted runtime evidence with an explicit process deviation, not retrospective independent-review evidence.
- P0 WO096 remains operationally open: no live Worker/tunnel mutation is authorized by this roadmap work; public v0.7.0 remains blocked pending the required hosted remote MCP-after-TTL proof.

## Active work orders

1. `WO-P1-134` - ACTIVE / GLM OWNED: T2-T4 Provider Evidence Detail in isolated worktree; GPT remains integrator/merge authority and must not overlap mutable UI/control/test scope.
2. `WO-P1-096` - P0 operational release gate; live Worker/tunnel mutation remains unauthorized; v0.7.0 publication blocked.
3. `PR #183 / WO-P1-132` - separate draft AiPASS roadmap lane; semantic reconcile required before merge, no overlap from WO136.
4. `WO-P3-136` - GPT docs-only shared SSoT closeout for accepted WO127/WO128/WO135 state.

## Immediate execution frontier

1. Complete WO136 docs-only reconciliation, exact-head CI, merge, and post-main verification.
2. Preserve WO134 ownership; consume its declared result only after GLM finishes and then independently review exact candidate identity, tests, secret/UI truth, CI and merge gates.
3. Reconcile PR #183 against current main and fresh AiPASS authorization/source evidence in its own separate claimed lane before any merge or AIP-1 implementation.
4. Keep WO096 fail-closed until explicit maintenance authority permits the isolated v0.0.13 hosted-after-TTL proof; do not publish v0.7.0.

## Source-of-truth rule

Do **not** reconstruct task state from chat memory. Use actual repo/GitHub state → CURRENT-WORK.md → handoff.md → active work order → PROJECT-PLAN/contracts.

## Verified completed work (this session, main `2da3d01`)

- **PR #35**: E2E real-system suite (24 tests) + rebind regex fix + `open(instances_root=...)`.
- **PR #36**: display name → **A-Sunday Conductor** (branding.APP_NAME single source).
- **PR #38–#39**: `scripts/build_installer.py` (payload assembly + PyInstaller Setup build, shares the cosmetic-PE AV hardening), `THIRD-PARTY-NOTICES.md` (full Serena MIT text, bundled into every install), `branding.APP_VERSION` 0.2.0 synced with pyproject, `_install_files` extraction + icon regression fix found by the real Setup run.
- **Public release v0.2.0**: repo flipped public (explicit user decision 2026-08-22, recorded in COLLAB.md); https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.2.0 with `A-Sunday-Conductor-Setup.exe`, `A-Sunday-Conductor-Portable.exe`, `THIRD-PARTY-NOTICES.md`; anonymous download verified (HTTP 200). Secret scan clean before flipping.
- **Local machine**: real `A-Sunday-Conductor-Setup.exe` ran end-to-end (files + shortcuts + HKCU + frozen uninstaller); smoke `A-CONDUCTOR_SMOKE_OK projects=4 workers=3` — user DB preserved.
- **Console window retitling (local files outside repo, user-authorized, `.bak` backups)**: all 13 `.cmd` launchers under `C:\AI\serena-instances\{conductor,phase6,wastewater}\` now set `title` — `Sunday-works 1 - Conductor`, `Sunday-works 2 - Phase6`, `Sunday-works 3 - Wastewater` (+ `- Stop/Status/Configure/Provision`, watchdog = `Sunday-works 3 - Wastewater Watchdog`); `watchdog.ps1` embedded title aligned. `Start-*.cmd`/`Stop-*.cmd` glob uniqueness preserved; Status script re-run OK after edit.

## Verified completed work (WO-P1-060, main `f7911db`)

- **PR #42 Worker CRUD**: `+ Worker` / `Rename` / `Delete` buttons (WORKERS bar). Add auto-picks the next free `a-worker-NN` (max+1, no reuse), rename touches display name only, delete requires unassigned + STOPPED.
- **PR #43 Connector create**: `+ ตัวเชื่อม` button + dialog (name / project / optional Tunnel ID). Materializes the validated layout from a live reference instance (shared tunnel paths parsed from its `instance.ps1`), port auto-allocated, Start/Stop windows titled `Sunday-works N - <Name>`.
- **PR #44 Connector manage**: `แก้ชื่อ` (alias in `instance_display_names`, folder untouched) and `ลบ` (stop-first via orchestrator → zip to `%LOCALAPPDATA%\A-Conductor\instance-backups\` → remove → flags/alias cleanup; refuses while it cannot stop).
- Real-machine evidence: `Serena-Smoketest` created from the real conductor reference on 18014, discovered, then deleted with `smoketest-20260822-140647.zip` — instances root returned to exactly the original three.
- Note: instance names normalize to a lowercase slug (`SmokeTest` → `serena-smoketest` folder, `Serena-Smoketest` display), matching the existing conductor/phase6/wastewater convention.

## v0.2.2 shipped (PRs #54-#55, CI-green; GUI/core suites now run in separate CI processes)

- **App close = clean machine (PR #54)**: WM_DELETE_WINDOW stops every running connector (failure-tolerant), reaps stale wrappers, then exits; toggle ปิดโปรแกรมแล้วหยุดทุกตัวเชื่อม in Settings (default ON). Includes `docs/plans/cross-platform-plan.md` (macOS/Linux/Pi feasible; Umbrel needs headless web milestone; GATE-0 = non-Windows tunnel-client builds).
- **MONITOR panel (PR #55)**: selected connector shows STATE/PID/MEM/log path/error count/last-12 log lines, 5s auto-refresh (real entrypoint only); `instance_monitor.py` is cross-platform-ready (/proc path for Linux). Replaces the need to keep CMD windows open.
- CI lesson: Tk tests + subprocess-heavy tests in one process deterministically tripped a Windows faulthandler 0x80000003 breakpoint on runners — suites now run in separate steps.

## v0.2.1 shipped (PRs #50-#52, all CI-green; installed on this machine)

- **Usability (PR #50)**: horizontal scrollbars on WORKERS/CONNECTORS; hover any row -> dark floating tooltip with the FULL path; right-click -> Copy path (logged); window title carries the version (`A-Sunday Conductor v0.2.1`).
- **Thai/English switch (PR #51)**: `i18n.py` string table + English variants for all 50 teaching error codes; `language` preference (Settings switch) applied at startup; known gap: config blurbs + Thai guide stay Thai (backlog).
- **Guide (PR #52)**: §4.3 refreshed for the new toolbar; §4.3.1 documents that ONE API key can own MANY tunnels (each = one parallel chat) with steps; §4.3.2 documents one chat using several workers (with trade-offs); §4.5 language switch + version note.
- Full suite at close: 932 passed. Installed build reinstalled + smoke OK (projects=4 workers=3 preserved).

## v0.2.3: private Drive data layer (2026-08-22)

- Secrets now live in the A-Wiki-Data Drive layer: `L:\My Drive\A-Wiki-Data\secrets\a-conductor-tunnels.md` holds all five Tunnel IDs (mapping worker/port/plugin); the Drive layer's `LAYOUT.md` records the two new roles.
- Connector-deletion zip backups automatically target `L:\My Drive\A-Wiki-Data\backups\a-conductor-instances\` when it exists (`default_backup_dir()` in desktop_control, Drive-first with LOCALAPPDATA fallback); the existing smoketest zip was moved there.
- Repo AGENTS.md now points every agent at the Drive layer + its AGENTS/LAYOUT rules before touching important/secret files.

## v0.2.4: A-Doctor deep-audit fixes (2026-08-22)

- **P1 fixes**: Toggle Auto wrote the wrong column (clobbered TUNNEL, left AUTO stale); reaper used substring matching (could kill sibling instances' wrappers — now path-boundary + apostrophe-escaped); project paths with apostrophes broke PowerShell single-quoted lines (now escaped via `_ps_quote` in create/rename/rebind); MONITOR froze the UI thread every 5s (async + cached instances + 64KB tail reads).
- **P2 fixes**: create validates the whole reference before touching disk (no skeleton folders); delete uses the real stop result code; backup zips include empty dirs; rename rollback covers read/write IO; stop-failures at close surface via confirm; error tables extended + made symmetric (Thai/EN) with the duplicate TUNNEL_ID_INVALID removed; CI GUI list completed (test_instance_create, test_doctor_fixes).
- WO-P1-052 closed (code shipped long ago); WO-P1-023 marked superseded. Guide §3 diagram/§4.5 refreshed for the current toolbars + MONITOR + shutdown switch.

## v0.3.0: backlog loops shipped (2026-08-23, PRs #59-#63)

- **Loop A (deep i18n)**: all 64 config blurbs bilingual (PR #60) + full English user guide bundled with every install; Guide button follows the language; MODE_BLURBS finally wired as a checkbox grid.
- **Loop B-1 (cross-platform P1)**: `platform_support` (env-override roots, Win32 constant flags), POSIX launcher (`/bin/sh` + start_new_session), headless smoke fallback; **CI now runs on Windows + Ubuntu + macOS** — the matrix caught 3 real POSIX bugs (subprocess attr, hardcoded instance base, Tk-no-display) before any user ever hit them. Remaining: B-2 (.sh instance templates) + B-3 (mac/Linux packaging).
- **Loop C (signing)**: SignPath pipeline ready (`scripts/sign.py` no-op until `SIGNPATH_API_TOKEN`; sign workflow on release publish); **user action pending**: apply per `docs/signing/SIGNPATH-APPLY.md` (free for OSS; consider switching the license to MIT/Apache first).
- **Loop D**: ADR-0001 defers the MCP gateway with explicit reopen conditions; no DECISION_REQUIRED markers remain.
- v0.3.0 installed on this machine (smoke OK, both guides bundled); bug-hunt suite stable ×2 (24/24).

## v0.3.0 COMPLETE (2026-08-23, PRs #59-#65, GitHub Release published)

**Everything from the approved backlog-loop plan is shipped:**

- **Loop A (deep i18n)**: bilingual config blurbs + English user guide + MODE grid
- **Loop B (cross-platform)**: platform layer (B-1) + POSIX .sh templates (B-2) + 3-OS CI matrix (B-3)
- **Loop C (signing)**: SignPath pipeline ready; user applies per docs/signing/SIGNPATH-APPLY.md
- **Loop D**: ADR-0001 gateway deferred with reopen conditions
- **GitHub Release v0.3.0**: https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.3.0 (Setup + Portable + both guides + notices)
- **README rewritten** (capabilities, quick-start, architecture) + **INSTALL.md** (Thai step-by-step)
- Bug-hunt stable ×2; no DECISION_REQUIRED markers remain anywhere

**Remaining (next milestone, not blocking):**
- macOS/Linux desktop builds (B-3 packaging — the groundwork + templates are in place)
- RPi (P3) + Umbrel headless (P4) per docs/plans/cross-platform-plan.md
- SignPath application (user action, guide provided)

## v0.4.0: Setup Wizard (2026-08-23, PRs #69-#70)

One-stop installer: new users download Setup.exe → open → wizard auto-opens → installs everything (uv, Python 3.13, Serena, tunnel-client) → creates first connector → saves credentials. No manual prerequisites.

- **PR-A (engine)**: setup_wizard.py — check_system, Installer (uv/Python/Serena/tunnel-client with injectable download/subprocess), FirstInstanceCreator (generates complete instance from embedded templates, no reference needed)
- **PR-B (UI)**: 7-step wizard dialog with first-run auto-open; i18n TH/EN; real-time install log; OpenAI Platform link

## v0.4.1-0.4.3: wizard backends + donate (2026-08-24, PRs #71-#73)

- v0.4.1: Node.js auto-install + backend selection (Filesystem / Serena)
- v0.4.2: Google Stitch backend (4th option)
- v0.4.3: Donate dialog (GitHub Sponsors + PromptPay QR) + DPAPI fix
- Final audit: repo health 100%, 1031 tests, zero DECISION_REQUIRED

## v0.5.0 UI Redesign + Session Summary (2026-08-24, PRs #74-#76+)

### Shipped this session:
- **PanedWindow layout** — all panels drag-resizable, no more disappearing panels
- **GPU particle logo** — 120px interactive canvas in header, eyes track mouse
- **Responsive button grids** — buttons auto-wrap at wide widths, stack at narrow
- **English button labels** — canonical_button_label forces English globally
- **Tri-lingual i18n** — Thai / 中文 / English with per-language tooltips
- **MONITOR + ACTIVITY side-by-side** — horizontal PanedWindow
- **Copy log** — Ctrl+C, right-click menu, Copy All buttons
- **Assign with confirmation** — popup when replacing existing assignment
- **Setup Wizard** — 4 backends (Filesystem, Serena, Google Stitch, custom)
- **Donate dialog** — GitHub Sponsors + PromptPay QR
- **DEFECT_LESSONS.md** — 3 documented lessons (PowerShell spawn, dialog destroy, Tk instance)
- **PowerShell spawn fix** — native ctypes API, 0 process spawns
- **+Worker dialog fix** — read entry before destroy
- **Splash screen fix** — Toplevel instead of second Tk()
- **Community files** — CODE_OF_CONDUCT, CONTRIBUTING, templates, FUNDING
- **CHANGELOG.md** — full version history
- **MIT License** + GitHub Sponsors + Privacy + Security policies
- **Repo health 100%**

### Current state:
- Version: v0.5.0
- Tests: ~1092 collected
- CI: Windows + Ubuntu + macOS
- GitHub Releases: v0.5.0
- Install: %LOCALAPPDATA%\Programs\A-Sunday Conductor
### Pending (backlog, non-blocking):
- GPT/GLM collaboration protocol (docs/agent-collab/)
- Connector column UX tooltip improvement
- macOS/Linux desktop packaging (B-3)
- RPi + Umbrel (P3/P4)
- SignPath application (user action)

## Live connector fleet (2026-08-22 night — backend renamed to one pattern, all READY)

| Folder / $InstanceName | Port | Display alias (matches ChatGPT plugin) | Project |
|---|---|---|---|
| sunday-worker-1 / Sunday-Worker-1 | 18011 | SunDay-Worker 1-Conduct (18011) | A-Wiki-Conductor |
| sunday-worker-2 / Sunday-Worker-2 | 18012 | SunDay-Worker 2-Conduct (18012) | L:\My Drive\A-Wiki-Data\personal-business\pharmacy |
| sunday-worker-3 / Sunday-Worker-3 | 18013 | SunDay-Worker 3-Conduct (18013) | env-wastewater-webapp |
| sunday-worker-4 / Sunday-Worker-4 | 18014 | SunDay-Worker 4-Conduct (18014) | A-Wiki-Conductor |
| sunday-worker-5 / Sunday-Worker-5 | 18015 | SunDay-Worker 5-Conduct (18015) | A:\GitHub\sunday-estate-webapp |

- Backend rename executed via `instance_rename.rename_instance_backend` (PR #48): folders, identity lines, profile/log literals, template filenames, and every cmd wrapper renamed; window titles now `Sunday-works N - <Action>`.
- Migration lesson: an app-started instance keeps a detached `cmd.exe` wrapper whose CWD is the instance folder — folder renames require stopping the instance AND reaping that wrapper by exact PID (command-line match) first.
- Projects are NOT locked to names: any connector can switch projects via the เปลี่ยนโปรเจกต์ button (this rename was done precisely to stop implying otherwise).

## Full suite at close

957 passed (v0.2.4 A-Doctor fixes included).

## Next safe action (user picks)

(a) กด `+ Worker` / `+ ตัวเชื่อม` ในแอปจริงเพื่อเปิดแชทขนานเพิ่ม (Tunnel ID ยังต้องสร้างใน OpenAI Platform web); (b) ตั้งชื่อ plugin ใหม่ใน ChatGPT + reconnect (user's own task); (c) rebuild+reinstall เพื่อให้ Start Menu ได้ปุ่มใหม่; (d) next §13 milestone with new work order + reuse gate.

## Mandatory boundaries

- MCP gateway: deferred per `docs/adr/ADR-0001-mcp-gateway-deferred.md` (reopen conditions listed there).
- A-Wiki remains brain authority. No machine-wide env changes.
- Do not rename internal package/CLI/data folder without an explicit migration decision.
- Do not modify `C:\AI\serena-instances` scripts further without user authority (this session's retitling was explicitly authorized; `.bak` files allow rollback).

## Escalation rule

GLM 5.3 owns routine implementation, TDD, regression, docs, PR/CI, merge. Escalate to GPT-5.6 Sol UltraHigh only for genuinely hard cross-cutting defects/architecture ambiguity, after checkpointing state.

## WO-P1-063 real-monitor extension checkpoint

Real-monitor extension checkpoint: user requested real CPU/RAM/app-uptime monitoring in the command-center overview. This extends WO-P1-063; it does not create a second dashboard. The implementation must use native/file-based sampling, no periodic subprocesses, bounded CPU history, and `—` for unavailable metrics. Claimed files include `src/a_conductor/system_metrics.py` and `tests/test_system_metrics.py` in addition to the existing WO-P1-063 UI scope.

## WO-P1-063 implementation evidence — terminal command center + real monitor

Current branch `feat/terminal-command-center-redesign` contains the implemented terminal command-center visual slice plus a real system-monitor extension. `SYSTEM OVERVIEW` now uses measured CPU/RAM/app uptime, not mockup numbers. New collector is `src/a_conductor/system_metrics.py`; it uses native Windows APIs / Linux `/proc`, no periodic subprocess. UI refresh = 2.5s, CPU history = max 60 points, callback cancels on close. Real UI smoke: CPU 5%, RAM 9.2 / 15.9 GB, uptime 00:00:03. Combined focused suite: 37 passed, 1 environment skip. Release loop is not complete until PR/CI/merge/fresh-install visual verification.

## WO-P1-063 PR checkpoint

Draft PR #77 is open from `feat/terminal-command-center-redesign`; implementation commit `c42d174` is pushed. CI started with Windows test + Ubuntu/macOS cross-platform smoke pending. Next owner must review actual PR diff and checks first, then fix only evidence-backed failures, finish packaging/fresh-install visual E2E, update SSoT, convert from draft/merge only after acceptance.

- AHA-5 audit evidence: related suite 122 passed; CI-equivalent full suite 1687 passed, 1 environment skip, 0 failed; compileall/diff-check/secret-pattern scan PASS.


## WO-P1-114 implementation checkpoint — 2026-08-30

- New provider runtime seams implemented in `awiki_environment_resolver.py` and `provider_runtime_assembly.py`; no scheduler/lease/job-store/UI mutation.
- RED collection proved both modules absent before implementation; GREEN focused suite now `15 passed`.
- Related provider/harness/AHA-6 regression: `211 passed`; compileall PASS.
- Full local suite: `1714 passed, 5 skipped, 2 known GPU dependency failures` outside WO-P1-114.
- Adversarial `.drive-path` decode defect repaired and recorded as `DEFECT_LESSONS.md #26`.
- Automatic GLM is still fail-closed: desktop runtime has no current `A_WIKI_DRIVE_PATH` binding, and AHA-6 cross-batch provider admission remains unsupported without serialized/atomic capacity authority.
- Next gate: scope/secret/encoding audit → implementation commit/push → exact-SHA GLM-5.3 MAX read-only review packet → bounded repair if valid → PR/CI.

### WO-P1-114 trust-boundary repair update

- Pre-external GPT review found 2 real fail-closed defects: invalid explicit Drive override fallback and corrupt SQLite provider row decode escape.
- Both have RED tests and bounded repairs; focused suite is now `17 passed`, related regression `224 passed`.
- `DEFECT_LESSONS.md #27` added.
- The first ignored GLM packet at `c94abfc755a279f873cd0745eb8cdb131103ef84` was never dispatched and is superseded.
- Next: exact-state full suite → audit/commit/push repair → regenerate exact-SHA GLM review packet.

### WO-P1-114 exact repaired full-suite evidence

Exact repaired snapshot: focused `17 passed`; related `224 passed`; full local `1716 passed, 5 skipped, 2 known GPU dependency failures`. No provider/runtime assembly regression. Next gate remains audit → repair commit/push → fresh exact-SHA GLM review.

### WO-P1-114 external review handoff

- Repaired implementation head `d914915e5a1b2f179ce1315b13633cc4aa5f7b7e` is pushed and clean.
- Exact local gates: focused `17 passed`, related `224 passed`, full local `1716 passed / 5 skipped / 2 known GPU dependency failures`; compile/diff/scope/secret/encoding additions audit PASS.
- Independent review task ID is `wo114-glm-review-002`; task/result live only under ignored `runs/wo114-glm-review-002/`.
- GLM-5.3 MAX is assigned read-only trust-boundary review only; GPT retains acceptance/repair/merge authority.
- Automatic GLM dispatch is still fail-closed; use one-way human pointer relay only if the packet cannot be dispatched automatically.
- Next: commit/push this handoff checkpoint, generate and re-read exact-SHA task packet, then dispatch review.

### WO-P1-114 independent review accepted

GLM-5.3 MAX task `wo114-glm-review-002` returned `PASS` at exact HEAD `75c8e21da3d47ffb2fff6f8e37f6240b537f2522`. GPT independently validated task/provider/model/HEAD/task SHA and all four source/test hashes. P0/P1/P2 findings: 0. Four P3 hardening notes are deferred without source mutation. Next gate: final branch audit, Draft PR, exact-head CI, re-audit, merge, post-main proof.

## WO223 RE2-A R3 repair override — 2026-09-15

Actual Git/GitHub/Issue truth supersedes the older authoritative section above where it differs.

- Frozen candidate `1d755b6d5de5ebf5e357c5348f2e1b2544641b09` is REJECTED for acceptance after independent exact-SHA R3.
- Issue #214 checkpoint `5675288481` reopens the same bounded four-file RE2-A repair scope.
- Confirmed blockers: typed deep-JSON failure, truncation-safe admission recovery, and EXISTING-lease launch/cleanup ownership.
- `SAFE_TO_MUTATE_RE2A_SOURCE=YES` only in `A:\GitHub\_worktrees\A-Wiki-Conductor-wo223-re2a-replay` under the existing claim.
- `SAFE_TO_MERGE_PR319=NO`; PR #319 remains on old head until a replacement SHA passes fresh independent R3 and hosted CI.
- Fuzz cross-dispatch duplicate model effect is expected to close by refusing `EXISTING` lease as launch authority; verify with a RED/green concurrent test rather than assumption.
- RE2-B job-lifecycle recovery and other P3 hardening remain separate and must not widen this repair silently.

One next safe action: continuity commit -> GLM-5.3 MAX RED-first bounded writer -> GPT verification -> replacement freeze -> fresh exact-SHA R3 rereview.