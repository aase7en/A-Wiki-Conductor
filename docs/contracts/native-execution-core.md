# Native Execution Core Contract

Status: Phase 1 / first bounded implementation
Owner: A-Conductor
Classification against A-Wiki: `EXTEND`

## Boundary

A-Wiki remains authoritative for orchestration knowledge, routing policy, work-order/claim conventions, and cost/model intelligence. A-Conductor owns deterministic host execution and enforcement. Serena remains the semantic code specialist.

This core is intentionally **not** a generic chat shell. It is a low-level primitive consumed by explicit adapters and policy gates. An LLM proposal is never sufficient authority to execute arbitrary host commands.

## Filesystem contract

- One `NativeExecutionScope` binds execution to one absolute existing project root.
- Callers pass relative paths only.
- Resolution must stay inside the root after symlink resolution.
- Text reads have a byte limit and UTF-8 decoding.
- Directory listing is single-level and sorted deterministically.
- Text writes require `mutation_allowed=True`.
- New-file writes are atomic. Existing-file overwrite additionally requires the caller to provide the exact current SHA-256 digest, preventing stale or blind overwrite.
- No delete, move, rename, recursive copy, or cleanup primitive belongs to this first slice.

## Subprocess contract

- Command is an argv tuple/list, never a shell command string.
- `shell=False` is mandatory.
- Executable basename must be in the scope's explicit allowlist.
- Working directory is relative, existing, and confined to the project root.
- Timeout is required and bounded.
- Child environment inherits only conservative runtime keys; custom overrides are rejected unless their keys are explicitly authorized by the scope.
- stdout/stderr capture is bounded. Results include SHA-256 digests and truncation flags.
- The primitive returns code-only execution errors; it does not log/persist argv, environment values, or secrets.
- A `mutation_intent` flag is an authority assertion from a trusted adapter; a mutating command is refused if project mutation is not allowed. It is not a substitute for command-family-specific policy.

## Future adapters

The next layer should expose fixed-method adapters instead of forwarding raw model strings:

- Git adapter: status/diff/add/commit and later carefully gated mutation families.
- Test/build adapter: pytest/compile/build with known command shapes.
- Artifact adapter: deterministic file creation/export.
- Generic interactive shell, if ever added, requires a separate approval/policy design and is out of scope here.
