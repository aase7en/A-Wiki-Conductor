# WO-P1-508 — JEV-4 held-out confidence cascade

Status: ACTIVE / R3 / CONTROL_PLANE_ONLY
Issue: #508
Parent: #501
Dependency: #505 COMPLETE / POST_MAIN_VERIFIED / LIVE_SYNTHETIC_SMOKE_PASS

## Lane binding

- Authority/execution repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo508-jev4-heldout`
- Branch: `feat/wo-p1-508-jev4-heldout-cascade`
- Current integration base after recovery: `441e550d9d85f671eee60f1e89fdb9d1cb8fcc90`
- Mutable scope:
  - `docs/work-orders/WO-P1-508-jev4-heldout-confidence-cascade.md`
  - `scripts/jev_confidence_cascade.py`
  - `tests/test_jev_confidence_cascade.py`
  - `tests/fixtures/jev_shadow/cases-heldout-v1.jsonl`

Everything else is read-only.

## Purpose

JEV-4 determines whether any of the five already accepted semantic families have
enough held-out evidence for a narrow SHADOW/ADVISORY confidence policy. It does
not enable automatic routing, mutation, claim, review, merge, completion, or
human-replacement authority.

Families under test:

1. `task_classification` — Choice
2. `skill_suggestion` — Choice
3. `failure_classification` — Choice
4. `evidence_relevance` — Noul
5. `escalation_decision` — Noul

`review_severity` / Score remains frontier-only and is deliberately excluded.

## Recovery provenance

Author attempt-0001 was terminal with exit 0 but made no tracked progress.
Author attempt-0002 reached RED-first implementation and wrote only
`tests/test_jev_confidence_cascade.py`; its runner/supervisor disappeared
without `exit.json` or `result.md`, leaving a stale RUNNING pointer and no
live owner process.

After exact process/session/Git reconciliation, blind GLM replay was stopped.
GPT/Worker takeover continues the same claim and exact mutable scope. The partial
RED test was preserved; no reset/clean/stash was used.

Deterministic RED before implementation:

`ModuleNotFoundError: No module named 'jev_confidence_cascade'`

## Held-out corpus

`cases-heldout-v1.jsonl` contains exactly 50 new sanitized/public English
cases: 10 per family, split into exactly 5 calibration and 5 validation cases.

Constraints:

- no exact normalized-state overlap with `cases.jsonl` or
  `cases-expanded.jsonl`;
- no private hospital/pharmacy/estate/user/chat payload;
- no secret-shaped value;
- Choice options exactly match the accepted
  `typesafe_questions.json` templates;
- Noul expected values are boolean;
- no Score / review_severity;
- validation cases never participate in threshold selection.

Thai/domain-specific calibration is explicitly deferred. English synthetic
evidence must not be treated as a Thai or domain-production threshold.

## Deterministic selection algorithm

### Choice families

Threshold selection uses calibration only.

- if all valid calibration predictions are correct, select the minimum observed
  correct confidence so the clean calibration set remains automatically
  decidable;
- if incorrect calibration predictions exist, find the maximum incorrect
  confidence and the nearest correct confidence strictly above it; select their
  midpoint as the separating threshold;
- if no separating threshold exists, mark the family selection infeasible and
  fail closed.

A decision is automatic only when confidence is at or above the frozen
threshold.

### Noul families

Center is fixed at 0.5. Candidate symmetric review-band margins are deterministic
0.05 steps from 0.0 through 0.5.

For each margin, only values strictly outside the review band are automatic.
Choose the margin with the maximum number of calibration automatic decisions
subject to zero false automatic decisions; ties choose the wider/more
conservative band.

Validation never influences selection.

## Candidate admission rule

A family can report `CANDIDATE` only when:

- calibration selection is feasible;
- calibration has zero false automatic decisions;
- validation has zero false automatic decisions;
- there are zero high-risk false automatic actions;
- all five validation cases are valid;
- at least one validation case is automatically decidable;
- no provider/schema error makes evidence incomplete.

Otherwise the family is `INCONCLUSIVE`.

Every report is structurally non-authoritative:

- `authoritative_for_production=false`
- `production_consequence_forbidden=true`

## Metrics

Per family and aggregate:

- raw accuracy;
- automatic-decision count / automatic accuracy;
- false automatic decisions;
- high-risk false actions;
- escalation/frontier-avoidance rate;
- p50 / p95 latency;
- input/output usage;
- total cost and cost per 1,000 decisions;
- provider/schema failures;
- chosen threshold/review band;
- calibration/validation counts.

Raw state is never copied into the report.

## Live plan after offline freeze

Only after offline tests, exact-scope verification, freeze, and independent R3
review:

1. build a separate external runtime capture using the accepted #505
   `TypeSafeSemanticDecisionProvider`;
2. use pinned `jev-1.13.0`;
3. resolve `TYPESAFE_API_KEY` through the accepted A-Wiki secret resolver at
   call boundary;
4. send synthetic/public held-out state only;
5. one call per case;
6. no blind retry and no automatic provider-SDK retry;
7. never persist or print the secret, Authorization header, raw provider body,
   or private state;
8. evaluate the captured result with this deterministic offline cascade;
9. use the result only as evidence for #509 JEV-5 production admission.

A successful live capture does not itself enable routing or product consequence.

## Verification gates

- RED-first targeted test proven before implementation;
- `tests/test_jev_confidence_cascade.py`;
- related JEV-1/JEV-2 semantic/provider regressions;
- `py_compile scripts/jev_confidence_cascade.py`;
- `git diff --check`;
- exact four-path scope;
- strict UTF-8 and added-line secret/session scan;
- exact-SHA independent R3 review;
- hosted CI before merge;
- post-main verification before close.

## Deterministic implementation checkpoint — 2026-09-23

Recovered GLM author history:

- attempt-0001: `TERMINAL_NO_PROGRESS`, no tracked mutation;
- attempt-0002: runner/supervisor disappeared without terminal evidence after
  writing only the RED test; exact process/session/Git recovery proved no owner
  remained;
- no third blind GLM author retry was dispatched;
- GPT/Worker takeover preserved the RED test and continued the same claim/scope.

RED was reproduced as:

`ModuleNotFoundError: No module named 'jev_confidence_cascade'`

Implementation then added the evaluator, 50-case held-out corpus, and this WO.
The first targeted run was 21 PASS / 4 FAIL. Two failures were test-fixture bugs
from the partial author result (invalid global `pytest.tmp_path_factory` use),
one was error-ordering, and one exposed a real Noul selection defect. All were
repaired inside the same four-path scope.

Current evidence:

- targeted JEV-4 suite: `25 passed`;
- related JEV shadow/strict-contract/semantic/provider regressions:
  `234 passed`;
- `py_compile`: PASS;
- exact mutable scope: PASS (four paths only);
- strict UTF-8: PASS;
- static credential/session-shape scan: PASS;
- `git diff --check`: PASS;
- no network/provider call was made by the author lane.

Next gate: exact-scope/UTF-8/secret scan -> freeze exact SHA -> independent R3
review + hosted CI. Live held-out capture remains a later, separately bounded
evidence action.

## Independent review repair checkpoint — 2026-09-23

Detached Worker-4 review of exact SHA
`5c45f0d8b89a343f8771f5b56821c4ebf7f083eb` returned
`CHANGES_REQUIRED` with P0=0 / P1=0 / P2=3.

Repairs remain inside the same four-path scope:

1. Removed `heldout_tag` from all model states. A read-only review probe proved
   the stripped corpus still has 50/50 unique states and zero exact overlap
   against 66 tuning states.
2. Enforced Noul center / decision threshold = 0.5 at corpus load time and added
   a fail-closed regression.
3. Added explicit family-wide and aggregate automatic-decision, auto-accuracy,
   false-auto, high-risk false-action, escalation/frontier-avoidance,
   provider-error and schema-failure metrics plus deterministic regressions.

Targeted repair suite is now `27 passed`.

The reviewer also noted one non-blocking P3: this script reuses private
`jev_shadow_benchmark` helpers for raw correctness and percentile calculation.
That coupling is same-repo, deterministic, and does not create new authority;
it remains a follow-up hardening note rather than an acceptance blocker.

Next gate: related regressions + static freeze gates -> repaired exact SHA ->
focused independent rereview + hosted CI.

## Stop / authority rules

- provider evidence can never grant task/claim/WIP/mutation/review/merge or
  completion authority;
- no production routing is enabled by this Work Order;
- no live provider call is allowed in the implementation author run;
- no third blind GLM author dispatch after the two recovered attempts;
- any later live capture is a separate bounded evidence action;
- unresolved authority, privacy, schema, calibration or ownership ambiguity
  fails closed to INCONCLUSIVE / escalation.
