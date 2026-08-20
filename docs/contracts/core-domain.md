# A-Conductor Core Domain Contract

Status: C1 baseline
Schema generation: JSON Schema Draft 2020-12
Active work order: `WO-C1-001`

## 1. Purpose

This document defines the canonical domain vocabulary and invariants for A-Conductor before runtime, broker, Serena adapter, or desktop UI implementation.

A-Conductor must remain:

- provider-neutral;
- runtime-neutral;
- local-first;
- resumable;
- evidence-first;
- compatible with A-Wiki's existing handoff/work-order/claim protocols;
- safe when sessions, tunnels, workers, or external agents disappear mid-task.

## 2. Boundary with A-Wiki coordination primitives

A-Wiki already owns reusable cross-agent coordination conventions such as work orders, claims, pause/resume, handoff, model-cost guidance, and durable project knowledge.

A-Conductor does **not** redefine those concepts merely to obtain a different file format or UI.

Canonical distinction:

- **A-Wiki Work Order** — human/agent-readable cross-agent chunk specification and ownership artifact.
- **A-Wiki Claim** — coordination ownership/lease preventing duplicate work on a shared surface.
- **A-Conductor Task** — durable runtime-control object representing work that the Conductor schedules, gates, executes, verifies, reviews, recovers, and completes.
- **A-Conductor Execution Lease** — runtime lease for one execution attempt. It may wrap or synchronize with an A-Wiki claim, but it is not permission to ignore A-Wiki ownership rules.

A Task may reference an A-Wiki work order. A lease may reference an A-Wiki claim. They are related but not assumed identical.

## 3. Canonical vocabulary

### Project

A registered work target.

A Project may describe a repository/worktree or another bounded work surface. Registration is metadata-only and must not mutate the target, initialize Git, change branches, install dependencies, or create files inside the target unless a separate authorized task permits it.

### Worker

An isolated reusable execution slot managed by A-Conductor.

A Worker is **not** a synonym for Serena, tunnel, model, project, or agent. Initial display names are `A-Worker 1`, `A-Worker 2`, `A-Worker 3`; internal IDs use stable machine-safe identifiers such as `a-worker-01`.

A Worker can be released and reassigned to another Project.

### Runtime

The executable environment hosted or controlled through a Worker.

Examples may include Serena, a coding-agent CLI, a local agent process, or another supported runtime. Serena is the first runtime implementation, not the Worker definition.

### Agent

An AI/coding actor that performs reasoning or execution through a Runtime or Provider.

Agent identity is distinct from model identity and worker identity.

### Provider

A replaceable source of model or agent execution capacity.

Examples can be local or cloud. Provider/product/model names are volatile metadata and must not become architectural policy keys.

### Capability

A declared, measurable ability required for routing or execution.

Examples:

- semantic code navigation;
- repository mutation;
- shell execution;
- deterministic test execution;
- long-running execution;
- resumability;
- background execution;
- web research;
- structured tool use.

Capabilities are claims that must be backed by adapter configuration and, where important, observed health/evidence.

### Assignment

A bounded relationship connecting a Task/Project to a Worker/Runtime for a defined period or attempt.

Assignment does not itself grant mutation authority. The Task Contract remains the authority boundary.

### Health

Observed readiness/state information for Worker, Runtime, Provider, or connector components.

Health is evidence, not a desired state. A process existing is insufficient to claim `READY`; identity and readiness checks may be required.

### Task Contract

A versioned machine-readable authority specification for one bounded task.

It defines goal, scope, target identity, allowed/forbidden actions, acceptance criteria, verification, budgets, retry/recovery rules, escalation conditions, and required evidence.

A worker may propose an amendment; it cannot silently expand its own Task Contract.

### Task

The durable state-machine object controlled by A-Conductor.

Recommended lifecycle baseline:

`NEW -> PLANNING -> READY -> CLAIMED -> GATING -> EXECUTING -> VERIFYING -> REVIEW_PENDING -> COMPLETE`

Failure/recovery branches:

- `VERIFYING -> REPAIRING -> EXECUTING`
- `REVIEW_PENDING -> CHANGES_REQUIRED -> REPAIRING`
- any active execution state -> `BLOCKED`
- stale/disconnected execution -> `RECOVERY_NEEDED`
- bounded terminal failure -> `FAILED`
- authorized cancellation -> `CANCELLED`

State transitions must be explicit and auditable.

### Execution

One bounded attempt to carry out all or part of a Task.

Every Execution has a stable attempt ID and records worker/runtime/provider, timing, budget consumption, checkpoints, outcome, and evidence references.

A retry creates a new Execution attempt; it does not rewrite history.

### Execution Lease

A time-bounded ownership token allowing one Worker/Execution attempt to act on a Task.

Lease expiry means **ownership is uncertain**, not "retry immediately".

Expired or stale leases move the Task to reconciliation/recovery before another mutating attempt can begin.

### Checkpoint

A durable boundary recording what was known or changed after a meaningful execution phase.

Typical phases:

`GATE -> READ -> EDIT -> VERIFY -> REVIEW -> COMMIT`

Not every task uses every phase. Fragile execution surfaces require smaller and more frequent checkpoints.

### Repository Identity

A verified snapshot of the repository/worktree context against which mutation authority is evaluated.

It may include absolute worktree identity, repository identity, branch, HEAD, dirty state, expected baseline, allowed paths, and relevant file hashes.

### Evidence Record

An immutable or append-only structured observation supporting verification, recovery, review, cost measurement, or audit.

Examples include command/exit status, test summary, changed files, diff hash, branch/HEAD, checksums, health observations, reviewer outcome, and warnings.

Evidence is not automatically promoted into A-Wiki long-term knowledge.

