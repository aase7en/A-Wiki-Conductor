# WO-P1-078 — A-Conductor North Star execution plan

Status: READY
Owner: GPT-5.6 Sol (integrator) + bounded workers per READY node
Branch: eat/north-star-runtime-sunday-family
Base: c72a550287a8c59d2361112b489e528639adeaa6
Current HEAD at planning: da103748ffc9768a9fe76f17bfa9c03fc1896015

## Objective

Advance A-Sunday Conductor toward the North Star durable local/hybrid execution fabric while preserving A-Wiki as brain/policy/memory, keeping runtime costs low, and finishing the reopened Sunday Family particle fidelity + gentle gaze/head-follow acceptance gap.

## Non-negotiable architecture

- A-Wiki remains brain, durable knowledge, policy, reusable procedures, and cross-project memory authority.
- A-Conductor remains manager/router/control plane: durable tasks, authority, scheduling, safety, evidence, recovery, verification, review/repair.
- Runtime integrations are replaceable execution hands only.
- Desktop Commander is an optional execution runtime, never task authority, planner, memory system, MCP gateway, or raw operator-shell bypass.
- Reuse existing durable job control/native execution/output backpressure before adding new state machines.
- Disabled/unused runtimes must have near-zero idle cost: no background polling, no periodic subprocess, no always-on discovery loop.
- Shared main and other owners' GE worktrees are out of mutation scope.

## Current verified starting point

- 63ac2fa refines Sunday Family GPU path: 17,280 adaptive particles at 120 px, local weighted head parallax, six eye gaze regions, bounded motion.
- da10374 adds pure Desktop Commander runtime metadata/contracts with no network/subprocess/thread/polling dependency.
- Targeted North Star regression: 66 passed, 1 environment-only Tk skip.
- GitHub latest release remains v0.6.0; v0.7.0 closeout must remain isolated.
- PR #102 GE-005A and PR #104 GE-6 remain open and must not be overwritten or duplicated.

## Dependency graph / execution frontier

N0 Safety baseline -> N1 Sunday Family visual acceptance

N0 -> N2 Runtime registry/profile integration -> N3 Bounded Desktop Commander transport contract

N3 + (GE-005A green/merged) + (GE-6 green/merged) + GE-7 dispatch seam ready -> N4 Durable execution bridge

N4 -> N5 Remote-device/on-demand capability -> N6 Failure/recovery/security audit -> N7 Operator UI/runtime routing -> N8 Release integration

N1 and N2 are independent READY tasks. N3 may proceed only in additive/new seams. N4 is BLOCKED until graph ownership gates are satisfied.

## N0 — Safety + baseline gate [READY]

Goal: freeze a known safe point before further implementation.

Actions:
1. Reconcile origin/main, open PRs, active worktrees/claims, branch/HEAD/dirty state.
2. Preserve shared main, GE-005A, GE-6, live connector ports 18011-18015, and A-Wiki HOLD.
3. Run focused baseline tests + compileall + diff-check.
4. Record exact environment limitations separately from code failures.

Exit: SAFE_TO_MUTATE=YES for this isolated worktree and bounded scopes only.

## N1 — Sunday Family production visual acceptance [READY / P0 UX]

Goal: finish the user-visible requirement, not merely unit-test motion.

Actions:
1. Run real WGL production-size renderer from this branch using the known GPU-capable environment.
2. Verify observable framebuffer, actual particle count, GPU error state, create/destroy cleanup, pointer return.
3. Exercise pointer sweep across whole application; verify eyes follow ~1-2 px and three heads turn subtly without chest/badge translation.
4. Compare 120 px installed/frozen appearance against master ssets/sunday-family-particle.png.
5. Benchmark buffer-build time, idle CPU/RAM, active animation CPU/RAM/GPU, repeated 5-minute run and create/destroy cycles.
6. Tune only evidence-backed constants/regions; no visual redesign outside the logo.
7. Verify forced GPU-disabled fallback remains <=7 Canvas items and responsive.

Acceptance:
- recognizable fine Sunday Family portrait at real header size;
- local head/gaze motion reads naturally and non-uncanny;
- no whole-image slide;
- no resource growth/leak or UI jank;
- user-visible visual evidence captured before DONE.

## N2 — Runtime registry + routing profile [READY / P0 architecture]

Goal: make Desktop Commander a first-class optional runtime capability without activating it.

Actions:
1. Integrate the pure runtime profile at the existing runtime/capability seam.
2. Add capability matching traits for local vs remote-device modes.
3. Make runtime availability explicit: INSTALLED/AVAILABLE/UNAVAILABLE/UNKNOWN; never infer readiness from configuration alone.
4. Keep imports lazy/optional; A-Conductor startup must not require Node/Desktop Commander.
5. Add deterministic selection policy: native fixed adapters first when sufficient; semantic Serena when code intelligence matters; Desktop Commander when interactive/remote/device-specific execution is materially useful.

Acceptance:
- zero always-on process/network/polling cost when unused;
- no new task state machine;
- no scheduler duplication;
- runtime-neutral core domain remains intact.

## N3 — Bounded Desktop Commander transport contract [READY after N2 / additive only]

Goal: define how Conductor may call Desktop Commander without exposing arbitrary model-to-shell authority.

