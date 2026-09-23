# WO-P1-507 — SundayMCP async receipt + multi-device contract gate

Status: P0 DOCS ACTIVE / R3 / CROSS_REPO
Parent: Issue #495
Issue: #507
Authority repository: `A:\GitHub\A-Wiki-Conductor`
Authority base at claim: `19ee92ca3888ce563ac743cfcca7707334cc8189`
Execution substrate (READ-ONLY in P0): `A:\GitHub\SunDayRemoteMCP`
Observed local execution SHA: `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`
Execution remote: `REMOTE_UNVERIFIED` (no configured Git remote; expected GitHub repository name did not resolve)
A-Wiki worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo507-sundaymcp-p0`
Branch: `docs/wo-p1-507-sundaymcp-async-contract`

## 1. Purpose

Freeze the smallest implementation-ready interface and failure contract needed
to make long SundayMCP work return a durable receipt quickly, survive
ChatGPT/MCP/session/transport loss without blind replay, and later route through
one logical SundayMCP endpoint to multiple devices.

This P0 is contract-only. It changes no SunDayRemoteMCP source, transport,
device registration, Worker plugin, Serena backend, task scheduler, claim store,
review authority, acceptance authority, or completion authority.

## 2. Authority boundary

A-Sunday Conductor remains the control-plane authority for:

- task / Work Order identity;
- claim and mutable-scope ownership;
- global WIP;
- risk and review requirements;
- exact repo/worktree/branch/HEAD binding;
- dispatch admission;
- replay authorization;
- review / acceptance / merge / completion;
- roadmap / NEXT_READY / goal closeout.

SunDayRemoteMCP remains execution substrate only. It may own durable execution
identity, local execution evidence, ephemeral process/path locks, status,
output, cancellation mechanics, recovery, and immutable evidence collection.
Those observations never become Conductor task/claim/review/completion
authority.

A device registry is observational routing state only. A device being online,
present, recently heartbeating, or matching a device ID never proves task
ownership, mutation authority, execution completion, or safe replay.

## 3. Source truth pinned for P0

### 3.1 Existing Sunday durable execution contract

At local SunDayRemoteMCP `2f033cf...` the runtime already exposes:

- `sunday_dispatch`
- `sunday_status`
- `sunday_output`
- `sunday_cancel`
- `sunday_harvest`
- `sunday_recover`
- `sunday_collect`

Observed behavior that P1 must preserve:

1. `dispatch()` validates the request, requires scopes for mutation, creates a
   durable manifest/evidence directory, and returns `DispatchReceipt {execId,
   evidenceDir}`.
2. The dispatch contract states the manifest is durably on disk before the
   foreground call returns; the child launches asynchronously.
3. Optional DEX binding already carries authority/execution repo names + exact
   SHAs, execution ID, attempt ID, canonical path/digest, and binding digest.
4. Reusing an authority-owned execution ID with existing evidence is rejected;
   callers must status/recover the existing execution rather than redispatch.
5. `status` and `output` are bounded observation calls.
6. `cancel` acts on one exact durable execution identity.
7. `recover` reconstructs truth from disk, reattaches still-running execution
   locks, and never replays work.
8. launch ambiguity is observation/reconciliation only; the substrate does not
   respawn an ambiguous execution.
9. `collect` is immutable terminal evidence collection. It is explicitly not a
   receipt and not acceptance; evidence drift is reported/quarantined rather
   than rewritten.
10. mutation admission checks active unattached durable executions and fails
    closed on overlapping scope.

These are reuse seams, not reasons to add a second execution database.

### 3.2 Multi-device gap

The existing Sunday durable request/receipt/binding does not carry
`device_id` or `connection_generation`.

The separate remote-device transport has a device ID for presence/routing, but
P0 found no durable connection-generation authority joined to Sunday execution
identity. The semantic-engine generation counter is unrelated and MUST NOT be
reused for device connection identity.

Therefore multi-device execution is not admitted until P1/P2 introduce an
explicit device/session binding.

### 3.3 Repository identity caveat

The canonical execution-substrate path is supplied by project authority as
`A:\GitHub\SunDayRemoteMCP`, and its local exact HEAD is pinned above.
However no Git remote is configured and the attempted GitHub repository lookup
did not resolve. P0 therefore records `REMOTE_UNVERIFIED`.

This blocks any SunDayRemoteMCP source mutation/release claim from this P0. It
does not block documenting the compatibility contract against the exact local
tree.

## 4. P0 terminology

### Execution identity

`execution_id` is the durable Sunday execution identity. When Conductor
supplies DEX admission identity, that exact identity is reused; transport loss
does not mint a replacement.

### Attempt identity

`attempt_id` identifies the admitted attempt inside the Conductor execution
contract. One consequential attempt MUST NOT be silently mapped to two Sunday
executions.

### Device identity

`device_id` is a stable logical device identifier used only to choose/verify
the intended execution device.

### Connection generation

`connection_generation` is a monotonically changing opaque identifier for one
device's currently admitted connection epoch. It distinguishes a current
connection from a stale/late connection using the same `device_id`.

It is transport/session evidence only. It is not a task generation, retry
number, Worker generation, semantic-engine generation, claim version, or
completion generation.

### Executor context is not authority

Serena / Worker `Active Project` is executor-local, session-bound,
transitional context only. It MUST NOT identify or grant task, lane, owner,
claim, mutation, merge, completion, recovery, or replay authority.

Every material request/dispatch MUST carry or resolve from durable authority an
explicit lane binding sufficient to prove the intended execution target:

- `authority_repo` and `execution_repo`;
- canonical repository/worktree identity;
- branch and expected HEAD;
- task / Work Order identity;
- claim / lease and generation when applicable;
- mutable scope and mutation intent;
- `execution_id + attempt_id`;
- `device_id + connection_generation` for remote/device-routed execution.

A matching `Active Project` is at most corroborating evidence. It never
substitutes for that explicit binding.

Before any consequential mutation or process launch through a Serena-compatible
adapter, the observed executor context MUST be checked against the explicit
lane binding. Mismatch, stale context, or unknown context fails closed before
side effect with a typed context-drift outcome. The adapter MUST NOT silently
mutate whichever project happens to be active in that session.

### Correlation identity

Every remote request/result path MUST be correlatable across:

```text
Conductor Work Order / claim
  -> Conductor execution_id + attempt_id
  -> Sunday durable execId
  -> device_id + connection_generation
  -> router request correlation_id
  -> device-agent delivery
  -> local executor evidence
  -> result / recover / collect
