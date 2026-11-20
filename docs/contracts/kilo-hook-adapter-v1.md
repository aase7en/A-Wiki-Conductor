# Kilo Hook Adapter v1 (HOOK-3 / Kilo lane)

Status: CONTRACT-ONLY CONFORMANCE CANDIDATE — WO-P1-376 / Issue #376 (identity rebound from WO-P1-262; see the WO-P1-376 work-order historical alias section)
Identity schema: GITHUB_ISSUE_V1
Adapter contract version: 1.0.0 (emits Hook Contract `1.0.0`)
Planning authority: `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md` (P4 — HOOK-3 harness adapters, Kilo sub-lane)
Dependency: Hook Contract v1 post-merge repair exact `0d4f0c3b36ff7fad9ed14636730443119683cb1d` (`docs/contracts/hook-contract-v1.md` blob `25f69a964140c082db9d43b65dd3fcd9dbfc0c3c`; `docs/contracts/hook-contract-v1.schema.json` blob `98451ee3a4b63b4f07ca7b38525f9f5016916d54`). Superseded accepted dependency (evidence only): `602f6db01e170f74456ff77e1b5df01622fb84dd` via merge `2a461ae22ab28ad3b48f15660ab818f700faab30`.
Machine conformance: `tests/test_kilo_hook_adapter_contract.py` + fixtures under `tests/fixtures/hook_adapters/kilo/`
Claim: WO-P1-376-KILO-HOOK-ADAPTER-REBIND-001
Result destination: `runs/WO-P1-376/repair/`

The key words MUST, MUST NOT, SHOULD, and MAY are to be
interpreted as described in RFC 2119/8174. This document defines the
adapter contract and its offline deterministic conformance harness only; it
implements no runtime, adds no event store, and mutates no `src/` code (WO-P1-376 is
CONTROL_PLANE_ONLY; the original NEW-only docs/tests/fixtures scope was authored
under WO-P1-262 and is preserved as historical evidence).

## 1. Purpose and authority

The Kilo Hook Adapter maps observed, safe Kilo CLI native stream evidence
into Hook Contract v1 normalized envelopes. It is a WRAP adapter in the
Hook Contract §2 sense: it changes no task semantics and creates no new
authority.

Non-negotiable boundaries (inherited from Hook Contract §1 and the
roadmap §3):

- The adapter NEVER grants task, claim, lease, provider-admission, model
  selection, mutation, retry, review, or acceptance authority.
- Provider, model, variant, and version names observed from Kilo are
  metadata only. They identify provenance of observed evidence; they never
  authorize anything and never select or fall back to another
  provider/model.
- The adapter is never SSoT. Actual Git/GitHub/runtime/durable evidence
  always outranks adapter projections.
- The adapter adds no global time authority and no second event store; it
  defers to Hook Contract §4/§5 identity, ordering, and dedupe semantics
  without restating or weakening them.
- Only `OBSERVE`-class normalized events are emitted by adapter v1. The
  adapter MUST NOT emit `GUARD`- or `COMMAND`-class events and MUST NOT
  borrow their gate/authority semantics (Hook Contract §8): every adapter
  envelope is `hook_class=OBSERVE`, and stream delivery is never an
  enforcement point.

## 2. Native surface evidence and capability truth

Evidence classes used throughout this contract:

- OBSERVED — seen in the installed CLI (version/help output, safe to
  inspect) or in the accepted author harness's sanitized handling of the
  `kilo run --format json` stream at Kilo CLI 7.7.2 on Windows.
- ASSUMED (fixture grammar) — not enumerated by observation; defined only
  as the bounded fake native-shaped fixture grammar so the mapping is
  deterministic and testable. Must be re-proven by capability discovery
  against the pinned native version before any live use.
- UNKNOWN — no observation and no fixture grammar. MUST NOT be mapped,
  guessed, or fabricated.

### 2.1 Installed CLI capability evidence (OBSERVED, 2026-09-19)

- `kilo --version` → `7.7.2` (npm-global `@kilocode/cli`, Windows host).
- `kilo run --help`: `--format json` is documented as emitting
  "raw JSON events" — the ingestion surface for this adapter.
- `kilo run --help`: `--variant` documented as provider-specific reasoning
  effort; `--model` takes `provider/model`; `--agent` selects an agent.
- `kilo plugin --help`: `kilo plugin <module>` installs an npm module
  plugin and updates config (`--global`, `--force`); global `--pure` runs
  without external plugins.
- `kilo --help` also lists `session`, `export [sessionID]`,
  `import <file>`, `models [provider]`, `agent`, `config`, `db`, `stats`,
  `remote`, `daemon` commands (existence only; not mapped).

