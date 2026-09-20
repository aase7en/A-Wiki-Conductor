# Claude Code Hook Adapter v1 (HOOK-3/Claude)

Status: CONTRACT-ONLY FREEZE CANDIDATE — WO-P1-375 / Issue #375
Adapter id: `claude-hook-adapter`
Adapter version: 1.0.0
Contract version emitted: Hook Contract v1 `1.0.0` (exact)
Dependency pin: Hook Contract (HOOK-0, WO-P1-258) at accepted commit
`602f6db01e170f74456ff77e1b5df01622fb84dd`
(`fix(WO258): review-001 dedupe identity, stream domain, late arrival`,
merged to main via `2a461ae22ab28ad3b48f15660ab818f700faab30`;
`docs/contracts/hook-contract-v1.md` blob `941f9731f9665fe109451a14cdc2b737555be99a`,
`docs/contracts/hook-contract-v1.schema.json` blob `d176fd5e6393af6f5619fad372ad59aa858391ee`).
Superseded historical pin (WO-P1-261 freeze, evidence only): commit
`f20fff006aad1e592b150ffdcb52ac331ec00a3a`
(`docs/contracts/hook-contract-v1.md` blob `b4f98fb8f2ce35958b4e5cfc660eeb671c46d723`,
`docs/contracts/hook-contract-v1.schema.json` blob `23c5dc3035320dc288e376bd103d8e00409a9762`).
Planning authority: `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md`
(§10 Claude Code, P4 HOOK-3).

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as
described in RFC 2119/8174.

If the Hook Contract head drifts from the pin above, this adapter contract is
invalid until the dependency is re-pinned and the affected delta is reviewed
(fail closed).

## 1. Purpose and authority

This document defines the deterministic mapping semantics from native
Claude Code hook/plugin lifecycle surfaces into Hook Contract v1 normalized
envelopes. It is a mapping contract only: it implements no runtime, bus,
store, or transport (those belong to later HOOK/STM/MON Work Orders).

Non-negotiable boundaries (inherited from the roadmap §3 and Hook Contract
§1, unchanged by this adapter):

- The adapter grants NO task, claim, lane, mutation, retry, review, or
  acceptance authority. A native hook firing is never proof of authority.
- GUARD outcomes MUST come only from existing accepted authority. This
  adapter v1 emits OBSERVE-class envelopes ONLY; it MUST NOT emit GUARD or
  COMMAND envelopes. A native deny/block/deny-decision observation is
  recorded as an OBSERVE event with at most identifier/digest/evidence
  fields, never as a guard verdict. Binding any GUARD semantics to Claude
  hooks requires a separate accepted Work Order with an explicit policy
  authority (`policy_ref`); none exists at this freeze.
- Adapter failures degrade observability only (Hook Contract §7.3); they
  MUST NOT rewrite task truth and MUST NOT block otherwise-safe execution.
- The adapter is version-bound to the native Claude Code surface. It MUST
  NOT assume native event names, field names, or payload shapes across
  native versions (§4, §8).

## 2. Reuse classification

- REUSE: Hook Contract v1 envelope/schema/identity/ordering/redaction rules
  and the shared fake-secret corpus `fake-secret-corpus/1`; the capability
  document format of Hook Contract §14; test conventions of
  `tests/test_hook_contract_schema.py`.
- WRAP: this adapter wraps native Claude Code hook/plugin surfaces into
  normalized envelopes without changing task semantics.
- EXTEND: later HOOK/STM Work Orders extend existing seams to transport
  these envelopes; this contract adds no new store or authority path.
- REPLACE/NEW: none.

## 3. Locally observed capability evidence (2026-09-19)

Evidence collection was restricted to the installed Claude CLI version and
help output only (no user config, network, chat history, cookies,
credentials, or raw prompts were inspected).

Observed on the local Windows device:

| Evidence | Command | Observation |
|---|---|---|
| Version | `claude --version` | `2.1.178 (Claude Code)` |
| Hook lifecycle events flag | `claude --help` | `--include-hook-events` — "Include all hook lifecycle events in the output stream (only works with --output-format=stream-json)" |
| Hooks subsystem exists | `claude --help` | `--bare` lists "skip hooks" among skipped subsystems |
| Hooks are session customization | `claude --help` | `--safe-mode` lists "hooks" among disabled customizations |
| Hook debug category | `claude --help` | `--debug [filter]` documents `"hooks"` as a filter category example |
| Streaming output surface | `claude --help` | `--output-format stream-json` (with `--print`) |

What this evidence proves: a hooks subsystem exists in `2.1.178`, hook
lifecycle events can be surfaced in a `stream-json` output stream, and
hooks are per-session customization.

