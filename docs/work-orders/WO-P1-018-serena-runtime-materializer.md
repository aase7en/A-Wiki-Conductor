# WO-P1-018: Serena Runtime Materializer

Status: in_progress
Lane/files: `src/a_conductor/serena_materializer.py`, `src/a_conductor/__init__.py`, `tests/test_serena_materializer.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-018-serena-runtime-materializer.md`
Branch: main
Model tier: mid/high

## Goal

Implement bounded Serena runtime materialization for one pre-bound worker/assignment: resolve worker-owned mutable paths, render a runtime profile atomically from a read-only template/token map, and construct an `OwnedProcessSpec` for the runtime executable without starting any process.

## Acceptance

- tests first / RED before implementation;
- mutable output/run/log/Serena-home paths must remain under `instance_root`;
- template and runtime executable are read-only references and may live outside `instance_root`;
- health host must be loopback-only;
- renderer discovers `__[A-Z0-9_]+__` placeholders and requires an exact token mapping;
- missing/extra/blank/unsafe token values fail before output mutation;
- errors never include token values;
- output profile is written atomically under worker run dir;
- rendered profile content is never returned by public result objects;
- materializer constructs `OwnedProcessSpec` using direct executable argv + `--profile-file`; controller owns PID metadata, so product command does not ask child runtime to own the PID file;
- expected process fingerprint includes executable name + exact rendered profile path;
- no process/network/secret-store action in this work order;
- tests operate only in pytest temp roots;
- full suite + compileall + `git diff --check` pass.

## Validated template evidence

Read-only scan of current conductor/phase6 profile templates found the placeholder set `__TUNNEL_ID__` in both templates. No values were read into tracked source.

## Forbidden

- No live Serena/tunnel/A-Worker 3 mutation.
- No output outside worker instance root.
- No raw token values in exceptions/logs/results.
- No `shell=True`.
- No Git remote/push.

## Checkpoint log

- [2026-08-20] Opened after P1-017 commit `62b36bc`; worktree clean.
