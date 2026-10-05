# Session rollover checkpoint — A-Sunday Conductor

Status: CHECKPOINT / CHAT ROLLOVER READY
Date: 2026-09-24 18:36 ICT
Topology: CONTROL_PLANE_ONLY checkpoint over a live multi-lane frontier
Authority repo: `/Users/aase7en/GitHub/A-Wiki-Conductor`
Execution repo: `/Users/aase7en/GitHub/SunDayRemoteMCP`
Checkpoint base: A-Wiki GitHub `main@b644fa02f480ae18fbae3d2b7a6d06f7fc79f726`
Context verdict: RED / ROTATE NOW; no trusted exact remaining-context percentage is exposed.

## Authority rule

This file is a recovery index, not higher authority than actual state.

`actual runtime/Git/GitHub/durable evidence -> claims/work orders/evidence -> CURRENT-WORK/active WO/handoff/COLLAB -> checkpoint -> chat memory`

Start with:
`A-SUNDAY-CONDUCTOR-PROJECT-INSTRUCTIONS -> 00-START-HERE -> 10-SSOT-AND-CONTINUITY -> 20-REPO-SAFETY-AND-OWNERSHIP -> repo 00-AGENT-ENTRY -> PROJECT-GRAPH -> AGENTS -> RECOVER actual state`.

CHAT/TURN LOSS != EXECUTION FAILURE. NEW SESSION != NEW TASK. Never redispatch work merely because the chat changed.

## Repository truth

