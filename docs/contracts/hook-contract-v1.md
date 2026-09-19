# Hook Contract v1 (HOOK-0)

Status: CONTRACT-ONLY FREEZE CANDIDATE — WO-P1-258 / Issue #368
Contract version: 1.0.0
Planning authority: `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md` (P1)
Machine schema: `docs/contracts/hook-contract-v1.schema.json`

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as
described in RFC 2119/8174.

## 1. Purpose and authority

Hook Contract v1 is the versioned normalized event envelope shared across
A-Sunday Conductor control-plane surfaces, SunDayRemoteMCP execution hooks,
and Claude Code / Kilo / RDC harness adapters, per the accepted WO-P1-257
roadmap.

Non-negotiable boundaries (inherited from the roadmap and WO-P1-258):

- A-Sunday Conductor is the sole task/claim/routing/retry/review/acceptance/
  command authority.
- A-FastTask/A-Faster are router/binder/profile only.
- SRM is execution/capability substrate only.
- The Hook Bus, STM, and Monitor are never SSoT. Actual Git/GitHub/runtime/
  durable evidence always outranks hook/STM projections.
- The first monitor milestone is read-only.
- Git pre/post-commit hooks are never orchestration authority.

This document defines the envelope, identity, ordering, class, versioning,
bounds, privacy, transport-adjacent, and capability-discovery rules. It does
not implement any runtime. Validation in production runtime is deferred to
HOOK-1 and later Work Orders that extend existing event seams.

## 2. Reuse classification

- REUSE: `src/a_conductor/control_events.py` event-id format precedent
  (`event-<uuid4hex>`) and typed `EVENT_*` error-code style; existing
  Draft 2020-12 schema conventions under `schemas/`.
- WRAP: adapters map native harness/substrate events into this envelope
  without changing task semantics.
- EXTEND: HOOK-1/HOOK-2 emit normalized events by extending existing
  control/lifecycle seams, not by adding a parallel event store.
- REPLACE/NEW: none.

## 3. Envelope

One hook event is one JSON object (the "envelope"). The required core is
small; all other fields are bounded optional context groups.

### 3.1 Required core

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | MUST match `^1\.\d+\.\d+$` (v1 line). |
| `event_id` | string | MUST match `^hk-[0-9a-f]{32}$`. Producers MUST generate it as UUIDv4 hex — a generation-only requirement (§4); consumers enforce the format only. Globally unique within the normalized event domain. |
| `event_type` | string | MUST match `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,2}$`, max 96 chars. MUST equal `domain` + `"."` + `action` optionally followed by one more `.segment` for phase-qualified types. |
| `hook_class` | enum | `OBSERVE` \| `ADVISORY` \| `GUARD` \| `COMMAND`. |
| `phase` | enum | `before` \| `after` \| `within` \| `terminal`. |
| `domain` | enum | `control` \| `execution` \| `process` \| `tool` \| `workspace` \| `batch` \| `semantic` \| `transport` \| `device` \| `advisory` \| `security`. |
| `action` | string | MUST match `^[a-z][a-z0-9_]{0,31}$`. |
| `occurred_at` | string | RFC 3339 UTC only: `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,9})?Z$`. Offsets are forbidden. |
| `source` | enum | `a-conductor` \| `srm` \| `claude-code` \| `kilo` \| `rdc`. |
| `source_version` | string | SemVer `^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$`, max 64 chars. |
| `device_id` | string | `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`. |
| `host_os` | enum | `windows` \| `macos` \| `linux`. |
| `privacy_class` | enum | `PUBLIC` \| `INTERNAL` \| `SENSITIVE`. `SECRET` is forbidden: secret-bearing envelopes are security-invalid (§10). |

### 3.2 Optional context groups

All optional fields are bounded (schema-enforced). Omitted means unknown, not
absent-of-fact; consumers MUST render unknown/omitted as `unknown`, never as
derived truth.

- Lane/task: `lane_id`, `task_id`, `work_order`, `task_topology`
  (`CONTROL_PLANE_ONLY` \| `EXECUTION_SUBSTRATE_ONLY` \| `CROSS_REPO` \|
  `UNBOUND`), `authority_repo`, `execution_repo`.
