# WO-P1-187 — GLM Wave 8 / 4,000-unit sustained delivery campaign

Status: DOCS-ONLY ORCHESTRATION PACKET / READY TO FREEZE
Parent: WO-P1-155 Zero-Relay Accelerator
Durable coordination: GitHub Issue #233
Owner of this docs packet: GPT-5.6 Sol integrator
Execution engine: GLM-5.3 MAX through ZCode nested `/goal`
Acceptance / merge authority: GPT-5.6 Sol
Repository: A-Wiki-Conductor
Branch: `docs/wo-p1-187-glm-wave8-4000`
Bootstrap main: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`

## Purpose

Keep GLM productively occupied for a multi-hour session with one human pointer while preserving repository authority. Wave 8 starts by implementing the newly READY ZRA-2 Phase-A task under WO165, then continues through independent non-overlapping delivery, falsification, security, continuity and successor-shaping work.

This is a workload queue, not a token-burning quota. Work that has no unresolved evidence must be skipped with a precise consumed/no-real-work reason. Re-running identical reads/tests on the same SHA solely to consume tokens is forbidden.

## Topology

- 20 programs: `P00..P19`.
- Each program owns 20 evidence-family slots: `F00..F19`.
- Each active family follows 10 child actions: `A..J`.
- Maximum base work units: `20 × 20 × 10 = 4,000`.
- Proven new findings may recurse `R1..R10`.
- When all base families are dispositioned and useful session budget remains, replenish with evidence-backed `X0001..X1999` goals.

A family may be marked `CONSUMED_PROVEN`, `BLOCKED_WITH_OWNER`, `DEFERRED_BY_AUTHORITY`, or `NO_REAL_WORK`; each non-executed family must name exact evidence/reason. Bulk completion claims without family evidence are invalid.

## Critical first action

`P00-F00` MUST consume and execute the separately claimed WO165 Phase-A packet:

`A:\GitHub\_worktrees\A-Wiki-Conductor-wo165-zra2-r2\runs\WO-P1-165\phase-a\TASK.md`

Expected task SHA256 at Wave-8 creation:
`ef982d8e7b06f3826595caaeb39bc805631e802847d1f254f2c3745c74f605ac`

WO165 source ownership is separate from this docs packet. Follow its exact claim/scope. After freezing the Phase-A candidate, stop mutating it, publish evidence, and continue Wave 8 with non-overlapping work. The authoring GLM session MUST NOT independently review its own WO165 candidate.

## Programs

- P00 — ZRA-2 Phase A delivery + freeze + evidence packaging.
- P01 — ZRA-2 Phase B repair-materializer reuse map and RED contract.
- P02 — ZRA-2 Phase C review-mailbox/ReviewBridge composition and spoofing matrix.
- P03 — ZRA-2 Phase D durable job/closeout composition and recovery matrix.
- P04 — ZRA-3 NEXT READY continuation contract, replay and timeout falsification.
- P05 — ZRA-4 bounded 2–3 lane fan-out/fan-in, partial-write and sibling-preservation evidence.
- P06 — ZRA-5/ODP readiness only; no broad ODP implementation before ZRA-4 acceptance.
- P07 — Agent security fixtures: indirect prompt injection, tool-output injection, metadata attacks, authority escalation.
- P08 — Secret/exfiltration fixtures and positive controls using fake/synthetic secrets only.
- P09 — AEET/evaluator corpus, known-good/known-bad fixtures, evaluator self-tests, gate-aware shaping.
- P10 — ZCode/provider compatibility: bundle behavior probes, materialization/attestation, ambient-hook suppression shaping.
- P11 — Process/recovery: PID identity/reuse, orphan prevention, output bounds, result-missing and ambiguous transport.
- P12 — Durable state: SQLite CAS, leases/admission, stale ownership, replay/dedup, foreign-but-valid evidence.
- P13 — Cross-platform/filesystem: Windows env, POSIX parity, symlink/junction/reparse, casefold, Unicode, long paths.
- P14 — Review/acceptance trust: exact-SHA binding, reviewer independence, base drift, review spoofing, merge fences.
- P15 — Defect memory: convert repeated defect classes into tests/checkers/invariants instead of prose-only lessons.
- P16 — Continuity/SSoT: CURRENT-WORK drift, Issue #213–#216 aging, cold-start drills; no hotspot writes without claim.
- P17 — Test economy/CI/release: focused-first ladders, runtime cost, exact-head CI, post-main verification.
- P18 — Repository hygiene: consumed packet PRs, stale branches/worktrees, ownership-aware cleanup recommendations only.
- P19 — Successor queue/future leverage: rank genuine READY work, simplify architecture, replenish X-goals.

## Standard family protocol A..J

A. RECOVER — re-pin actual Git/GitHub/runtime/claim state relevant to this family.
B. REUSE — identify existing authority/test/helper before proposing anything new.
C. TRACE — follow the exact call/data/identity path; avoid broad speculative reading.
D. POSITIVE CONTROL — prove the intended benign path before adversarial mutation/probe.
E. FALSIFY — attack the highest-risk assumption with bounded deterministic evidence.
F. DELIVER — implement only if an explicit child WO/claim/scope gate grants mutation; otherwise produce a bounded packet/reproducer.
G. VERIFY — targeted/related tests or deterministic proof appropriate to the risk.
H. DEFECT MEMORY — if a real defect was found, prefer regression test/checker/type/schema/invariant over prose.
I. CHECKPOINT — write changed-state-only durable evidence to the relevant Issue/PR/run surface.
J. ROUTE — choose DONE/REPAIR/REVIEW/BLOCKED/NEXT without asking the user to type continue.

## Mutation authority

This WO187 branch may mutate only:
- `docs/work-orders/WO-P1-187-glm-wave8-4000.md`
- `docs/prompts/GLM-MARATHON-WAVE8-4000-GOALS.md`

It grants NO blanket product/source/test/runtime/provider/private/DB/process mutation authority.

Any implementation child must:
1. reuse an existing WO if one is already canonical;
2. otherwise create a bounded WO/claim only if the packet explicitly permits that bootstrap;
3. prove repo/worktree/branch/HEAD/dirty/owner/claim/scope/non-overlap;
4. keep separate worktree/branch;
5. freeze exact SHA and stop mutation for required independent review.

## R2/R3 independence

A GLM session that authors a candidate cannot serve as its independent exact-SHA reviewer. After authoring/freeze, checkpoint the candidate and continue other non-overlapping families. GPT/integrator or a separate independent reviewer handles acceptance/review.

## No-repeat rule

Consume Wave 1–7 evidence. Do not rerun a completed family unless material state changed. A valid consume record names the previous checkpoint/source and explains why it still applies to current SHA.

## Replenishment

After base programs, derive `X0001..X1999` only from:
- new proven defects;
- newly unblocked dependency nodes;
- frozen candidates needing independent review where this session is genuinely independent;
- missing executable defect memory;
- changed-state SSoT/claim/CI/PR drift;
- accepted architecture gaps with a precise smallest next slice.

Never manufacture X-goals simply to extend runtime.

## Checkpoint cadence

Checkpoint at:
- source claim acquired/released;
- RED reproduced;
- candidate frozen;
- independent review result observed;
- material dependency unblocked/blocked;
- every 5–10 meaningful families or before context/session rollover.

Use Issue #233 plus the relevant Issue/PR. Keep detailed logs under gitignored `runs/**`.

## Completion

Wave 8 may stop only when one of these is true:
- provider/session hard limit is near and a resumable checkpoint is durable;
- all genuine base and replenishment goals are exhausted;
- every remaining item is blocked by explicit human/authorization/safety authority.

`DONE` never means “all 4,000 tokens/units were consumed.” It means every selected unit has evidence or a truthful skip/block classification.