```

No hop may replace the authority IDs with a UI/session-specific ID.

## 5. Dispatch receipt contract

P1 must project the existing durable dispatch into a fast receipt shape without
creating another scheduler.

Minimum receipt fields:

```text
receipt_version
execution_id
attempt_id
sunday_exec_id
device_id
connection_generation
evidence_ref
durability = MANIFEST_DURABLE
accepted_at
```

Rules:

1. Receipt is returned only after the Sunday durable manifest/binding exists.
2. Receipt means **durably admitted to the execution substrate**. It does NOT
   mean child started, work succeeded, executor claim is true, review passed,
   or Conductor accepted completion.
3. Consequential mutation must have Conductor authority binding and explicit
   `device_id + connection_generation` before remote delivery.
4. Read-only work may use the same receipt shape so recovery is uniform.
5. Receipt serialization must contain no secret, bearer token, private command
   output, or raw credential material.
6. Foreground callers should return after durable receipt rather than hold one
   MCP request open for the work duration.
7. P1 target: the foreground path performs only bounded admission/durable write
   and dispatch handoff; it MUST NOT wait for terminal execution. Latency is
   measured and gated in tests rather than achieved by a second async queue.

## 6. Status / output / collect / recover contract

### status

Returns bounded current evidence for an exact `sunday_exec_id`. Status is an
observation and may be non-terminal.

### output

Returns bounded output tail only. Output text is never completion authority.

### harvest

Separates terminal verified process/exit evidence from executor claims. A
worker/model saying DONE cannot replace verified terminal evidence.

### collect

Returns immutable digested evidence for a terminal execution. Repeat collect
returns the same accepted record or reports drift/quarantine. Collect does not
accept the Work Order.

### recover

Reconstructs durable execution truth after new ChatGPT session, MCP reconnect,
router reconnect, supervisor restart, or device reconnect. Recover MUST NOT
redispatch.

### cancel

Targets one exact durable execution. Cancellation request or timeout does not
manufacture a terminal outcome when exact process/result truth is unavailable.

## 7. Outcome and replay model

The Conductor-facing projection must distinguish at least:

- `RECEIPT_DURABLE` — durable manifest/receipt exists; execution may not yet be
  proven running.
- `RUNNING` — live execution evidence exists.
- `TERMINAL_VERIFIED` — terminal substrate evidence exists.
- `FAILED_BEFORE_DURABLE_RECEIPT` — no durable execution identity/evidence was
  created.
- `OUTCOME_UNKNOWN` — an execution may have been admitted/launched but current
  evidence cannot safely prove terminal or replay-safe state.
- `QUARANTINED` — evidence/binding drift or malformed evidence blocks normal
  continuation.

These are transport/execution facts. Conductor still maps them into task/job
state under existing authority.

### Replay matrix

| Situation | Consequential mutation | Read-only execution |
| --- | --- | --- |
| Failure proven before durable receipt | New admitted dispatch may be allowed | Bounded retry may be allowed |
| Durable receipt known | Never mint a replacement attempt solely because foreground transport failed | Recover/status original execution first |
| Response lost after possible admission | `OUTCOME_UNKNOWN`; reconcile original identity | Reconcile original identity before replay unless the read contract explicitly proves idempotent duplicate safety |
| Running/unattached evidence | Attach/recover; no replay | Attach/recover |
| Terminal verified, not collected | Harvest/collect same exec | Harvest/collect same exec |
| Collect drift/quarantine | Stop and escalate | Stop and escalate |
| Cancel outcome ambiguous | `OUTCOME_UNKNOWN`; exact reconciliation | Reconcile before retry |

No transport/UI/session failure releases claim, WIP, lease, path lock, or device
binding.

## 8. Duplicate identity rules

For an authority-supplied `execution_id + attempt_id`:

- same identity + same canonical binding/payload digest:
  return/recover the existing execution/receipt; do not spawn another writer;
- same identity + conflicting binding/payload:
  fail closed with a typed conflict;
- new identity while an overlapping consequential execution remains active or
  unattached:
  fail closed under existing scope/claim/lease rules;
- missing/ambiguous durable evidence after possible launch:
  `OUTCOME_UNKNOWN`, never "not started" by assumption.

P1 should reuse existing Sunday evidence directories and DEX binding rather than
add a receipt database.

## 9. Device / connection-generation rules

A remote consequential dispatch is admitted only when:

1. Conductor admission is valid for the exact Work Order/claim/scope;
2. `device_id` is explicit;
3. `connection_generation` is explicit and matches the router's current
   admitted generation for that device;
4. the result/ack carries the same `device_id + connection_generation +
   correlation_id + sunday_exec_id`;
5. late data from an older generation cannot mutate current execution state.

Required behavior:

- stale generation before delivery -> reject/no local spawn;
- reconnect increments/replaces connection generation;
- late response from old generation -> observational late-result evidence only,
  never attached to the newer generation;
- router restart without generation truth -> fail closed/reconcile;
- duplicate delivery for the same durable exec -> recover/attach existing exec,
  never duplicate consequential mutation;
- device presence/heartbeat alone -> insufficient for admission.

The device registry may answer "where can this be routed?" It cannot answer
"may this task mutate?" or "is this work complete?".

## 10. Native MCP Tasks mapping

Native MCP Tasks, when supported, is an optional transport adapter only.

Capability negotiation may map:

- task creation -> Sunday durable dispatch/receipt;
- task status -> Sunday status;
- task result/output -> bounded output/harvest/collect;
- task cancellation -> exact Sunday cancel.

It MUST NOT create a second task scheduler, retry engine, claim store, WIP
authority, review state, or completion authority. If Tasks is unsupported, the
baseline `sunday_dispatch/status/output/cancel/harvest/recover/collect`
contract remains sufficient.

## 11. #333 / PR #335 disposition

Issue #333 / PR #335 (WO248) is prototype evidence, not the production remote
execution substrate.

Reusable evidence/ideas:

- HMAC-authenticated request concepts;
- replay-protection tests;
- bounded request identity;
- mutation serialization/concurrency tests;
- exact process/transport safety lessons;
- protocol/failure-test patterns that can be re-expressed against SRM.

Do NOT:

- merge its Python `sunday_remote_bridge.py` / `sunday_runtime.py` as a
  second production remote runtime beside SunDayRemoteMCP;
- make it a scheduler/task/claim/review/completion authority;
- copy its runtime state into a new parallel execution database.

Any useful tests are to be ported/adapted to the accepted SRM interface, not
used to establish competing runtime authority.

## 12. Crash / disconnect failure matrix required before P1 acceptance

P1 implementation tests must deterministically cover:

1. crash before durable manifest -> no receipt, replay may be admitted;
2. durable manifest written, foreground response lost -> recover same exec;
3. shim/launch initiated but child identity absent -> launch ambiguous /
   `OUTCOME_UNKNOWN`, no respawn;
4. child running, ChatGPT/MCP connection drops -> recover/attach;
5. child terminal, response delivery lost -> status/harvest/collect same exec;
6. supervisor restart while execution runs -> recover from disk and restore
   local path-lock protection;
7. duplicate same-identity/same-binding dispatch -> no duplicate child;
8. duplicate same-identity/conflicting-binding dispatch -> typed conflict;
9. overlapping mutation from another session/worktree -> fail closed;
10. stale `connection_generation` delivery -> reject before local spawn;
11. reconnect then old-generation late result -> never attach to current
    generation;
12. router loses generation truth -> no consequential delivery;
13. cancel with unverifiable process identity -> outcome unknown/manual
    reconciliation, not fabricated cancellation;
14. collect drift/malformed evidence -> quarantine, no acceptance;
15. remote transport loss never releases Conductor claim/WIP/lease;
16. result/claim saying DONE without deterministic evidence -> no completion.

## 13. P1 implementation scope hypothesis

P1 is still separately gated. No source mutation is authorized by this P0.

Expected SunDayRemoteMCP source focus, to be re-pinned against its canonical
repository identity before mutation:

- `src/sunday/mcp-runtime-tools.ts` — receipt/status tool projection only;
- `src/sunday/supervisor.ts` — expose/reuse durable receipt/recovery truth, not
  new scheduling;
- a narrow existing/new Sunday transport-binding type near `src/sunday/**` for
  `device_id + connection_generation + correlation_id`;
- remote-device/router boundary only where needed to validate generation and
  route an already-admitted Sunday execution;
- focused tests for durable receipt latency, response loss, replay,
  connection-generation and late-response behavior.

Exact mutation paths MUST be frozen by the P1 claim after canonical
SunDayRemoteMCP repository identity is resolved. This list is a hypothesis, not
mutation authority.

## 14. P2 and later direction

After P1 proves local durable receipt compatibility:

- P2: one logical SundayMCP endpoint -> device router -> Windows/macOS device
  agents, generation-bound and fail-closed;
- P3: continue #215 NEXT_READY production path using durable execution identity;
- P4: compose #226 A-Goal/GoalCloseout from existing graph/job/SRM evidence;
- P5: continue #457 Browser Wake from its reviewed existing core;
- P6: #341 native semantic parity;
- P7: retire Worker 1..5 as primary ChatGPT-facing transport separately from
  any later Serena backend retirement.

## 15. P0 verification / acceptance

Before P0 can close:

- [x] A-Wiki authority repo exact main pinned at claim.
- [x] SunDayRemoteMCP canonical local path and exact local HEAD pinned.
- [x] remote identity caveat recorded as `REMOTE_UNVERIFIED`.
- [x] existing durable receipt/status/output/cancel/harvest/recover/collect
  semantics sourced from local SRM code.
- [x] `device_id + connection_generation` gap proved from source.
- [x] #333/PR335 disposition explicitly frozen.
- [x] replay / outcome-unknown / duplicate / crash-window contract frozen.
- [x] P1 source scope hypothesis identified but not authorized.
- [x] no SRM source mutation.
- [x] exact-scope docs check / secret scan.
- [ ] freeze exact A-Wiki SHA.
- [ ] independent R3 exact-SHA review.
- [ ] hosted CI / post-main closeout if repository policy requires it.

## 16. Stop / release rule

P0 completion releases only this docs claim. It does not authorize P1 source
mutation until:

1. independent R3 review accepts this exact contract;
2. canonical SunDayRemoteMCP repository identity/remote is resolved or the
   authority explicitly accepts local-SHA-only mutation binding;
3. fresh CROSS_REPO mutation gate binds exact authority + execution SHA pair;
4. global WIP and hotspot ownership are re-recovered.
