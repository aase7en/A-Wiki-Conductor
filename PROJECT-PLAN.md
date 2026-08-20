# A-Wiki Conductor — Project Plan

## 1. Project Vision

A-Wiki Conductor is a local autonomous control plane for coordinating multiple AI agents, coding agents, MCP servers, local models, cloud models, and A-Wiki memory.

The long-term goal is a controlled autonomous loop:

PLAN -> DECOMPOSE -> ROUTE -> EXECUTE -> VERIFY -> REVIEW -> REPAIR -> CONTINUE -> COMPLETE

The user should not need to manually copy prompts between sessions, repeatedly issue `continue`, select a model for every micro-task, run every test by hand, or manually move context between agents.

The Multi-Serena Control Center is an early subsystem and foundation of this larger architecture. A-Wiki Conductor must not be reduced to only a Serena launcher.

## 2. Architectural Principle

Do not fork Serena core by default.

Treat Serena as the semantic coding engine and MCP execution layer. Build A-Wiki Conductor above it as the orchestration and control-plane layer.

Serena remains responsible for:
- semantic code navigation
- symbol-aware editing and refactoring
- LSP integration
- project-local memory
- MCP tools

A-Wiki Conductor is responsible for:
- project registry
- reusable worker slots
- process lifecycle
- tunnel/profile assignment
- health checks
- task routing
- concurrency control
- agent/model selection
- verification/review loops
- activity history
- recovery and state visualization
- UI and operator experience

Fork Serena only if a required capability cannot be implemented cleanly through public CLI/config/MCP interfaces, process supervision, a wrapper/runtime manager, or a thin adapter layer. Any fork decision must be documented as `DECISION-SERENA-FORK` / `DECISION_REQUIRED` with an explicit upstream-maintenance, licensing, update, and security cost analysis.

Before considering a fork, attempt in order:
1. existing Serena CLI/config
2. MCP tools
3. process supervision / wrapper runtime manager
4. adapter/plugin
5. upstream contribution
6. maintained downstream fork as last resort

If a fork eventually becomes necessary, keep it as a maintained downstream engine. Do not move Conductor UI, task-broker, scheduler, or orchestration logic into Serena core.

## 3. Validated Multi-Serena Foundation

The multi-instance isolation design has now been validated in real local operation. This is validated implementation evidence, not a replacement for the product architecture.

Validated properties:
- separate Serena process per concurrent worker
- separate `SERENA_HOME` per worker
- separate tunnel-client process/profile per concurrently exposed ChatGPT connector
- separate health port per worker
- project pinning at Serena startup
- active-project state does not leak between independent Serena processes
- targeted stop does not broad-kill unrelated Serena workers
- idempotent start prevents duplicate worker processes
- PID ownership is checked before targeted stop
- existing uncommitted repository work remains untouched by infrastructure operations

Validated deployment on 2026-08-20:

| Worker | ChatGPT tool | Project | Instance root | Serena home | Health |
|---|---|---|---|---|---|
| Phase6 | `Serena_Local` | `A:\GitHub\A-Wiki-vnext-clean` | `C:\AI\serena-instances\phase6` | `C:\AI\serena-instances\phase6\serena-home` | `127.0.0.1:18012` |
| Conductor | `Sunday -Conductor` | `A:\GitHub\A-Wiki-Conductor` | `C:\AI\serena-instances\conductor` | `C:\AI\serena-instances\conductor\serena-home` | `127.0.0.1:18011` |

Legacy port `127.0.0.1:18010` has been retired from normal daily use and was verified free after migration. Legacy launcher/configuration material must be retained for rollback/recovery until a later explicit cleanup decision.

Verified migration matrix:
- PROCESS ISOLATION = PASS
- PORT ISOLATION = PASS
- SERENA_HOME ISOLATION = PASS
- PROJECT BINDING = PASS
- CONNECTOR SEPARATION = PASS
- CROSS-SESSION ACTIVE PROJECT LEAK TEST = PASS
- TARGETED STOP = PASS
- IDEMPOTENT START = PASS
- PHASE6 WORKTREE PRESERVATION = PASS

