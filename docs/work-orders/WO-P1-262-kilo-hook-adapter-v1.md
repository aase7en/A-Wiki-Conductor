# WO-P1-262 — Kilo Hook Adapter v1 Conformance

Status: CLAIMED / BOOTSTRAP
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
