# WO-P1-739 Tool / Hook / Skill Inspector

Issue: #739
Status: PREVIEW
Classification: R2 read-only projection and local discovery; no command authority.
Base: `a0eccf2` (orchestrator supplied; not independently checked in executor).
Worktree: `A:\GitHub\AWC-739-inspector`
Branch: `feat/739-inspector-v1` (orchestrator supplied).
Owner/scope: https://github.com/aase7en/A-Wiki-Conductor/issues/739#issuecomment-6737467325
Mutable scope: this WO, `src/a_conductor/inspector_projection.py`, `src/a_conductor/inspector_sources.py`, `tests/test_inspector_projection.py`, `tests/test_inspector_sources.py` only.
Round 2 scope extension: `src/a_conductor/monitor_projection.py`, `src/a_conductor/monitor_page.py`, `tests/test_monitor_page.py`.

## 1. Objective

Provide the read-only Tool / Hook / Skill Inspector slice 1 seam: pure bounded
presentation rows plus local source collectors. Round 1 supplied behavioral tests
and importable frozen dataclasses/enums with RED build/collect stubs. Round 2
implements those seams and adds the explicitly authorized minimal monitor
projection/page integration. Verification and GREEN acceptance remain pending.

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
Orchestrator must verify the supplied worktree/base/claim and authorized-scope diff,
retain RED evidence, and capture GREEN behavior without collection/import failure.

Verification commands (orchestrator only):

```text
py -3.13 -m pytest tests/test_inspector_projection.py -q
py -3.13 -m pytest tests/test_inspector_sources.py -q
py -3.13 -m pytest tests/test_inspector_projection.py::test_imports_are_pure -q
py -3.13 -m pytest tests/test_monitor_page.py -q
```

Evidence model: record exact-head RED then GREEN hashes and verification output.
RED commit hash: `00d91eb` (supplied by orchestrator, not independently checked).
RED test evidence: 82 failing tests reported by orchestrator; executor ran none.
GREEN commit hash: PENDING (orchestrator).
GREEN test evidence: PENDING.
Independent review / exact-head CI / post-main CI: PENDING (orchestrator gates).
This WO is the bounded slice checkpoint; shared CURRENT-WORK.md and handoff.md
are deliberately untouched because outside this executor's allowed scope.

## 7. Out Of Scope And Risks

NO gateway actions, NO writes to devices/connectors, NO new store/scheduler/router.
Desktop cockpit source-provider wiring remains deferred. Round 2 explicitly
authorizes monitor_projection.py / monitor_page.py / test_monitor_page.py changes
for an optional injected inspector view and rendering only; no live source wiring.
Local discovery imports subprocess for unrelated existing orchestration; GREEN
must invoke only discovery/health, never spawn. Health reads may fail or hang;
reuse existing bounded timeouts. Registry external paths, oversized/malformed
files, path traversal, freshness drift, and per-item read errors need fail-safe
handling during GREEN review. Static contract availability does not prove live
registration; fail-closed adapter emission is not GUARD authority. Test evidence
and line counts do not substitute for orchestrator verification or acceptance.

## 8. Round 2 Checkpoint

Implemented projection validation/redaction, frozen row models, bounded retained
counts, and source discovery/health/contract/registry reads. All collectors return
rows plus code-only notes, with per-item failure isolation and no source writes.
Registry reads are bounded, duplicate JSON keys rejected, and timestamps injected
for freshness tests. Repo-relative skill paths must resolve inside the explicit
root; external/home-relative/escaping paths stay UNKNOWN without metadata reads.
This is conservative local availability, not proof of cross-machine installation.
Additional source note: `TOOL_ENTRY_INVALID` for malformed discovered rows.

The optional monitor inspector is re-projected with an allowlist, bounded rows,
recomputed state counts, sanitized text, and preserved truncation evidence.
Absent is UNKNOWN; malformed is DEGRADED with INSPECTOR_PROJECTION_INVALID,
isolated from existing monitor views. The page adds one flat Inspector section,
three groups, explicit unknown/empty badges, and a disconnected badge class.
CSP, memory-only fragment token, and same-origin GET polling are unchanged.
The existing JS double-quote escape-map key was corrected to survive Python
string decoding; a page-byte regression assertion records that correction.

Purity test now walks reachable module imports through sys.modules as well as
checking the module namespace and AST. Existing behavioral assertions remain.
Static source self-review only: no Git, GitHub, pytest, shell, browser execution,
or other runtime verification. Exact HEAD/diff and all GREEN evidence belong to
the orchestrator. This checkpoint does not claim that tests or CI have passed.

