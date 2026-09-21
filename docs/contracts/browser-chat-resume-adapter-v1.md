# Browser Chat Resume Adapter Contract v1 (BWA-0)

Status: CONTRACT-ONLY FREEZE CANDIDATE — WO-P1-449 / Issue #449
Contract version: 1.0.0
Parent roadmap: WO-P1-446 / Issue #446 / merged PR #378
Machine schema: `docs/contracts/browser-chat-resume-adapter-v1.schema.json`

The key words MUST, MUST NOT, SHOULD, and MAY are to be interpreted as
described in RFC 2119/8174.

## 1. Purpose and authority

This contract freezes the DEX-3b browser/provider adapter semantics
required for a later Native Messaging + MV3 fake-provider implementation
(BWA-1). It defines transport, binding, replay, and security semantics
only. It does not implement Chrome, a native host, live ChatGPT/Gemini
automation, production DEX-3a delivery, or any new control plane, and it
is not runtime code.

Non-negotiable ownership fences (consumed by reference, never
reimplemented here):

- Issue #215 exclusively owns automatic accepted-completion ->
  NEXT_READY continuation, successor selection, completion/provenance
  validation, and same-tick continuation/reconcile. BWA-0 defines no
  automatic continuation algorithm.
- merged WO433 / PR #441 owns the generic/manual bounded runtime
  activation primitive and the authoritative production composition
  (`ParallelReadyNodeContract` composition/reachability). BWA-0 reuses
  it by reference only; there is no second runtime producer.
- The latest accepted Hook-contract family owns normalized event
  identity, ordering, and dedupe vocabulary. BWA-0 reuses that
  vocabulary by reference (identifier formats, at-least-once delivery,
  idempotent consumers, bounded replay windows) and MUST NOT fork a
  browser event bus or a second project-wide event identity.
- DEX-2b control-plane receipt is accepted and post-main verified.
  SunDayRemoteMCP carries an accepted LOCAL-ONLY DEX-2a compatibility
  anchor in the frozen DEX set; that anchor is not public/remote
  production delivery and is not proof of live browser compatibility.
- Production DEX-3a completion-event delivery/correlation is
  UNAVAILABLE until a separately accepted producer seam exists.
- WO369 owns context/session rollover truth; browser new-chat resume
  consumes it unchanged.
- WO374 owns delegated-lane evidence pointer identity; BWA-0 pointers
  reuse that identity discipline without gaining lane authority.
- Consequential execution controls (task/execution pause, cancel,
  retry, recover, reassign) belong to Command Gateway authority. No
  production gateway source is assumed on current main.
- Browser Wake is DEX-3b adapter/transport only.

## 2. Reuse classification

- REUSE: Hook Contract v1 envelope discipline (bounded fields, closed
  schema, RFC 3339 UTC timestamps, typed failure codes, shared
  fake-secret corpus); DEX-2b receipt identity; WO369 rollover and
  WO374 pointer conventions; WO433 runtime activation primitive.
- WRAP: the browser adapter maps provider page/conversation state into
  the message types of this contract without changing task semantics.
- EXTEND: BWA-1 extends existing transport seams (Native Messaging
  host, MV3 extension) to carry these envelopes; it adds no new event
  store.
- REPLACE/NEW: none. A browser-specific event identity need that
  cannot be represented in the accepted Hook family requires a
  separately reviewed Hook-contract extension, not a local fork.

## 3. Message envelope

One message is one JSON object. Required core:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | MUST match `^1\.\d+\.\d+$` (v1 line). |
| `message_id` | string | MUST match `^bwa-[0-9a-f]{32}$` (UUIDv4 hex). Unique within the adapter contract domain. |
| `message_type` | enum | `adapter_capability` \| `conversation_binding` \| `wake_request` \| `browser_response` \| `wake_delivery_status` \| `wake_arm_control` \| `test_only_fake_ingress`. |
| `occurred_at` | string | RFC 3339 UTC only. Offsets are forbidden. |

