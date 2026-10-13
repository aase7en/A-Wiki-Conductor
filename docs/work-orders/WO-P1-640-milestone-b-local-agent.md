# WO-P1-640 — MILESTONE-B: offline local-agent integration (test-only credentials)

Status: DONE — SRM PR #24 merged 2026-10-13 at `f5f3fdd` (pinned-head `9d59b7d`); review chain: independent GLM exact-SHA PASS at `c9cdd1c` (0 P0/P1/P2; P3 repairs pre-merge); claim released #640 comment 6144238748
Issue: #640
Parent: #495 (fabric; authorization c6143365204 — MILESTONE_B=OFFLINE_READY_SUBJECT_TO_WO_AND_CLAIM), #630 (Option 1 lineage), REPLACE-ALL Goal Milestone B (2026-10-13 steer).
Risk: R3 — composes shipped trust contracts (enrollment verification, credential lifecycle semantics, at-most-once anchor) into one runtime; offline/test-only throughout.
Topology: EXECUTION_SUBSTRATE_ONLY. Compatibility: SRM `cb5950c` + AWC `572fd70` (re-pin on drift).

## Scope (offline; no public endpoint, no real credentials, no live enrollment, no real filesystem)

ONE SRM runtime `src/sunday/local-agent.ts` integrating the shipped contracts by composition (REUSE first):

1. **Enrollment binding** — test-only `IssuerTwin` + `runEnrollmentFlow` (PKCE S256, device-screen consent affordances, offline compact-JWS credential verification before any pairing write) → PAIRED device identity. The enrollment PoP key pair is THE agent registration key (cnf-bound).
2. **Agent-side transport contract** — compose `SimAgent` (canonical PoP registration frame; durable generation-INDEPENDENT `command_id` dedup as the authoritative at-most-once anchor; reconcile) against the shipped `SimRouter` (freshness/nonces/GENERATION_TAKEN/SUPERSEDED_GENERATION, revocation, PENDING-insert-before-execute).
3. **Read-only fixture executor** — pure synthetic fixture tree at an injected allowlist root; ops `read`/`list` only; typed fail-closed denials: absolute path, `..` traversal, outside-root, missing target, node-type mismatch, and ANY non-read-only op kind. No real filesystem access. No write/mutation surface in this slice.
4. **Credential lifetime guards** — NEW executions fail closed after credential expiry (`now >= exp`); recorded duplicate outcomes remain authoritative (dedup checked first — the M4 anchor is not weakened by expiry). Router-side revocation stays the dispatch-time bound and is pinned through this integration.
5. **Restart semantics** — agent dedup state persists via an injectable load/save store; a restarted agent (fresh instance, same store) serves recorded outcomes for duplicates and executes new commands exactly once.

## Deterministic test matrix (RED first; `test/test-sunday-local-agent.js`, plain node, imports `../dist/`)

enroll PAIRED (deviceId assigned, state saved) · enroll denied (typed failure, no execution surface) · authorized read returns fixture content (stateful execution counter) · denied reads: absolute / traversal / outside-root / missing / read-on-dir / list-on-file · non-read-only op kind rejected (OP_NOT_READ_ONLY) · duplicate command_id returns recorded outcome, counter UNCHANGED · restart from store: duplicate served from record, new command executes once · credential expiry: new execution refused (CREDENTIAL_EXPIRED), prior duplicate still served · router revocation blocks dispatch · registration integration rows via SimRouter (REGISTERED; forged PoP POP_INVALID; nonce replay NONCE_REPLAY; stale ts STALE_TS).

## Forbidden

Public endpoints/listeners; production credentials/keys; live/real enrollment; real filesystem, hospital or private data; write/mutation tools; weakening any shipped contract (enroll-contract, enroll-credential-lifecycle, transport-sim semantics); mock-as-production claims; interop claims against unmerged #335.

## Checkpoint log (append-only)

- [2026-10-13] WO created. Lane issue #640 verified real (gh issue view) BEFORE naming; one clean `Issue: #640` line. No source mutation yet. Operator authorization: #495 c6143365204 (NEXT_READY without further operator approval, subject to canonical WO/claim/R3 gates).