No plugin lifecycle event/hook vocabulary, event-name list, or
subscription syntax is documented in any help output. The Kilo plugin
extension surface therefore exists as an install/config surface, but its
lifecycle event APIs are UNPROVEN (UNKNOWN) and are not mapped by v1.

Not inspected (forbidden by WO-P1-376, and before it by WO-P1-262): Kilo
auth/credential stores, raw
share URLs, credentials, secret env, external web. Adapter v1 derives
nothing from those surfaces.

### 2.2 Observed stream families (OBSERVED)

From the accepted author harness (`runs/WO-P1-262/author/attempt-0001/`,
sanitized). That path is preserved historical evidence from the WO-P1-262
author lane and remains the factual provenance of these observations after
the WO-P1-376 identity rebind:

- One JSON object per line (`kilo run --format json` NDJSON).
- Top-level fields: `type`, `timestamp`, `sessionID`, and a `part` object.
- Observed `type` values: `step_start`, `tool_use`, `text`.
- `tool_use` parts contain a tool name and a `state` object with
  `status`, `input`, `output` members.
- `text` parts contain a string `text` member.

### 2.3 Capability table

| Capability | Class | Evidence |
|---|---|---|
| NDJSON stream, top-level `type`/`timestamp`/`sessionID`/`part` | OBSERVED | harness stream, CLI 7.7.2 |
| `step_start` events | OBSERVED | harness stream |
| `tool_use` with name + `state.status`/`input`/`output` | OBSERVED | harness stream |
| `text` parts with `part.text` | OBSERVED | harness stream |
| `tool_use.state.status` value vocabulary `{running, completed, failed}` | ASSUMED (fixture grammar) | fixtures only |
| `timestamp` is ISO-8601 parseable, possibly with non-UTC offset | ASSUMED (fixture grammar) | fixtures only |
| Native per-source monotonic `sequence` | UNKNOWN (not observed) | `supports_sequence=false` |
| Session start/end lifecycle stream events | UNKNOWN | not observed; never fabricated |
| Permission request/grant/deny events | UNKNOWN | not observed; never fabricated |
| Failure/error stream events beyond `tool_use` state | UNKNOWN | not observed; never fabricated |
| Terminal/result stream events | UNKNOWN | not observed; harness exit code is dispatcher evidence, not a stream event; never fabricated |
| Kilo plugin lifecycle event APIs | UNKNOWN | CLI install/config surface observed; event vocabulary unproven |

Adapter v1 binds to native surface family **Kilo CLI 7.7.x** (observed at
7.7.2). Any other native version (including 7.8+ or 6.x) requires fresh
capability discovery before emission; until then the adapter fails closed
with a typed version mismatch (§7). This binding is to the observed
surface family, not a claim that other versions differ.

## 3. Fixture grammar (ASSUMED, bounded)

The fixture grammar is the ONLY native shape v1 maps. It lives under
`tests/fixtures/hook_adapters/kilo/` as fake, bounded, native-shaped
data. Real emission against a live stream additionally requires the
UNKNOWN rows in §2.3 to be re-classified by capability discovery.

`stream-meta.json` — per-stream context:

```json
{
  "kilo_version": "7.7.2",
  "provider_model": "cointh-glm/glm-5.3",
  "evidence_base": "runs/WO-P1-262/author/attempt-0001/kilo-sanitized.ndjson"
}
```

`*.ndjson` — one native record per line:

- `type`: string; mappable values `step_start`, `tool_use`, `text`;
  any other value is an unknown type (§6.4).
- `timestamp`: ISO-8601 string; converted to RFC 3339 UTC (`Z`);
  unparseable → record invalid.
- `sessionID`: non-empty string.
- `part`: object. `tool_use` → `{"name": <bounded tool name string>,
  "state": {"status": "running"|"completed"|"failed", "input": <any>,
  "output": <any>}}`; `text` → `{"text": <string>}`; `step_start` →
  object (content ignored beyond digest).

Adapter context (from the conformance harness / future dispatcher, never
from the native stream): `device_id`, `host_os`, `harness_id`, and the
expected `provider_model`. The expected provider/model is compared for
mismatch detection only (§7); it never selects or changes mapping.

## 4. Mapping to Hook Contract v1

All normalized events are `hook_class=OBSERVE`, `source=kilo`,
`source_version=<kilo_version>`, `privacy_class=INTERNAL`,
`correlation_id=<sessionID>`, `harness_id`, `model_id=<provider_model>`,
`evidence_refs=["<evidence_base>:L<n>"]` (1-based line number), and
`evidence_digest=sha256(raw native NDJSON line, UTF-8)` (full 64 hex).