- The schema is closed: `additionalProperties` is false everywhere, and
  every non-core field is legal only on the message types listed in the
  schema's exclusivity matrix.
- Whole-envelope size: SHOULD be <= 16384 UTF-8 bytes and MUST be
  <= 32768 UTF-8 bytes. Larger envelopes are `BWA_EVENT_OVERSIZED` and
  MUST be rejected typed, never truncated into valid-looking messages.
- Omitted optional fields mean unknown, not absent-of-fact; consumers
  MUST render unknown/omitted as `unknown`, never as derived truth.
- Delivery is at-least-once where durable delivery is used; there is NO
  exactly-once promise and no global dedupe store. Consumers MUST be
  idempotent (Section 8).

## 4. Adapter capability

An `adapter_capability` message carries exact identity: `adapter_id`,
`adapter_version`, `provider_id`, `provider_surface` (`web_chat` only in
v1), the exact browser adapter `contract_version` (a `1.x.y` of this
contract the adapter implements), bounded `capabilities` tokens, and
`capability_version`.

Capability is a transport fact, not permission. The states `CAPABLE`,
`READY`, `AUTHORIZED`, and `ADMITTED` are distinct dimensions governed
by existing admission seams (provider/runtime admission, leases,
claims). A consumer MUST NOT infer any later state from an earlier one:
a CAPABLE adapter is not thereby READY, a READY adapter is not thereby
AUTHORIZED, and an AUTHORIZED adapter is not thereby ADMITTED. This
contract defines no readiness field and grants no admission.

## 5. Conversation binding

A `conversation_binding` message carries a non-secret,
non-authoritative provider locator triple (`project_locator`,
`conversation_locator`, `binding_generation`, `binding_version`) plus
`adapter_id`/`provider_id` identity and bounded `observed_evidence`
pointers.

- Locators are opaque provider-side identifiers. They are not
  authority: actual durable task/execution truth always outranks the
  binding projection.
- Locators MUST NOT be or contain URLs, cookies, or session material;
  the locator grammar forbids scheme, slash, and `=` characters, so a
  share URL or cookie value can never be a legal locator value.
- Reconciliation against the durable binding record is typed and
  fail-closed. The only legal outcomes are:
  - `BINDING_MATCH` — identity and generation match exactly;
  - `BINDING_MISMATCH` — adapter/provider/conversation identity
    differs, or the observed generation is ahead of the durable record
    (drift is never guessed or absorbed);
  - `BINDING_STALE` — the observed generation is behind the durable
    record;
  - `BINDING_UNKNOWN` — required evidence is missing.
  Mismatch, stale, and unknown bindings fail closed; a binding outcome
  is never guessed, defaulted, or upgraded from partial evidence.
- Binding messages carry no wake/response/delivery vocabulary.

## 6. Wake request

A `wake_request` message asks a bound adapter/conversation to surface a
bounded continuation prompt to the human-operated browser chat.

- `wake_event_id` (`^bwk-[0-9a-f]{32}$`) is the exact wake identity
  used for dedupe and replay control (Section 8).
- Content is pointers only: at least one of `goal_ref`, `task_ref`,
  `work_order_ref` MUST be present, plus typed `reason`, bounded
  `evidence_refs`, and `requested_next_decision`
  (`PROPOSE_CONTINUATION` | `AWAIT_OPERATOR_DECISION`). `reason` is
  closed to `AGENT_RESULT_READY` | `REVIEW_REQUIRED` | `NEXT_READY` |
  `RECOVERY_REQUIRED`; it is event context only and grants no successor
  selection or continuation authority. Copied task truth, task state,
  free-form prompt text, or executable content is forbidden.
