# WO-P1-178 — ZRA-COMP-1 composition E2E

Status: READY_FOR_INDEPENDENT_REVIEW / R2 TEST-ONLY
Date: 2026-09-10
Owner: GPT-5.6 Sol integrator
Repository: aase7en/A-Wiki-Conductor
Branch: test/wo-p1-178-zra-comp-1
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo178-zra-comp-1
Base: 1244b14fd8bc09eba191433a0297c1fc5f3f14ac
Parent authority: Issue #213 ZRA-1 + Issue #233; GLM-WAVE3 Stage 2 `runs/GLM-WAVE3-READONLY/STAGE-2-ZRA-COMP-1.md`.

## Goal

Add one deterministic, test-only end-to-end proof that the already-accepted Zero-Relay primitives compose correctly after WO176:

`verified TaskPacket -> canonical provider snapshot/generation -> real provider admission -> real WorkerLease -> assemble_zcode_execution -> supervised ZCODE_APP_SERVER_V1 -> actual create-time provider/model binding -> durable execution result -> AgentResultPacket -> scoped AgentChangeApplier/no-change result -> replay dedup`,

with zero human prompt/result relay and no new production authority.

## Classification

R2 NORMAL, test-only. This work changes integration evidence across multiple accepted authorities but does not modify production behavior. If any acceptance case requires a production-source change, STOP, checkpoint the RED evidence, and open/escalate a separate bounded R3 repair WO; do not expand this claim silently.

## Reuse-only contract

REUSE:
- ProviderConfiguration / ProviderEndpointConfig / ProviderConfigurationSnapshot;
- SQLiteProviderConfigStore + real ProviderAdmissionRecord acquisition/release;
- SQLiteWorkerLeaseStore + WorkerLeaseBroker;
- TaskPacketFile;
- assemble_zcode_execution / SupervisedZCodeRunner / SupervisedRunCoordinator;
- SupervisedExecutionService + ZCODE_APP_SERVER_V1 helper;
- WO176 ZCodeRuntimeModel provider/model/endpoint materialization + attestation;
- SQLiteExecutionStore / durable artifacts / dedup identity;
- AgentResultPacket / AgentChangeApplier and existing continuity/lease gates.

NEW production store/router/scheduler/retry/review/provider authority: FORBIDDEN.

## Mutable scope

Tracked scope:
- `docs/work-orders/WO-P1-178-zra-comp-1.md`
- `tests/test_zcode_real_helper_e2e.py` — one composition E2E plus test-only imports; scope expansion checkpointed in Issues #213/#233 before mutation
- ignored `runs/WO-P1-178/**` evidence

Forbidden:
- `src/a_conductor/**` production changes;
- provider/lease/store schemas;
- CURRENT-WORK.md / handoff.md / COLLAB.md;
- private Drive or secret values;
- live ZCode user config;
- installed A-Sunday Conductor app/live DB;
- broad process operations;
- merge/self-acceptance.

## Acceptance matrix

Positive CI-portable composition:
1. Create a disposable git/workspace + sacrificial SQLite authorities.
2. Persist canonical provider endpoint/profile/AVAILABLE observation and acquire a real generation-bound provider admission.
3. Acquire a real MUTATION WorkerLease through WorkerLeaseBroker, bound to exact project/worktree/branch/head/task/scope.
4. Verify TaskPacketFile bytes/hash.
5. Run production assembly through real supervised helper lifecycle and a CI-portable fake app-server child that records `session/create` and `session/send`.
6. Assert create payload carries the exact authorized WO176 runtimeModel provider/model/baseURL and only an env-key credential reference; synthetic secret never appears on protocol/argv/durable evidence.
7. Assert durable response/result/report identity and exactly one child spawn.
8. Convert the result into the existing AgentResultPacket/no-change path and prove no unauthorized mutation.
9. Replay the identical durable task/runtime identity and prove no second child spawn/execution.
10. Release provider admission and WorkerLease and verify terminal release state.

Fail-closed negatives (minimum five):
- provider generation drift -> no spawn;
- credential_ref mismatch -> no spawn;
- session model attestation missing/mismatch -> no `session/send` and no success;
- replay duplicate -> no second spawn;
- out-of-scope change or stale/invalid continuity/lease -> apply rejection and untouched disposable worktree;
- provider/lease/admission identity mismatch -> no spawn.

Windows host-only proof (skip when installed bundle unavailable):
- use installed ZCode 0.16.5 exact bundle hash and a synthetic loopback provider/credential only;
- actual bundle must contact only the authorized loopback endpoint/model, never ambient provider;
- natural child shutdown; exact PID proof; no live user ZCode config mutation.

## Verification

- RED first where current tests do not compose a required seam.
- targeted new test file;
- related ZCode/provider/lease/result/applier regression;
- Windows host-only installed-bundle case when available;
- `python -m compileall` for affected test/module import surface;
- `git diff --check`, strict UTF-8, exact scope and secret-value scan;
- freeze exact SHA -> independent review appropriate to R2 -> exact-head hosted CI -> GPT acceptance/merge.

## Completion boundary

This WO does NOT itself claim the real CoinTH live provider pilot. After ZRA-COMP-1 merges/post-main verifies, execute the separately prepared live ZRA-1 proof using current source, sacrificial control DB, canonical `secret-ref:awiki-env/COINTH_GLM_AUTH_TOKEN`, real admission/lease and exactly one harmless model turn. Human relay target remains 0.

## Bootstrap checkpoint

Fresh isolated worktree created from `origin/main@1244b14fd8bc09eba191433a0297c1fc5f3f14ac` after WO176 PR #250 merge and post-main CI run #34503380949 SUCCESS on Windows/Ubuntu/macOS. Open-PR read-only overlap scan found no source/test overlap; PR #249 touches only WO176/Wave-3 docs. Source scope remained forbidden throughout.

## Candidate verification checkpoint

The missing positive composition proof is implemented in the existing real-helper E2E surface instead of duplicating its fixture stack. The test acquires the provider admission and WorkerLease from their canonical SQLite authorities, consumes those exact records in `assemble_zcode_execution`, asserts the actual WO176 create-time provider/model/baseURL wire payload, crosses the existing AgentResultPacket/AgentChangeApplier NO_CHANGES boundary, replays the identical runner and proves no second child spawn, then releases both admission and lease.

First execution exposed only a test-fixture issue: legacy helper `HEAD = "h" * 40` is not a valid Git object id and therefore cannot pass canonical `WorkerLeaseRequest` validation. The composition test was corrected to use one valid synthetic hex head consistently across broker, execution authorities and result packet; no production source changed.

Deterministic evidence on Windows at base `1244b14fd8bc09eba191433a0297c1fc5f3f14ac`:
- new composition test: `1 passed`;
- combined composition/fail-closed authority battery: `264 passed`;
- fail-closed negatives are REUSE evidence rather than duplicated tests: provider generation and credential drift, lease/worktree/head/task/scope mismatches, admission provider/generation/batch/execution mismatches, session model attestation missing/mismatch, replay no-respawn, and AgentChange scope/continuity failures;
- production `src/a_conductor/**` changes: none.

Next gate: hygiene/scope checks -> freeze exact SHA -> independent exact-SHA R2 review -> hosted CI -> GPT acceptance/merge -> post-main verification. Real CoinTH live proof remains a separate next gate.
