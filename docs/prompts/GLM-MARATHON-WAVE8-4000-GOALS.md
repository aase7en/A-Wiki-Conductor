# GLM MARATHON WAVE 8 — 4,000-UNIT EVIDENCE DELIVERY TREE

## ROOT `/goal`

Run this as one sustained ZCode/GLM-5.3 MAX goal. Continue automatically across child goals until the provider/session hard limit is near, the evidence-backed queue is exhausted, or every remaining goal has a real authority blocker.

Do not ask the user to type `continue` between safe goals. Do not make the user copy results back to GPT. Persist checkpoints/results to the declared GitHub Issues/PRs and gitignored `runs/**` surfaces.

## Mandatory cold start

Before material work:
1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and route only relevant nodes.
3. Read `AGENTS.md`.
4. Re-pin actual repo/remote/worktree/branch/HEAD/dirty state, open PRs, active claims/leases and relevant CI.
5. Read the active child WO/task packet before any mutation.
6. Read only task-relevant FAST protocol / DEFECT_LESSONS sections.
7. Treat `CURRENT-WORK.md`, handoff and COLLAB as projections; actual Git/GitHub/runtime evidence wins when they conflict.
8. Never mutate when owner/claim/scope/dirty/overlap is unknown.

## Wave-8 bootstrap identity

