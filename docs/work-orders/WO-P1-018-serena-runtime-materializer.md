# WO-P1-018: Serena Runtime Materializer

Status: completed
Lane/files: `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-018-serena-runtime-materializer.md`
Branch: main
Model tier: mid/high

## Goal

Implement bounded Serena runtime materialization for one pre-bound worker/assignment: resolve worker-owned mutable paths, render a runtime profile atomically from a read-only template/token map, and construct an `OwnedProcessSpec` without starting any process.

## Acceptance evidence

- RED: `ModuleNotFoundError: a_conductor.serena_materializer` before implementation.
- Mutable `serena_home`, `run_dir`, `log_dir`, profile/PID/log outputs confined under `instance_root`.
- Runtime executable/profile template treated as read-only external references.
- Loopback-only health host; IPv6 loopback URL bracketed correctly.
- Exact placeholder-token set required; invalid/missing/extra/newline/NUL token values rejected before output mutation.
- Known binding tokens (`WORKER_ID`, `PROJECT_PATH`, `SERENA_HOME`, health address) are checked if present.
- Sensitive token values are not retained in result objects or exception text.
- Profile write uses same-directory temporary file + fsync + atomic `os.replace`; failed replace cleans temporary file.
- `OwnedProcessSpec` command uses direct executable argv `run --profile-file <rendered-profile>` and intentionally omits child-owned `--pid.file`; A-Conductor owns PID metadata.
- Expected process fingerprint uses executable name + exact rendered profile path.
- Targeted tests: `19 passed`.
- Full suite: `293 passed in 4.05s`.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static scan: no subprocess/network/secret-store action.
- No live Serena/tunnel/A-Worker 3 mutation.

## Validated template evidence

Read-only scan of current conductor/phase6 profile templates found placeholder set `__TUNNEL_ID__` in both templates. No values were copied into tracked source.

## Checkpoint log

- [2026-08-20] Opened after P1-017 commit `62b36bc`.
- [2026-08-20] Coordination commit `b50c3fd`.
- [2026-08-20] RED module-missing checkpoint captured.
- [2026-08-20] GREEN targeted 19/19; full suite 293/293; materializer complete.
