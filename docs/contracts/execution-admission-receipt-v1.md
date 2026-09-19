# Execution Admission and Receipt Contract v1 (DEX cross-repo boundary)

Status: BINDING ARCHITECTURE CONTRACT (v1) / RUNTIME IMPLEMENTATION GATED BEHIND WO-P1-259 + WO-P1-260
ADR: `docs/adr/ADR-0002-dex-execution-admission-receipt-boundary.md`
Topology: CROSS_REPO — authority repo `A-Wiki-Conductor`, execution substrate repo `SunDayRemoteMCP`. Topology labels are defined once in `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md` and are projected here by reference only.
Future implementation work orders: `docs/work-orders/WO-P1-259-dex-2a-srm-physical-supervision.md`, `docs/work-orders/WO-P1-260-dex-2b-conductor-reconciliation-receipt.md`

The key words MUST, MUST NOT, SHOULD, and MAY are normative. This contract
defines the delegated-execution seam between the A-Sunday Conductor control
plane and the SunDayRemoteMCP (SRM) execution substrate. It creates no new
scheduler, task store, claim/lease store, retry engine, review/completion
authority, project SSoT, or secret store; it binds behavior into the existing
authorities named below.

## 0. Authority summary

- A-Sunday Conductor: admission decision, reconciliation, receipt, retry
  authorization, review, acceptance. Sole source of accepted task state.
- SRM: physical supervision (launch/observe/quiesce/collect) and immutable
  collection evidence. Never accepts/completes/retries tasks.
- A-FastTask: routing/binding only; no execution lifecycle authority.

## 1. Identity

Terms already owned elsewhere are reused, not redefined:

- `execution_id` — stable durable identity of one delegated execution,
  independent of chat/MCP/session IDs (REUSE:
  `docs/contracts/durable-execution-record.md`).
- Liveness classes (`RUNNING`, `TERMINAL_UNHARVESTED`, `STALLED`,
  `INTERRUPTED`, `UNKNOWN`, ...) and the replay-safety projection
  (`NOT_STARTED` / `PARTIAL` / `COMPLETE_UNVERIFIED` / `COMPLETE_VERIFIED` /
  `UNKNOWN`) are owned by `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`.

New terms owned by this contract:

- `attempt_id` — identity of exactly one physical dispatch of an execution onto
  the substrate. An `execution_id` MAY have multiple attempts; a retry (when
  authorized) is a new `attempt_id` under the same `execution_id`. Attempts are
  never merged or reused.
- **task/WO/lane/claim-generation refs** — the admission request MUST carry the
  task/work-order reference, lane binding tuple
  (`repo -> worktree -> branch -> HEAD -> task/claim -> scope`, defined in
  `TOOL_AND_FAST_PATH_ROUTING.md`), and the current claim generation of the
  owning claim. Admission against a superseded claim generation MUST be
  rejected (`STALE_GENERATION`).
- **binding digest** — an immutable digest computed at admission over the
  binding tuple: `execution_id`, `attempt_id`, task/WO/lane refs, claim
  generation, authority/execution repo SHA set, host+boot identity, and
  executable/attempt identity. Every later supervision, collection, and
  receipt record for the attempt MUST reference the same binding digest;
  mismatch is fatal evidence rejection.
- **exact authority/execution repo SHA set** — the WO-P1-251 compatibility set
  `{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}` pinned at admission.
  Collection receipts are only valid against this pinned set.
- **host + boot identity** — machine identity plus a boot epoch (e.g. boot
  timestamp/boot id). Process identity MUST NOT be compared across boot epochs;
  a boot-epoch change invalidates live process identity for prior attempts.
- **executable/attempt identity** — the launched executable path plus a content
  digest where computable, plus the bounded/redacted argv shape. Raw secret
  values MUST NOT appear.
- **OS process creation identity** — where observable: PID, process creation
  timestamp, and OS process key/handle if available. PID alone is never
  sufficient identity (PID-reuse defense, section 3).

## 2. Admission (A-Conductor decides; SRM executes)

