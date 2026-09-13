# GLM Goal — WO-P1-230 ZRA-2 review task-contract provider authority

Execute this bounded predecessor only. Do not merge and do not resume WO226 source in this same lane.

## Bootstrap / mutation gate

1. Read `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md`.
2. Re-pin actual `origin/main`, branch/worktree/HEAD/dirty state, Issue #214, PR #314, and open claims.
3. Read:
   - `docs/work-orders/WO-P1-230-zra2-review-task-contract-provider-authority.md`;
   - current accepted `src/a_conductor/zero_relay_review_task.py` + focused tests;
   - existing `schemas/task-contract.schema.json`;
   - `provider_execution_authority.py` / `parallel_ready_execution.py` / `zcode_runner.py` read-only authority seams selected by the WO.
4. Reconcile stale open C0 PRs #296/#298/#299 as historical/rejected/superseded lanes already folded through WO222/PR #303. Do not mutate those worktrees/branches.
5. Publish one new bounded source claim before mutation. Fresh isolated source branch/worktree from then-current `origin/main` is preferred.
6. Confirm no current owner overlaps `zero_relay_review_task.py` / `test_zero_relay_review_task.py`. Unknown/conflict => `SAFE_TO_MUTATE=NO` and STOP.

## Root cause to solve

Do NOT patch WO226 with another caller-supplied security/profile check.

Current review v1 is a deterministic Markdown task with synthetic logical contract ref. Production provider authority requires security provenance from persisted `task-contract/v1` bytes via `ProviderExecutionRequirement`, whose task-contract ref is a project-relative authority file and whose operation ref wraps the exact base operation.

Create a v2 review publication that preserves v1 unchanged and adds a deterministic task-contract authority sidecar for the same exact reviewer prompt.

## Required v2 shape

Use deterministic artifacts derived from exact author `ResultIdentity` + exact reviewed HEAD + explicit trusted project id:

- `runs/zra2-review-v2-<digest>.md` — reviewer Markdown prompt;
- `runs/zra2-review-v2-<digest>.task.json` — canonical existing `task-contract/v1` authority;
- `runs/zra2-review-result-v2-<digest>.json` — logical semantic result destination.

For v2, the contract ref is the project-relative `.task.json` path. The Markdown remains the `TaskPacketFile.path` and its exact SHA is bound inside the task-contract metadata.

The task-contract must validate the existing schema and be READ_ONLY/no-secret/no-task-egress. Provider/model/endpoint/credential/generation/runtime facts are NOT embedded as caller authority in review bytes.

## Provider-authority compatibility target

Prove with real existing types (no live provider) that the persisted v2 task-contract can be consumed by:

`ProviderExecutionRequirement.from_task_contract_file(...)`

where:

- requirement task_contract_ref == v2 contract ref/path;
- requirement base_operation_ref == exact `ZCodeTaskPacketIdentity.canonical_operation_ref()` of the Markdown packet;
- GraphDispatch work-order ref == v2 contract ref;
- GraphDispatch operation ref == `provider_requirement.operation_ref`;
- task packet contract ref == provider requirement contract ref;
- provider security and expected generation align with the requirement;
- complete endpoint/security/generation authority is present;
- `ParallelReadyTask` constructor accepts the exact aggregate;
- drift of requirement security/generation/operation/work-order fails at existing authority boundaries.

Do not call a live provider, reserve admission, spawn ZCode, resolve secrets, or alter provider/store/lease code.

## Publication safety

Reuse `NativeFileSystem.create_text_if_absent()` and existing deterministic verification only.

RED-first cover exact replay, prompt-only crash recovery, divergent prompt, divergent authority sidecar, authority rebinding wrong prompt path/hash, concurrent exact publication, concurrent divergent publication, and unverifiable partial state.

No raw `Path.write_text`, overwrite, second no-clobber helper, new journal/store/lock/scheduler.

## Mutable scope

Normally ONLY:

- `src/a_conductor/zero_relay_review_task.py`;
- `tests/test_zero_relay_review_task.py`;
- WO230 result/checkpoint evidence.

Provider/ParallelReady/ZCode modules are read-only. If implementation needs to modify any of them, STOP `SCOPE_EXPANSION_REQUIRED` with exact evidence before touching them.

If the required provider-operation/task-contract identity cannot be expressed while preserving existing v1 + production authority, STOP `DESIGN_GAP` with the conflicting exact invariants. Do not invent another provider-policy engine or requirement type.

## Verification floor

Before freeze:

- all existing v1 C0 tests remain green;
- v2 RED/GREEN matrix from WO230 is green for the correct reason;
- real task-contract schema validation passes;
- real ProviderExecutionRequirement + ParallelReadyTask compatibility proof passes;
- directly related provider-authority/parallel-ready identity tests remain green where read-only execution is sufficient;
- compile/import, `git diff --check`, strict UTF-8/no U+FFFD, scope and secret-shape checks pass;
- no C1 semantic parser, provider store/schema, runtime or live effect creep.

Freeze ONE candidate SHA, push/open or update one draft PR, record exact tests/results in a durable WO230 result/checkpoint, trigger exact-head CI, and STOP at `CANDIDATE_FROZEN_FOR_INDEPENDENT_REVIEW`.

Never self-accept or merge. Sol/Astra own exact-SHA acceptance and post-main release.
