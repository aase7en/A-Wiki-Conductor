# HANDOFF — A-Sunday Conductor

Last updated: 2026-09-02 - WO127 + WO128 core released; WO134 T2–T4 claimed

## Current objective

Execute WO134 provider evidence detail/UI with GLM-5.3 MAX ZCode Goal + `$a-loop`, while GPT-5.6 Sol owns integration/review/commit/PR/merge. Preserve `SELECTION_REASON=UNKNOWN`, `FALLBACK_REASON=NOT_EVALUATED`, no new router/policy/graph authority, and keep WO096 blocked without explicit live maintenance authority.

## Repository / release identity

- authoritative remote main: `b6d50921035ae6ec6d32b6c05b3f723530b8c68d`; protected root checkout remains stale/dirty and MUST NOT be mutated.
- WO127 PR #182 merged exact reviewed head `e91647a7ccaefe522b11ba867719b3186ed5b96d`; post-main CI `33585602021` SUCCESS.
- WO128 core PR #184 merged exact reviewed head `a9f4fe6a92367650e7c22caaa9df9e8c148cf3ad`; GLM review 002 PASS P0/P1/P2=0; post-main CI `33591789871` SUCCESS.
- source/development version remains `0.7.0`; GitHub Latest remains `v0.6.0`; stable publication remains blocked by WO096.

## Ownership / claims

- GPT-5.6 Sol owns dependency order, SSoT, acceptance, commit/PR/merge and release adjudication.
- WO127 and WO128 T0+T1 source lanes are RELEASED; their old clean worktrees confer no active mutable ownership.
- WO134 is the only mutable AHA-7 provider UI/control lane: GLM-5.3 MAX / ZCode Goal + `$a-loop` owns only its declared source/test/work-order scope in `A:\GitHub\A-Wiki-Conductor-wo134-provider-evidence-detail`.
- Shared SSoT remains GPT-owned during GLM implementation. GLM may not mutate provider store authority, graph production, job/execution/scheduler/parallel/elastic/provider policy/readiness/runtime assembly, secrets, live DB, Workers/tunnels, WO096, or release state.
- WO096 grants no live Worker/tunnel mutation authority.

## Verified evidence

- WO124 focused operator view = 25 passed; provider matrix = 84 passed; GLM independently re-ran both plus 12/12 adversarial reproductions.
- WO124 post-main attempt 1 hit the known unrelated Windows owned-process transient; attempt 2 passed the same main SHA through full Windows packaging/Frozen E2E without AHA-7 product changes.
- WO129 local focused = 28 passed; related = 117 passed before commit and 90 passed recheck; real Windows lifecycle = 10/10; GLM repeated the real test 3/3 and scripted adversarial cases 9/9.
- WO129 post-main CI is fully green, closing the repeated hosted-Windows post-stop observation race with a bounded/fail-closed repair.
- WO125 RED baseline reproduced 8 intended failures; final exact-head local focused 92 passed, full repo 1973 passed / 4 skipped / 2 known optional-GPU failures, GLM independently ran 92 focused + 44 related + 12/12 adversarial reproductions, and hosted exact-head/post-main CI are green.
- WO126 Python 3.13 focused panel = 10/10 PASS; ordered UI/control/i18n/singleton/button matrix = 118/118 PASS after process-global language cleanup.
- WO126 exact feature HEAD `eee3e0e202b27c685f63c222ff10646ae667987e` passed GLM independent review with all 11 pinned file hashes verified and P0/P1/P2=0; exact-head CI `33540512066` passed Windows/Ubuntu/macOS; PR #179 merged as `010ab4bdefbe54725388a5cea936117b8eb93b6b`; post-main CI `33544097620` passed the same 3-OS matrix including Windows packaging and Frozen Setup install/uninstall E2E.
- WO131 local execution matrix = 44/44 PASS; tied-timestamp + formerly flaky stress = 10 iterations x 2 tests all PASS; compileall/diff-check/UTF-8 PASS.
- WO131 exact-head CI `33543935682` and post-main CI `33545560617` are SUCCESS across Windows/Ubuntu/macOS including Windows packaging/Frozen Setup E2E. PR #180 merged externally as `af7a933fe27d2a3e3f29360abf9214df1e5478c5`; no GLM review result existed before merge, so the process deviation remains explicit.
- WO127/WO128 shaping result says both `READY_AFTER_WO126`; WO128 must render `SELECTION_REASON: UNKNOWN` and `FALLBACK_REASON: NOT_EVALUATED` rather than inventing router/fallback authority.