Operational implementation evidence currently lives outside this repository under `C:\AI\serena-instances\`. The runbook is `C:\AI\serena-instances\SERENA-MULTI-INSTANCE.md`.

Treat those files as reference evidence only:
1. inspect them to understand proven lifecycle/isolation patterns,
2. extract reusable concepts into typed Conductor abstractions,
3. do not blindly copy launcher implementation into the product,
4. keep infrastructure secrets and machine-specific credentials outside source control.

## 4. Worker Pool Model

The target design is not one permanent tunnel for every repository.

Use a small reusable worker pool sized for expected concurrency. Initial target: 3 concurrent worker slots.

Example:

```text
Worker 1 -> Project A
Worker 2 -> Project B
Worker 3 -> Project C / free slot
```

When a project is no longer actively running, its worker slot can be released and reassigned to another project.

A `Worker` is an isolated reusable execution slot, not a synonym for Serena. Serena is the first runtime implementation. The abstraction must remain compatible with future non-Serena workers and runtimes.

Core domain vocabulary should evolve around:
- `Project` — a registered work target; registration must not mutate the repository
- `Worker` — an isolated reusable execution slot
- `Runtime` — the execution environment hosted by a worker, initially Serena
- `Agent` — an AI/coding actor using a runtime or provider
- `Provider` — local or cloud capability source
- `Capability` — declared action/skill available for routing
- `Health` — observed runtime/process readiness state
- `Execution` — one bounded attempt of assigned work
- `ReviewResult` — structured verification/review outcome

A Serena-backed worker owns at minimum:
- worker ID and display name
- assigned project path
- isolated instance root
- isolated `SERENA_HOME`
- tunnel/profile assignment where remote ChatGPT access is required
- health/admin port
- process/PID ownership metadata
- log directory
- lifecycle state
- connector/app identity where applicable

Target lifecycle states:

```text
STOPPED -> STARTING -> READY -> BUSY -> STOPPING -> STOPPED
                         |        |
                         +-> ERROR <-+
```

Operational failure states should remain explicit rather than collapsing into a generic error:
- `PORT_IN_USE`
- `TUNNEL_COLLISION`
- `PID_MISMATCH`
- `PROJECT_NOT_FOUND`
- `PROJECT_IDENTITY_FAILED`
- `UNHEALTHY`
- `UNKNOWN`

The Conductor must refuse unsafe transitions such as duplicate use of the same tunnel, ambiguous PID ownership, or conflicting project assignment.

## 5. Concurrent Work Target

Primary operating target: 2-3 projects at the same time.

The UI and scheduler should optimize for this practical concurrency level first rather than designing for dozens of simultaneous local Serena processes.

The system should support many registered projects but only allocate worker resources to currently active projects.

Conceptual control path:

```text
A-Wiki Conductor
      |
      v
Project Registry
      |
      v
Scheduler / Worker Pool
      |
      v
Serena Runtime Manager
      |
      v
Isolated Serena Instances
      |
      v
MCP / Secure Tunnel Layer
      |
      v
