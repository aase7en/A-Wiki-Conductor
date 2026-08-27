# WO-P1-080 — GLM Desktop Commander bounded transport contract

Status: INTEGRATED_ACCEPTED
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

## Checkpoint — GLM implementation (2026-08-27)

Status: LOCAL_VERIFIED (worker claim; stopped for integrator review per delivery rule).

TDD RED: `tests/test_desktop_commander_transport_contract.py` (13 tests) all failed with `FileNotFoundError` before any schema/example/contract file existed.

Implementation summary (only the four allowed new files):

- `schemas/desktop-commander-operation.schema.json` (`urn:a-conductor:schema:desktop-commander-operation:1.0.0`, draft 2020-12, matching existing schema conventions): closed object (`additionalProperties: false`), exactly six required fields (`operation_ref`, `tool_family`, `project_id`, `mutation_intent`, `timeout_seconds` 1..3600, `max_output_bytes` 1..8,388,608) plus optional `device_id` (remote-only, fail-closed wording in its description). `tool_family` is a fixed closed enum of exactly the eight N3 families; no `REMOTE_SHELL`. `operation_ref` reuses operator.v1 opaque-identifier charset/pattern.
- `schemas/examples/desktop-commander-operation.example.json`: remote read-only `PROJECT_FILE_READ` definition with explicit `device_id` — pins the "read-only inspection first" recommendation mechanically.
- `docs/contracts/desktop-commander-bounded-transport.md`: REUSE + WRAP/EXTEND contract stating: reuse of operator.v1 `job.execute` opaque `operation_ref` and the native-operation allowlist pattern; does not create a second registry and does not create a second `operation_ref` namespace; no second scheduler/state machine/retry authority; ADR-0001 in force with no MCP gateway; no raw command/argv/shell/executable/env/prompt/SQL fields; four independent clamps (project identity, mutation intent, timeout, output budget) with 8 MiB hard output maximum and pagination beyond; device identity explicit-registered-only, fails closed, no discovery or polling; read-only inspection as recommended first remote capability; defense-in-depth guardrails are not A-Conductor's authorization boundary; durable execution ID before any side effect; transport loss is not execution failure (reuses resilient supervisor contracts); transport adapter gate unchanged; this slice adds no transport.
- `tests/test_desktop_commander_transport_contract.py`: 13 stdlib-only tests (json/re/pathlib/typing) covering parseability, closed-object + exact required set, recursive absence of 19 forbidden raw-authority property names, exact closed tool-family enum (REMOTE_SHELL excluded), two-state mutation intent, both numeric hard bounds, cross-check that the doc states the 8,388,608 maximum, device_id optionality + fail-closed description, example conformance + opaque-ref pattern, example-is-remote-read-only-first, and doc invariant anchor statements for acceptance items 1, 4, 5, 6, 7, 8.

Exact verification results (worktree `A:\GitHub\A-Wiki-Conductor-glm-dc-contract`, branch `feat/north-star-dc-contract-glm`, base `131a8b2`):

- `python -m pytest -q tests/test_desktop_commander_transport_contract.py tests/test_desktop_commander_runtime.py tests/test_runtime_catalog.py --basetemp=<isolated>` → **28 passed** (13 new contract + 4 existing DC runtime + 11 existing runtime catalog).
- `python -m compileall -q src/a_conductor` → PASS.
- `git diff --check` → PASS.
- Static scan: recursive property-name walk of the schema finds none of the 19 forbidden raw-authority field names; the new test file imports only stdlib `json`/`re`/`pathlib`/`typing`; no production imports or transport/MCP/network/process code introduced anywhere.

Files changed (only allowed scope): the four new files above plus this WO checkpoint section. Dirty state at commit: exactly those files; nothing else touched. No PR opened or merged.

Limitations:

- Contract + schema + mechanical guards only; no resolver/adapter code exists or is implied (live transport stays gated per the runtime contract's 8-point adapter gate and N6).
- `max_output_bytes` hard maximum (8 MiB) is a new documented bound chosen for this contract; it is not yet cross-wired to `MAX_ARTIFACT_READ_BYTES` (64 KiB) in `execution_artifacts.py` — the future adapter must reconcile per-page vs per-operation budgets.
- Doc anchor tests assert exact phrases; integrator may rephrase only together with the test update (kept in one commit for reviewability).

One next safe action: GPT-5.6 Sol reviews this contract against N3 acceptance (1-8) and the parent runtime contract; if accepted, the next bounded slice is the injected fake-backend adapter design (still no live transport), while N4 stays BLOCKED on GE gates.

## Integrator review — 2026-08-28

Verdict: `ACCEPTED / INTEGRATED`.

GPT-5.6 Sol independently reconciled the GLM commit against N3 acceptance and parent runtime authority, then integrated it into the North Star branch as commit `ac8ff93`.

Evidence:
- bounded changed scope remains exactly the N3 contract/schema/example/test files plus this WO;
- no production transport, MCP gateway, scheduler, job-state, UI, or A-Wiki mutation was introduced;
- opaque `operation_ref`, project identity, explicit mutation intent, timeout, output budget, and optional explicit `device_id` remain fail-closed contract inputs;
- runtime output budget mismatch (8 MiB operation maximum vs smaller artifact-read pages) remains an explicit future-adapter reconciliation item, not hidden behavior;
- `pytest -q tests/test_desktop_commander_transport_contract.py tests/test_desktop_commander_runtime.py tests/test_runtime_catalog.py` -> **28 passed**;
- `python -m compileall -q src/a_conductor` -> PASS;
- `git diff --check` -> PASS.

N3 is complete. N4 remains blocked until the accepted GE-6 scheduler and GE-7 durable dispatch implementation seam are both integrated on the applicable line.