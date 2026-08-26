# GE-0006 — Event-driven bounded scheduler with deterministic worker pairing

Status: ACCEPTED — GPT-5.6 Sol MAX integrator decision, 2026-08-26
Date: 2026-08-26
Parent: `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md`
Design evidence: `docs/work-orders/WO-GE-006-scheduler-dispatch-design.md`

## Context

GE-1..GE-5 establish the graph domain, persistence, DAG semantics, hidden-conflict analysis, and global ReadySet. GE-6 must now choose which globally-ready nodes may run on the real worker fleet without turning graph scheduling into a second execution lifecycle.

The current fleet target is five reusable SunDay worker slots. Worker/runtime state changes asynchronously; provider/gate conditions may also change independently of graph dependencies. Existing Conductor architecture already separates transport state, durable execution state, and worker lifecycle.

A-Wiki's current authoritative boundary assigns brain policy/gates/claims to A-Wiki and process/worker dispatch to A-Wiki-Conductor. No A-Wiki scheduler is therefore available or appropriate to wrap. The A-Wiki `dag_eval` parallel-level semantics are already ported in GE-3.

## Decision

### 1. Scheduler core is event-driven, pure, and re-entrant

GE-6 uses a deterministic `schedule_once(...) -> SchedulePlan` style core. It does not own a background polling loop, thread, process, or timer.

The orchestration/integration layer invokes a scheduling pass after relevant state changes:

- graph/node readiness transition;
- worker state, assignment, capability, or mutation-authority change;
- gate/provider/rate-limit eligibility change;
- dispatch completion/failure/reservation release;
- startup/reconnect/explicit reconcile/rescan;
- a targeted wake-up at a known future eligibility boundary such as rate-limit expiry.

A low-frequency reconciliation tick may later be added outside the pure scheduler as missed-event insurance. It must call the same deterministic scheduling pass and must not carry separate scheduler semantics.

### 2. ReadySet remains worker-neutral

GE-5 answers graph-level readiness. It must not select a worker or launch work.

GE-6 receives:

- the graph / ReadySet result;
- current node execution/planning observations;
- current conflict report / running reservations;
- a scheduler-facing worker snapshot;
- gate/provider eligibility snapshots;
- an injected scheduling policy.

The worker snapshot is an application port, not a desktop-UI dependency. It exposes only scheduling facts needed by GE-6, such as worker ID, state, project/workspace identity, capabilities, runtime/provider binding, mutation authority, and whether the slot is already reserved/inflight.

### 3. Capacity is bounded to five slots for the current fleet

The current policy default is `max_parallel = 5`, injected rather than scattered as a magic constant.

Effective dispatch capacity is bounded by all of:

- configured `max_parallel`;
- number of eligible READY worker slots;
- existing inflight/reserved slots;
- resource/conflict constraints;
- gate/provider eligibility.

One graph node consumes one worker slot in the GE-6 MVP.

Workers in STOPPED, STARTING, BUSY/inflight, STOPPING, or ERROR state are not eligible for a new reservation. The scheduler does not start, stop, restart, assign, or rebind workers as a side effect of selection.

### 4. Capability and identity matching are fail-closed

For a candidate node/worker pair:

- every `TaskNode.worker_requirement` capability must be present in the scheduler-facing worker/runtime capability set;
- an explicit worker binding, when present, is authoritative;
- mutating work (`write_set` non-empty or equivalent mutation contract) requires matching project/workspace identity and positive mutation authority;
- ambiguous or missing identity blocks the pair rather than guessing or silently rebinding;
- provider/runtime-specific constraints are evaluated from injected metadata/policy, not encoded as hardwired vendor logic in `scheduler.py`.

### 5. Selection is deterministic

Among otherwise eligible nodes, GE-6 orders candidates by:

1. greater `TaskNode.priority` first;
2. earlier DAG/topological rank;
3. lexical node ID as the stable final tie-break.

