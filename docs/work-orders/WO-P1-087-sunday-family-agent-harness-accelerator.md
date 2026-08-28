# WO-P1-087 — Sunday Family Multi-Model Agent Harness Accelerator

Status: ACTIVE / PLAN-FIRST ACCELERATOR
Owner: GPT-5.6 Sol integrator via Remote Desktop Commander
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-agent-harness`
Branch: `docs/wo-p1-087-agent-harness-priority`
Base: `origin/main@9106da2e5d2e7f5a687d40cc0b4677b6321ce1c1`

## Goal

Make the next primary A-Sunday Conductor development priority a provider-neutral multi-model execution fabric that can hand bounded work to sub-agents automatically, beginning with an Anthropic/Claude-Code-style harness backed by the user's GLM-5.3 Anthropic-compatible proxy.

Primary user outcome:

> Give A-Sunday Conductor the goal once. The Conductor creates durable task packets, selects an eligible model/runtime, dispatches work, gathers evidence, reviews/repairs, and continues without the user copying prompts between GPT, GLM, Claude Code, ZCode, or future models.

This is an accelerator for the existing North Star and Capability Fabric. It is not a second scheduler, task store, memory system, worker registry, or product.

## User-priority decision — 2026-08-28

The user explicitly moved this capability ahead of other new feature development because eliminating manual copy/paste and model switching should increase the speed of all later A-Conductor work.

Safety/release fixes and already-owned Graph branches remain independent P0 lanes and are not cancelled, overwritten, or deleted by this priority change.

## Reuse-before-build verdict

Classification: `REUSE + EXTEND + WRAP`.

Reuse:
- A-Wiki brain/policy/memory and cross-agent work-order conventions;
- Capability Fabric v1 / WO-P1-085;
- C0 capability vocabulary contract in PR #110 / WO-P1-086;
- North Star runtime catalog/routing seam (N2);
- bounded provider-operation contract pattern (N3);
- GE scheduler and durable job/execution/recovery authority;
- existing Sunday Family desktop/control-center branding and interaction direction.

Do not invent:
- a second provider database if the current Provider/Runtime/Capability seams can be extended;
- a Claude-specific task lifecycle;
- a GLM-specific scheduler;
- a second retry/claim/checkpoint system;
- a GUI macro/desktop-click automation dependency for Claude Code or ZCode.

## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only in this isolated worktree and the bounded documentation/SSoT scope below.

Allowed in this plan-first slice:
- `PROJECT-PLAN.md`
- `DESIGN.md`
- `COLLAB.md`
- `CURRENT-WORK.md`
- `handoff.md`
- this work order
- `docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md`

Forbidden in this slice:
- production `src/**` and `tests/**`;
- PR #104 / GE-6 branch/worktree;
- PR #108 installer branch/worktree;
- PR #110 files;
- active North Star branch files;
- A-Wiki mutation;
- live connector processes/ports;
- credential stores and plaintext API keys.

## First-provider decision

The first implementation target is an **Anthropic-harness provider path** because the user prefers the Claude Code/Anthropic agent harness behavior.

Preferred coding path:

`A-Sunday Conductor -> Claude Code CLI harness -> Anthropic-compatible provider -> GLM-5.3`

Optional lightweight path later:

`A-Sunday Conductor -> Anthropic-compatible direct API -> GLM-5.3`

The architecture must remain provider-neutral so OpenAI, Anthropic first-party, Gemini, Qwen/DeepSeek-compatible APIs, local/Ollama/llama.cpp, and future workers can be added without changing the task model.

## Security / trust boundary

- Never persist provider API keys/tokens in Git, work orders, logs, screenshots, task prompts, or provider profiles.
- Store only a credential reference; resolve secrets from an OS/private secret store at execution time.
- A third-party proxy is a distinct trust boundary. Provider policy must be able to restrict sensitive/private data egress independently of model capability.
- Never assume an Anthropic-compatible endpoint is Anthropic-operated.
- Provider health/quota observations are evidence, not authority.

## Acceleration dependency graph

```text
AHA-0  Accept capability vocabulary C0 (#110)
  |
  +--> AHA-1  Provider + Harness contracts
              |
              +--> AHA-2  Secure provider configuration + health/quota observation
              |            |
              |            +--> AHA-3  Claude-Code/GLM adapter with fake backend
              |                         |
GE-6/GE-7 ----+-------------------------+--> AHA-4  Durable dispatch integration
                                                     |
                                                     +--> AHA-5  GPT <-> GLM review/repair loop
                                                     |           |
                                                     |           +--> AHA-6 Parallel READY-task execution
                                                     |
                                                     +--> AHA-7 Sunday Family Models & Agents UI
                                                                  |
                                                                  +--> AHA-8 Additional providers
```

AHA-1/AHA-2 may proceed as isolated contracts/configuration seams while GE work remains owned elsewhere. AHA-4 must not create a substitute scheduler/dispatcher merely to bypass GE gates.

## Acceptance for this plan-first slice

- roadmap makes the agent-harness accelerator the primary new-feature priority;
- existing Sunday Family brand/UI authority is extended, not replaced;
- Anthropic/Claude Code harness is first implementation path but vendor-neutral abstractions remain explicit;
- proxy credential values are absent from tracked files;
- third-party trust and quota/health are modeled as policy/evidence;
- existing PR/worktree ownership is preserved;
- branch/worktree cleanup removes only proven merged/redundant material;
- `git diff --check` and a bounded secret-pattern scan pass;
- next implementation slice is small and resumable.

## Verification

Run:

```text
git status --short --branch
git diff --check
git diff --name-only origin/main...HEAD
```

Before push/PR, verify no secret-like GLM proxy token or `ANTHROPIC_AUTH_TOKEN` credential value is present in the diff.

## Next safe action

1. PR #110 C0 is merged as `6487cb2`; consume it as the accepted vocabulary contract;
2. open a new bounded AHA-1 implementation work order from current `origin/main` for provider/harness contracts only;
3. keep #104/#108/North-Star mutable scopes isolated;
4. do not start live provider execution until credential/trust/quota policy and fake-backend verification exist.

## Checkpoint — plan branch / Draft PR

- Plan/SSoT commit: `9a2e8dd6b7c492ffa2c7e2b747dd3280dc2f1e6c`.
- Draft PR: #111 `docs: prioritize Sunday Family multi-model agent harness`.
- Remote PR base: `main@9106da2`; head after first push: `9a2e8dd`.
- Remote diff inspected: exactly seven intended docs/SSoT files; no production code/tests.
- Local `git diff --check`: PASS before commit.
- Bounded secret scan: PASS; no proxy credential value persisted.
- Safe cleanup preserved #104, #108, #110, North Star, unique audit/untracked lanes; merged/redundant branches/worktrees only were removed.
- Old release worktree registration was removed, but its physical folder remains process-locked; no unknown process was killed.

Next safe action: create the AHA-1 provider/harness contract slice from `main` including merged C0 (`6487cb2`); do not start live provider execution yet.
