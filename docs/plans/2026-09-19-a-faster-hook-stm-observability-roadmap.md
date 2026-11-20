# A-Faster Hook / STM / Observability Roadmap

Created: 2026-09-19
Status: PLANNING AUTHORITY CANDIDATE — WO-P1-257 / Issue #365
Task topology: `CROSS_REPO`

## 1. Purpose

Build the next observability and execution-coordination layer for A-Sunday
Conductor without creating a second control plane.

The target is a system where Windows, macOS, Kilo, Claude Code,
SunDay-Worker lanes, SunDayRemoteMCP and future local/remote execution surfaces
emit a common stream of lifecycle/tool/execution events that A-Sunday Conductor
can observe, summarize and present in Desktop, Web and Extension UI.

The roadmap introduces:

- a versioned **Hook Contract**;
- source-specific **Hook Adapters**;
- a bounded **Hook Bus / event stream**;
- **STM (Short-Term Memory)** as rebuildable operational working state;
- a shared **Hook Monitor projection/API**;
- Desktop/Web/Extension UI that consume the same monitor model;
- a later authority-preserving **Command Gateway** for pause/cancel/retry/
  reassign and other consequential controls.

None of those components becomes project/task/claim/review/completion authority.

## 2. Accepted baseline

Authority repo:

`A:\GitHub\A-Wiki-Conductor`

Execution substrate:

`A:\GitHub\SunDayRemoteMCP`

Accepted baseline at roadmap capture:

- A-Wiki-Conductor `origin/main@4f93005d20feb5781b5febb8f963ccd224d29e25`;
- A-Faster PR #363 merged; A-Faster is the accelerated profile over canonical
  A-FastTask, not a second router authority;
- SunDayRemoteMCP `main@70046f0a46f74c1655020ef272cd9c00e41737cd`;
- SEM-0 + SEM-1a semantic foundations are accepted; Issue #341 remains the
  semantic roadmap;
- Issue #340 remains the provider-neutral executor/model portability roadmap;
- A-Conductor already has lifecycle/event infrastructure such as
  `control_events.py`, lifecycle coordinator/journal/recovery and durable
  execution authorities;
- SunDayRemoteMCP has execution/process/tool infrastructure but no accepted
  generic public Hook Contract;
- Claude Code supports native hook/plugin lifecycle surfaces; exact supported
  events must be capability-discovered and version-bound during implementation;
- Kilo CLI has an external plugin system; exact event/hook vocabulary must be
  capability-discovered and version-bound during implementation;
- Ponytail is installed as an advisory Claude Code plugin on the current
  Windows device;
- Caveman and Grill-me are advisory skills, not automatic project authority;
- RDC is used for macOS/device operations only when actually exposed and
  verified.

## 3. Non-negotiable authority boundaries

### A-Sunday Conductor

Owns:

- project/task/work-order semantics;
- claim/lease and mutable-scope authority;
- routing/admission and global WIP;
- retry/replay decisions;
- review/acceptance/merge policy;
- command authorization;
- durable task/evidence continuity.

### A-FastTask / A-Faster

- A-FastTask remains the canonical router/binder.
- A-Faster remains an accelerated profile over A-FastTask.
- A-Faster may add device/harness/model/cleanup routing constraints.
- Neither skill becomes scheduler/task DB/review/completion authority.

### SunDayRemoteMCP

Owns execution/capability implementation only:

- filesystem/search/edit;
- Git inspection;
- terminal/process/batch execution;
- durable dispatch/status/output/cancel/harvest/recover;
- execution hooks;
- semantic/LSP capabilities.

It never owns project task, claim, review, merge or completion authority.

### STM / Hook Bus / Monitor UI

Never become SSoT.

`HOOK/STM STATE != PROJECT AUTHORITY`

Actual Git/GitHub/runtime/durable task state always outranks transient monitor
state.

## 4. Terminology

### Hook Contract

