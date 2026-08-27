# WO-P1-080 — GLM Desktop Commander bounded transport contract

Status: READY_FOR_GLM
Owner: GLM 5.3 MAX (bounded contract/test); GPT-5.6 Sol = integrator/reviewer
Parent: WO-P1-078 / N3
Repository: `aase7en/A-Wiki-Conductor`
Target worktree: `A:\GitHub\A-Wiki-Conductor-glm-dc-contract`
Target branch: `feat/north-star-dc-contract-glm`

## Goal

Define and mechanically verify the Desktop Commander provider-specific bounded-operation contract without implementing live MCP/remote transport. Reuse A-Conductor's existing opaque `operation_ref`, operator protocol, native-operation authority model, durable execution identity, and recovery stack.

## Reuse-before-build verdict

Classification: `REUSE + WRAP/EXTEND`, not NEW orchestration.

Verified existing authority:
- `docs/contracts/operator-command-api.md` — `job.execute` already carries only opaque `operation_ref`.
- `docs/contracts/native-operation-registry.md` + `src/a_conductor/native_operations.py` — fixed allowlisted operation pattern already exists.
- `docs/contracts/desktop-commander-runtime.md` — DC is an execution hand, not authority.
- ADR-0001 remains in force: no general MCP gateway/proxy.
- A-Wiki GitHub `main` cross-agent work-order protocol re-confirmed 2026-08-27; additive isolated worktrees remain the required multi-agent pattern.

## Read first

1. `AGENTS.md`
2. `PROJECT-PLAN.md` sections 15-19
3. `COLLAB.md`
4. `docs/work-orders/WO-P1-078-north-star-execution-plan.md`
5. `docs/work-orders/WO-P1-077-desktop-commander-runtime-profile.md`
6. `docs/contracts/desktop-commander-runtime.md`
7. `docs/contracts/operator-command-api.md`
8. `docs/contracts/native-operation-registry.md`
9. `src/a_conductor/native_operations.py` read-only
10. `docs/adr/ADR-0001-mcp-gateway-deferred.md`
11. `DEFECT_LESSONS.md`

## Allowed mutable scope ONLY

- `docs/contracts/desktop-commander-bounded-transport.md` (new)
- `schemas/desktop-commander-operation.schema.json` (new)
- `schemas/examples/desktop-commander-operation.example.json` (new)
- `tests/test_desktop_commander_transport_contract.py` (new)
- this WO checkpoint section only

Everything else is read-only. If the contract cannot be completed in these files, stop `BLOCKED`; do not broaden scope.

## Forbidden

- no production transport/MCP/network/process code
- no new operation registry or second `operation_ref` namespace
- no raw `command`, `argv`, `shell`, `executable`, `env`, prompt, SQL, or arbitrary payload field
- no scheduler/job-state/graph/GE changes
- no UI/assets/DESIGN changes
- no edits to `native_operations.py`, `operator_protocol.py`, `domain.py`, registry, job lifecycle, or hotspot continuity files
- no PR #102/#104 worktree/branch mutation
- no A-Wiki mutation
- no live connector/device probing
- no dependency/lock changes

## Contract shape

The new schema describes an INTERNAL pre-authorized provider operation definition resolved after `operation_ref`; it is not a model/operator free-form payload.

Required bounded fields:
- `operation_ref` — same opaque identifier semantics already used by A-Conductor
- `tool_family` — fixed enum only
- `project_id` — authoritative project identity reference
- `mutation_intent` — explicit `READ_ONLY` or `PROJECT_MUTATION`
- `timeout_seconds` — integer 1..3600
- `max_output_bytes` — positive bounded integer with a documented hard maximum

Optional `device_id` is allowed only for remote-device definitions; missing/unknown device identity must fail closed later.

Fixed `tool_family` enum should cover only the N3 families needed to describe future adapter calls, for example:
- `PROJECT_FILE_READ`
- `PROJECT_FILE_SEARCH`
- `PROCESS_START`
- `PROCESS_INSPECT`
- `PROCESS_READ_OUTPUT`
- `PROCESS_INTERACT`
- `DOCUMENT_READ`
- `DATA_ANALYZE`

Remote execution is a target identity (`device_id`), not a generic raw-shell family. Do not add `REMOTE_SHELL` or equivalent.

## Acceptance

1. Contract explicitly reuses existing operator/native `operation_ref` authority rather than inventing another registry.
2. JSON schema is `additionalProperties: false` and contains no generic command/argv/shell/executable/env/prompt fields.
3. Every definition is bounded by project identity, mutation intent, timeout, and output budget.
4. Remote-target semantics require explicit registered device identity; no discovery/polling behavior is specified.
5. Read-only inspection is the recommended first remote capability; interactive mutation remains later-gated.
6. Contract states allowed-directory/blocklist protections are defense-in-depth, not the Conductor authorization boundary.
7. Contract states durable execution ID must exist before side effects and transport loss is not execution failure.
8. No second scheduler, state machine, retry authority, or MCP gateway appears.

## Verification

Write tests first for the schema/contract guards, then make them pass.

Run at minimum:
- `pytest -q tests/test_desktop_commander_transport_contract.py tests/test_desktop_commander_runtime.py tests/test_runtime_catalog.py`
- `python -m compileall -q src/a_conductor`
- `git diff --check`
- static scan changed files for forbidden raw-authority words/fields and unexpected production imports.

Tests should parse the schema with stdlib `json`; do not add a dependency solely for schema validation. Assert required fields, fixed families, hard bounds, `additionalProperties: false`, and absence of forbidden payload fields.

## Delivery

Commit only allowed files on the assigned branch. Append exact RED/PASS evidence, branch/HEAD/dirty state, changed files, limitations, and next safe action here. Do not open/merge a PR. Stop after commit for integrator review.

N4 remains BLOCKED regardless of N3 completion until GE-005A, GE-6, and the GE-7 dispatch seam are independently proven ready on current main.
