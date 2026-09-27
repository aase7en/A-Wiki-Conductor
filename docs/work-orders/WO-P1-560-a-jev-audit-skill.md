# WO-P1-560 — A-JEV-Audit skill

Status: GOVERNANCE BOOTSTRAP / READY TO CLAIM
Issue: #560
Risk: R2 — routing guidance and deterministic skill-contract coverage
Topology: CONTROL_PLANE_ONLY
Authority repo: `aase7en/A-Wiki-Conductor`
Execution repo: `aase7en/A-Wiki-Conductor`
Base: `0f0a5f17b33e82516e39ff00f482887728810e87`
Branch: `codex/wo-p1-560-a-jev-audit`
Worktree: `/Users/aase7en/.codex/worktrees/wo-p1-560-jev-routing/A-Wiki-Conductor-codex-supervisor`

## Goal

Add one repository-local skill that audits whether an already-authorized,
bounded semantic question is suitable for the accepted TypeSafe-JEV seam. It
must recommend `FIT`, `SHADOW_ONLY`, `NO_FIT`, or `INSUFFICIENT_EVIDENCE`
from explicit evidence while leaving task selection, claims, quota, provider
admission, mutation, review, merge, and completion authority with existing
deterministic systems and the integrator.

## Exact mutation scope

1. `.agents/skills/a-jev-audit/SKILL.md` (new)
2. `tests/test_a_jev_audit_skill_contract.py` (new)
3. `docs/work-orders/WO-P1-560-a-jev-audit-skill.md` (this checkpoint)

Everything else is read-only. In particular, do not touch A-FastTask,
A-Faster, A-NightShift, `.codex/hooks/**`, `src/a_conductor/**`, #498/#549/#551
owned paths, A-Wiki, SunDayRemoteMCP, provider configuration, secret stores,
or runtime claim/WIP/quota state.

## Required behavior

- Load the accepted A-Faster JEV fast-path reference; reuse existing
  provider-neutral seams rather than inventing another provider, scheduler,
  task/claim store, state machine, or authority.
- Audit semantic task fit only after deterministic task identity, scope,
  authority, and ordinary execution eligibility are established.
- State the supported JEV family and mode from current accepted evidence;
  never infer production admission from provider responsiveness or skill
  wording.
- Minimize/redact payloads; reject secrets, raw private/customer data, and
  unnecessary source/context. Record sensitivity and minimization evidence.
- Require held-out/local evidence, deterministic baseline/fallback, expected
  benefit, confidence/error handling, and mode/circuit status before
  recommending beyond shadow observation.
- Keep proxy quota, upstream readiness, JEV credential/route readiness, and
  hardware/device liveness as separate dimensions. `UNKNOWN` is neither
  `EXHAUSTED` nor `AVAILABLE`.
- Treat the previously exposed TypeSafe credential as unsafe until an
  authoritative rotation proof is recorded; resolver presence alone is not
  rotation proof. No live JEV call is authorized by this work order.
- Emit only `FIT`, `SHADOW_ONLY`, `NO_FIT`, or `INSUFFICIENT_EVIDENCE`, with
  evidence and the deterministic decision owner. JEV output never authorizes
  execution or changes a route by itself.

## Acceptance

- Skill has valid YAML frontmatter (`name: a-jev-audit`), concise triggers,
  authority boundaries, procedure, decision rubric, and output format.
- Skill-contract tests pin the four outputs, evidence requirements, security
  boundary, accepted-mode gate, stale/unknown handling, and no-authority rules.
- Targeted contract tests pass; strict UTF-8 and exact-scope checks pass;
  `git diff --check` is clean.
- Freeze an exact candidate SHA. Independent review uses the one global review
  slot only when free; review/CI/integrator acceptance remain separate gates.

## Provider and execution gates

- No TypeSafe/JEV or GLM request in this lane. The JEV credential remains
  blocked pending the rotation evidence required by WO-P1-488.
- No quota probe, Kilo/Claude dispatch, or new child lane. Provider work is
  outside this skill's scope and remains governed by the accepted pre-dispatch
  authorities.
- This work order does not alter the accepted project-wide WIP policy.

## Bootstrap checkpoint

The Issue #560 proposal is the governing task authority for this bounded
docs/test slice. This file is the permitted initial governance bootstrap; after
its commit, re-run branch/HEAD/dirty/scope/claim/collision checks before
creating the skill or tests. Use an exact Issue #560 claim comment with current
branch, worktree, HEAD, scope, executor, and next action before implementation.

## Checkpoint log

- 2026-09-27: Created the bounded bootstrap in a clean isolated worktree at
  the verified remote-main base. No skill, test, provider, hook, or source
  mutation has started.