Tracked packet branch: `docs/wo-p1-187-glm-wave8-4000`
Bootstrap main: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`
Tracked work-order: `docs/work-orders/WO-P1-187-glm-wave8-4000.md`
Durable coordination: GitHub Issue #233

This tracked packet is transport/orchestration only. Its branch is not product-mutation authority.

## PREEMPTION 0 — MUST RUN FIRST: WO165 / ZRA-2 Phase A

The Zero-Relay critical path has advanced: ZRA-1 LIVE-3 is ACCEPTED and independently adjudicated ACCEPT. Resume the canonical existing ZRA-2 work order; do NOT invent a second ZRA-2.

Read and execute:

`A:\GitHub\_worktrees\A-Wiki-Conductor-wo165-zra2-r2\runs\WO-P1-165\phase-a\TASK.md`

Expected packet SHA256 at Wave-8 publication:
`ef982d8e7b06f3826595caaeb39bc805631e802847d1f254f2c3745c74f605ac`

Expected WO165 refresh lane at publication:
- worktree `A:\GitHub\_worktrees\A-Wiki-Conductor-wo165-zra2-r2`
- branch `feat/wo-p1-165-zra2-review-repair-loop-r2`
- refresh head `1dda36d613e4a5c4502ec4049df510c8d20565b0`
- Draft PR #258
- source claim owner: GLM-5.3 MAX bounded implementation lane
- exact mutable scope: `src/a_conductor/zero_relay.py`, `tests/test_zero_relay.py`, WO165 doc only.

Re-pin before editing. If the exact lane has materially drifted or another owner overlaps it, checkpoint `RECONCILE_REQUIRED` instead of stealing/resetting/rebasing.

For Phase A:
- execute RED-first;
- implement only the pure durable-reference state machine;
- no live provider/credential/Git/review/file/process/network I/O in `zero_relay.py`;
- exactly one repair generation;
- UNKNOWN/ambiguous => RECOVERY_REQUIRED;
- author/reviewer execution IDs distinct;
- no sequence continuation (ZRA-3) and no repair materialization/review transport (later phases);
- freeze exact SHA, push normally, update PR #258 + Issues #214/#233;
- stop mutating WO165 after freeze;
- DO NOT independently review/self-accept/self-merge the candidate you authored.

After Phase-A freeze, immediately return to this Wave-8 queue and continue non-overlapping work while GPT/integrator arranges independent review.

## Work accounting

Wave 8 defines:
- programs `P00..P19`;
- family slots `F00..F19` inside every program;
- actions `A..J` inside each selected family;
- maximum base actions = 20 × 20 × 10 = 4,000;
- recursive proven-finding children `R1..R10`;
- post-base evidence-backed replenishment `X0001..X1999`.

This is a capacity envelope, not a requirement to manufacture work. Every family must be one of:
- `DELIVERED` — new evidence/implementation/packet/checkpoint produced;
- `CONSUMED_PROVEN` — earlier exact evidence remains applicable; cite it;
- `BLOCKED_WITH_OWNER` — another lane/authority owns it; cite owner/claim;
- `DEFERRED_BY_AUTHORITY` — dependency/policy gate not satisfied;
- `NO_REAL_WORK` — no unresolved evidence-backed work exists; explain why.

Do not claim 4,000 units completed merely because the family table was enumerated. Evidence is the completion authority.

## Standard nested family protocol

For each selected `Pxx-Fyy`, create/execute child goals in this order unless a dependency makes one inapplicable:

### A — RECOVER
Re-pin relevant Git/GitHub/runtime/claim/CI state. Record only material delta.

### B — REUSE
Search for existing source/test/contract/WO/claim. Classify `REUSE | WRAP | EXTEND | REPLACE | NEW`. Prefer REUSE→WRAP→EXTEND.

### C — TRACE
Trace the exact authority/data path and identify where trust changes hands. Do not broad-read the repo without need.

### D — POSITIVE CONTROL
Prove a valid benign path first. If the positive control fails, stop interpreting adversarial failures until the fixture is fixed.

### E — FALSIFY
Attack the highest-risk assumption: identity mismatch, stale evidence, duplicate/replay, timeout/UNKNOWN, parser ambiguity, permission/claim drift, secret exposure, cross-platform edge, or sibling-loss as applicable.

### F — DELIVER
If a current child WO/claim grants mutation, implement the smallest accepted slice. Otherwise create only a bounded reproducer/packet/recommendation under an allowed ignored/docs surface.

### G — VERIFY
Run targeted then related deterministic tests. Full/hosted CI is for frozen candidates or when broad coupling justifies it.

### H — DEFECT MEMORY
For real defects, prefer regression test → deterministic checker → type/schema/invariant → CI/lint/monitoring → docs. Avoid prose-only memory when executable memory is possible.

### I — CHECKPOINT
Persist changed-state-only evidence to relevant Issue/PR and detailed local `runs/**` as appropriate.

### J — ROUTE
Route to next family, bounded repair, independent review wait, recovery, or explicit blocker. Never stop just to ask the user to type continue.

## Program P00 — ZRA-2 Phase A delivery/freeze

F00 is PREEMPTION 0 above. Use remaining families only for real Phase-A support: caller archaeology, identity model, adversarial probes, evidence packaging, exact-scope hygiene, assurance packet, and post-freeze read-only support. Never review your own frozen candidate.

## Program P01 — ZRA-2 Phase B repair materialization

After Phase A freezes, shape but do not silently implement Phase B until Phase-A acceptance/scope gate permits. Focus on reuse of `AgentRepairRequest`, `build_repair_task_markdown`, confined deterministic path, same-bytes reuse, different-bytes collision, exact rejected-result binding, and no raw prompt synthesis.

## Program P02 — ZRA-2 Phase C review composition

Map `ReviewMailboxResultReader`, `ReviewResultForwarder`, A-Wiki ReviewBridge contract and reviewer identity. Falsify self-review, foreign task/result, stale reviewed SHA, forged provider/model, task-hash drift, oversized/truncated result, and addressed-but-unverified blocker semantics. No second ReviewBus.

## Program P03 — ZRA-2 Phase D durable lifecycle composition

Shape the wrapper from accepted/rejected review decisions into existing JobStore/GoalCloseout authorities. Challenge REVIEW_PENDING, CHANGES_REQUIRED, repair generation, UNKNOWN recovery, exact-head acceptance and no completion from provider exit/reviewer prose alone.

## Program P04 — ZRA-3 automatic NEXT READY

Prepare the thinnest continuation seam after ZRA-2 acceptance. Reuse scheduler/graph/job authorities. Falsify duplicate tick, stale ready state, timeout, foreign completion, dirty/lease drift, and restart replay. Do not implement before ZRA-2 acceptance if policy blocks it.

## Program P05 — ZRA-4 bounded parallel/fan-in

Prepare 2–3 independent READY-lane proof using existing lease/provider admission/WIP limits. Challenge sibling failure preservation, partial fan-in writes, provider-capacity uncertainty, duplicate execution, stale lease, one malformed authority result, and exact-result binding. No new scheduler.

## Program P06 — ZRA-5 / ODP readiness

Readiness/reconciliation only unless ZRA-4 acceptance has actually landed. Map how capability-first routing consumes accepted zero-relay execution without making mailbox/provider names new authority. Do not broadly implement ODP early.

## Program P07 — agent injection/security fixtures

Derive bounded fake-first fixtures for repository-content injection, tool-output injection, malicious metadata, instruction hierarchy attacks, authority escalation and inter-agent taint. Every bad fixture needs a valid positive twin. No real secrets or live providers.

## Program P08 — secret/exfiltration boundaries

Use synthetic secrets only. Challenge task/result/log/artifact/exception/argv/env leak paths, redirects, endpoint drift, ambient user settings/config, review payload leakage and child-process env expansion. Existing explicit env authorities remain primary.

## Program P09 — AEET / evaluator

Refresh corpus provenance from accepted tests, seed known-good/known-bad pairs, define evaluator self-tests and false-positive/false-negative controls. Respect roadmap/gate ownership; if implementation remains blocked, deliver only exact packets/fixtures.

## Program P10 — ZCode/provider compatibility

Build evidence around runtimeModel materialization, create-time attestation, bundle behavior, schema drift, endpoint/generation fences and ambient hooks. Prefer behavior probes over brittle minified-bundle substring checks. Do not use live provider traffic unless separately authorized.

## Program P11 — process/recovery

Audit/extend evidence for PID+creation-time identity, orphan prevention, process-gone-before-release, output flood/bounds, supervisor/result missing, cleanup locks, timeout ambiguity, restart attach/reuse and no broad kill surface.

## Program P12 — durable DB/concurrency/replay

Challenge JobStore version CAS, execution-store identity, provider admission lifecycle, WorkerLease expiry/release, foreign-but-valid evidence, duplicate/replay identity, concurrent sibling preservation and stale-owner reconciliation. Do not create parallel stores.

## Program P13 — cross-platform/filesystem

Use bounded tests/probes for Windows SYSTEMROOT minimality, POSIX parity, junction/symlink/reparse, case-insensitive env aliases, Unicode/UTF-8, long paths/argv, file-replacement semantics and OS-specific exception classes. Avoid broad live `.zcode\v2` search.

## Program P14 — review/acceptance trust

Audit exact-SHA review binding, reviewer independence, base drift, candidate movement, review spoofing, CI exact-head, expected-head merge and historical process deviations. Missing prior evidence stays missing; never backfill fictional review.

## Program P15 — executable defect memory

Mine repeated high-value defect classes from `DEFECT_LESSONS.md` and recent accepted WOs. For each real recurrence candidate, map an executable prevention mechanism and prove whether it already exists before proposing new code.

## Program P16 — continuity / SSoT / claims

Audit changed-state staleness in CURRENT-WORK/handoff/COLLAB/Issues. Do not directly edit shared hotspots without single-writer claim. Prefer durable Issue/WO checkpoints until a legitimate fold lane exists. Run cold-start recovery drills using actual entry routing.

## Program P17 — test economy / CI / release

Measure focused-vs-related-vs-hosted yield, identify redundant re-runs, preserve R3 assurance, and improve accepted-throughput without moving defects downstream. Release/post-main evidence remains exact-SHA authority.

## Program P18 — repository hygiene

Classify consumed docs packets, stale branches/worktrees, abandoned claims and superseded PRs. Do not delete/reset unknown work. Produce safe cleanup candidates with ancestry/clean-state/ownership evidence.

## Program P19 — successor queue and leverage

Rank the next genuine critical-path and high-leverage work after consuming all actual state. Simplify before building. Produce a bounded `NEXT READY` queue with dependencies, owner, risk, smallest mutable scope, evidence required and one exact next action.

## Recursive finding goals R1..R10

Spawn a recursive goal only when a concrete finding survives a positive control and falsification. Each recursive child must record:
- parent family;
- exact evidence;
- severity P0/P1/P2/P3/process;
- affected authority;
- whether existing tests/checkers already cover it;
- smallest repair/reproducer scope;
- owner/claim need;
- exit condition.

Depth >10 is forbidden. If the same material failure recurs twice without new evidence, stop retrying and enter root-cause/replan mode.

## Preemption rules

Preempt the queue when:
1. a frozen R2/R3 candidate from another author becomes ready and this session is genuinely independent;
2. a P0/P1 finding threatens an active external-effect boundary;
3. a claim/ownership drift makes planned mutation unsafe;
4. an exact CI/merge/post-main result unblocks the critical path.

After preemption checkpoint, return to the prior queue automatically.

Do NOT independently review any candidate authored in this same GLM session.

## Replenishment X0001..X1999

After P00..P19 are truthfully dispositioned, and useful session budget remains, mint X-goals only from proven current evidence. Priority:
1. newly unblocked critical path;
2. independent review of other-author frozen candidate;
3. P0/P1/P2 defect reproducer/repair packet;
4. missing executable defect memory;
5. security/adversarial fixture with positive twin;
6. cross-platform proof gap;
7. SSoT/claim drift creating duplicate-work risk;
8. measurable throughput/test-economy improvement;
9. cleanup candidate with deterministic ownership/ancestry evidence;
10. architecture simplification/removal of duplicate authority.

No speculative feature expansion and no token-padding goals.

## Multi-session continuity

When context or provider limit approaches:
- checkpoint exact completed program/family IDs;
- record candidate SHA/claims/open blockers;
- record current queue head and skip set;
- persist detailed evidence paths;
- emit one resume pointer that tells the next GLM session to continue from the first unresolved family/X-goal, never restart Wave 8 from P00 unless state materially invalidated earlier evidence.

## Final result contract

At end of a session/wave checkpoint report:
- actual repo/main/PR/CI state;
- WO165 Phase-A candidate/result state;
- programs/families delivered/consumed/blocked/deferred counts;
- recursive findings by severity;
- candidates created/frozen and exact SHAs;
- independent reviews performed only where independence is genuine;
- mutations with claims/scopes;
- tests/probes and defects found/falsified;
- ZRA-2/3/4/5 maturity delta;
- security/evaluator/process/cross-platform delta;
- SSoT/claim drift;
- top NEXT READY queue;
- `DO_NOT_BUILD` list;
- exactly one highest-priority `NEXT_SAFE_ACTION` for GPT/integrator if an authority boundary remains.

Work until the session has no truthful safe next action or provider/session capacity is near its hard limit. Evidence production, not token consumption, is the objective.