- Repository: `repo`, `worktree`, `branch`, `head_sha` (`^[0-9a-f]{7,64}$`),
  `claim_ref`.
- Execution: `execution_id`, `harness_id`, `model_id`, `effort`, `state`
  (`^[A-Z][A-Z0-9_]{1,31}$`, e.g. `RUNNING`/`BLOCKED`/`DONE`),
  `duration_ms` (integer ≥ 0), `blocker_code` (`^[A-Z][A-Z0-9_]{1,63}$`).
- Ordering/dedupe: `sequence` (§5), `dedupe_key` (§4).
- Correlation: `correlation_id`, `causation_id` (§6).
- Evidence: `evidence_refs` (max 16 unique pointer strings), `evidence_digest`
  (`^[0-9a-f]{16,128}$`) (§12).
- Presentation: `summary` (max 512 chars, sanitized free text; MUST NOT
  contain corpus items from §11).
- Class payloads: `guard` (§8.3, GUARD events only), `command_request`
  (§8.4, COMMAND events only), `adapter` (§14, OBSERVE capability-discovery
  events only) — the schema forbids each on every other hook class.

Unknown-field policy: the 1.0.0 schema is closed (`additionalProperties`
false everywhere). Consumer forward-compatibility rules are in §7.2 and
the normative reference consumer ingest algorithm is §7.4.

## 4. Event identity

- `event_id` MUST be globally unique within the normalized event domain.
  v1 reserves the `hk-` prefix; producers MUST generate `hk-<uuid4hex>`.
  UUIDv4 is producer-generation-only: the published schema and consumers
  enforce the `hk-[0-9a-f]{32}` format and the uniqueness discipline, but
  they MUST NOT reject a same-major envelope solely because the hex is not
  UUIDv4-shaped. Tightening the schema pattern to enforce UUIDv4
  version/variant nibbles would retroactively invalidate envelopes valid
  under the published 1.x schema — a semantic change requiring a major
  bump, not a 1.x repair.
- Every emission (including retries by the adapter or transport) MUST reuse
  the same `event_id` for the same semantic event.
- Delivery is at-least-once where durable delivery is used; there is NO
  exactly-once promise. Consumers MUST be idempotent.
- The bounded replay window is consumer/Monitor deployment configuration:
  its default (1800 s) and clamp bounds (300 s–86400 s) are chosen and
  enforced solely by the consuming deployment, and no envelope field can select, extend, or widen it.
  v1 defines no such envelope field; producer-side window hints are
  non-conforming.
- Consumers MUST dedupe on explicit duplicate identity inside a bounded
  replay window: default 1800 s, configurable, clamp 300 s–86400 s. The
  duplicate identity is the explicit `dedupe_key` when a producer
  deliberately supplies one, otherwise the globally unique `event_id`;
  `source` + `sequence` MUST NOT be used as a fallback duplicate identity
  (`sequence` is a per-stream ordering hint, §5, and may legitimately
  restart with a new observed transport/adapter session or coincide across
  devices). Distinct `event_id`s MUST NOT be dropped as duplicates merely
  because their `source` and `sequence` match. Redelivery carrying an
  already-seen `event_id`, or an already-seen deliberate `dedupe_key`
  inside the window, MUST be dropped as a duplicate; beyond the window,
  idempotent consumer design absorbs residual risk; no global dedupe table
  is implied.

## 5. Ordering

- Ordering stream domain: an ordered stream is identified by the observed
  triple `(source, device_id, transport/adapter session context)` — never
  by bare `source`. The session context is the transport/adapter session
  or reconnect boundary the consumer actually observed; it is not an
  envelope field, and no project-wide epoch or sequence store is created.
  The projection maintains one ordered queue per observed stream. When
  the producer provides `sequence` (a monotonically increasing
  non-negative integer within one observed stream), `sequence` is
  authoritative for order within that stream: the queue orders that
  stream's buffered events carrying `sequence` by `sequence`, and
  consumers MUST NOT reorder a stream's events against their `sequence`.
  A new observed session may restart `sequence` without colliding with a
  prior session's queue.