## 9. Independent Review Repair Round

Review verdict: FAIL (four P1 findings) -> PENDING_RE_REVIEW.
Repair base: `2fb5642` (orchestrator supplied; no executor Git verification).

- P1-1, secret redaction: whole-value redaction now includes any Authorization
  header scheme and URL userinfo for any URI scheme, before text truncation.
  Marker matching uses NFKD, case folding, combining-mark removal, explicit
  cross-script confusable folding, and conservative non-ASCII assignment labels.
  NFKD alone does not convert Cyrillic lookalikes. Added projection and monitor
  re-projection regressions across name, last_error, routing_hint, and provenance.
- P1-2, oversized integers: integer last_verified values are accepted only in
  the documented inclusive -2**53 .. 2**53 range, with exact-int checks excluding
  bool. Both projection and monitor re-projection enforce that range without
  stringifying huge values. Added huge-positive/negative and endpoint tests;
  monitor regressions assert isolated DEGRADED, unchanged other views, and a
  successful json.dumps round trip instead of losing the whole snapshot.
- P1-3, unreadable marker isolation: the inspector now enumerates directories
  and parses each instance.ps1 independently using the shared marker/tunnel-ID
  regexes and LocalInstance type. This supersedes the earlier all-or-nothing
  discover_local_instances call; the shared local_instances.py is unmodified.
  Each bad marker is skipped with TOOL_MARKER_UNREADABLE:<hashed-name-suffix>;
  notes contain neither raw exception text nor directory credentials. Added
  good/unreadable/good survival and exact escaped-quote marker grammar tests.
  The existing root-discovery failure test now injects enumeration failure,
  retaining its assertions while targeting the new discovery seam.
- P1-4, probe error truth: only ConnectionError, TimeoutError, or OSError with
  ECONNREFUSED/ECONNRESET/EHOSTUNREACH/ETIMEDOUT establishes disconnection.
  PermissionError, FileNotFoundError, and unclassified OSError are DEGRADED with
  TOOL_PROBE_FAILED. Existing STOPPED/TRANSPORT_ERROR observations still map to
  DISCONNECTED. Added parameterized transport-versus-permission/config tests.

Regression tests were authored before the implementation repairs; no test or
shell command was executed by this executor. Orchestrator verification and
independent re-review are required before any PASS or acceptance claim.

## 10. Repair Round 2: Redaction Availability

Repair base: `c0be7d3` (orchestrator supplied; no executor Git verification).
Re-review reported the prior four P1 repairs satisfactory, but found a new P1:
unanchored URI/userinfo and Unicode-assignment regex alternatives repeatedly
scanned suffixes of long non-matching input, delaying monitor snapshots.
Verdict for this availability repair: PENDING_RE_REVIEW; no acceptance claim.

The raw free-text limit is now 4096 characters, inclusive. Longer values raise
INSPECTOR_PROJECTION_INVALID_INPUT before stripping, normalization, or scanning,
even when they contain secrets. Accepted fields are still redacted as whole
values before the existing 200-character display truncation.

Redaction no longer uses regex. Each accepted field undergoes one NFKD/casefold
normalization, combining-mark removal, and confusable fold, then str.split
whitespace tokenization. Per-token analysis uses fixed marker/prefix vocabularies:
Authorization headers and standalone Bearer evidence; URI authority boundaries
with @ before the following slash; share/private-key shapes; and assignment
labels split into disjoint colon/equal-delimited parts. Prefix searches advance
monotonically and inspect fixed windows of at most 32 characters, not unbounded
candidate suffixes. Cross-token state is bounded to 32 label characters plus
private-header flags. The number of passes is fixed; delimiter count cannot
induce nested suffix rescans or regex backtracking.

Added regressions for accepted/truncated 4096-character ASCII, pre-normalization
rejection at 4097 characters, a roughly 4000-character punctuation-heavy
non-secret, and whole-value redaction of secrets at character 300 in an
800-character field. Additional checks preserve spaced/embedded secret shapes
and distinguish URL-path @ from userinfo. Monitor regressions require isolated
DEGRADED on oversized input, unchanged sibling views, and JSON serialization;
the existing monitor exception boundary needs no implementation change.

Prior test assertions were not weakened or adjusted. Source review only; no
Git/GitHub/pytest/shell or runtime performance measurements were executed.
The orchestrator owns test execution, measured verification, and re-review.

