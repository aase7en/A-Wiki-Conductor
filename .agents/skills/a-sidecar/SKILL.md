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

### Orchestration-mode activation

Activation clauses are case-insensitive, and the obvious in-project typo
"A-Sidebar" resolves to this same skill. Activation also engages the
orchestration-mode projection in this skill: the chat becomes a typed
orchestration and cross-surface handoff surface for the already-running
execution stack. Orchestration mode grants no new authority; the authority
floor at the end of this skill still applies in full.

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

## Desktop binding and successor-thread migration

A durable Codex thread existing on disk, or being readable from a separately
spawned App Server, is **not** proof that Codex Desktop has loaded that thread
into its conversation runtime. Treat Desktop binding as a separate recovery
gate whenever a Goal/Schedule is migrated to a successor thread.

Recognized failure signature:

- Goal/thread records exist and a standalone App Server can read them;
- Schedule configuration is `ACTIVE` and points at the intended thread id;
- the target rollout does not advance as expected; and
- Codex Desktop logs report
  `Conversation state not found conversationId=<thread-id>`.

Supported recovery:

1. Do not edit Codex SQLite/session/thread-writer-lock files and do not steal or
   delete locks.
2. Do not broad-kill or restart ChatGPT/Codex merely to force ownership.
3. Open the durable target through the Codex Desktop user-facing deep link
   `codex://threads/<thread-id>` so the Desktop-managed backend can resume/load
   the thread.
4. Verify the writer lock is held by the actual Desktop-managed App Server
   process, not by a temporary standalone App Server.
5. Verify the rollout advances and the intended model/reasoning settings remain
   applied after Desktop resume.
6. Verify the Goal state and Schedule target/cadence from their durable owners.

A migration is not end-to-end accepted from config state alone. After the
current turn reaches a safe idle boundary, observe one real scheduled
heartbeat/continuation on the new Desktop-loaded thread before declaring the
Schedule proven. Never trigger a duplicate wake while a mutation is
`RUNNING`, `UNKNOWN`, `AMBIGUOUS`, or `TERMINAL_UNHARVESTED`.

Keep these distinctions explicit:

`THREAD_DURABLE != DESKTOP_LOADED != SCHEDULE_PROVEN`

A separately spawned App Server is a supported protocol surface for compatible
operations, but its existence never proves Desktop UI/runtime ownership. Native
queue cross-writer behavior is likewise valid only for a thread whose current
writer/runtime identity has been recovered and verified.

Writer continuity (successor-parent migration):

- Never raw-edit Codex SQLite/session/lock files, never steal or delete
  writer locks, never broad-kill or restart ChatGPT/Codex to force ownership,
  and never run a duplicate writer against a lane another runtime owns.
- Supported successor migration happens only at a proven safe idle with no
  active mutation: create exactly one Luna LOW successor, bind the same
  durable Goal and current skills, prove a recovery-only first turn
  (`SUCCESSOR_RECOVERY_READY`) before activation, and pause/tombstone the
  old Goal. The watchdog stays a separate goal.
- Never reset, clean, or stash unknown work.

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

## Orchestration-mode supervision contract (projection)

When orchestration mode is active, this lane projects — never replaces — the
accepted supervision stack, and creates no parallel or shadow authority.

- **GPT-5.6 Sol in A-Conductor_Chat** is Architect / Conductor / Researcher /
  Prompt Designer / Integrator / Incident Recorder — not the default heavy
  implementation or review worker while a valid delegation route exists.
- **The persistent Codex Desktop/App-Server Parent Goal (GPT-6 Luna LOW)** is
  the low-traffic controller:
  `RECOVER -> RECONCILE -> HARVEST -> SAFE_READY -> delegate -> verify ->
  continue`.
- **Composition order:** compose A-FastTask first, then A-Audit. A-Faster
  owns existing-WIP/fanout/collision/auto-refill projection; A-NightShift
  owns unattended continuation and waits; A-Sidecar owns typed cross-surface
  handoff and continuity. Never create parallel or shadow authorities.
