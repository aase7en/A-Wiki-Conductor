# WO-P1-530 — A-Faster hierarchical /goal sub-goals

Issue: #530
Class: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-530-A-FASTER-GOALTREE-MAC-001
Base: 1486e75484afa21a79810a7ebe0e92abb384c3b7
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo530-a-faster-goaltree
Branch: feat/wo-p1-530-a-faster-goaltree

## Goal

Standardize hierarchical goal routing without creating a second scheduler:

`Codex/A-NightShift parent /goal -> A-Faster lane binding -> Sunday durable execution -> Kilo /goal child -> GLM worker -> optional Jev advisory -> result -> parent HARVEST/REFILL`.

## Required invariants

- Parent NightShift goal is the only run lifecycle owner.
- Child `/goal` is a bounded task packet executor, not roadmap/scheduler/claim/review/completion authority.
- Global WIP stays max 3 mutable + 1 independent read-only review; 1 hotspot = 1 owner.
- Normal nesting is bounded to parent -> Kilo/GLM child -> optional TypeSafe-Jev advisory.
- No recursive unbounded spawning.
- Every child binds task/claim/repo/worktree/branch/HEAD/scope/evidence/result destination.
- Every material GLM child requires a fresh CoinTH quota preflight immediately before dispatch.
- Kilo child transport must be through `sunday_dispatch`, explicit `--dir`, process-local `KILO_CONFIG_CONTENT={"share":"disabled"}`, CLI `--no-share`.
- Direct Kilo attempts that emit a share URL or lack durable execution identity are invalid acceptance evidence.
- GLM-5.3 MAX: bounded author/repair/review.
- GLM-5.3 Flash: bounded read-only census/recon/shaping.
- TypeSafe-Jev: advisory only; `authoritative_for_action=false`.
- Parent harvests terminal children before refill or duplicate dispatch.
- No work is manufactured merely to burn quota.

## Prerequisite proof

Before tracked semantic changes, prove the installed Kilo runtime accepts a `/goal` child entry under a Sunday durable read-only execution with sharing disabled. Record exact execution/result evidence. If unsupported, encode a truthful fallback to the existing one-pointer task command rather than inventing syntax.

## Allowed tracked scope

- `.agents/skills/a-faster/SKILL.md`
- `tests/test_a_faster_invocation_contract.py`
- `tests/test_a_faster_utilization_guard.py` only if required
- this WO

## Forbidden

NightShift files/tests, `src/a_conductor/**`, task/claim stores, CURRENT-WORK, handoff, COLLAB, secrets.

## Verification

- exact Kilo /goal route proof;
- focused A-Faster invocation/utilization tests;
- adversarial tests for WIP, nesting, durable transport, quota gate and privacy;
- UTF-8, diff-check, secret scan, exact scope;
- independent R3 review on frozen exact SHA;
- exact-head CI;
- Sol exact-SHA acceptance and post-main verification.


## Route-proof checkpoint

The bounded read-only Sunday execution exec-muf9a5wr-qz0tnqxp launched
GLM-5.3 Flash through Kilo with process-local sharing disabled and /goal at
the prompt boundary. It produced no output or capability receipt while the
Kilo session remained alive without session progress for more than ten
minutes. The exact execution was cooperatively cancelled, harvested and
collected with zero output and no tracked mutation.

Classification: KILO_GOAL_CAPABILITY=UNVERIFIED_HEADLESS.
This is not evidence that Kilo UI lacks /goal; it proves only that the current
headless Kilo run route cannot be trusted as a verified slash-goal transport.
WO530 therefore standardizes POINTER_FALLBACK until an exact harness/version
capability probe succeeds. No blind redispatch was performed.

## Post-review bounded repair (R3 CHANGES_REQUIRED on 5bfef6908a79b6058ee7bb4abfbcb2ca16a089eb)

Independent R3 review exec-mufcpisi-waxstdlv returned CHANGES_REQUIRED
(P2=1, P3=1) on the frozen candidate above. Accepted findings and repair,
inside the existing WO530 allowed scope only:

