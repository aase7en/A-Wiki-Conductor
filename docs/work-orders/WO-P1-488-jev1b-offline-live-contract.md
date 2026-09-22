# WO-P1-488 — JEV-1B offline live-contract readiness

Status: ACTIVE / R2 / OFFLINE_ONLY
Issue: #488
Parent: #484 / JEV-1
Topology: CONTROL_PLANE_ONLY
Reuse classification: EXTEND JEV-1A (#486 / PR #487)

## Lane binding

- Authority/execution repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo488-jev1b`
- Branch: `feat/wo-p1-488-jev1b-offline-live-contract`
- Base/current at claim: `8aa21157a8e0bb1fa0a76bbcbecc73410ae3db5f`
- Claim: Issue #488 comment #5781697837
- Owner/integrator: GPT-5.6 Sol
- Global mutable WIP at claim: #480 dirty candidate + #482 dirty candidate + #488 = 3

## Goal

Prepare the exact TypeSafe System One request/response contract and a larger sanitized benchmark corpus so that, after credential rotation, the first live Jev benchmark requires only a bounded transport/smoke slice rather than new design work.

This slice is offline-only. It never reads credentials and never opens a network connection.

## Current official TypeSafe contract evidence — refreshed 2026-09-23

Official live docs were refreshed before implementation:

- endpoint: `POST https://api.typesafe.ai/v1/systemone`;
- request body: `state`, `model`, `questions`;
- question types: `choice`, `score`, `noul`;
- Choice: required criteria map, max 255 options;
- Score: required ordered criteria, 2..10 levels;
- Noul: optional true/false criteria;
- response: exact versioned `model`, `answers` map, `usage.input_tokens`, `usage.output_tokens`;
- Choice response: `choice`, `confidence`, `probabilities`;
- Score response: `score`, `confidence`, `probabilities`, `legend`;
- Noul response: `noul` only; no invented confidence requirement;
- stable model observed: `jev-1.13.0`;
- documented current input price: USD 0.042 / 1M input tokens; output free;
- aliases currently point to Jev 1.13 but may move, so benchmark requests pin `jev-1.13.0`;
- API errors documented: 401, 422, 429 and 529; live retry behavior is later transport scope.

Model/pricing evidence must be refreshed again immediately before live admission because vendor limits/pricing/aliases can change.

## Allowed scope

- NEW `docs/work-orders/WO-P1-488-jev1b-offline-live-contract.md`
- NEW `scripts/jev_typesafe_contract.py`
- NEW `tests/test_jev_typesafe_contract.py`
- NEW `tests/fixtures/jev_shadow/cases-expanded.jsonl`
- NEW `tests/fixtures/jev_shadow/typesafe_questions.json`
- bounded MODIFY `tests/test_jev_shadow_benchmark.py` only if shared harness coverage strictly requires it

No `src/a_conductor/**` mutation.

## Contract layer

`scripts/jev_typesafe_contract.py` must be pure and network-free.

Responsibilities:
1. load/validate family-level TypeSafe question specs;
2. validate each benchmark case is compatible with its question spec;
3. build one deterministic `/v1/systemone` JSON request body per case;
4. require a versioned benchmark model ID and reject moving aliases for benchmark admission;
5. normalize one successful Choice/Score/Noul response into the existing JEV-1A `ProviderResult`;
6. validate response model identity, answer type, answer space, probabilities/confidence and usage;
7. compute cost only from an explicitly supplied input-token price;
8. emit a deterministic safe JSONL request manifest for later live execution;
9. never include expected answers in the request body.

The module must not:
- import network clients;
- read environment variables;
- read `TYPESAFE_API_KEY`;
- perform retries;
- perform HTTP;
- decide production routing.

## Expanded corpus

Create 60 sanitized/public synthetic cases: 10 each for:
- `task_classification`;
- `skill_suggestion`;
- `failure_classification`;
- `review_severity`;
- `evidence_relevance`;
- `escalation_decision`.

Requirements:
- unique stable IDs;
- no private project/user payload;
- states contain text-only leaves;
- expected truth is defensible from the case wording;
- choice answer spaces are fixed per family and match TypeSafe criteria exactly;
- Score uses a frozen ordered rubric;
- Noul policies keep binary truth separate from review-band escalation;
- risk classes are mixed;
- corpus contains both easy and boundary-like wording but no intentionally ambiguous case whose expected truth cannot be defended.

This corpus is benchmark input, not production training data.

## Frozen family question specs

### task_classification / Choice

Options:
- `bugfix` — restore broken/regressed existing behavior;
- `feature` — add a new product capability or behavior;
- `docs` — documentation/governance-only change;
- `review` — inspect/evaluate an existing candidate without implementing it.

### skill_suggestion / Choice

Options:
- `repo_semantic` — repository code/symbol/reference navigation;
- `pdf` — PDF creation/edit/analysis workflow;
- `slides` — presentation/slide workflow;
- `spreadsheet` — workbook/data-table workflow;
- `none` — no specialized skill above is needed.

### failure_classification / Choice

Options:
- `CODE_FAILURE`
- `TEST_FAILURE`
- `TRANSPORT_FAILURE`
- `RATE_LIMITED`
- `AUTH_FAILURE`

### review_severity / Score

Four ordered levels:
0. no material defect;
1. minor/P3 hardening or clarity issue;
2. material/P2 defect requiring repair before acceptance;
3. critical/P1/P0 safety/authority/data-loss/security defect.

### evidence_relevance / Noul

Probability that the supplied evidence directly supports the stated claim.

### escalation_decision / Noul

Probability that deterministic/local handling is insufficient and the case should escalate to stronger reasoning/integrator/human review because authority, risk, ambiguity or evidence is unresolved.

## Verification

Targeted:
- `python -m pytest tests/test_jev_typesafe_contract.py tests/test_jev_shadow_benchmark.py -q`
- request-manifest CLI generation over all 60 expanded cases;
- deterministic repeated manifest equality;
- `py_compile`;
- `git diff --check`;
- UTF-8/U+FFFD scan;
- committed-content credential/session-URL scan;
- static forbidden-import/read scan for network/environment/key access.

## Acceptance

R2 acceptance requires:
- all targeted tests green;
- 60/60 corpus cases build valid pinned-model requests;
- all three answer primitives normalize correctly;
- malformed response/model/usage/question mismatches fail closed;
- no network/key/environment read path exists;
- exact allowed-file scope;
- independent read-only review if required by current policy;
- hosted CI before merge;
- post-main verification.

## Security blocker for successor live slice

At claim time the approved private secret store still contains the same TypeSafe API key that was previously pasted into chat. Presence is not sufficient; that credential is treated as exposed.

`LIVE_JEV_ALLOWED = NO`

Successor live work requires:
1. key revoked/rotated by an authorized human;
2. secret-safe hash check proving the binding differs from the exposed key without printing it;
3. fresh TypeSafe model/pricing/limits docs refresh;
4. only sanitized/public corpus payloads;
5. bounded live smoke before the full benchmark.

## Checkpoint — offline implementation complete

- [2026-09-23] Official TypeSafe live docs refreshed for Quickstart, HTTP API, Python API index, and Models before implementing the offline contract.
- [2026-09-23] Added a pure request/response contract module with pinned `jev-1.13.0` model identity, Choice/Score/Noul mapping, exact answer/model/usage validation, explicit input-token price accounting, and deterministic manifest emission.
- [2026-09-23] Added 60 sanitized cases: 10 per decision family, plus six frozen family question specs.
- [2026-09-23] Targeted verification: `49 passed`.
- [2026-09-23] Manifest CLI: 60/60 records, repeated output SHA-identical.
- [2026-09-23] `py_compile`, `git diff --check`, UTF-8/U+FFFD, secret/session-URL scan, and static forbidden network/environment/process surface scan: PASS.
- [2026-09-23] No live TypeSafe call and no credential read occurred. Live gate remains blocked because the secret-store binding has not been rotated away from the credential previously exposed in chat.

## Next safe action

Implement the pure contract module, balanced corpus, and deterministic tests only inside this allowlist.