| Native | event_type | phase | domain/action | Extra fields |
|---|---|---|---|---|
| adapter start | `transport.adapter_capabilities` | `before` | `transport`/`adapter_capabilities` | `adapter` capability object (§5) |
| `step_start` | `execution.step_start` | `within` | `execution`/`step_start` | — |
| `tool_use` `status=running` | `tool.execute.before` | `before` | `tool`/`execute` | `command_digest=sha256(input)`, `summary="kilo tool <name> running (input redacted)"` |
| `tool_use` `status=completed` | `tool.execute.after` | `after` | `tool`/`execute` | `command_digest=sha256(input)`, `summary="kilo tool <name> completed (input/output redacted)"` |
| `tool_use` `status=failed` | `tool.execute.after` | `after` | `tool`/`execute` | `command_digest=sha256(input)`, `state="FAILED"`, `blocker_code="KILO_TOOL_FAILED"`, `summary="kilo tool <name> failed (input/output redacted)"` |
| `text` part | `execution.message` | `within` | `execution`/`message` | `summary="kilo text part (redacted, digest only)"`; raw text NEVER carried |

Rules:

- `event_type` always equals `domain` + `.` + `action` (+ optional one
  segment for phase-qualified tool types), per Hook Contract §3.1.
- Tool identity is the bounded tool `name` inside `summary` only. Raw
  `input`/`output` (which can embed commands, env, file contents,
  secrets) are carried ONLY as SHA-256 digests (`command_digest` for
  input; the record-level `evidence_digest` covers the whole record).
- Raw message text is NEVER carried; `text` parts map digest-only.
- Any `status` value outside the fixture grammar vocabulary, any unknown
  `type`, and any malformed record are dropped with a typed reason
  (§6.4/§7); the adapter MUST NOT guess, synthesize, or reinterpret them.
- `occurred_at` = native `timestamp` normalized to RFC 3339 UTC with `Z`.
  If the timestamp carries an offset, conversion to UTC is arithmetic
  only; the adapter never shifts, estimates, or invents clock values.
  Unparseable timestamp → record invalid (dropped, typed).
- Session lifecycle, permission, and terminal native events are UNKNOWN;
  no mapping exists and none may be inferred from presence/absence of
  stream traffic.

## 5. Capability discovery

The adapter MUST emit one `transport.adapter_capabilities` OBSERVE event
before any stream mapping, carrying the `adapter` object (Hook Contract
§14):

```json
{
  "adapter_id": "kilo-hook-adapter",
  "adapter_version": "1.0.0",
  "contract_version": "1.0.0",
  "emits": [
    "transport.adapter_capabilities",
    "execution.step_start",
    "execution.message",
    "tool.execute.before",
    "tool.execute.after"
  ],
  "redaction_policy": "fake-secret-corpus/1",
  "supports_sequence": false
}
```

Fail-closed gates:

- No capability document → the adapter emits NOTHING.
- `contract_version` outside the `1.x.y` line → `HOOK_VERSION_UNSUPPORTED`;
  no emission.
- An event type not listed in `emits` MUST NOT be emitted; if a mappable
  native record would produce an unlisted type, the record is dropped with
  a typed capability reason.
- The `adapter` payload is legal ONLY on this `transport.adapter_capabilities`
  OBSERVE event (`domain` `transport`, `action` `adapter_capabilities`); the
  Hook Contract 1.0.0 schema rejects `adapter` on any other event (Hook
  Contract §14). The adapter MUST NOT attach `adapter` to any other
  envelope.

## 6. Identity, ordering, dedupe (delegated)

Ordering and dedupe semantics are OWNED by Hook Contract §4/§5 at the
post-merge repair pin `0d4f0c3b36ff7fad9ed14636730443119683cb1d`. This adapter
delegates to them and adds no second identity, ordering, or dedupe
authority; this section records only the adapter-local derivation facts.

- Duplicate identity is exactly Hook Contract §4: the explicit
  `dedupe_key` when a producer deliberately supplies one, otherwise the
  globally unique `event_id`. `source` + `sequence` MUST NOT be used as
  fallback duplicate identity; the adapter never derives identity from
  `source` + `sequence` and never emits `sequence`, so source/sequence
  dedupe is structurally impossible on this adapter's envelopes.
- `event_id` = `hk-<uuid4hex>` generated at first normalization of a
  native record and memoized by `dedupe_key`, so retries/republish of the
  same semantic event reuse the same `event_id` (Hook Contract §4).
- `dedupe_key` = `kilo:<sessionID>:<sha256(raw native line)[:16]>` — a
  deliberate, explicit, stable, source-local key re-derivable from the
  native record alone. A repeated identical native line re-derives the
  same `dedupe_key` and reuses the memoized `event_id`; only its
  per-occurrence evidence pointer differs. Distinct native records
  (distinct digests) always keep distinct `event_id`/`dedupe_key`
  identity and are never collapsed.