A versioned normalized event schema shared across Conductor, SRM and harness
adapters.

### Hook Adapter

A source-specific mapper that converts native events into Hook Contract events
without changing task semantics.

Examples:

- Claude Code native hooks -> normalized events;
- Kilo plugin events -> normalized events;
- SRM execution/process/tool lifecycle -> normalized events;
- A-Conductor lifecycle/route/dispatch/harvest events -> normalized events;
- RDC/device runtime observations -> normalized device events.

### Hook Bus

A bounded transport for normalized events.

It is not a task queue or scheduler.

### STM

Short-Term Memory = bounded, TTL-governed operational working state derived
from recent normalized events and authoritative references.

STM is disposable and rebuildable.

### Monitor Projection

Read model used by Desktop/Web/Extension UI.

### Command Gateway

Future A-Conductor-owned authority boundary through which consequential UI
actions must pass.

## 5. Hook classes

Every hook/event belongs to one class.

### OBSERVE

Telemetry/visibility only.

Failure behavior: do not block otherwise-safe execution; surface
`OBSERVABILITY_DEGRADED`.

### ADVISORY

Optimization/review/help behavior such as Ponytail, Caveman or Grill-me.

Failure behavior: block only the advisory feature.

### GUARD

Safety/authority enforcement where an existing accepted policy requires a gate.

Every GUARD registration must explicitly declare its failure behavior or be
refused. Security- or authority-classified GUARD hooks MUST fail closed. A
non-security GUARD may fail open only when its accepted Work Order explicitly
defines and tests that behavior.

### COMMAND

A user/operator command request.

It never directly mutates execution state from UI. It goes through the
A-Conductor Command Gateway.

## 6. Hook Contract v1 target

Minimum normalized fields:

- `schema_version`;
- `event_id`;
- `event_type`;
- `hook_class`;
- `phase`;
- `domain`;
- `action`;
- `occurred_at`;
- `source`;
- `source_version`;
- `device_id`;
- `host_os`;
- `lane_id`;
- `task_id/work_order`;
- `task_topology`;
- `authority_repo`;
- `execution_repo`;
- `repo`;
- `worktree`;
- `branch`;
- `head_sha`;
- `claim/lease reference`;
- `execution_id`;
- `harness_id`;
- `model_id`;
- `effort/variant`;
- `state`;
- `duration_ms` when known;
- `blocker_code` when applicable;
- `evidence_refs`;
- `correlation_id`;
- `causation_id`;
- source-local sequence/dedupe identity;
- privacy/redaction classification.

`event_id` is globally unique within the normalized event domain. Consumers
must additionally use the source-local dedupe identity within a bounded replay
window so a retried adapter delivery cannot create a second semantic event.

Raw prompts, credentials, tokens, cookies, session/share URLs and unrestricted
command lines are forbidden by default.

## 7. Delivery semantics

Do not promise exactly-once delivery.

Recommended baseline:

- at-least-once delivery where durable delivery is needed;
- idempotent consumers;
- explicit dedupe key/source sequence;
- correlation + causation identity;
- bounded buffers;
- typed backpressure/degradation;
- source-local order preserved when available;
- cross-source total order never inferred from wall-clock timestamps alone.

Observability loss must not rewrite task truth.

Material task/result evidence continues to use accepted durable evidence/job
authorities, not the Hook Bus.

## 8. A-Conductor control-plane hooks

Planned normalized control-plane events include:

- `route.before` / `route.after`;
- `claim.bound` / `claim.released`;
- `dispatch.before` / `dispatch.after`;
- `execution.reconcile`;
- `harvest.before` / `harvest.after`;
- `verify.before` / `verify.after`;
- `review.requested` / `review.harvested`;
- `accept.before` / `accept.after`;
- `lane.blocked` / `lane.released`;
- `cleanup.eligible` / `cleanup.blocked` / `cleanup.complete`.

