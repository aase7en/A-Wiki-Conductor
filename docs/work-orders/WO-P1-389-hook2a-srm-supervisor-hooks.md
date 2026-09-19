# WO-P1-389 — HOOK-2a SunDayRemoteMCP Supervisor Hook Normalization Foundation

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #389
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — cross-repo contract/runtime boundary
Topology: CROSS_REPO

## Authority and compatibility binding

Authority repo:
- repo: aase7en/A-Wiki-Conductor
- worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo389-hook2a-authority
- branch: feat/wo-p1-389-hook2a-srm-hooks
- branch base: 480a2cc7565adaa02d301d92c898af3d3ea784cf
- accepted Hook Contract candidate: 602f6db01e170f74456ff77e1b5df01622fb84dd
- Hook Contract blobs:
  - docs/contracts/hook-contract-v1.md = 941f9731f9665fe109451a14cdc2b737555be99a
  - docs/contracts/hook-contract-v1.schema.json = d176fd5e6393af6f5619fad372ad59aa858391ee
- control-plane HOOK-1 is accepted on main by merge commit 3067bd32569d7bcd6cc41e18c1c97a9a4f7db9c9

Execution repo:
- repo: A:\GitHub\SunDayRemoteMCP
- canonical local-first main at claim: ac01b37ba2e4b9d0249addf7694c0b91deb352c7
- remote: NONE / DEFERRED by existing local-first repository policy
- root worktree is protected; untracked .serena/ belongs to local tooling and is OUT OF SCOPE
- implementation MUST use an isolated SRM worktree/branch from the exact base above

Claim:
- WO-P1-389-HOOK2A-SRM-SUPERVISOR-HOOKS-001
- integrator: GPT-5.6 Sol
- preferred implementation labor: GLM-5.3 MAX
- planning authority: docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md §9
- authority boundary: ADR-0002 / execution substrate only

## Reuse classification

EXTEND + WRAP existing SRM primitives:
- src/sunday/supervisor-evidence.ts
- src/sunday/supervisor.ts
- existing durable events.jsonl
- existing supervisor execution/recovery evidence

Do NOT add:
- another event store or queue;
- another execution/task/job/claim/retry/review/completion authority;
- Hook Bus, STM or Monitor state;
- a copied Hook Contract schema in SRM;
- a GitHub remote for SRM;
- lifecycle/tool/batch/semantic/transport wiring beyond this micro-step.

## Goal

Add the smallest execution-substrate Hook foundation:

1. Newly written native SRM supervisor events receive a stable persisted Hook event
   identity at native-event append time.
2. A pure normalizer maps only three unambiguous native supervisor events:
   - shim-spawned -> process.spawned
   - terminal-evidence-seen -> process.terminal
   - recovered-attached -> execution.recovery
3. Output conforms to Hook Contract v1 and remains OBSERVE-only.
4. Legacy native events without persisted Hook identity remain readable as native
   evidence but fail normalization typed. Never synthesize a replacement identity
   from timestamp, source, sequence, PID or execution id.

## Native identity design

Hook Contract event identity is globally unique and is the duplicate identity when
no explicit dedupe_key is supplied.

SRM therefore persists a new `hookEventId` on every newly written
`ExecutionEvent`:
- exact format: `hk-[0-9a-f]{32}`;
- generated once when the native event is appended;
- rereading the native event returns exactly the same identity;
- normalizer reuses it unchanged as envelope.event_id.

`ExecutionEvent.hookEventId` remains optional in the TypeScript interface only
for backward readability of legacy events. New write paths MUST persist it.

The synchronous initial `dispatched` event and `EvidenceStore.appendEvent`
must both use the same identity generator so future native evidence is consistent,
even though this micro-step normalizes only three event types.

## Initial pure mappings

### shim-spawned
- event_type: process.spawned
- hook_class: OBSERVE
- phase: after
- domain: process
- action: spawned

### terminal-evidence-seen
- event_type: process.terminal
- hook_class: OBSERVE
- phase: terminal
- domain: process
- action: terminal

