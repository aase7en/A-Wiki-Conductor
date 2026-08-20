# WO-P1-022: Tunnel Reference + Strict Preflight Boundaries

Status: in_progress
Lane/files: `src/a_conductor/tunnel_boundaries.py`, `src/a_conductor/owned_process.py`, `src/a_conductor/__init__.py`, `tests/test_tunnel_boundaries.py`, `tests/test_owned_process.py`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-022-tunnel-preflight-references.md`
Branch: main
Model tier: high

## Goal

Implement secret-safe local reference/token resolution and a strict bounded `tunnel-client doctor --profile-file ... --explain` preflight service without starting a long-lived runtime.

## Acceptance

- tests first / RED before implementation;
- worker keeps opaque `tunnel_binding_ref`; concrete reference store maps opaque IDs to local files externally;
- reference file values are read only, trimmed, single-line, non-empty, NUL-free; errors expose codes only, never values;
- token provider discovers actual template placeholders and returns only required tokens;
- derived tokens (`PROJECT_PATH`, `SERENA_HOME`, health address, worker ID) are generated locally when requested;
- `__TUNNEL_ID__` resolves through opaque reference store;
- unknown placeholder fails closed before materialization;
- child environment builder is shared with owned-process spawner and remains allowlisted;
- preflight uses exact executable + `doctor --profile-file <path> --explain`, `shell=False`, bounded timeout, safe child env;
- preflight stdout/stderr are not returned in lifecycle result;
- timeout/exit failure map to stable redacted codes;
- no long-lived process, no Git mutation, no live A-Worker 3 mutation;
- full suite + compileall + diff/static scan pass.

## Forbidden

- No raw tunnel/credential values in tracked files, errors, evidence, or logs.
- No arbitrary command arguments/subcommands.
- No whole-parent environment passthrough.
- No live tunnel provisioning/start.
- No Git remote/push.

## Checkpoint log

- [2026-08-20] Opened after P1-021 commit `d6589a7`; worktree clean.