- P2 (transport ambiguity): the child-routing wording now pins the exact
  `sunday_dispatch` durable execution tool. A generic "durable dispatch"
  category, alternate durable transports, other dispatch tools, and direct
  Kilo invocations are rejected as INVALID_CHILD_EVIDENCE for this contract.
  The invocation-contract test now pins the exact tool name and the
  rejections.
- P3 (admission hardening): the child-routing section now states that fresh
  CoinTH proxy quota alone is never upstream readiness. Material GLM child
  admission requires PROXY_QUOTA_STATE=AVAILABLE AND
  UPSTREAM_PROVIDER_READINESS=READY plus the existing route/claim/scope
  gates. UPSTREAM_PROVIDER_READINESS=THROTTLED waits for the declared reset/cooldown without repeated
  probing; UNKNOWN or any non-READY upstream fails closed for GLM child
  dispatch while independent GPT/Codex work may continue. Readiness values
  are per-dispatch observed evidence and must never be hard-coded from any
  transient probe (the READY evidence from exec-mufchq7d-8v9a099t is context
  only, never a contract constant).

No other WO530 invariant changed: parent NightShift lifecycle ownership,
max 3 mutable + 1 review, one hotspot one owner, bounded nesting, no
recursive spawning, KILO_GOAL_CAPABILITY fallback truth, share disabled +
--no-share, MAX/Flash/Jev role boundaries, harvest-before-refill, and no
quota burning are unchanged. New candidate SHA is frozen by the integrator
for delta re-review.

## Integrator semantic correction

The GLM repair initially wrote PROXY_QUOTA_STATE=THROTTLED, which is outside
the accepted proxy-quota enum. The integrator corrected this before freeze to
UPSTREAM_PROVIDER_READINESS=THROTTLED and added a negative assertion that
PROXY_QUOTA_STATE=THROTTLED must not appear in the child-routing contract.


## 2026-09-24 user override — wait-aware A-NightShift/A-Faster flow

The operator explicitly requires the parent run to keep useful work moving while
another lane is waiting on approval, CI, GLM, TypeSafe-Jev, another external
dependency, or a provider cooldown. This behavior is now part of A-Faster rather
than a long prompt the operator must repeat.

`WAIT_AWARE_AUTO_BACKFILL` recognizes:
- `WAITING_APPROVAL`
- `WAITING_CI`
- `WAITING_GLM`
- `WAITING_JEV`
- `WAITING_EXTERNAL`
- `COOLDOWN`

A-NightShift remains the parent lifecycle owner. On a typed wait it checkpoints
truthfully; A-Faster reconstructs actual occupancy and fills independent
`SAFE_READY` capacity using the existing A-FastTask binding, claim, lease,
scope, collision, provider and review gates.


Wait state is not itself capacity evidence. A parent marked `WAITING_GLM`
does not release its mutable slot when an active delegated GLM mutation child
still owns the same hotspot. Active mutation occupancy is reconstructed from
durable process/execution/claim evidence, not from a label.

The accepted Issue #537 elastic policy permits up to two borrowed mutable claims
while qualifying base lanes are truthfully waiting, but simultaneous active
mutation remains at most three and one mutable hotspot still has exactly one
owner. The independent read-only review lane remains separate.

When a dependency resolves:
`RECOVER -> RECONCILE -> HARVEST -> recompute occupancy -> contract/refill`.
If a returning base lane needs capacity, borrowed work finishes only its current
bounded micro-step, checkpoints, and becomes `PARKED_CAPACITY` before base
resume. Contraction never kills an owned task, resets Git, stashes unknown work,
or duplicates a claim/redispatch merely to lower occupancy.

Once `A_FASTER_ACTIVE` is established, this flow continues automatically until
a real goal/stop gate, terminal completion, or explicit deactivation. Chat/session
loss is recovery/continuation, not a reason to forget or duplicate existing work.
