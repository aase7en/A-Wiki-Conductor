# WO-P1-171 — Evidence-Native Agent Engineering Roadmap

Date: 2026-09-10
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / STACKED_ROADMAP_CAPTURE
Priority: P1 SAFETY-ACCELERATOR / FUTURE CAPABILITY
Risk: R2 architecture/governance docs
Repository: `aase7en/A-Wiki-Conductor`
Branch: `docs/wo-p1-171-agent-evidence-roadmap`
Base: `origin/docs/wo-p1-170-provider-settings-roadmap@2b5ecaab309f9db031c06b24ba8490c9db61013a`
Parent dependency: Draft PR #243 / WO-P1-170 (claim released; PROJECT-PLAN delta unmerged)

## User outcome

Extend the future A-Sunday Conductor roadmap with source-verifiable patterns from current AI engineering practice and public developer communities. Prefer reuse/copy-and-adapt where license and architecture allow it; do not rebuild a framework just because its idea is useful.

This WO is roadmap-only. It does not authorize runtime/source changes, package installation, telemetry export, provider traffic, memory promotion, secret access, or changes to active WO168/169/Zero-Relay implementation lanes.

## Reuse-before-build

Classification: `REUSE + WRAP + EXTEND`; `BUILD` only after an implementation WO proves the capability is missing.

A-Conductor already owns durable jobs, worker/provider admission, execution/recovery, ReviewBus, orchestration evidence and operator state. The new roadmap must extend those authorities rather than introduce a second scheduler, trace SSoT, router, evaluator authority, memory store or provider registry.
## External evidence basis

Canonical research synthesis is being captured in A-Wiki at `docs/research/agent-engineering-evidence-20260910.md`. Key public evidence includes:
- Ponytail independent benchmark #236: minimality lowers code substantially but can reduce unstated-edge robustness;
- Pydantic AI durable-execution docs + issue #6911: required durability can disappear silently when a capability is not effectively bound;
- Hugging Face smolagents: OpenTelemetry-based instrumentation for production run inspection;
- OpenTelemetry GenAI semantic conventions: common agent/tool/model/usage identity plus explicit sensitive-content warnings;
- SWE-agent trajectories: per-run config/log/exit/trajectory artifacts with evaluation kept separate;
- OWASP AI Agent Security + AgentDojo: tool data, memory, autonomy and multi-agent propagation require adversarial security testing;
- Aider issue #5058: planner/architect output must not become trusted editor authority transitively.

## Roadmap decision

Add an **Agent Efficiency, Evidence & Trust Plane (AEET)** after current Zero-Relay/active compatibility gates. It is not a new control plane; it is a set of bounded capabilities attached to existing execution/evidence authorities.

Planned capabilities:
1. benchmark/evaluator self-test and task baseline;
2. risk-adaptive minimality policy for coding-agent lanes;
3. effective policy/capability attestation;
4. local-first versioned execution trace envelope;
5. stable replay/operation identity audit and idempotency gaps;
6. inter-agent provenance/taint validation;
7. adversarial agent-security eval pack;
8. accepted-run efficiency/quality scoreboard;
9. sanitized evidence feedback to A-Wiki.
## Dependency / sequencing guard

Do not interrupt or rewrite the frozen/current lanes. The first implementation slice may be claimed only after re-pinning actual main and active ownership. In particular:
- WO168/169 compatibility/continuity work keeps its existing authority;
- WO170 remains the stacked parent roadmap delta until PR #243 is merged/rebased/closed;
- Zero-Relay remains the throughput priority; AEET must improve its safety/measurement rather than displace it;
- before broad multi-provider autonomous pilots, the future implementation plan must explicitly decide whether effective-capability attestation and inter-agent provenance gates are prerequisites based on the then-current runtime evidence.

## Mutable scope

- `COLLAB.md` claim/checkpoint row for WO171;
- `PROJECT-PLAN.md` roadmap section only;
- this work order.

Forbidden: `src/**`, `tests/**`, secrets/private Drive, `CURRENT-WORK.md`, `handoff.md`, WO168/169 source/worktrees, and the WO170 accelerator-plan file.

## Verification

- verify stacked ancestry exactly from WO170 head;
- confirm WO170 claim is released and PR #243 remains the only parent `PROJECT-PLAN.md` delta;
- exact changed-file/scope audit;
- `git diff --check` and strict UTF-8 read;
- scan changed docs for secret/private-path values;
- source/URL/license spot-checks against public evidence;
- independent exact-SHA architecture review required before merge because this changes future trust/evaluation policy.

## Next safe action

Capture the AEET section in `PROJECT-PLAN.md`, verify the docs-only candidate, release the mutable claim, push a stacked PR against `docs/wo-p1-170-provider-settings-roadmap`, and do not merge it ahead of its parent.
