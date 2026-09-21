# WO-P1-449 — BWA-0 DEX-3b Browser Chat Resume Adapter Contract

Status: R3_REPAIR_CYCLE_3_COMPLETE / PRE-FREEZE
Issue: #449
Identity schema: GITHUB_ISSUE_V1
Risk: R3 protocol/schema + replay/dedupe/security trust boundary
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Historical author claim: WO-P1-449-BWA0-CONTRACT-R2-001 (dispatch identity only; risk escalated to R3 before freeze)
Parent roadmap: WO-P1-446 / Issue #446 / merged PR #378
Date: 2026-09-21

## Exact binding

Initial BWA-0 authoring was merged by PR #451 at
`18b55b11be1558cc931014a9ab604edfaff8f38d`. Post-main repair cycle 1 was
merged by PR #455 at `3db441f3aa2ec7ef3a7f41ce98d41df047b72a3c`.
A later deterministic Sol probe found the cycle-2 credential-shape security
gap, so the current active binding is the post-PR-455 repair lane below.
Actual Git/GitHub truth supersedes earlier acceptance checkpoints where they
conflict with this later finding.

- repo: `aase7en/A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo449-secretshape-repair`
- branch: `fix/wo-p1-449-bwa0-secret-shape-postmain`
- post-main repair base: `3db441f3aa2ec7ef3a7f41ce98d41df047b72a3c`
- parent merge: PR #455 / `3db441f3aa2ec7ef3a7f41ce98d41df047b72a3c`
- historical cycle-1 worktree:
  `A:\GitHub\_worktrees\A-Wiki-Conductor-wo449-postmain-r3-repair`
- historical cycle-1 candidate: `5550f14d6a652722085a4ce7a7858c718f7e2108`
- historical authoring branch: `docs/wo-p1-449-bwa0-browser-chat-resume-contract`
- historical initial dispatch/base: `1d3449c04622fb84a9b36de1963460c7100e2683`
- cycle-2 pre-mutation state: clean exact post-PR-455 main; Issue #449 remains
  the durable repair authority; exact allowed tracked scope remains the same
  four WO449 files
- cycle-2 patch was transferred from the preserved historical worktree with
  exact diff SHA-256
  `3e67c05f7c076965dedb5aa5292e2107bac2ddd8eb2bc1e57f7245768ac18921`;
  source and applied diff hashes matched exactly
- the historical dirty worktree is preserved and receives no further mutation

## Exact mutable scope (4 tracked files; bounded modification only)

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

## R3 repair cycle 2 — 2026-09-21

Candidate `5550f14d6a652722085a4ce7a7858c718f7e2108` received a fresh
independent GLM-5.3 MAX rereview PASS with reviewer counts P0/P1/P2/P3 =
0/0/0/3 and exact-head hosted CI SUCCESS. Sol did not accept that result
because a fresh deterministic probe covered credential-shaped values outside
the exact `fake-secret-corpus/1`.

The probe injected synthetic non-secret values shaped like real credential
families (for example `sk-proj-`, `ghp_`, `xoxb-`, and `AKIA`) into
schema-legal string/list surfaces. The existing full conformance gate accepted
the first credential-shaped probe across 21 legal destinations, contradicting
Security §13's MUST-level prohibition on credential relay.

The repair reuses the accepted Claude Hook adapter security-invalid destination
pattern rather than inventing a second secret vocabulary:

- token-like prefixes `sk-`, `ghp_`, `xoxb-`, `AKIA`, `Bearer `;
- private-key header markers;
- session-cookie and share markers;
- the exact shared `fake-secret-corpus/1`;
- the existing v1 URL-shape rejection.

RED evidence before this repair:
`test_noncorpus_secret_shapes_rejected_everywhere` failed on
`conversation_binding.project_locator = sk-proj-SYNTHETIC...` because the
full gate returned `BWA_EVENT_VALID`.

GREEN evidence after the bounded repair:

- new targeted test: 1 passed;
- focused BWA-0 contract: 98 passed;
- BWA-0 + work-order identity + Hook schema: 228 passed;
- read-only prototype of the reused marker policy: zero minimal-message false
  positives and zero synthetic secret-shape gaps.

The repair remains contract/test-only inside the existing WO449 scope. No
runtime, browser, MV3, Native Messaging, provider, scheduler, NEXT_READY,
Command-Gateway, DEX-3a, Git/process/filesystem, or secret-store authority is
added.

## R3 repair cycle 3 — 2026-09-21

Candidate `d2cc2c4de898cb3b00c9f2ef0957999a65721449` had exact-head hosted
CI SUCCESS across Windows, Ubuntu, and macOS, but the independent MAX run did
not satisfy the acceptance packet: it returned a static/plan-oriented
preliminary PASS direction while explicitly leaving the required dynamic probe
matrix unexecuted. Its review worktree also gained reviewer-generated untracked
`.kilo/` plan material, so that run is retained as advisory evidence only.

Both the reviewer static analysis and a separate frozen-SHA Sol probe found the
same semantic defect in cycle 2: the helper used case-folded substring matching
for secret markers while the contract described token-like prefixes and
claimed direct reuse of the accepted Claude Hook profile. Deterministic
harmless-value injection found 100 schema-valid placements rejected only
because an incidental substring matched, including examples such as
`project-sk-alpha`, `MakiaProject`, and `runs/share/result.json`.

Cycle 3 narrows the value gate to credential-bearing positions while preserving
the MUST-level no-secret boundary:

- token families are matched only at the start of the value:
  `sk-`, `ghp_`, `xoxb-`, `AKIA`, `Bearer `;
- private-key material is matched as an actual leading private-key header shape;
- session/cookie material is matched as an assignment-like leading prefix such
  as `sessionid:` or `cookie=`;
- any `://` URL shape remains invalid, so share URLs stay blocked;
- exact `fake-secret-corpus/1` items remain invalid;
- incidental marker substrings and local paths are not secrets by shape alone.

RED evidence before cycle-3 repair:
`test_harmless_marker_substrings_remain_conformant` failed on
`adapter_capability.adapter_id = project-sk-alpha` because the cycle-2 gate
returned `BWA_EVENT_INVALID`.

GREEN evidence after cycle-3 repair:

- harmless-marker targeted test: 1 passed;
- non-corpus secret-shape targeted test: 1 passed;
- focused Browser Wake contract: 99 passed;
- Browser Wake + work-order identity + Hook schema: 229 passed;
- read-only precise-gate prototype: 49/49 synthetic security probes rejected
  and 100/100 harmless schema-valid marker probes accepted.

This repair remains bounded to the same WO449 contract/work-order/test scope and
adds no runtime or execution authority.

## Next gate

GPT-5.6 Sol final R3 adversarial/authority audit -> freeze a NEW exact candidate
SHA -> fresh independent exact-SHA GLM-5.3 MAX focused rereview of repair cycle
2, with P0/P1/P2 = 0 -> new exact-head hosted CI green -> Sol
acceptance/expected-head merge and post-main verification. The author does not
merge or self-accept. BWA-1 tracked implementation starts only after repaired
BWA-0 acceptance plus a free mutable WIP slot, with source placement re-derived
from the owner map.