Implementation should EXTEND the existing A-Conductor event/lifecycle
infrastructure before adding any new event store.

Do not use Git pre/post-commit hooks as orchestration authority. Native Git
transactions intentionally suppress ambient repository hooks for deterministic,
non-interactive mutation.

## 9. SunDayRemoteMCP execution hooks

Planned substrate events include:

- `workspace.bind.before/after`;
- `execution.before/after`;
- `process.spawned`;
- `process.terminal`;
- `tool.execute.before/after`;
- `batch.before/after`;
- `semantic.request.before/after`;
- `semantic.context_drift`;
- `transport.connected/disconnected`;
- `output.backpressure`;
- `execution.recovery`.

SRM hook callbacks may observe or enforce execution-local safety, but must not
decide project acceptance, task ownership or merge authority.

## 10. Harness adapters

### Claude Code

Implement a version-bound adapter over native Claude hook/plugin events.

Target mappings should include session lifecycle, user prompt submission,
tool pre/post execution, sub-agent lifecycle and stop/terminal events where
supported by the installed version.

Do not assume event names across versions. Capability discovery is required.

### Kilo CLI

Implement a version-bound adapter using the Kilo plugin extension surface.

Target mappings should include session/message lifecycle, tool execution
before/after, permission or failure events, and terminal/result events where
supported.

Do not invent a Claude-compatible shell-hook abstraction if Kilo's native
plugin contract differs.

### Ponytail

Ponytail remains advisory.

Automatic Ponytail hooks may provide simplification/YAGNI guidance, but never
override a Work Order, claim, safety gate or verification requirement.

### Caveman

Conditional token-compression skill only.

Never compress persisted project artifacts, security/destructive warnings,
exact commands/errors/identifiers/numbers/units or evidence where meaning could
change.

### Grill-me

Conditional decision-challenge skill.

Use only after tools/repository authority cannot recover the missing decision.
A real unresolved product/architecture choice becomes
`HUMAN_DECISION_REQUIRED`; Grill-me does not manufacture facts.

## 11. STM architecture

STM is **operational working memory**, not long-term memory and not project SSoT.

Initial implementation should be a **derived in-memory TTL projection inside the
Monitor backend**, not a separate durable subsystem. Promote STM into a distinct
component only if MON-1 evidence proves the derived projection cannot satisfy
working-set, restart, or multi-consumer requirements without duplicating logic.

Example STM content:

- currently active lanes;
- recent hook health;
- recent blockers/errors;
- recent device/harness readiness;
- most recent evidence references;
- short-lived recent execution summaries;
- recent monitor filters/operator context.

Required properties:

- bounded memory;
- TTL/expiry;
- per-project/task/device/lane partitioning;
- no secrets/raw credentials;
- no authoritative claim/completion state;
- rebuildable from authoritative state + recent event stream;
- explicit stale/unknown markers;
- purge/compaction at meaningful task boundaries;
- deterministic precedence: authoritative state overrides STM.

Do not use STM as a second task DB.

## 12. Hook Bus / event pipeline

Target flow:

```text
Native sources
  A-Conductor / SRM / Claude / Kilo / RDC / Workers
            |
            v
       Hook Adapters
            |
            v
     Hook Contract v1
            |
            v
        Hook Bus
       /         \
      v           v
     STM      Sanitized durable
 working set   observability refs
      \           /
       v         v
     Monitor Projection
            |
    +-------+--------+
    |                |
 Desktop UI        Web/Extension UI
```

Prefer a single normalized projection rather than separate state models for each
UI.

## 13. Hook Monitor requirements

The monitor should expose at least:

- source;
- hook/event;
- device;
- host OS;
- lane;
- task/WO;
- task topology;
- repo/worktree/branch/SHA;
- claim reference;
- harness;
- model/effort;
- state;
- duration;
- blocker;
- evidence reference;
- exact timestamp;
- correlation/causation identity.

### Required views