ChatGPT / Codex / Local Agents
```

This is the initial Serena-backed path, not a permanent Serena-only constraint.

## 6. Desktop UI Direction

### Style

The UI should be minimal, CLI-inspired, compact, and information-dense, with restrained color accents.

Desired visual character:
- dark or near-dark neutral base
- terminal/CLI influence without looking like a raw terminal emulator
- monospaced font for commands, paths, logs, IDs, and status details
- highly legible sans-serif for labels/navigation where useful
- restrained semantic status colors: green = ready/healthy/running, amber = warning/busy/pending, red = error/blocked, muted blue/cyan = selected/active/informational, gray = idle/disabled/unknown
- use color as system state rather than decoration
- no excessive gradients
- no large decorative cards
- no glossy or game-like chrome
- no decorative charts without operational value
- no oversized typography
- minimal animation; transitions only where they improve state comprehension
- compact spacing so 2-3 workers and several projects can be understood at a glance

The application should feel closer to a polished developer console than a traditional enterprise/SaaS dashboard.

### Proposed Main Screen

```text
+--------------------------------------------------------------------+
| A-WIKI CONDUCTOR                    [Command Palette]      ● ONLINE |
+----------------------+---------------------------------------------+
| PROJECTS             | WORKERS                                     |
|                      |                                             |
| > A-Wiki Phase 6     | 01  READY   A-Wiki Phase 6      :18012     |
|   A-Wiki Conductor   | 02  READY   A-Wiki Conductor   :18011     |
|   Wastewater Webapp  | 03  FREE                                  |
|   Game Project       |                                             |
|                      | [Assign] [Start] [Stop] [Open] [Logs]       |
+----------------------+---------------------------------------------+
| ACTIVITY / LOG                                                     |
| 08:04  worker-01  Serena ready                                    |
| 08:05  worker-02  task accepted                                   |
| > _                                                                |
+--------------------------------------------------------------------+
```

### UX Principles

- keyboard-first where practical
- command palette for common actions such as Assign Project, Start Worker, Stop Worker, Open Logs, Open Project, Run Health Check, Inspect Serena, and Release Worker
- clear project/worker identity at all times
- never hide active project assignment
- dangerous operations must be visibly distinct
- one-click access to logs and health state
- no need to open raw `.cmd`, `.ps1`, PID, tunnel-profile, or Serena config files during normal operation
- operator should understand system state in under five seconds
- errors should show actionable causes, not stack traces by default
- raw logs remain available in an expandable panel

### Relationship to Serena Dashboard

Do not rebuild Serena's semantic tooling UI inside Conductor.

Conductor should surface only the operational state needed for multi-worker orchestration and either:
- open/link to Serena's own dashboard for deeper Serena inspection, or
- expose a small selected subset of Serena operational data when needed by the control center.

Conductor UI owns worker/project/runtime orchestration, not duplication of Serena internals.

## 7. Phase 1 — Multi-Serena Control Center

Phase 1 should convert the proven manual infrastructure into a managed desktop control center.

Scope:
- discover/register local projects without modifying the repository
- maintain project registry
- manage 3 reusable worker slots
- assign/release project to/from worker
- start/stop/restart worker safely
- isolated `SERENA_HOME` generation/management
- runtime profile generation/management
- per-worker Serena configuration surface (profile-driven, recorded 2026-08-21 from explicit user requirements): language backend / language-server selection, project binding, tool enable/disable (excluded/included/fixed tools), and modes — edited through the Conductor UI, materialized into the worker's isolated `SERENA_HOME` config, and applied on worker restart. Live `serena_config.yml` hand-editing remains a debugging fallback only. This is a selected subset exposed per the §6 Serena-dashboard relationship rule; Conductor does not clone the whole Serena dashboard.
- per-worker health port allocation
- health indicator per worker
- active-project verification after startup
- PID ownership validation
- stale PID detection and safe reconciliation
- tunnel collision prevention
- port collision prevention
- accidental project conflict prevention
- per-worker logs and recent events
- open project folder
- open Serena dashboard when enabled
- remember worker/project assignments
- status view for ChatGPT connector identity
- preserve rollback/recovery paths and existing manual launchers as debugging/recovery tools

Normal operation must not require manual editing of YAML, `.ps1`, `.cmd`, PID files, tunnel IDs/profiles, or Serena configuration.

Non-goals for Phase 1:
- autonomous coding loop
- automatic multi-model routing
- modifying or forking Serena core
- large plugin marketplace
- distributed/multi-machine workers

### Phase 1 Definition of Done

The control-center MVP is successful when the user can:
1. start A-Wiki Conductor,
2. see all known projects,
3. see three reusable worker slots,
4. assign a project to a free worker,
5. start the worker,
6. observe `STARTING` then `READY`, assigned project, health, and port,
7. run multiple different projects simultaneously,
8. stop/reassign a worker safely,
9. inspect logs when something fails,
10. recover without manually killing processes or editing runtime files.

The normal user workflow should not require understanding `SERENA_HOME`, PID files, tunnel-client profiles, health ports, or PowerShell launcher internals.

## 8. Phase 2 — Task Router

After Worker Control Center is stable:
- submit a goal once
- create task record
- decompose into bounded subtasks
- assign task to a worker/agent
- enforce repository and branch safety gates
- capture execution result
- verification step before completion
- operator-visible task timeline

Initial routing should be rule-based and deterministic before introducing model-driven dynamic routing.

The worker abstraction introduced in Phase 1 must allow future workers backed by Serena, Codex, local agents/models, cloud agents/models, or other runtimes/providers without changing the core task model.

## 9. Phase 3 — Review and Repair Loop

Add controlled autonomy:

EXECUTE -> VERIFY -> REVIEW -> REPAIR

Requirements:
- explicit retry budget
- stop conditions
- detection of repeated failure loops
- human approval gates for high-impact operations
- diff/review evidence before commit or deployment
- per-project safety policy

## 10. Phase 4 — A-Wiki Memory Integration

Connect A-Wiki as long-term operational memory:
- project history
- architecture decisions
- recurring failure patterns
- user preferences and workflows
- task handoffs
- worker outcomes
- reusable procedures

Memory retrieval must be scoped and evidence-aware so irrelevant historical context does not contaminate current execution.

## 11. Future Serena Fork Decision Gate

A maintained Serena fork is optional, not assumed.

Consider a fork only if one or more critical capabilities cannot reasonably be implemented through:
- Serena CLI/config
- MCP
- process supervision
- wrapper/runtime manager
- adapter/plugin
- upstream contribution

Examples that could trigger evaluation:
- worker lifecycle hooks unavailable externally
- required structured telemetry cannot be exposed through current interfaces
- project pinning/runtime isolation requires unsupported internal changes
- MCP behavior needed by Conductor cannot be implemented by wrapper/adapter
- upstream Serena architecture blocks critical orchestration features

A fork decision must explicitly evaluate:
- why upstream Serena cannot satisfy the requirement
- maintenance and merge cost
- licensing obligations
- update strategy
- security implications

## 12. Safety Requirements

Conductor must never casually perform broad process or repository operations.

Required protections:
- targeted PID ownership checks before stop/kill
- no broad kill of `python.exe`, `serena.exe`, or `tunnel-client.exe`
- no destructive Git operation without explicit policy authorization
- never silently `reset`, `clean`, `stash`, `checkout`, `switch`, `rebase`, `merge`, or force-push user work
- preserve dirty/uncommitted work
- registering/discovering a project must not modify that repository
- never automatically `git init` a registered project
- detect tunnel/port collisions before start
- never silently reuse a tunnel/profile already owned by another worker
- verify expected project identity after start
- each worker has explicit PID ownership, instance root, `SERENA_HOME`, health port, project assignment, runtime profile, and logs
- explicit `UNKNOWN`, `DECISION_REQUIRED`, `ISOLATION_FAILED`, `PORT_IN_USE`, `TUNNEL_COLLISION`, `PID_MISMATCH`, `PROJECT_NOT_FOUND`, `PROJECT_IDENTITY_FAILED`, and `UNHEALTHY` states where applicable
- Runtime/Admin/API keys must never appear in logs or UI
- do not store plaintext API keys in source-controlled configuration
- rollback path must exist for infrastructure migrations
- legacy launchers/configuration remain recovery material until an explicit cleanup decision

### Live lifecycle integration test gate

The first concrete A-Conductor lifecycle mutation test must use a dedicated isolated test worker rather than an active development/production worker. Prefer a free/sacrificial slot such as `A-Worker 3` with its own runtime root, `SERENA_HOME`, health port, transport binding, logs, and disposable/read-only test project.

Do not use the active Conductor or Phase6 worker as the first target for start/stop/restart testing. A live test must have explicit PID/resource ownership, rollback/recovery path, bounded scope, and evidence before the next mutation step.

Track this implementation gate as `DR-P1-002` until a dedicated lifecycle-test target is established.

### Dedicated transport provisioning gate

`DR-P1-003`: a dedicated live Worker 3 test must have a unique transport binding. A-Conductor must not silently reuse the active Conductor/Phase6 binding and must not invoke a credential-bearing/external tunnel provisioning flow merely because local provisioning scripts or credentials exist. External provisioning requires an explicit authorized provisioning action; until then, live Worker 3 transport validation is `BLOCKED_EXTERNAL` while local Control Center/UI work may continue.

## 13. Near-Term Implementation Order

1. Preserve current validated two-instance infrastructure as reference implementation; do not blindly copy it into the product.
2. Define `Worker`, `Project`, `Runtime`, `RuntimeProfile`, `Agent`, `Provider`, `Capability`, `HealthState`, `Assignment`, `Execution`, and `ReviewResult` data models.
3. Define failure-state and lifecycle contracts, including stale-PID recovery and collision handling.
4. Build local process manager around Serena/tunnel-client.
5. Build minimal CLI-inspired desktop shell.
6. Implement Projects + Workers screen.
7. Implement start/stop/restart/assign/release/health/log operations.
8. Add Worker 3 and test three-project concurrent operation.
9. Remove normal dependency on manual `.cmd`/PowerShell launchers while retaining them as recovery/debugging tools.
10. Per-worker Serena configuration surface (WO-P1-048): typed settings edited in the UI, rendered to the isolated `SERENA_HOME` config, applied on worker restart.
11. Add task router only after worker lifecycle is stable.
11. Revisit Serena fork decision only after real integration constraints are observed.

## 14. Product Definition of Done — Control Center MVP

The MVP is successful when the user can open one application, see registered projects and three worker slots, assign up to three projects, start them, confirm health/project identity, open concurrent ChatGPT/agent sessions, inspect logs, and stop/reassign workers without manually editing configuration files or accidentally leaking active-project state between projects.

The MVP must preserve the already validated isolation and safety properties while hiding `SERENA_HOME`, PID files, tunnel-client profiles, health ports, and launcher internals from normal operation.

## 15. Product Naming and Execution-Surface Strategy

### Approved Product Naming

The repository/project name remains `A-Wiki Conductor` / `A-Wiki-Conductor`.

The intended finished user-facing product name is:

**A-Conductor**

Initial reusable worker-slot display names:
- `A-Worker 1`
- `A-Worker 2`
- `A-Worker 3`

Recommended stable internal IDs:
- `a-worker-01`
- `a-worker-02`
- `a-worker-03`

An `A-Worker` is a reusable execution slot. It is not a synonym for a tunnel or for Serena. Serena is the first runtime implementation; future A-Workers may host other coding agents, local runtimes, or provider-specific execution surfaces.

### Execution-Surface Strategy

A-Conductor must explicitly account for execution-surface durability, not only model quality, price, or tool capability.

Validated operator experience shows that long chat-plugin-tunnel/Serena sessions may disconnect or become unstable, forcing the user to repeatedly issue `continue` even when the underlying project task is conceptually one continuous job.

Therefore:
- chat-plugin-tunnel/Serena work should be split into small, bounded, checkpointed, resumable execution transactions
- long-running or high-value tasks may be routed to more durable supported execution surfaces when available, including ChatGPT Work or future headless/agent interfaces
- ChatGPT Work is an optional execution surface/provider capability, not an architectural dependency
- A-Conductor remains authoritative for task state, authority, checkpoints, evidence, retry budget, recovery, and completion regardless of which execution surface performs the work
- an external surface reporting `done` is evidence, not sufficient authority by itself to mark a Conductor task complete
- the product goal is to remove the need for the user to repeatedly type `continue` merely because a specific transport/session cannot safely sustain a long operation

Future routing should be able to consider capability metadata such as:
- `supports_long_running`
- `supports_resume`
- `supports_background_execution`
- `supports_repo_tools`
- `requires_human_presence`
- `max_safe_transaction_scope`

This creates two complementary operating lanes rather than forcing every task through the same interface:

```text
Interactive / bounded repository work
  -> A-Worker + Serena/tunnel micro-transactions

