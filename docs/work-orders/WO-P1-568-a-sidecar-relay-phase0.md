# WO-P1-568 — A-Sidecar + A-Relay Phase 0

Status: ACTIVE / R2 / CLAIMED / IMPLEMENTED_PENDING_VERIFICATION
Issue: #568
Claim: `WO-P1-568-ASIDECAR-MAC-001`
Repository: `aase7en/A-Wiki-Conductor` (`CONTROL_PLANE_ONLY`)
Base: `c72bf7e1ffdb4f347db54bfe02bf709e2ad89539`
Branch: `feat/wo-p1-568-a-sidecar-relay`
Worktree: `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo568-a-sidecar-relay`

## Goal

Author Phase 0 of the A-Sidecar/A-Relay capability as a docs/skill-contract
slice: an explicitly-invoked ChatGPT ordinary-chat companion skill for an
existing A-Conductor/Codex execution, plus the typed durable cross-surface
event contract it emits. The skill recovers truth from live durable evidence
(never prior-chat dependence), inspects the Codex lane read-only through
supported Desktop-managed App Server/native queue APIs, performs only
non-conflicting companion work unless an exact canonical claim and
non-overlap gate admit mutation, and rolls over bounded sessions through
`HARVEST -> VERIFY -> SIDECAR_CHECKPOINT -> NEXT_READY`. The relay contract
defines eleven initial event families, a minimum envelope, and
idempotency/replay/ack semantics suitable for a future runtime without
creating a second queue authority.

## Authority and failure model

- Risk is R2: new binding skill/contract projections that steer routing
  behavior, with no source/runtime mutation. Escalate to R3 only if a
  successor touches router skills, hooks, or runtime code.
- GPT integrator frames the trust boundary and owns final acceptance/merge.
  A-Sidecar/A-Relay grant no scheduler, task, claim, WIP, review, merge, or
  completion authority.
- Failure mode guarded: a second chat becoming a duplicate mutation owner, or
  a relay becoming a second queue/control-plane authority. Both are
  structurally forbidden by the skill's mutation gate and the contract's
  non-authority invariant.
- Missing capability (Codex App Server/queue surface unavailable) fails closed
  as a typed `SURFACE_UNAVAILABLE` blocker with degraded Git/WO evidence; it
  never justifies raw SQLite/session/lock access.

## Exact claimed file scope (NEW files only)

1. `.agents/skills/a-sidecar/SKILL.md`
2. `.agents/skills/a-sidecar/agents/openai.yaml`
3. `docs/contracts/a-sidecar-relay-v1.md`
4. `docs/work-orders/WO-P1-568-a-sidecar-relay-phase0.md` (this file)

## Non-goals / explicitly forbidden

- No modification of any existing tracked or untracked file. In particular:
  no A-FastTask/A-Faster/A-Audit/A-NightShift changes, no hooks, no `src/`,
  no tests, no `CURRENT-WORK.md`/`handoff.md`/COLLAB edits.
- No A-Wiki repository or SunDayRemoteMCP mutation.
- No relay runtime, carrier implementation, schema file, hook, scheduler,
  queue service, or second task/claim/WIP/review/completion authority.
- No implicit skill activation: `openai.yaml` pins
  `allow_implicit_invocation: false`.
- No secret-like material in any of the four files.

## Non-overlap

- Issue #498 owns `CURRENT-WORK.md`, `handoff.md`, and the shared executable
  PRE_DISPATCH/guard wiring surface; this claim touches none of those paths.
- No other open claim covers `.agents/skills/a-sidecar/**` or
  `docs/contracts/a-sidecar-relay-v1.md`; the four paths above are wholly new,
  so hotspot overlap with any active mutable lane is empty by construction.
  Re-verify with the A-FastTask collision gate if HEAD or claims drift.

## GLM-first authoring route

- `GLM_OFFLOAD_ASSESSMENT: DISPATCHED` — this lane is itself the GLM offload:
  the heavy authoring labor for all four files was executed by GLM-5.3 under
  the durable WO-P1-568 task packet (one pointer command, no bespoke relay).
