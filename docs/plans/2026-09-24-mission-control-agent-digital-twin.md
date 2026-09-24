# A-Conductor Mission Control — Agent Digital Twin

Status: ROADMAP / NOT IMPLEMENTATION-AUTHORIZED
Date: 2026-09-24
Topology: CONTROL_PLANE_ONLY UI/observability projection
Parent roadmap: `docs/plans/2026-09-19-a-faster-hook-stm-observability-roadmap.md`

## 1. Product goal

Build a visually rich operator surface that lets the user understand, in seconds,
what A-Sunday Conductor, Codex, GLM lanes, GitHub CI, devices, repositories and
durable executions are doing without opening terminals or asking ChatGPT for state.

The target experience is a 3D interactive **Agent Digital Twin / Mission Control**,
not a decorative dashboard. Every node, edge, animation and timeline item must map
to normalized evidence already projected by A-Conductor.

Primary user question:

> Who is doing what, where, under which authority, and what happens next?

## 2. Non-negotiable authority boundary

Mission Control is an **observer/projection first**.

It MUST NOT become:
- a task database;
- a claim/lease authority;
- a scheduler;
- a retry engine;
- a completion or merge authority;
- a second source of execution truth;
- a replacement for Git/GitHub/Sunday durable evidence.

Actual Git/GitHub/runtime/durable evidence outranks the UI.

All UI state is derived from the accepted Monitor projection/API. If the projection
is stale, missing or contradictory, the UI must show `STALE`, `UNKNOWN` or
`DEGRADED` rather than inventing a clean state.

## 3. 3D scene model

Preferred visualization direction: React + Three.js / React Three Fiber, subject to
benchmarking against the accepted Web UI stack.

Represent at least:
- GPT/Sol integrator node;
- Codex / A-NightShift supervisor node;
- GLM-5.3 MAX mutable/review lanes;
- GLM Flash read-only helper lanes;
- advisory agents such as JEV;
- GitHub / PR / CI nodes;
- repository/worktree nodes;
- device/runtime nodes;
- durable execution nodes.

The scene should cluster by project/repository and remain usable for the practical
2–3 project concurrency target rather than optimize for hundreds of agents.

## 4. Live visual semantics

Visual state must be deterministic, not cosmetic.

Examples:
- pulse / subtle motion = actively executing;
- slow orbit / breathing = `WAITING_EXTERNAL`;
- static ready ring = `READY`;
- ownership ring = current claim/hotspot owner;
- animated edge = handoff/tool/model call in progress;
- warning halo = degraded/ambiguous evidence;
- frozen/locked node = real stop gate;
- broken/faded edge = unavailable route;
- CI progress arc = exact GitHub Actions state;
- queue marker = queued continuation/message;
- collision marker = competing hotspot/request denied.

Animations must never imply progress when authoritative state is unchanged.

## 5. Operator drill-down

Selecting a node opens a side panel with the exact normalized facts relevant to it.

For an agent/execution:
- model + effort;
- role;
- execution/attempt IDs;
- task/WO + claim;
- repo/worktree/branch/SHA;
- current state and duration;
- exact external dependency;
- next safe action;
- stop gate;
- evidence pointers.

For A-Faster:
- mutable lanes used / max 3;
- review lane used / max 1;
- `FANOUT_TARGET`;
- `UNUSED_SAFE_CAPACITY`;
- `A_FASTER_UNDERUTILIZED`;
- `AUTO_REFILL_REQUIRED`.

## 6. Command audit trail

The UI must make autonomous delegation visible.

Show a chronological event stream such as:
- Sol materialized NightShift contract;
- Sol launched Codex supervisor;
- `/goal` was sent;
- Codex recovered durable executions;
- reviewer dispatched;
- CI watcher started;
- result harvested;
- Sol acceptance requested;
- PR merged;
- post-main verification completed.

Each event should preserve actor, target, timestamp, correlation/causation IDs and
sanitized evidence references. Raw prompts, tokens, secrets and unrestricted command
lines are excluded by default.

## 7. Timeline replay

Provide a replay slider over normalized durable events.

The operator should be able to answer:
- what was running at a chosen time;
- which lane owned each hotspot;
- when a handoff occurred;
- why a wait or stop happened;
- which evidence caused a transition;
- whether state was observed, derived or unknown.

