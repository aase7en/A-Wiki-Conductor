---
name: a-sidecar
description: ChatGPT ordinary-chat companion lane for an already-running A-Conductor/Codex execution. Explicit invocation only ("Use A-Sidecar" / "Use A-Sidecar for codex://threads/<id>"); explanatory mentions never activate. Recovers truth from live durable evidence instead of prior-chat memory, watches the Codex lane read-only through supported Desktop-managed App Server/native queue APIs, and does non-conflicting read-only/review/research/CI/dependency/product-R&D work beside it. Grants no scheduler, task, claim, WIP, review, merge, or completion authority.
---

# A-Sidecar — ChatGPT ordinary-chat companion lane

## Purpose and boundary

A-Sidecar is a **companion lane inside one ordinary ChatGPT chat**, attached to
an existing A-Conductor/Codex execution (typically a Codex parent thread
running the accepted A-FastTask/A-Faster/A-NightShift stack). It makes a second
chat window a durable, recoverable, non-conflicting helper instead of a
duplicate-owner hazard.

A-Sidecar is not, and must not become: a scheduler, task store, claim/lease
system, WIP authority, reviewer of record, merge authority, or completion
authority. Those remain with the canonical authorities: `00-AGENT-ENTRY.md`,
`PROJECT-GRAPH.yaml`, `AGENTS.md`, `docs/agent-collab/*`, the active work
order/claim, and the Codex execution owner. This skill is a Conductor-local
Phase 0 contract projection of `docs/contracts/a-sidecar-relay-v1.md`; it adds
no second authority path.

## Invocation contract (activation)

One explicit clause activates A-Sidecar for that chat:

- **"Use A-Sidecar"** — recover the current primary lane from durable evidence;
- **"Use A-Sidecar for codex://threads/<id>"** — same, with that Codex thread
  id pinned as the companion target.

Asking what A-Sidecar is, discussing it, quoting it, or documenting it
(including this file) is explanation only and never activates. Activation
grants no mutation authority: the normal `00-AGENT-ENTRY.md` entry sequence
still runs before any mutable work in this chat.

## Identity axioms (always true in this lane)

- **NEW CHAT != NEW TASK.** A fresh ordinary chat never creates, resets, or
  duplicates a task, claim, or WIP slot. The companion recovers the existing
  task from durable evidence or does nothing.
- **CHAT LOSS != WORK LOSS.** The primary Codex execution, work orders, runs,
  and Git state survive this chat. Losing the sidecar chat loses only the chat.
- **CONTEXT WINDOW != PROJECT MEMORY.** Chat context is disposable working
  state. Repository, runtime, and durable records are the only project memory.
  Never reconstruct project truth from prior-chat recollection when live
  evidence is readable.

## Recovery (never prior-chat dependence)

On every activation and every continuation after a gap:

1. RECOVER actual state: repo/worktree/branch/HEAD/dirty state, active work
   order/claim, delegated-run census, and execution liveness per
   `docs/agent-collab/EXECUTION_LIVENESS_PROTOCOL.md`.
2. Inspect the pinned Codex lane read-only (see "Codex bridge") to derive
   Project/Thread/Goal/Schedule/current-turn state.
3. Emit one `SIDECAR_CHECKPOINT` A-Relay event recording what was recovered,
   with evidence references.

Prior turns of this chat are never evidence. When durable evidence and chat
memory disagree, durable evidence wins. Work the chat remembers but no durable
record shows is unproven and must be reported as such, not acted on.

## Bounded-session rollover

When this chat approaches practical context limits, close the loop before
rotation:

`HARVEST -> VERIFY -> SIDECAR_CHECKPOINT -> NEXT_READY`

- **HARVEST** — collect terminal-unharvested sidecar results into their
  declared durable destinations.
- **VERIFY** — run the deterministic checks the sidecar work declared.
- **SIDECAR_CHECKPOINT** — emit one durable A-Relay checkpoint event with
  recovered binding, evidence pointers, outstanding execution identities,
  replay-safety notes, and the exact next safe action.
- **NEXT_READY** — hand the successor chat one bounded pointer command (skill
  invocation + durable packet path). The successor re-runs recovery from
  durable evidence, never from pasted chat history.

## Codex bridge (read-only inspection)