Long-running / research / large artifact / durable agent work
  -> suitable long-running execution surface

Both
  -> A-Conductor task contract + checkpoints + evidence + review
```

### North Star — Work-Class Durable Agent Tunnel

A-Conductor is not intended to stop at being a Serena control panel. Its long-term product goal is to become a durable local/hybrid agent tunnel and execution fabric that provides as many of the practical capabilities of products such as GPT Work / Claude-style long-running work surfaces as can reasonably and safely be implemented.

Primary user outcome:

> Give A-Conductor a goal once, preferably from Discord or another lightweight operator surface, and let it plan, decompose, route, execute, checkpoint, resume, verify, review, repair, and continue across suitable workers without requiring the user to repeatedly carry context or type `continue`.

Target capabilities, implemented incrementally and without assuming any single vendor:
- long-running and resumable jobs
- background/durable execution where the selected worker/runtime supports it
- strong native filesystem, shell, Git, test, build, and artifact operations behind deterministic safety gates
- Serena as a semantic-code specialist rather than the only filesystem/shell engine
- multi-agent / multi-provider worker routing
- local, free, and low-cost model/runtime support where quality is sufficient
- selective escalation to premium models/surfaces only when their capability is materially valuable
- durable TODO/checklist/checkpoint/evidence/handoff state across sessions and vendors
- repository/worktree identity and mutation authority controls
- review/repair loops with explicit budgets and stop conditions
- Discord-first or similarly lightweight remote operator interaction, while preserving the desktop Control Center for local visibility and recovery
- provider/runtime neutrality so future execution surfaces can be added without redesigning the task model

### Cost and Quota Objective

A-Conductor should actively minimize unnecessary premium-model consumption and user subscription quota usage across future projects.

This means cost-aware and quota-aware routing should eventually consider, where observable and policy-allowed:
- whether deterministic/local execution can complete the step without an LLM
- whether a local/free/low-cost model is sufficient
- whether a premium reasoning model is required only for planning, difficult judgment, or review
- whether a durable external execution surface is justified for a long task
- model/provider price and practical quota pressure
- context size and repeated-context cost
- retry history and failure cost
- expected task duration and `max_safe_transaction_scope`

The goal is to **reduce dependence on and consumption of weekly / rolling-window premium limits**, not to bypass provider limits, access controls, or terms. Premium models should become high-value specialists rather than the default labor force whenever cheaper or local workers can safely do the work.

Conceptually:

```text
User / Discord
      |
      v