## 11. Repair Round 3: Punctuation-Adjacent Bearer

Repair base: `9968855` (orchestrator supplied; no executor Git verification).
Re-review found a P1: quoted, parenthesized, or bracketed Bearer credentials
escaped the exact whitespace-token check. Verdict: PENDING_RE_REVIEW.

Bearer detection now makes one linear pass over the normalized whitespace
tokens, stripping a fixed punctuation set from both ends. A pending Bearer
marker redacts the whole field only when a subsequent similarly stripped token
is non-empty; punctuation-only tokens are skipped. A bare or wrapped bearer
word with no following credential remains unchanged. All other matcher logic,
monotonic prefix windows, normalization, and the 4096-character cap are retained;
no regex was introduced.

Added projection and raw-monitor regressions for quoted, parenthesized,
bracketed, error-prefixed, and trailing-punctuation credentials in both name
and last_error. Additional cases cover intervening punctuation-only tokens and
the no-credential negative at both boundaries, including JSON-safe output.
The WO update is append-only. No Git/GitHub/pytest/shell or runtime verification
was performed; test execution and independent acceptance remain orchestrator gates.

## 12. Repair Round 4: Literal Marker Recognition

Repair base: `e52d9a6` (orchestrator supplied; no executor Git verification).
Re-review found that token-end punctuation stripping still missed embedded
Bearer markers in message assignments, error wrappers, and hyphen wrappers.
Verdict: PENDING_RE_REVIEW. This replaces the earlier word-marker strategy,
rather than adding more token-boundary special cases.

The 4096-character raw limit remains before all scanning. A field receives one
NFKD/casefold/combining-mark/confusable normalization; whitespace is canonicalized
from its token list. One module-level compiled _MARKERS_RE is searched exactly
once against that normalized field. Its pattern consists solely of literal
marker alternatives enclosed by word boundaries. Hyphenated, underscored,
compact, and spaced API/access-key spellings are explicit literal alternatives;
there are no character classes, repetition quantifiers, or variable-length
prefixes in the regex. The prior suffix/label/Bearer token-vocabulary rules are
removed. Fixed-length alternatives bound matching work per input position.

A match redacts the entire field when its tail contains a non-empty following
token after fixed punctuation stripping, or a non-empty value after colon/equal
within the next 32 characters. This tail is examined once with a fixed number
of passes, never per regex match. Structural Authorization, URL-userinfo,
share/private-key, and monotonic fixed-window credential-prefix checks remain.
Redaction still precedes the 200-character display truncation; a bare bearer
without payload remains unchanged.

Added projection and raw-monitor regressions for all three embedded reproductions
in name/last_error and projection routing_hint. Additional tests require a regex
containing only word boundaries and literal alternatives, and one marker-search
call for a normalized field. All prior assertions remain intact, including
Basic auth, userinfo, Unicode markers, beyond-200 redaction, wrapped Bearer,
bare-Bearer negatives, cap boundaries, and punctuation-heavy non-matches.
The WO change is append-only. No Git/GitHub/pytest/shell or runtime verification
was performed; verification and independent acceptance remain orchestrator gates.

## 13. Repair Round 5: Assignment Label Families

Repair base: `bd23970` (orchestrator supplied; no executor Git verification).
Re-review found that word boundaries do not split underscore-prefixed assignment
labels, allowing access_token, refresh_token, and OPENAI_API_KEY reproductions.
Verdict: PENDING_RE_REVIEW.

The _MARKERS_RE declaration and pattern are byte-identical to round 4; its one
search per normalized capped field is unchanged. An additional linear pass reuses
the same normalized whitespace tokens. Each token is split at its first colon
or equals; surrounding fixed punctuation/quotes are stripped from label and
payload. A non-empty payload plus label.endswith against a fixed vocabulary
redacts the whole field. The vocabulary contains marker families, not provider
names. There is no new regex, variable-length regex scan, or repeated suffix scan.
The 4096 cap, normalization, structural checks, and display truncation remain.

Added projection and raw-monitor regressions for access_token, refresh_token,
OPENAI_API_KEY, session_secret, SERVICE_PASSWORD, and wrapped/quoted assignments.
Negatives pin monitored=1, key_count=5, and prefixed secret labels with empty
payloads. A dedicated regression pins the unchanged literal-marker regex.
Existing assertions remain intact. This WO section is append-only; no
Git/GitHub/pytest/shell or runtime verification was performed by the executor.