1. **Fleet overview**
   - device/Worker/harness health;
   - active mutable/review lanes;
   - WIP utilization;
   - degraded surfaces.

2. **Live timeline**
   - normalized hook events;
   - filter by task/lane/device/repo/harness/model/state;
   - pause/resume display without pausing execution.

3. **Lane detail**
   - exact binding tuple;
   - current execution;
   - last verified evidence;
   - outstanding delegated-run pointers;
   - hook health.

4. **Hook health**
   - adapter connected/version;
   - event rate;
   - latency;
   - error/drop/backpressure state;
   - last successful event.

5. **STM inspector**
   - sanitized derived working state;
   - TTL/staleness;
   - authoritative reference that supersedes it.

6. **Evidence drill-down**
   - links/pointers only to sanitized durable evidence;
   - never display raw secrets.

7. **Semantic activity**
   - future Issue #341 symbol/reference/diagnostic/context-drift events.

## 14. Web UI / Extension UI

Web UI and Extension UI must consume the same monitor projection/API.

Do not create separate browser/extension task state.

Recommended first transport:

- local authenticated read API;
- one-way server event stream for live monitor;
- no consequential command channel in the read-only milestone.

Whether the stream uses SSE, WebSocket or another local transport is an
implementation decision to benchmark/review before freeze. A read-mostly SSE
baseline is preferred for simplicity; GPT Astra should challenge this choice.

### Extension UI

The extension surface should remain thin:

- connect to local monitor API;
- render the same normalized events;
- deep-link to task/repo/evidence;
- show surface/harness health;
- no direct process/Git mutation.

### Web UI

The first Web UI is not a replacement for the desktop command center.

It should initially provide:

- hook monitor;
- fleet/lane status;
- logs/evidence pointers;
- read-only STM/health projection.

This Web UI later becomes the natural operator surface for headless
Linux/Pi/Umbrel deployments.

## 15. Consequential UI actions — later phase

Only after read-only monitor architecture is proven.

Flow:

```text
UI action
  -> Command Request
  -> A-Conductor Command Gateway
  -> task/claim/safety/replay/ownership gate
  -> authorized execution request
  -> SRM/Worker/harness
  -> result/evidence
  -> normalized hook event
  -> UI projection
```

Potential actions:

- pause;
- cancel;
- retry;
- recover;
- reassign;
- release lane;
- cleanup request;
- merge/release request.

The UI never kills a process, edits Git, changes a claim or merges a PR
directly.

## 16. Global WIP / multi-device invariant

One project-wide budget applies across every:

- device;
- harness;
- repository;
- CROSS_REPO compatibility-set member.

Default:

- max 3 mutable implementation lanes;
- max 1 independent read-only review lane.

Recovery/blocker work uses headroom **inside the same budget** unless an
accepted Work Order explicitly changes capacity.

`1 MUTABLE HOTSPOT = 1 MUTATION OWNER`

Windows and macOS never concurrently mutate the same branch/worktree/hotspot.

### Multi-session ChatGPT integrator hardening (Issue #475 / MSP)

The normal operator workflow may use 2-4 ChatGPT sessions against the same project.
Those sessions share the same project-wide WIP, claim and hotspot authorities; a new
chat is not a new task and never receives mutation authority from browser/session
identity alone.

MSP extends the existing architecture in four bounded slices:

1. `MSP-0` — collision-proof delegated-run artifact identity. The existing random
   `DELEGATED_RUN_ID` remains logical execution identity; physical
   `attempt-NNNN` directories must become uniquely namespaced so concurrent
   sessions cannot overwrite task/config/pointer artifacts.
2. `MSP-1` — privacy-preserving chat-origin provenance projected through existing
   Hook/harness/MCP metadata. Origin metadata is trace-only and excluded from
   task/claim mutation authority.
3. `MSP-2` — atomic/fenced multi-session hotspot admission that reuses the
   accepted A-Wiki claim identity and existing A-Conductor mutation/lease
   mechanics. Do not create a session-lock database or browser-owned claim.
