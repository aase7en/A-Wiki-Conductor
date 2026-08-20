# Native Execution Fixed Adapters

Status: first fixed-method adapter layer
Owner: A-Conductor
Depends on: `docs/contracts/native-execution-core.md`

## Purpose

The native core is intentionally not a raw model-facing shell. This adapter layer converts approved high-level operations into fixed argv command shapes.

## Git read adapter

Allowed operations:
- short status
- working-tree diff
- cached diff

Every command:
- runs with `shell=False` through `NativeSubprocessRunner`;
- uses per-command `safe.directory=<bound project root>`;
- executes in the bound root;
- places any pathspecs after `--`;
- validates pathspecs are relative and confined to the project root.

Git mutation and network families are out of scope.

## Verification adapter

Allowed operations:
- `python -m pytest ...`
- `python -m compileall -q ...`

Verification paths must be existing root-confined paths. These commands set `mutation_intent=True` because test/build tools may create caches, bytecode, or other artifacts even when their logical purpose is verification.

## Future Git mutation layer

Stage/commit support must be a separate transaction design with explicit mutation authority and state preconditions (for example expected status/diff hashes). It must not be added by widening this read adapter with arbitrary args.
