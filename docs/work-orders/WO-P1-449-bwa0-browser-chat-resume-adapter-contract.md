# WO-P1-449 — BWA-0 DEX-3b Browser Chat Resume Adapter Contract

Status: CANDIDATE_READY / POST-MAIN R3 REPAIR / AWAITING EXACT-SHA REREVIEW + CI
Issue: #449
Identity schema: GITHUB_ISSUE_V1
Risk: R3 protocol/schema + replay/dedupe/security trust boundary
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Historical author claim: WO-P1-449-BWA0-CONTRACT-R2-001 (dispatch identity only; risk escalated to R3 before freeze)
Parent roadmap: WO-P1-446 / Issue #446 / merged PR #378
Date: 2026-09-21

## Exact binding

Initial BWA-0 authoring is historical and was merged by PR #451 at
`18b55b11be1558cc931014a9ab604edfaff8f38d`. The current active binding is the
post-main R3 defect-repair lane below; actual Git/GitHub truth supersedes the
initial dispatch binding where they differ.

- repo: `aase7en/A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo449-postmain-r3-repair`
- branch: `fix/wo-p1-449-bwa0-postmain-r3-repair`
- post-main repair base: `18b55b11be1558cc931014a9ab604edfaff8f38d`
- parent merge: PR #451 / `18b55b11be1558cc931014a9ab604edfaff8f38d`
- historical authoring branch: `docs/wo-p1-449-bwa0-browser-chat-resume-contract`
- historical initial dispatch/base: `1d3449c04622fb84a9b36de1963460c7100e2683`
- repair pre-mutation state: clean exact post-main base; Issue #449 remains OPEN;
  repair claim/checkpoint is durable on the Issue; exact tracked scope remains
  the same four WO449 files
- previous dirty repair was transferred by an exact diff with matching SHA-256;
  the historical worktree is preserved and receives no further mutation

## Exact mutable scope (4 tracked files, NEW only)

1. `docs/contracts/browser-chat-resume-adapter-v1.md`
2. `docs/contracts/browser-chat-resume-adapter-v1.schema.json`
3. `tests/test_browser_chat_resume_adapter_contract.py`
4. `docs/work-orders/WO-P1-449-bwa0-browser-chat-resume-adapter-contract.md`

Forbidden (READ-ONLY): every other tracked path, including `src/**`,
SunDayRemoteMCP, MV3/native-host source, production DEX-3a producer,
NEXT_READY/successor selection, `CURRENT-WORK.md`, `handoff.md`,
`COLLAB.md`, live browser/provider configuration, credentials/cookies/
session-token handling, Command-Gateway source, and the legacy identity
fixture. If any fifth tracked file appears modified, work stops and is
reported before further mutation.

## Deliverable

A small versioned DEX-3b adapter contract (not runtime code):
`browser-chat-resume-adapter-v1` with message types `adapter_capability`,
`conversation_binding`, `wake_request`, `browser_response`,
`wake_delivery_status`, `wake_arm_control`, and the separately labeled
`test_only_fake_ingress`. Closed JSON Schema Draft 2020-12
(`urn:a-conductor:schema:browser-chat-resume-adapter:1.0.0`) with a full
field/message-type exclusivity matrix, bounded strings/arrays, a
whole-envelope size rule (SHOULD 16384 / MUST 32768 UTF-8 bytes), pinned
`UNTRUSTED` browser-result trust, and deterministic offline conformance
tests with pure in-file reference algorithms (single-effect wake gate,
response dedupe, delivery follow-up, binding reconciliation, restart
reconcile).

## Authority fences preserved

- Issue #215 exclusively owns automatic accepted-completion ->
  NEXT_READY, successor selection, completion/provenance validation,
  same-tick continuation/reconcile; BWA-0 defines no automatic
  continuation algorithm.
- merged WO433 / PR #441 owns the generic/manual bounded runtime
  activation primitive and authoritative production composition; reuse
  by reference only, no second runtime producer.
- the latest accepted Hook-contract family owns normalized event
  identity/ordering/dedupe vocabulary; BWA-0 reuses it by reference and
  forks no browser event bus.
- DEX-2b control-plane receipt accepted/post-main verified;
  SunDayRemoteMCP DEX-2a anchor is LOCAL-ONLY and proves no production
  DEX-3a delivery; production DEX-3a correlation is UNAVAILABLE until
  separately accepted.
- WO369 owns context/session rollover truth; WO374 owns delegated-lane
  pointer identity; consequential execution controls remain Command
  Gateway authority; Browser Wake is DEX-3b adapter/transport only.

## RED evidence (before schema/contract existed)

- Command: `python -m pytest -q tests/test_browser_chat_resume_adapter_contract.py`
- Result: `5 failed, 11 passed, 77 errors`.
- Cause: genuine missing artifacts — `FileNotFoundError` for
  `docs/contracts/browser-chat-resume-adapter-v1.md` and
  `docs/contracts/browser-chat-resume-adapter-v1.schema.json` (schema
  parse/draft, minimal examples, bounds, forbidden fields, corpus, and
  all contract-text pins fail). No RED was faked by syntax errors or
  intentionally invalid test code: collection succeeded and the 11
  passing tests were pure reference-algorithm ladder checks that do not
  read the artifacts.