- When `sequence` is absent for a stream, the queue preserves observed
  producer arrival order for that stream within the transport session and
  MUST NOT claim stronger ordering than it observed.
- Sequence constrains ordering only among the currently buffered/known
  events of a stream. The projection MUST NOT wait for, invent, or
  synthesize unseen events to fill gaps, and MUST NOT demote, splice, or
  reorder observed items because a gap or a missing `sequence` exists.
  In a mixed queue, events without `sequence` keep their observed arrival
  slots and the events carrying `sequence` fill the remaining slots in
  `sequence` order; no-sequence events are never assigned a synthesized
  or sentinel `sequence` value. Gaps and unknown ordering are surfaced as
  stale/unknown/gap metadata in the projection only where later Monitor
  work supports it; no new durable state store is added for gap tracking.
- Emitted history is append-only. Once a projection has emitted a
  stream's events, that history is never retroactively reordered,
  spliced, or rewritten. A later-arriving event whose `sequence` is lower
  than (or a reuse of) sequence values already emitted in that stream is
  never inserted before already-emitted history: it appends at its
  observed arrival position — joining the not-yet-emitted buffer, where
  the buffered-ordering rules above apply — and the projection surfaces
  sequence inversion (and gap/unknown, where metadata is supported)
  instead of rewriting history or inventing missing events.
- Consumers MUST NOT infer any global total order from `occurred_at` wall
  clock values. Cross-device clock skew is assumed. In the merge,
  `occurred_at` is observed presentation metadata only and carries no
  causal or global-order claim.
- Deterministic monitor merge: when interleaving streams, the projection
  is a stable k-way merge across the per-stream ordered queues. Only the
  current head of each stream queue is eligible at each step. Among
  eligible heads, the deterministic cross-stream ranking key is
  `(occurred_at_instant, source, event_id)`, where `occurred_at_instant`
  is the head's `occurred_at` value parsed as an RFC 3339 UTC instant.
  Raw string comparison of `occurred_at` is forbidden: fractional seconds
  can invert string order (an event at `…T07:00:20.5Z` ranks before
  `…T07:00:20Z` as a raw string but is the later instant); the head's
  `sequence` MAY be carried as redundant metadata. Instant parsing
  changes presentation/interleave ordering only — never causal truth
  (the wall-clock-skew rule above still applies). This key selects only
  among heads of different stream queues and MUST NOT reorder items
  within one stream queue, so a timestamp-first global sort of all
  events is non-conforming even when labeled as observed interleaving.
  The merged result MUST be labeled as observed interleaving, not causal
  order.
- `correlation_id`/`causation_id` are links, not time order. A causation
  chain MUST NOT be used to reorder events; it only connects related
  envelopes (§6).

## 6. Correlation and causation

- `correlation_id` (`^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`) groups related
  events (one interaction/operation family).
- `causation_id` MUST be the exact `event_id` (`hk-<uuid4hex>`) of the prior
  normalized event that caused this one.
- Both are identifier-only: carrying objects, payloads, or embedded content
  in these fields is invalid.

## 7. Versioning and compatibility

### 7.1 Producer rules

- Producers MUST pin an exact `schema_version` they conform to.
- Additive optional fields require a minor bump; core (required) changes,
  removals, or semantic changes require a major bump.

### 7.2 Consumer rules (compatibility matrix)

| Producer declares | Consumer knows | Behavior |
|---|---|---|
| same major, minor ≤ consumer | any minor | strict validation against this schema family. |
| same major, producer minor > consumer known minor | older minor | validate core; MUST ignore unrecognized optional fields (forward-compatible) via the §7.4 reference ingest algorithm — raw security scan first, then unknown-optional projection, then strict known-schema validation; never reject solely for new optional fields. |
| different major | — | typed reject `HOOK_VERSION_UNSUPPORTED`; no silent fallback. |
| unparseable / schema-invalid | — | typed reject `HOOK_EVENT_INVALID`; drop; monitor MUST NOT crash. |
| over size bounds (§9) | — | typed reject `HOOK_EVENT_OVERSIZED`. |