- `supports_sequence=false`: no native sequence was observed, so the
  adapter MUST NOT synthesize, assign, or infer any `sequence` value.
  Per-stream order is observed arrival order within the observed stream
  domain `(source, device_id, transport/adapter session context)` (Hook
  Contract §5 — never bare `source`); the adapter preserves record order
  and MUST NOT sort by `occurred_at`, merge or interleave across streams,
  or rewrite already-emitted history. Cross-stream k-way merge and
  late-arrival/append-only handling stay wholly with the downstream
  projection defined by Hook Contract §5.
- `causation_id` is only set when the exact prior normalized `event_id`
  is known; the adapter does not invent causal links.

## 7. Version, provider/model, and capability mismatch

All mismatches are explicit and fail closed; silent fallback is forbidden
(roadmap P4 exit gate). The conformance harness records typed reasons;
mapped Hook Contract failure codes are shown in parentheses.

| Condition | Behavior |
|---|---|
| `kilo_version` outside the pinned `7.7.x` family | emit nothing; typed `KILO_VERSION_UNSUPPORTED` (`HOOK_VERSION_UNSUPPORTED`) |
| capability `contract_version` not `1.x.y` | emit nothing; `HOOK_VERSION_UNSUPPORTED` |
| no capability document | emit nothing; `HOOK_ADAPTER_UNAVAILABLE` |
| stream `provider_model` != expected context value | emit nothing; typed `KILO_PROVIDER_MODEL_MISMATCH` (`HOOK_ADAPTER_UNAVAILABLE`) — never re-map under the observed name |
| native `type` unknown | drop record; typed `KILO_TYPE_UNKNOWN` (`HOOK_ADAPTER_UNAVAILABLE` for that type) |
| `tool_use` status outside grammar | drop record; typed `KILO_STATUS_UNKNOWN` |
| unparseable JSON line / non-object / missing `sessionID` / bad `timestamp` | drop record; typed `KILO_RECORD_INVALID` (`HOOK_EVENT_INVALID`) |

Provider/model notes: `model_id` in normalized envelopes is observed
metadata copied from stream context. Two streams that differ only in
`model_id` MUST produce envelopes identical except for `model_id` —
provider/model names never change mapping, admission, or authority. There
is no Claude-compatible abstraction assumption: no Claude Code hook name,
lifecycle, or semantics is borrowed (roadmap §"Kilo CLI": do not invent a
Claude-compatible shell-hook abstraction).

## 8. Redaction policy

`redaction_policy = fake-secret-corpus/1` (Hook Contract §11). The
adapter MUST pass the shared corpus; no corpus item may appear in any
normalized payload, `summary`, or evidence pointer. Additionally:

- Kilo share URLs (host `app.kilo.ai` with path prefix `/s/`), bearer
  tokens,
  credential-shaped assignments, cookies, and private-key blocks MUST
  never appear in any emitted field. Because v1 carries raw content
  nowhere (digest-only policy), corpus/secret leakage is structurally
  excluded; the conformance suite still asserts it byte-wise over every
  serialized envelope.
- Raw prompts/messages, raw env/argv, and secret-bearing command data are
  never carried; command identity is `command_digest`/`command_ref` only
  (Hook Contract §10).
- If redaction cannot be proven for a field, that field is not emitted.

## 9. Bounds

- Every emitted envelope MUST validate against
  `docs/contracts/hook-contract-v1.schema.json` (Draft 2020-12,
  `additionalProperties: false`).
- Envelope UTF-8 size ≤ 65536 bytes (`HOOK_EVENT_OVERSIZED` above;
  digest-only payloads keep v1 envelopes far below this).
- Fixtures are bounded (< 64 records each, short strings) and contain
  ONLY fake data from the shared corpus; no real secrets.

## 10. Conformance

Deterministic, offline, no network, no MCP, no runtime validation:

- `tests/test_kilo_hook_adapter_contract.py` implements the reference
  mapper for this contract and proves, over the fixtures: capability
  document/event conformance; exact expected-envelope equality; Hook
  Contract schema validity; identity/dedupe stability; no synthesized
  sequence and arrival-order preservation; corpus/redaction exclusion
  with digest verification; unknown-type/status/record typed drops;
  version/provider-model/capability mismatch fail-closed behavior; and
  that provider/model is metadata-only.
- `tests/test_hook_contract_schema.py` (WO-P1-258) remains the authority
  for envelope semantics; this adapter suite must not weaken or duplicate
  its ordering/dedupe authority.

Any change to Hook Contract v1 (dependency SHA or exact blob drift from
`0d4f0c3b36ff7fad9ed14636730443119683cb1d` /
`25f69a964140c082db9d43b65dd3fcd9dbfc0c3c` /
`98451ee3a4b63b4f07ca7b38525f9f5016916d54`) invalidates this
adapter contract until re-pinned and re-reviewed under the governing repair.