## Next safe actions

1. Verify WO134 task packet SHA + exact claim HEAD + worktree clean state, then dispatch GLM-5.3 MAX through ZCode Goal + `$a-loop`.
2. GLM executes RED-first implementation and writes only the declared result artifact; GPT independently inspects the working tree/diff/tests before any commit.
3. GPT performs deep bug hunt + real Tk/SQLite E2E, freezes exact SHA, dispatches independent exact-head review, then handles PR/CI/merge/post-main gates.
4. Fold WO128 chronology/corruption/review-freeze lessons into Defect Memory during the bounded closeout after product acceptance.
5. Do not publish v0.7.0 until WO096 hosted remote MCP-after-TTL evidence and final release E2E are complete.

## Accepted predecessor

AHA-4B PR #147 merged as `7f9a16f6dfafe17f3795167da22d4886945611e0`.
Exact-head CI `33260601487` and post-main CI `33261050931` passed Windows/Ubuntu/macOS;
Windows passed Frozen Setup install/uninstall E2E.

## AHA-5 checkpoint

- Proposal boundary GREEN: `agent_change_packets.py` decodes Claude/GLM result envelopes
  and applies only complete-file proposals that pass exact identity, active lease,
  mutable/forbidden scope, exact HEAD and overwrite content-hash preconditions.
- Relevant regression: 176 passed; compileall/diff-check PASS.
- GLM remains read-only by design; Conductor owns materialization. This supersedes the
  earlier idea of granting GLM direct repository mutation rights.
- Raw direct-GLM maintenance probe timed out and exposed a Windows descendant/pipe-hold
  hazard. Do not use raw subprocess for the live slice; use `SupervisedExecutionService`.
- Next safe action: checkpoint commit, then run a supervised direct-Z.ai GLM proposal
  from exact clean HEAD and review/apply it through the new boundary.

## 2026-08-30 AHA-5 file bridge checkpoint

- proposal/result decoding, exact identity, one-file-per-task scope and content-hash preconditions are implemented;
- human one-prompt bridge reads/writes durable `runs/` task/result files; integrator reads results directly;
- deterministic review → repair packet → repaired result E2E is GREEN without human result copy-back;
- Claude provider execution is isolated from user-level settings with `--setting-sources project,local`;
- direct GLM-5.3 MAX reached Z.ai but provider returned HTTP 429 `[1113]` insufficient resource package;
- the user also has a working external Claude-CLI GLM proxy profile, but its credential is intentionally not tracked or copied into Conductor artifacts;
- automatic proxy dispatch remains fail-closed until that credential/profile is exposed through an approved external secret resolver; the durable one-prompt file bridge remains usable without result copy-back;
- these are external provider/configuration conditions, not permission to weaken deterministic gates;
- next safe action: defect-memory + broad regression/chaos + diff/secret audit, then PR/CI/re-audit/merge.

- AHA-5 audit evidence: related suite 122 passed; CI-equivalent full suite 1687 passed, 1 environment skip, 0 failed; compileall/diff-check/secret-pattern scan PASS.

## AHA-5 final acceptance

- PR #149 merged after exact-head CI passed.
- Post-main CI `33284585961` passed all jobs, including Windows packaging and Frozen Setup E2E.
- Local CI-equivalent suite: 1687 passed, 1 environment skip, 0 failed.
- Related AHA-5 regression: 122 passed.
- Automatic GLM proxy use remains fail-closed until an approved external runtime profile is configured; quota must be checked before dispatch.