### 7.3 Degrade behavior

- Validation/transport failures degrade observability only
  (`OBSERVABILITY_DEGRADED` / `HOOK_STREAM_DEGRADED`); they MUST NOT rewrite
  task truth and MUST NOT block otherwise-safe execution unless an accepted
  GUARD hook declares otherwise (§8.3).
- Transport failure is not execution failure.

### 7.4 Reference consumer ingest algorithm (normative)

A conforming v1 consumer ingests an incoming envelope through the following
ordered steps. Earlier steps always decide before later steps run, and no
later step may relax an earlier decision. The published schema stays closed
(`additionalProperties: false`): forward compatibility is consumer ingest
behavior defined here, not a loosening of the schema.

1. Whole-envelope byte bound (BEFORE any parsing or semantic
   normalization): hook validation operates on the exact serialized
   envelope bytes that cross the Hook Bus ingestion seam. Measure the
   exact incoming UTF-8 serialized envelope bytes at the consumer
   transport boundary; if the size exceeds the §9 MUST cap (65536
   bytes), reject `HOOK_EVENT_OVERSIZED`. Every conforming producer,
   including a structured in-process adapter, MUST supply or expose
   those exact serialized bytes to the validator before parsed-object
   validation, and the identical cap is applied to those bytes before
   normalization. An object-only call with no defined emission
   serialization is not sufficient evidence for the byte cap and MUST
   NOT be accepted as a production conformance path. A test/reference
   helper may use one explicitly named deterministic serialization only
   as a conformance fixture, never as a substitute for the producer's
   actual emitted bytes. Measurement MUST NOT under-measure: counting
   characters instead of UTF-8 bytes, or re-serializing an
   already-parsed object (key-sorted or canonical JSON), MUST NOT be
   used as a substitute measurement of the incoming bytes as
   received/emitted.
2. Parse fail-closed, duplicate-aware: decode UTF-8 and parse JSON with
   duplicate object member detection at every object depth. Unparseable
   or non-UTF-8 input, a parsed envelope that is not a JSON object, or
   any duplicate object member name at any nesting depth — including
   inside nested objects and inside objects within arrays — rejects
   `HOOK_EVENT_INVALID`. Duplicate-key rejection is parser input
   validation, not a schema field: it applies identically in strict and
   forward-compat modes, before forward projection (step 6) and before
   parsed-envelope security interpretation can lose information, because
   a first-wins or last-wins parser can silently discard an earlier
   member — an earlier forbidden nested field before the step 3
   security scan, or an earlier `guard` `failure_policy` value.
   Consumers MUST NOT silently choose first-wins or last-wins.
3. Raw security scan (before ANY unknown-field handling): recursively walk
   the fully parsed raw envelope — every object at every nesting depth,
   including objects inside arrays and inside unknown fields. If any
   object key is a §10 forbidden field name (`prompt`, `messages`,
   `transcript`, `token`, `api_key`, `apikey`, `secret`, `secret_value`,
   `password`, `credential_value`, `cookie`, `share_url`, `session_url`,
   `argv`, `command_line`, `shell_command`), or any string value anywhere
   contains a §11 fake-secret-corpus item, the envelope is
   security-invalid: reject `HOOK_EVENT_INVALID` and flag it. This scan
   runs on the RAW envelope precisely so that unknown-field filtering
   (step 6) can never hide a future-named `token`, `cookie`, `password`,
   argv/env/command-line carrier, raw prompt/session/share URL, or any
   other §10 forbidden field before the security-invalid decision.
4. Version gate: read `schema_version`. A well-formed
   `<major>.<minor>.<patch>` whose major differs from the consumer's
   major (v1 consumers: major 1) rejects `HOOK_VERSION_UNSUPPORTED`; no
   silent fallback. A malformed version string falls through to strict
   validation and rejects `HOOK_EVENT_INVALID`.
