# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-30 - WO-P1-115 / AHA-6A.1 ACTIVE / IMPLEMENTED / REVIEW_GATE

## Current objective

Execute WO-P1-115 / AHA-6A.1: add provider-global atomic admission and production runtime/bootstrap wiring by extending existing provider authorities. Automatic GLM/provider execution remains fail-closed until an exact provider route, fresh required quota evidence, secret resolution and admission gates are all proven. `WO-P1-096` remains the higher P0 release blocker pending explicit live-Worker maintenance authority.

## Repository state

- Active work order: `docs/work-orders/WO-P1-115-provider-admission-runtime-wiring.md` - ACTIVE / CLAIMED / IMPLEMENTED / REVIEW_GATE.
- Worktree: `A:\GitHub\A-Wiki-Conductor-provider-admission`; branch `feat/wo-p1-115-provider-admission-runtime`; base `origin/main@5a66e100b2f48c061b0677f0b2f39d1b9f23e80b`; clean at claim.
- Predecessor WO-P1-114 implementation + closeout are merged, post-main green and cleaned; no WO-P1-114 branches/worktrees remain.
- Reuse gate: A-Wiki remote main `71406f8a25079f364face422012e4bdeac5f483e`; secret authority is `docs/protocols/secrets-global-env.md`; A-Wiki local checkout remains dirty/read-only.
- GitHub open PRs at claim: 0; A-Wiki live claims: 0; North Star worktree clean and file-level non-overlapping.
- Implementation head `4e66cdeefbc31bd0513c8bd32ff322dc6230641b` is pushed; source/tests are frozen for independent review. Focused `59 passed`; related `253 passed`; full local `1750 passed / 4 skipped / 2 known GPU dependency failures`; compile/diff/scope/secret/encoding audit PASS.
- Installed-style DB-copy E2E preserved 12 existing tables, added 4 provider tables and left the live DB unchanged; cross-process admission E2E returned exactly `ADMITTED,CAPACITY_WAIT`.
- Automatic GLM remains fail-closed: current loopback route is not proven active, and official Z.ai `/api/monitor/usage/quota/limit` still lacks reset time required by the full five-hour tuple. One-way ignored `runs/` task/result bridge remains fallback.
- Independent review task is `wo115-glm-review-001`; GLM-5.3 MAX is read-only and must write only its ignored result artifact. GPT validates exact task/HEAD/hashes and owns any tracked repair/SSoT/PR/merge action.
- AHA-5 implementation PR `#149` — MERGED as `f648e04eba647d3a40b6aaa8353c90714f0a2ea1`.
- AHA-5 closeout PR `#150` — MERGED as current base `64b6ef839f16a270295fb2c24649d01e0f54d862`.
- Post-main CI `33286026232` — SUCCESS on Windows/Ubuntu/macOS; Windows Frozen Setup E2E PASS.
- AHA-5 implementation + closeout worktrees/branches cleaned after exact tree-equality proof.
- Previous completed work order: `docs/work-orders/WO-P1-113-aha6-parallel-ready-execution.md` — COMPLETE / RELEASED.
- Worktree: `A:\GitHub\A-Wiki-Conductor-aha6-parallel`.
- Branch: `feat/wo-p1-113-aha6-parallel-ready` @ `64b6ef839f16a270295fb2c24649d01e0f54d862`.
- Root checkout remains protected/dirty and is not the mutation surface.
- AHA-6 implementation checkpoint: `bad6567a7909f6cceb34d6debff20a23e5c42484` — pushed to the active feature branch.
- Focused AHA-6 13 passed; relevant scheduler/dispatch/chaos/lease/provider/harness/AHA-5 regression 193 passed; compile/diff/secret audit PASS.
- Independent GLM review authority used durable `runs/` task/result files with no human result copy-back; review and repair re-review are now complete.
- Full local suite: 1696 passed, 5 skipped, 2 known local GPU dependency failures outside AHA-6 scope; related AHA-6 suite remains 193 passed.
- Auto GLM is not assembled in the installed app: no provider tables in the real control DB and no concrete production environment-reference resolver; quota evidence is also unavailable. Do not dispatch automatically.
- One-direction bridges `aha6-glm-review-001` and `aha6-glm-rereview-002` both completed; automatic provider dispatch remains fail-closed until its separate secret/quota assembly gates are proven.
- GLM review `aha6-glm-review-001` at `ae3dae595b6acc173657e15120c48068fcc4af7a` returned `CHANGES_REQUIRED`; identity/task SHA/source SHA/test SHA were validated before accepting findings.
- Accepted P2 repair: malformed `LEASED` outcomes no longer raise batch-wide; missing lease / worker drift become typed recovery while siblings retain outcomes. Repair commit: `2a4d8fd786a9d3086a8cd2a298b8ee8cfcb6adc8`.
- Post-repair evidence: focused 16 passed; related regression 196 passed; full local 1698 passed, 5 skipped, only the same two known GPU/OpenGL/Tcl environment failures outside AHA-6 scope.
- Cross-batch provider capacity is not globally reserved by this thin seam. Production wiring is blocked until batch admission is serialized per provider or an existing atomic provider-capacity authority supplies/reserves the snapshot; do not create a duplicate semaphore/store.
- Exact-repair-HEAD re-review `aha6-glm-rereview-002` returned `PASS` with zero findings at `960bf95de9c135a44a1afb33d488f7b4973dd6c6`; task/source/test/prior-result hashes matched.
- Final local PR audit: related regression 196 passed; compileall/diff-check/scope/secret scans PASS.
- PR #151 exact reviewed head `5cc2425580c1724ae34f5f836a2211ee6af06b1d` passed CI `33293013006` on Windows/Ubuntu/macOS including Windows Frozen Setup E2E, then merged as `7825afa0ae946d0389b5c6b2955a63a8ae36f54b`.
- Post-main CI `33293299053` on merge SHA `7825afa0ae946d0389b5c6b2955a63a8ae36f54b` passed Windows/Ubuntu/macOS including Frozen Setup E2E.
- Docs-only closeout uses `A:\GitHub\A-Wiki-Conductor-aha6-closeout` / `docs/wo-p1-113-aha6-closeout` from exact merged main. After closeout merge/post-main proof, remove only the clean AHA-6 implementation+closeout worktrees/branches after ancestry/tree-equality/no-unique-diff proof.

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
