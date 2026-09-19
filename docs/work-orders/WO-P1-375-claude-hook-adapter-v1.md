# WO-P1-375 — Claude Code Hook Adapter v1 Conformance

Status: RE-PINNED / READY_FOR_REREVIEW
Issue: #375
Identity schema: GITHUB_ISSUE_V1
Risk: R3 trust/redaction contract
Topology: CONTROL_PLANE_ONLY
Dependency: WO-P1-258 Hook Contract exact 602f6db01e170f74456ff77e1b5df01622fb84dd
(md blob 941f9731f9665fe109451a14cdc2b737555be99a,
schema blob d176fd5e6393af6f5619fad372ad59aa858391ee)

## Current binding (canonical, WO-P1-375 rebind lane)
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo375-claude-hook-rebind
Branch: fix/wo-p1-375-claude-hook-rebind
Dispatch HEAD (base): 27b55a9d6efc2b7c4d9754130e0365abed6cadf4
Claim: WO-P1-375-CLAUDE-HOOK-ADAPTER-REBIND-001
Result destination: runs/WO-P1-375/repair/attempt-0001/
Replay safety: recover pointer/process/result/Git before redispatch.

## Mutable scope
docs/contracts/claude-hook-adapter-v1.md
tests/test_claude_hook_adapter_contract.py
tests/fixtures/hook_adapters/claude/**
this Work Order (renamed from docs/work-orders/WO-P1-261-claude-hook-adapter-v1.md)
Everything else read-only; no src/runtime mutation.

## Goal
Define deterministic Claude native-hook to Hook Contract v1 mapping and fixtures.
No task/claim/mutation authority. Secret/raw prompt/credential/argv data must not
enter normalized payloads. Unsupported version/capability is explicit typed
degrade/reject; no silent fallback. GUARD decisions come only from existing authority.
WO-P1-375 additionally rebinds canonical task identity to Issue #375 and re-pins
the dependency from the WO261 freeze pin to the accepted Hook Contract head.

## Acceptance
Offline fixture conformance, invalid/redaction/version cases, exact dependency SHA,
scope/diff/UTF-8/secret checks, frozen SHA, independent review + CI.
If the Hook Contract head drifts from the pin, fail closed and re-pin before
further mutation.

## Historical alias / identity migration (WO-P1-261 -> WO-P1-375)

WO-P1-261 is the superseded task identity for this same work. It is preserved
here as historical factual evidence only and is NOT current authority. Canonical
task identity is WO-P1-375 / Issue #375 (identity schema GITHUB_ISSUE_V1).

Historical WO261 binding facts (unchanged, evidence only):

- Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo261-claude-hook-adapter
- Branch: docs/wo-p1-261-claude-hook-adapter-v1
- Base/contract SHA at freeze: f20fff006aad1e592b150ffdcb52ac331ec00a3a
  (Hook Contract md blob b4f98fb8f2ce35958b4e5cfc660eeb671c46d723,
  schema blob 23c5dc3035320dc288e376bd103d8e00409a9762)
- Owner: GLM-5.3 MAX author under GPT-5.6 Sol
- Claim: WO-P1-261-CLAUDE-HOOK-ADAPTER-001
- Result destination: runs/WO-P1-261/author/
- Prior adapter candidate: e50bd5ab9603bf98d0c4aaa82bfc01d6b2240f7e
  (`feat(WO261): Claude hook adapter v1 conformance contract + offline
  fixtures/tests`)

The remote PR transport branch remains named
`docs/wo-p1-261-claude-hook-adapter-v1` (head e50bd5ab9603bf98d0c4aaa82bfc01d6b2240f7e).
That branch name is retained historical transport naming only; branch naming
grants no task authority.

Dependency history: the WO261 freeze pinned f20fff006aad1e592b150ffdcb52ac331ec00a3a;
the accepted Hook Contract review-001 head 602f6db01e170f74456ff77e1b5df01622fb84dd
(merged to main via 2a461ae22ab28ad3b48f15660ab818f700faab30) supersedes it. The
WO-P1-375 rebind lane re-pinned the adapter contract and tests to the 602f6db
blobs (see the rebind/re-pin checkpoint below).

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

## Rebind/re-pin checkpoint (2026-09-19, WO-P1-375 rebind lane)

- Baseline at dispatch HEAD 27b55a9d6efc2b7c4d9754130e0365abed6cadf4 (clean
  tree, branch fix/wo-p1-375-claude-hook-rebind): adapter suite 73 passed,
  Hook Contract suite 97 passed. The accepted Hook Contract creates NO
  compatibility failure in adapter behavior; the defect was a stale recorded
  dependency pin (f20fff0 blobs) that the old pin test could not detect.
- Dependency re-pin: f20fff006aad1e592b150ffdcb52ac331ec00a3a (md blob
  b4f98fb8f2ce35958b4e5cfc660eeb671c46d723, schema blob
  23c5dc3035320dc288e376bd103d8e00409a9762) -> accepted head
  602f6db01e170f74456ff77e1b5df01622fb84dd via merge
  2a461ae22ab28ad3b48f15660ab818f700faab30 (md blob
  941f9731f9665fe109451a14cdc2b737555be99a, schema blob
  d176fd5e6393af6f5619fad372ad59aa858391ee); old pin preserved in the
  contract doc as superseded historical evidence.
- Identity rebind: contract status line and test module identity -> WO-P1-375 /
  Issue #375; this Work Order renamed from WO-P1-261 with the full historical
  alias/migration record above (prior candidate e50bd5ab and all WO261
  claim/lane/run/branch/worktree/result pointers preserved verbatim).
- Semantics re-pinned to the accepted contract with no authority change:
  OBSERVE-only intact; GUARD/COMMAND still forbidden; adapter payload still
  only `transport.adapter_capabilities` (now also schema-enforced, proven by a
  new negative test); dedupe identity is the global `event_id` (adapter
  supplies no `dedupe_key`) and `source` + `sequence` never becomes duplicate
  identity; stream-domain ordering, append-only history, k-way merge, gap
  handling, and replay-window dedupe remain fully delegated (Hook Contract
  §4/§5). No new runtime/store/claim/retry/review authority.
- Regression proof added: `test_recorded_pin_equals_actual_hook_contract_blobs`
  fails closed if the working-tree Hook Contract blobs drift from the recorded
  pin; superseded-pin preservation, identity/dedupe doc locks, and the
  adapter-payload schema constraint are also asserted.
- Verification at candidate head: adapter suite 77 passed; Hook Contract suite
  97 passed; `git diff --check` clean; strict UTF-8 with no U+FFFD on all
  changed files; secret scan clean (fake-secret-corpus/1 confined to the test
  module vocabulary and the 4 marked bait frames); scope diff vs dispatch HEAD
  is exactly docs/contracts/claude-hook-adapter-v1.md,
  tests/test_claude_hook_adapter_contract.py, and the WO261->WO375 rename;
  fixtures byte-unchanged; Kilo adapter files, Hook Contract files, src/**,
  WO369/WO381/A-Faster scope, and continuity files untouched.
- Stop state: READY_FOR_REREVIEW at this commit (head recorded in
  runs/WO-P1-375/repair/attempt-0001/result.md). No merge, no self-accept;
  independent exact-SHA review + CI remain open per acceptance gates.
