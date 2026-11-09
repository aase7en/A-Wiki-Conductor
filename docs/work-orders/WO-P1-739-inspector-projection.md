# WO-P1-739: Inspector read-only projection (slice 1 bootstrap)

Issue: #739
Status: PARKED / REVIEW_R4_HARD_PARK / NOT_PUBLISHED
Classification: R2 read-only pure projection (no runtime, no authority)
Base: a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217 (origin/main frozen; exact-SHA freeze required)
Worktree: ../A-Wiki-Conductor-wo739-bootstrap
Branch: docs/wo739-inspector-projection
Mutable scope: this doc + CURRENT-WORK.md + handoff.md ONLY.
Implementation reservation: NEW `src/a_conductor/inspector_projection.py` + NEW `tests/test_inspector_projection.py` ONLY. No existing-file edits are authorized. If port semantics or safe redaction cannot be established within those two new files, PARK the slice (see §5); do not edit existing files to force it.

Joint adjudication provenance (on record, 2026-11-09): Terra (a) 0.88 + JEV direct noul 0.18 → Option A = projection-only slice. This bootstrap commits to the projection-only scope; it grants no runtime, authority, or merge permission.

## §1 Objective (adjudicated contract)

Implement a pure, offline, read-only projection over THREE injected evidence ports:

1. registry snapshot port
2. hook-evidence port
3. tool-evidence port

Each projected item carries:

- facts,
- source identity or pinned revision,
- observation time,
- explicit availability/freshness evidence.

Constraints: no live reads, no collectors, no network. The projection consumes only what the three injected ports hand it. Registration/routing facts and health are separate concerns (§2); output is allowlisted and redacted (§3).

## §2 Truth rules

- Registration/routing facts are kept strictly separate from health.
- NEVER infer per-item health from bus-level signals.
- A-Wiki hook classification is hard/soft — do NOT present it as OBSERVE/GUARD.
- The five-state set (READY / UNKNOWN / STALE / DISCONNECTED / DEGRADED) is emitted ONLY where an authoritative evidence contract defines the mapping. Everywhere else, emit UNKNOWN + reason.
- Missing, stale, or disconnected evidence NEVER implies healthy.

## §3 Output safety

- Strict field allowlist for every emitted item.
- Redact secrets from ALL emitted values, including reasons and source metadata.
- Drop unrecognized fields (fail closed to the allowlist).

## §4 RED-first fixture matrix (from #739)

Failing-test-first fixtures, in this order:

1. absent registration,
2. stale evidence,
3. disconnected device,
4. duplicate startup,
5. HookBus backpressure,
6. missing skill registry,
7. secret redaction.

Ambiguous per-item effects stay UNKNOWN (never guessed into READY/DEGRADED).

## §5 Gates

Before any implementation merge:

1. Claim issue #739.
2. Exact-SHA freeze on the reviewed head.
3. Independent review (never author self-review acceptance).
4. Exact-head CI green.
5. Merge concurrence recorded.
6. Exact post-main CI verified.
7. Fold into CURRENT-WORK.md + handoff.md.

Park condition: if port semantics or safe redaction cannot be established within the two new files, park the slice and checkpoint here. No existing-file edits to force it.

## §6 Out of scope

- Monitor API/UI wiring (next slice).
- Live collectors (later slice; separate WO).
- Privileged actions.
- New authorities.

Slice plan: slice 1 projection → slice 2 wire fifth view → slice 3 live collectors. Each slice is its own WO/gate cycle.

## §7 Park record (2026-11-09)

Status: **PARKED / REVIEW_R4_HARD_PARK / NOT_PUBLISHED** per joint adjudication. All work preserved unmerged on branch `docs/wo739-inspector-projection` (base `a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217`); no merge to main.

Full review chain:

- R1 (P1×4 P2×2) → repair 1
- R2 (P1×3 P2×2) → repair 2
- R3 (P1×1 P2×2) → adjudicated final repair (Terra 0.83 + JEV 0.72 joint grant)
- R4 (P1×1 → HARD PARK)

R4 finding (verbatim): equal match COUNTS do not establish the same matched SEGMENTS — `℀Bearer one & tоken=two` (Cyrillic о): original scan matches Bearer, folded scan matches token, 1==1 → surgical path redacts only Bearer, folded token leaks (inspector_projection.py:302-306).

H2/H3 CLOSED and pinned: 52 lane tests + 40 regression tests green at frozen sha256 `80b94df797f34aea04ac8835c2864a46f3766f4e82d4b412740dd978f64ec51c` (`src/a_conductor/inspector_projection.py`) / `2c7828e89a69290899db869d1c4eebd15157007424a9b0ff000f6ea063c40993` (`tests/test_inspector_projection.py`), byte-verified against the parked worktree at park time.

RESUME CONTRACT (next lane, fresh claim required — no further cycles under this adjudication):

1. Replace count-equality with matched-segment-SET comparison: original-scan segments vs folded-scan segments — any difference → whole-value redaction. Simplest correct form: if the folded scan fires ANY segment whose ASCII-scan counterpart did not fire → whole-value redaction.
2. RED tests: the `℀Bearer`/`tоken` probe + segment-boundary family (fold shifts a boundary, marker exists only folded, two mixed segments).
3. Keep every existing pin.
4. One fresh review; hard park on any finding.

## Checkpoint log (append-only)

- [2026-11-09] bootstrap agent (GLM/ZCode lane): docs-only bootstrap created at base `a0eccf289f69dbf61b13cb2a9b8c0b581a3ca217` in worktree `../A-Wiki-Conductor-wo739-bootstrap`, branch `docs/wo739-inspector-projection`. Scope = this doc + CURRENT-WORK.md + handoff.md only. Implementation NOT authorized; next executor = gate rerun + claim on #739 + implement per §5 using RED-first fixtures §4 first.
- [2026-11-09] park agent: implementation lane executed in reserved files only; review chain R1→R2→R3→R4 completed with R4 P1 hard park. Status set to PARKED / REVIEW_R4_HARD_PARK / NOT_PUBLISHED; full record in §7 Park record. Branch committed and pushed; no merge; resume only via fresh claimed lane per §7 RESUME CONTRACT.