Among equivalent eligible workers, explicit binding wins; otherwise use stable worker ID ordering unless a later accepted policy adds a stronger cost/capability preference.

No random assignment is permitted. Fairness/aging is not silently invented in GE-6; starvation evidence may justify a later policy extension.

### 6. Conflict closure covers running work and the same scheduling batch

GE-4 is the authoritative hidden-conflict semantic seam. GE-6 must prevent conflicts between a candidate node and:

- already-running/inflight nodes; and
- nodes already tentatively selected in the current scheduling pass.

This same-batch closure is necessary because multiple nodes can be globally READY simultaneously before any is marked DOING.

Dynamic constraints (`FILE_WRITE`, `WORKSPACE_WRITE`, `WORKER`, `RUNTIME`, `PROVIDER`, `RATE_LIMIT`, `RESOURCE`) remain scheduler/readiness reasons. They do not become persisted DAG precedence edges merely to serialize work unless an explicit deterministic analyzer produces a valid ordering under GE-0003.

### 7. Brain and human gates are injected inputs

The pure scheduler consumes typed gate/provider eligibility results. The concrete brain integration may use only the GE-0005 seam: `python -m conductor` or the importable A-Wiki `conductor/` package.

No graph/scheduler module may read A-Wiki `.tmp/*` state or import `scripts.lib.*`.

A NO-GO, human-approval wait, provider wait, or rate-limit wait yields a typed blocked/deferred reason and no reservation.

### 8. Scheduling output is a plan, not a mutation

GE-6 returns an immutable scheduling result containing selected `{node_id, worker_id}` reservations plus blocked/deferred reasons and capacity evidence. It does not:

- mutate TaskNode planning status;
- transition durable jobs;
- launch processes;
- increment attempts;
- write A-Wiki claims;
- perform Git/filesystem operations.

GE-7 owns durable dispatch of the accepted schedule plan.

## Required GE-5 repair before GE-6 production merge

PR #96 merged GE-5 with a resource check that compares write-set strings literally. That is weaker than GE-4's accepted glob-aware conflict semantics and can mark overlapping paths such as `src/**/*.py` and `src/specific.py` simultaneously ready.

This defect does **not** block isolated GE-6 TDD after this ADR is merged because GE-6 already consumes the authoritative GE-4 conflict report and must close conflicts against running + same-batch selections. It **does** block merging GE-6 as production-ready until GE-5 reuses one authoritative GE-4 overlap/conflict seam and adds a regression for glob-vs-specific overlap. GE-6 must not copy the weaker GE-5 path matcher or create a third overlap algorithm.

## Rejected alternatives

### Hot polling loop

Rejected as the primary model. It adds latency/idle work, duplicates state ownership, complicates deterministic testing, and is unnecessary when durable graph/worker/dispatch events already define scheduling boundaries.

### Scheduler launches or rebinds workers itself

Rejected. Worker lifecycle and project assignment are separate control-plane responsibilities with their own safety gates. Selection must not hide lifecycle mutations.

### ReadySet performs worker selection

Rejected. Global graph readiness and worker/resource assignment have different inputs and change rates. Mixing them would make ReadySet impure and couple GE-5 to runtime/provider topology.

### Materialize every conflict as a graph edge

Rejected by GE-0003. Dynamic resource constraints are not automatically true predecessor relations and must not distort DAG/cycle semantics.

## Consequences

- Scheduling decisions are deterministic and unit-testable without live workers or network access.
- Five-slot fleet capacity is explicit but policy-injected.
- Missed events are recoverable through startup/reconnect/reconcile passes without making polling the scheduler authority.
- Same-batch resource conflicts cannot slip through merely because both nodes were READY at the start of a pass.
- Scheduler remains runtime/provider neutral and does not depend on desktop UI structures.
- GE-5's post-merge conflict mismatch is a blocking upstream repair rather than hidden technical debt in scheduler code.