5. Mode select: same major with producer minor ≤ the consumer's known
   minor is strict mode — validate the whole envelope directly against
   the consumer's known closed schema; unknown fields are NOT ignored in
   this mode and any unknown field rejects `HOOK_EVENT_INVALID`. Same
   major with producer minor > the consumer's known minor is forward
   mode (steps 6–8).
6. Forward-mode projection: recursively filter ONLY additive unknown
   OPTIONAL fields/subfields. Top-level fields absent from the
   consumer's known schema properties are dropped; unknown subfields
   inside known optional objects (`guard`, `command_request`,
   `adapter`) are dropped the same way. All known fields — required core
   and known optionals — are preserved verbatim with their known nested
   required fields and constraints intact. Known fields are
   never filtered and class-condition semantics (GUARD requires `guard`;
   `guard` is forbidden on every other class; COMMAND requires
   `command_request`; `command_request` is forbidden on every other
   class; `adapter` only on the `transport.adapter_capabilities` OBSERVE
   event) are enforced on the projection exactly as in strict mode:
   projection never makes an invalid envelope valid.
7. Strict validation of the projection: the projected envelope MUST
   validate against the consumer's known closed schema (required core,
   enums, patterns, bounds, class conditionals). Unknown
   required/core/enum semantics are NOT forward-compatible additions
   (§7.1): a producer needing them MUST major-bump. Where such a
   violation is detectable on the projected envelope (a known core enum
   carrying an unknown value, a known required field missing or
   violating its constraint), the consumer rejects
   `HOOK_EVENT_INVALID`.
8. Semantic validators: run the consumer's semantic checks (at minimum
   `event_type` = `domain` + `"."` + `action` with an optional
   `.segment`, §3.1) on the projected envelope and reject
   `HOOK_EVENT_INVALID` on failure.

Only after steps 1–8 pass is the (possibly projected) envelope accepted
into downstream processing (dedupe §4, ordering §5, monitor projection).
The accepted form of a forward-mode envelope is the projected known
envelope; unknown optional data is discarded, not stored. A reference
implementation of this algorithm is pinned deterministically in
`tests/test_hook_contract_schema.py` as conformance test code — not
runtime code; production runtime validation remains deferred to HOOK-1
and later Work Orders that extend existing event seams.

## 8. Hook classes

### 8.1 OBSERVE

- Telemetry/visibility only. OBSERVE failures cause visibility degradation
  only (`OBSERVABILITY_DEGRADED`); they MUST NOT block otherwise-safe
  execution.

### 8.2 ADVISORY

- Optimization/review/help behavior (e.g. Ponytail, Caveman, Grill-me
  projections). ADVISORY failures MUST block only that advisory feature and
  MUST NOT override a Work Order, claim, safety gate, or verification
  requirement.

### 8.3 GUARD

- Safety/authority enforcement where an existing accepted policy requires a
  gate. Every GUARD event MUST carry a `guard` object with explicit
  `failure_policy` (`FAIL_CLOSED` | `FAIL_OPEN`), `security_scope`
  (boolean), and `authority_scope` (boolean).
- If `security_scope` or `authority_scope` is true, `failure_policy` MUST be
  `FAIL_CLOSED`. Fail-open security/authority GUARD is invalid.
- Ambiguity fails closed: a GUARD without explicit scope declarations or
  explicit failure policy is invalid; a classifier that cannot decide
  security/authority involvement MUST classify it as security/authority
  (fail closed) or refuse the registration. Ambiguous GUARD can never fail
  open.
- A non-security, non-authority GUARD MAY declare `FAIL_OPEN` only when its
  accepted Work Order explicitly defines and tests that behavior; otherwise
  `FAIL_CLOSED` is the default.
- Enforcement point: a GUARD's `failure_policy` is evaluated and enforced
  at hook invocation time by the gate authority that synchronously
  consults the hook. FAIL_CLOSED is enforced at that invocation/gate
  authority point, never by eventual stream delivery: the Hook Bus, STM,
  and Monitor pipeline is at-least-once and degradable (§7.3, §16) and
  MUST NOT be the mechanism by which a fail-closed decision blocks
  anything. A GUARD outcome lost to stream degradation is surfaced as
  visibility loss (`HOOK_STREAM_DEGRADED`), not re-decided by the stream.