## GREEN evidence

- Command: `python -m pytest -q tests/test_browser_chat_resume_adapter_contract.py`
- Result: `93 passed` (deterministic, offline, no network/MCP/browser).
- The adversarial floor of Issue #449 is covered: unknown/malformed
  version rejected with pinned v1 rule; oversize strings/arrays/envelope
  rejected; missing adapter/provider/version/capability rejected;
  capability/readiness separation (CAPABLE/READY/AUTHORIZED/ADMITTED
  never inferred); binding mismatch/stale/unknown typed fail-closed;
  duplicate wake id single-effect; duplicate response no second effect;
  consumed replay rejected; ambiguous delivery never blind-retries;
  TEST_ONLY fake ingress cannot validate as or impersonate production
  DEX-3a; cookie/session/share/credential/argv/Git/pid field matrix
  rejected; fake-secret corpus pinned and excluded; Play/Pause arm-only
  with execution pause/cancel/retry rejected; pointer-only payloads with
  no task-state mutation fields; authority boundaries pinned in text;
  no new scheduler/claim/lease/retry/review/completion/memory/
  model-policy authority; full offline BWA-1 cycle.

## Replay safety / no shadow authority

The contract states and the tests prove: same `wake_event_id`
redelivery authorizes at most one browser/model effect; duplicate
browser responses cause no second downstream effect; consumed event
replay is rejected; transport ambiguity maps to
`WAKE_DELIVERY_UNKNOWN` and reconciles durable receipt/binding before
any resend; no exactly-once global-store claim. The reference
algorithms live only inside the focused test file; no production
module, scheduler, store, claim, lease, retry, review, completion,
memory, or model-policy authority is introduced anywhere.

## Verification battery (author-run, pre-freeze)

- `python -m pytest -q tests/test_browser_chat_resume_adapter_contract.py` -> 93 passed
- `python -m pytest -q tests/test_work_order_identity.py` -> green (identity guard)
- `python -m pytest -q tests/test_hook_contract_schema.py` -> green (related Hook-family regression)
- `git diff --check` -> clean
- strict UTF-8 / zero U+FFFD on all four files -> clean
- added-lines secret-pattern scan -> clean
- `git status --short` -> exactly the four scope files, nothing else

## R3 repair cycle 1 — 2026-09-21

The first current-main-fanned candidate `804e3ae1cc9dea1e55cef6e8baa070894d3e1df7`
received independent GLM-5.3 MAX review PASS with reviewer counts
P0/P1/P2/P3 = 0/0/0/3 and exact-head hosted CI SUCCESS. GPT-5.6 Sol did
not accept it because adversarial probes confirmed two MUST-level contract
inconsistencies:

1. value-level sanitation: legal field shapes could still carry synthetic
   sensitive values / URL-shaped pointer material even though Security §13
   says no conformant envelope may carry them;
2. versioning: prose claimed higher-minor unknown optional fields were ignored
   while the root schema is deliberately closed with `additionalProperties:false`.

The bounded repair preserves the same four-file scope and adds RED-first
coverage plus:

- typed wake reasons (`AGENT_RESULT_READY`, `REVIEW_REQUIRED`, `NEXT_READY`,
  `RECOVERY_REQUIRED`) instead of free-form reason text;
- schema-level URL-scheme rejection on durable pointer/reference fields;
- a mandatory consumer-side value sanitation gate in addition to schema and
  byte-size validation, with the shared fake-secret corpus rejected across
  all legal string/list surfaces;
- coherent closed-schema minor handling: `1.x.y` identifies the v1 family,
  but unknown additive fields fail closed until the newer schema is explicitly
  supported; consumers MUST NOT ignore unrecognized fields.

Repair RED subset: 3 failed / 2 passed before the schema/contract repair.
Repair GREEN subset: 5 passed. Focused Browser Wake contract after repair:
97 passed. Combined related regression after repair: 227 passed
(`test_browser_chat_resume_adapter_contract.py` + work-order identity + Hook
schema). Exhaustive post-main R3 audit reports zero value-level sensitive
surface gaps and zero blocking findings.

## Next gate

GPT-5.6 Sol final R3 adversarial/authority audit -> freeze a NEW exact candidate
SHA -> fresh independent exact-SHA GLM-5.3 MAX R3 rereview focused on the two
repaired trust boundaries plus prior blocking findings, with P0/P1/P2 = 0 ->
new exact-head hosted CI green -> Sol acceptance/expected-head merge and
post-main verification. The author does not merge or self-accept. BWA-1 tracked
implementation starts only after BWA-0 acceptance plus a free mutable WIP slot,
with source placement re-derived from the owner map.
