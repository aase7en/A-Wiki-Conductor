# WO-P1-079 — GLM runtime catalog + deterministic routing slice

Status: READY_FOR_GLM
Owner: GLM 5.3 MAX (bounded implementation); GPT-5.6 Sol = integrator/reviewer
Parent: WO-P1-078 / N2
Repository: `aase7en/A-Wiki-Conductor`
Target worktree: `A:\GitHub\A-Wiki-Conductor-glm-northstar-runtime`
Target branch: `feat/north-star-runtime-catalog-glm`

## Goal

Implement the non-UI, pure-Python N2 runtime catalog/routing seam so Desktop Commander can be represented as an optional execution runtime without launching it, while keeping A-Wiki and A-Conductor authority unchanged.

## Read first

1. `AGENTS.md`
2. `PROJECT-PLAN.md` sections 15-19
3. `COLLAB.md`
4. `CURRENT-WORK.md` and `handoff.md` for conflicts only
5. `docs/work-orders/WO-P1-078-north-star-execution-plan.md`
6. `docs/work-orders/WO-P1-077-desktop-commander-runtime-profile.md`
7. `docs/contracts/desktop-commander-runtime.md`
8. `DEFECT_LESSONS.md`

## Repository safety / ownership

Before mutation verify repo, worktree, branch, HEAD, dirty state, remote and worktrees.

Allowed mutable scope ONLY:
- `src/a_conductor/runtime_catalog.py` (new)
- `tests/test_runtime_catalog.py` (new)
- this WO checkpoint section only

Forbidden:
- all `src/a_conductor/graph/**`
- `registry.py`, `domain.py`, scheduler/dispatch/job-state files
- UI/assets/DESIGN
- `PROJECT-PLAN.md`, `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`
- PR #102 / PR #104 worktrees/branches
- A-Wiki repository
- live connector ports/processes
- dependency/lock files

If the goal cannot be achieved within allowed files, stop with `BLOCKED` and explain the smallest additional seam required. Do not broaden scope yourself.

## Required behavior

Create a pure metadata catalog/selector with no I/O.

1. Define explicit availability states: `INSTALLED`, `AVAILABLE`, `UNAVAILABLE`, `UNKNOWN`.
2. Catalog entries must carry `Runtime`, `ExecutionSurfaceTraits`, availability, and stable runtime-family identity.
3. Catalog construction/selection must never probe filesystem, processes, network, MCP, Node, or devices.
4. Desktop Commander readiness is supplied observation; configuration/profile existence alone must never imply AVAILABLE.
5. Capability matching is deterministic and uses exact capability names.
6. Selection order when several AVAILABLE candidates satisfy the request:
   - native/fixed deterministic runtime first when sufficient;
   - Serena before Desktop Commander for semantic-code capability;
   - Desktop Commander only when interactive/long-running/remote-device capability materially requires it.
7. `UNKNOWN`, `UNAVAILABLE`, or merely `INSTALLED` candidates must not be selected as executable-ready.
8. Stable lexical runtime-id tie-break within the same priority.

## TDD + acceptance

Write failing tests first, then minimal implementation.

Acceptance tests must prove:
- explicit availability transition semantics are fail-closed;
- unavailable/unknown/installed-only Desktop Commander is never selected;
- remote Desktop Commander is selectable only when AVAILABLE and `remote.device` is requested;
- deterministic native-first selection for overlapping fixed capabilities;
- semantic Serena preference is representable without importing Serena runtime I/O;
- lexical tie-break is stable;
- empty/no-match result is explicit (`None` or a small typed result), never a guessed runtime;
- module import and selector call have zero external side effects.

Do not implement transport, MCP calls, subprocess launch, scheduler dispatch, persistence, UI, or remote discovery.

## Verification

Run at minimum:
- `pytest -q tests/test_runtime_catalog.py tests/test_desktop_commander_runtime.py tests/test_domain.py`
- `python -m compileall -q src/a_conductor`
- `git diff --check`
- inspect the final diff for I/O/background/transport dependencies that violate this pure-metadata slice.

Use an isolated pytest `--basetemp` if shared temp cleanup causes `WinError 5`; record that as environment evidence rather than changing product code.

## Delivery

Commit only the bounded allowed files on the assigned branch. Append checkpoint evidence here: RED test, implementation summary, exact test results, branch/HEAD/dirty state, files changed, limitations, and one next safe action.

Do not open or merge a PR unless the integrator later asks. Worker DONE is a claim until independently reconciled.

## Checkpoint — GLM implementation (2026-08-27)