4. `MSP-3` — Monitor/UI projection of
   chat-origin -> command -> claim -> lane -> delegated run -> model/device/PID/SHA.

The losing side of a same-hotspot race must receive a typed attach/conflict outcome
and launch no second writer. Legitimate recovery/takeover by a different chat after
release remains allowed.

### WO-P1-517 — A-Faster utilization enforcement (policy-only)

The global WIP invariant above is machine-checkable through the pure
deterministic classifier `src/a_conductor/a_faster_utilization_guard.py`
(WO-P1-517). It computes `FANOUT_TARGET`, `UNUSED_SAFE_CAPACITY`,
`A_FASTER_UNDERUTILIZED` and `AUTO_REFILL_REQUIRED` plus typed blockers —
including `SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE` when Sol performs
GLM-eligible direct long labor while eligible GLM capacity is idle — from
structured utilization facts gated by an `A_FASTER_ACTIVE` tasking receipt;
explanation-only mentions of A-Faster are never activation. The classifier
is a projection only: no scheduler, task, claim/lease, provider,
dispatch/retry, review, merge, or completion authority; no manufactured
work; no quota burning (quota evidence stays the existing
refresh-before-each-material-dispatch structured flow). Enforcement is
`POLICY_ONLY`; shared executable PRE_DISPATCH guard wiring is successor
scope after WO-P1-498 releases. The §13 Fleet-overview "WIP utilization"
view consumes these labels without becoming authority.

## 17. Multi-device / cross-platform direction

### Windows

Primary current implementation/verification host.

### macOS

Use RDC only after exact device/runtime/repo binding.

Mac hook/skill/plugin installation is independently verified; Windows
installation is not Mac evidence.

### Linux / Raspberry Pi

Reuse the same Hook Contract and monitor backend.

### Umbrel / headless

The headless milestone should reuse:

- A-Conductor daemon/control services;
- monitor projection/API;
- Hook Bus;
- STM;
- Web UI.

Do not build a separate Umbrel monitoring/state stack.

## 18. Security / privacy / trust

Required:

- secret values never enter normal hook payloads;
- raw prompts disabled by default;
- raw command lines sanitized or replaced by digest/reference;
- bounded payload size;
- schema validation;
- untrusted adapter payloads fail validation;
- event-source identity/version recorded;
- user-visible evidence distinguishes observed vs derived vs unknown;
- monitor endpoints local/private by default;
- browser-consumed localhost endpoints must resist CSRF and DNS-rebinding;
  require explicit origin validation plus a local authentication/session token
  before Web/Extension UI connects, even when binding only to loopback;
- remote exposure requires separate auth/threat-model work;
- no extension/browser surface obtains implicit filesystem/process authority;
- every adapter/redaction implementation must pass the same fake-secret corpus
  so prompt/token/session/command leakage tests are uniform across sources.

## 19. Failure model

Required typed failures include at least:

- `HOOK_ADAPTER_UNAVAILABLE`;
- `HOOK_VERSION_UNSUPPORTED`;
- `HOOK_EVENT_INVALID`;
- `HOOK_EVENT_OVERSIZED`;
- `HOOK_BACKPRESSURE`;
- `HOOK_STREAM_DEGRADED`;
- `STM_STALE`;
- `STM_REBUILD_REQUIRED`;
- `MONITOR_PROJECTION_DEGRADED`;
- `COMMAND_GATEWAY_UNAVAILABLE`;
- `DEVICE_ROUTE_UNAVAILABLE`.

Observation failures block only observability unless an accepted GUARD hook says
otherwise.

Transport failure is not execution failure.

## 20. Integration with existing roadmaps

### Issue #341 — semantic/LSP

Independent parallel roadmap.

Semantic requests will eventually emit normalized monitor events, but Hook/STM
architecture must not change semantic edit authority or
`SEMANTIC_CONTEXT_DRIFT` semantics.