Design:
- Conductor receives opaque pre-authorized operation refs, never free-form shell text from operator protocol.
- Resolver maps an operation ref to one fixed tool family + project/device scope + timeout/output budget + mutation intent.
- Transport returns bounded structured results/evidence refs; large output is paged/tail-read, not injected wholesale into model context.
- Credentials/device tokens remain external secure configuration; never Git/docs/logs.
- Allowed-directory/blocklist from Desktop Commander are defense-in-depth only, not Conductor's authority boundary.

Initial fixed families:
- project file read/search;
- bounded process start/inspect/read-output/interact for approved workflows;
- document/data read where native adapters do not already provide the capability;
- remote-device execution only with explicit registered device identity.

Forbidden in this node:
- generic raw shell API exposed to model/operator;
- direct Git mutation families;
- arbitrary file writes outside project scope;
- scheduler/job-state changes;
- always-on remote discovery.

## N4 — Durable job-control bridge [BLOCKED on GE gates]

Preconditions:
- PR #102 / GE-005A green, reviewed, merged and reconciled;
- PR #104 / GE-6 green, reviewed, merged and reconciled;
- GE-7 dispatch contract/implementation seam confirmed against current main.

Goal: route Desktop Commander execution through existing durable execution identity, duplicate protection, claims, checkpoints, output backpressure and recovery.

Required behavior:
1. Reserve/claim/gate using existing durable job lifecycle.
2. Resolve runtime adapter only after worker/project/device authority is re-observed.
3. Dispatch one bounded operation with stable execution identity/fingerprint.
4. Transport loss != execution failure; reconnect attaches/reconciles original work.
5. Duplicate request attaches/reuses; never blindly launches twice.
6. Results enter VERIFYING/REVIEW flow; runtime saying DONE is not task completion authority.

## N5 — Remote device on-demand mode [BLOCKED on N4]

Goal: gain Desktop Commander remote-machine reach without making A-Conductor heavy.

Actions:
- explicit operator opt-in per registered device;
- connect/probe only when task routing needs the device or user requests status;
- bounded reconnect budget with backoff; no hot loop;
- durable device identity + capability snapshot, but secrets/tokens remain external;
- fail closed on stale/unknown identity;
- support local workstation first; Pi/other devices only after capability evidence.

Idle invariant: if no task needs Desktop Commander, no Desktop Commander connector needs to be running because of A-Conductor alone.

## N6 — Failure, security, recovery and performance audit [BLOCKED on N4/N5]

Scenarios:
- device offline before dispatch;
- connection lost while execution may still be running;
- duplicate dispatch/retry;
- stale device identity or changed project root;
- oversized output/log pagination;
- timeout and long-running session resume;
- denied filesystem scope;
- prompt/content attempts to induce raw shell bypass;
- A-Conductor restart during remote execution;
- Desktop Commander unavailable/not installed;
- native/Serena fallback selection where appropriate.

Performance gates:
- no periodic subprocesses/polling when idle;
- bounded memory growth;
- bounded context/output sizes;
- startup regression measured against baseline;
- Sunday Family animation remains independent of execution-runtime workload.

Verdict required: AUDIT_PASS or AUDIT_PASS_WITH_NOTES; blocking trust-boundary/recovery findings loop back before UI/release.

## N7 — Operator UI + cost-aware runtime routing [BLOCKED on N2, integrate after N6]

Goal: surface capability without clutter or hidden automatic authority.

UI principles:
- Desktop Commander appears under optional Runtime/Execution Surface details, not as the product identity.
- Show connection/device/project provenance separately from configured/bound state.
- Missing evidence = UNKNOWN, never READY by assumption.
- Explain why a runtime was selected: cheapest/safest sufficient capability first, premium/durable/remote only when materially valuable.
- No continuous status subprocess; reuse cached/event-driven observations and explicit refresh/state-change events.

## N8 — PR / release integration [BLOCKED on all applicable gates]

Sequence:
1. Keep Sunday Family v2 and runtime-profile changes reviewable as coherent commits/PR slices.
2. Do not merge North Star branch while v0.7.0 exact-release closeout is unresolved unless release owner explicitly rebases the boundary.
3. Rebase/reconcile from exact current main only after v0.7 publication/closeout and GE ownership state is known.
4. Independent review: Standards axis + Spec axis.
5. Targeted tests -> full suite -> realistic E2E -> security/reliability/performance audit.
6. Open PR; inspect actual remote diff; classify CI; repair evidence-backed failures only.
7. Re-audit final PR HEAD after CI green.
8. Merge under repository policy, fetch/reconcile, then perform frozen/install post-merge verification.

## Parallel execution policy

Safe parallel frontier after N0:
- Lane A: N1 Sunday Family visual/E2E only.
- Lane B: N2 runtime registry/profile only.
- Lane C: N3 contract/research after N2, additive files only.

Do not parallelize N4 against GE-6/GE-7 mutable scopes. Each worker must receive a bounded contract with its own worktree/branch/allowed files and handoff.

## Completion definition

North Star increment is not DONE until:
- Sunday Family passes real visual + resource acceptance;
- runtime profile is integrated with near-zero idle cost;
- Desktop Commander execution is bounded by Conductor authority/durable lifecycle, not raw MCP shell;
- disconnect/retry/idempotency/output limits are realistically verified;
- A-Wiki brain ownership is unchanged;
- final diff/review/CI/E2E/audit/post-merge evidence is durable;
- a fresh agent can continue from repository SSoT without chat memory.

## Immediate next safe action

Execute N0, then start N1 and N2 as independent bounded lanes. Do not start N4 until the GE merge gates are proven from actual GitHub/main state.
