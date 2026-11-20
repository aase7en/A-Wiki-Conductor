# WO-P1-636 — INSTALL-M4-SIM: offline transport simulation

Status: DONE — SRM PR #23 merged 2026-10-13 at `cb5950c` (pinned-head `009ed01`); review chain SRM PR #23 comment 6138013687; claim released #636 comment 6138014267
Issue: #636
Parent: #495 (fabric), #630 (Option 1 lineage); design = issue #636 body (v2, challenger-verified).
Risk: R3 — transport/trust protocol semantics (deterministic offline simulation only).
Topology: EXECUTION_SUBSTRATE_ONLY (SRM source; AWC docs only). Compatibility: SRM `46f5a54` + AWC `25cb18b` (re-pin on drift).

## Scope (offline; no public endpoint, no real credentials, no live enrollment)

In-process deterministic simulation of the v2 design: pure router+registry (durable single-unit state semantics via an injectable serialized store double), fake transport with loss/duplication/reorder injection, a simulated agent over the test-only issuer twin's credential family. Fault matrix per design §4: reconnect races, duplicate sessions, stolen-bearer registration, wrong-device traffic, mid-command loss (UNKNOWN reconciliation), stale generations, revoked devices, duplicate command ids (IN_FLIGHT/OUTCOME/DUPLICATE), generation split-brain co-execution attempts, registration replay (freshness/nonce), router-restart restoration.

## Forbidden

Public endpoints/listeners; production credentials/keys; live enrollment; weakening any shipped contract; interop claims against unmerged #335 (by-specification reuse only; merge-order re-verify condition recorded).

## Checkpoint log (append-only)

- [2026-10-13] WO created; lane issue #636 verified real BEFORE naming; design v2 posted as the issue body and independently challenged (REVISION_REQUIRED 6xP1 -> all closures verified -> SOUND_FOR_SUCCESSOR_WO). No source mutation yet.
- [2026-10-13] COMPLETE — SRM PR #23 merged at `cb5950c` (pinned-head `009ed01`; worktree SRM-m4-sim off `46f5a54`; claim c6137476769, released c6138014267). Design v2 + LOCAL_FIRST_NOW/CLOUD_OPTIONAL_LATER addendum v2.1 (c6137500621). R3 review: 2 exact-SHA rounds on the separate GLM lane (r1 CHANGES_REQUIRED 3xP2: tautological no-re-execution row / liveness outside the serialized apply unit / missing IN_FLIGHT row -> repaired at `d368bef` -> r2 PASS; nits at `009ed01`; chain SRM PR #23 c6138013687). CI codespell SUCCESS; post-main verify green (transport-sim + enroll suites). Delivered: pure offline simulation — PoP registration (freshness/nonces/GENERATION_TAKEN/SUPERSEDED_GENERATION), durable single-unit router state with authoritative restart, atomic insert-before-execute command machine (agent-side durable generation-independent dedup as the authoritative at-most-once anchor, pinned by a stateful execution counter), revocation TTL bound + fresh registration introspection, no-co-execution invariant, UNKNOWN+reconcile+new-id retry. Recorded follow-ups (live phase): agentAck=false and SUPERSEDED_GENERATION rows untested; registration cache-bypass pinned by code inspection; #335 merge-order re-verify.
