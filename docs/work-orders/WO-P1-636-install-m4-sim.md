# WO-P1-636 — INSTALL-M4-SIM: offline transport simulation

Status: READY (design accepted SOUND_FOR_SUCCESSOR_WO; implementation claim pending)
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
