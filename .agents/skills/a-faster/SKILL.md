---
name: a-faster
description: Accelerated multi-device / multi-harness profile for the canonical A-FastTask router/binder. Use for substantial A-Sunday Conductor work that benefits from coordinated Windows + macOS + GitHub lanes, Kilo/Claude Code GLM delegation, fast lane recycle, and safe merged-worktree cleanup. MUST load and obey ../a-fasttask/SKILL.md first. Adds routing constraints only; grants no task, claim, cleanup, provider, review, merge, or acceptance authority.
---

# A-Faster — accelerated A-FastTask profile

A-Faster is an **overlay on A-FastTask**, not a second control plane.

Before using this profile, read and obey:

`../a-fasttask/SKILL.md`

If the base skill is unavailable or conflicts with this file, fail closed as
`A_FASTTASK_BASE_MISSING_OR_CONFLICT`. The base skill owns generic recovery,
claim, risk, evidence, cleanup, and authority rules. A-Faster only adds
multi-device and multi-harness routing constraints.

## Trigger

For **substantial A-Sunday Conductor engineering work**, A-Faster is the
default acceleration overlay after canonical A-FastTask has bound authority.
Also use it whenever one or more are true:

- the user explicitly asks for A-Faster / faster multilane execution;
- independent READY work can run concurrently on Windows and macOS;
- Kilo Code CLI and Claude Code CLI can safely own different bounded lanes;
- a finished lane should be recycled after exact closeout/cleanup proof;
- the task needs coordinated Workers + RDC + GitHub remote truth.

Do not force A-Faster onto trivial Q&A, a single obvious mechanical edit, or
already-bound mid-lane work that needs no new routing decision. These exclusions
preserve A-FastTask's negative triggers and avoid routing overhead for tiny work.

### Invocation contract (one clause is enough)

