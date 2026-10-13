# WO-P1-643 — MILESTONE-B2: credential refresh integration (offline, test-only)

Status: DONE — SRM PR #25 merged 2026-10-13 at `3be057a` (pinned-head `08ec3c2`); review chain: independent GLM exact-SHA PASS at `08ec3c2` (0 P0-P2, 5 P3 notes, no repairs); claim released #643 comment 6146249340
Issue: #643
Parent: #495 (fabric; steer c6143365204 item 7 — continue READY offline tasks), #640 (Milestone B predecessor, DONE at SRM `f5f3fdd`).
Risk: R3 — composes shipped trust contracts (offline token verification, cnf binding, at-most-once anchor) with a credential-rotation path; offline/test-only throughout.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `f5f3fdd` + AWC `366f807` (re-pin on drift).

## Scope (offline; no public endpoint, no real credentials, no live enrollment, no real filesystem; ZERO shipped-file changes)

Extend `src/sunday/local-agent.ts` (the WO-P1-640 runtime) with the credential-lifetime loop:

1. **Refresh-token capture at enrollment (WRAP)** — `LocalAgent.enroll` wraps the caller's issuer port `poll` and retains the refresh token in the agent durable state. `runEnrollmentFlow`'s shipped return shape is untouched (WRAP beats EXTEND per the reuse gate). Test-only custody: production key/credential custody remains the standing Phase-1 human gate.
2. **Refresh seam** — runtime-owned `RefreshIssuerPort` (`refresh(refreshToken) -> { accessToken; refreshToken }`) mirroring the test-only twin's rotation-on-use refresh. The PoP-bound refresh presentation against the real Option-1 issuer stays in the shipped `verifyRefreshPresentation` contract (M3-live slice, human-gated).
3. **`LocalAgent.refresh(options)`** — call the port; OFFLINE-verify the new access token with the enrollment verification options family (issuer/audience/device/scope/expiry/signature); REQUIRE `cnf` == enrolled PoP thumbprint; on success set `credentialExp` FROM `claims.exp` (verified-credential-derived — closes the WO-P1-640 P3-1 note properly) and persist the rotated refresh token.
4. **Typed failures** — `REFRESH_NO_TOKEN`; `REFRESH_ISSUER_REJECTED` (port throw/denial: covers rotation-on-use replay and revoked device); `REFRESH_CREDENTIAL_REJECTED` (offline verification or cnf mismatch). Credential stays expired on every failure path.

## Deterministic test matrix (RED first; `test/test-sunday-local-agent.js` additions)

expired → `CREDENTIAL_EXPIRED` → refresh → `REFRESHED` (exp == verified claims.exp) → NEW command executes · old-token replay after use → `REFRESH_ISSUER_REJECTED` (rotation-on-use) · revoked device → `REFRESH_ISSUER_REJECTED` · malicious port returning wrong/garbage token → `REFRESH_CREDENTIAL_REJECTED` · no retained token → `REFRESH_NO_TOKEN` · duplicate command after refresh still returns the recorded outcome (dedup survives refresh) · restart persists the retained token (refresh possible after restart).

## Forbidden

Public endpoints/listeners; production credentials/keys; live/real enrollment; real filesystem or hospital/private data; write/mutation tools; weakening any shipped contract (including `runEnrollmentFlow`'s return shape); mock-as-production claims.

## Checkpoint log (append-only)

- [2026-10-13] WO created. Lane issue #643 verified real (gh issue view) BEFORE naming; one clean `Issue: #643` line. No source mutation yet.
