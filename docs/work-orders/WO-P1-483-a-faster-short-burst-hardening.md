# WO-P1-483 — A-Faster short-burst orchestration and timeout recovery hardening

Status: ACTIVE / DOCS-ONLY SHAPING — shaping contract frozen 2026-09-22 at dispatch HEAD 11c777f99542bd80b64341be655a0094d16ca6be
Issue: #483
Topology: CONTROL_PLANE_ONLY
Risk: R2 policy/tooling; source mutation may become R3 if execution semantics change
Claim: WO-P1-483-SHORT-BURST-DOCS-WINDOWS-001
Authority repo: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo483-short-burst
Branch: docs/wo-p1-483-short-burst-hardening
Base SHA: 90d92bff51f1547548199be941c85c54d0a9fd3a
Dispatch HEAD: 11c777f99542bd80b64341be655a0094d16ca6be

## Goal

Eliminate the recurring perceived-hang pattern by making short-burst orchestration, bounded output and timeout recovery explicit in A-Faster without weakening durable recovery or creating a second scheduler/retry authority.

## Frozen SHORT_BURST default loop

Every burst follows exactly:

```
RECOVER EXACT EVIDENCE -> ONE BOUNDED ACTION/DISPATCH -> USER CHECKPOINT -> NEXT BURST
```

This is the frozen default for the whole contract below. One burst = one bounded
action (or one bounded dispatch), then a checkpoint, then the next burst. No
burst may contain a second material action after an UNKNOWN/RECOVER outcome.

## Root-cause map (observed failure class -> root cause -> remedy)

| Observed failure class | Root cause | Remedy seam |
|---|---|---|
| Broad output/search/read exceeds wrapper limits | No bounded-output seam exists anywhere in repo; output size is accidental, harness-dependent | Default budgets (§Budgets) + head/tail slicing; policy now, deterministic constants later |
| Wrapper timeout while child may still run | Timeout was implicitly treated as failure; no UNKNOWN/RECOVER rule | §Timeout semantics: timeout => UNKNOWN/RECOVER, never FAILURE; reconciliation gate before any redispatch |
| Long foreground build/test occupies a turn too long | No foreground/background threshold exists | §Foreground/background threshold: >120s estimate => background-first with pointer |
| Repeated broad recovery scans add latency | Census/recovery has no query budget; broad scans are the fallback by default | Exact-query-first + one bounded escalation per burst; broad scans stay out of the critical path |
| Pre-model transport failures waste turns | Dispatch/transport failures are conflated with execution outcomes | §Transport taxonomy: typed pre-model classes, never acceptance evidence |
| Opaque tool cards hide progress | Checkpoints implicitly depend on tool-card UI rendering | Durable user-visible checkpoint cadence independent of tool cards |

## Reuse map (verified seams, read at dispatch HEAD 11c777f)

| Capability | Existing seam | Where | Reuse verdict |
|---|---|---|---|
| Durable pointers | `pointer.md` / `execution-pointer.json` under `runs/<WO>/<lane>/attempt-NNNN-<random-id>/` with minimum fields (lane_ref, delegated_run_id, binding_digest, destinations, replay_safety, expected_completion) | `.agents/skills/a-faster/references/durable-lanes.md` §3 | REUSE verbatim; no new pointer schema |
| Pointer parse/enumerate/recover (pure, fail-closed, write-free) | `parse_delegated_run_id`, `attempt_dir_name/path`, `enumerate_attempt_dirs`, `read_pointer_run_id`, `recover_attempt_run`; stable code-only `DelegatedRunArtifactError` codes | `src/a_conductor/delegated_run_artifacts.py` | REUSE as-is; never modify in this WO |
| Exact PID liveness (read-only observation) | `observe_child_process(pid)` returns `{pid, created_epoch_ms, executable, parent_pid}`, fail-closed `None`, Windows/Linux/macOS | `src/a_conductor/zcode_process_truth.py` | REUSE for exact-PID reconciliation; a bare PID number alone is never liveness |
| Exact-owned process lifecycle (spawn/stop exact fingerprinted PID) | `OwnedProcessSpec` + injected observer, stop only exact proven PID | `src/a_conductor/owned_process.py` | REUSE precedent; no new kill/spawn authority |
| Result/exit markers | Pointer `destinations: task_ref, result_ref, exit_ref, log_ref`; recover algorithm step 3 reads and classifies them | durable-lanes.md §3/§5 | REUSE; exit/result artifacts are the only terminal evidence |
| Liveness classification | `STARTING/RUNNING/WAITING/STALLED/TERMINAL_UNHARVESTED/INTERRUPTED/TERMINAL/UNKNOWN`; truth priority `ACTUAL PROCESS -> DURABLE EVENTS -> PROVIDER/CI -> OPERATOR PROJECTION -> CHAT CLAIM`; unknown/contradictory fails closed | `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md` | REUSE only; never a second state machine |
| Census + dispositions (RUNNING never redispatch; TERMINAL_UNHARVESTED harvest-first; STALLED reconcile; UNKNOWN fail closed) | A-Faster delegated-run census + recovery dispositions table | `.agents/skills/a-faster/SKILL.md`; durable-lanes.md §5 | REUSE; SHORT_BURST adds budgets, not dispositions |
| Bounded output | NONE executable. Only traces: harness `background_process` log-tail retention (outside repo) and WO155 audit note in `docs/agent-collab/AGENT_TASKS.md` L222 (unbounded stdout accumulation was an accepted-blocker finding) | — | GAP: policy now (§Budgets), helper constants later (§Future scope) |
| Foreground/background execution | Harness background tools exist outside repo; in-repo background semantics live only in runner internals that are out of scope | — | GAP: threshold policy now; no runner change in this WO |