Replay is read-only reconstruction. It must never mutate current task state or create
a parallel historical state authority.

## 8. Mobile and 2D fallback

The 3D view is progressive enhancement, not the only usable monitor.

Required fallbacks:
- compact 2D topology/list view;
- timeline view;
- lane table;
- command audit trail;
- evidence drill-down.

On phones, prioritize current blocker, next safe action, active executions, CI state,
quota/cost and stop gates over full 3D navigation.

A low-power/headless client must remain useful even when WebGL is unavailable.

## 9. Model / cost telemetry

Mission Control should expose read-only model economics and routing evidence:
- model/provider;
- effort/variant;
- token counts where available;
- quota/readiness state;
- estimated or observed cost where trustworthy;
- which model was selected as supervisor, worker, reviewer or integrator.

The UI may compare available routing candidates, but it does not select or authorize
a model by itself. Model choice remains with the accepted routing/integrator policy.

Unknown or unavailable pricing/quota data must display as unknown, never zero.

## 10. Interaction phases

### MC-0 — design/projection contract
Freeze scene vocabulary, state-to-visual mapping, data contract and failure semantics.

### MC-1 — read-only 2D operator console
Consume MON-1 projection; prove exact state semantics before 3D.

### MC-2 — 3D Agent Digital Twin
Add topology scene, interactive nodes/edges, status animation and project clustering.

### MC-3 — timeline replay + command audit
Replay normalized events and explain autonomous delegation/handoffs.

### MC-4 — mobile/operator-away view
Responsive monitoring for NightShift/A-Faster while the operator is away.

### MC-5 — consequential controls
Only after ACT-1 Command Gateway is accepted.

## 11. Consequential-control rule

Future buttons may include:
- pause;
- cancel;
- recover;
- retry;
- reassign;
- release lane;
- cleanup request;
- merge/release request.

Every button sends a typed command request to the accepted A-Conductor Command
Gateway. The UI never directly kills a process, edits Git, changes a claim, creates
a lease, merges a PR or changes completion state.

No control button is enabled merely because the 3D scene appears healthy.

## 12. Security and privacy

- local/private by default;
- explicit authenticated session for browser clients;
- origin validation and DNS-rebinding/CSRF defenses;
- no secret values in scene data;
- raw prompts disabled by default;
- raw command lines sanitized or replaced by digest/reference;
- bounded payloads;
- untrusted adapter data validated before rendering;
- no executable HTML/markdown from agent output rendered unsafely;
- evidence links point to sanitized durable records.

A rendering failure must not affect execution.

## 13. Performance / UX acceptance

The operator should understand the current system state within five seconds.

Acceptance should include:
- no model polling caused by the UI;
- no periodic subprocess spawning for visual refresh;
- event-driven updates from the Monitor stream;
- scene degradation/fallback under large event bursts;
- bounded memory for timeline replay;
- 3D animation pauses/reduces when tab is hidden;
- no stale animation that falsely suggests active progress;
- keyboard and non-3D navigation remain available;
- mobile view remains operational on modest hardware.

Visual polish is important, but correctness of state semantics has priority.

## 14. Dependency order

Mission Control depends on, and must reuse:
1. accepted Hook Contract;
2. A-Conductor + Sunday execution emitters;
3. Hook Bus / derived STM;
4. MON-1 shared read-only Monitor projection/API;
5. MSP-3 provenance for multi-session traceability;
6. A-Faster utilization markers;
7. NightShift execution/receipt events.

MC-5 consequential actions additionally depend on ACT-1 Command Gateway.

Do not build a separate websocket task store or UI-owned agent graph database to
bypass these dependencies.

## 15. Definition of done

The Mission Control track is successful when a user can open one screen and
truthfully see:
- every active project/lane/agent and its exact role;
- current repo/worktree/SHA and device;
- who dispatched whom;
- current execution and external waits;
- A-Faster WIP/utilization;
- NightShift state and next action;
- CI/PR progress;
- model/quota/cost telemetry;
- blockers and stop gates;
- durable evidence behind every important transition;
- a replay of how the current state was reached.

The same facts must agree with the non-3D monitor/list view because both consume the
same projection. 3D is a visualization layer, never a second truth layer.