- `guard` MUST NOT appear on non-GUARD events.

### 8.4 COMMAND

- A COMMAND envelope is a request envelope only; it grants no mutation
  authority and carries no executable payload.
- COMMAND MUST carry `command_request` = `{request_id, command, target_ref?,
  justification?}` with `command` restricted to:
  `pause` | `cancel` | `retry` | `recover` | `reassign` | `release_lane` |
  `cleanup_request` | `merge_request`.
- `command_request` MUST NOT contain process directives (argv/executable/
  shell/env), Git operations, or any direct mutation field; consequential
  execution happens only through the A-Sunday Conductor Command Gateway with
  task/claim/safety/replay/ownership gates (later ACT-1 phase).
- `command_request` MUST NOT appear on non-COMMAND events.

## 9. Payload bounds

- Field-level bounds are schema-enforced (string `maxLength`, integer
  minimum, array `maxItems`/`uniqueItems`). No performance SLOs (rate,
  latency, throughput budgets) are fixed in v1; benchmark planning belongs
  to the roadmap P1 benchmark plan, not this contract.
- Whole-envelope size: SHOULD be ≤ 32768 UTF-8 bytes; MUST be ≤ 65536 UTF-8
  bytes. Larger envelopes are `HOOK_EVENT_OVERSIZED`.
- Size measurement is pinned to the
  exact incoming UTF-8 serialized envelope bytes at the consumer
  transport boundary, before parsing, semantic normalization,
  projection, or validation (§7.4 step 1).
  Structured in-process adapters MUST apply the identical cap to the
  exact bytes they would enqueue/serialize before normalization; the
  cap counts UTF-8 bytes, not characters (multibyte content counts its
  full byte width), and key-sorted or
  canonical JSON re-serialization MUST NOT be used as a hidden
  alternative measurement.
- Producer byte supply: every conforming producer, including a
  structured in-process adapter, MUST supply or expose the exact
  serialized envelope bytes that cross the Hook Bus ingestion seam to
  the validator before parsed-object validation. An object-only call
  with no defined emission serialization is not sufficient evidence for
  the byte cap and MUST NOT be accepted as a production conformance
  path; measurement MUST NOT under-measure by counting characters or by
  re-serializing an already-parsed object (§7.4 step 1).
- Sizing context: a known-schema-valid envelope that fills every
  allowed optional field to its bound stays well below the 65536-byte
  MUST cap. This observed headroom does not weaken the cap:
  forward-mode, duplicate-key, malformed, and adversarial envelopes
  still reach the MUST bound and are rejected typed
  (`HOOK_EVENT_OVERSIZED` / `HOOK_EVENT_INVALID`).
- Oversized or invalid envelopes MUST be rejected typed; they MUST NOT be
  truncated into "valid-looking" events.

## 10. Security-invalid envelopes

Regardless of version, an envelope containing any of the following is
security-invalid and MUST be rejected (`HOOK_EVENT_INVALID`) and flagged:

- raw prompt content (`prompt`, `messages`, `transcript` fields);
- credentials/secrets (`token`, `api_key`, `apikey`, `secret`,
  `secret_value`, `password`, `credential_value`, `cookie` fields);
- session/share URLs (`share_url`, `session_url` fields);
- unrestricted command lines (`argv`, `command_line`, `shell_command`
  fields).

Redaction: when command identity is needed, producers MUST emit a digest or
reference (`command_digest` `^[0-9a-f]{16,128}$` or `command_ref` bounded
string) instead of the raw line. `privacy_class` MUST NOT be `SECRET`; there
is no legal secret-carrying hook envelope in v1.

## 11. Privacy classification and shared fake-secret corpus

- `privacy_class` (`PUBLIC` | `INTERNAL` | `SENSITIVE`) is required core and
  classifies envelope visibility. `SENSITIVE` envelopes SHOULD be
  payload-minimal (identifiers and pointers only).
