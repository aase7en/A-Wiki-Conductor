# WO-P1-738 Verified NEXT READY Selection (verify-then-select)

Issue: #738
Status: PARKED_ROUND_4 / REVIEW_R7_PARK / NOT_PUBLISHED_TO_MAIN
Classification: R3 read-only durable-state boundary (offline fixture-provable)
Base: `a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217`
Worktree: `/Volumes/MAC_WORK/DevWorkspace/Github/A-Wiki-Conductor-wo738-bootstrap`
Branch: `fix/wo738-sanitized-job-snapshot` @ `9af835b` (park-round-1 branch `docs/wo738-verified-next-ready`, round-2 park branch `fix/wo738-observed-normalization` @ `5c377d4`, and round-3 park branch `fix/wo738-monitor-capture-normalization` @ `7c1b524` preserved in history; see §Park notes)
Mutable bootstrap scope: this document + `CURRENT-WORK.md` + `handoff.md` only.
Implementation reservation (future, gated): NEW `src/a_conductor/verified_next_ready.py` + `tests/test_verified_next_ready.py` ONLY; no existing source file edits. This reservation is not a claim or authorization.
Parent frontier: #736 (OPEN ZRA-3G/ZRA-4 tracker). WO-736 delivered via PR #737 (merge `226aa10`, post-main green on `a0eccf2`).

