# WO-P1-262 — Kilo Hook Adapter v1 Conformance

Status: READY_FOR_REVIEW (candidate frozen on this branch; no merge/self-accept)
Issue: #376
Risk: R3 provider/harness/redaction contract
Topology: CONTROL_PLANE_ONLY
Dependency: WO-P1-258 Hook Contract exact f20fff006aad1e592b150ffdcb52ac331ec00a3a

## Binding
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo262-kilo-hook-adapter
Branch: docs/wo-p1-262-kilo-hook-adapter-v1
Base/current contract SHA: f20fff006aad1e592b150ffdcb52ac331ec00a3a
Owner: GLM-5.3 MAX author under GPT-5.6 Sol
Claim: WO-P1-262-KILO-HOOK-ADAPTER-001

## Mutable scope
NEW docs/contracts/kilo-hook-adapter-v1.md
NEW tests/test_kilo_hook_adapter_contract.py
NEW tests/fixtures/hook_adapters/kilo/**
this Work Order
Everything else read-only; no src/runtime mutation.

## Goal
Define deterministic Kilo native evidence to Hook Contract v1 mapping and fixtures.
No task/claim/provider-admission/mutation authority. Redact share URLs, credentials,
raw prompts and secret-bearing commands. Model/provider/version mismatch must be
explicit; no silent provider/model fallback.

## Acceptance
Offline fixture conformance, invalid/redaction/version cases, exact dependency SHA,
scope/diff/UTF-8/secret checks, frozen SHA, independent review + CI.
If WO258 head drifts, fail closed and re-pin before further mutation.

Result destination: runs/WO-P1-262/author/
Replay safety: recover pointer/process/result/Git before redispatch.

## Checkpoint 2026-09-19 — author attempt-0001 READY_FOR_REVIEW

Delivered exactly the four-path NEW-only scope on top of dispatch HEAD
06377ee0a0a353919c997fc50ca7862af2866c7c (dependency f20fff0 verified as
parent; tree clean before mutation):

- docs/contracts/kilo-hook-adapter-v1.md — adapter contract: safe
  capability evidence (Kilo CLI 7.7.2; `run --format json` raw JSON
  events; `plugin` install surface with UNPROVEN lifecycle vocabulary),
  OBSERVED/ASSUMED/UNKNOWN capability table, fixture grammar, Hook
  Contract v1 mapping, identity/ordering/dedupe (supports_sequence=false,
  arrival order, no synthesized sequence, no second event store), digest-
  only redaction, capability discovery + fail-closed mismatch rules.
- tests/fixtures/hook_adapters/kilo/** — capability doc, 6 native-shaped
  fake streams (basic/redaction/provider-mismatch/version-drift/
  version-unverified/invalid-records), 2 generated expected-envelope
  files, README provenance.
- tests/test_kilo_hook_adapter_contract.py — deterministic reference
  mapper + 21 offline conformance tests (exact expected equality, schema
  validity, dedupe/identity stability, corpus/share-URL exclusion with
  digest verification, unknown type/status/record typed drops, version/
  provider-model/capability fail-closed, metadata-only model proof).

Evidence: adapter suite 21 passed; Hook Contract suite 82 passed (103
total incl. parametrized); `git diff --check` clean; strict UTF-8 decode
of all 20 added files; added-line secret scan 0 non-fake hits (only the
declared fake-secret-corpus/1 and one fake share-URL shape inside native
redaction fixtures); normalized outputs carry no fakes. Kilo capability
evidence recorded at runs/WO-P1-262/author/attempt-0001/
kilo-capability-evidence.md (gitignored). No src/runtime mutation; Hook
Contract files untouched.

Risks/unknowns for review: (1) `tool_use.state.status` vocabulary,
timestamp offsets, and part-field placement are ASSUMED fixture grammar,
not observed — live emission requires capability discovery re-proof;
(2) plugin lifecycle APIs remain UNKNOWN and unmapped by design;
(3) adapter binds to native family 7.7.x (observed 7.7.2) and fails
closed on any other version until re-pinned.

Next: independent exact-SHA review + CI on this branch head; GPT accept/
merge authority retained.