- Shared fake-secret corpus `fake-secret-corpus/1` (not secret; used by every
  adapter/redaction test so leakage checks are uniform):
  - `sk-FAKE0000000000000000000000000000000000`
  - `ghp_FAKE0000000000000000000000000000000`
  - `xoxb-FAKE-000000000000000000000000`
  - `AKIAFAKE0000000000`
  - `FAKESESSIONCOOKIE=0000000000000000`
  - `-----BEGIN FAKE PRIVATE KEY-----`
  - `https://chat.example/FAKE/share/0000`
  - `Bearer FAKE000000000000000000000000000`
- Any redaction/adapter implementation MUST pass the corpus: no corpus item
  may appear in any normal hook payload, `summary`, or evidence pointer.
- Raw prompts are disabled by default everywhere in the pipeline.

## 12. Evidence pointers, not authority copies

- `evidence_refs` are pointers (paths/URIs) and `evidence_digest` is a
  content digest. They reference accepted durable evidence/job authorities
  (e.g. durable execution records) and MUST NOT carry evidence content,
  task state, or authority. The Hook Bus is never an evidence store.

## 13. STM relationship

- STM is a derived, bounded, TTL-governed in-memory read-model inside the
  Monitor backend (roadmap §11). Hook events feed it; it never feeds
  authority. Authoritative state always overrides STM; STM exposes explicit
  stale/unknown markers. No STM component may write task/claim truth.

## 14. Adapter capability and version discovery

- Each adapter MUST expose a versioned capability document consumable as a
  normalized `transport.adapter_capabilities`-typed event or equivalent
  local discovery record, with at minimum: `adapter.adapter_id`,
  `adapter_version`, `contract_version` (a `1.x.y` this adapter emits),
  `emits` (bounded list of `event_type` values), `redaction_policy`
  (`fake-secret-corpus/1` for v1), and `supports_sequence` (boolean).
- Adapters are version-bound to their native surface; they MUST NOT assume
  event names across native versions. Capability mismatch is typed
  (`HOOK_VERSION_UNSUPPORTED` / `HOOK_ADAPTER_UNAVAILABLE`); silent fallback
  is forbidden.
- In the 1.0.0 schema, the `adapter` payload is legal only on an OBSERVE
  event whose `event_type` is exactly `transport.adapter_capabilities`
  (`domain` `transport`, `action` `adapter_capabilities`); any other
  adapter-bearing event is schema-invalid.

## 15. Localhost browser boundary

- Monitor endpoints are local/private by default. Any browser-consumed
  localhost endpoint (Web UI, Extension UI) MUST enforce explicit Origin
  validation (allowlist; resist CSRF and DNS-rebinding) plus a local
  authentication/session token before serving event data, even when bound
  only to loopback.
- No extension/browser surface obtains implicit filesystem/process/Git
  authority; the read-only milestone has no consequential command channel.
- Remote exposure requires separate auth/threat-model work and is out of
  scope for v1.

## 16. Backpressure and degradation

- The pipeline uses bounded buffers. On overflow, consumers observe typed
  `HOOK_BACKPRESSURE` and then `HOOK_STREAM_DEGRADED`.
- `HOOK_STREAM_DEGRADED` is a local consumer/monitor health condition: it
  reports that the consumer's local event channel is degraded. It MUST be
  raised and recorded as local state and MUST NOT depend on successfully re-enqueueing
  a new event onto the already degraded stream.
- Drop policy under sustained pressure: drop/shed OBSERVE and ADVISORY
  first; never silently drop GUARD rejections or COMMAND requests —
  surface their loss as `HOOK_STREAM_DEGRADED`.
- Degradation affects observability only (§7.3) unless an accepted GUARD
  declares otherwise.

## 17. Failure vocabulary