- `source_event_ref` correlates the wake to an accepted source event
  only when one is available (for example an accepted DEX-2b receipt
  pointer or a normalized Hook event identifier). It is a pointer, never
  a payload copy, and it grants no authority. Production DEX-3a
  correlation is UNAVAILABLE (Section 10).
- Transport delivery identity/counters (`delivery_attempt` on the
  delivery status message) are transport metadata only and MUST NOT
  become task attempt or retry authority; retry authorization stays
  with existing A-Conductor reconciliation seams.

## 7. Browser proposal and result

A `browser_response` message reports what the adapter observed in the
browser conversation after a wake.

- `wake_event_id` provides exact request correlation; the response also
  repeats `adapter_id`, `provider_id`, `conversation_locator`, and
  `binding_generation` so the response is checkable against the bound
  context.
- `response_capture_id` (`^bwr-[0-9a-f]{32}$`) identifies the capture
  event and drives response dedupe (Section 8).
- `observed_completion_state`
  (`RESPONSE_OBSERVED` | `RESPONSE_PARTIAL` | `RESPONSE_ABSENT` |
  `RESPONSE_UNKNOWN`) is an observation of the provider page, not a task
  state.
- `proposal_refs`/`result_refs` are bounded pointers to captured
  proposal/result artifacts; they are not content copies.
- `trust_state` is fixed `UNTRUSTED` by the schema: a browser result
  remains UNTRUSTED until A-Conductor re-reads and revalidates current
  durable authority. A browser result cannot declare task acceptance or
  completion as authority; there is no legal trust-bearing value, and
  no acceptance/completion field exists on any message type.

## 8. Dedupe, replay, and restart

- The same `wake_event_id` redelivery authorizes at most one
  browser/model effect. The first delivery of a wake id authorizes the
  effect; any later delivery of the same id is rejected as
  `WAKE_EVENT_ALREADY_CONSUMED`. Consumed event replay is rejected
  outright.
- A duplicate browser response (same `response_capture_id`) cannot
  cause a second downstream effect; it is dropped typed
  (`DUPLICATE_RESPONSE_DROPPED`-class outcome).
- Transport ambiguity maps to `WAKE_DELIVERY_UNKNOWN` (Section 9) and
  never to a blind retry.
- Restart/reconnect reconciles the durable receipt set and the binding
  outcome before any resend: a wake id with a durable receipt is
  already consumed; a non-`BINDING_MATCH` outcome requires binding
  reconciliation first; only a reconciled, unreceipted wake may be
  resent.
- No exactly-once global-store claim is made or implied; the reference
  algorithms in the conformance test are bounded, deterministic, and
  own no durable state beyond their scope.

## 9. Delivery states and failure vocabulary

- `WAKE_DELIVERY_CONFIRMED` — the adapter confirmed delivery to the
  bound conversation; the consumer may await a browser response.
- `WAKE_DELIVERY_FAILED` — delivery failed; any reschedule is allowed
  only after binding reconciliation.
- `WAKE_DELIVERY_UNKNOWN` — transport ambiguity (timeout, disconnect,
  unknown page state). The consumer MUST NOT blind retry: it holds and
  reconciles durable receipt/binding state first (Section 8). The bounded
  reference-consumer decision is `HOLD_RECONCILE_NO_RESEND`; this is an
  adapter decision result only, not a new durable task/retry state.
- Envelope-level failures reuse the Hook-family typed style:
  `BWA_EVENT_INVALID`, `BWA_EVENT_OVERSIZED`, `BWA_VERSION_UNSUPPORTED`,
  `BWA_ADAPTER_UNAVAILABLE`. Validation/transport failures degrade the
  browser wake path only; they MUST NOT rewrite task truth and MUST NOT
  block otherwise-safe execution elsewhere.
- Transport failure is not execution failure.

## 10. DEX boundary and TEST_ONLY fake ingress

