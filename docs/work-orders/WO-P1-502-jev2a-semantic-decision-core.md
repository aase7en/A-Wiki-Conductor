# WO-P1-502 — JEV-2A semantic decision core

Status: ACTIVE / R2 / CONTROL_PLANE_ONLY
Parent: Issue #501
Issue: #502
Reuse class: EXTEND existing ODP/JEV/A-FastTask architecture

## Lane binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution repo: same repo
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo502-jev2a`
- Branch: `feat/wo-p1-502-jev2a-semantic-core`
- Base at claim: `bf1d9727c6f0b88abd11b6a744e6276c69e769ca`
- Owner: bounded implementation lane; GPT-5.6 Sol remains integrator/acceptance authority
- Mutable slot: M2
- Active non-overlap: #498 owns pre-dispatch guard/zcode hotspots; this WO must not touch them.

## Goal

Implement the pure provider-neutral semantic decision seam required by ODP-2/JEV-2. This slice is deterministic and I/O-free. It provides normalized typed evidence and advisory policy primitives only.

## Allowed scope

- `src/a_conductor/semantic_decision.py`
- `tests/test_semantic_decision.py`
- this Work Order

No other tracked path may change without explicit integrator re-gate.

## Contract

The module must provide:

1. Bounded semantic decision families:
   - `task_classification`
   - `skill_suggestion`
   - `failure_classification`
   - `evidence_relevance`
   - `escalation_decision`
   - `review_severity`
2. Primitive kinds: `choice`, `score`, `noul`.
3. Immutable normalized request contract with:
   - stable request ID;
   - decision family;
   - primitive;
   - sanitized bounded state;
   - explicit choice/rubric/threshold metadata as applicable;
   - risk level.
4. Immutable normalized evidence envelope with:
   - provider/model;
   - answer;
   - optional confidence/probabilities;
   - input/output usage;
   - latency;
   - typed error;
   - `authoritative_for_action=False` structurally.
5. `SemanticDecisionProvider` protocol.
6. Deterministic fake provider for tests only.
7. Modes: `OFF`, `SHADOW`, `ADVISORY`.
8. Dispositions: `BYPASS`, `OBSERVE`, `ADVISE`, `ESCALATE`.
9. Policy:
   - only the five benchmark-proven families are Jev-eligible;
   - `review_severity` is frontier-only;
   - OFF -> BYPASS;
   - SHADOW -> OBSERVE only, never ADVISE;
   - ADVISORY may ADVISE only when evidence is valid, family eligible, confidence/threshold requirements are satisfied and risk policy permits;
   - malformed, non-finite, out-of-range, mismatched or provider-error evidence -> ESCALATE;
   - no output grants claim, mutation, review, merge, completion or SSoT authority.

## Hard boundaries

- No filesystem/network/environment/secret/process access.
- No TypeSafe/Jev transport in this WO.
- No A-FastTask/A-Faster routing mutation in this WO.
- No new provider registry/scheduler/task DB/claim state.
- No changes to #498/#500 scope.

## Verification

- RED-first targeted tests.
- `python -m pytest tests/test_semantic_decision.py -q`
- related provider-policy/fallback tests if imports/interfaces intersect.
- `python -m py_compile src/a_conductor/semantic_decision.py tests/test_semantic_decision.py`
- `git diff --check`
- exact-scope audit + added-line secret/session scan.
- freeze exact SHA -> independent review + hosted CI -> merge/post-main.

## Integrator harvest checkpoint — 2026-09-23

- Jev advisory routed this bounded core to GLM-5.3 MAX (confidence 0.86); GPT retained routing/acceptance authority.
- CoinTH quota/readiness and exact `cointh-glm/glm-5.3` route passed before dispatch.
- A transport timeout left a live delegated process. A duplicate replay was detected by A-Faster census before source mutation and the later duplicate process tree was stopped by exact verified PIDs only.
- Kilo durable-session recovery identified the retained writer session and proved RED-first progress: `tests/test_semantic_decision.py` was authored and `ModuleNotFoundError` was reproduced before implementation.
- The retained writer later entered a pending write-tool state. GPT/Worker-1 performed an explicit same-scope takeover after exact process shutdown; the GLM-written module had landed by the takeover boundary, so it was harvested rather than overwritten.
- First deterministic harvest: `69 passed, 2 failed`. One failure was a duplicate-keyword test bug. The other incorrectly treated a structurally valid Choice probability distribution as invalid; JEV-1C only requires exact keys, bounded probabilities and sum=1, so the test was repaired without inventing a new provider invariant.
- Final targeted: `71 passed`.
- Related JEV/provider regression set: `110 passed`.
- `py_compile`, `git diff --check`, added-line credential/session scan, and anchored forbidden-I/O import scan: PASS.
- Production module imports only `math`, `re`, `dataclasses`, `enum`, `types`, and `typing`; it performs no filesystem/network/environment/secret/process access.

## Freeze candidate

Freeze only:
- `src/a_conductor/semantic_decision.py`
- `tests/test_semantic_decision.py`
- this Work Order

Next gate: exact-SHA independent review + hosted CI. No TypeSafe transport or A-Faster routing mutation is part of this candidate.

## Independent review repair checkpoint — 2026-09-23

SunDay-Worker 4 reviewed exact candidate
`23a87636aadfabe57014e03b7761927b9215afec` read-only and returned
`CHANGES_REQUIRED` with P0=0 / P1=0 / P2=1.

Finding: `_validate_probabilities()` treated `None` as valid. That allowed
Choice/Score evidence without the probability map required by the accepted
JEV-1C strict contract to reach SHADOW `OBSERVE` or ADVISORY `ADVISE`
instead of failing closed.

Repair is intentionally narrow:

- added RED coverage proving Choice `probabilities=None` escalates;
- added RED coverage proving Score `probabilities=None` escalates;
- reproduced both failures before code mutation;
- changed `_validate_probabilities(None)` to invalid;
- final core suite: `73 passed`;
- related JEV/provider regression suite: `110 passed`;
- `py_compile` and `git diff --check`: PASS.

Next gate: freeze repaired SHA -> focused independent rereview -> exact-head CI.

## Replay / closeout

Worker/GLM DONE is a claim only. If an external writer terminates, harvest exact Git/result evidence before retry. No blind replay.