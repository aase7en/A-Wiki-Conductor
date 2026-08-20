# WO-P1-045: Product Packaging + Serena Reference Notes

Status: complete
Lane/files: `README.md`, `pyproject.toml`, `docs/references/serena-configuration-notes.md`, `docs/work-orders/WO-P1-045-product-packaging.md`, `CURRENT-WORK.md`, `handoff.md`
Branch: chunk/p1-045-product-packaging (PR)
Model tier: high

## Goal

Make A-Wiki Conductor installable and runnable as a named program (`a-conductor`), document it, and durably capture the Serena configuration reference read on 2026-08-20 for future fork/copy-and-develop decisions.

## Reuse classification

`NEW (docs/packaging only)`: no runtime code touched; pure additive metadata and documentation.

## Acceptance

- `pyproject.toml` declares the package, console script `a-conductor`, and preserves pytest config.
- Root `README.md` covers what/requirements/install/run/develop/docs/agent-entry.
- `docs/references/serena-configuration-notes.md` captures the Serena configuration surface (layers, contexts, modes, SERENA_HOME, ls_specific_settings) with fork implications.
- `python -m a_conductor --smoke` passes against a temp database.
- Full test suite passes unchanged.

## Completion evidence

- smoke: `A-CONDUCTOR_SMOKE_OK projects=0 workers=3` (exit 0) against temp DB via `PYTHONPATH=src python -m a_conductor --smoke`.
- `python -m pip install --dry-run -e .` parsed project metadata without error.
- full suite: 741 passed, 1 skipped (display-dependent UI test), exit 0.
- no runtime/source module modified.

## Forbidden

- No runtime behavior change; no new dependency; no remote/visibility change.
