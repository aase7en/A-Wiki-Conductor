# WO-P1-261 — Claude Code Hook Adapter v1 Conformance

Status: AUTHOR_COMPLETE / READY_FOR_REVIEW
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

## Author checkpoint (2026-09-19, GLM-5.3 MAX)

- Dependency verified fail-closed at dispatch: dispatch HEAD 1a44418d50cf14c10649765f04ea75fafc7697c1,
  parent = f20fff006aad1e592b150ffdcb52ac331ec00a3a (ancestor confirmed),
  Hook Contract blobs identical at both commits
  (md b4f98fb8f2ce35958b4e5cfc660eeb671c46d723, schema 23c5dc3035320dc288e376bd103d8e00409a9762).
  Tree was clean; scope stayed NEW-only.
- Local capability evidence (version/help only, 2026-09-19): claude --version
  -> "2.1.178 (Claude Code)"; --help proves a hooks subsystem
  (--bare skips hooks, --safe-mode disables them), hook lifecycle events in
  stream-json via --include-hook-events, and a --debug "hooks" category.
  No native event name asserted for any real version; 2.1.178 registry entry
  is DISCOVERY_REQUIRED with zero bindings and emits only
  transport.adapter_capabilities.
- Deliverables: docs/contracts/claude-hook-adapter-v1.md (OBSERVE-only mapping
  contract; OBSERVE-only, GUARD/COMMAND forbidden; registry-gated mappings for
  session/prompt/tool pre-post-failed/subagent/stop; closed-field allowlist;
  digest-only command identity; fixed-vocabulary summaries; typed
  unavailable/unsupported/invalid/oversized outcomes with no silent fallback;
  ordering/dedupe delegated to Hook Contract), plus 17 fixture files
  (capability_registry.json, 14 frames, 12 expected) and
  tests/test_claude_hook_adapter_contract.py.
- Verification: adapter suite 73 passed; Hook Contract dependency suite
  82 passed (155 total, deterministic offline). git diff --check clean;
  strict UTF-8 on all 28 new/changed files; fake-secret corpus confined to
  the 4 marked bait frames and never present in registry/expected/envelopes.
- Stop state: READY_FOR_REVIEW at this commit. No merge, no self-accept.
  Independent review + CI remain open per acceptance gates.