- Production DEX-3a completion-event delivery/correlation is explicitly
  UNAVAILABLE/TBD until a separately accepted producer seam exists.
  `source_event_ref` may reference only accepted durable sources that
  already exist (DEX-2b receipts, normalized Hook events); it MUST NOT
  be populated from an unaccepted or hypothetical producer.
- BWA-1 deterministic tests use a separately labeled TEST_ONLY fake
  ingress: `message_type` `test_only_fake_ingress` with required
  `test_only: true`, `fake_source_kind: "FAKE_INGRESS"`,
  `fake-` prefixed `fake_provider_id`, `fake_conversation_locator`,
  `fake_binding_generation`, and `fake_trigger_kind`.
- The fake ingress is structurally disjoint from production vocabulary:
  it cannot carry `source_event_ref`, `wake_event_id`, or any
  production correlation field, and production-typed messages cannot
  carry any `test_only`/`fake_*` field. The fake ingress MUST NOT
  validate as, impersonate, or be accepted as a production DEX-3a
  event/source/authority. Passing fake-ingress tests proves transport,
  binding, restart, and dedupe mechanics only.

## 11. Play and Pause

- `PLAY` arms future automatic browser wake delivery for the bound
  adapter/conversation.
- `PAUSE` disarms future automatic browser wake delivery.
- Neither value mutates active execution: a conformant consumer MUST
  NOT use Play or Pause to suspend, kill, cancel, retry, or otherwise
  control any active execution, model, worker, or task. `arm_command`
  is wake-arm state only; execution pause, cancel, retry, recover, and
  reassign values, fields, or semantics are rejected by the schema and
  remain outside BWA-0/BWA-1 under Command Gateway authority.

## 12. Versioning and compatibility

- Producers MUST pin an exact `schema_version` they conform to.
  Additive optional fields require a minor bump; core changes,
  removals, or semantic changes require a major bump.
- Consumers recognize `1.x.y` as the v1 schema family, but recognition
  is not blanket forward compatibility. A consumer validates against
  its exact known closed schema and MUST NOT ignore unrecognized fields.
  A higher producer minor may validate only when its payload remains
  entirely inside the consumer's known closed vocabulary; unknown
  additive fields are `BWA_EVENT_INVALID` until that newer schema is
  explicitly supported. A different major is a typed reject
  `BWA_VERSION_UNSUPPORTED` with no silent fallback, and an
  unparseable/schema-invalid message is `BWA_EVENT_INVALID` (drop; the
  consumer MUST NOT crash).
- The v1 compatibility rule is pinned here: only `1.x.y` versions are
  v1-family versions; `0.x`, `2.x`, partial, or prefixed versions are
  never silently coerced into v1. Closed-schema fail-closed behavior
  always outranks convenience forward parsing.

## 13. Security

- DOM/page/browser output is hostile and untrusted. It is sanitized
  into bounded pointers/observations and never executed.
- No cookie, session token, credential, or share URL may be exported,
  scraped, persisted, or relayed by any conformant implementation.
  Forbidden fields (schema-closed): `prompt`, `messages`, `transcript`,
  `token`, `api_key`, `apikey`, `secret`, `secret_value`, `password`,
  `credential`, `credential_value`, `cookie`, `session_token`,
  `share_url`, `session_url`, `argv`, `command_line`, `shell_command`,
  `git_operation`, `pid`. There is no legal secret-carrying envelope in
  v1.
- Schema validity alone is not full v1 conformance. After schema
  validation and the whole-envelope byte gate, every consumer MUST run
  a value-level sanitation gate before accepting the envelope. The gate
  recursively inspects string/list values and returns `BWA_EVENT_INVALID`
  if a shared `fake-secret-corpus/1` value is present, if URL-shaped
  material containing `://` appears anywhere in v1, or if a value matches
  the accepted adapter secret-shape profile: token-like prefixes (`sk-`,
  `ghp_`, `xoxb-`, `AKIA`, `Bearer `), private-key headers, or
  session/share markers. This reuses the accepted Claude Hook adapter
  security-invalid destination pattern instead of inventing a second
  redaction vocabulary. v1 defines no URL field. This is a bounded validation
  step only, not a credential store, redaction authority, or browser-content
  parser.