- **Idempotency key.** Every admission request MUST carry a client-generated
  idempotency key derived from the binding tuple (not from wall-clock or
  session state).
- **Duplicate request behavior.** A request whose idempotency key matches an
  existing admission MUST return the original admission decision (or its
  current state projection) and MUST NOT spawn a second process.
- **Admission states.** An attempt is exactly one of `ACCEPTED`, `REJECTED`
  (with typed reason, at minimum `STALE_GENERATION`, `DUPLICATE_LIVE_ATTEMPT`,
  `SHA_SET_MISMATCH`, `QUOTA/PROVIDER`, `SCOPE`), or `AMBIGUOUS`.
- **LAUNCH_AMBIGUOUS.** If the admission response path can fail after the spawn
  decision point (shim crash, response loss), the attempt state MUST be
  representable as `LAUNCH_AMBIGUOUS`: admission accepted, spawn outcome
  unconfirmed. `LAUNCH_AMBIGUOUS` MUST be resolved only by physical
  reconciliation (process creation identity lookup + immutable evidence),
  never by assumption or timeout expiry.
- **Lost admission response.** A client that loses the admission response MUST
  re-query by idempotency key. It MUST NOT re-dispatch a new attempt.
- **Simultaneous dispatch fencing.** If two dispatches arrive for the same
  execution/binding, the first accepted admission wins; later ones MUST be
  fenced (`REJECTED: DUPLICATE_LIVE_ATTEMPT`) or attached to the live attempt
  as observers. Exactly one live physical attempt per binding MAY exist.
- **Stale-generation rejection.** Dispatch referencing a claim generation that
  the control plane has superseded MUST be rejected `STALE_GENERATION`, even if
  the process shape is otherwise valid.

## 3. Physical supervision (SRM side)

- **Per-execution shim/resource-guard boundary.** Each attempt MUST run under
  a per-execution shim or resource-guard boundary owned by SRM that captures
  creation identity and output evidence. Shared/global capture channels MUST
  NOT be the only evidence source.
- **Parent/child/descendant identity.** SRM MUST record the parent/child
  relation from the shim to the direct child and SHOULD capture descendant
  process identity (grandchildren) where the OS exposes it.
- **Descendant quiescence.** An attempt is not physically terminal until the
  child and observable descendants are exited or demonstrably detached
  orphans. Descendant quiescence MUST be verified before collecting a terminal
  result.
- **Exact PID/process identity.** Supervision decisions MUST use exact PID
  plus creation identity (creation time/process key) plus boot epoch — never
  name/pattern heuristics. PID reuse MUST be detectable: a PID re-observed
  with a different creation identity or boot epoch is a different process and
  MUST NOT be treated as the live child.
- **No broad kill.** Cancellation targets the exact supervised process tree by
  verified identity only. Broad process kill by name/pattern remains forbidden
  (repository-wide rule; see AGENTS.md).

## 4. Collection (SRM side; immutable evidence)

- **Repeatable immutable collect.** Collection MUST be repeatable and
  immutable: repeated collects of a terminal attempt return the same evidence
  (same digests); evidence is append-only and MUST NOT be rewritten.
- **Result/evidence digest.** Every collected artifact (result document,
  stdout/stderr spool, report refs) MUST carry a content digest; the result
  document binds the digests of everything it references.
- **Supervisor-observed vs executor-claimed facts.** Evidence MUST distinguish
  facts observed by the supervisor/shim (process creation/exit, timing,
  output capture) from claims asserted by the executor (task-level success
  statements). Executor-claimed facts are advisory (section 5).
- **Malformed/forged evidence rejection.** Strict decoders and schema
  expectations apply at every ingest boundary. Digest mismatch, schema
  violation, or identity mismatch (binding digest, attempt_id, SHA set) MUST
  cause rejection with a quarantine marker — never silent acceptance or
  repair-by-guessing.
- **Bounded/redacted output.** Collected output MUST be bounded and redacted
  per the output-backpressure rules (`docs/contracts/output-backpressure.md`);
  transport responses are summaries/tails, not unbounded streams.