### Issue #340 — provider-neutral portability

Hook adapters must bind to harness capability/version, not model identity.

Provider/model/harness remains separate from task semantics.

### DEX / resilient execution

Hook monitor observes durable dispatch/reconcile/harvest lifecycle but does not
replace durable execution pointers or recovery authority.

### Issue #475 — multi-session provenance / collision hardening

MSP is a cross-cutting dependency, not a second scheduler or claim system.

- MSP-0 hardens physical delegated-run artifacts before deliberate multi-session
  writer scaling.
- MSP-1 extends HOOK-3/harness/MCP provenance without changing binding authority.
- MSP-2 hardens the existing mutation admission boundary against concurrent
  ChatGPT integrators and is R3.
- MSP-3 extends MON-1/UI-1 with session/lane traceability.

Goal-runner, Chrome Extension, Web UI and Tampermonkey surfaces consume these
accepted contracts. Browser/tab state never becomes project authority.

### ODP — orchestration decision plane

Hook Monitor is a candidate shared observability substrate for ODP task
timeline / Models & Agents work such as ODP-7. The ODP lane must make that
integration decision against its own accepted contract rather than inheriting
it implicitly from this roadmap.

It does not become planner/adjudicator authority.

## 21. Delivery roadmap and priority

### P0 — accepted baseline + ambiguity closure

**Priority: immediate / blocking architecture work**

- keep A-Faster/A-FastTask authority relationship explicit;
- harden the two carried A-Faster review P2s:
  1. global WIP wording must name devices + harnesses + repos + CROSS_REPO set;
  2. recovery/blocker spare capacity is headroom inside 3+1, not extra lanes;
- freeze this roadmap and independent-review it;
- define ownership boundaries before runtime work.

Exit gate: no shadow authority and no ambiguous WIP semantics.

### MSP critical path — multi-session provenance & collision hardening

**Priority: immediate alongside the accepted baseline; Issue #475.**

Dependency order:

1. `MSP-0` collision-proof delegated-run artifact identity — P0, implement before
   scaling same-project ChatGPT writer sessions.
2. `MSP-1` chat-origin provenance — bind to HOOK-3/harness/MCP adapter work after
   the hook identity/privacy contract is frozen.
3. `MSP-2` atomic hotspot admission — P0/R3, reuse accepted claim + mutation/lease
   authority and prove concurrent same-hotspot winner/loser behavior.
4. `MSP-3` session/lane observability — integrate with MON-1/UI-1 after provenance
   fields are accepted.

MSP-0 and MSP-2 are required before a goal-runner/browser surface intentionally
drives multiple same-project ChatGPT sessions without human supervision.

Exit gate: concurrent-session adversarial tests prove one writer per hotspot,
collision-proof run artifacts, deterministic attach/recovery, no shadow authority
and no privacy leak.

### P1 — HOOK-0 Contract + threat/failure model

- Hook Contract v1 schema;
- hook classes;
- event identity/correlation/causation;
- ordering/dedupe;
- privacy/redaction;
- payload bounds;
- capability/version discovery contract;
- benchmark plan for overhead/backpressure.

Exit gate: deterministic schema/invalid/oversized/redaction tests.

### P2 — HOOK-1 A-Conductor emitter/projection foundation

- extend existing control/lifecycle event seams;
- normalized control-plane events;
- sanitized projection;
- no new task store;
- adapter health state.

Exit gate: source mutation has no change to existing task/claim authority.

### P3 — HOOK-2 SunDayRemoteMCP execution hook seam

- execution/process/tool/workspace hooks;
- no project-authority fields invented by SRM;
- bounded callback/event emission;
- no global mutable project state.

Exit gate: build + deterministic lifecycle tests + exact execution identity.

### P4 — HOOK-3 Harness adapters

Parallel sub-lanes after P1 contract freezes:

