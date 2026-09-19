# WO-P1-245 — A-FastTask repo-scoped session router (docs/skill only)

Status: PREPARED - repair-1 + Sol continuation-semantics repair recomposed onto current main; pending pre-freeze checks and independent exact-SHA review
Risk: R2 — binding governance/session-routing policy, docs-only
Owner/Integrator: GPT-5.6 Sol
Writer: GLM-5.3 MAX (bounded original lane); current-main recomposition: GPT-5.6 Sol integrator
Repository: `aase7en/A-Wiki-Conductor`
Base: `main@83db3be4248a02546a4d31b9c3dc9b33958bd957` (fresh current-main worktree; exact seven-path main-delta from original base was empty)
Branch: `docs/wo-p1-245-a-fasttask-current-main`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo245-a-fasttask-current-main`
Driving durable authority: GitHub Issue #327 comments (Astra Phase-A 7-file design; Sol current-main claim), 2026-09-16.

## Goal

Implement A-FastTask as a tiny repo-scoped progressive-disclosure router/binder
under the verified official OpenAI repo-local skills mechanism (Sol,
2026-09-16): skills live under `$REPO_ROOT/.agents/skills`; `SKILL.md` requires
`name` + `description`; references are progressive-disclosed after selection;
`agents/openai.yaml` may set UI metadata and invocation policy; implicit
selection matches the description and defaults true.

A-FastTask routes a session to EXISTING authorities. It MUST NOT become a
scheduler, task store, claim/lease system, reviewer, handoff SSoT, completion
state machine, daemon, background cleanup queue, or source/runtime adapter.

## Scope

Allowed tracked paths (exactly these seven; nothing else):

1. `PROJECT-GRAPH.yaml` — minimal extension of the existing
   `fast_path_tool_routing` trigger/read list to point at A-FastTask; no
   second graph lifecycle.
2. `.agents/skills/a-fasttask/SKILL.md` — short router only.
3. `.agents/skills/a-fasttask/agents/openai.yaml` — UI metadata, default
   prompt, `policy.allow_implicit_invocation: true`; no fake dependencies.
4. `.agents/skills/a-fasttask/references/conductor.md`
5. `.agents/skills/a-fasttask/references/material-boundary.md`
6. `.agents/skills/a-fasttask/references/closeout.md`
7. `docs/work-orders/WO-P1-245-a-fasttask.md` (this file)

Writer result goes only to ignored `runs/WO-P1-245/result.md`.

Forbidden: every other tracked path — especially `src/**`, `tests/**`,
`CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, root checkout, A-Wiki,
provider/runtime/credentials, WO205/WO227/Browser Wake. No `.kilo/` plans,
worktrees, or extra tracked files. No commit/push/merge and no Issue/GitHub
mutation from the writer lane.

## Reuse audit (A-Wiki reuse-before-build gate)

Classification: WRAP — wrap and bind existing authorities; add no new authority
path, store, or lifecycle.

Reused as-is, by reference only:

- Entry/lifecycle: `00-AGENT-ENTRY.md`, `PROJECT-GRAPH.yaml`, `AGENTS.md`
- Execution/risk/routing: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`,
  `TOOL_AND_FAST_PATH_ROUTING.md`, `CAPABILITY_MATRIX.md`,
  `EXECUTION_LIVENESS_PROTOCOL.md`, `COLLAB_PROTOCOL.md`
- Authority: existing WO/task packet + claim/lease + independent review + CI
  evidence chains, including the delivery gate sequence (exact reviewed head →
  CI run ID on that exact head → merge the expected-head only → post-main CI
  run ID → checkpoint recorded on the driving issue).

Overlap check: WO-P1-228's routing doc is pointed at, not modified. No open
WO205/WO227/Browser-Wave surface is touched; no source/runtime lane overlaps.

## Trigger / negative-trigger contract

Trigger (bind the skill): substantial repo/session routing; safe parallel-lane
fill/recycle; cross-executor continuation/takeover; temporary-lane closeout.

Negative trigger (bypass): trivial Q&A; a single obvious mechanical edit;
mid-lane execution of an already-claimed packet; work with no
executor/workflow/lane selection. `allow_implicit_invocation` stays `true`;
the sharply bounded `description` carries the negative-trigger burden.

Routing-loop output contract: record/return the existing task/claim reference,
the chosen existing workflow, the evidence destination, the current blocker
(typed code or NONE), `CLEANUP_STATE=NOT_NEEDED|PENDING|BLOCKED|COMPLETE`
(with exact path/reason/evidence when applicable), and the exact next action. The A-FastTask routing role
then ends, but the user-facing session continues immediately under that
existing workflow whenever this agent is the authorized selected
executor/integrator and a safe next micro-step exists. Stop only for a real
blocker/approval gate/terminal state or a route to a different execution
surface. Skill selection grants no mutation/transfer/cleanup/acceptance
authority.

## Takeover / cleanup contract (summary; detail in skill references)

- Takeover: fail-closed. Requires proof the old writer is inactive (OFFLINE is
  not INACTIVE; a still-executing child blocks takeover), exact
  repo/worktree/branch/HEAD/dirty recheck, pending-command inventory,
  claim/lease + overlap recheck, and serialization through the SAME existing
  claim authority; the old executor is read-only after transfer
  (`references/material-boundary.md`).
- Cleanup: explicit end-of-lane only. Requires accepted/reconciled/post-main
  evidence as applicable, durable preservation of material review/result
  evidence OUTSIDE the target worktree or on GitHub/tracked authority (an
  ignored result inside the target worktree is NOT durable), no live
  owner/process, full dirty+ignored+untracked inventory,
  unique-commit/evidence preservation (squash/rewrite-aware), exact path
  identity, then canonical `git worktree remove` WITHOUT force; any unknown =>
  `SAFE_TO_CLEANUP = NO`; branch deletion is a separate later decision
  (`references/closeout.md`).

## WIP behavior

Existing `PROJECT-GRAPH.yaml` `rules.default_wip` governs: 3 mutable lanes +
1 independent read-only review lane, spare capacity for recovery. WIP full =>
no new mutable lane; the router returns the blocker, live-lane inventory, and
exact next safe action instead.

## Scenario / adversarial matrix

| # | Scenario | Expected behavior |
|---|---|---|
| 1 | Normal Sol+GLM delivery | Sol routes via entry/classify/claim; router records task/claim ref + workflow + destination + blocker + next action, then its routing role ends; the authorized session continues immediately under the selected existing workflow, with GLM executing the bounded lane and evidence going to the declared `runs/` destination |
| 2 | SundayWorker NOT_EXPOSED | Classify the failure code; fall back to the next eligible existing route (GLM lane or native tools); never wait on an unexposed Worker |
| 3 | Codex/Astra rate-limit/transport stop | NO immediate takeover; Sol takes over only after inactivity proof (terminal session AND no executing child); otherwise checkpoint and hold |
| 4 | Dirty merged lane cleanup | `SAFE_TO_CLEANUP = NO`; dirty state explained/preserved by its owner first; force removal forbidden |
| 5 | Detached clean reviewer worktree | Cleanup eligible ONLY after review/result evidence is durably checkpointed outside the target worktree or folded to GitHub/tracked authority; an ignored result inside the target is NOT durable |
| 6 | Child process still executing / executor offline with unknown children | NO takeover and NO cleanup; recover via the liveness protocol; fail closed |
| 7 | Squash/rewritten merge | Lane commits are not ancestors of main; preserve the unique evidence (verify in the squashed diff or copy to a durable destination outside the target worktree) BEFORE worktree removal |
| 8 | Trivial task | Skill bypassed via negative trigger; no claim ceremony invented |
| 9 | WIP full (3 mutable + 1 review in use) | No new mutable lane; typed blocker + live-lane inventory + exact next action returned |

## R2 verification / acceptance

- Changed set is exactly the seven allowed tracked paths.
- YAML parses: `PROJECT-GRAPH.yaml`, `.agents/skills/a-fasttask/agents/openai.yaml`,
  and the `SKILL.md` frontmatter block.
- No unresolved placeholders; no secret-like content; `git diff --check` clean.
- Skill stays router-only: no scheduler/store/claim/reviewer/SSoT/state-machine/
  daemon/queue/adapter semantics in any new file.
- R2 sequence before any merge (Sol is integrator/adjudicator, NOT the
  independent reviewer): Sol pre-freeze integration/adversarial review →
  deterministic checks → freeze exact candidate SHA → qualified independent
  read-only exact-SHA reviewer distinct from author/integrator → exact-head
  hosted CI → Sol adjudication → expected-head merge → post-main
  verification/checkpoint. The writer lane performs no merge.

## No-second-authority constraints

A-FastTask files may only reference or point to existing authorities. On any
conflict, `00-AGENT-ENTRY.md`, `AGENTS.md`, `PROJECT-GRAPH.yaml`, and
`docs/agent-collab/*` win. Skill selection grants no mutation, transfer,
cleanup, or acceptance authority, and no A-FastTask file may define a new
authority path to work around a missing one.

## Checkpoint

Original GLM writer lane produced the seven-file repair on branch `docs/wo-p1-245-a-fasttask` at base `5267ef94b0b23a631bdbb740bfd67d629aae85f4`; it remains preserved and uncommitted. Sol re-pinned `main@83db3be4248a02546a4d31b9c3dc9b33958bd957`, proved that main changed none of the seven claimed WO245 paths, created fresh branch `docs/wo-p1-245-a-fasttask-current-main`, and recomposed the exact repaired bytes there. Only this WO metadata/checkpoint was then updated inside the already-claimed seven-file scope to name the current base/branch/worktree.
Repair-1 batch (2026-09-16) applied to the four Sol P1 findings from Issue
#327: (1) `agents/openai.yaml` conformed to the official interface/policy
metadata shape; (2) `references/material-boundary.md` now preserves
coordination single-writer authority (lane writes only its declared
result/evidence destination; Sol/integrator or an explicitly assigned executor
folds accepted state into WO/`CURRENT-WORK.md`/`handoff.md`); (3)
`references/closeout.md` now requires material review/result evidence outside
the target worktree or on GitHub/tracked authority before worktree removal
(an ignored result inside the target is NOT durable); (4) this WO now records
the correct R2 sequence with an independent exact-SHA reviewer distinct from
author/integrator. Checks and self-audit in `runs/WO-P1-245/result.md` with
sentinel `A_FASTTASK_GLM=READY_FOR_SOL_REREVIEW`.

Sol current-main pre-freeze review then found one additional P1 continuation
semantic defect: literal `RETURN, then EXIT` would stop the current Codex
session after routing. The bounded repair keeps A-FastTask router-only but ends
only its routing role; when the current agent is the authorized selected
executor/integrator and a safe next micro-step exists, control immediately
continues under the chosen existing workflow. A real blocker/approval gate,
terminal state, or handoff to another execution surface remains a valid stop.

Next safe action: Sol runs pre-freeze integration/adversarial review of the
exact seven-file head, runs the deterministic checks, freezes the exact
candidate SHA, dispatches a qualified independent read-only exact-SHA reviewer
distinct from author/integrator, obtains exact-head hosted CI, adjudicates,
then owns the expected-head merge decision and post-main verification/checkpoint
through the standard delivery gates.