Typed failure codes (roadmap §19) used by this contract:
`HOOK_ADAPTER_UNAVAILABLE`, `HOOK_VERSION_UNSUPPORTED`,
`HOOK_EVENT_INVALID`, `HOOK_EVENT_OVERSIZED`, `HOOK_BACKPRESSURE`,
`HOOK_STREAM_DEGRADED`, `STM_STALE`, `STM_REBUILD_REQUIRED`,
`MONITOR_PROJECTION_DEGRADED`, `COMMAND_GATEWAY_UNAVAILABLE`,
`DEVICE_ROUTE_UNAVAILABLE`, plus `OBSERVABILITY_DEGRADED` for OBSERVE-only
visibility loss.

## 18. Conformance and tests

Deterministic conformance is `tests/test_hook_contract_schema.py`
(schema parse/draft; minimal valid OBSERVE; optional groups; invalid/missing
identity; invalid class/phase/domain/action; version bounds;
sequence/dedupe; k-way merge ordering consistency (no timestamp-first
global sort); GUARD explicit policy; security/authority fail-open
rejected; ambiguous GUARD cannot fail open; secret/raw-prompt exclusion;
oversized rejection; COMMAND without direct process/Git authority;
correlation/causation identifier-only; unknown optional field policy;
dedupe identity proofs — explicit `dedupe_key` else global `event_id`,
never `source` + `sequence`, distinct `event_id`s survive a source/sequence
collision across devices, a restarted sequence under a new observed session
is not a duplicate, same-`event_id` redelivery is a duplicate, and explicit
`dedupe_key` idempotence stays bounded by the replay window; ordering
stream domain `(source, device_id, observed session)` — never bare source
— with a deterministic late-lower-sequence append-only-history regression
and no waiting for unseen gap events; `event_type` = `domain.action`
semantic pin; adapter capability payload constrained to the
capability-discovery event; GUARD fail-closed enforcement point pinned to
invocation/gate authority, never eventual stream delivery;
forward-compatibility consumer algorithm proofs (§7.4): the strict schema
stays closed on unknown fields, a reference consumer accepts same-major
newer-minor envelopes carrying benign unknown optional fields including
benign unknown nested subfields inside known optional objects after the
raw security scan, rejects the same unknown field on same/older known
minor, rejects §10 forbidden fields before filtering including nested
attacks and corpus leakage, preserves GUARD/COMMAND/adapter class
conditionals and `event_type` semantic validation after projection,
rejects a different major `HOOK_VERSION_UNSUPPORTED`, and measures the
whole-envelope cap on exact incoming UTF-8 bytes at the transport
boundary ahead of the raw security scan; replay-window ownership pinned
to consumer/Monitor deployment configuration; cross-stream `occurred_at`
rank uses parsed RFC 3339 instants with a `20Z` vs `20.5Z` inversion
regression; `HOOK_STREAM_DEGRADED` pinned to a local health condition
that never depends on re-enqueueing onto the degraded stream; `event_id`
UUIDv4 pinned producer-generation-only). Post-review P2 hardening pins:
duplicate object member names at any depth rejected `HOOK_EVENT_INVALID`
in strict and forward modes before projection and before parsed-envelope
security interpretation can lose information (benign top-level
duplicate; duplicate unknown key whose first value carries a forbidden
field while the second is benign — the last-wins information-loss
proof; duplicate nested key inside an unknown object; duplicate key
inside an object inside an array; a duplicate known `guard` member that
would flip `failure_policy` under last-wins), with non-duplicate
controls still accepted; structured in-process adapter byte-supply
conformance — the producer's exact emitted UTF-8 bytes are the measured
evidence, one explicitly named deterministic serialization serves
test/reference fixtures only, an object-only call is not a production
conformance path, and measurement never counts characters or
re-serializes a parsed object, proven at the exact 65536-byte boundary
and with multibyte emitted bytes; unknown optional subfield inside
`adapter` dropped in forward mode with known adapter semantics
preserved; `command_request` on OBSERVE rejected in forward mode even
with unknown fields present; nested unknown field under a known
optional object rejected in strict mode; maximal known-schema-valid
envelopes stay well below the MUST cap without weakening it.
No network, no MCP, no runtime validation is added by this contract.
