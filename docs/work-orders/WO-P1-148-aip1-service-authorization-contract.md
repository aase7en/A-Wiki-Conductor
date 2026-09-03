# WO-P1-148 — AIP-1 provider service-authorization contract

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: CLAIMED / RED_FIRST
Priority: P1
Repository: `A:\\GitHub\\A-Wiki-Conductor`
Worktree: `A:\\GitHub\\A-Wiki-Conductor-wo148-service-authorization`
Branch: `feat/wo-p1-148-service-authorization-contract`
Base: `origin/main@6e96b773aeb0795807cb65abce93956b7702f33e`

## Prerequisite proof
- PR #183 exact head `a84f7a8569846c196ba3000f69d9e83eb473ad96`; CI `33710739794` SUCCESS; merge `6e96b773aeb0795807cb65abce93956b7702f33e`; post-main `33712217339` SUCCESS.
- GLM long audit `wo132-glm-aip1-audit-002`, task SHA `4a11cec8f9ddd657b3a75effddc82c525fca17ab58d99ad1cd1e6c57681c19c8`: PREAUDIT_COMPLETE, P0/P1/P2=0.
- Fresh AiPASS Terms effective 2026-08-19 section 3.4 still require explicit written authorization for the gated automation/direct-system modes; live automation defaults `BLOCKED_EXTERNAL`.
- Fresh upstream `niawjunior/aipass-bridge@d59f03d8c58071f0fd947e6d286194e972521544`; MIT; root LICENSE blob `17ddd0b8425c523d029917a1027d7e40a0916100`. MIT source permission is not service authorization.

## Reuse-before-build
Classification: `EXTEND` with one pure provider-neutral guard. Reuse existing provider identity/generation/readiness/task-policy/admission/runtime authorities unchanged. Do not add a second registry, policy engine, scheduler, quota/admission engine, retry state machine, memory store, credential vault, or mutation authority.

## Mutable scope
- new `src/a_conductor/provider_service_authorization.py`
- new `tests/test_provider_service_authorization.py`
- this work order
- bounded `COLLAB.md` claim/release bookkeeping only

Forbidden: `provider_config_store.py`, `provider_policy.py`, `provider_execution_authority.py`, `parallel_ready_execution.py`, runtime/UI/adapter files, DB migrations, Workers/tunnels, credentials/cookies/tokens, live AiPASS traffic.

## Contract target
Preserve: `CONFIGURED != READY != SERVICE_AUTHORIZED != TASK_AUTHORIZED != ADMITTED != EXECUTED`.
The pure guard owns only SERVICE_AUTHORIZED. It performs no I/O and cannot make a provider READY, authorize a task, acquire admission, or execute anything.

Modes: `FAKE`, `READ_ONLY`, `LIVE`. `FAKE` is guaranteed zero-service-I/O and needs no external authorization. `READ_ONLY` and `LIVE` require exact current service authorization; both fail closed otherwise.
Authorization evidence is represented only by a SHA-256 digest, never raw approval text, URL query, cookie, token, header, or credential.

## RED acceptance matrix
1. FAKE is allowed without service evidence and carries an explicit no-service-I/O reason.
2. READ_ONLY/LIVE with no record fail closed.
3. UNKNOWN/BLOCKED_EXTERNAL fail closed.
4. provider mismatch fails closed.
5. requested mode mismatch fails closed.
6. stale Terms identity fails closed.
7. provider generation drift fails closed.
8. expired recheck window fails closed.
9. AUTHORIZED requires a valid evidence SHA-256.
10. timestamps must be timezone-aware and ordered.
11. record/decision serialization and repr expose no raw secret-bearing fields by construction.
12. MIT/source-license evidence cannot make service authorization allowed.
13. malformed enum/text/hash/generation inputs fail validation.
14. pure evaluator has no filesystem/network/process/store side effects.

## Verification
RED first, then focused tests, existing provider regression matrix, compile/diff/UTF-8/secret/scope audits, independent exact-SHA review before merge. No live test is authorized in WO148.
