# GLM GE-11 + v0.7 Release Audit — RESULT

Revision: r2 (2026-08-29, second pass). r1 findings were re-verified after the GE-11 lane committed and opened PR #140; deltas are marked below. Instruction packet unchanged (`docs/agent-collab/GLM-GE11-RELEASE-AUDIT.md`, branch `audit/glm-ge11-release` @ `26b1c39`).

Auditor: GLM 5.3 MAX (independent, READ-ONLY; the only file written in the audit worktree is this result; no checkout/merge/commit/claim performed).
Audited base: `origin/main@1fea5cfffbe9bb8a9093e67dfa1065559e324ab2` (unchanged since r1; main CI runs `33237480511`, `33236050828` success). GE-11 lane head: `b74cf8e` (pushed; PR #140 OPEN, CI run `33239227923` success).
Method: `git show/grep/ls-tree` on origin refs + read-only inspection of worktrees + `gh` for PR/CI/release truth. No chat memory or agent claims treated as authority.

## Context facts established first

- GE-8 (`barriers.py` @ `76a7b55`), GE-9 (`lifecycle_bridge.py` @ `da50305`), GE-10 (13-case chaos matrix @ `1fea5cf`, PR #139) are merged on `origin/main`. GE-11 is the remaining GE lane: worktree `A:\GitHub\A-Wiki-Conductor-ge11-ui`, branch `feat/wo-ge-011-graph-operator-ui`, head `b74cf8e` "feat(graph): add factual operator monitor", PR #140 open with green CI.
- Latest GitHub release is still `v0.6.0` (2026-08-25); `CHANGELOG.md` says `## [0.7.0] — Unreleased`; source identifies `0.7.0`.

## A. GE-11 operator UI — findings

### A1. [r2: RESOLVED] Uncommitted active lane

r1 found the entire GE-11 lane (WO + adapter + tests) untracked with zero commits (P1 continuity defect). As of this pass: single commit `b74cf8e` contains exactly the WO-declared scope (WO-GE-011, `operator_view.py`, `desktop_control.py` +18, `desktop_ui.py` +246, both test files, parent WO-GE-001 checkpoint, DEFECT_LESSONS entry), worktree is clean, branch is pushed, and PR #140 is open with CI green. Continuity risk closed; no action remains beyond normal review/merge.

### A2. VERIFIED SOUND: implementation matches the WO boundary (now against committed code, not just the WO text)

- Read-only database access: `operator_view.py:70-75` `_connect_read_only` uses `sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)`.
- No mutation surface: committed `operator_view.py` contains zero `CREATE/INSERT/UPDATE/DELETE/executescript` occurrences.
- No new timer/process authority: `desktop_ui.py` additions only use the existing `_schedule_after`/`_cancel_after`/`_refresh_monitor_async` monitor mechanisms (no `Thread`, `Popen`, `subprocess`, `socket`, or extra `.after(` loop added).
- Factual identity: WO requires an explicit operator-supplied run id; blank id renders planning-only with `RUNTIME: NO RUN EVIDENCE`; "no implicit latest/current run discovery" is an acceptance item; GE-9 `project_graph_node_states` (`lifecycle_bridge.py:59`) is the authoritative projection; missing jobs remain TODO.
- WO-P1-068 overlap fence respected (connector ACTIVE/BOUND PROJECT, `/readyz`, recovery rendering untouched by GE-11 mode).

### A3. RISK (P2, conditional, unchanged): `GraphStore.__init__` mutates schema on construction

Evidence: `src/a_conductor/graph/store.py:84-96` — constructor runs `PRAGMA foreign_keys=ON` + `executescript(_SCHEMA)` on every instantiation; no read-only path exists in `GraphStore`. Reproducer: any future caller that opens a graph DB for display via `GraphStore(...)` creates/migrates tables, violating the GE-11 acceptance "reads use SQLite read-only mode and do not create/migrate tables". Current GE-11 code avoids it; risk remains for the next consumer. Safest bounded fix: `readonly` flag or `GraphStore.open_read_only()` + RED test (fresh path, ro open, assert no tables created).

### A4. Risk noted (P2, unchanged): `desktop_ui.py` shared hotspot

GE-11's allowed scope includes `desktop_ui.py`; no conflicting UI lane is active today. Keep UI lanes serialized per COLLAB hotspot rules when GE-11 lands.

## B. v0.7 release blockers — findings (unchanged from r1; main did not move)

### B1. CONFIRMED P0: operational soak/release gates remain open

Evidence: `docs/work-orders/WO-P1-096-connector-runtime-resilience.md` (tail, on main): "WO-P1-096 stays ACTIVE / P0 RELEASE BLOCKER until the operational soak and release E2E gates pass", with: shared live binary still `0.0.11`; installed app still `v0.6.0`; no sacrificial/idle tunnel proven available for the v0.0.13 deadline/TTL soak. `gh release list` confirms v0.6.0 Latest. These require a user-provided sacrificial connector and execution of the specified soak/E2E sequence — not new source work.

### B2. CONFIRMED DEFECT (P1): stale SSoT on main persists (~9 merges behind reality)

Evidence: on `origin/main@1fea5cf`, `CURRENT-WORK.md` is the 2026-08-28 edition ("PR #124 merged / AHA-4 ... ACTIVE"; "Draft PR #130 is open"; "Protected parallel work remains PR #125 ... PR #108 ...") and `handoff.md` is WO-P1-100 era, while #125/#130/#108/#132/#133/#134/#135/#139 plus GE-8/9/10 are merged. Reproducer: a fresh agent resuming per AGENTS.md is directed to a dead lane and told to avoid merged PRs' files as if live. Safest bounded fix: one docs-only integrator commit refreshing CURRENT-WORK/handoff (GE-11 PR #140 open+green, WO-P1-096 operational gate status, PR #131 still open/behind, GE-8/9/10 merged).

### B3. VERIFIED OK: CI and versioning hygiene

- main CI green (`33237480511`, `33236050828`); GE-11 branch CI green (`33239227923`, 8m17s).
- `CHANGELOG.md` correctly marks `0.7.0` Unreleased; no false release claims found.

### B4. Unsafe cleanup / hygiene (P2, unchanged)

- Dead local branch `fix/v070-installer-powershell-path-quoting` (ahead 1, no PR) with 1 dirty file in its worktree.
- Detached worktrees `pr108-integration`, `pr125-integration` (@ `08369ad`), `glm-release-audit` (`12a4c56`) lingering post-merge; `ultra-audit` idle.
- Remote `fix/wo-p1-107-native-timeout-cleanup` not deleted after #135 merged.
- No bounded startup-sweep WO yet for `%TEMP%\a-conductor-exec-*` orphans (residual of #135's `COMMAND_CLEANUP_FAILED` path).
- All cleanup requires per-item dirty/untracked reconciliation and owner approval per PROJECT-PLAN §22.

## Summary table

| # | Finding | Class | Severity | Status r2 |
|---|---|---|---|---|
| A1 | GE-11 lane was fully uncommitted | confirmed defect (continuity) | P1 | **RESOLVED** (`b74cf8e`, clean, pushed, PR #140, CI green) |
| A2 | GE-11 boundary sound (ro access, no mutation SQL, reused monitor scheduling, run-id truth, WO-068 fence) | verified sound | — | re-verified on committed code |
| A3 | `GraphStore` constructor always creates schema; no ro path | risk (conditional) | P2 | open |
| B1 | v0.7.0 blocked: soak + upgrade + install E2E open; binary 0.0.11; app v0.6.0 | confirmed (gate) | P0 | open (needs user-provided sacrificial connector) |
| B2 | CURRENT-WORK/handoff stale ~9 merges | confirmed defect | P1 | open |
| B4 | Dead/detached worktrees+branches; no temp sweeper | hygiene | P2 | open |

## Safest bounded next actions (in order)

1. Review + merge PR #140 (GE-11) — CI already green; verify the remote diff matches the WO scope before merge per repo policy.
2. docs-only SSoT refresh by the integrator (B2) — prerequisite-quality fix, one commit.
3. Release side: user designates the sacrificial connector → authorized v0.0.13 upgrade + TTL soak with zero manual Starts → exact-main artifact install/smoke/uninstall acceptance → publish v0.7.0 → close WO-P1-075's open checkboxes (`WO-P1-075:77-78`).
4. Optional bounded WOs: `GraphStore.open_read_only()` + RED test (A3); `%TEMP%\a-conductor-exec-*` startup sweep (B4).
