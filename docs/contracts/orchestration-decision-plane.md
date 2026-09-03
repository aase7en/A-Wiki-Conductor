# Orchestration Decision Plane — Packet v1 Contract

Status: ODP-1 FEATURE-BRANCH IMPLEMENTATION / NOT YET ACCEPTED
Owner boundary: A-Wiki owns high-level orchestration/capability/model policy; A-Conductor owns runtime projection, graph state, execution eligibility, evidence, and safety enforcement.

## 1. Purpose

`orchestration-packet/v1` is the minimized read-only decision envelope passed from A-Conductor runtime state to a future planner/adjudicator.

It is **not**:
- a planner implementation;
- an execution request authority replacement;
- a provider admission decision;
- a scheduler/task-store replacement;
- a worker assignment;
- a review lifecycle;
- a credential/session container;
- a chat transcript.

The packet exists so a decision provider can reason over bounded, current facts without receiving unnecessary private/runtime data or direct mutation authority.

## 2. Build seam

Production seam:

`a_conductor.orchestration_packet.build_orchestration_packet(...)`

Inputs are already-observed/validated facts:
- existing `task-contract/v1` mapping;
- existing `TaskGraph` plus current runtime `node_states`;
- explicit `RepositoryFacts` produced by a repository/authority observer outside this module;
- `EligibleRouteCandidate` values that existing provider/worker policy has **already** deemed eligible;
- policy/evidence/blocker references;
- explicit parallelism/adjudication budgets.

The builder performs no I/O and makes no readiness/authorization/admission decision.

## 3. Packet shape

```text
orchestration-packet/v1
├─ task
│  ├─ task identity / goal / risk
│  ├─ mutation + human-approval booleans
│  ├─ safe target identity expectations
│  ├─ allowed/forbidden file scope + diff/file limits
│  ├─ acceptance criteria + review requirement
│  ├─ privacy/network/secret-access class
│  ├─ routing capability + safe surface traits
│  ├─ budget / retry / escalation
│  └─ required evidence classes
├─ graph
│  ├─ graph_id
│  ├─ node summaries
│  ├─ dependency edges
│  └─ ready_frontier
├─ repository
│  ├─ project/repository/worktree refs
│  ├─ branch/HEAD
│  ├─ dirty
│  ├─ identity_verified
│  └─ mutation_authorized
├─ eligible_candidates[]
│  ├─ candidate / role / provider / model identity
│  ├─ capabilities + surface traits
│  ├─ max_concurrency
│  ├─ cost/quota classification
│  └─ evidence refs
├─ policy_refs[]
├─ evidence_refs[]
├─ blockers[]
└─ limits
   ├─ max_parallelism
   └─ max_adjudication_rounds
```

Default `max_adjudication_rounds = 3`.

## 4. Task-contract allowlist

Only an explicit allowlist crosses this boundary.

Before projection, authority-bearing fields that cross the boundary are validated against the pinned `task-contract/v1` semantics (schema version, enums, booleans, bounds, required evidence, routing traits, and scope controls). ODP-1 is not a replacement JSON-Schema engine, but it must never project malformed control values as if they were valid authority.

Projected:
- `task_id`, `work_order_ref`, `task_type`, `goal`, `risk_class`;
- `authority.mutation_allowed`, `authority.human_approval_required`;
- target project/repository identity ref, expected branch/HEAD, identity policy;
- allowed/forbidden files and file/diff/scope-growth limits;
- acceptance criteria and review requirement/class;
- privacy class, network policy, secret-access boolean;
- routing required capabilities and allowlisted surface traits;
- elapsed/token/cost budgets;
- retry attempt/identical-failure/lease-expiry rules;
- escalation conditions;
- required evidence classes.

Not projected:
- requester/approver names or IDs;
- approval reference payloads;
- expected absolute worktree path from the task contract;
- allowed/forbidden command strings;
- verification command strings;
- network allowlist targets;
- arbitrary task `metadata`;
- provider endpoints/headers;
- credentials, keys, tokens, cookies, environment values;
- conversation/chat transcripts.

Nested `preferred_surface_traits` are also allowlisted; unknown nested fields are dropped instead of copied wholesale.

## 5. Graph truth

The packet does not calculate a second readiness policy.

`ready_frontier` is produced by existing `graph.ready.compute_ready_set()`.

Node summary status uses the same current-state default as that authority: absent runtime state means `TODO`. `TaskNode.model_requirement` is intentionally **not projected** because canonical ODP routing is capability/role-first rather than permanent vendor/model identity.

The builder never mutates the supplied graph or node-state mapping.

## 6. Candidate precondition

`EligibleRouteCandidate` means eligibility has already been proved elsewhere.

The type deliberately contains no independent `ready`, `authorized`, or `admitted` flags. ODP-1 must not recreate or override provider execution authority.

Future ODP routing must only construct candidates after the existing chain proves the route is eligible, conceptually:

`CAPABLE ∧ READY ∧ AUTHORIZED ∧ ADMITTED ∧ POLICY_OK`

Candidate identity is stable and duplicate candidate IDs fail closed. Candidate order is canonicalized by `candidate_id` so packet output does not depend on discovery order.

## 7. Safety invariants

- Module is side-effect free.
- Packet is JSON-safe before return.
- `RepositoryFacts.mutation_authorized=True` requires `identity_verified=True`.
- Parallelism/adjudication budgets are positive non-boolean integers.
- Malformed required task sections fail with typed `ValueError` rather than being silently omitted.
- Unknown graph node-state IDs fail closed.
- No provider/model is hard-coded by this contract.
- No hidden chain-of-thought is requested or stored.
- Packet references use field-specific semantic namespaces: repository identity uses `repo:` / `github:`, worktree identity uses `worktree:`, policy uses `policy:` / `awiki-policy:`, and evidence uses the declared evidence-reference namespace set. Raw paths, URL-like forms, environment/credential namespaces, credential-shaped payload prefixes, cross-field namespace substitution, and arbitrary free text are rejected before serialization.
- Packet evidence references are references, not raw secret-bearing evidence payloads.
- A packet is a decision input, never mutation authorization by itself.

## 8. Next ODP seams

Not implemented by ODP-1:
- ODP-2 decision-provider adapter;
- ODP-3 graph-proposal admission validator;
- ODP-4 capability-first candidate resolution/selection reasons;
- ODP-5 evidence/adjudication loop + no-progress budget;
- ODP-6 ReviewBus integration;
- ODP-7 operator observability;
- ODP-8 orchestration fault-injection E2E;
- ODP-9 real multi-provider pilot.

Each requires its own claim/work order and must reuse current A-Wiki/A-Conductor authorities rather than growing this projection module into a second orchestrator.
