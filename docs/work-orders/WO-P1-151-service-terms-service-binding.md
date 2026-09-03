# WO-P1-151 - Service authorization service/Terms binding

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: CLAIMED / RED_REQUIRED
Priority: P1
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo151-service-terms-binding`
Branch: `fix/wo-p1-151-service-terms-binding`
Base: `origin/main@128844c7d719a61c959f2a20df3a8646ddabef8c`

## Root cause
Merged WO148 proves provider/mode/Terms/generation/chronology, but its semantic Terms slug is not bound to a trusted service identity.
A record/evaluation can consistently pair `provider_id=aipass` with `other-service-terms@2026-08-19` and return `SERVICE_AUTHORIZATION_ALLOWED`.
Provider IDs are opaque/provider-neutral, so comparing the Terms slug directly with provider_id would be incorrect.

## Goal
Extend the pure WO148 guard with an explicit trusted `service_identity` binding.
The service slug encoded by `<service>-terms@YYYY-MM-DD` must match the declared service identity.
No I/O, storage, provider readiness, task policy, admission, quota, runtime or live AiPASS traffic.

## Mutable scope
- `src/a_conductor/provider_service_authorization.py`
- `tests/test_provider_service_authorization.py`
- this work order
- bounded `COLLAB.md` claim/release bookkeeping

## RED acceptance
1. AUTHORIZED record rejects service identity that does not match the Terms slug.
2. Evaluation rejects requested service identity mismatch.
3. Cross-service Terms cannot authorize another service even when provider/mode/generation/Terms strings otherwise match.
4. Same service identity + matching Terms preserves existing allowed behavior.
5. FAKE remains zero-service-I/O and does not gain authorization semantics.
6. Service identity is a bounded public slug; raw path/header/token/query shapes fail validation.
7. Serialization/repr contains only public service identity, never approval text or credentials.
8. Existing provider-neutral behavior and all WO148 chronology/timezone protections remain green.

## Verification
- RED focused tests before production edit.
- GitNexus impact before production symbol edit if available; tool failures recorded, no DLL installation.
- focused service-auth suite.
- broad provider/config/store/policy/execution-authority/runtime/parallel/quota/harness regression.
- `py_compile`, `git diff --check`, strict UTF-8/U+FFFD, scope and added-secret scans.
- independent exact-SHA review before PR/merge.

## Forbidden
No provider config/store migration, policy/runtime/admission/UI changes, no live AiPASS call, no cookies/tokens/credentials, no A-Wiki mutation, no destructive Git.

## Next safe action
Commit/push claim, add deterministic RED tests only, prove failure, then minimally extend the pure service-authorization contract.