What this evidence does NOT prove: any native hook event name, any native
payload field name, any matcher/config schema, any ordering guarantee, or
any subagent/stop/terminal event semantics for `2.1.178` or any other real
version. All of those remain capability UNKNOWN at this freeze and require
discovery (§4.3). This contract asserts NO native event name for any real
Claude Code version.

## 4. Capability registry

### 4.1 Format

The adapter is driven by a version-pinned capability registry
(canonical fixture: `tests/fixtures/hook_adapters/claude/capability_registry.json`).
One entry per exact native version string:

```
<version>: {
  "status": "DISCOVERY_REQUIRED" | "FIXTURE_ONLY" | "PROVEN",
  "real_version": bool,
  "discriminator_field": <native discriminator field name, only once proven>,
  "evidence": [ {kind, command, observed, observed_at}, ... ],
  "native_bindings": { <native-discriminator>: binding, ... },
  "emits": [ <normalized event_type>, ... ]
}
```

- `discriminator_field` names the native frame field carrying the event
  discriminator. It is itself registry-bound evidence: a version whose
  discriminator field name is not proven carries no `discriminator_field`
  and no frame from it can be classified at all (typed unavailable, §8).
  Fixture registry entry `0.0.0-fixture-a` uses the synthetic field name
  `fixture_event`.
- `native_bindings` maps the native frame discriminator (native event name)
  to a binding `{event_type, phase, privacy_class, summary_token}` from the
  mapping table (§6).
- `emits` MUST equal the set of normalized event types the version's
  bindings produce, plus `transport.adapter_capabilities`. A real version
  with no proven bindings emits exactly
  `["transport.adapter_capabilities"]` and nothing else.
- Entries with `"real_version": true` describe actually observed native
  versions; entries with `"real_version": false` are synthetic fixture
  vocabularies that prove mapping mechanics only and MUST never be
  referenced as capability claims about any real version.

### 4.2 Freeze state

At this freeze the registry contains exactly:

- `2.1.178` — `DISCOVERY_REQUIRED`, `real_version: true`, the §3 evidence
  pointers, `native_bindings: {}` (nothing proven),
  `emits: ["transport.adapter_capabilities"]`.
- `0.0.0-fixture-a` — `FIXTURE_ONLY`, `real_version: false`, synthetic
  `Fx*` bindings for all §6 mappings, used by offline conformance only.

Registry rule (fail-closed): a `real_version: true` entry MAY carry
bindings only when every binding is backed by recorded local discovery
evidence (§4.3); at this freeze no real version carries any binding.

### 4.3 Discovery procedure (required before any real mapping)

Before the adapter may normalize any real-version native frame:

1. Run the pinned native CLI version locally with a benign synthetic
   workload, capturing hook lifecycle event output through its documented
   streaming surface (for `2.1.178`: `--print --output-format=stream-json
   --include-hook-events` per `--help` evidence).