- Claude Code hook adapter;
- Kilo plugin adapter;
- MSP-1 chat-origin provenance adapter where the harness/MCP surface exposes a
  session/conversation reference;
- version/capability mismatch behavior.

Ponytail projection and Caveman/Grill-me advisory-monitor integration are
DEFERRED until after MON-1 unless a concrete earlier dependency is proven; they
do not gate the native Claude/Kilo adapter contract.

Exit gate: fake/native fixture conformance and no silent fallback.

### P5 — STM-1 Hook Bus + STM

- bounded bus;
- idempotent consumers;
- backpressure;
- derived in-memory STM partition/TTL/eviction/rebuild first; separate STM
  subsystem only after MON-1 evidence justifies it;
- stale/unknown semantics;
- deterministic authority-over-STM precedence.

Exit gate: fault tests prove bus/STM loss cannot change task truth.

### P6 — MON-1 shared read-only Monitor API

- monitor projection;
- fleet/timeline/lane/hook-health/STM/evidence views;
- MSP-3 chat-origin/command -> claim/lane/run correlation view;
- authenticated local API;
- live stream;
- no command authority.

Exit gate: read-only E2E; monitor restart does not disturb execution; before
any browser/extension client connects, localhost API tests must prove origin +
token enforcement against webpage-originated CSRF and DNS-rebinding attempts.

### P7 — UI-1 Web UI + Extension UI Hook Monitor

Parallel UI lanes against frozen MON-1 contract:

- Web UI;
- Extension UI, including MSP-3 multi-session lane visibility;
- optional desktop UI adapter to same projection.

Exit gate: same event semantics across all UI surfaces; no shadow state.

### P8 — ACT-1 Command Gateway

Only after read-only monitor acceptance.

- typed command request;
- A-Conductor authorization;
- claim/replay/ownership validation;
- MSP-2 atomic/fenced hotspot admission before any material writer dispatch;
- result/evidence binding;
- no direct UI mutation.

Exit gate: destructive/ambiguous commands fail closed.

### P9 — MD-1 Multi-device + headless rollout

- Windows + macOS verified;
- RDC device adapter;
- Linux/Pi;
- Umbrel/headless Web UI;
- remote monitor auth only under separate threat model.

Exit gate: cross-device isolation and exact device/repo binding.

### P10 — SEM/ODP integration

- semantic activity projection from Issue #341;
- provider/model routing activity;
- ODP timeline/decision evidence;
- no authority merge.

### P11 — CONF-1 conformance / chaos / performance / security

Fault matrix:

- duplicate events;
- out-of-order events;
- missing events;
- adapter crash;
- monitor restart;
- STM eviction;
- backpressure;
- device disconnect;
- chat timeout/context rollover;
- process loss/reboot;
- stale repo/HEAD;
- secret-bearing malformed payload;
- untrusted extension reconnect;
- command replay;
- browser-to-localhost CSRF and DNS-rebinding attempts;
- cross-device clock skew;
- Hook Contract schema-version skew between producer and consumer;
- sustained-load/soak with bounded memory and backpressure;
- shared fake-secret/redaction corpus across every adapter.

Exit gate: task truth and execution safety remain correct.

### P12 — migration / retirement

Only after conformance:

- remove duplicated legacy monitor paths;
- consolidate Desktop/Web/Extension projection;
- retire transitional adapters only after parity;
- Serena Worker semantic dependency remains until Issue #341 conformance says
  native SRM parity is sufficient;
- clean obsolete worktrees/components only through accepted cleanup gates.

## 22. Parallelization guidance

After P1 contract freeze:

- Lane A: A-Conductor emitter/projection;
- Lane B: SRM execution hook seam;
- Lane C: harness adapter fixture/design preparation;
- Review lane: exact-SHA read-only architecture/review.

After MON-1 contract freeze:

- Web UI and Extension UI can run in parallel on non-overlapping codebases.

Do not parallelize two writers on the same event schema/hotspot.

