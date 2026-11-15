# WO-P1-757 — SFU26 Card 09: Provider/Model/Scout Freshness Projection

Identity schema: GITHUB_ISSUE_V1
Issue: #757
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (consume-only read projection; no refresh/purchase/activation; no provider config change; no readiness grant)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `2661ee4d3c63887df3110b056e83f5bd908a845c` (origin/main verified at bootstrap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo757-freshness`; branch `feat/wo757-model-freshness`.
- Program authority: SFU26 roadmap card `CAND-SFU26-09` (after cards 06/08 delivered; plan order 09→07→10).
- Exclusive files: NEW `src/a_conductor/model_artifact_freshness_projection.py`, NEW `tests/test_model_artifact_freshness_projection.py`, this WO. `provider_operator_view.py` and every existing module UNTOUCHED (scope note on #757 records the boundary: provider-observation readiness is a separate evidence domain from A-Wiki artifact freshness).

## Verified Inputs (discovery 2026-11-15)

- No AWC code reads any A-Wiki model artifact today (zero grep hits in src/ and tests/) — card 09 creates the first reader.
- Artifact set + decision-input map (mirror in report metadata): `.tmp/model-scout-current.json` → policy TIER1/TIER2 PRIMARY + RACE override (`generated_at` offset-ISO; `volatile`/`offline` flags; recommendations{} may be EMPTY — type it, never fabricate); `wiki/context/model-roster.conf` → policy tier slots/fallbacks/TIER3/RACE base/pinned (flat KEY="VALUE", header `Generated:` date); `.tmp/model-router-policy.conf` → composed policy (naive-local `MODEL_ROUTER_POLICY_GENERATED_AT`, `MODEL_SCOUT_GENERATED_AT` echo, `MODEL_IDS_ARE_SEEDS`); `.tmp/model-catalog.json` → model_match tier/price matrix (may be near-empty: `model_count: 0`); `.tmp/model-capability-cache.json` → capability scores by family (`as_of`, `confidence: "training"`, `base:` pointer). Real-world drift exists (policy generated 2026-08-20 while roster regenerated later) — the report must surface cross-artifact divergence honestly.
- No secret-shaped content in artifacts; machine-local paths exist and MUST NOT be echoed into output (scrub/omit raw paths).
- Vocabulary precedent: staleness `AVAILABLE/STALE/UNKNOWN` (mtime-based; future-dated → UNKNOWN) from inspector chain + card-06-style state+reason pairs for per-artifact detail.

## Deliverables

1. **NEW pure module** (no clock/network/store I/O beyond injected loader; injectable `now`; no provider imports; no write paths — structurally cannot refresh or pin anything): `project_model_artifact_freshness(snapshot, *, now=None) -> ModelIntelFreshnessReport` over an injectable artifact snapshot (duck-typed or loader-callable per card-08 pattern) containing per-artifact records:
   - artifact key, decision-input role (from map above), read state (`AVAILABLE`/`ABSENT`/`UNPARSEABLE`/`UNREADABLE` with reason code), mtime staleness label (`AVAILABLE`/`STALE`/`UNKNOWN` by injectable per-artifact `max_age_seconds` defaults, documented; future mtime → UNKNOWN), file age seconds, embedded `generated_at`/`Generated:`/`as_of` raw string + parse state (`PARSED_OFFSET`/`PARSED_NAIVE_LOCAL`/`UNPARSEABLE` — handle BOTH formats; naive-local never silently converted to UTC), embedded flags (`volatile`, `offline`, `confidence`, `model_count`, `MODEL_IDS_ARE_SEEDS`) carried typed, content revision fingerprint (sha256 of raw bytes), size bytes.
   - recommendation-emptiness typed: scout/catalog present-but-empty stays a valid AVAILABLE record with `recommendations_empty: true` / `model_count: 0` — never fabricated, never treated as failure.
   - cross-artifact observations: roster-regenerated-after-policy (drift), scout-echo mismatch (policy `MODEL_SCOUT_GENERATED_AT` vs scout's own `generated_at`), seeds-active warning (`MODEL_IDS_ARE_SEEDS=1`) — each a typed note with the compared values; comparisons only when both sides parse.
   - report carries `non_authoritative: True` (init=False pinned), no raw paths in any output field, and no readiness/exec vocabulary anywhere.
2. **NEW tests** (inline fixtures, no tests/fixtures additions): axes — per-artifact AVAILABLE/STALE(by injected threshold)/future-UNKNOWN/ABSENT/UNPARSEABLE/UNREADABLE; both timestamp formats parse-state; naive-local NOT UTC-converted (assert raw preserved + labeled); empty-scout/empty-catalog typed-not-failed; drift detection (roster newer than policy → note with values); scout-echo mismatch; seeds warning; no-raw-path assertion (fixture embeds a `/Users/...` path; assert absent from repr/str of report); loader-injection failure → typed degraded report (not exception); zero-provider-import structural test; frozen+slots dataclasses; purity (no time/network/subprocess in module).

## Acceptance

- RED-first: ModuleNotFoundError + behavioral RED (projection API missing) recorded verbatim.
- Per-file green: `tests/test_model_artifact_freshness_projection.py`, plus regression neighbors `tests/test_provider_operator_view.py`, `tests/test_work_order_identity.py` (incl. this WO); `python3 -m compileall -q src/a_conductor`; no npm changes; no existing module touched (diff = 3 files only).
- Delivery gate: frozen local commit → independent review → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI (macOS capacity rerun precedent) → checkpoint + close on #757.

## Checkpoint

- 2026-11-15: lane bootstrapped @`2661ee4`; issue #757; discovery recorded; implementation pending.
- 2026-11-15: implementation lane complete (local commit, no push). Evidence:
  - Phase 0 baselines: `tests/test_provider_operator_view.py` 26 passed; `tests/test_work_order_identity.py` 33 passed.
  - RED-first (verbatim): `ModuleNotFoundError: No module named 'a_conductor.model_artifact_freshness_projection'` — `ERROR collecting tests/test_model_artifact_freshness_projection.py` / `1 error during collection` (all behavioral axes RED behind the missing projection API); direct `python3 -c` import of `project_model_artifact_freshness` produced the same ModuleNotFoundError.
  - GREEN: new suite 41 passed; regression neighbors 26 + 33 passed (identity suite validates WO-P1-757 filename/`Issue: #757`/marker); `python3 -m compileall -q src/a_conductor` clean; `git status --porcelain` = exactly the 3 exclusive files (2 new source + this WO). Scope: no existing module touched.
  - Design decisions:
    - Artifact keys (canonical order, never paths): `model_scout_current`, `model_roster`, `model_router_policy`, `model_catalog`, `model_capability_cache`; decision-input roles exported as fixed strings (e.g. `POLICY_TIER_PRIMARY_AND_RACE_OVERRIDE_SOURCE`).
    - Record types: `ModelIntelFreshnessReport` (artifacts, observations, `degraded`, `degraded_reason`, `non_authoritative` pinned `init=False=True`), `ModelArtifactRecord`, `ModelArtifactEmbeddedFlags`, `ModelFreshnessNote` — all frozen+slots; module imports restricted to `collections.abc/dataclasses/datetime/hashlib/json` (purity + zero-provider-import test pins the allowlist via AST).
    - Per-artifact default `max_age_seconds` (documented, injectable per call as scalar or per-key mapping over `DEFAULT_MAX_AGE_SECONDS_BY_ARTIFACT`): scout 21600 (6h), roster 86400 (24h), policy 86400 (24h), catalog 604800 (7d), capability 2592000 (30d). Rationale: thresholds track each artifact's own regeneration cadence — scout regenerates on the shortest cycle, capability scores drift slowest; invalid or unknown-key overrides fail closed (`ValueError`).
    - Read-state vocabulary: `AVAILABLE/OK`, `ABSENT/ARTIFACT_ABSENT`, `UNPARSEABLE/EMBEDDED_JSON_INVALID|EMBEDDED_JSON_SHAPE_INVALID|EMBEDDED_CONF_INVALID`, `UNREADABLE/ARTIFACT_MATERIAL_MALFORMED`. Staleness `AVAILABLE/STALE/UNKNOWN` (future mtime → UNKNOWN; missing mtime → UNKNOWN; UNREADABLE/ABSENT → UNKNOWN).
    - Timestamp parse states: `PARSED_OFFSET` (ISO-8601 with offset incl. `Z`), `PARSED_NAIVE_LOCAL` (naive ISO incl. date-only roster `Generated:` header), `UNPARSEABLE`; raw preserved byte-for-byte, naive-local never converted to UTC. Cross-artifact comparisons run only like-kind (`OFFSET_INSTANT` aware↔aware, `NAIVE_LOCAL_WALL` naive↔naive); mixed-kind pairs never ordered, so no note is fabricated.
    - Cross-artifact notes: `ROSTER_NEWER_THAN_POLICY` (DRIFT), `SCOUT_ECHO_MISMATCH` (MISMATCH; parse-level instant equality so `Z` vs `+00:00` match is not a mismatch), `SEEDS_ACTIVE` (WARNING, `MODEL_IDS_ARE_SEEDS=1`). Note value fields are populated only when both sides parsed.
    - Snapshot/loader contract: mapping of key→material, object exposing `.artifacts`, iterable of entries carrying `artifact_key`, or zero-arg loader callable (card-08 duck-typed pattern); loader exception → typed degraded report `LOADER_FAILURE` (never an exception), unresolvable shape → `SNAPSHOT_SHAPE_INVALID`. Materials carry `raw` (`str`/`bytes`/`None`) + optional `mtime_epoch_seconds`; unknown artifact keys are ignored; extra attributes (incl. machine-local paths) are never echoed — no output field carries a path.
    - Empty-scout (`recommendations: {}` → `recommendations_empty: true`) and near-empty catalog (`model_count: 0`) stay AVAILABLE typed records; never fabricated, never failure.
  - Delivery gate next: independent review → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI → checkpoint + close on #757.
