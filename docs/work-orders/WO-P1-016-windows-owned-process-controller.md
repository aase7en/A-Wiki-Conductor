# WO-P1-016: Windows Owned-Process Controller

Status: completed
Lane/files: `src/a_conductor/owned_process.py`, `src/a_conductor/__init__.py`, `tests/test_owned_process.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-016-windows-owned-process-controller.md`
Branch: main
Model tier: mid/high

## Goal + Acceptance criteria

Implement the first production host-mutation primitive: a Windows owned-process controller that may spawn or stop **only an exactly owned process** and may write/delete PID/log metadata **only inside an explicitly allowed runtime root**. Integration tests must target only the Stage A dummy runtime.

Acceptance:
- tests written before implementation;
- inspect validated prototype start/stop ownership pattern read-only before implementation;
- `OwnedProcessSpec` validates command/profile marker and all mutable paths under one allowed root;
- start uses argv list + `shell=False`; no arbitrary shell string;
- start is idempotent when PID metadata points to an already-owned process;
- invalid/stale/mismatched/unknown PID ownership never causes blind duplicate spawn;
- PID metadata is written atomically after spawn;
- if PID metadata persistence fails after spawn, controller attempts cleanup only through the exact child handle it just created and reports recovery if cleanup cannot be proven;
- stop reads PID metadata and terminates only when observer proves `OWNED` for expected executable/profile marker;
- mismatch/unknown ownership refuses stop; stale metadata requires recovery and is not silently deleted;
- after proven exit, only controller-owned PID metadata may be removed;
- concrete Windows terminator targets an integer PID only with `shell=False`;
- path traversal/out-of-root mutation is rejected before process spawn/stop metadata changes;
- real integration tests use only harness-owned dummy child process;
- post-test active Conductor PID/health remain unchanged within an atomic preservation run;
- full tests, compileall, `git diff --check`, and mutation-command review pass.

## Reference pattern

- `docs/contracts/lifecycle-integration-test-strategy.md` Stage A.
- `docs/contracts/serena-runtime-manager.md` ownership/start/stop rules.
- `src/a_conductor/windows_observer.py` + `runtime_safety.py` for exact ownership classification.
- validated external start/stop scripts: read-only evidence only.

## Steps

1. Commit coordination checkpoint.
2. Inspect validated external start/stop ownership/termination pattern read-only.
3. Write failing unit/integration tests first.
4. Capture RED result.
5. Implement `OwnedProcessSpec`, result states, exact-PID terminator, and controller.
6. Run targeted tests against Stage A dummy runtime only.
7. Verify active Conductor PID/health unchanged.
8. Run full suite + compileall + diff/mutation-command review.
9. Update checkpoint/current-work/handoff and commit.

## Forbidden

- No broad process-name termination.
- No target PID accepted from unvalidated free-form shell input.
- No `shell=True`.
- No writes outside the controller's explicit allowed root.
- No automatic stale/mismatch PID-file deletion before reconciliation.
- No Serena/tunnel/A-Worker 3 mutation.
- No writes to `serena-test`, A-Wiki, Phase6, or external runtime roots.
- No Git remote/push.

## Verification evidence

- Coordination commit before implementation: `b0f8762`.
- Prototype scan found targeted `Stop-Process`/PID metadata handling and no `taskkill` primitive in the validated reference scripts.
- RED: targeted tests failed with `ModuleNotFoundError: a_conductor.owned_process` before implementation.
- Test-fixture repair: shell-quoting-created literal `\\n` line was corrected; real integration switched from the Hermes venv launcher to the base CPython executable so the observed runtime PID equals `Popen.pid`, matching the direct-executable production contract.
- Targeted P1-016 tests: `16 passed`.
- Full suite: `250 passed in 4.60s`.
- `python -m compileall -q src tests`: PASS.
- `git diff --check`: PASS.
- Broad-kill scan: no `taskkill`, `shell=True`, `Stop-Process -Name`, or broad kill pattern in `owned_process.py`.
- Atomic active-worker preservation run: Conductor PID `25396` before and after targeted integration; tests `16 passed`; `/readyz` independently verified HTTP 200 around the verification period.
- GitHub connector access was attempted because the user requested `@GitHub`, but the platform returned `FORBIDDEN: This conversation is restricted to developer MCPs`; local repo also has no remote configured. No GitHub write was attempted.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after Stage A dummy-runtime integration commit `bf9d1eb`. Production mutation permitted only against test-owned dummy resources in this work order; Stage B Serena/tunnel remained gated.
- [2026-08-20] Read-only prototype primitive inventory: targeted `Stop-Process` and local metadata cleanup; no broad `taskkill` primitive found.
- [2026-08-20] RED checkpoint: production module absent.
- [2026-08-20] GREEN: exact-owned process controller complete; targeted 16/16, full suite 250/250, preservation gate passed. Work order closed.
