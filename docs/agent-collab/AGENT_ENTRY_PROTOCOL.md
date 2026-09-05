# Universal Agent Entry Protocol

Status: CANDIDATE / BINDING AFTER WO157 ACCEPTANCE
Introduced by: WO-P1-157
Purpose: make every execution surface start from the same durable state with minimum ceremony.

## 1. Mandatory startup core

For any non-trivial work:

1. `00-AGENT-ENTRY.md`
2. `PROJECT-GRAPH.yaml`
3. `AGENTS.md`
4. actual repo/worktree/remote/branch/HEAD/dirty/claim state
5. `CURRENT-WORK.md`
6. active `docs/work-orders/<id>.md` when one exists or has already been claimed
7. `handoff.md` only for resume/transfer work, unclear continuity, or when `CURRENT-WORK.md` points to it for material context
8. task-relevant nodes selected by `PROJECT-GRAPH.yaml`
9. `DEFECT_LESSONS.md` before `src/a_conductor/` mutation

Do not require `PROJECT-PLAN.md` and `DESIGN.md` for every task. Read them when the project graph says the task touches architecture/roadmap or UI/UX. This preserves context quality while reducing repeated startup cost.

If a new task has no work order yet, product/source mutation is blocked, but a bounded docs-only governance bootstrap may create the initial WO/claim in a clean isolated scope. Re-run the full mutation gate immediately after bootstrap. The bootstrap exception never grants product/source/runtime mutation authority.

## 2. Authority and state truth

Safety, legal/user authority, and binding repository policy constrain all actions. Actual Git/runtime/process/DB evidence determines what state really exists inside those constraints; it never overrides them.

When state-bearing sources disagree, use this truth order:

1. actual Git/runtime/process/DB evidence
2. active claim/lease and exact work order
3. `CURRENT-WORK.md`
4. `handoff.md` when applicable to the active resume/transfer context
5. chat/session memory

Chat memory is never state authority.

## 3. Default routing model

### GPT / integrator

Owns architecture/trust boundaries, dependency graph/risk tier, work-order/claim boundaries, cross-lane conflict/SSoT, acceptance criteria, final defect adjudication, merge, release, and live acceptance.

GPT should not spend premium reasoning on repetitive implementation/test/refactor mechanics when a bounded execution lane can do them safely.

### Capability-selected implementation executor

Select the executor by task class, risk, capability, readiness, authorization, cost, availability, ownership, and result-destination gates using `CAPABILITY_MATRIX.md`.

GLM/ZCode is the current preferred candidate for bounded READY implementation when those gates pass; it is not a permanent architectural dependency.

The selected executor may continue `implement -> targeted test -> debug -> repair -> retest` until the contract is satisfied or a real blocker/stop condition is reached.

No implementation model self-grants broader scope, merge authority, secret access, destructive authority, retry after ambiguous execution, or acceptance authority.

### Deterministic/native tools

Preferred for tests, builds, hashes, schema checks, static checks, exact Git/process/file identity, and CI/release evidence.

## 4. Risk-tier routing

- R0: direct bounded docs/admin work is usually cheapest on the current integrator/tool surface.
- R1: use the cheapest capable authorized executor; GPT performs lightweight final acceptance.
- R2: GPT defines contract/architecture boundaries -> capability-selected executor implements -> independent exact-SHA review -> GPT accepts.
- R3: GPT defines authority/failure model before mutation -> capability-selected bounded implementation -> adversarial/deterministic evidence -> strongest independent review -> GPT final acceptance/release.

A model name never lowers the risk tier.

## 5. Task packet instead of bespoke prompt

A durable WO/task packet is the prompt contract. It must contain Task ID/goal, repository/worktree/branch/base HEAD, owner, allowed/forbidden scope, acceptance criteria, required verification, risk tier, stop conditions, and result/evidence destination.

When this exists, GPT should send only a short pointer command rather than regenerate the whole contract in chat.

## 6. Relay modes

### Current safe fallback

Human relays once:
`Read <task-packet>. Execute only that claimed lane with your supported goal/skills loop. Write result/evidence to <result-destination>. Do not merge.`

The integrator reads the result destination directly.

### Zero-Relay after R3 acceptance

A-Conductor automatically sends the same task packet, ingests the result, verifies it, and dispatches at most the bounded repair/continue steps allowed by policy.

Zero-Relay removes transport latency only. It must not weaken provider, claim, secret, replay, review, or acceptance gates.

## 7. No-progress and stop conditions

Continue automatically across safe micro-steps. Stop and checkpoint only when ownership/claim/dirty state becomes ambiguous; authorization/secret/destructive approval is required; execution outcome is UNKNOWN and replay would be unsafe; the same material failure repeats without new evidence; scope would expand outside the WO; an R2/R3 frozen candidate is ready for independent review; or acceptance is complete.

## 8. Handoff

Before ownership/session transfer persist task/status, repo/worktree/branch/HEAD, dirty state, completed evidence, blockers/decisions, current owner/claim, and exact next safe action.

A fresh agent with no chat history must be able to resume from the mandatory startup core plus the conditional handoff context when applicable.
