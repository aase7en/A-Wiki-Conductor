# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-30 — WO-P1-113 / AHA-6 ACTIVE

## Current objective

Execute AHA-6 fixed-pool parallel READY tasks with exact scheduler selection, AHA-4B lease/scope collision safety, provider capacity/quota preflight and no blind replay. Automatic CoinTH/GLM execution must resolve secrets externally from `A-Wiki-Data/.env`; credentials never enter tracked state.

## Repository state

- AHA-5 implementation PR `#149` — MERGED as `f648e04eba647d3a40b6aaa8353c90714f0a2ea1`.
- AHA-5 closeout PR `#150` — MERGED as current base `64b6ef839f16a270295fb2c24649d01e0f54d862`.
- Post-main CI `33286026232` — SUCCESS on Windows/Ubuntu/macOS; Windows Frozen Setup E2E PASS.
- AHA-5 implementation + closeout worktrees/branches cleaned after exact tree-equality proof.
- Active work order: `docs/work-orders/WO-P1-113-aha6-parallel-ready-execution.md` — ACTIVE / CLAIMED.
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
- Final local PR audit: related regression 196 passed; compileall/diff-check/scope/secret scans PASS. Next safe action is Draft PR -> exact-head CI -> re-audit/merge.

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
