---
name: a-faster
description: Accelerated multi-device / multi-harness profile for the canonical A-FastTask router/binder. Use for substantial A-Sunday Conductor work that benefits from coordinated Windows + macOS + GitHub lanes, Kilo/Claude Code GLM delegation, fast lane recycle, and safe merged-worktree cleanup. MUST load and obey ../a-fasttask/SKILL.md first. Adds routing constraints only; grants no task, claim, cleanup, provider, review, merge, or acceptance authority.
---

# A-Faster — accelerated A-FastTask profile

A-Faster is an **overlay on A-FastTask**, not a second control plane.

Before using this profile, read and obey:

`../a-fasttask/SKILL.md`

If the base skill is unavailable or conflicts with this file, fail closed as
`A_FASTTASK_BASE_MISSING_OR_CONFLICT`. The base skill owns generic recovery,
claim, risk, evidence, cleanup, and authority rules. A-Faster only adds
multi-device and multi-harness routing constraints.

## Trigger

Use A-Faster when one or more are true:

- the user explicitly asks for A-Faster / faster multilane execution;
- independent READY work can run concurrently on Windows and macOS;
- Kilo Code CLI and Claude Code CLI can safely own different bounded lanes;
- a finished lane should be recycled after exact closeout/cleanup proof;
- the task needs coordinated Workers + RDC + GitHub remote truth.

For ordinary substantial single-device work, A-FastTask remains sufficient.

## Global WIP and no-collision rule

The default budget remains **global across every device and harness**:

- max 3 mutable implementation lanes;
- max 1 independent read-only review lane;
- spare capacity for recovery/blocker investigation.

Never multiply WIP by device.

`1 MUTABLE HOTSPOT = 1 MUTATION OWNER`

Two devices may work in the same project only when each mutable lane has a
different claimed hotspot and normally a different worktree/branch. Never let
Windows and macOS mutate the same branch/worktree/hotspot concurrently.

Every A-Faster lane adds these fields to the normal A-FastTask binding:

- `DEVICE_ID` / verified hostname or connector device id;
- `HOST_OS`;
- `EXECUTION_SURFACE` (Worker, RDC, GitHub, Kilo, Claude Code, etc.);
- `HARNESS_ID`;
- `MODEL_ID` + effort/variant when a model is used;
- durable execution/result pointer for delegated work.

## Surface routing

### Windows

Prefer SunDay-Worker 1..5 for repo/file/code work after exact lane activation
and mutation gating. Workers are dynamic lanes, not permanent roles.

Kilo Code CLI and Claude Code CLI may execute delegated packets from isolated
Windows worktrees when their exact route is READY.

### macOS

Use Remote Desktop Commander (RDC) for exact Mac device discovery, shell,
filesystem, process, repo/worktree, test, and CLI operations when RDC is
actually exposed and online.

`RDC ONLINE != SAFE_TO_MUTATE`.

If RDC is not exposed, record `PLUGIN_NOT_EXPOSED_TO_CHAT`; do not pretend the
Mac lane ran, and do not reconstruct a missing Mac repo from chat memory.

### GitHub

Use the GitHub connector for remote Issue/PR/SHA/diff/CI/merge truth when the
connector is callable. If connector invocation is unavailable, record the typed
surface failure. A locally authenticated `gh` CLI may be used only as an
explicit fallback under the same repo/task authority and must not be described
as the connector.

## GLM multilane delegation

Kilo and Claude Code are **harnesses only**. They never grant mutation,
provider, review, or acceptance authority.

Before **every material GLM dispatch**:

1. recover outstanding delegated executions first;
2. verify exact repo/worktree/branch/HEAD/task/claim/scope;
3. refresh CoinTH quota/readiness through the approved secret-safe resolver;
4. prove the exact harness/model route;
5. create a durable execution pointer/result destination before or at launch.

Preferred routes:

- Kilo Code CLI: exact `cointh-glm/glm-5.3`, effort/variant `max`;
- Claude Code CLI: exact `glm-5.3` with `--effort max`, only after a live
  route probe proves that exact model is accepted.

Never silently fall back to another model/provider/harness. A failed Claude GLM
probe blocks only that route; Kilo or another already-authorized route may
continue independent work.

Run Kilo and Claude concurrently only on non-overlapping claimed scopes or as
read-only analysis/review lanes. Freeze exact candidate SHA(s) before review.

## Advisory skill layer

Advisory skills may shape work but never become authority.

### Ponytail

On Claude Code, prefer the installed `ponytail@ponytail` plugin when useful:

- `ponytail` before implementation to challenge unnecessary work;
- `ponytail-review` on a frozen candidate;
- `ponytail-audit` / `ponytail-debt` for bounded simplification analysis.

Do not let YAGNI advice override an accepted Work Order, safety gate, or
verification requirement.

### Caveman

Use the GitHub-sourced `caveman` skill only for transient delegated-agent
communication/token compression where meaning remains unambiguous.

Do **not** use Caveman compression for:

- persisted project docs, issues, PR bodies, commits, handoffs, or evidence;
- security warnings or irreversible-action confirmations;
- exact error text, commands, identifiers, numbers, units, or contract terms.

### Grill Me

When a real product/architecture decision remains ambiguous **after codebase and
authority inspection**, invoke `/grill-me plan` before inventing a decision.
Use `/grill-me check` when useful to challenge an implemented plan.

If Grill Me requires interactive user input that is unavailable, classify the
decision normally (`HUMAN_DECISION_REQUIRED`) rather than guessing. Do not use
Grill Me to ask the user for facts that tools/authority can recover.

## Cross-device handoff

A device handoff is a normal lane handoff, not a new task.

Before another device takes over:

1. checkpoint task/claim/scope/current SHA and delegated-run state;
2. preserve material evidence outside any worktree scheduled for cleanup;
3. push/fold through the accepted remote authority where that repo has one;
4. on the receiving device, re-pin actual repo/worktree/branch/HEAD and prove
   no mutable overlap before continuing.

No accepted remote/source on the receiving device means
`SOURCE_UNAVAILABLE / SAFE_TO_MUTATE=NO`.

## Lane recycle and cleanup

A-Faster reuses A-FastTask `references/closeout.md`. Cleanup is never implied
by model/Worker DONE or by a merged-looking branch.

A worktree/folder becomes cleanup-eligible only after all are proven:

- accepted/merged or explicitly abandoned by authority;
- material result/review evidence folded outside the target;
- no active claim/lease/process/editor/test/executor bound to it;
- tracked + untracked + ignored inventory accounted for;
- no unique work would be lost; accepted content is reachable/evidenced;
- exact registered path identity is known.

Use canonical non-force worktree removal. Never reset/clean/stash/force merely
to make cleanup succeed. Branch deletion remains a separate decision.

## Routing output additions

In addition to normal A-FastTask output, report:

- `DEVICE_ROUTE` for every active/blocked device;
- `WIP_SLOT` and mutable/review role;
- `HARNESS_ROUTE` + exact model/effort/readiness;
- `ADVISORY_SKILLS` actually available/invoked;
- `CLEANUP_STATE` for completed lanes;
- exact next safe action.

A-Faster ends where A-FastTask ends: after routing/binding. The authorized
executor/integrator continues safe work immediately under the selected existing
workflow.