For substantial A-Sunday engineering, any of these canonical user clauses —
**"use A-Faster"**, **"ใช้ A-Faster"**, or the roadmap shorthand
**"ใช้ A-Faster ทำงานต่อ ตาม Roadmap"** — requests the whole acceleration
behavior of this profile for that session. The roadmap shorthand is
semantically equivalent to the verbose multilane intent
("ใช้ A-Faster ทำงานต่อ ตาม Roadmap และสั่งงาน GLM-5.3/GLM-5.3-Flash หลาย lane
พร้อม GPT-5.6 Sol แบบผสานงานกัน ไม่ชนกัน ไม่ซ้ำซ้อน"): the verbose form
adds emphasis only and never grants more WIP, authority, quota, or collision
tolerance than the short form. After the normal A-FastTask binding and
authority gates, the routed default profile is:

- delegated-run recovery/harvest and the mandatory entry census first;
- one global WIP reconstruction across every device/harness — normal active
  compute remains `3 mutable + 1 independent review`; Issue #537 additionally
  permits up to 2 borrowed mutable claims while qualifying base lanes are
  truthfully waiting, without ever exceeding 3 simultaneous active mutations;
- WAIT_AWARE_AUTO_BACKFILL: A-NightShift checkpoints typed waits and A-Faster
  immediately AUTO-FILLs independently SAFE_READY capacity instead of idling;
- GLM-first long-running labor with MAX/Flash task-class routing:
  GLM-5.3 MAX for eligible R2/R3 implementation/repair/required independent
  review; GLM-5.3-Flash only for bounded read-only
  reconnaissance/shaping/precheck/advisory;
- GPT-5.6 Sol as fleet integrator for decomposition, collision prevention,
  deterministic verification, fan-in, repair, acceptance, and next-READY
  routing, with direct Sol execution only as the eligible fallback when GLM
  routes are blocked;
- the default Windows/macOS/GitHub execution surfaces below with event-driven
  cross-device collision and lifecycle-status pulses, plus advisory
  Ponytail/Caveman consideration;
- autonomous continuation through the next safe READY steps; and
- no-overlap: one mutable hotspot has one mutation owner, always enforced
  through the collision gate and the PRE-DISPATCH DEDUPE GATE.

The user need not restate multiagent/multilane/multitasking/device-routing/
GLM/fallback/advisory-skill instructions each session, and does not need to
repeat a long "continue / fill another lane while this waits" instruction on
every wait transition. An `A_FASTER_ACTIVE` tasking receipt includes the
wait-aware backfill loop below until a real goal/stop gate, terminal completion,
or explicit deactivation. The clause routes only; the normal A-FastTask binding
and authority gates still apply.

## Global WIP and no-collision rule

The default budget remains **one global budget across every device, harness,
repository, and CROSS_REPO compatibility-set member**:

- max 3 **simultaneously active mutable implementation lanes**;
- max 2 additional **borrowed mutable claims** under the accepted Issue #537
  wait-aware capacity contract;
- max 1 independent read-only review lane.

Thus total mutable claims may reach 5 while active mutation compute remains
`<= 3`. A borrowed claim is continuity capacity, not permission for a fourth
or fifth simultaneous mutation. Recovery/blocker work still consumes actual
active headroom; no label or session creates free compute. Issue #537 is the
accepted capacity change for borrowed claims only.

Never multiply WIP by device, harness, repository, or session.

All ChatGPT sessions, devices, and harnesses for the project share this one
global WIP budget. Every invocation reconstructs current occupancy from
durable evidence (census + lane occupancy matrix), never from chat/session
memory. A session or tool timeout is not failure and never resets occupancy:
a slot stays occupied until census evidence shows that lane terminal/absent
per the disposition rules.

AUTO-FILL: after recovery/census/harvest and the collision gate,
automatically fill every free safe active slot from independent READY nodes up
to the global active `3 mutable + 1 review` budget — dispatch-first,
harvest-later. Issue #537 may retain up to 2 additional borrowed mutable claims
in waiting/parked continuity state, but never increases active mutation above 3.
Do not manufacture work to occupy slots and do not preempt active owned
lanes. Do not serialize independent GLM jobs just to conserve quota: when
refreshed quota evidence says `QUOTA_AVAILABLE`, treat the remaining amount
as capacity evidence, not a reason to self-throttle. Still refresh quota
before EACH material dispatch and obey actual
`QUOTA_EXHAUSTED`/auth/transport/cost gates.

`1 MUTABLE HOTSPOT = 1 MUTATION OWNER`

Two devices may work in the same project only when each mutable lane has a
different claimed hotspot and normally a different worktree/branch. Never let
Windows and macOS mutate the same branch/worktree/hotspot concurrently.

Every A-Faster lane adds these fields to the normal A-FastTask binding:

- `DEVICE_ID` / verified hostname or connector device id;
- `HOST_OS`;
- `EXECUTION_SURFACE` (Worker, RDC, GitHub, Kilo, Claude Code, etc.);
- `HARNESS_ID`;
- `MODEL_ID` + effort/variant when a model is used;
- durable execution/result pointer for delegated work;
- latest cross-device lifecycle pulse + freshness timestamps when the lane is
  material/long-running.

## Utilization enforcement (WO-P1-517)

Underutilization must be machine-detectable (WO-P1-517) without creating
a scheduler or second authority. The pure deterministic classifier
`src/a_conductor/a_faster_utilization_guard.py` consumes structured
utilization facts (lane occupancy, independent READY candidates, structured
quota admission, GLM route readiness, Sol direct-labor state) and emits:

- `FANOUT_TARGET` — admitted lanes AUTO-FILL may dispatch now (budget- and
  candidate-bounded, quota/route admitted, activation-gated);
- `UNUSED_SAFE_CAPACITY` — idle slots inside the global WIP budget that
  independent READY work could occupy;
- `A_FASTER_UNDERUTILIZED` — A-Faster is active and safe READY capacity is
  idle;
- `AUTO_REFILL_REQUIRED` — the refill obligation is due now;
- typed blockers such as `QUOTA_EXHAUSTED`, `QUOTA_UNKNOWN`,
  `SECRET_SOURCE_UNAVAILABLE`, `GLM_ROUTE_BLOCKED`, and
  `NO_INDEPENDENT_READY_WORK`.

The classifier remains a projection only: it creates no scheduler, task store,
claim/lease, provider, dispatch, retry, review, merge, or completion authority,
launches nothing, and never burns or probes quota itself. WO-P1-549 adds
`src/a_conductor/a_faster_auto_refill.py` as the executable auto-refill bridge:
an accepted `A_FASTER_ACTIVE` verdict with `AUTO_REFILL_REQUIRED` and a positive
`FANOUT_TARGET` may consume only an existing scheduler-owned `SchedulePlan` plus
its exact `ParallelReadyTask` mapping, bound the batch to the global lane budget,
and delegate exactly once through the existing `ParallelReadyExecutor`. The
bridge creates no scheduler or second authority and never discovers READY work.

Executable refill does not upgrade every action path automatically. The exact
underlying route remains `POLICY_ONLY` unless the accepted WO-P1-498
`PRE_DISPATCH` guard is proven on that material action path; only that proven
path may be reported `GUARD_ENFORCED`. The refresh-quota-before-each-material-
dispatch rule is unchanged. Verdicts never manufacture work and never relax the
active `3 mutable + 1 review` compute budget. Accepted Issue #537 changes claimed
continuity capacity only (up to 2 borrowed mutable claims), not this
active-compute ceiling.

### Activation receipt — tasking vs explanation

`A_FASTER_ACTIVE` is a proven tasking receipt: a canonical invocation
clause plus the normal A-FastTask binding/authority gates for that
session. Describing, explaining, or quoting A-Faster anywhere — including
the roadmap shorthand inside documentation, review prose, or another
session's transcript — is explanation only (`A_FASTER_EXPLANATION_ONLY`):
it is never an activation receipt, never triggers utilization enforcement,
and never grants WIP, claim, quota, or mutation authority.

### Sol direct long labor while GLM capacity is idle

GLM-first routing is preserved: GPT-5.6 Sol directly executes eligible
long labor only as the fallback when eligible GLM routes are blocked. When
Sol is performing GLM-eligible direct long labor while eligible GLM
capacity is idle (structured quota evidence `QUOTA_AVAILABLE` plus a ready
route), the classifier must emit
`SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE` as the typed blocker. The
integrator then either transfers the labor to an eligible GLM lane or
records why the fallback is legitimate. Idle capacity with fillable
independent READY work and no typed blocker means `AUTO_REFILL_REQUIRED`.

### Codex executor fallback while GLM blocked

GLM-5.3 MAX remains the preferred heavy executor. A Codex fallback is eligible only when structured current evidence says `GLM_ROUTE_BLOCKED`; if `GLM_ROUTE_READY=TRUE`, fallback is forbidden.

Provider-scoped throttling, including a proven five-hour GLM limit, blocks only that provider route. The bounded Codex child still uses the same claim, worktree, scope, WIP, review, and verification gates. It is distinct from the low-cost Codex supervisor, which remains traffic control and never the primary engineer.

When currently exposed and admitted, GPT-6 Luna at effort max is the well-scoped high-volume implementation fallback. GPT-5.6 Sol remains the complex repair/integration/acceptance-bound route. GPT-6 Astra is reserved for exceptional architecture, adversarial review, or difficult debugging escalation.

The binding rule is explicit: **model identity grants no authority** for task ownership, mutation, independent review, merge, acceptance, completion, or retry. An authoring Codex lane cannot satisfy its own independent-review requirement.

If all accepted Codex execution routes are unavailable or usage-limited, emit `CODEX_EXECUTION_CAPACITY_EXHAUSTED`, checkpoint durable state, and defer to the existing NightShift stop rules; do not spin through model names or manufacture work.

### JEV System-One advisory fast path

When the currently accepted JEV mode admits the request, prefer TypeSafe-JEV as a low-cost System-One advisory before expensive model work for deterministic condition checks, evidence relevance scoring, route suggestions, guardrail checks, and bounded confidence estimates. Consume its mode and confidence from accepted JEV authority; never infer that production admission exists because the service responds.

JEV output is advisory evidence only. It never creates or transfers task, claim, mutation, retry, independent-review, merge, acceptance, completion, quota, or NEXT_READY authority. Low confidence, malformed output, policy mismatch, circuit-open state, or provider failure falls back to the normal deterministic/qualified-model path without blind replay. Never manufacture JEV calls merely to consume capacity.

### Device resource capacity projection

Treat verified online execution surfaces as capacity evidence, not as extra authority. Discover the five logical Windows `SunDay-Worker 1..5` surfaces individually and the `SundayMCP Mac` surface when exposed; retain RDC only as a secondary device/process bridge. An ONLINE/READY surface may host an independently SAFE_READY lane after the normal claim/lease/collision/worktree gates, but it never multiplies the global WIP budget by device or plugin count.

Current accepted policy remains at most 3 simultaneously active mutable lanes, up to 2 borrowed waiting/parked claims under Issue #537 semantics, and 1 independent review lane. Future evidence-based expansion belongs to the provider-neutral roadmap in Issue #340 and must compute safe parallelism from non-overlap, machine capacity, provider/quota capacity, and WIP policy rather than assuming that five Workers plus one Mac means six writers.

### No manufactured work, no quota burning

The classifier and any consumer must never manufacture work to occupy
slots: idle capacity with no independent READY work carries
`NO_INDEPENDENT_READY_WORK`, never a dispatch. Never burn quota or spin
probe/redispatch loops to make an underutilization verdict disappear;
quota evidence comes only from the existing
refresh-before-each-material-dispatch flow as structured admission
evidence, and `SECRET_SOURCE_UNAVAILABLE` fails closed.

## Delegated-run launch discipline (WO-P1-517 bootstrap lessons)

Every delegated launch under this profile preserves the three bootstrap
lessons from WO-P1-517 attempts 0001–0003, pinned as
`DELEGATION_LAUNCH_PRECONDITIONS` in the classifier:

1. consume structured admission evidence only — never infer quota
   admission by matching serialized command text; a structured probe
   result of `SECRET_SOURCE_UNAVAILABLE` means admission is unavailable
   regardless of any command-text side channel;
2. launch Kilo with an explicit `--dir` bound to the claimed worktree and
   require in-session repo/worktree/branch/HEAD proof before any
   mutation — never rely on the harness's ambient Active Project;
3. run delegated Kilo with a per-run `share=disabled` override unless
   sharing is separately authorized — ambient user-level share settings
   are never delegation policy.

## Mandatory substantial-session bootstrap

For every substantial A-Sunday Conductor engineering session:

1. attempt lightweight READ-ONLY readiness discovery for **SunDay-Worker 1..5**
   individually; record each as available, unavailable, or a typed surface
   blocker such as `PLUGIN_NOT_EXPOSED_TO_CHAT`; never claim a Worker ran when
   the current harness cannot invoke it;
2. attempt runtime readiness for `SundayMCP Mac` plus RDC/device discovery for
   every connected Windows/macOS device that can materially help the task; record
   online surfaces separately from mutation admission;
3. run the PROJECT/TASK DELEGATED-RUN CENSUS below, including the latest
   durable cross-device lifecycle pulse/freshness evidence for every material
   lane, and reconcile or harvest everything it finds before allocating new
   work;
4. reconstruct the global WIP budget occupancy projection before dispatch:
   at most 3 simultaneously active mutable lanes plus 1 independent read-only
   review lane across every Worker, device, harness, repository and CROSS_REPO
   compatibility-set member; Issue #537 may additionally retain at most 2
   borrowed mutable claims only while actual active mutation remains <=3;
5. if Windows and macOS are both READY and independent work exists, prefer a
   non-overlapping cross-device split; if not, continue on the safe available
   device rather than manufacturing parallelism;
6. keep Worker slots beyond admitted active/borrowed capacity read-only/standby/
   recovery helpers. Five discovered Workers or five mutable claims never mean
   five simultaneous mutable writers.

Readiness discovery is routing evidence only. `WORKER/RDC ONLINE !=
SAFE_TO_MUTATE`; exact task/claim/scope/worktree gates still apply.

## Default device execution routes

These are routing preferences, not authority and not permanent Worker roles:

- **Windows:** prefer exposed SunDay-Worker 1..5 as the primary chat-visible
  repo/code execution surface after exact lane binding. Use RDC secondarily for
  device/process/runtime inspection, recovery, local shell/build/test work, or
  when the required Worker surface is unavailable. For long-running bounded
  inference labor inside an admitted Windows lane, prefer Kilo/Claude CLI with
  the eligible GLM class below.
- **macOS:** prefer an exposed and verified `SundayMCP Mac` plugin as the primary
  chat-visible repo/shell/CLI execution surface; use RDC secondarily for device,
  GUI, process, or recovery work that needs it. Local Serena or similar tooling
  may exist, but A-Faster must not require, infer, or claim a Mac Worker/Serena
  surface unless the current harness actually exposes and verifies it. For
  long-running bounded inference labor, launch the admitted Kilo/Claude CLI
  route through the exact Mac lane bound by the active claim.
- **GitHub:** remains remote Issue/PR/SHA/CI/merge truth, not a substitute for
  either device's local dirty-state/ownership proof.

A missing preferred surface blocks only dependent work. Re-route through the
next already-authorized surface without changing task/claim/scope semantics.

## PROJECT/TASK DELEGATED-RUN CENSUS (every A-Faster entry)

At every A-Faster entry, BEFORE selecting new READY work, run a mandatory
delegated-run census over existing authorities only:

- active work-order/Issue checkpoints for the current project, including
  the latest A-Faster lifecycle pulse when one exists;
- known durable lane pointers under `runs/` when local
  (`references/durable-lanes.md` layout);
- exact process/session identity where the device is reachable;
- result/exit/log evidence at the declared destinations;
- actual Git/worktree/branch/HEAD/dirty state.

Never infer `RUNNING` from a stale PID number alone: a PID proves liveness
only when it matches the recorded creation/command/boot identity where
available. The census scope is the current project — its active/open work
orders and Issues plus material recent lane pointers — and it MUST include
old GLM assignments from prior A-Faster invocations, including ones started
by another ChatGPT session, whenever they are discoverable from that durable
evidence. Do not scan arbitrary ancient unrelated projects.

Derive each outstanding attempt as `RUNNING` / `TERMINAL_UNHARVESTED` /
`STALLED` / `INTERRUPTED` / `UNKNOWN` / `TERMINAL` using the existing
`docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md` classes, and apply the
`references/durable-lanes.md` dispositions: `RUNNING` never redispatches;
`TERMINAL_UNHARVESTED` harvests and verifies first; other ambiguous states
reconcile side effects and replay safety before takeover. A fresh
chat/session never means a fresh task. Also compare `last_activity_at`,
`last_progress_at`, optional `last_heartbeat_at`, and the lane's declared
task/adapter-specific stall policy. Crossing a declared freshness bound makes
the lane a stall candidate requiring reconciliation; elapsed time alone never
proves the owner is gone and never grants replay/takeover authority. This
census is read-only recovery routing; it creates no new execution store or
lifecycle state machine.

## LANE OCCUPANCY MATRIX (per-invocation projection)

After the census, derive a deterministic LANE OCCUPANCY MATRIX for this
invocation. The matrix is a **projection reconstructed from authority and
evidence on every invocation** — not a scheduler, registry, database, or
state store, and nothing in it is task authority. Reuse the stable
`LANE_REF` / `DELEGATED_RUN_ID` / `ATTEMPT` / pointer identity from
`references/durable-lanes.md`; never invent a second identity scheme.

Each occupied or candidate lane row carries at minimum:

- `WIP_SLOT` — ephemeral slot label only (`M1`/`M2`/`M3` for mutable,
  `R1` for the independent read-only review lane); labels are per-invocation
  projections, not durable identities;
- `LANE_REF` + task/claim reference;
- repo / worktree / branch / HEAD;
- mutable scope;
- owner / execution surface;
- harness/model (`MODEL_ID` + effort/variant);
- latest run id / attempt / pointer location;
- derived liveness state from the census;
- latest lifecycle pulse label + `observed_at`;
- `last_activity_at`, `last_progress_at`, optional `last_heartbeat_at`;
- declared stall/freshness policy and derived `stall_candidate_after_at` when
  deterministically available;
- exact next safe action.

Checkpoint the matrix to the active work order/Issue when material (lane
state changes, terminal-unharvested destinations, rollover, takeover), then
reconstruct it fresh from evidence next invocation — never treat a stale
checkpoint as live occupancy truth.

## Cross-device lifecycle pulse projection

A-Faster MUST publish and recover a compact durable lifecycle pulse for every
material mutable/delegated lane so another device/session can understand the
lane without chat memory. This is a **projection/checkpoint over existing
authorities**, never a scheduler, lease, registry, heartbeat service, or second
execution state machine.

Use these pulse labels only as communication events. The pulse `event` and
existing `liveness_class` are separate fields with separate meanings; even when
literal names overlap, never derive, overwrite, or promote authoritative
liveness/task state from the event label alone:

- `STARTED` — an authorized lane/continuation began;
- `PROGRESS` — a material task milestone advanced;
- `WAITING` — the known owner is intentionally waiting on a typed dependency;
- `STOPPED` — the current executor/session intentionally ceased work without
  claiming completion; replay safety and the exact next action are mandatory;
- `TERMINAL_UNHARVESTED` — the attempt ended but result/evidence still needs
  harvest/reconciliation;
- `COMPLETED` — the claimed scope is accepted/reconciled terminal; an
  agent/model merely saying DONE is insufficient;
- `TAKEOVER_STARTED` — a receiving device/session passed the existing
  ownership/replay-safety/collision gates and became the current mutable owner.

Every pulse carries at least: `LANE_REF`, latest `DELEGATED_RUN_ID` when one
exists, task/claim, device, repo/worktree/branch/HEAD/scope, existing
`liveness_class`, `observed_at`, `started_at`, `last_activity_at`,
`last_progress_at`, optional `last_heartbeat_at`, typed reason/blocker,
task/adapter-specific `stall_policy`, derived `stall_candidate_after_at` when
deterministically computable, replay-safety, evidence/result reference, and
exact next safe action. Timestamps are ISO-8601 with offset or `UNKNOWN`; never
invent missing times.

Publish/fold the pulse to the active Work Order/Issue at least on `STARTED`,
material `PROGRESS`, `WAITING`/`STOPPED`, `TERMINAL_UNHARVESTED`,
`COMPLETED`, and `TAKEOVER_STARTED`, plus before session/device handoff when
state changed materially. Device-local `runs/` pointers retain detailed local
evidence; the Issue/WO pulse is the durable cross-device carrier. If that
carrier is unavailable, record `PULSE_CARRIER_UNAVAILABLE` in local evidence,
do not claim the pulse was published, and block handoff/takeover/cleanup steps
that depend on cross-device publication until the pulse is durably folded.
Local work may continue only when its existing task/claim/ownership/replay gates
remain independently satisfied.

Activity, progress and heartbeat remain distinct per
`docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`. Repeated polling or
identical logs do not advance progress. There is **no global timeout**:
each task/executor declares its appropriate bounded activity/heartbeat policy.
When the current time crosses a deterministically derived
`stall_candidate_after_at`, classify `RECONCILE_REQUIRED` / possible
`STALLED`; do not automatically cancel, replay, reassign, or take over.

Before a takeover, reconcile the exact prior process/session, logs/results,
Git/worktree/branch/HEAD/dirty state, claim/ownership and replay-safety. An
explicit handoff or evidence that the prior mutable owner is no longer active
is required. The receiving device then publishes `TAKEOVER_STARTED` with the
old/new device identity and binding-digest delta. If the old device later
resumes, it MUST rerun census/collision first and yield to the valid current
owner instead of resuming mutation from stale chat state.

## Collision gate before material dispatch/mutation

Before every material dispatch or mutation, compare the candidate's mutable
scope against every recovered active mutable scope in the global project WIP
(the occupancy matrix above). `SAFE_TO_MUTATE=NO` for that lane when any of:

- same repo path overlap with an active mutable scope;
- same mutable hotspot;
- branch/worktree ownership conflict;
- unknown ownership for an overlapping scope.

Different sessions, chats, or devices never get separate WIP budgets and
never bypass this gate. A lane blocked here keeps its typed blocker and
exact next safe action; independent non-overlapping lanes proceed.

### Collision pulse — event-driven refresh boundaries

Within every active A-Faster invocation, refresh/reconstruct the delegated-run
census + lane occupancy projection and rerun the collision gate at least:

- before allocating new work on A-Faster entry;
- before every material delegated dispatch;
- before every material mutation;
- after a material lane transition, lifecycle-pulse publication, harvest,
  takeover, or scope change;
- before Windows <-> macOS handoff;
- before candidate freeze;
- before fan-in / merge;
- after material remote-main/claim/ownership drift is observed.

This is lifecycle/event-driven reconciliation, not background polling. Plain
ChatGPT does not self-wake after a turn ends; a later turn/session reconstructs
truth from durable Issue/WO/run-pointer/Git/runtime evidence before continuing.

## PRE-DISPATCH DEDUPE GATE (before every material GLM launch)

Motivated by the WO493 duplicate-dispatch incident: a wrapper timeout or a
missing UI card is never evidence that a delegated run stopped. Before every
material GLM launch, reconcile ALL of:

1. durable task/claim identity for the candidate (work order / Issue /
   claim reference);
2. repo / worktree / branch / HEAD / dirty state;
3. mutable scope / hotspot overlap against every active lane;
4. durable execution pointer plus result/exit/log evidence at the declared
   destinations;
5. exact process identity where the device is reachable — recorded PID plus
   creation/command identity, never a bare PID number.

Then apply the census dispositions to any matching attempt:

- `RUNNING` => do not dispatch; attach or wait on the existing owner;
- `TERMINAL_UNHARVESTED` => harvest and verify before any conflicting work;
- `STALLED` / `INTERRUPTED` / `UNKNOWN` => reconcile side effects and replay
  safety before any takeover or retry.

A wrapper/tool timeout, a missing tool/UI card, chat/session loss, or an
executor's Active Project drift never grants redispatch authority; each is
`UNKNOWN/RECOVER` until the reconciliation above proves otherwise. This gate
reuses the census, the collision gate, and the durable-lane identity — it
creates no new scheduler, registry, or retry authority — and
`1 MUTABLE HOTSPOT = 1 MUTATION OWNER` still applies.

## JEV semantic fast path

For bounded semantic triage, A-Faster may consult an **accepted/admitted**
provider-neutral semantic decision seam after deterministic facts and normal
lane authority are known. Until that seam/route exists, effective mode is
`OFF`; do not improvise direct provider calls from this skill. Read
`references/jev-semantic-fast-path.md` when a READY task needs task
classification, skill suggestion, failure classification, evidence relevance,
or escalation triage.

Initial modes are `OFF`, `SHADOW`, and `ADVISORY` only. Semantic output is
evidence, never task/claim/mutation/review/merge/completion authority; it never
creates a separate WIP slot. `review_severity`, security/authority/ownership
judgment, and any consequential acceptance remain frontier/deterministic work.
Provider failure, malformed evidence, low confidence, or policy uncertainty
fails closed to the existing GPT/GLM path rather than blind retry.

## Model routing by benchmark

Prefer GLM labor where capable, especially for bounded work that can run
longer than one chat/tool interaction, selected by task benchmark rather than
fear of quota. GPT-5.6 Sol remains fleet integrator — decomposition, collision
prevention, deterministic verification, fan-in, acceptance — and is the
direct-execution fallback when eligible external GLM routes are unavailable:

- **GLM-5.3 MAX** (effort `max`) is the default for R2/R3 implementation,
  durable state/concurrency/idempotency/security/protocol work, complex
  repair, and any required independent R3 review.
- **GLM-5.3-Flash** is the default for bounded read-only reconnaissance,
  pointer/run census assistance, dependency/scope scans, task-packet
  shaping, compatibility precheck, and advisory pre-review — where a MAX
  independent review is still required by policy, Flash only prepares, it
  never satisfies that requirement.
- Flash must not silently satisfy an R3 MAX/qualified independent-review
  requirement, and no model identity grants task, claim, mutation, or
  acceptance authority.
- Route by proven quality/latency/task class and deterministic evidence.
  Benchmark data may change routing later without rewriting task semantics:
  the task packet's scope/authority stays model-neutral, and only the
  routing decision records the harness/model evidence.

## Surface routing

### Windows

Prefer SunDay-Worker 1..5 as the primary chat-visible repo/file/code surface
after exact lane activation and mutation gating. Workers are dynamic lanes,
not permanent roles. Use RDC as the secondary Windows surface for exact
device/process/runtime inspection, recovery, shell/build/test operations, or
when the needed Worker surface is unavailable.

Kilo Code CLI and Claude Code CLI may execute delegated packets from isolated
Windows worktrees when their exact route is READY; for eligible long-running
bounded labor they are preferred over keeping Sol occupied with routine
implementation.

### macOS

Use Remote Desktop Commander (RDC) as the primary chat-visible Mac surface for
exact device discovery, shell, filesystem, process, repo/worktree, test, and
CLI operations when RDC is actually exposed and online. Kilo/Claude CLI may
run inside the RDC-bound Mac lane after normal route/quota/task gates.

Local Serena or another semantic tool may exist on the Mac, but A-Faster must
not require or claim a Mac Serena/Worker route unless that surface is actually
exposed and verified in the current harness.

`RDC ONLINE != SAFE_TO_MUTATE`.

If RDC is not exposed, record `PLUGIN_NOT_EXPOSED_TO_CHAT`; do not pretend the
Mac lane ran, and do not reconstruct a missing Mac repo from chat memory.

### GitHub

Use the GitHub connector for remote Issue/PR/SHA/diff/CI/merge truth when the
connector is callable. If connector invocation is unavailable, record the typed
surface failure. A locally authenticated `gh` CLI may be used only as an
explicit fallback under the same repo/task authority and must not be described
as the connector.

## GLM multilane delegation

Kilo and Claude Code are **harnesses only**. They never grant mutation,
provider, review, or acceptance authority.

Before **every material GLM dispatch**:

1. pass the PRE-DISPATCH DEDUPE GATE above (recover outstanding delegated
   executions first);
2. verify exact repo/worktree/branch/HEAD/task/claim/scope;
3. refresh CoinTH quota/readiness through the approved secret-safe resolver;
4. prove the exact harness/model route;
5. create a durable execution pointer/result destination before or at launch.

Preferred routes:

- Kilo Code CLI: exact `cointh-glm/glm-5.3`, effort/variant `max`;
- Claude Code CLI: exact `glm-5.3` with `--effort max`, only after a live
  route probe proves that exact model is accepted;
- GLM-5.3-Flash on a proven route for the bounded read-only assist classes
  in "Model routing by benchmark" (reconnaissance, census assistance,
  dependency/scope scans, task-packet shaping, compatibility precheck,
  advisory pre-review). Flash assist lanes never hold mutation authority
  and never satisfy a required independent R3 MAX/qualified review.

Never silently fall back to another model/provider/harness. A failed Claude GLM
probe blocks only that route; Kilo or another already-authorized route may
continue independent work.

When all eligible GLM routes for a task are blocked, classify the actual cause
(`QUOTA_EXHAUSTED`, `QUOTA_UNKNOWN`, auth/entitlement, transport, route,
harness, cost, etc.) without collapsing unlike failures. After reconciling any
prior GLM attempt and transferring/confirming mutable ownership, GPT-5.6 Sol
directly continues the eligible safe task instead of leaving it idle. This is
an executor fallback only: it never relaxes task/claim/scope/WIP/verification
gates, never silently changes provider/model, and an authoring Sol lane cannot
satisfy an independent-review requirement that still applies. If the task
specifically requires an unavailable independent model/reviewer, that review
gate remains blocked while other safe work may continue.

Run Kilo and Claude concurrently only on non-overlapping claimed scopes or as
read-only analysis/review lanes. Freeze exact candidate SHA(s) before review.

## SHORT_BURST execution policy

Every A-Faster burst follows the frozen SHORT_BURST loop and bounded budgets
defined in `references/short-burst.md` (WO-P1-483):

```
RECOVER EXACT EVIDENCE -> ONE BOUNDED ACTION/DISPATCH -> USER CHECKPOINT -> NEXT BURST
```

One burst = one bounded action (or one bounded dispatch), then a durable
user-visible checkpoint, then the next burst; no burst contains a second
material action after an UNKNOWN/RECOVER outcome. Prefer exact-path/pointer
reads before any broad scan; broad recursive scans are forbidden in the
critical path except the one bounded staged escalation defined there. Any
command or dispatch estimated to run longer than 120 s goes background-first:
write the durable pointer before or at launch recording PID + verified
command identity plus `log_ref`/`exit_ref` destinations. A wrapper or tool
timeout is `UNKNOWN/RECOVER` — never automatic FAILURE and never redispatch
permission — until reconciled per the dispositions above. Checkpoint cadence
is independent of tool-card UI rendering.

## Mandatory enforcement-hook checkpoints

A-Faster MUST treat the accepted Hook Contract v1 as the enforcement backstop
for every **material** boundary once an executable GUARD route exists. The
canonical checkpoint sequence is:

`ENTRY -> RECOVERY -> PRE_DISPATCH -> PRE_MUTATION -> PRE_FREEZE -> PRE_REVIEW -> PRE_MERGE -> POST_MAIN`

Each checkpoint is a policy gate even before runtime GUARD wiring exists. An
agent MUST NOT skip a checkpoint merely because chat context, a tool card, or
its own prompt memory omitted it.

Hook enforcement state is explicit:

- `POLICY_ONLY` — the A-Faster skill/checklist and deterministic tests require
  the checkpoint, but no accepted executable GUARD invocation is proven on the
  current route. The agent must follow the gate, but MUST NOT claim that runtime
  enforcement prevented bypass.
- `GUARD_ENFORCED` — an accepted Hook Contract `GUARD` invocation is proven
  on the exact material-action path. Security/authority guard failures are
  fail-closed; `DENY`, unavailable guard evidence, malformed guard evidence,
  or ambiguous scope blocks the dependent action.
- `OBSERVE_ONLY` — Hook telemetry exists but is non-blocking. OBSERVE events
  never satisfy a required GUARD checkpoint.

For every material action, the integrator records the checkpoint verdict and
evidence reference in the existing WO/run-pointer lifecycle evidence; no new
hook state store is created. The Hook Bus/STM/Monitor remain projections, never
task/claim/retry/review/acceptance authority.

Until all material mutation/dispatch/merge routes are behind an accepted
guarded execution/Command Gateway path, raw shell/Git/tool capability remains a
possible bypass at the harness level. Therefore A-Faster MUST fail honestly:
do not report `GUARD_ENFORCED` unless the exact action passed the executable
GUARD. The roadmap target is to route material actions through guarded entry
points so prompt forgetfulness cannot bypass these gates.

See `references/short-burst.md` for the per-checkpoint evidence minimum and
fail-closed disposition.

## Durable lane identity overlay

Every delegated A-Faster lane carries the durable identity overlay defined in
`references/durable-lanes.md` (projection only; never authority):

- `LANE_REF` `lane:<TASK_ID>:<role>:<ordinal>` — stable routing label across
  device/harness/session changes for the life of the lane;
- `DELEGATED_RUN_ID` `run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`
  — unique per-dispatch attempt identity for observation/recovery/harvest;
  recovery of proven pre-grammar legacy pointer aliases (WO-P1-480 P1 + P2
  repair seams) is pointer-evidence-only, preserves the original string
  verbatim, accepts only the bounded legacy classes (7..12-hex recovery
  tails; opaque bounded numeric legacy tags never reinterpreted as
  ordinals), and never grants minting/path authority;
- `ATTEMPT` — monotonic only inside the lane evidence directory; never retry
  authority;
- `BINDING_DIGEST` — SHA-256 over canonical UTF-8 JSON (sorted keys, compact
  separators) of the safe binding tuple; drift detection only, not
  encryption/authentication.

The durable execution pointer required before or at launch is written under
`runs/<WO>/<lane>/attempt-NNNN-<random-id>/pointer.md` (WO-P1-480 / MSP-0
collision-proof naming: the suffix is the DELEGATED_RUN_ID's exact accepted 8- or 12-hex random
id for new minting — the 7..12-hex family is bounded legacy recovery
compatibility only; legacy `attempt-NNNN/` directories remain readable/recoverable and are
never rewritten) with the minimum fields, secret-redaction rules, recover
algorithm, and cross-device re-pin semantics defined in
`references/durable-lanes.md`. The pure parse/derive/enumerate/recover
helper is `src/a_conductor/delegated_run_artifacts.py`. Different
recomputed digest on
takeover is `CONTEXT_DRIFT` requiring explicit re-pin and reconciliation,
never automatic transfer. `NEW SESSION != NEW TASK`: reconcile
pointer/process/result/Git and harvest `TERMINAL_UNHARVESTED` work before
redispatch. No global lane registry is created or implied.

## Advisory skill layer

Advisory skills may shape work but never become authority.

### Ponytail

On each Claude Code device, verify the user-level `ponytail@ponytail` plugin
before relying on it. When missing and current user/tool authorization permits
installation, use the upstream-supported Claude Code sequence as two separate
commands/prompts:

```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

For headless automation, use an equivalent CLI form only when that installed
Claude Code version's help explicitly proves it is supported. Re-verify the
installed marketplace/plugin after mutation; one device's install is never
evidence for another device.

When a Claude lane is actually used and the plugin is verified available,
automatically consider Ponytail as an advisory simplification layer at each
applicable boundary:

- `ponytail` before implementation to challenge unnecessary work;
- `ponytail-review` at a frozen-candidate/review boundary;
- `ponytail-audit` / `ponytail-debt` at applicable review/debt boundaries.

This consideration is advisory only. Do not let YAGNI advice override an
accepted Work Order, safety gate, or verification requirement.

### Caveman

Verify the user-level GitHub-sourced `caveman` skill on every device. When
missing and installation is authorized, install the **skill only** from
`JuliusBrussee/caveman` using its supported skills installer, for example:

```text
npx skills add JuliusBrussee/caveman -g
```

Do not install or enable the optional Caveman proxy/engine merely to satisfy
this skill requirement. Re-verify the resulting skill path/content after
installation. Automatically consider Caveman only for transient
agent-to-agent communication/token compression where exact semantics are
not needed and meaning remains unambiguous.

Do **not** use Caveman compression for:

- persisted project docs, issues, PR bodies, commits, handoffs, or evidence;
- security warnings or irreversible-action confirmations;
- exact error text, commands, identifiers, numbers, units, or contract terms.

### Grill Me

Preserve any existing local Grill Me skill; A-Faster runtime convergence must
never overwrite a customized `grill-me` installation. When a real
product/architecture/intent decision remains ambiguous **after codebase,
authority and tool inspection**, invoke the installed Grill Me flow before
inventing the decision (for installations supporting the current project
commands, `/grill-me plan`; `/grill-me check` may challenge an implemented
plan).

If Grill Me requires interactive user input that is unavailable, classify the
decision normally (`HUMAN_DECISION_REQUIRED`) rather than guessing. Do not use
Grill Me to ask the user for facts that tools/authority can recover.

## Cross-device handoff

A device handoff is a normal lane handoff, not a new task.

Before another device takes over:

1. checkpoint task/claim/scope/current SHA and delegated-run state, and
   publish a timestamped `WAITING` or `STOPPED` lifecycle pulse as truthful;
2. preserve material evidence outside any worktree scheduled for cleanup;
3. push/fold through the accepted remote authority where that repo has one;
4. on the receiving device, re-pin actual repo/worktree/branch/HEAD and prove
   no mutable overlap before continuing;
5. recompute `BINDING_DIGEST` from observed binding facts per
   `references/durable-lanes.md`; a different digest is `CONTEXT_DRIFT`
   (typically the device-bound fields), resolved only by explicit re-pin,
   recorded delta, and prior-attempt reconciliation — never automatic
   transfer;
6. only after takeover gates pass, publish `TAKEOVER_STARTED` with the prior
   and receiving device identities plus the binding-digest delta. A stale
   timestamp by itself is never takeover authority.

No accepted remote/source on the receiving device means
`SOURCE_UNAVAILABLE / SAFE_TO_MUTATE=NO`.

## Session rollover checkpoint

Before a chat/session/context rotation (not only a device handoff), fold the
durable state into the active work-order/Issue checkpoint: the current lane
occupancy matrix, outstanding LANE_REF/DELEGATED_RUN_ID pointers, and every
terminal-unharvested result destination with its harvest instruction. Publish
a truthful timestamped `WAITING`/`STOPPED` pulse when the current executor is
intentionally ceasing work. The new session then starts with census + harvest
per this skill — never with redispatch of work a prior session may still be
running or may have finished unharvested.

## Lane recycle and cleanup

A-Faster reuses A-FastTask `references/closeout.md`. Cleanup is never implied
by model/Worker DONE or by a merged-looking branch.

At every accepted/merged/explicitly-abandoned lane closeout, **automatically run
a cleanup-eligibility audit** for that lane and any temporary worktree/folder it
owns. This audit is mandatory; deletion is not. Record
`CLEANUP_STATE=COMPLETE|PENDING|BLOCKED` with the exact path and evidence.
Eligible registered Git worktrees should be removed promptly with canonical
non-force `git worktree remove <exact-path>` so finished lanes do not consume
machine storage. A non-worktree project folder may be deleted only when the
same ownership/disposition/unique-content/process proof establishes that it is
an exact disposable lane artifact rather than user data.

A worktree/folder becomes cleanup-eligible only after all are proven:

- accepted/merged or explicitly abandoned by authority;
- material result/review evidence folded outside the target;
- no active claim/lease/process/editor/test/executor bound to it;
- tracked + untracked + ignored inventory accounted for;
- no unique work would be lost; accepted content is reachable/evidenced;
- exact registered path identity is known.

Use canonical non-force worktree removal. Never reset/clean/stash/force merely
to make cleanup succeed. Branch deletion remains a separate decision.


## Hierarchical child-goal routing (WO-P1-530)

A-Faster may bind a bounded delegated task as a CHILD_GOAL, but this is an
execution-packet shape only. The A-NightShift/Codex parent remains the one run
lifecycle owner and the existing A-FastTask/claim authorities remain unchanged.
A child goal never becomes a scheduler, roadmap owner, task database,
claim/lease system, review authority, merge authority, or completion authority.

The normal goal tree is bounded:
PARENT_GOAL -> KILO_GLM_CHILD -> OPTIONAL_JEV_ADVISORY.
Deeper recursive spawning is forbidden. Global active compute remains max 3
mutable plus 1 independent read-only review; Issue #537 may additionally retain
up to 2 borrowed mutable claims without increasing active mutation above 3, and
one mutable hotspot has exactly one owner.

Every CHILD_GOAL binds the existing lane tuple: task/work order, claim/owner,
repo, worktree, branch, exact HEAD, allowed/forbidden scope, expected result,
evidence destination, verification, replay safety and stop conditions. The
child returns evidence to the parent; the parent must HARVEST terminal durable
children before REFILL or equivalent redispatch.

Kilo child transport is capability-gated:
- KILO_GOAL_CAPABILITY=VERIFIED for the exact Kilo harness/version permits a
  bounded slash-goal pointer such as "/goal Read <task_packet_ref> and execute
  only that child goal".
- KILO_GOAL_CAPABILITY=UNVERIFIED_HEADLESS or UNAVAILABLE forbids inventing
  slash-goal semantics. Use POINTER_FALLBACK: one bounded instruction such as
  "Read <task_packet_ref> and execute only that child task". The task packet,
  not slash syntax, carries authority and scope.
- A stalled/ambiguous capability probe is UNVERIFIED_HEADLESS, never proof of
  support and never a reason to block other safe work.

All material Kilo/GLM children are transported through the exact
`sunday_dispatch` durable execution tool. For this contract the tool name is
exact: a generic "durable dispatch" category, an alternate durable transport,
another dispatch tool, or a direct Kilo invocation is not valid child
transport. Every child dispatch through `sunday_dispatch` uses explicit
--dir, process-local KILO_CONFIG_CONTENT={"share":"disabled"}, CLI
--no-share, and a fresh CoinTH quota preflight immediately before dispatch.
Any non-`sunday_dispatch` transport, a direct non-durable Kilo call, or any
attempt that emits a share URL is INVALID_CHILD_EVIDENCE and cannot satisfy
review/acceptance.

Fresh CoinTH proxy quota alone is never upstream readiness. Material GLM
child admission requires both structured per-dispatch facts —
PROXY_QUOTA_STATE=AVAILABLE AND UPSTREAM_PROVIDER_READINESS=READY — plus the
existing route/claim/scope gates; neither fact alone admits a dispatch. These
are observed evidence values refreshed per dispatch, never cached or
hard-coded constants from a transient earlier probe. When
UPSTREAM_PROVIDER_READINESS=THROTTLED, wait until the declared reset/cooldown
elapses; do not repeated-probe while waiting. When
UPSTREAM_PROVIDER_READINESS=UNKNOWN or any non-READY value, fail closed for
GLM child dispatch; independent GPT/Codex work may continue on its own gates.

GLM-5.3 MAX handles bounded heavy author/repair/review work. GLM-5.3 Flash is
read-only census/recon/shaping only and never satisfies a required R3 MAX or
qualified independent review. TypeSafe-Jev is optional nested advisory only
with authoritative_for_action=false.

After every child terminal transition:
RECOVER -> RECONCILE -> HARVEST -> recompute accepted READY frontier -> REFILL.
If quota is available and independent SAFE READY work exists, continuation does
not wait for a ChatGPT user turn. If no READY work exists, report the truthful
typed blocker/wait state. Never manufacture work merely to consume quota.

Pinned transport vector:
KILO_HEADLESS_PROBE=STALLED_NO_OUTPUT =>
KILO_GOAL_CAPABILITY=UNVERIFIED_HEADLESS, CHILD_ENTRY=POINTER_FALLBACK.

## Wait-aware auto-backfill (A-NightShift + A-Faster)

`WAIT_AWARE_AUTO_BACKFILL` is part of every `A_FASTER_ACTIVE` run. The
A-NightShift parent remains lifecycle owner; A-Faster is the router/binder that
recomputes occupancy and fills independent `SAFE_READY` capacity whenever an
owned lane enters a typed wait.

Recognized wait reasons include:
- `WAITING_APPROVAL` — human/acceptance gate is pending;
- `WAITING_CI` — exact-head CI/check result is pending;
- `WAITING_GLM` — parent orchestration is waiting on a delegated GLM child;
- `WAITING_JEV` — parent orchestration is waiting on TypeSafe-Jev advisory work;
- `WAITING_EXTERNAL` — another typed external dependency is pending;
- `COOLDOWN` — a declared provider/rate-limit/reset window is active.

A wait label alone never frees a mutable slot. Occupancy is reconstructed from
actual active-mutation evidence. In particular, if `WAITING_GLM` has an active
delegated mutation child that still owns the hotspot/claim, that child remains an
active mutable lane and its slot stays occupied. Parent-orchestrator idleness is
not extra mutation capacity. The invariant remains
`1 MUTABLE HOTSPOT = 1 MUTATION OWNER` and simultaneous active mutation stays
`<= 3`.

When a typed wait releases real active headroom and independent READY work exists,
A-Faster may admit borrowed continuity work under Issue #537: at most 2 borrowed
mutable claims, still never more than 3 simultaneous active mutations, plus the
separate independent review lane. Existing claim/lease/scope/collision/provider
gates remain mandatory and no work is manufactured only to fill a slot.

The steady-state loop is:
`RECOVER -> RECONCILE -> HARVEST -> classify active/waiting/parked evidence ->
REFILL SAFE_READY -> CHECKPOINT`. A-NightShift continues supervising the parent
goal while delegated children and advisory work run; one slow child does not
serialize unrelated safe work.

When a dependency resolves, reconcile and HARVEST its exact evidence first. If a
returning base lane would exceed the active mutation ceiling, enough borrowed work
finishes only its current bounded micro-step, checkpoints through existing
authority, and becomes `PARKED_CAPACITY` before the base lane resumes. Contraction
must never kill an owned task, reset Git, stash unknown work, or create a duplicate
claim/redispatch just to reduce occupancy.

The user does not need to repeat the long "continue / open another lane while this
waits" instruction after each transition. Once `A_FASTER_ACTIVE` is established,
this wait-aware loop continues automatically until a real goal/stop gate, terminal
completion, or explicit deactivation. A chat/session timeout is not deactivation
and NEW SESSION remains continuation/recovery, not permission to forget running
work.

## Autonomous continuation

After routing, dispatch, harvest, or fan-in, continue with the next safe
READY step automatically — within already-bound authority, without waiting
for the user to repeat "continue" for each step. A GLM quota/route/harness
failure routes eligible work to the Sol direct fallback above after recovery
and ownership reconciliation; it is not by itself a reason to idle the whole
project. Stop only when the affected task still has a real unresolved gate
(collision, required-independent-review unavailability, verification failure,
authority/safety ambiguity, no safe fallback) or at terminal completion; when
stopping, publish the truthful `WAITING`/`STOPPED`/`COMPLETED` lifecycle pulse
with timestamps, replay-safety, exact blocker and next safe action.

## Routing output additions

In addition to normal A-FastTask output, report:

- `DEVICE_ROUTE` for every active/blocked device;
- `WIP_SLOT` and mutable/review role;
- census disposition: `NONE`, or per-lane derived states with
  harvest/recovery disposition for every outstanding attempt found;
- lane occupancy matrix summary (projection, with its checkpoint location
  when one was written);
- `HARNESS_ROUTE` + exact model/effort/readiness;
- `EXECUTOR_FALLBACK` when a preferred GLM/device route is blocked, including
  the typed blocker and the verified next executor;
- latest collision-pulse boundary/result when material;
- latest lifecycle pulse label, `observed_at`, activity/progress/heartbeat
  timestamps, stall policy, and stall-candidate time when available;
- `LANE_REF` + latest `DELEGATED_RUN_ID`/pointer state for every delegated
  lane (or the reconciled disposition per `references/durable-lanes.md`);
- `ADVISORY_SKILLS` actually available/invoked;
- `CLEANUP_STATE` for completed lanes;
- exact next safe action.

A-Faster ends where A-FastTask ends: after routing/binding. The authorized
executor/integrator continues safe work immediately under the selected existing
workflow.
