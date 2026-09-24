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