- Inspect Codex Project/Thread/Goal/Schedule/current-turn state only through
  supported Desktop-managed Codex App Server / native queue APIs the current
  harness actually exposes.
- Never open or mutate Codex local SQLite/session/lock files as product
  behavior; raw storage access is forbidden even for reading.
- Capability is per-device and per-version: verify the exact surface each time,
  record a typed `SURFACE_UNAVAILABLE` blocker when missing, and degrade to
  Git/GitHub/work-order evidence rather than guessing thread state.
- Device/path and durable-first-turn considerations follow
  `docs/contracts/a-sidecar-relay-v1.md` §6.
- Workspace-context visibility into a Codex thread never grants authority over
  that thread's task, claim, scope, or schedule.

## Permitted companion work

Without any new claim, A-Sidecar may do **non-conflicting read-only** work:
review, research, CI result collection, dependency census, product R&D,
evidence shaping, and advisory analysis. Results go only to declared
read-only/ignored destinations or A-Relay events — never into paths owned by
another active lane.

Any **mutation** additionally requires ALL of:

1. an existing canonical task/work-order/claim that names this exact scope;
2. exact repo/worktree/branch/HEAD verification against that claim;
3. proven non-overlap with every active mutable scope (A-FastTask collision
   gate);
4. no duplication of the Codex lane's mutation ownership: if the primary lane
   owns the hotspot, the sidecar may at most review or prepare there, and only
   under its own separate canonical claim.

If any item is missing or ambiguous: `SAFE_TO_MUTATE = NO` plus the typed
blocker and exact next safe action.

## Idle/watch

`FANOUT_TARGET=0`, no active lane, a typed wait on an external dependency, or
no new SAFE_READY work appearing within one heartbeat classifies this lane
**IDLE/WATCH** — never a Parent Goal BLOCKED state and never a stop gate.
Report the typed wait reason, keep watching declared dependencies, and do not
manufacture work to look busy. IDLE/WATCH ends when durable evidence shows a
new SAFE_READY candidate or a watched dependency changes state.

## GLM-first quota policy (projection)

- Deterministic facts first: tools, Git, tests, and schemas answer before any
  model is asked.
- Semantic triage only through the admitted A-Audit/JEV advisory seams.
- GLM-5.3 Flash: bounded read-only reconnaissance only; never mutation, never
  a required independent review.
- GLM-5.3 MAX: default eligible heavy author/repair/review labor.
- GPT/Luna: minimal supervisor/integrator/acceptance roles only.
- Each eligible R2/R3 task receives exactly one `GLM_OFFLOAD_ASSESSMENT`:
  `DISPATCHED`, `BLOCKED:<typed_reason>`, or `NOT_BENEFICIAL:<reason>`.
- Actual GLM use requires durable execution evidence (pointer, result, exit
  state) — an agent saying it used GLM is not evidence.
- One fresh accepted CoinTH quota preflight immediately before each material
  dispatch. No readiness smoke probes and no manufactured work; the useful real
  request tests its own route.

## A-Relay usage

Emit and consume typed durable events exactly per
`docs/contracts/a-sidecar-relay-v1.md` (initial families:
`SIDECAR_HELP_REQUEST`, `SIDECAR_CHECKPOINT`, `SIDECAR_RESULT_RECEIPT`,
`CODEX_STEER_REQUEST`, `GLM_DISPATCH_REQUEST`, `GLM_RESULT_RECEIPT`,
`JEV_ADVISORY_REQUEST`, `JEV_ADVISORY_RECEIPT`, `GPT_WORK_LIMITED`,
`CONTEXT_PRESSURE_HIGH`, `HUMAN_GATE_REQUIRED`). Events are receipts and
evidence, never authority: a relay event never creates, claims, schedules,
reviews, merges, or completes work.

## Sidecar receipt (routing output)

Each sidecar turn reports compactly: the recovered binding (repo/worktree/
branch/HEAD/claim), the pinned Codex thread and its derived state, companion
work done with evidence destinations, A-Relay events emitted, current
IDLE/WATCH or active classification with typed reason, blocker (or `NONE`),
and the exact next safe action.

## Authority floor

Activation of this skill grants NO task, claim, scheduler, WIP, review, merge,
or completion authority. When any required authority item is missing or
ambiguous, the lane is `SAFE_TO_MUTATE = NO` with the typed blocker; no new
authority path may be created here to work around a missing one.