- **Parent loop until roadmap completion:** `RECOVER -> RECONCILE -> HARVEST
  -> NEXT_READY -> A-Audit -> DELEGATE -> VERIFY -> REVIEW/CI -> bounded
  REPAIR -> exact-authority MERGE/POST-MAIN -> refresh WIP -> NEXT_READY`.
  One blocked lane never blocks the parent.
- **Automation floor:** AI-safe decisions inside owned authority are
  automatic; humans are engaged only for genuine `HUMAN_DECISION_REQUIRED`,
  `HUMAN_ACTION_REQUIRED`, `AUTHORIZATION_REQUIRED`, `SAFETY_BLOCK`, or the
  terminal `TRUE_NO_SAFE_NEXT_ACTION`.
- **Watchdog:** a separate `WATCHDOG_ONLY` Luna LOW wake notifies the Parent
  only on a material durable delta, at a 30-minute cadence; an unchanged
  idle state is `DONT_NOTIFY`.

## Skill freshness and progressive disclosure

- A stale supervisor checkout must never hide current repo-local skills:
  resolve skills against live accepted `origin/main` (or a clean read-only
  snapshot at that commit) before declaring a skill missing.
- When the catalog reports "Exceeded skills context budget", explicitly
  attach the required skills instead of relying on auto-discovery.
- Progressive disclosure: load A-FastTask first and only the needed overlays;
  load A-NightShift only when wait/continuation semantics apply.

## GLM-first quota policy (projection)

- Deterministic facts first: tools, Git, tests, and schemas answer before any
  model is asked.
- Semantic triage only through the admitted A-Audit/JEV advisory seams.
- GLM-5.3-Flash MAX: bounded read-only reconnaissance only; never mutation,
  never a required independent review.
- GLM-5.3 MAX: default eligible heavy author/repair/review labor.
- GPT/Luna: minimal supervisor/integrator/acceptance roles only.
- Each eligible R2/R3 task receives exactly one `GLM_OFFLOAD_ASSESSMENT`:
  `DISPATCHED`, `BLOCKED:<typed_reason>`, or `NOT_BENEFICIAL:<reason>`.
- Actual GLM use requires durable execution evidence (pointer, result, exit
  state) — an agent saying it used GLM is not evidence.
- One fresh accepted CoinTH quota preflight immediately before each material
  dispatch. No readiness smoke probes and no manufactured work; the useful real
  request tests its own route.
- Offload eligibility is substantial R2/R3 only, after deterministic checks;
  GLM-5.3 MAX via KiloCLI/CoinTH is the preferred heavy executor for
  implementation/repair/review labor.
- GLM-5.3-Flash MAX is bounded to read-only reconnaissance, evidence shaping,
  and prechecks; JEV output is accepted advisory evidence only, never
  authority.
- The CoinTH preflight is fail-closed: no fresh pass means no GLM request,
  and no synthetic smoke may substitute for the real request.
- When `GLM_ROUTE_READY=true`, equivalent long Luna/Sol implementation is
  forbidden; a typed GLM block may fall back to an accepted alternate route;
  never blind-spin a blocked route.
- Never force GLM onto trivial deterministic work and never burn quota to
  fill lanes.
- Terminal FAILED/CANCELLED executions with no canonical binding or verified
  identity are non-acceptance evidence and are never replayed as success.

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

## Recorded corrections (binding semantics)

- SRM status `claimPresent=false` means the SRM completion done-claim
  artifact is missing — NOT that the A-Conductor project claim or WorkerLease
  is absent. Project/WO claim, WorkerLease/mutation admission, and SRM
  collection semantics are separate facts.
- Never fabricate a DEX `bindingDigest`/identity. When canonical
  `mode=mutate` admission is unavailable on a direct route, do not issue an
  unbound mutate; use read-only patch authoring and keep the output
  non-authoritative pending separate apply/verification.
- Exact full SHAs come from live Git only, never reconstructed from a prefix.
  Any new candidate SHA requires fresh hosted CI and an independent
  exact-SHA review before merge.

## Authority floor

Activation of this skill grants NO task, claim, scheduler, WIP, review, merge,
or completion authority. When any required authority item is missing or
ambiguous, the lane is `SAFE_TO_MUTATE = NO` with the typed blocker; no new
authority path may be created here to work around a missing one.