### ReviewResult

A structured reviewer outcome such as:

- `PASS`;
- `CHANGES_REQUIRED`;
- `BLOCKED`;
- `ESCALATE`.

A ReviewResult references evidence and scope. Reviewer prose alone does not overwrite deterministic evidence.

### Approval

A human or explicitly authorized policy decision required for operations beyond autonomous authority.

Examples expected to require human approval include production deployment, destructive persistent-data operations, force push, credential rotation, irreversible infrastructure changes, and material expansion outside the approved repository/task boundary.

### Execution Surface

The transport/environment through which an agent performs work.

Examples include chat-plugin-tunnel, GPT Work, ACP coding agents, CLI/headless agents, or local model processes.

Routing must consider surface durability in addition to model intelligence/cost.

## 4. Core invariants

### INV-001 — Authority is external to the worker

An LLM/agent may propose an action. Only the Task Contract + Conductor policy determine whether the action is authorized.

Tool availability is not task authority.

### INV-002 — Project registration is non-mutating

Registering/discovering a Project must not modify the project/repository.

### INV-003 — Worker slots are reusable

A Worker is a reusable isolated slot and must not be permanently bound to one repository, Serena home, model, or provider identity.

### INV-004 — Serena is an engine, not the control plane

Serena supplies semantic code/project tooling. A-Conductor owns worker lifecycle, assignment, task state, policy enforcement, recovery, evidence, and operator state.

### INV-005 — Identity gate before mutation

A mutating Execution must verify the actual target identity against the contract before mutation.

Mismatch requires stop/reconciliation; it must never be silently repaired with checkout/reset/clean/stash.

### INV-006 — No blind retry after disconnect

A vanished worker/session/lease must enter `RECOVERY_NEEDED` before another mutating attempt.

Recovery classifies actual state before choosing resume/retry/escalation.

### INV-007 — History is append-only by attempt

Retries create new attempt IDs. Previous attempts/evidence remain inspectable.

### INV-008 — Deterministic verification first

When tests, lint, typecheck, schema validation, hashes, Git inspection, or static checks can establish a fact, prefer them over an LLM assertion.

### INV-009 — `DONE` requires acceptance evidence

A Task cannot become `COMPLETE` solely because a worker reports completion. Acceptance criteria and required review/evidence must pass.

### INV-010 — Cost routing cannot bypass risk policy

Cost/quota optimizers may select among eligible workers/providers only after required capability, security/risk, privacy, and authority constraints are satisfied.

### INV-011 — Execution-surface durability is routable metadata

Routing may consider fields such as `supports_long_running`, `supports_resume`, `supports_background_execution`, `requires_human_presence`, and `max_safe_transaction_scope`.

Fragile chat/tunnel surfaces should receive bounded micro-tasks; durable surfaces may receive longer work when permitted.

### INV-012 — Raw execution history is not A-Wiki memory

Execution logs/evidence remain Conductor operational history unless explicitly distilled/promoted according to A-Wiki knowledge/privacy rules.

### INV-013 — Reuse-before-build is mandatory

Before implementing a coordination primitive, inspect A-Wiki GitHub/work orders/live claims/relevant worktrees and classify the capability as `REUSE`, `WRAP`, `EXTEND`, `REPLACE`, or `NEW`.

### INV-014 — Cross-agent continuity is mandatory

No critical state may exist only in chat context. Work orders, current-work state, checkpoints, evidence, and handoff must allow another agent to resume safely.

### INV-015 — Lease expiry is not retry authority

Expiry only establishes that ownership is stale/uncertain. Reconciliation determines what actually happened.

### INV-016 — External `done` is evidence, not final authority

A GPT Work task, coding agent, provider, or worker may report `done`; A-Conductor still applies acceptance/verification/review policy before Task completion.

## 5. Recovery classifications

When a worker disappears or task state is uncertain, reconciliation should classify the target as one of:

- `NO_MUTATION` — expected mutation did not begin or no target change is observed;
- `PARTIAL_MUTATION` — bounded intended changes exist but task/phase is incomplete;
- `MUTATION_COMPLETE_UNVERIFIED` — intended mutation appears complete but required verification/evidence is missing;
- `COMPLETE_VERIFIED` — intended mutation and required verification are present;
- `UNEXPECTED_DRIFT` — state changed outside the expected contract/scope/baseline;
- `UNKNOWN` — evidence is insufficient to classify safely.

Only policy-approved classifications may transition to a new mutating attempt.

## 6. Risk and approval baseline

Suggested risk classes:

- `LOW` — read-only or isolated mechanical operation with no meaningful persistence risk;
- `NORMAL` — bounded project mutation under verified repository identity and acceptance tests;
- `HIGH` — security/auth/architecture/shared-state or broad-scope mutation requiring stronger reviewer/escalation;
- `HUMAN_REQUIRED` — irreversible/destructive/production/credential operations that autonomous policy cannot approve.

Risk class is independent from model price or intelligence tier.

## 7. Retry/circuit-breaker baseline

Every Task Contract may constrain:

- max attempts;
- max identical failure count;
- max changed files;
- max diff size;
- max elapsed time;
- max token/cost budget;
- max consecutive worker/provider failures;
- allowed scope growth (normally none without amendment).

Repeated identical failure, unexpected destructive action, merge conflict, baseline invalidity, credential requirement, privacy risk, security-boundary change, or scope expansion should escalate instead of looping.

## 8. Contract artifacts

C1 machine-readable schemas:

- `schemas/task-contract.schema.json`
- `schemas/repository-identity.schema.json`
- `schemas/evidence-record.schema.json`

These schemas are authority/data contracts, not a commitment to a particular programming language, ORM, broker, UI framework, or provider.