- **Collection under drift grants no mutation.** If the execution worktree
  HEAD/dirty state drifted after dispatch, SRM MAY still collect old terminal
  evidence (advisory harvest). Drift MUST NOT grant any new mutation: the
  evidence is flagged as collected-under-drift and the control plane keeps new
  mutation fail-closed until re-pin.

## 5. Receipt (A-Conductor side)

- **Idempotent ingestion receipt.** Conductor ingestion of collected evidence
  MUST be idempotent, keyed by `(execution_id, attempt_id, result digest)` and
  the binding digest.
- **Receipt binds result digest + identity.** A receipt records the result
  digest, attempt/execution identity, claim generation, pinned SHA set, and
  the disposition decision. The receipt — not any substrate marker — is the
  only acceptance-grade record.
- **Repeated receipt safe.** Re-presenting already-receipted evidence MUST
  return the existing receipt without double-applying task effects.
- **Lost receipt response.** If the substrate loses the receipt response, it
  MAY redeliver; Conductor deduplicates. Lost receipt response never
  re-opens or duplicates the attempt.
- **TERMINAL_UNHARVESTED.** The liveness class defined in
  `EXECUTION_LIVENESS_PROTOCOL.md` applies at this seam as: terminal evidence
  exists at the substrate AND no matching Conductor receipt exists. This state
  MUST block conflicting redispatch/mutation until harvest/reconciliation.
- **SRM never decides accepted/completed task state.** Substrate status
  vocabulary is advisory collection state; accepted/completed is producible
  only by Conductor receipt plus existing review/acceptance authority.

## 6. Recovery / retry

- **Replay-safety first.** Before any retry, the prior attempt MUST be
  classified via the replay-safety projection (`NOT_STARTED` / `PARTIAL` /
  `COMPLETE_UNVERIFIED` / `COMPLETE_VERIFIED` / `UNKNOWN`) from
  supervisor-observed facts plus durable records — never from chat memory.
- **Outcome-known != retry-authorized.** A terminal outcome of attempt N never
  authorizes attempt N+1 by itself; retry authority lives in Conductor
  reconciliation under the current claim generation.
- **Stale claim/session while child lives.** If the claiming session/lease
  looks stale but the child process is alive under valid identity, ownership
  MUST NOT be released; the lease is preserved until verified terminal state
  plus descendant quiescence, controlled handoff, or explicit authorized
  cancellation.
- **Reboot persistence boundaries.** Durable records (admission, evidence,
  receipts) survive reboot; live process identity does not. After a boot
  epoch change, prior live-process observations are void and the attempt MUST
  be reclassified from durable evidence (typically `UNKNOWN` or terminal per
  evidence) before any action.
- **No blind replay.** No response loss, timeout, session loss, or
  transport failure is replay authority. `UNKNOWN` fails closed.

## 7. Security

- **Strict decoders/schema.** Every boundary (admission, supervision,
  collection, receipt) uses strict typed decoders; unknown fields fail closed
  unless explicitly versioned forward-compatible.
- **Allowlisted credential references only.** Evidence and dispatch records
  reference credentials by allowlisted handle; raw tokens/keys are forbidden.
- **No raw secret argv/env.** Durable evidence MUST NOT contain raw
  secret-bearing argv or environment values; only bounded, redacted command
  shape (ADR-0002 rule 9).
- **Trusted-local-process MVP.** V1 assumes a trusted local executor/shim and
  a non-hostile local environment. Hostile-local-executor hardening is a
  future explicit threat-model decision and MUST NOT be claimed as a v1
  property.

## 8. Conformance and fault gates

Deterministic expected invariants for this seam are catalogued in
`docs/contracts/fault-injection.md` (DEX boundary scenarios). WO-P1-259 and
WO-P1-260 are not acceptable until their fake/fault suites cover those
scenarios deterministically. A future notification-ack boundary (DEX-3a) is
explicitly out of scope for v1 receipts.
