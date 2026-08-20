# A-Wiki ↔ A-Conductor Responsibility & Integration Contract

Status: binding architecture contract
Version: 1
Last updated: 2026-08-20

## 1. Decision

`A-Wiki-Conductor` remains a **separate sibling Git repository** from `A-Wiki`.

It is not an A-Wiki worktree and should not become one by default. A Git worktree represents another checkout/branch of the same repository and history; A-Conductor has an independent product/runtime lifecycle, packaging surface, persistent execution state, desktop/Discord operator surfaces, worker adapters, process supervision, and future provider integrations.

A-Wiki already has a validated sibling-repository precedent: production application code can live in a separate repository while A-Wiki remains the durable knowledge/policy/domain source and stores a companion pointer back to that repository.

Changing this boundary requires `DECISION_REQUIRED` with migration, compatibility, release, security, and history impact.

## 2. North-star relationship

The two repositories form one cooperating system with different authorities:

```text
A-Wiki
Knowledge / Policy / Memory / Orchestration Intelligence
        |
        | versioned policy / work-order / claim / skill / context contracts
        v
A-Conductor
Durable Task Runtime / Execution Control Plane / Cost Enforcement
        |
        v
A-Worker 1..N / deterministic tools / external durable workers
        |
        v
Evidence / result / handoff / learned outcome
        |
        +------------------------------> A-Wiki
```

Short rule:

> **A-Wiki owns durable brain/policy/orchestration knowledge. A-Conductor owns durable execution/runtime/recovery. A-Workers perform bounded work.**

## 3. Responsibility ownership

| Capability | A-Wiki authority | A-Conductor authority |
|---|---|---|
| Cross-project knowledge / second brain | OWNER | consume + return outcomes |
| Architectural decisions / ADR knowledge | OWNER | enforce applicable decisions |
| Skills / reusable procedures | OWNER | discover/execute through adapters |
| Cross-agent work-order convention | OWNER | implement/consume without incompatible fork |
| Claim/lease convention | OWNER | integrate/enforce at execution boundary |
| Long-term/session memory conventions | OWNER | write evidence/handoffs back through contract |
| High-level orchestration intelligence | OWNER / reusable source | invoke/wrap; do not silently duplicate |
| Cost/model policy knowledge | OWNER | operational routing/enforcement |
| Durable task runtime state | reference/knowledge | OWNER |
| Worker pool / worker assignment | policy input | OWNER |
| Process/PID/port/tunnel lifecycle | safety policy | OWNER |
| Filesystem/shell/Git/test/build execution | policy/constraints | OWNER |
| Runtime checkpoint/recovery/resume | protocol input | OWNER |
| Evidence collection/runtime journal | schema/policy input | OWNER |
| Desktop Control Center | optional knowledge | OWNER |
| Discord/operator gateway | optional knowledge/policy | OWNER |
| Provider/runtime adapters | provider knowledge | OWNER |
| Runtime secret/reference handling | policy | OWNER of safe implementation; secrets never copied to A-Wiki by default |

Ownership means the other repository may wrap, call, cache a versioned projection, or implement an execution adapter for the capability; it does **not** authorize an incompatible second source of truth.

## 4. Mandatory reuse-before-build classification

Before A-Conductor implements an architecture-level capability that could overlap A-Wiki, classify it as exactly one of:

- `REUSE` — use A-Wiki capability/protocol directly.
- `WRAP` — keep A-Wiki authoritative and expose it through an A-Conductor adapter.
- `EXTEND` — add execution-specific behavior while preserving the A-Wiki contract/source of truth.
- `REPLACE` — intentionally supersede an A-Wiki capability.
- `NEW` — capability is genuinely outside A-Wiki ownership.

Preference order:

`REUSE -> WRAP -> EXTEND -> NEW/REPLACE only with evidence`

`REPLACE`, or materially overlapping `NEW`, requires `DECISION_REQUIRED` including:

1. current A-Wiki implementation/protocol checked;
2. active work orders/claims checked where available;
3. compatibility and migration plan;
4. duplicate-state risk;
5. rollback path;
6. explicit owner after migration.

## 5. Anti-duplication gate

Do not begin a new A-Conductor planner, work-order system, claim system, memory layer, scheduler policy, model router, long-horizon orchestrator, or similar coordination primitive merely because implementation in A-Conductor would be convenient.

First inspect authoritative A-Wiki state, relevant protocols/ADRs/skills/scripts, active work orders/claims, and known parallel worktrees/branches when material. If authoritative state cannot be checked, record the verification gap and avoid overlapping architecture mutation.

The repository boundary is **not** permission to duplicate orchestration.

## 6. Integration contracts

The following logical interfaces are the intended direction. Their concrete schemas may be versioned later; these names establish responsibility now.

### 6.1 `ExecutionRequest`

Direction: `A-Wiki/orchestrator -> A-Conductor`

