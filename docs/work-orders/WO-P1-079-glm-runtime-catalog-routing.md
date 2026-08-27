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
