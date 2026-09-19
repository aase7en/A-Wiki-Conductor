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

For **substantial A-Sunday Conductor engineering work**, A-Faster is the
default acceleration overlay after canonical A-FastTask has bound authority.
Also use it whenever one or more are true:

- the user explicitly asks for A-Faster / faster multilane execution;
- independent READY work can run concurrently on Windows and macOS;
- Kilo Code CLI and Claude Code CLI can safely own different bounded lanes;
- a finished lane should be recycled after exact closeout/cleanup proof;
- the task needs coordinated Workers + RDC + GitHub remote truth.

Do not force A-Faster onto trivial Q&A, a single obvious mechanical edit, or
already-bound mid-lane work that needs no new routing decision. These exclusions
preserve A-FastTask's negative triggers and avoid routing overhead for tiny work.

## Global WIP and no-collision rule

The default budget remains **one global budget across every device, harness,
repository, and CROSS_REPO compatibility-set member**:

- max 3 mutable implementation lanes;
- max 1 independent read-only review lane.

Recovery/blocker work uses headroom inside this same `3 mutable + 1 review`
budget; it is not an additional lane class unless an accepted Work Order
explicitly changes capacity.

Never multiply WIP by device, harness, or repository.

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

## Mandatory substantial-session bootstrap

For every substantial A-Sunday Conductor engineering session:

1. attempt lightweight READ-ONLY readiness discovery for **SunDay-Worker 1..5**
   individually; record each as available, unavailable, or a typed surface
   blocker such as `PLUGIN_NOT_EXPOSED_TO_CHAT`; never claim a Worker ran when
   the current harness cannot invoke it;
2. attempt RDC device discovery and runtime readiness for every connected
   Windows/macOS device that can materially help the task;
3. recover all outstanding delegated executions before allocating new work;
4. bind the single global WIP ledger before dispatch: at most 3 mutable lanes
   plus 1 independent read-only review lane across every Worker, device,
   harness, repository and CROSS_REPO compatibility-set member;
5. if Windows and macOS are both READY and independent work exists, prefer a
   non-overlapping cross-device split; if not, continue on the safe available
   device rather than manufacturing parallelism;
6. keep Worker slots beyond the global WIP budget read-only/standby/recovery
   helpers. Five discovered Workers never mean five mutable writers.

Readiness discovery is routing evidence only. `WORKER/RDC ONLINE !=
SAFE_TO_MUTATE`; exact task/claim/scope/worktree gates still apply.

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

## Durable lane identity overlay

Every delegated A-Faster lane carries the durable identity overlay defined in
`references/durable-lanes.md` (projection only; never authority):

- `LANE_REF` `lane:<TASK_ID>:<role>:<ordinal>` — stable routing label across
  device/harness/session changes for the life of the lane;
- `DELEGATED_RUN_ID` `run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>`
  — unique per-dispatch attempt identity for observation/recovery/harvest;
- `ATTEMPT` — monotonic only inside the lane evidence directory; never retry
  authority;
- `BINDING_DIGEST` — SHA-256 over canonical UTF-8 JSON (sorted keys, compact
  separators) of the safe binding tuple; drift detection only, not
  encryption/authentication.

The durable execution pointer required before or at launch is written under
`runs/<WO>/<lane>/attempt-NNNN/pointer.md` with the minimum fields,
secret-redaction rules, recover algorithm, and cross-device re-pin semantics
defined in `references/durable-lanes.md`. Different recomputed digest on
takeover is `CONTEXT_DRIFT` requiring explicit re-pin and reconciliation,
never automatic transfer. `NEW SESSION != NEW TASK`: reconcile
pointer/process/result/Git and harvest `TERMINAL_UNHARVESTED` work before
redispatch. No global lane registry is created or implied.

## Advisory skill layer

Advisory skills may shape work but never become authority.

### Ponytail

On each Claude Code device, verify the user-level `ponytail@ponytail` plugin
before relying on it. When missing and current user/tool authorization permits
installation, use the upstream-supported Claude Code sequence as two separate
commands/prompts:

```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```

For headless automation, use an equivalent CLI form only when that installed
Claude Code version's help explicitly proves it is supported. Re-verify the
installed marketplace/plugin after mutation; one device's install is never
evidence for another device.

When available, prefer Ponytail as an advisory simplification layer:

- `ponytail` before implementation to challenge unnecessary work;
- `ponytail-review` on a frozen candidate;
- `ponytail-audit` / `ponytail-debt` for bounded simplification analysis.

Do not let YAGNI advice override an accepted Work Order, safety gate, or
verification requirement.

### Caveman

Verify the user-level GitHub-sourced `caveman` skill on every device. When
missing and installation is authorized, install the **skill only** from
`JuliusBrussee/caveman` using its supported skills installer, for example:

```text
npx skills add JuliusBrussee/caveman -g
```

Do not install or enable the optional Caveman proxy/engine merely to satisfy
this skill requirement. Re-verify the resulting skill path/content after
installation. Use Caveman only for transient delegated-agent
communication/token compression where meaning remains unambiguous.

Do **not** use Caveman compression for:

- persisted project docs, issues, PR bodies, commits, handoffs, or evidence;
- security warnings or irreversible-action confirmations;
- exact error text, commands, identifiers, numbers, units, or contract terms.

### Grill Me

Preserve any existing local Grill Me skill; A-Faster runtime convergence must
never overwrite a customized `grill-me` installation. When a real
product/architecture/intent decision remains ambiguous **after codebase,
authority and tool inspection**, invoke the installed Grill Me flow before
inventing the decision (for installations supporting the current project
commands, `/grill-me plan`; `/grill-me check` may challenge an implemented
plan).

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
   no mutable overlap before continuing;
5. recompute `BINDING_DIGEST` from observed binding facts per
   `references/durable-lanes.md`; a different digest is `CONTEXT_DRIFT`
   (typically the device-bound fields), resolved only by explicit re-pin,
   recorded delta, and prior-attempt reconciliation — never automatic
   transfer.

No accepted remote/source on the receiving device means
`SOURCE_UNAVAILABLE / SAFE_TO_MUTATE=NO`.

## Lane recycle and cleanup

A-Faster reuses A-FastTask `references/closeout.md`. Cleanup is never implied
by model/Worker DONE or by a merged-looking branch.

At every accepted/merged/explicitly-abandoned lane closeout, **automatically run
a cleanup-eligibility audit** for that lane and any temporary worktree/folder it
owns. This audit is mandatory; deletion is not. Record
`CLEANUP_STATE=COMPLETE|PENDING|BLOCKED` with the exact path and evidence.
Eligible registered Git worktrees should be removed promptly with canonical
non-force `git worktree remove <exact-path>` so finished lanes do not consume
machine storage. A non-worktree project folder may be deleted only when the
same ownership/disposition/unique-content/process proof establishes that it is
an exact disposable lane artifact rather than user data.

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
- `LANE_REF` + latest `DELEGATED_RUN_ID`/pointer state for every delegated
  lane (or the reconciled disposition per `references/durable-lanes.md`);
- `ADVISORY_SKILLS` actually available/invoked;
- `CLEANUP_STATE` for completed lanes;
- exact next safe action.

A-Faster ends where A-FastTask ends: after routing/binding. The authorized
executor/integrator continues safe work immediately under the selected existing
workflow.