A-Conductor
  Goal + Durable Task State
      |
      +--> Deterministic/native tools        [lowest cost when sufficient]
      +--> Local/free/cheap A-Worker         [routine execution]
      +--> Serena semantic specialist        [code intelligence]
      +--> GPT/Claude/other premium worker   [hard reasoning/review]
      +--> Durable Work-class surface        [long-running jobs]
      |
      v
Evidence -> Verify -> Review -> Repair -> Continue -> Complete
```

### Relationship with A-Wiki Orchestrator

A-Conductor and A-Wiki orchestrator are complementary layers and should be developed to cooperate rather than replace one another.

Preferred responsibility split:
- **A-Wiki** = brain, durable knowledge, policies, architectural decisions, cross-project memory, work-order/claim conventions, existing orchestration intelligence, and reusable procedures
- **A-Conductor** = execution fabric, durable worker/runtime control, filesystem/process/tool execution, scheduling, checkpoints, evidence, recovery, operator UI/Discord gateway, and provider/runtime adapters
- **A-Worker** = replaceable execution slot that may host Serena, local models, Codex-like workers, cloud agents, deterministic tools, or future providers

A-Conductor must reuse or wrap A-Wiki orchestration primitives when practical. It must not create a second incompatible memory, claim, work-order, or orchestration universe merely because the execution control plane lives in another repository.

Long-term integration direction:

```text
A-Wiki
Knowledge / Policy / Memory / Orchestration Intelligence
        |
        v
