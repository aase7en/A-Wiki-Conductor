# WO-P1-261 — Claude Code Hook Adapter v1 Conformance

Status: CLAIMED / BOOTSTRAP
Issue: #375
Risk: R3 trust/redaction contract
Topology: CONTROL_PLANE_ONLY
Dependency: WO-P1-258 Hook Contract exact f20fff006aad1e592b150ffdcb52ac331ec00a3a

## Binding
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo261-claude-hook-adapter
Branch: docs/wo-p1-261-claude-hook-adapter-v1
Base/current contract SHA: f20fff006aad1e592b150ffdcb52ac331ec00a3a
Owner: GLM-5.3 MAX author under GPT-5.6 Sol
Claim: WO-P1-261-CLAUDE-HOOK-ADAPTER-001

## Mutable scope
NEW docs/contracts/claude-hook-adapter-v1.md
NEW tests/test_claude_hook_adapter_contract.py
NEW tests/fixtures/hook_adapters/claude/**
this Work Order
Everything else read-only; no src/runtime mutation.

## Goal
Define deterministic Claude native-hook to Hook Contract v1 mapping and fixtures.
No task/claim/mutation authority. Secret/raw prompt/credential/argv data must not
enter normalized payloads. Unsupported version/capability is explicit typed
degrade/reject; no silent fallback. GUARD decisions come only from existing authority.

## Acceptance
Offline fixture conformance, invalid/redaction/version cases, exact dependency SHA,
scope/diff/UTF-8/secret checks, frozen SHA, independent review + CI.
If WO258 head drifts, fail closed and re-pin before further mutation.

Result destination: runs/WO-P1-261/author/
Replay safety: recover pointer/process/result/Git before redispatch.
