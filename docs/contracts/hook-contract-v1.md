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
| `event_id` | string | MUST match `^hk-[0-9a-f]{32}$` (UUIDv4 hex). Globally unique within the normalized event domain. |
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
- Ordering/dedupe: `sequence`, `dedupe_key` (§5).
- Correlation: `correlation_id`, `causation_id` (§6).
- Evidence: `evidence_refs` (max 16 unique pointer strings), `evidence_digest`
  (`^[0-9a-f]{16,128}$`) (§12).
- Presentation: `summary` (max 512 chars, sanitized free text; MUST NOT
  contain corpus items from §11).
- Class payloads: `guard` (§8.3, GUARD events only), `command_request`
  (§8.4, COMMAND events only), `adapter` (§14, OBSERVE capability-discovery
  events only) — the schema forbids each on every other hook class.

Unknown-field policy: the 1.0.0 schema is closed (`additionalProperties`
false everywhere). Consumer forward-compatibility rules are in §9.2.

## 4. Event identity

- `event_id` MUST be globally unique within the normalized event domain.
  v1 reserves the `hk-` prefix; producers MUST generate `hk-<uuid4hex>`.
- Every emission (including retries by the adapter or transport) MUST reuse
  the same `event_id` for the same semantic event.
- Delivery is at-least-once where durable delivery is used; there is NO
  exactly-once promise. Consumers MUST be idempotent.
- Consumers MUST additionally dedupe on source-local identity
  (`dedupe_key` if present, else `source` + `sequence` if present, else
  `event_id`) inside a bounded replay window: default 1800 s, configurable,
  clamp 300 s–86400 s. Events seen with identical source-local identity
  inside the window MUST be dropped as duplicates. Beyond the window,
  idempotent consumer design absorbs residual risk; no global dedupe table
  is implied.

## 5. Ordering

- Per-source ordered queue: the projection maintains one ordered queue per
  observed `source` per transport session. When the producer provides
  `sequence` (monotonically increasing non-negative integer per `source`),
  `sequence` is authoritative for order within that source: the queue
  orders that source's events carrying `sequence` by `sequence`, and
  consumers MUST NOT reorder a source's events against their `sequence`.
- When `sequence` is absent for a source, the queue preserves observed
  producer arrival order for that source within the transport session and
  MUST NOT claim stronger ordering than it observed.
- Sequence gaps and mixed sequence availability within a source are
  handled conservatively: the projection MUST NOT invent, wait for, or
  synthesize unseen events to fill gaps, and MUST NOT demote, splice, or
  reorder observed items because a gap or a missing `sequence` exists. In
  a mixed queue, events without `sequence` keep their observed arrival
  slots and the events carrying `sequence` fill the remaining slots in
  `sequence` order; no-sequence events are never assigned a synthesized
  or sentinel `sequence` value. Gaps and unknown ordering are surfaced as
  stale/unknown/gap metadata in the projection only where later Monitor
  work supports it; no new durable state store is added for gap tracking.
- Consumers MUST NOT infer any global total order from `occurred_at` wall
  clock values. Cross-device clock skew is assumed. In the merge,
  `occurred_at` is observed presentation metadata only and carries no
  causal or global-order claim.
- Deterministic monitor merge: when interleaving sources, the projection
  is a stable k-way merge across the per-source ordered queues. Only the
  current head of each source queue is eligible at each step. Among
  eligible heads, the deterministic cross-source ranking key is
  `(occurred_at, source, event_id)`; the head's `sequence` MAY be carried
  as redundant metadata. This key selects only among heads of different
  source queues and MUST NOT reorder items within one source queue, so a
  timestamp-first global sort of all events is non-conforming even when
  labeled as observed interleaving. The merged result MUST be labeled as
  observed interleaving, not causal order.
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
| same major, producer minor > consumer known minor | older minor | validate core; MUST ignore unrecognized optional fields (forward-compatible), never reject solely for new optional fields. |
| different major | — | typed reject `HOOK_VERSION_UNSUPPORTED`; no silent fallback. |
| unparseable / schema-invalid | — | typed reject `HOOK_EVENT_INVALID`; drop; monitor MUST NOT crash. |
| over size bounds (§9) | — | typed reject `HOOK_EVENT_OVERSIZED`. |

### 7.3 Degrade behavior

- Validation/transport failures degrade observability only
  (`OBSERVABILITY_DEGRADED` / `HOOK_STREAM_DEGRADED`); they MUST NOT rewrite
  task truth and MUST NOT block otherwise-safe execution unless an accepted
  GUARD hook declares otherwise (§8.3).
- Transport failure is not execution failure.

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
correlation/causation identifier-only; unknown optional field policy).
No network, no MCP, no runtime validation is added by this contract.