A-Conductor
Durable Task + Cost/Quota Router + Execution Control Plane
        |
        v
A-Worker 1..N / Durable External Workers
        |
        v
Evidence / Handoff / Outcome
        |
        +--------------------> A-Wiki memory and learning loop
```

This North Star supersedes any interpretation of Phase 1 as the final product boundary. The current Serena Control Center is infrastructure needed to reach this larger goal.

## 16. A-Wiki Reuse-Before-Build Gate

**Binding boundary contract:** `docs/contracts/a-wiki-a-conductor-integration.md`
**Prepared A-Wiki companion registration payload:** `docs/contracts/a-wiki-companion-registration-payload.md`

A-Conductor remains a separate sibling Git repository, not an A-Wiki worktree by default. Repository separation does not permit orchestration duplication: the binding contract defines ownership, anti-duplication rules, logical cross-repo interfaces, and the `REUSE / WRAP / EXTEND / REPLACE / NEW` classification gate.

A-Wiki is the existing brain/policy/protocol repository and must be checked before A-Conductor creates coordination primitives that may already exist.

Current A-Wiki GitHub `main` already documents or references:
- `docs/protocols/cross-agent-plan-handoff.md` for resumable planning and `handoff.md` checkpoints
- `docs/protocols/cross-agent-work-orders.md` for work orders, claim tables, lanes, pause/resume, and cross-agent continuation
- `skills/awiki/a-claim/SKILL.md` plus `claim_acquire` / `claim_list` and TTL leases for duplicate-work prevention
- `wiki/context/session-memory.md` for cross-session decisions and TODOs
- Hermes as an existing long-horizon orchestrator
- AG2 goal planning/chunking, swarm delegation, and cost-first model routing

This overlap is intentional input to A-Conductor, not permission to duplicate it.

Before implementing handoff, work-order, claim/lease, task-router, scheduler, model-router, long-horizon orchestration, memory-coordination, or other architecture-level coordination features, the following **mandatory pre-work gate** must pass:
1. Inspect the current authoritative **A-Wiki GitHub** state, not only the local worktree.
2. Inspect relevant A-Wiki ADRs, protocols, scripts, skills, and existing orchestration surfaces.
3. Inspect current **work orders** and active/paused ownership records relevant to the proposed capability.
4. Inspect **live claims / leases** where the A-Wiki coordination system exposes them, so another session or agent is not already working on the same surface.
5. Inspect known local **worktrees / branches / current-work or handoff records** that may contain parallel work not yet visible from the current worktree.
6. Classify the proposed A-Conductor capability as `REUSE`, `WRAP`, `EXTEND`, `REPLACE`, or `NEW`.
7. Prefer `REUSE -> WRAP -> EXTEND` before building a parallel implementation.
8. Any `REPLACE` or materially overlapping `NEW` capability requires `DECISION_REQUIRED` with migration, compatibility, and duplication impact.
9. Record the resulting boundary in both A-Conductor continuity artifacts and, when appropriate, A-Wiki GitHub so the projects remain cross-linked.

**Gate rule:** if GitHub/work-order/claim state cannot be checked when that state is material to duplicate-work risk, do not assume the current local worktree is authoritative. Record the verification gap and avoid starting overlapping architecture work until the risk is reconciled.

A local worktree must never be assumed to represent current A-Wiki truth by itself. This gate exists specifically to prevent separate worktrees, sessions, GPT Work tasks, A-Workers, or external agents from independently implementing the same architecture.

## 17. Handoff, Memory, and Cross-Agent Continuity

Handoff continuity is a core project invariant, not optional documentation hygiene.

Long-running work must be resumable across chat sessions, GPT Work, A-Workers, Serena sessions, and external AI/coding agents without relying on conversational memory. Repository/project artifacts are the durable source of truth; chat context is temporary transport context.

For every non-trivial task, maintain directly or through existing equivalent documents:
- current goal, scope, and phase/task ID
- ordered TODO/checklist with explicit `DONE`, `IN_PROGRESS`, `BLOCKED`, or `NOT_STARTED` state
- completed steps and evidence
- exact files/areas changed
- commands/tests run and results
- repository/worktree/branch/HEAD identity when repository work is involved
- unresolved questions and `DECISION_REQUIRED` items
- next safe action(s)
- forbidden actions and safety constraints
- assumptions/dependencies
- a handoff summary sufficient for a new session or different-vendor agent to resume without guessing

Preferred durable document roles, reusing existing equivalents rather than creating duplicates blindly:
- `PROJECT-PLAN.md` = authoritative long-term plan and roadmap
- `CURRENT-WORK.md` = active phase/task, checklist, evidence, and next steps
- `HANDOFF.md` = concise cross-session/cross-agent transfer snapshot
- ADR/decision records = durable, expensive-to-reverse decisions

Required operating discipline:
1. Before work, read the authoritative plan, current-work state, latest handoff, and relevant decisions.
2. Before mutation, verify identity, scope, authority, and safety constraints.
3. During work, update checklist/checkpoints at meaningful boundaries rather than waiting for the end of a long session.
4. On interruption, failure, or session end, update the durable handoff before stopping whenever the execution surface permits it.
5. On resume, reconcile the actual current state against the handoff; never assume a previous agent completed an action merely because it claimed success.
6. Mark work complete only when required evidence/verification exists.
7. Never silently overwrite conflicting decisions; raise `DECISION_REQUIRED`.

A-Conductor should eventually automate this continuity protocol so the user does not need to repeatedly carry context, copy prompts, or type `continue` across fragile execution surfaces.

## 18. Future Autonomous Control Loop Compatibility

The Multi-Serena Control Center is the first operational subsystem, not the final product boundary.

Future direction remains:

```text
Goal
  |
  v