## 23. Acceptance strategy

Every implementation milestone receives its own Work Order.

R3 components require as applicable:

- exact repo/worktree/task/claim binding;
- failure model;
- RED/GREEN deterministic tests;
- payload/redaction/adversarial tests;
- exact candidate SHA;
- independent exact-SHA review;
- hosted CI;
- cross-repo exact-SHA compatibility proof;
- post-main verification;
- durable evidence fold;
- cleanup only after evidence/ownership/process/unique-work proof.

## 24. Architecture questions reserved for independent review

GPT Astra should challenge at least:

1. Is the Hook Contract boundary correctly split between control plane and
   execution substrate?
2. Should Hook Bus be embedded in A-Conductor, SRM, or a transport-neutral
   local component?
3. Should the first monitor stream be SSE, WebSocket, local IPC or another
   transport?
4. What event ordering/causality model is sufficient without excessive
   complexity?
5. Is STM useful enough to justify a subsystem, or should it initially be a
   derived in-memory projection only?
6. Which hook classes must fail closed vs fail open?
7. How should redaction prevent prompt/command/secret leakage?
8. How should Kilo and Claude version/capability drift be handled?
9. Where should extension authentication live?
10. How should UI command requests be protected against replay/stale claim?
11. What performance budgets should be fixed before implementation?
12. Which existing A-Conductor event/lifecycle code should be extended instead
    of replaced?
13. Which roadmap phases can safely run in parallel?
14. Which phases are unnecessary/YAGNI and should be removed?
15. What is the smallest architecture that still reaches the final multi-device
    autonomous-control goal?

## 25. Definition of roadmap success

The roadmap is successful when the system can truthfully answer, in real time:

- What is each lane doing?
- On which device/repo/worktree/SHA?
- Through which harness/model?
- Which hook just fired?
- Is the event observed, derived or authoritative?
- What is blocked and why?
- What evidence exists?
- Is a delegated run still live, terminal-unharvested or complete?
- Is STM fresh or stale?
- Is the monitor itself healthy?

And when every consequential action still flows through A-Sunday Conductor
authority rather than through the monitor, STM, hook adapters or UI.


## 26. Mission Control / Agent Digital Twin follow-on — 2026-09-24

Dedicated plan:
`docs/plans/2026-09-24-mission-control-agent-digital-twin.md`

The operator-facing monitor should evolve from the MON-1/UI-1 read-only projection
into **A-Conductor Mission Control — Agent Digital Twin**: a 3D interactive view of
integrators, NightShift supervisors, A-Faster lanes, GLM/review agents, repositories,
devices, durable executions, PRs and CI.

This is a visualization/projection milestone, not a new authority layer. It consumes
the same normalized Monitor API/event stream as the 2D Web/Extension UI and must show
`STALE` / `UNKNOWN` / `DEGRADED` truthfully when evidence is incomplete.

Planned slices:
- `MC-0` scene/data/visual-semantics contract;
- `MC-1` read-only 2D operator console proving state semantics;
- `MC-2` 3D topology / interactive Agent Digital Twin;
- `MC-3` command audit trail + timeline replay;
- `MC-4` mobile operator-away/NightShift view;
- `MC-5` consequential controls only through accepted ACT-1 Command Gateway.

The 3D scene should make autonomous work visible rather than mysterious: who sent a
`/goal`, which model/effort is active, who owns each lane/hotspot, what external
dependency is being watched, where Sol acceptance is required, and what exact next
safe action follows. Model/quota/cost telemetry is read-only routing evidence.

Preferred implementation direction is React + Three.js / React Three Fiber after
MON-1 freezes the projection contract and after a lightweight benchmark confirms the
stack does not compromise mobile/headless fallback, accessibility or event-driven
low-overhead monitoring.

Acceptance invariant:

> 3D and 2D views must render the same normalized state; neither may become a second
> task/claim/scheduler/merge/completion authority.