### A-Wiki
- GitHub `main=b644fa02f480ae18fbae3d2b7a6d06f7fc79f726` (PR #532 merge).
- Protected root is STALE_LOCAL_CHECKOUT: local `main@d3f319a64fd4cef03a7fe5e23a676ba6db8d4b2b`.
- Root has unknown untracked `.kilo/agents/data.md` and `HUMAN_DECISION_REQUIRED`.
- Root `SAFE_TO_MUTATE=NO`; never reset/clean/stash/switch/delete those paths. Use isolated worktrees.
### SunDayRemoteMCP
- local/remote `main=e6460ebb3823f1b0c179f78b9f1944b05963531f`; canonical root clean.
- WO535 stdin-EOF substrate repair is merged; post-main sequential build/focused suite passed.
- direct runtime EOF probe `exec-muffsdg2-1yr6kd1v` COMPLETED.
- Issue #535 CLOSED. PR #536 remains an open checkpoint projection; recover actual need before action.

## Accepted/merged this session
- #531 / PR #534: candidate `af10709f7d954d03778fe99ae45a4b5ebf6cea16`, merge `e70e34340018f4bdd82379bfbc3696bd8d23ddca`, hosted checks SUCCESS, issue CLOSED.
- #530 / PR #533: candidate `4c1a8818c2b6d595b81b759cfd9154239ce5cd10`, merge `26fa04d9da26bc8cc18b556c6e2e9a94da414031`, hosted checks SUCCESS, issue CLOSED.
- #529 / PR #532: final head `e6b72b5f5fb680df981efd8c290714190a24de18`, merge/current main `b644fa02f480ae18fbae3d2b7a6d06f7fc79f726`, hosted checks SUCCESS. Issue #529 remains OPEN; recover/fold closeout rather than assuming COMPLETE.

## Outstanding durable execution — recover first

### exec-muffj4kd-52dlz9rj
- label: `WO537 post-compose slow UI capacity fencing tests`
- state at checkpoint: RUNNING; replay/duplicate dispatch FORBIDDEN while RUNNING.
- mode: read
- worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo537-elastic-mission-control`
- child PID 91432; shim PID 91410
- last output: test progress dots (`...........`)
- next action: `sunday_status`; when terminal HARVEST then COLLECT. Never broad-kill Python/shim.

## Active frontier — Issue #537

Issue #537 `Elastic borrowed lanes + Mission Control wait observability` is OPEN.
### PR #539 — elastic Mission Control
- PR OPEN; remote head `7845d838d535cb92815f0e5b0773d2f0c265b884`; hosted checks SUCCESS; CLEAN/MERGEABLE.
- Independent Codex R3 `exec-muffol1l-su8y1g0z` on exact `7845d83...`: **CHANGES_REQUIRED**, P0=0/P1=3/P2=2/P3=0.
- Blockers: borrowed lanes can survive BLOCKED wait; activity can override terminal/recovery/lost execution truth; real desktop-control path does not feed new activity observation; wait without execution_id can bind stale identity/leak rejected details; capacity summary can undercount WAITING_GLM with live mutating child.
- `READY_FOR_EXPECTED_HEAD_MERGE=NO`.
- local worktree is clean at `ce1487ba6fb5e17b0eddabafc288f815a17997a8`, a local compose/merge of origin/main into the branch; it is ahead of remote PR head and is not acceptance evidence.
- Harvest the running slow test first. Then repair the five R3 blockers under existing WO/ownership, freeze new SHA, targeted verify, fresh independent R3, Sol acceptance. Do NOT merge from green CI alone.

### PR #540 — A-Faster wait-aware auto-backfill
- PR OPEN; current head `01011c1eb9a2623a187d609a37977f13ae76569b`; matching worktree clean.
- Ubuntu/macOS checks SUCCESS; Windows/full `test` was IN_PROGRESS at checkpoint.
- Independent GLM-5.3 MAX R3 `exec-muffq1cy-0v0f0kdg` PASSED on older exact head `3a22570925b0f91e6172db0dfa1caa59f429dee7`, P0/P1/P2/P3=0/0/0/4.
- Current `01011c1...` is a later test-hardening commit and is NOT covered by that PASS.
- next: exact-head CI -> independent delta/exact-head review -> Sol acceptance -> expected-head merge only if green.

## Other open continuity
- #337 / PR #538: OPEN at `2e953ca9486d4944cd6a331214530609efde02a9`; CLEAN/MERGEABLE; hosted test/Ubuntu/macOS SUCCESS. Recover exact independent-review/Sol-acceptance state before merge. Historical PR #338 stays historical.
- #541 OPEN: `SundayMCP Chat output hygiene — lossless compact receipts + evidence retrieval`. No mutation authority granted by this checkpoint; recover claim/owner first.
- #512/#498 remains outside current accepted frontier; earlier review had blockers. Fresh-check before touching.
## A-Faster + A-NightShift continuation contract
- Use accepted versions from actual current main after recovery; open PR candidates do not become canonical by existing.
- A-Faster is router/binder/refill only; no shadow scheduler/task DB/claim/review/completion authority.
- Default WIP stays max 3 mutable + 1 independent read-only review unless an accepted merged WO changes it; one mutable hotspot = one owner.
- Before every material GLM dispatch refresh CoinTH proxy quota AND prove fresh upstream readiness; proxy quota alone is insufficient.
- GLM-5.3 MAX = bounded R2/R3 author/repair/review; Flash = bounded read-only shaping/recon.
- Harvest terminal children before refill/re-dispatch. External waits are blocking/event-driven; no model-turn busy polling.
- A-NightShift parent owns /goal lifecycle; A-Faster may route/refill children under accepted policy.
- Do not invent a new NightShift objective merely for rollover. Materialize a fresh ephemeral contract only for an actual unattended goal after stale/terminal pointer recovery.

## Exact new-session recovery order
1. Read protocol/entry files and run `sunday_recover`.
2. Reconcile `exec-muffj4kd-52dlz9rj` first. RUNNING => no duplicate; terminal => HARVEST + COLLECT.
3. Fresh-check GitHub main, PRs #539/#540/#538, Issues #537/#529/#337/#541.
4. Do not mutate protected A-Wiki root while unknown untracked files remain.
5. Continue #537: repair PR #539 R3 blockers; finish PR #540 exact-head CI + fresh review.
6. Reconcile #337/PR #538 when WIP allows.
7. Fold #529 closeout if actual post-main evidence satisfies its WO.
8. Use A-Faster to refill only SAFE_READY work; use A-NightShift only under accepted lifecycle/contract rules.
9. Checkpoint again before another context/session/model rotation.

## Prohibitions
- no reset/clean/stash of unknown work;
- no touch/delete of root `.kilo/agents/data.md` or `HUMAN_DECISION_REQUIRED` without proven ownership;
- no broad-kill processes;
- no redispatch of RUNNING durable execution;
- no merge using a review from a different exact head without delta/exact-head adjudication;
- green CI is not automatic acceptance;
- no secret/global Kilo-config exposure;
- no shadow task/claim/quota/provider/review/completion authority.

The next chat must RECOVER and continue automatically. The user must not be asked to reconstruct this session. Actual state wins if it has advanced.
