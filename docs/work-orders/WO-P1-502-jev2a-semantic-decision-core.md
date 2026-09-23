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

## Replay / closeout

Worker/GLM DONE is a claim only. If an external writer terminates, harvest exact Git/result evidence before retry. No blind replay.