Minimum semantic content:
- goal/task identity;
- project/repository identity requirements;
- allowed mutation scope and authority;
- acceptance criteria / verify requirements;
- relevant skills/policies/work-order/claim references;
- routing constraints or preferences;
- budget/quota/escalation policy;
- human approval requirements.

A-Conductor may decompose the request into bounded runtime transactions, but must not silently weaken authority or acceptance criteria.

### 6.2 `PolicySnapshot`

Direction: `A-Wiki -> A-Conductor`

A versioned projection of execution-relevant policy. A-Conductor may cache it for durability but A-Wiki remains authoritative for policy meaning. Cached policy must carry source/version identity and must not be presented as current when freshness is unknown.

### 6.3 `EvidenceBundle`

Direction: `A-Conductor -> A-Wiki/reviewer`

May include:
- pre/post repository identity;
- changed-file/diff identity;
- command/test/build results;
- runtime/tool/model versions;
- checkpoints/recovery classification;
- warnings/refusals/escalations;
- artifact references;
- final verification state.

Secret values, tunnel IDs, API keys, credential contents, or unredacted sensitive runtime payloads are excluded by default.

### 6.4 `ExecutionResult`

Direction: `A-Conductor -> A-Wiki/orchestrator`

Carries result state such as COMPLETE / CHANGES_REQUIRED / BLOCKED / RECOVERY_NEEDED / FAILED plus evidence references and resumable next action.

An external worker saying `done` is evidence only. A-Conductor's deterministic verification/review policy determines whether runtime completion criteria are satisfied.

## 7. State authority and consistency

- A-Wiki is durable authority for knowledge, policy, decisions, procedures, orchestration conventions, and cross-project context.
- A-Conductor is durable authority for live execution state: tasks, workers, process ownership, runtime checkpoints, retries, recovery, evidence, and operator-visible runtime status.
- Project repository Git state remains authority for actual project files/history.
- Secrets remain in approved secret/reference stores; neither repository should become a plaintext secret database.
- Chat/session context is transport, never authoritative project state.

When authorities conflict, do not reconcile silently. Surface `DECISION_REQUIRED`, `RECOVERY_NEEDED`, or a stale-policy condition as appropriate.

## 8. Cost and quota boundary

A-Wiki may own knowledge/policy about model capability, cost strategy, escalation rules, and preferred providers. A-Conductor operationalizes those policies using observable runtime facts.

A-Conductor should prefer deterministic/local/free/low-cost execution when sufficient and escalate to premium workers for hard reasoning/review when materially valuable. This objective reduces premium consumption; it must never bypass provider access controls, quotas, limits, or terms.

## 9. Companion-repository discovery

Both sides should expose a durable pointer to the other:

### A-Conductor side

This contract and `PROJECT-PLAN.md` identify A-Wiki as the companion brain/policy repository.

### A-Wiki side

A-Wiki should receive a companion-project entity/pointer describing:
- repo/product name: `A-Wiki-Conductor` / `A-Conductor`;
- relationship: sibling Git repository;
- role: work-class durable execution/control plane;
- North Star;
- responsibility split;
- authoritative integration contract path in A-Conductor;
- current phase/status and handoff/work-order entry points;
- explicit `DO NOT DUPLICATE` capabilities owned by A-Conductor.

The prepared payload is in `docs/contracts/a-wiki-companion-registration-payload.md`.

## 10. Worktree and submodule rule

- A-Conductor must not be converted into an A-Wiki worktree without a new architecture decision.
- Git submodule coupling is not required for the initial integration and should not be introduced merely for discovery.
- Use sibling-repository pointers + versioned contracts + work-order/claim/handoff integration first.

## 11. Completion rule for cross-repo changes

A cross-repo capability is not considered coordinated merely because one repository changed.

For architecture changes affecting both sides:
1. update the owner repository contract/decision;
2. update companion pointer/registration when appropriate;
3. record compatibility/version impact;
4. preserve resumable handoff;
5. verify no conflicting active work/claim;
6. return evidence to both continuity systems when tooling/authority permits.

If one repository cannot be mutated in the current execution surface, prepare an explicit registration/apply payload and mark that step pending rather than claiming cross-repo completion.

## 12. Current classification

Current A-Conductor direction relative to A-Wiki:

- A-Wiki work orders/claims/handoff/memory conventions: `REUSE/WRAP`.
- A-Wiki orchestration intelligence and cost policy: `REUSE/WRAP`, later adapter work.
- A-Conductor worker/process/runtime supervision: `NEW` and A-Conductor-owned.
- A-Conductor native filesystem/shell/Git/test/build engine: `NEW` execution layer, constrained by A-Wiki policy.
- A-Conductor durable task/checkpoint/recovery implementation: `EXTEND` A-Wiki coordination semantics into runtime state; it must not become an incompatible second planning/work-order universe.
- Discord/Desktop operator surfaces: `NEW`, A-Conductor-owned.

This contract is the boundary guard for all future roadmap work.