Decision provenance: next-slice selection adjudicated by GPT-6.1 Terra, 2026-11-08, confidence 0.82; JEV advisory unavailable (documented server defect on [#709 comment 6719134323](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6719134323)); decision stands per integrator authority without JEV concurrence, documented for the record.

## §Park note (2026-11-08)

Candidate PARKED at R4; preserved unmerged on this lane branch (`docs/wo738-verified-next-ready`, src `abada6fc…`, tests `21214c77…`; tests 53+63 green). Review chain: R1 P1×2 → R2 P1×2 → R3 P1×3 (all repaired, reproductions closed) → R4 six contract points CLOSED + flip adjudicated SOUND, but R4 surfaced a NEW P1 on the OBSERVED-side version comparison, outside the verdict ingress: observed-side `facts.parent.version` int-subclass with a lying `__ne__` launders stale evidence into selection (`verified_next_ready.py:622`). Exact fix contract for the future lane: extend the same ingress normalization to observed/durable-side values (`facts.parent.version` and any other observed field reaching a comparator) + pin REJECTED-direction + liar pins. Adjudication pointer: park checkpoint posted on #738. No further review/repair cycle under this adjudication; resume requires a fresh claimed lane on #738.

## §Park-round-2 note (2026-11-08)

Candidate re-PARKED at R5; preserved unmerged on this branch (`fix/wo738-observed-normalization` @ `594c1bc`; src `3d748c57…`, tests `51308af8…`; 120 tests green). R5 fresh review = CHANGES_REQUIRED P1×1 (reproduced conflicting-read bypass): `_ParentReadMonitor` retains RAW read values (`verified_next_ready.py:323`), the consistency check hashes/compares them raw (`:344-347`), and only the projected first parent is normalized (`:636-667`); a lying `__eq__` + colliding-hash int-subclass second read defeats the read-conflict gate → SELECTED. Everything else PASSED: R4 reproduction blocked (closed), disclosure ACCEPTABLE, 120 tests green, hashes verified. Adjudicated PARK 0.94 per stop condition; park-round-2 checkpoint posted on #738. REMAINING FIX CONTRACT for any future lane: normalize each read's identity tuple AT CAPTURE inside `_ParentReadMonitor` (exact-type rules identical to the module's ingress: type-is int/str); RED test = the colliding-hash reproduction expecting `OBSERVATION_INCONSISTENT:PARENT_JOB_READS_CONFLICT`; all 120 tests green; one fresh review; park on any P1. No further cycles under this adjudication; resume requires a new adjudicated lane (fresh claim only).

## §Park-round-3 note (2026-11-08)

Candidate re-PARKED at R6; preserved unmerged on this branch (`fix/wo738-monitor-capture-normalization` @ `7c1b524`; src `acbacdc2…`, tests `9c461f10…`; 121 tests green). R6 single review verdict = PARK per lane contract (P1×1 + P2×1): P1 — monitor `get_job` returns the RAW job (`verified_next_ready.py:367`) and the reused seam compares the raw `job_id` (`next_ready_continuation.py:432`); a hostile `__ne__` is invoked once before the eventual blocker — violates comparators-never-invoked. P2 — hostile-read-1 classification asymmetry (`COMPLETION_VERSION_MISMATCH` vs `PARENT_JOB_READS_CONFLICT`). Everything else PASSED: R5 reproduction blocked with 0 invocations (closed), 121 tests green, hashes verified. Park-round-3 checkpoint posted on #738. RECORDED NEXT-LANE CONTRACT (one remaining idea, likely closes the class IN the same two-file scope): `_ParentReadMonitor` returns a SANITIZED plain-typed job snapshot from `get_job` instead of the raw store object — an exact-type dataclass copy (`job_id`/`state`/`version`/node fields plain) so the reused seam never touches a foreign object; keep capture-time normalization + all pins; RED test = R6's read-2 str-subclass `job_id` case asserting ZERO hostile comparator invocations anywhere (monkeypatch-count at the subclass); 121+ tests green; one fresh review; park on any P1. Alternative if that fails: scope-expanded WO on the reused seam's own typing (`next_ready_continuation.py` — separate files, separate claim). No further cycles under this adjudication; resume requires a fresh claimed lane on #738.

## §Park-round-4 note (2026-11-08) — STRUCTURAL CONCLUSION

Candidate re-PARKED at R7; preserved unmerged on this branch (`fix/wo738-sanitized-job-snapshot` @ `9af835b`; src `431d24d8…`, tests `44f521f5…`; 123 tests green). The round executed the recorded round-3 next-lane contract in full: `_ParentReadMonitor.get_job` now returns a sanitized plain-typed snapshot (`_snapshot_job`), capture-time normalization and all hostile-comparator pins from R1–R6 kept, and R6's read-2 str-subclass RED test present. R7 single review verdict = PARK per lane contract (P1×2):

- **P1-A** — `_snapshot_job` keeps parent fields VERBATIM (`verified_next_ready.py:503-509`, `plain_identity=False`), so the REUSED seam compares `job_id` at `next_ready_continuation.py:411` and `:432` and `ParentCompletion.__post_init__` compares `version < 1` at `next_ready_continuation.py:109` — ALL BEFORE the observed-side exact-type ingress `verified_next_ready.py:821-835`. The pinned typed codes fire correctly, but hostile `__ne__`/`__lt__` are invoked first — comparators-never-invoked violated.
- **P1-B** — non-parent normalization converts via `str(job_id)` (`verified_next_ready.py:415`), trusting an overridable `__str__`; a fabricated identity is laundered into a plain string and the run returns `NOOP_ALL_REPRESENTED` with no blocker — silent misrepresentation.

Deviations (1)(3)(4) adjudicated SOUND. Joint adjudication: JEV advisory 0.68 + Terra 0.84, both conditions satisfied.

**STRUCTURAL CONCLUSION (record prominently):** the "zero hostile comparator invocations" contract is NOT achievable from the monitor/wrapper side while the REUSED observation seam (`next_ready_continuation.py`) compares raw fields internally before any external gate. Four park rounds have exhausted the wrapper-side class: every achievable monitor-boundary sanitization still leaves the reused seam invoking comparators on fields it owns, because the seam's own input boundaries (`:411`/:432` identity checks, `ParentCompletion.__post_init__:109` version check) are un-gated. The durable fix belongs INSIDE `next_ready_continuation.py` — exact-type gates at its own input boundaries plus its `ParentCompletion.__post_init__` — a DIFFERENT file requiring its own work order and fresh review budget. The wrapper-side lanes (4 parks, 123 tests, all pins) remain preserved unmerged as scaffolding/reference for that future lane. Park-round-4 checkpoint posted on #738. No-further-cycles rule stands: no further review/repair cycles on this lane under this adjudication; any continuation requires a fresh claimed lane on #738 under the next-lane proposal (exact-type ingress inside `next_ready_continuation.py`).

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