2. Record the observed native discriminator vocabulary and payload field
   names into the registry entry with an evidence pointer (command, date,
   stored raw-capture reference under the Work Order's evidence area).
3. Re-review the affected mapping bindings under the Work Order gates;
   only then may `status` become `PROVEN` for that exact version.
4. Discovery MUST NOT infer names from documentation, network sources,
   memory, or other versions. Only locally observed vocabulary counts.

## 5. Native input frames

A native input frame is one JSON object delivered to the adapter by the
native hook surface. Frames are untrusted input.

- Discriminator: the frame's native event discriminator field. Its field
  name is registry-bound per version (fixture registry: `fixture_event`).
  A frame whose discriminator is not bound for the pinned version is
  rejected typed (§8); it is never guessed or fuzzy-matched.
- Closed destination allowlist: the adapter copies values into envelope
  fields ONLY through the identifier destinations below. Every other
  native field is dropped entirely — never passed through, logged, or
  summarized. There is no passthrough mode.
- Identifier destinations (each value MUST match the Hook Contract pattern
  for its destination before entering the envelope; otherwise it is
  dropped or the frame is rejected per §7):
  - session identifier → `correlation_id`
  - turn identifier → `execution_id`
  - subagent identifier → `execution_id`
  - model identifier → `model_id`
  - `occurred_at` → normalized to RFC 3339 UTC `Z` (§5.1)
  - `duration_ms` → `duration_ms` (integer ≥ 0)
  - tool identity + tool payload + failure code → `command_digest` only
    (§7.2); tool names, tool inputs, tool outputs, and result bodies are
    never copied
  - failure code → `blocker_code` (closed vocabulary, §6)
- `summary` is generated exclusively from the binding's fixed
  `summary_token` vocabulary. Native text NEVER enters `summary`,
  `evidence_refs`, or any other envelope field.

### 5.1 Timestamp normalization

- Input timestamps carrying an explicit UTC offset are converted to UTC
  `Z` form (fractional seconds preserved when present).
- Timestamps without an offset are ambiguous and the frame is rejected
  typed `HOOK_EVENT_INVALID` (fail closed; the adapter never guesses a
  timezone).
- Unparseable timestamps are rejected the same way.

## 6. Mapping table

All mappings produce OBSERVE-class envelopes. `event_type` conforms to
Hook Contract §3.1 (`domain` + `.` + `action` [+ `.` + segment]).

| # | Normalized event_type | domain | action | phase | privacy_class | summary_token (closed vocabulary) | Native lifecycle target |
|---|---|---|---|---|---|---|---|
| 1 | `execution.session_started` | execution | session_started | within | INTERNAL | `session started` | session lifecycle start |
| 2 | `execution.session_ended` | execution | session_ended | terminal | INTERNAL | `session ended` | session lifecycle end |
| 3 | `execution.prompt_submitted` | execution | prompt_submitted | before | SENSITIVE | `prompt submitted` | user prompt submission |
| 4 | `tool.execute.before` | tool | execute | before | INTERNAL | `tool execution before` | tool pre-execution |
| 5 | `tool.execute.after` | tool | execute | after | INTERNAL | `tool execution after` | tool post-execution |
| 6 | `tool.execute.failed` | tool | execute | after | INTERNAL | `tool execution failed` | tool execution failure |
| 7 | `execution.subagent_started` | execution | subagent_started | within | INTERNAL | `subagent started` | sub-agent lifecycle start |
| 8 | `execution.subagent_stopped` | execution | subagent_stopped | after | INTERNAL | `subagent stopped` | sub-agent lifecycle stop |
| 9 | `execution.agent_stopped` | execution | agent_stopped | after | INTERNAL | `agent turn stopped` | main-agent stop/turn terminal |

- Every mapping is registry-gated: it fires only when the pinned native
  version's registry binding maps the observed discriminator to that row.
  No binding is proven for any real version at this freeze.
- Envelope core for all mappings: `schema_version` = the exact Hook
  Contract version this adapter pins (`1.0.0`), `source` = `claude-code`,
  `source_version` = the pinned native version string,
  `hook_class` = `OBSERVE`, plus configured `device_id` and observed
  `host_os`.
- `blocker_code` closed vocabulary for mapping 6:
  `NATIVE_TOOL_ERROR` | `NATIVE_TIMEOUT` | `NATIVE_PERMISSION_DENIED`.
  A native failure code outside the closed vocabulary is rejected typed
  `HOOK_EVENT_INVALID`; it is never transliterated or passed through.

### 6.1 Capability discovery event

Every adapter instance exposes one versioned capability document as a
normalized `transport.adapter_capabilities` OBSERVE event (Hook Contract
§14): `adapter.adapter_id` = `claude-hook-adapter`, `adapter_version` =
this contract's version, `contract_version` = the pinned `1.x.y`,
`emits` = the registry `emits` for the pinned native version,
`redaction_policy` = `fake-secret-corpus/1`, `supports_sequence` = `false`
(§9). For `2.1.178` this event honestly reports zero lifecycle mappings.
The `adapter` payload appears ONLY on this capability-discovery event, as
the accepted 1.0.0 schema requires (Hook Contract §14): any other
adapter-bearing event is schema-invalid.

## 7. Redaction

### 7.1 Absolute exclusions

The following NEVER enter any normalized payload, `summary`, evidence
pointer, or identifier destination, regardless of native field name:

- raw prompt / message / transcript content;
- secrets, tokens, API keys, cookies, credentials (including every
  `fake-secret-corpus/1` item);
- session/share URLs;
- raw environment values, raw argv / command lines, secret-bearing
  command lines;
- tool input/output bodies, file contents, and native free text of any
  kind.

### 7.2 Digest-only command identity

When tool or command identity is needed:

`command_digest` = first 64 hex chars of
`sha256( UTF8( <tool_identifier> + ":" + <payload_sha256> ) )` where
`payload_sha256` = `sha256( UTF8( canonical_json(tool_payload) ) )` and
`canonical_json` sorts keys with compact separators. The digest is
derived, never truncated from, the raw values; raw values do not appear
anywhere in the envelope.

### 7.3 Security-invalid frames

If any value destined for an envelope field (identifier destinations,
timestamps, durations) matches secret shapes — including any
`fake-secret-corpus/1` item, token-like prefixes (`sk-`, `ghp_`, `xoxb-`,
`AKIA`, `Bearer `), private-key headers, or session/share-URL markers —
the frame is rejected typed `HOOK_EVENT_INVALID` with a security-invalid
flag; no envelope is emitted. Secrets detected only in dropped (non-
destination) native fields never enter the envelope; the frame may still
produce a clean envelope because there is no passthrough (§5).

## 8. Version and capability mismatch (no silent fallback)

| Condition | Typed outcome | Envelope? |
|---|---|---|
| Native version not present in the registry | `HOOK_ADAPTER_UNAVAILABLE` (detail: unknown native version; discovery required) | no |
| Registry entry exists but the discriminator is unbound (incl. all real versions at this freeze) | `HOOK_ADAPTER_UNAVAILABLE` (detail: mapping unavailable for version) | no |
| Requested contract version has major ≠ 1 | `HOOK_VERSION_UNSUPPORTED` | no |
| Native version registry status `DISCOVERY_REQUIRED` | every lifecycle mapping returns `HOOK_ADAPTER_UNAVAILABLE`; only the capability event (§6.1) is emittable | capability only |
| Frame discriminator/identifier/timestamp/failure-code invalid | `HOOK_EVENT_INVALID` | no |
| Finalized envelope > 65536 UTF-8 bytes | `HOOK_EVENT_OVERSIZED` (no truncation into valid-looking events) | no |

- Fixture-only registry entries (`real_version: false`) MUST NOT satisfy
  lookups for real versions; binding lookups are exact-version.
- There is no fallback vocabulary, no cross-version name inference, and
  no default mapping. Silent fallback is forbidden (roadmap §10, P4 exit
  gate).
- Typed rejection evidence carries at most: the typed code, a bounded
  fixed-vocabulary detail token, the pinned native version, and an
  identifier-validated discriminator token. It never carries frame
  content.

## 9. Ordering and dedupe (delegated)

The adapter does not invent global sequence or clock authority:

- It emits no `sequence` field and reports `supports_sequence: false`.
- `dedupe_key` is omitted (no deliberate native replay identity is
  claimed); per Hook Contract §4 as accepted at the pinned head,
  consumers dedupe these envelopes on the globally unique `event_id`
  only. `source` + `sequence` MUST NOT become duplicate identity for
  these envelopes under any consumer configuration.
- Retries/duplicates of the same semantic native event MUST reuse the
  same `event_id`; first-normalization identity is retained by the
  runtime seam that later Work Orders provide.
- Stream-domain ordering — the
  `(source, device_id, observed transport/adapter session)` stream
  identity, per-stream `sequence` authority, append-only emitted
  history, late-arrival append with surfaced sequence inversion,
  interleaving, k-way merge, gap handling, and replay-window dedupe —
  is entirely Hook Contract §4/§5 semantics; this adapter adds none
  of it.

## 10. Envelope size guard

At finalization the serialized envelope (UTF-8) MUST be ≤ 65536 bytes
(SHOULD ≤ 32768). Oversized candidates are rejected typed
`HOOK_EVENT_OVERSIZED` and are never truncated into valid-looking events.

## 11. Conformance and fixtures

Deterministic offline conformance is
`tests/test_claude_hook_adapter_contract.py` against
`docs/contracts/hook-contract-v1.schema.json`, driven only by
`tests/fixtures/hook_adapters/claude/**`:

- `capability_registry.json` — the registry (§4);
- `frames/*.json` — bounded synthetic native-shaped frames: one per §6
  mapping (valid), plus unknown discriminator, real-version-unbound,
  secret-in-destination, secret-in-dropped-field, ambiguous timestamp,
  and invalid failure-code cases; redaction-bait frames are explicitly
  marked;
- `expected/*.json` — the exact normalized envelopes (deterministic ids,
  device, and timestamps) and the two capability events.

The suite proves: schema validity of every expected envelope; exact
mapper output equality; registry honesty for `2.1.178` (no lifecycle
emits); fixture/real-version isolation; typed rejects with no silent
fallback; secret-bait confinement (corpus items appear only in marked
input frames and never in any envelope, expected file, or the registry);
fixed-vocabulary summaries; UTC-Z normalization; retry identity reuse;
ordering delegation; the recorded dependency pin equals the actual
pinned Hook Contract blobs (fail-closed against silent drift); the
`adapter` payload is legal only on the capability-discovery event; the
size guard; and that no GUARD/COMMAND envelope
is ever produced. No network, no live CLI, no MCP, no runtime.

## 12. Out of scope / future Work Orders

- Live discovery run against the installed CLI (§4.3) and `PROVEN`
  registry upgrades;
- runtime wiring of the adapter into a hook/bus/STM seam;
- GUARD policy binding via `policy_ref` under separate accepted authority;
- COMMAND emission (none is contemplated for this adapter);
- any native Claude config mutation.
