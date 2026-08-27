# WO-P1-077 — Desktop Commander runtime profile / North Star execution hand

Status: IN_PROGRESS
Owner: GPT-5.6 Sol
Branch: `feat/north-star-runtime-sunday-family`
Base: `63ac2fa`

## Research facts

Desktop Commander provides local/remote filesystem work, terminal/process sessions, interactive process control, bounded output pagination, search, document/data tooling, audit logging, and a Remote Device bridge. Its own security policy explicitly says allowed directories/blocklists are guardrails, not a sandbox; arbitrary terminal execution trusts the connected AI client.

A-Conductor already owns durable jobs, task authority, repo/worktree gates, fixed native adapters, retries/dedup/recovery, evidence, and operator protocol. ADR-0001 forbids building a second MCP gateway/orchestration universe.

## Decision

`Desktop Commander = optional execution hand`, never the brain/control plane.

Add a lightweight provider/runtime profile that makes Desktop Commander routable by capability and security posture without adding an MCP client, polling loop, background thread, Node dependency, or raw-shell operator surface.

## Invariants

- A-Wiki remains brain/policy/memory authority.
- A-Conductor remains manager/router/durable lifecycle/security/verification authority.
- Desktop Commander never receives model-authored arbitrary commands through operator.v1.
- Future execution calls must originate from pre-authorized fixed-method adapters/opaque operation refs.
- Remote capability is metadata until an explicit bounded transport adapter is separately designed and verified.

## Acceptance

1. Pure Python profile maps local/remote Desktop Commander to canonical `Runtime`, `Capability`, and `ExecutionSurfaceTraits`.
2. Remote mode advertises `remote.device`; local mode does not.
3. Long-running/resume/background/repo-tool traits are explicit and deterministic.
4. Security posture records `trusted_client_required=True` and `guardrails_are_sandbox=False`.
5. No network/process/filesystem I/O occurs while constructing a profile.
6. No raw shell/argv/command payload is added to operator protocol or graph scheduler.
7. No new runtime dependency is introduced.
8. Unit tests and architecture contract pin these boundaries.

## Later bounded extension (not this slice)

After GE-6/GE-7 are green/merged, add an injected transport adapter that maps opaque pre-authorized operation refs to fixed Desktop Commander calls. Reuse durable job control, supervisor/reconciliation, dedup, output backpressure and evidence stores. Do not implement a general MCP proxy.

## Checkpoint — 2026-08-27

Implemented as an additive pure metadata slice.

- TDD RED: 3 tests failed because `a_conductor.desktop_commander_runtime` did not exist.
- Added `DesktopCommanderMode`, deterministic local/remote profiles, canonical runtime capabilities, execution-surface traits, and explicit security posture.
- Security contract pins: trusted client required; guardrails are not a sandbox; task authority false; direct operator shell false; owns MCP gateway false.
- Remote mode adds only `remote.device` capability.
- New architecture contract: `docs/contracts/desktop-commander-runtime.md`.
- Combined domain + Desktop Commander + Sunday Family regression: 66 passed, 1 local Tcl/Tk environment skip.
- `compileall` PASS; `git diff --check` PASS.
- Static scan found no subprocess/network/thread/timer/poll implementation in the runtime profile.

Status: LOCAL_VERIFIED — future actual transport remains separately gated after GE-6/GE-7 and security design; this slice itself adds no live transport.
