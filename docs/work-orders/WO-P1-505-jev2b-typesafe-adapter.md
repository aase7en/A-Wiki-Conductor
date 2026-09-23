# WO-P1-505 — JEV-2B TypeSafe semantic provider adapter

Status: AUTHOR PHASE COMPLETE / R3 / CONTROL_PLANE_ONLY
Parent: Issue #501
Issue: #505
Dependency: #502 (accepted semantic decision core) — COMPLETE/CLOSED/POST_MAIN_VERIFIED on this base
Dispatch HEAD: `19ee92ca3888ce563ac743cfcca7707334cc8189`
Branch: `feat/wo-p1-505-typesafe-semantic-provider`

## Goal

Implement the minimal live TypeSafe/Jev provider adapter behind the accepted
provider-neutral `SemanticDecisionProvider` seam from #502. The adapter is
callable and safely normalized; it does not enable automatic routing.
Jev/TypeSafe evidence remains structurally non-authoritative for
task/claim/mutation/review/merge/completion decisions.

## Allowed scope (exact)

- `docs/work-orders/WO-P1-505-jev2b-typesafe-adapter.md`
- `src/a_conductor/typesafe_semantic_provider.py` (NEW)
- `tests/test_typesafe_semantic_provider.py` (NEW)

Everything else read-only. Verified: dirty scope after author phase is
exactly the two new source paths plus this document; no tracked file changed.

## Adapter design

`TypeSafeSemanticDecisionProvider.evaluate(request)` performs, in order:

1. request type guard (non-`SemanticDecisionRequest` -> typed SCHEMA
   evidence, never raises across the boundary);
2. credential resolution at the call boundary only, from an injected
   resolver matching the accepted A-Wiki environment resolver surface
   (`resolve("secret-ref:awiki-env/TYPESAFE_API_KEY")`); absence, empty,
   oversized or control-character credentials -> typed AUTH evidence and no
   transport call; the value is used only in the `Authorization` header and
   is never persisted, logged or returned;
3. deterministic request body `{state, model, questions.decision}` built
   from the already-sanitized bounded core state (frozen mappings/tuples
   converted to plain JSON), pinned versioned model and an explicit
   per-primitive question (choice: criteria map from declared options;
   score: ordered level criteria; noul: no criteria). No policy metadata
   (min_confidence/decision_threshold/review_band) is sent to the provider;
4. bounded-size gate: serialized request > 256 KiB -> typed SCHEMA evidence
   without a transport call;
5. exactly one `transport.post(...)` through the injected
   `TypeSafeTransport` boundary (`TypeSafeHTTPRequest`: pinned
   `https://api.typesafe.ai/v1/systemone`, Bearer/Content-Type/Accept
   headers, bounded timeout). No internal retry; ambiguous outcomes are
   never blind-replayed by this adapter;
6. outcome normalization into `SemanticEvidence`
   (`authoritative_for_action=False` structurally):
   - transport exceptions -> TIMEOUT (incl. nested `URLError(TimeoutError)`),
     TRANSPORT (OSError family) or UNKNOWN;
   - HTTP 401/403 -> AUTH, 429 -> RATE_LIMIT, 422 -> SCHEMA,
     529/5xx -> OVERLOAD, anything else -> UNKNOWN; error details carry the
     status only, never the body;
   - 200 responses are normalized under the JEV-1C strict contract: exact
     top-level fields, pinned-model identity, exact usage fields,
     exactly the requested question id, exact per-primitive answer fields,
     confidence/probabilities finite/in-range/exact-keys/sum-1, score
     legend shape, noul bareness; malformed JSON/shape, model mismatch and
     invalid measurements -> typed SCHEMA evidence;
   - answers outside the declared option/level/probability space pass
     through unmodified so the accepted #502 core escalates them
     (`EVIDENCE_ANSWER_INVALID` family) — the adapter normalizes, the core
     decides.

`UrllibTypeSafeTransport` (stdlib, bounded reads, HTTP-error bodies
surfaced as responses) exists for the later live gate; unit tests are
network-free by injected fake transport.

Reuse: `semantic_decision` vocabulary/envelope/error kinds (#502),
JEV-1B/JEV-1C endpoint/model/field/error contracts, the existing
secret-reference resolver surface. No new secret store, registry,
scheduler, claim state or routing surface.

## Verification (author phase)

- RED-first: `tests/test_typesafe_semantic_provider.py` reproduced
  `ModuleNotFoundError` before implementation existed.
- `python -m pytest tests/test_typesafe_semantic_provider.py -q` ->
  91 passed.
- Regression: `python -m pytest tests/test_semantic_decision.py
  tests/test_jev_shadow_benchmark.py tests/test_jev_typesafe_contract.py
  -q` -> 135 passed.
- `python -m compileall` on both changed Python paths: OK.
- `git diff --check`: clean.
- Dirty-scope audit: only the two NEW files (plus this doc); no tracked
  file modified.
- Added-line secret/session scan (apikey_/sk-/Bearer/credential-shape):
  no matches.

## Live smoke

Not attempted (normally NO for author phase). WO-P1-488 records
`LIVE_JEV_ALLOWED = NO` pending credential rotation, so no live TypeSafe
call and no credential read occurred in this slice.

## Known risks / remaining gates

- The real `UrllibTypeSafeTransport.post` path and live model/pricing
  drift are unverified until the R3 live-smoke gate opens (credential
  rotation + refreshed WO-P1-488 evidence required first).
- Score `legend` and any provider-side retry behavior are validated
  off-contract only; live drift would surface as typed SCHEMA evidence.
- Remaining R3 gates: independent review of the exact frozen SHA,
  hosted CI on that head, integrator accept/merge, then (later, separate
  authorization) the bounded live smoke against synthetic/public corpus
  only.
- No A-Faster routing, #498/#500 files, MCP descendants, global env
  mutation, commit/push/merge in this slice.

## Result

safe-to-freeze: YES — dirty scope is exactly the three allowed paths,
all deterministic gates pass, and the slice contains no live I/O.
