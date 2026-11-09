# WO-P1-739 Tool / Hook / Skill Inspector

Issue: #739
Status: PREVIEW
Classification: R2 read-only projection and local discovery; no command authority.
Base: `a0eccf2` (orchestrator supplied; not independently checked in executor).
Worktree: `A:\GitHub\AWC-739-inspector`
Branch: `feat/739-inspector-v1` (orchestrator supplied).
Owner/scope: https://github.com/aase7en/A-Wiki-Conductor/issues/739#issuecomment-6737467325
Mutable scope: this WO, `src/a_conductor/inspector_projection.py`, `src/a_conductor/inspector_sources.py`, `tests/test_inspector_projection.py`, `tests/test_inspector_sources.py` only.

## 1. Objective

Provide the read-only Tool / Hook / Skill Inspector slice 1 seam: pure bounded
presentation rows plus local source collectors. This round supplies complete
behavioral tests and importable frozen dataclasses/enums with RED build/collect
stubs only. Every build/collect function raises
`NotImplementedError("INSPECTOR_SLICE_1_RED")`; GREEN implementation is deferred.

## 2. Failure Model

Registration is not start, connection, injection, or runtime readiness (#343).
Only a health observation can establish tool READY. File/contract presence never
establishes live hooks; their runtime state stays UNKNOWN. Skill AVAILABLE means
registry entry plus an existing skill path, never runtime READY or authorization.
Stale data, transport failures, malformed input, and unavailable sources remain
visible without optimistic promotion. No raw secrets or exception text may leak.

## 3. Acceptance Criteria

- `tests/test_inspector_projection.py`: enums, frozen rows, unknown clamping,
  all five states, skill-only AVAILABLE, per-section 128-row drop-oldest bounds,
  redaction before truncation, 200-character text caps, hostile input, scalar
  validation, retained-state counts, provenance, fixed-NOW determinism.
- `tests/test_inspector_sources.py`: exact PowerShell discovery markers,
  injectable dead/ready/unknown probes, explicit discovery-only, omitted-probe
  health reuse, per-item degradation, contract presence versus hook liveness,
  missing/malformed contracts, real schema-v3 registry fixtures, missing and
  unreadable registry, missing skill path, mtime freshness, duplicate/deprecated
  rows, invalid-neighbor survival, unchanged fixture bytes and mtimes.
- Projection purity: no I/O-bearing imports; banned roots are subprocess,
  socket, urllib, sqlite3, shutil, requests, http. Namespace and AST import gates
  follow the command-gateway purity pattern and reject relative project imports.
- All collector tests are offline, fixture-owned, Windows-safe, no conftest.
- Code-only projection failures use `InspectorProjectionError.code` equal to
  `INSPECTOR_PROJECTION_INVALID_INPUT`; invalid input never becomes READY.
- GREEN collectors use stdlib and existing discovery/health seams only, never
  write, spawn, read credentials beyond discovery's existing pairing check, or
  expose a tunnel ID. UNKNOWN, STALE, DISCONNECTED, DEGRADED are first-class.

## 4. Reuse-Before-Build Audit

Read-only source inspection in this worktree covered provider operator rows,
command-gateway purity/tests, local instance discovery and health, instance
monitoring, Drive-root resolver, control-hook header/constants, hook JSON schema,
Claude/Kilo adapter contracts, provider-view tests, and monitor API conventions.
No new store, router, scheduler, event bus, or live hook registry is introduced.
Reuse `local_instances.discover_local_instances` and `instance_health_state`;
do not import the orchestration class or call any start/stop path.
The supplied A-Wiki repo root is explicit; resolving a private Drive/env layer
is unnecessary for the public registry and must not load secret env files.

Canonical A-Wiki data observed read-only: `A:\GitHub\A-Wiki\skills-registry.json`.
Authority/loader: `A:\GitHub\A-Wiki\scripts\skills_registry\__init__.py`.
Routing consumer: `A:\GitHub\A-Wiki\scripts\skills_registry\routing.py`.
Scanner: `scripts/skills_registry/scan.py` produces drafts, not another authority.
Top-level shape: object with `schema_version: 3`, `generated_at: str`, `skills: list`.
Required entry fields: `name`, `domain`, `lifecycle_phase`, `category`, `source`,
`path`, `status`. Observed optional fields include `aliases`, `agents`, `version`,
`description`, `invocation`, `invocation_hint`, `a_phase`, `triggers`,
`th_description`, `when_to_use`, `examples` (scenario/how objects),
`process_steps`, `migrated_to`; loader also supports `canonical` on aliases.
Harness compatibility comes from `agents: list[str]` (including `all`), routing
from `triggers: list[str]` and optional invocation hint. `status` vocabulary is
`canonical`, `alias`, `deprecated`; deprecated is derived from status, not an
invented boolean. Duplicate is derived from repeated names, not alias status.
Paths can be repo-relative or external; this slice tests repo-relative fixtures.

## 5. Frozen Test Contract

`build_inspector_views` returns tools/hooks/skills sections of serialized row
dictionaries plus summary. `summary.generated_at` is the supplied aware UTC
datetime's `isoformat()`. Each section summary has `counts` (by retained state),
`truncated: bool`, and `dropped: int`; input order defines oldest, not timestamps.
Validate every row, including rows discarded by the display bound.
InspectorState retains exactly READY/UNKNOWN/STALE/DISCONNECTED/DEGRADED;
SkillInspectorRow additionally accepts string AVAILABLE. Unknown hook classes
and fail modes render UNKNOWN, never silently choose an authority class.

Collectors consistently return `(tuple(rows), tuple(degraded_notes))`, including
tools, to expose discovery-wide failures without exceptions. Notes are code-only:
`TOOLS_DISCOVERY_UNAVAILABLE`, `TOOL_PROBE_TRANSPORT_ERROR`, `TOOL_PROBE_FAILED`,
`HOOK_CONTRACT_UNAVAILABLE`, `HOOK_CONTRACT_INVALID`,
`SKILLS_REGISTRY_UNAVAILABLE`, `SKILL_ENTRY_INVALID`.
An injected tool probe is callable `(LocalInstance) -> InstanceHealthState`.
Transport exceptions yield DISCONNECTED; unexpected failures yield DEGRADED.
An omitted probe (Ellipsis sentinel) means the real existing health checker;
explicit `probe=None` disables probing and means discovery-only. This resolves
the supplied design's conflict between a real default and explicit no-probe.
Configured + READY is CONNECTED; unconfigured + READY is STARTED; otherwise
discovery establishes REGISTERED only. Injection is never inferred.

Static rows are named `HookBus:<class>`, `control-hook-adapter`,
`claude-hook-adapter`, `kilo-hook-adapter`. All carry contract version 1.0.0
in authority_source and provenance contract-only. HookBus classes come from
schema properties.hook_class.enum; the control row uses its source header.
GUARD FAIL_CLOSED requires explicit policy evidence from hook-contract-v1.md
when present; a schema permitting FAIL_OPEN and FAIL_CLOSED alone is UNKNOWN.
OBSERVE adapter version/capability fail-closed gates do not imply GUARD policy.

Skill provenance is registry-only; registry_source is `skills-registry.json`.
`now` is injectable for deterministic skill freshness; max_age_seconds defaults
to 604800. Age greater than the threshold is STALE for existing skill paths;
missing paths remain UNKNOWN even if the registry is stale. The JSON
generated_at is not the freshness clock. No A-Wiki Python package is imported.

## 6. Delivery Gates

Only the orchestrator runs Git, GitHub, shell commands, verification, and commits.
Executor did not independently verify actual HEAD/dirty/claim status and grants
no new claim, review, merge, acceptance, runtime, or cross-repo authority.
Orchestrator must verify the supplied worktree/base/claim and exact five-file diff,
then capture RED behavior as NotImplementedError, not collection/import failure.

Verification commands (orchestrator only):

```text
py -3.13 -m pytest tests/test_inspector_projection.py -q
py -3.13 -m pytest tests/test_inspector_sources.py -q
py -3.13 -m pytest tests/test_inspector_projection.py::test_imports_are_pure -q
```

Evidence model: record exact-head RED then GREEN hashes and verification output.
RED commit hash: PENDING (orchestrator).
RED test evidence: PENDING (not run by executor).
GREEN commit hash: PENDING (later implementation round).
GREEN test evidence: PENDING.
Independent review / exact-head CI / post-main CI: PENDING (orchestrator gates).
This WO is the bounded slice checkpoint; shared CURRENT-WORK.md and handoff.md
are deliberately untouched because outside this executor's allowed scope.

## 7. Out Of Scope And Risks

NO gateway actions, NO writes to devices/connectors, NO new store/scheduler/router.
Desktop cockpit integration and monitor_projection.py / monitor_page.py /
test_monitor_page.py changes are deferred to the next slice.
Local discovery imports subprocess for unrelated existing orchestration; GREEN
must invoke only discovery/health, never spawn. Health reads may fail or hang;
reuse existing bounded timeouts. Registry external paths, oversized/malformed
files, path traversal, freshness drift, and per-item read errors need fail-safe
handling during GREEN review. Static contract availability does not prove live
registration; fail-closed adapter emission is not GUARD authority. Test evidence
and line counts do not substitute for orchestrator verification or acceptance.