Status: LOCAL_VERIFIED (worker claim; awaits independent reconciliation).

Readiness note: the assigned worktree/branch did not exist at first attempt; GLM correctly stopped BLOCKED (read-only verification, no mutations). The integrator then settled the lane (commit `d5537c9` committed this WO + WO-P1-078 checkpoint on `feat/north-star-runtime-sunday-family`) and created the assigned worktree/branch before implementation started.

Environment evidence (recorded, product code unchanged):

- Isolated pytest `--basetemp` used for every run per WO; no `WinError 5` encountered.
- The local `python` on PATH is a hermes-agent venv (3.11.15) whose interpreter cannot combine `sys.addaudithook` with bytecode compilation — even `import json` under a no-op audit hook fails (`AttributeError: 'bytes' object has no attribute 'co_filename'` in `_compile_bytecode`). An audit-hook subprocess purity gate is therefore non-deterministic on this machine. Purity is instead proven deterministically by (a) an AST import-allowlist test pinning the module's static import surface to `dataclasses`/`enum`/`collections.abc` + the two pure `a_conductor` metadata modules, and (b) a poisoned-callable test that replaces `builtins.open`/`os.system`/`subprocess.Popen`/`socket.socket` with raisers before `importlib.reload` of the module and then exercises construction + selection across all three families.

TDD RED: `tests/test_runtime_catalog.py` (10 tests at authoring time) all failed with `ModuleNotFoundError: No module named 'a_conductor.runtime_catalog'` before implementation.

Implementation summary (new `src/a_conductor/runtime_catalog.py`, pure metadata only):

- `RuntimeAvailability` explicit states: `INSTALLED` / `AVAILABLE` / `UNAVAILABLE` / `UNKNOWN`; only `AVAILABLE` is executable-ready.
- `RuntimeCatalogEntry` carries domain `Runtime`, `ExecutionSurfaceTraits`, availability, and a stable `runtime_family` (`native` / `serena` / `desktop-commander`, the latter matching the existing `runtime_type` from WO-P1-077).
- `mark_availability` is fail-closed: entering `AVAILABLE` requires a supplied `RuntimeObservation`; `INSTALLED`/profile existence never implies readiness.
- Helpers reuse the existing pure profile: `desktop_commander_entry` (defaults `UNKNOWN`) wraps `build_desktop_commander_profile`; `native_entry`/`serena_entry` are pure domain metadata (semantic-code = `semantic.code` capability).
- `select_runtime` — exact case-sensitive capability-name matching, empty request → `None`, no-match → `None` (never a guessed runtime); eligibility: `AVAILABLE` only, full request subset, remote-advertising entries selected only when `remote.device` is requested, desktop-commander family only when the request intersects `{process.interactive, process.long-running, remote.device}`; ranking native → serena → desktop-commander with stable lexical `runtime_id` tie-break independent of catalog insertion order.
- No transport, MCP calls, subprocess launch, scheduler/dispatch, persistence, UI, or remote discovery.

Exact verification results (worktree `A:\GitHub\A-Wiki-Conductor-glm-northstar-runtime`, branch `feat/north-star-runtime-catalog-glm`, base `d5537c9`):

- `python -m pytest -q tests/test_runtime_catalog.py tests/test_desktop_commander_runtime.py tests/test_domain.py --basetemp=<isolated>` → **32 passed** (11 new catalog tests + 4 existing DC runtime + 17 existing domain).
- `python -m compileall -q src/a_conductor` → PASS.
- `git diff --check` → PASS.
- Static scan of the new module for `subprocess|socket|open(|threading|Timer|asyncio|requests|urllib|Popen|os.system|sleep|while|poll` → zero matches.

Files changed (only allowed scope): `src/a_conductor/runtime_catalog.py` (new), `tests/test_runtime_catalog.py` (new), this WO checkpoint section.

Dirty state at commit: exactly the two new files above plus this checkpoint edit; nothing else touched. No PR opened or merged.

Limitations:

- Availability is supplied observation only; no slice here observes anything (by design).
- The hermes-venv audit-hook defect means the subprocess-based zero-side-effect gate cannot run locally; a stock interpreter (e.g. CI) may reintroduce it if desired.
- `semantic.code` is catalog vocabulary for the Serena preference seam; it is not yet wired to any Serena engine capability source.

One next safe action: integrator review/reconcile this branch against N2 acceptance (near-zero idle cost, no new task state machine, runtime-neutral domain intact), then decide whether N3 (bounded DC transport contract) may start in an additive seam.
