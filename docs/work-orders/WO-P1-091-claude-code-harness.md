# WO-P1-091 — Claude Code Harness Adapter (AHA-3)

Status: ACTIVE / TDD IMPLEMENTATION
Owner: GPT-5.6 Sol via Remote Desktop Commander
Parent: WO-P1-087 Sunday Family Agent Harness Accelerator
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-claude-harness`
Branch: `feat/wo-p1-091-claude-code-harness`
Base: `origin/main@ca4cd986c9d3ad0b9af833350f067ff9056df653`

## Goal

Implement the smallest provider-neutral Claude Code harness adapter required before durable scheduler/dispatch integration.

The adapter consumes the accepted AHA-1 dispatch shape plus AHA-2 provider readiness evidence, builds a fixed non-interactive read-only Claude Code invocation, uses an injected runner, accepts only explicit task-packet files, bounds output, and redacts in-memory sensitive values before returning evidence.

## Reuse-before-build

Classification: `WRAP + EXTEND`.

Reuse:
- AHA-1 `harness-dispatch/v1` and provider/harness contract;
- AHA-2 provider configuration + fresh readiness evaluation;
- existing durable/supervised execution contracts as the future runner boundary;
- existing Sunday Family task/work-order SSoT; no chat transcript becomes dispatch authority.

Observed local Claude Code interface (read-only inspection):
- version `2.1.178`;
- `-p/--print` non-interactive mode;
- `--output-format json`;
- `--no-session-persistence`;
- `--safe-mode`;
- `--system-prompt-file <file>`;
- explicit `--permission-mode`, `--tools`, `--model`, and `--effort` controls.

## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only in this isolated worktree and the bounded files below.

Allowed scope:
- this work order;
- `src/a_conductor/claude_code_harness.py`;
- `tests/test_claude_code_harness.py`;
- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md` for continuity;
- `README.md`, `docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md`, and `docs/plans/2026-08-28-worker-auto-fallback-and-glm-benchmark.md` for the user-requested roadmap/status update.

Forbidden:
- GE-6/GE-7 scheduler/graph/durable-dispatch ownership;
- PR #108 installer files;
- North Star unique branch files;
- desktop UI;
- actual Claude subprocess execution or live provider/network call;
- credential-store implementation or raw credential values in tracked/durable state;
- second scheduler/router/retry authority/task lifecycle.

## Acceptance

1. Python dispatch model mirrors AHA-1 required identity/budget fields and contains no prompt/transcript/command/argv/environment payload.
2. Only `CLAUDE_CODE_CLI` is accepted by this adapter.
3. AHA-3 initially executes `READ_ONLY` only; `PROJECT_MUTATION` fails closed until durable AHA-4 gates exist.
4. Provider must be enabled and have a fresh `AVAILABLE` AHA-2 observation before runner invocation.
5. Task packet is an explicit existing file, bound to `task_contract_ref`, constrained under the declared worktree, size-bounded, and SHA-256 verified before invocation.
6. Invocation is fixed non-interactive JSON mode, no session persistence, safe mode, read-only tools, plan permission mode, exact cwd/model/effort, and no dangerous permission bypass.
7. Environment metadata is a closed allowlist of provider endpoint/credential references only; no environment values enter dispatch/invocation evidence.
8. Runner is injected; tests use a fake runner only. No subprocess/network client is implemented.
9. Timeout and output budget are copied exactly from dispatch; oversized output fails closed.
10. JSON result is parsed only after budget checks; returned payload/stderr are redacted with caller-supplied in-memory sensitive values.
11. Runner/provider DONE remains evidence only; adapter creates no task completion authority.

## Verification

RED first, then GREEN:
- `python -m pytest -q tests/test_claude_code_harness.py tests/test_provider_configuration.py tests/test_provider_harness_contract.py tests/test_domain.py`
- `python -m compileall -q src/a_conductor`
- `git diff --check`
- changed-file/forbidden-import/secret-signature scans.

Stop after fake-runner adapter is CI-green and merged. Live read-only provider smoke is a separately gated follow-up requiring safe configured credentials/health; AHA-4 remains blocked on GE scheduler/durable-dispatch acceptance.

## Checkpoint — roadmap / delegation planning

User added worker auto-fallback as a priority before broad autonomous parallelism. AHA-4A/AHA-4B are now in the harness roadmap; README exposes release/development versions and a live checklist.

GLM-5.3 repository benchmark evidence:
- owned GE-6 / PR #104 remains open on `feat/ge-6-scheduler`;
- independent current graph-suite recheck in that worktree: `83 passed in 1.76s`;
- GitHub currently reports PR #104 non-mergeable against newer `main`, so its next suitable bounded task is owner-led reconciliation + graph verification.

AHA-3 TDD state remains RED-to-GREEN in progress: the fake-runner tests were written and the production module has only begun. No live Claude/provider subprocess has been authorized or executed. Roadmap/docs checkpoint may be committed independently; partial AHA-3 source/tests must remain preserved for the next implementation micro-step.