Planner
  |
  v
Task Graph
  |
  v
Router
  |
  v
Worker Scheduler
  |
  v
Serena / Codex / Local / Cloud Agent
  |
  v
Verifier
  |
  v
Reviewer
  |
  v
Repair
  |
  v
Continue
  |
  v
Complete
```

The initial implementation may be Serena-backed, but core product concepts must remain runtime/provider neutral so that future agents and execution engines can be composed without redesigning the control plane.

## 19. Resilient Execution Supervisor — Transport-Independent Recovery

**Binding contract:** `docs/contracts/resilient-execution-supervisor.md`
**Architecture capture:** `docs/work-orders/WO-P1-044-resilient-execution-supervisor-plan.md`

Real A-Wiki Phase 6 failures established a stronger reliability requirement: a Serena/MCP/chat transport can return HTTP 502 or terminate while the underlying process continues or has already completed successfully. Therefore A-Conductor must treat transport state and execution state as independent dimensions.

Core invariant:

> **TRANSPORT FAILURE != EXECUTION FAILURE**

Consequences:
- never mark a substantial execution failed merely because its requesting/observing transport disappeared;
- never blind-retry until the original execution is classified as never-started, still-running, completed, partial, or unknown;
- preserve execution/job/file ownership across temporary transport loss;
- re-check project/repo/branch/HEAD/dirty/claim identity before mutation after reconnect;
- prefer supervised launch/inspect/collect for medium/long/high-output operations instead of one long MCP request;
- persist durable run/log/report evidence and return bounded summaries/tails through transports;
- deduplicate equivalent live executions using stable execution fingerprints;
- use a fake backend/fault-injection harness rather than real Serena outages as the recovery test mechanism;
- keep the abstraction backend-neutral for Serena, Codex, local shell, MCP servers and future workers.

This capability is an **`EXTEND + WRAP`** of the existing durable job store/execution coordinator/native execution/owned-process/lifecycle recovery foundation. It must not create another job state machine, work-order system, planner, scheduler universe or A-Wiki memory system.

MVP sequence:
1. `AC-RES-001` — durable execution record;
2. `AC-RES-002` — supervised subprocess launch/inspect/collect;
3. `AC-RES-003` — transport-loss state separation;
4. `AC-RES-004` — recovery reconciliation + identity gate;
5. `AC-RES-005` — duplicate-execution protection;
6. `AC-RES-006` — output backpressure + durable reports;
7. `AC-RES-007` — fake executor + deterministic fault injection;
8. `AC-RES-008` — Serena adapter integration.

Advanced backend failover/routing should begin only after these primitives pass deterministic recovery tests. A-Conductor may enforce operational scheduling/routing/recovery, but A-Wiki remains owner of orchestration intelligence, policy, durable knowledge and cross-project memory.
