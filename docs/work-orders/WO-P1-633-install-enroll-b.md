# WO-P1-633 — INSTALL-ENROLL-B: contract extension + test-only issuer twin + enroll wiring

Status: DONE — SRM PR #22 merged 2026-10-13 at `46f5a54` (pinned-head `ee975ab`); review chain SRM PR #22 comment 6132007917; claim released #633 comment 6132008724
Issue: #633
Parent: #630 (Option 1 c6122489537; M2 approval c6131329187; proposal v2 c6127288782); audit #607 c6122338729.
Risk: R3 — authentication and trust contract.
Topology: EXECUTION_SUBSTRATE_ONLY — SRM source only; AWC untouched except this doc.
Compatibility gate: SRM `cdb669ec5294e814100e7cf8e58330b328752825` + AWC `b356d9c30705e1649f56cdb7b2446d6c8c123e9a` (read-only references). Drift before merge → re-pin.

## Scope (offline; per the approved M2 contract)

1. Extend `src/sunday/enroll-contract.ts`: refresh semantics (rotation-on-use, revocation lists, idle ≤30d/absolute ≤180d bounds), PoP binding (cnf/jwk claim registered at /device/start; refresh requires PoP signature over a challenge), signed-JWKS continuity (new keys ONLY inside JWKS revisions signed by a currently-trusted key; attacker-origin/unsigned/foreign-signed JWKS rejected).
2. Test-only issuer twin under `src/sunday/test-issuer/` — structural firewall (imported only by tests; lint guard in the test runner or a dedicated export surface), implementing the exact issuer-side contract (device-start/poll, PKCE verification, signing, refresh, revocation) with injectable keys/clock. NEVER a production minting path.
3. `sunday enroll` end-to-end wiring against an injectable issuer: drives the PKCE device-grant flow, verifies the returned credential OFFLINE via the extended contract, calls completePairing ONLY with the verified credential. Fail-closed everywhere; UNPAIRED stays the default.
4. Adversarial matrix: slice-A rows + refresh-replay, PoP-forgery, unsigned/foreign-signed/attacker-origin JWKS, stale device code, interrupted enrollment retry, revoked-device drop-to-UNPAIRED, expired refresh, idle/absolute bound violations.

## Forbidden

Live network issuance; deployment/hosting/keys; new listeners; production credentials; RDC tokens as PAIRED; fabricating production PAIRED state; second authority store; weakening any slice-A guarantee or accepted test.

## Stop conditions

- If the contract extension forces a breaking change to slice-A's shipped interface → park, re-scope additively.
- If the twin cannot be structurally firewalled to the reviewer's satisfaction → park that seam for redesign.

## Checkpoint log (append-only)

- [2026-10-13] WO created per the approved M2 contract (c6131329187); lane issue #633 verified as a real issue BEFORE naming. Audit + slice-A seams grounded. No source mutation yet; SRM worktree off cdb669e next.
- [2026-10-13] COMPLETE — SRM PR #22 merged at `46f5a54` (pinned-head `ee975ab`; worktree SRM-enroll-b off `cdb669e`). R3 review: 2 exact-SHA rounds on the separate-session GLM read-only lane (r1 PASS with P2 hardening: unconditional cnf, strict nbf + finite guards, seenRtis caller-contract, dead code; r2 PASS verifying closures; chain: SRM PR #22 c6132007917). CI codespell SUCCESS; post-main verify 5 enroll suites + agent-gate green. Recorded follow-ups for the wiring slice: thread seenRtis on every refresh call; JWKS revision sequence/rollback; Infinity test row via raw 1e999; slow_down docstring; guard breadth. M3 offline contract COMPLETE; the issuer/verifier implementation + authenticated workflow remainder sits behind the deployment/hosting/keys human gates.
