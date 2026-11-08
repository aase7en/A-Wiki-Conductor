# WO-P1-738 Verified NEXT READY Selection (verify-then-select)

Issue: #738
Status: PARKED / REVIEW_R4_NEW_P1 / NOT_PUBLISHED_TO_MAIN
Classification: R3 read-only durable-state boundary (offline fixture-provable)
Base: `a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217`
Worktree: `/Volumes/MAC_WORK/DevWorkspace/Github/A-Wiki-Conductor-wo738-bootstrap`
Branch: `docs/wo738-verified-next-ready`
Mutable bootstrap scope: this document + `CURRENT-WORK.md` + `handoff.md` only.
Implementation reservation (future, gated): NEW `src/a_conductor/verified_next_ready.py` + `tests/test_verified_next_ready.py` ONLY; no existing source file edits. This reservation is not a claim or authorization.
Parent frontier: #736 (OPEN ZRA-3G/ZRA-4 tracker). WO-736 delivered via PR #737 (merge `226aa10`, post-main green on `a0eccf2`).

Decision provenance: next-slice selection adjudicated by GPT-6.1 Terra, 2026-11-08, confidence 0.82; JEV advisory unavailable (documented server defect on [#709 comment 6719134323](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6719134323)); decision stands per integrator authority without JEV concurrence, documented for the record.

## §Park note (2026-11-08)

Candidate PARKED at R4; preserved unmerged on this lane branch (`docs/wo738-verified-next-ready`, src `abada6fc…`, tests `21214c77…`; tests 53+63 green). Review chain: R1 P1×2 → R2 P1×2 → R3 P1×3 (all repaired, reproductions closed) → R4 six contract points CLOSED + flip adjudicated SOUND, but R4 surfaced a NEW P1 on the OBSERVED-side version comparison, outside the verdict ingress: observed-side `facts.parent.version` int-subclass with a lying `__ne__` launders stale evidence into selection (`verified_next_ready.py:622`). Exact fix contract for the future lane: extend the same ingress normalization to observed/durable-side values (`facts.parent.version` and any other observed field reaching a comparator) + pin REJECTED-direction + liar pins. Adjudication pointer: park checkpoint posted on #738. No further review/repair cycle under this adjudication; resume requires a fresh claimed lane on #738.

## 1. Objective

Provide the verify-then-select seam for the adjudicated ZRA-3G slice 2: one read-only function for one explicit graph ID + one explicit graph-run ID + one completed parent node, selecting at most one direct-successor node ID for a future continuation. Inputs are graph/durable job observations, guard verdicts, and an accepted-completion verdict bound to the exact parent job/version/completion evidence. Ports are injected and fixture-only: the existing read-only job observation interface plus an authoritative completion-verification interface. REUSE `observe_next_ready_facts` (`src/a_conductor/next_ready_continuation.py:378`) and `plan_next_ready_continuation` (`src/a_conductor/next_ready_continuation.py:256`) — both verified present at the stated anchors on base `a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217` in this worktree; re-verify exact accessibility and semantics at the implementation head before writing code and record the verified anchors in evidence. Output is exactly one of: one selected direct-successor ID | an existing no-op/reconciliation outcome | a typed blocker. Planner priority/topological/node-ID ordering is preserved in every selection and every ordered output.

## 2. Failure Model

All five modes fail closed:

1. Forged, rejected, or missing acceptance verdict cannot select.
2. Cross-graph / cross-run / cross-job / cross-version evidence cannot authorize a successor — any binding mismatch is rejected, never reinterpreted.
3. Partial, conflicting, or malformed reads yield typed blockers with exact reason codes — never a silent "no successor".
4. Already-represented successor or uncertain prior dispatch yields an explicit recovery outcome — never a blind reselect.
5. Guard failure, ambiguity, cycle, or stale observations yield typed blockers.

## 3. Prohibitions

No loop, no continuation-loop reconstruction, no dispatch-request construction, no execution, no claim mutation (ORCH-1/7 HOLD per [#709 comment 6719134323](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6719134323)), no network/credentials/live runtime, no new store/scheduler/authority. Never manufacture an acceptance verdict. The selection output is advisory only and is not dispatch authorization. This seam must not weaken, bypass, or shadow any existing ORCH-1 boundary.

## 4. Acceptance Criteria

Offline deterministic verification only: fixture-owned stores/ports, no network, no live runtime, no credentials. RED-first tests covering, per failure mode (§2) with exact typed reason codes defined in the gated implementation contract before tests are written:

- Forged acceptance verdict rejected; rejected acceptance rejected; missing acceptance yields a typed blocker — none select.
- Cross-graph, cross-run, cross-job, and cross-version evidence each rejected with exact codes.
- Partial read, conflicting reads, and malformed reads each yield typed blockers (not "no successor").
- Already-represented successor and uncertain prior dispatch each yield the explicit recovery outcome.
- Guard failure, selection ambiguity, cycle detection, and stale observations each yield typed blockers.
- Happy path selects exactly the expected direct successor.
- Ordering preservation asserted against planner priority/topological/node-ID order.
- Restart/re-read stability: same inputs after simulated restart re-derive the identical outcome.

Assert all typed outcomes with exact reason codes; exceptions or generic failures are not sufficient evidence.

## 5. Delivery Gates

Immediately after this bootstrap rerun the full entry and mutation gates in `AGENTS.md`, including actual ownership and non-overlap proof, and obtain a claim on #738 before any implementation. Freeze the exact candidate SHA-256 for `verified_next_ready.py` and its test file; obtain independent review (never author self-review acceptance) and exact-head CI; adviser merge concurrence required; merge only by acceptance authority at the exact reviewed head; record exact post-main CI on #738; fold continuity (`CURRENT-WORK.md` + `handoff.md`) after post-main verification. Evidence destination: `runs/WO-P1-738/`. This packet alone authorizes no implementation, dispatch, merge, or runtime action.

## 6. Out Of Scope

Continuation-loop composition, parallel fan-in, any /7 mutable-refill surface, live/runtime activation, and any dispatch wiring. Each of these needs its own future slice/gate decision.
