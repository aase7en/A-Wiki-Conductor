# WO-P1-183 — ZCode runtimeModel duplicate-key hardening

Status: READY_FOR_FREEZE / R1 HARDENING
Date: 2026-09-11
Owner: GPT-5.6 Sol integrator/implementer
Repository: aase7en/A-Wiki-Conductor
Branch: fix/wo-p1-183-zcode-runtime-json-dupkeys
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo183-zcode-dupkeys
Base: 680566d25e105630b321127c1a9b3e9e61af4bd4
Coordination: Issue #233
Source finding: GLM Wave 4 G8-A1, independently probed on then-current main.

## Goal

Harden `ZCodeRuntimeModel.from_json` so duplicate JSON object keys at any object depth are rejected rather than silently accepted with JSON's default last-wins behavior.

This is defense-in-depth on a trusted parent->helper environment channel. It is not a current P0/P1 Zero-Relay blocker, but duplicate-key rejection makes runtime provider/model/baseURL authority parsing unambiguous and executable.

## Risk / delivery

R1 bounded parser hardening unless implementation expands outside the declared parser/test seam. It must not preempt or modify WO181/WO179. Freeze may proceed while WO181 is under review, but this branch must not merge before WO181 critical-path acceptance/merge/post-main unless GPT/integrator explicitly re-adjudicates base drift.

## Reuse / implementation boundary

REUSE Python `json.loads` with a small `object_pairs_hook` duplicate detector; do not add a JSON library or second schema parser.

Mutable scope only:
- `src/a_conductor/zcode_protocol.py`
- `tests/test_zcode_phase_c.py`
- this WO document

Forbidden:
- ZCode helper/process/provider/credential behavior changes;
- `CURRENT-WORK.md`, `COLLAB.md`, `handoff.md`, project plan;
- live ZCode config, private secret layer, installed app/DB;
- WO181 source/test/doc scope;
- merge before WO181 unless explicitly re-adjudicated.

## RED / acceptance

RED-first must prove default parser accepts duplicate object keys today. Then candidate must reject at least:
1. duplicate top-level `provider`;
2. duplicate nested provider `baseURL`;
3. duplicate `modelId` inside nested model object;
4. normal canonical `to_json()` roundtrip remains accepted.

Required checks:
- focused `test_zcode_phase_c.py`;
- all ZCode tests or directly related parser/helper tests;
- `compileall`, diff check, UTF-8, changed-scope and secret scan;
- freeze exact SHA and keep Draft/blocked behind WO181 merge ordering.

No independent R3 review is required solely because this remains R1 and does not expand authority; GPT/integrator performs bounded acceptance after deterministic evidence. Escalate to R2/R3 if actual implementation changes serialized schema or provider/credential semantics.

## Implementation checkpoint

- RED: all three duplicate-key cases (top-level `provider`, nested provider `baseURL`, nested model `modelId`) were accepted by the predecessor parser and failed `pytest.raises` as expected — 3 RED failures.
- Repair: reuse stdlib `json.loads(..., object_pairs_hook=...)`; reject a duplicate decoded key at any JSON object depth and normalize to the existing `runtime model metadata is invalid` error contract.
- No serialized schema, provider identity, model identity, endpoint, or credential-delivery semantics changed.
- Targeted duplicate/roundtrip/inline-secret set: 5 passed.
- Full `tests/test_zcode_phase_c.py`: 27 passed.
- All `tests/test_zcode*.py`: 196 passed.
- Merge ordering remains locked behind WO181 critical-path merge/post-main verification; this lane may freeze/push as Draft only until that dependency is cleared.