### recovered-attached
- event_type: execution.recovery
- hook_class: OBSERVE
- phase: after
- domain: execution
- action: recovery

All:
- schema_version: 1.0.0
- source: srm
- privacy_class: INTERNAL
- occurred_at derives only from persisted native event `t` and converts to
  RFC3339 UTC Z without changing the native timestamp
- execution_id may use exact native `execId` only if it satisfies Hook Contract
  bounds; invalid values fail typed
- no task/lane/work-order/claim/repo facts are inferred
- no sequence or dedupe_key is invented
- no PID, command, args, env, raw output, prompt, credential or arbitrary native
  fields are copied into the normalized envelope

Required caller context because it is deployment/runtime fact, not native task truth:
- source_version — SemVer, max 64
- device_id — Hook Contract device pattern/max
- host_os — windows | macos | linux

Optional future context is OUT OF SCOPE for this micro-step.

## Normalization failure model

Provide bounded typed failures at minimum for:
- missing/invalid legacy hookEventId;
- unsupported native event type;
- invalid/non-finite/out-of-range timestamp;
- invalid execution id for Hook Contract envelope;
- missing/invalid source_version/device_id/host_os;
- any schema-bound field overflow.

Normalization failure is observability degradation only:
`OBSERVABILITY_DEGRADED != EXECUTION FAILURE`.

Never mutate the native event or execution/task truth while normalizing.

## Execution-repo intended mutable scope

Preferred exact scope:
- src/sunday/supervisor-evidence.ts
- src/sunday/supervisor.ts
- NEW src/sunday/supervisor-hook-normalizer.ts
- test/test-sunday-supervisor.js only if required to prove persisted identities on existing supervisor paths
- NEW test/test-sunday-supervisor-hook-normalizer.js

No other production/test file may change without stopping as BLOCKED/SCOPE_CHANGE_REQUIRED.

## Authority-repo mutable scope

This Work Order only.
No A-Faster/A-FastTask/Hook Contract/control adapter/runtime source mutation.

## RED-first requirements

Before implementation prove failures for:
1. new appendEvent native event lacks Hook identity;
2. synchronous dispatched event lacks the same identity format;
3. normalizer module/mappings absent;
4. legacy event without hookEventId rejected typed once normalizer API exists;
5. unsupported native event fails typed;
6. no native payload leakage.

## GREEN acceptance

Execution repo:
- all new native events written by touched paths persist `hk-<32 lowercase hex>`;
- re-read preserves exact identity;
- three mappings exact;
- source/event inputs remain unmutated;
- malformed/legacy/unsupported inputs fail typed;
- no sequence/dedupe/task/claim/command/guard/adapter fields;
- no secret-bearing/arbitrary payload propagation;
- existing supervisor fault/recovery suite remains green;
- TypeScript build/typecheck green;
- exact scope, diff-check, UTF-8/U+FFFD and secret scans green.

Cross-repo:
- freeze exact A-Wiki authority candidate SHA and exact SRM candidate SHA;
- external integration validation MUST load
  A-Wiki `docs/contracts/hook-contract-v1.schema.json` at the accepted blob and
  validate representative output from all three mappings under Draft 2020-12;
- A-Wiki Hook Contract blobs must still equal the accepted 602f6db blobs;
- no production SRM dependency on A-Wiki filesystem or Python/jsonschema.

R3 acceptance:
- deterministic local verification;
- independent exact-SHA review;
- cross-repo exact-SHA compatibility proof;
- GPT-5.6 Sol acceptance;
- no self-accept by author model.

## Replay / continuity

Before any retry:
- recover execution pointer/PID/result/Git;
- RUNNING is never redispatched;
- TERMINAL_UNHARVESTED is harvested first;
- unknown side effects fail closed.

SRM has no configured remote at claim time. Candidate durability is therefore:
local Git commit + isolated worktree/branch + durable run evidence. Do not invent,
initialize or publish a remote. A later explicit repository/publication decision
may add remote-backed CI; this Work Order does not.