## AHA-6 claim checkpoint — 2026-08-30

- GitHub open PRs: 0 at claim time; A-Wiki local claim store: 0 live claims.
- Reuse gate: scheduler, atomic lease/recovery, durable graph dispatch, AHA-5 packet/result boundary and provider quota model already exist.
- Allowed implementation is restricted to the new parallel coordination seam + focused tests; existing scheduler/lease/job-store modules are forbidden unless scope is explicitly reopened.
- Provider quota fields already normalize to `QuotaSnapshot`; do not create a second quota model.
- CoinTH live dispatch remains fail-closed until the runtime resolver can source credentials through `A-Wiki-Data/.env` and produce the required five-hour quota observation without exposing values.

Next safe action: commit this claim/SSoT checkpoint, then add RED tests for WO-P1-113.


## WO-P1-114 AHA-6A checkpoint — provider runtime assembly

- Worktree `A:\GitHub\A-Wiki-Conductor-auto-provider-dispatch`; branch `feat/wo-p1-114-auto-provider-dispatch`; claim commit `7229d6ffa24932b7656825c63031b041f446079f`.
- Implemented native A-Wiki Drive/env reference resolution plus SQLite-backed Claude provider-state assembly; provider secret values are resolved only at the supervised execution boundary and are not stored in tracked state.
- Focused `15 passed`; related `211 passed`; full local `1714 passed, 5 skipped, 2 known GPU dependency failures`.
- Defect #26 records malformed `.drive-path` decode fail-closed behavior.
- Remaining production blockers are explicit: no desktop `A_WIKI_DRIVE_PATH`/equivalent runtime binding is assembled yet, and provider-global cross-batch admission still needs serialized admission or an existing atomic capacity authority.
- Next authority handoff is an exact-SHA GLM-5.3 MAX read-only review through ignored `runs/`; human relay is one pointer only if automatic provider execution remains unavailable.

### WO-P1-114 pre-external-review repair

GPT exact-state review found two additional fail-closed defects and repaired them with RED-first tests: explicit Drive override no longer falls through when invalid, and corrupt persisted provider data now resolves unavailable instead of leaking decode exceptions. Focused `17 passed`; related `224 passed`; defect memory #27 added. The earlier ignored GLM packet for `c94abfc...` was not dispatched and must not be reused.

Exact repaired full-suite evidence: `1716 passed, 5 skipped, 2 known GPU dependency failures`; focused `17 passed`, related `224 passed`. No WO-P1-114 regression. Generate a new external-review packet only after the repair commit is pushed.

### WO-P1-114 external review packet prep

Repair head `d914915e5a1b2f179ce1315b13633cc4aa5f7b7e` is pushed/clean. Final local evidence before external review: focused `17 passed`, related `224 passed`, full `1716 passed / 5 skipped / 2 known GPU dependency failures`, compile/diff/scope/secret/encoding additions audit PASS.

Prepared task identity: `wo114-glm-review-002`; ignored task/result paths are `runs/wo114-glm-review-002/task.md` and `runs/wo114-glm-review-002/result.json`. The task packet must be generated only after the tracked handoff checkpoint is committed, then re-read/hash-verified against the resulting exact HEAD. GLM is read-only; human relays only the pointer if automatic dispatch remains blocked.

### WO-P1-114 independent review accepted

`wo114-glm-review-002` is complete. GLM-5.3 MAX returned PASS on exact `75c8e21da3d47ffb2fff6f8e37f6240b537f2522`; GPT validated result identity, task SHA `17696ee758555478d41de76d2a6be23ca380549ae85eb7ccc9269e37aedab4ca`, and all pinned source/test hashes. No P0/P1/P2 findings. Four P3 hardening observations are accepted as non-blocking/deferred; no source/test change follows this review. Next safe action is final audit -> Draft PR -> exact-head CI -> re-audit -> merge/post-main proof.

### WO-P1-114 final release checkpoint