- Durable execution evidence: this work order, the four-file diff/commit on
  the exact branch/base above, and the verification outputs below.
- A fresh accepted CoinTH quota preflight was satisfied by the dispatching
  integrator immediately before this material dispatch; no readiness smoke was
  run and no work was manufactured to occupy quota.

## Acceptance criteria

1. All four files exist, are strict UTF-8 (LF, no trailing whitespace), and
   contain only the authorized content; the diff touches exactly the four
   claimed paths.
2. `.agents/skills/a-sidecar/SKILL.md` carries valid frontmatter
   (`name: a-sidecar`, single-line description), documents: explicit
   invocation clauses; companion-not-owner boundary; the three identity
   axioms (`NEW CHAT != NEW TASK`, `CHAT LOSS != WORK LOSS`,
   `CONTEXT WINDOW != PROJECT MEMORY`); durable-evidence recovery; the
   bounded-session rollover loop; read-only Codex inspection; permitted
   companion work; the four-condition mutation gate including never
   duplicating the Codex mutation owner; IDLE/WATCH semantics; the GLM-first
   quota projection; and the authority floor.
3. `docs/contracts/a-sidecar-relay-v1.md` defines all eleven initial event
   families, the minimum envelope (EVENT_ID, EVENT_TYPE, SOURCE_SURFACE,
   SOURCE_THREAD_ID, SOURCE_TURN_ID, TASK_ID/CLAIM_ID and
   REPO/WORKTREE/HEAD_SHA when applicable, REQUESTED_CAPABILITY, PRIORITY,
   EVIDENCE_REFS, CREATED_AT), idempotency/replay/ack semantics with the
   no-second-queue-authority constraint, and the Codex bridge constraints
   (supported App Server/native queue only; no raw SQLite/lock access;
   Mac/Windows UTF-8; device/path and durable-first-turn handling; workspace
   context grants no mutation authority).
4. `openai.yaml` parses as YAML, uses only the official `interface`/`policy`
   shape, aligns the default prompt with recovery/non-conflicting work, and
   sets `allow_implicit_invocation: false`.
5. This work order records task/claim/base/scope/non-goals, carries exactly
   one `Issue: #568` identity line, and satisfies the work-order identity
   guard.
6. `git diff --check` passes; no secret-like material; no forbidden path
   changed.

## Review requirements

- One independent exact-SHA review (R2) by a lane that did not author these
  files, bound to the frozen candidate SHA, plus exact-head hosted CI before
  GPT acceptance/merge. No push, PR, or merge from the authoring lane.

## Verification (author lane, 2026-09-30)

- Entry gate: pwd/root/branch/HEAD/clean verified before mutation
  (`feat/wo-p1-568-a-sidecar-relay` at base
  `c72bf7e1ffdb4f347db54bfe02bf709e2ad89539`, clean tree).
- `git status --porcelain` after authoring shows exactly the four new paths.
- Frontmatter/structure sanity and YAML parse of `openai.yaml`: PASS.
- Strict UTF-8 decode + no CRLF/no trailing whitespace on all four files:
  PASS. `git diff --check`: PASS.
- Secret scan of the four files: no matches.
- Work-order identity: exactly one `Issue: #568` line, filename token `568`
  unused elsewhere in the corpus.
- No automated product tests apply (no source changed).

## Checkpoint log (append-only)

- [2026-09-30] GLM authoring lane (claim `WO-P1-568-ASIDECAR-MAC-001`):
  entry gate verified, canonical entry/protocol files read
  (`00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`, `AGENTS.md`, A-FastTask/
  A-Faster/A-Audit/A-NightShift skills, FAST_EXECUTION_PROTOCOL, Codex
  resume-adapter contract, work-order identity guard), four files authored
  within scope, verification above run. Remaining: commit the four-file
  candidate, independent exact-SHA review, exact-head CI, GPT
  acceptance/merge.
