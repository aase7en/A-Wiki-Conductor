# HANDOFF — A-Sunday Conductor

Last updated: 2026-09-01 — WO121/WO118A merged; WO120 final rereview pending

## Current objective

Close WO120/PR162 with exact-head Ultra evidence and post-main proof, then execute WO118B. Keep P0 WO096 separate.

## Repository / release identity

- authoritative remote main: `0ff914efa2887a0f9c6d330859fa4e49ed921d89`; protected root checkout is stale/dirty and MUST NOT be mutated;
- PR #164 / WO121: MERGED as `1b0468fa...`; GLM rereview004 PASS; post-main CI `33404736157` SUCCESS;
- PR #165 / WO118A: MERGED as `0ff914ef...`; Ultra rereview004 PASS at exact `2bfcdab...`, P0/P1/P2=0; exact-head CI `33405254844` SUCCESS; post-main CI `33417911998` SUCCESS across Windows/Ubuntu/macOS including Windows Frozen Setup E2E; WO118B remains pending;
- PR #162 / WO120: DRAFT final candidate `899d002745b7ae56704c8a6614e7b9a957ab0ba6`; final union `359 passed`; packet `runs/wo120-ultra-rereview-002/task.md` SHA `63751963056bd463b9d456de25e4026afbb148ef6537109f165fcc5a2e22062c`; exact-head CI `33418133578` SUCCESS on Windows/Ubuntu/macOS; Ultra review pending.

## Ownership / claims

- No live mutable source claims remain; pushed exact heads are immutable until an evidence-backed repair claim is required.
- GPT integrator owns SSoT, review adjudication, merge/release and WO118B architecture.
- WO118B may start only after WO120 releases worker/elastic seams.

## Verified evidence

- WO121: exact-head GLM PASS; parallel 57, related 162 reviewer tests; post-main CI green.
- WO118A: Ultra004 PASS; review003 F1/F2 independently closed; reviewer-fresh focused `70 passed` and related `213 passed`; exact-head CI `33405254844` green; merge commit `0ff914ef...`; post-main CI `33417911998` green including Windows packaging/install E2E.
- WO120: latest crash-window RED proved stale unbound ACTIVE/RECOVERY could release capacity from owner+age; repair requires runtime-absence evidence while explicit known-pre-provision `release_unstarted()` remains valid. Focused+related 209; refreshed union 263; final post-WO118A union 359; compile/diff gates PASS.

## Next safe actions

1. Ingest Ultra WO120 rereview002; revalidate the already-green exact-head CI `33418133578`; merge #162 only if P0/P1/P2=0 and identity/hash match, then require post-main CI.
2. Execute WO118B after #162 merges: generation/policy denial must precede admission, lease, elastic expansion, credential access and launch.
3. Keep WO096 blocked pending explicit maintenance authority.

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

## WO-P1-116 implementation checkpoint ? 2026-08-31

- Active worktree/branch: `A:\GitHub\A-Wiki-Conductor-elastic-capacity` / `feat/wo-p1-116-elastic-worker-capacity`; tracked base remains `origin/main@23243651d51780b76dce15cdb24eaba90fce9a99` and PR #157 is still draft until exact-SHA review/CI gates complete.
- Recovery reconciled stale partial scratch to remote `d52a054f393c2e7864a2cec5e186c76a66e17c20` non-force; preserved abandoned scratch outside repo at `A:\GitHub\_recovery\WO-P1-116-20260831-092824`.
- Implemented production candidate/task assembly, existing-lease-store provisioning reservations, cross-process bounded capacity, owner-scoped provisioned-worker re-observation, production schedule?expand?reschedule?broker?runner composition, and default-disabled remote connector authorization.
- Defects #32-#34 capture eligibility-before-expansion, reservation visibility/owner handoff, and durable recovery-state requirements.
- Deterministic local evidence: focused/related `163 passed`; compileall/diff-check pass; spawned-process `max_extra=1` race has one ACQUIRED/one LIMIT_WAIT; realistic fixed-pool E2E starts with one reserved existing worker and executes on exactly one added worker.
- CI-topology local evidence: GUI 277 passed, local-instance 23 passed, supervised 11 passed, isolated core passed through 30 files; run then hit shared Hermes-vEnv GPU dependency gaps outside WO scope. Exact-head GitHub CI must remain final full-suite authority.
- Worker routing snapshot: Worker5 clean/no READY mutable Sunday-Estate lane and is fallback candidate only; Worker1 protected-root dirty; Worker2 active pharmacy cycle; Worker3 dirty; Worker4 reserved for WO-P1-096 P0. No worker/project rebind occurred.
- Next safe action: final audit ? commit/push exact source/SSoT ? generate ignored exact-SHA GLM read-only review packet. Automatic GLM route is still fail-closed; human may relay only `???? runs/<task-id>/task.md ?????????`, and GPT reads/validates `result.json` itself.