PR #153 exact head `00d0828816e11110f30299c76d6b5a43e7d5b095` passed CI `33299166993`, merged as `8828f07654746a52110bc89cc359e9e558b2f9e5`, and post-main CI `33299559419` passed Windows/Ubuntu/macOS including Frozen Setup E2E. WO-P1-114 is COMPLETE / RELEASED.

No successor AHA lane is claimed. The next accelerator slice requires a new work order for AHA-6A.1: runtime Drive binding, fresh complete quota observation, and serialized/atomic provider admission. Until that exists, automatic live GLM/provider dispatch remains fail-closed and the one-way task/result file bridge remains the accepted fallback. WO-P1-096 remains the separate higher P0 release blocker pending authorized live connector soak.

## WO-P1-115 final release checkpoint

- PR #155 exact head `7959ff9d8a300b2920a2ef1014c63db64b19518c` passed CI `33312763072` on Windows/Ubuntu/macOS including Windows Frozen Setup E2E.
- PR #155 merged as `a758f9e882db03e988d67a3f04f69862dd9195c2`; post-main CI `33313201851` passed all three OS jobs including Frozen Setup E2E.
- GLM review and exact-repair re-review are accepted historical evidence; both result packets are ignored runtime artifacts and must not be reused for later HEADs.
- Automatic live GLM remains fail-closed until an active provider route and complete reset-bearing five-hour quota tuple are proven. Provider admission/bootstrap capability is merged, not equivalent to provider readiness.
- Closeout branch/worktree: `docs/wo-p1-115-provider-admission-closeout` / `A:\GitHub\A-Wiki-Conductor-provider-admission-closeout` from exact merged main.
- After closeout merge/post-main proof, remove only WO-P1-115 implementation/closeout worktrees and branches after clean/ancestry/no-unique-commit/tree-diff proof. Preserve root/North-Star/other worktrees.
- No successor accelerator claim exists yet. Re-enter actual roadmap/claims after cleanup; WO-P1-096 remains P0 when maintenance authority becomes available.

## WO-P1-116 implementation checkpoint - 2026-08-31

- Active worktree/branch: `A:\GitHub\A-Wiki-Conductor-elastic-capacity` / `feat/wo-p1-116-elastic-worker-capacity`; tracked base remains `origin/main@23243651d51780b76dce15cdb24eaba90fce9a99` and PR #157 is still draft until exact-SHA review/CI gates complete.
- Recovery reconciled stale partial scratch to remote `d52a054f393c2e7864a2cec5e186c76a66e17c20` non-force; preserved abandoned scratch outside repo at `A:\GitHub\_recovery\WO-P1-116-20260831-092824`.
- Implemented production candidate/task assembly, existing-lease-store provisioning reservations, cross-process bounded capacity, owner-scoped provisioned-worker re-observation, production schedule?expand?reschedule?broker?runner composition, and default-disabled remote connector authorization.
- Defects #32-#34 capture eligibility-before-expansion, reservation visibility/owner handoff, and durable recovery-state requirements.
- Deterministic local evidence: focused/related `163 passed`; compileall/diff-check pass; spawned-process `max_extra=1` race has one ACQUIRED/one LIMIT_WAIT; realistic fixed-pool E2E starts with one reserved existing worker and executes on exactly one added worker.
- CI-topology local evidence: GUI 277 passed, local-instance 23 passed, supervised 11 passed, isolated core passed through 30 files; run then hit shared Hermes-vEnv GPU dependency gaps outside WO scope. Exact-head GitHub CI must remain final full-suite authority.
- Worker routing snapshot: Worker5 clean/no READY mutable Sunday-Estate lane and is fallback candidate only; Worker1 protected-root dirty; Worker2 active pharmacy cycle; Worker3 dirty; Worker4 reserved for WO-P1-096 P0. No worker/project rebind occurred.
- Next safe action: final audit ? commit/push exact source/SSoT ? generate ignored exact-SHA GLM read-only review packet. Automatic GLM route is still fail-closed; human may relay only `???? runs/<task-id>/task.md ?????????`, and GPT reads/validates `result.json` itself.