- Pointer/reference fields additionally reject URL-scheme shapes in the
  JSON Schema itself while preserving local durable refs such as
  `runs/...` and normalized colon-delimited event identities.
- No raw prompt/transcript credential envelope exists; `reason` is a
  typed enum rather than free text, and all remaining string values are
  bounded plus subject to the mandatory sanitation gate.
- No direct Git, process, filesystem, or task mutation fields exist;
  DOM/page observations grant no such authority.
- Native Messaging is a future BWA-1 transport choice, not implemented
  here, and inherits every rule of this section plus the Hook-family
  localhost browser boundary (explicit Origin validation and local
  authentication before serving data).
- Provider terms/quota restrictions cannot be evaded by this contract
  or any conformant implementation.
- Shared fake-secret corpus `fake-secret-corpus/1` (not secret; used
  uniformly by redaction/adapter tests):
  - `sk-FAKE0000000000000000000000000000000000`
  - `ghp_FAKE0000000000000000000000000000000`
  - `xoxb-FAKE-000000000000000000000000`
  - `AKIAFAKE0000000000`
  - `FAKESESSIONCOOKIE=0000000000000000`
  - `-----BEGIN FAKE PRIVATE KEY-----`
  - `https://chat.example/FAKE/share/0000`
  - `Bearer FAKE000000000000000000000000000`
  No corpus item may appear in any conformant message, pointer, or
  free-text field.

## 14. Authority fence

BWA-0 adds no new authority of any kind: no new scheduler, task
router, claim store, lease authority, retry policy, review lifecycle,
completion/acceptance authority, memory store, or model-policy store.
Automatic successor selection stays with Issue #215; runtime activation
stays with WO433; event identity stays with the Hook family; rollover
stays with WO369; lane pointers stay with WO374; receipts stay with
DEX-2b; consequential commands stay with the Command Gateway. If a
browser-side need appears to require any of these authorities, the
correct action is a reviewed extension of the owning contract, never a
local browser-side implementation.

## 15. BWA-1 offline usability

The whole contract is usable by BWA-1 fake-provider tests with no live
browser, no network, no MCP, and no provider account: the
`test_only_fake_ingress` vocabulary drives deterministic wake/response/
delivery cycles, and the reference algorithms (single-effect wake gate,
response dedupe, delivery follow-up, binding reconciliation, restart
reconcile) are pure and deterministic. Passing those tests proves
transport, binding, replay, and restart mechanics only; it does not
claim live autonomous continuation or live browser compatibility.

## 16. Conformance and tests

Deterministic conformance is
`tests/test_browser_chat_resume_adapter_contract.py` (schema
parse/draft/closedness; minimal valid examples for every message type;
core/identity format enforcement; type exclusivity; typed version
rejection with the pinned v1 rule; string/array/envelope bounds;
missing capability identity rejection; capability/readiness separation;
fail-closed binding reconciliation including URL/cookie locator
rejection; single-effect wake dedupe; at-least-one durable pointer;
transport counter non-authority; duplicate response drop; consumed
replay and restart reconcile; ambiguous delivery never blind-retries;
TEST_ONLY fake-ingress isolation; forbidden field matrix; mandatory
value-level sanitation across all strings/lists, including accepted
adapter secret-shape markers; URL-shaped pointer rejection; typed wake
reasons; fake-secret corpus pinning and exclusion;
strict closed-schema higher-minor handling; Play/Pause arm-only semantics;
pointer-only payloads with pinned UNTRUSTED trust; pinned authority
boundaries; authority-fence vocabulary; and the offline BWA-1 cycle).
No network, no MCP, no live browser, and no production runtime is
added by this contract.