## Behavior classification

**A. Orchestration policy only (no repo artifact needed; binds every executor of this WO family):**

- SHORT_BURST default loop (frozen above).
- One burst = one bounded action/dispatch; no second material action after UNKNOWN/RECOVER in the same burst.
- Redispatch forbidden until pointer + result/exit + exact-PID reconciliation.
- Pre-model transport failures are never acceptance evidence.

**B. A-Faster skill policy (future edit to `.agents/skills/a-faster/**` after #480 releases the hotspot):**

- Default budgets and staged escalation (§Budgets) as skill text + new `references/short-burst.md`.
- Wrapper timeout => UNKNOWN/RECOVER rule added to census dispositions.
- Foreground/background threshold (>120s estimate => background-first) as routing rule.
- User-visible checkpoint cadence as reporting rule (extends existing "Routing output additions").

**C. Executable helper/runner change (future, smallest set in §Future scope):**

- NEW pure budget/ledger helper exposing frozen constants and deterministic escalation classification; consumes `delegated_run_artifacts` and liveness vocabulary; performs no writes, no process operations, no network.
- NO change to `delegated_run_artifacts.py`, `owned_process.py`, `zcode_process_truth.py`, or shared runner behavior — they are consumed, never modified.

**D. Not enforceable in repo code:**

- Wrapper/harness timeout duration and UI rendering of tool cards (harness-owned).
- Chat-visible user attention between bursts (human-owned).
- Cross-harness output retention policies (harness-owned).
- Enforcement against executors that bypass skill loading entirely (authority layer owns this; repo can only fail closed on its own artifacts).

## Default budgets (frozen values; skill policy now, helper constants later)

| Budget | Default value | Notes |
|---|---|---|
| Single command output | ≤ 200 lines or ≤ 8 KiB (head+tail slice), never full dump | applies to shell/build/test output folding |
| Exact-file read | ≤ 400 lines per read by default | targeted single-file reads |
| Glob/query result set | ≤ 50 paths or ≤ 40 matches, ≤ 5 context lines | broad result sets are truncated and reported as truncated |
| Bounded exact queries per burst | ≤ 2 before escalation | not-found/ambiguous counts as a failed query |
| Foreground command time | ≤ 120 s | longer => background-first |
| Background polling | ≤ 1 poll per 30 s, ≤ 10 polls per burst, then yield turn with checkpoint | bounded polling only; no busy wait |

**Staged escalation rules.** Broad recursive scans are forbidden in the
critical path. Escalation is allowed only when a bounded exact query FAILS
(not-found or ambiguous), at most one escalation step per burst, widening
exactly one dimension (e.g., one glob family or one include-set), still
bounded (≤ 3 directory levels or ≤ 200 candidate paths). Every escalation is
recorded in the burst checkpoint. A second failed escalation ends the burst:
checkpoint the typed blocker and plan the next burst; do not scan harder.

## Timeout semantics

- Wrapper/harness timeout => classify `UNKNOWN/RECOVER`, never automatic FAILURE.
- `UNKNOWN/RECOVER` blocks redispatch until reconciliation proves one of:
  exact recorded PID dead (`observe_child_process` returns None against the
  recorded pid+identity) AND `result_ref`/`exit_ref`/`log_ref` reconciled AND
  git/worktree/HEAD/dirty state compared against `dispatch_head`/`mutable_scope`.
- If the exact PID is still live with matching creation/command identity => `RUNNING`: attach or wait; never kill broadly, never redispatch.
- Terminal result detail (COMPLETED_ACCEPT / FAILED / ABNORMAL_EXIT, etc.) comes only from result/exit artifacts, never from wrapper behavior alone.
- Precedent: WO438 post-main harness returned exit 1 after all gates passed (PowerShell `[Math]::Max` arity) — wrapper exit code alone is neither acceptance nor failure evidence.

## Foreground/background threshold

- Any dispatch with an expected duration > 120 s MUST be background-first: write the durable pointer (existing `pointer.md` fields) before or at launch, recording PID + verified command identity when observable, plus `log_ref`/`exit_ref` destinations.
- A foreground command crossing the 120 s boundary without completing is treated exactly as a wrapper timeout: `UNKNOWN/RECOVER`, reconcile before any further action in that hotspot.
- Background lanes are observed only by bounded polling (budget table) plus event-style re-entry per the existing collision-pulse refresh boundaries; a fresh turn never assumes background state without re-deriving it from pointer + process + artifacts.

## Pre-model transport failure taxonomy

Typed classes; each proves only that the dispatch did not produce model execution evidence:

| Class | Meaning | Evidence status |
|---|---|---|
| `DISPATCH_POINTER_MISSING` | no durable pointer written before/at launch | dispatch invalid; retry requires fresh pointer first |
| `HARNESS_ROUTE_FAILURE` | harness/model route rejected or never launched | proves nothing about child outcome; quota/route gates re-run before any redispatch |
| `QUOTA_EXHAUSTED` / `QUOTA_UNKNOWN` | provider quota gate | routing evidence only |
| `AUTH_OR_ENTITLEMENT` | credential/entitlement failure | routing evidence only |
| `TRANSPORT_CONNECTIVITY` | network/relay failure pre-model | proves nothing about any prior child process |
| `WRAPPER_TIMEOUT_UNKNOWN` | timeout with child state unproven | => `UNKNOWN/RECOVER` per §Timeout semantics |

None of these classes may become acceptance evidence, completion evidence, or
failure-of-record for the underlying task. The only acceptance path remains:
pointer → result/exit artifacts → deterministic verification → review/merge gates.

## User-visible checkpoint cadence

Independent of opaque tool cards, checkpoints are written to the active WO/Issue
checkpoint or the lane result destination:

- one line before each burst (what/where/why);
- one line after each terminal/harvest outcome;
- immediately at any escalation, any `UNKNOWN/RECOVER`, and any `WAITING/STOPPED`;
- at least every ~10 minutes of wall time inside one material lane;
- content reuses the existing lifecycle pulse minimum fields (durable-lanes.md §3.1); no new format.

## Canonical invocation equivalence

For substantial A-Sunday Conductor work, the short user instruction

`ใช้ A-Faster ทำงานต่อ ตาม Roadmap`

is the canonical shorthand for the full acceleration intent. After normal
recovery/authority gates, it MUST behave as if the user had explicitly asked:

- continue the accepted roadmap automatically;
- recover/harvest outstanding delegated executions before new dispatch;
- reconstruct the one global `3 mutable + 1 independent review` WIP budget;
- fill every independent safe READY slot rather than leaving capacity idle;
- prefer GLM-5.3 MAX for eligible R2/R3 implementation/repair/required review;
- use GLM-5.3-Flash for bounded read-only shaping/reconnaissance/advisory work;
- keep GPT-5.6 Sol active as fleet integrator for decomposition, collision
  prevention, deterministic verification, fan-in, repair, acceptance and next
  READY routing;
- prevent duplicate work by reconciling durable delegated-run identity,
  exact claim/scope/worktree/HEAD and live pointer/process/result/exit evidence
  before every material dispatch;
- never overlap a protected hotspot or an already-owned Work Order merely to
  maximize agent count;
- continue safe bounded work autonomously without requiring the user to repeat
  the long-form GLM/multilane wording each session.

Therefore the short form and the verbose form are semantically equivalent as
routing intent. The verbose form adds emphasis only; it does not grant more WIP,
authority, quota, collision tolerance, or permission to bypass safety gates.

### Duplicate-dispatch acceptance gate

The #493 incident demonstrated why semantic equivalence must be backed by a
dispatch dedupe gate. Before any material GLM launch, the integrator MUST prove
that no matching active delegated execution already owns the same
`task/claim + repo/worktree + mutable-scope hotspot`. A wrapper timeout,
missing tool card, chat/session loss, or stale local executor context is
`UNKNOWN/RECOVER`, never permission to launch another writer. If a matching
run is RUNNING, attach/wait; if TERMINAL_UNHARVESTED, harvest; if
STALLED/INTERRUPTED/UNKNOWN, reconcile replay safety before any takeover.

## Smallest FUTURE mutable path set (only after #480 / PR #490 is accepted/merged/post-main)

1. `docs/work-orders/WO-P1-483-a-faster-short-burst-hardening.md` — this contract (already mutable in this docs-only slice).
2. `.agents/skills/a-faster/references/short-burst.md` — NEW: budgets, escalation rules, transport taxonomy tables (skill policy text).
3. `.agents/skills/a-faster/SKILL.md` — bounded edit: add SHORT_BURST section pointer, timeout/UNKNOWN disposition, foreground/background threshold, checkpoint cadence to routing output.
4. `src/a_conductor/short_burst_guard.py` — NEW pure helper: frozen budget constants, escalation-ledger classification, `UNKNOWN/RECOVER` reconciliation checklist derivation consuming `delegated_run_artifacts` outputs and liveness vocabulary. Write-free, process-free, network-free.
5. `tests/test_short_burst_guard.py` — NEW tests (RED-first per matrix below).

Explicitly NOT in scope, ever, for this WO: `delegated_run_artifacts.py` and its
tests, `owned_process.py`, `zcode_process_truth.py`, shared runner behavior,
any scheduler/task-DB/retry authority, any JEV #484/#486/#488/#492 artifact.

## Deterministic RED/test/lint matrix (future implementation slice)

RED first (before `short_burst_guard.py` exists):

- `python -m pytest tests/test_short_burst_guard.py -q` — fails (import error) = RED.

Then, after implementation:

- `python -m pytest tests/test_short_burst_guard.py -q` — GREEN; must cover:
  1. budget constants equal the frozen table values exactly;
  2. escalation ledger: ≤2 failed exact queries allowed; 1 escalation allowed only after a failed query; broad recursive scan in critical path denied; second escalation denied with typed reason;
  3. reconciliation derivation on synthetic attempt dirs (legacy + suffixed naming): exit/result absent + PID unprovable => `UNKNOWN/RECOVER`; recorded PID dead + artifacts absent => `INTERRUPTED`; artifacts present => `TERMINAL_UNHARVESTED`; `RUNNING` case never recommends redispatch;
  4. transport taxonomy: every typed class maps to `not acceptance evidence`; no class maps to a terminal task outcome;
  5. timeout fixture maps to `UNKNOWN`, never `FAILED`.
- `python -m pytest tests/test_delegated_run_artifacts.py -q` — stays green (proves no protected-source drift).
- `python -m py_compile src/a_conductor/short_burst_guard.py` — exit 0.
- `git diff --check` — clean.
- UTF-8 readback with strict decoding for all touched docs — no decode errors.
- Scope check: `git status --porcelain` tracked deltas exactly the declared paths.

## Migration notes

- This slice is docs-only: the contract above binds behavior by text immediately for any executor reading this WO; the helper (path 4) only later turns budgets/ledger into deterministic constants. No runner or protected-source behavior changes now.
- Implementation order after #480 releases the hotspot: RED tests (5) → helper (4) → skill edit (2,3) → full matrix → independent review per risk class (R2; escalate to R3 review only if execution semantics change beyond classification/reporting).
- Existing lanes are unaffected: `durable-lanes.md` identity grammar, census dispositions, and `delegated_run_artifacts` recovery behavior are consumed as-is; legacy `attempt-NNNN` directories keep recovering unchanged.
- If a future harness natively provides bounded output/background tooling, the skill policy references it instead of duplicating it; the helper constants remain the repo-side fail-closed floor.

## Non-authority invariants (binding)

- No second scheduler, task DB, retry engine, lease/registry, or completion state machine is created by any slice of this WO.
- Liveness classes and dispositions are reuses of `EXECUTION_LIVENESS_PROTOCOL.md` and `durable-lanes.md` §5 only.
- Budgets bound the agent's own critical path; they never weaken claim/lease/ownership/secret/destructive-operation gates.
- A model or wrapper claiming DONE is never acceptance evidence; only the declared verification path is.

## Current mutation restriction

DOCS ONLY. Until #480 follow-up PR #490 is accepted/merged/post-main:
- do not modify .agents/skills/a-faster/**
- do not modify delegated_run_artifacts.py or its tests
- do not modify shared runner behavior
- do not overlap JEV family scopes

RELEASED for the attempt-0002 implementation slice: PR #490 was merged
post-main (fb455f1), so paths 2–3 of the future mutable set plus the
invocation-contract regression test are now mutable under the attempt-0002
task packet's exact four-path scope; see the implementation checkpoint below.

## JEV protected scope

Do not touch any JEV #484/#486/#488/#492 scripts/tests/fixtures/docs/roadmap.

## This shaping slice mutable scope

- docs/work-orders/WO-P1-483-a-faster-short-burst-hardening.md

Flash shaping may read current A-Faster docs/helpers but must leave all other tracked files unchanged.

## User-directed hook-enforcement extension (2026-09-23)

Latest user direction requires A-Faster not only to describe the sequence but to
use hooks as a backstop so an AI Agent cannot silently skip required stages.

This WO therefore freezes two enforcement layers:

1. **Skill/policy layer now:** mandatory material-boundary sequence
   `ENTRY -> RECOVERY -> PRE_DISPATCH -> PRE_MUTATION -> PRE_FREEZE -> PRE_REVIEW -> PRE_MERGE -> POST_MAIN`,
   deterministic regression coverage, explicit `POLICY_ONLY` vs
   `GUARD_ENFORCED` vs `OBSERVE_ONLY`, and fail-honest reporting.
2. **Executable GUARD child next:** reuse/extend Hook Contract v1 `GUARD` at
   invocation boundaries. Authority/security GUARD failures fail closed. This
   child must reuse existing dispatch/dedupe/claim/merge authorities and may not
   create a hook task store, retry engine, lease system or second control plane.

Current limitation is binding and explicit: Hook OBSERVE telemetry on main does
not make material actions unskippable. Full technical enforcement requires the
material dispatch/mutation/merge entry points to route through an accepted
executable GUARD / Command Gateway path. Raw shell/Git/tool calls remain a
possible harness-level bypass until that routing is accepted; A-Faster must
never mislabel such a path as `GUARD_ENFORCED`.

Reuse classification for the executable follow-up: **EXTEND** existing HOOK-0 /
Hook Contract v1, existing duplicate-execution guard / supervised execution
seams, and accepted mutation/merge authority. Do not create a parallel Hook Bus,
scheduler or authority store. HOOK-0 repair PR #385 must be reconciled/accepted
before a new GUARD implementation pins that contract as its dependency.

## Implementation slice checkpoint (attempt-0002, Windows lane)

- Claim: WO-P1-483-SHORT-BURST-IMPLEMENTATION-WINDOWS-002
- Dispatch HEAD: b4e330809eaed5f132b989c24ca14fb844533362 (base 90d92bf)
- Mutable scope (exact, from the task packet): `.agents/skills/a-faster/SKILL.md`, `.agents/skills/a-faster/references/short-burst.md` (NEW), `tests/test_a_faster_invocation_contract.py` (NEW), this file. `src/a_conductor` untouched; JEV/#482/#493/#265 protected scopes untouched.
- RED evidence: `python -m pytest tests/test_a_faster_invocation_contract.py -q` before edits => 8 failed, 2 passed (missing roadmap shorthand, equivalence statement, full default-profile markers, Sol fleet-integrator role, PRE-DISPATCH DEDUPE GATE, short-burst reference + link, WO literal).
- GREEN evidence: same command after edits => 10 passed in 0.17s (2026-09-23, Windows lane); `tests/test_delegated_run_artifacts.py` stays 127 passed; `git diff --check` clean; strict UTF-8 readback clean for all three touched markdown files.
- SKILL.md changes (bounded): invocation contract expanded to the three canonical clauses + emphasis-only equivalence + enumerated default profile; new `## PRE-DISPATCH DEDUPE GATE` section bound into the GLM dispatch checklist; Sol fleet-integrator role named; new `## SHORT_BURST execution policy` section linking `references/short-burst.md`.
- `references/short-burst.md` (NEW): frozen loop, exact-path-first + one bounded staged escalation, frozen budget table, timeout semantics (UNKNOWN/RECOVER), >120 s background-first rule, pre-model transport taxonomy, tool-card-independent checkpoint cadence.
- Tests are semantic assertions (section extraction + markers), not full-file snapshots.
- Changes left uncommitted for GPT-5.6 Sol harvest; no commit/push/merge performed by this slice.
