# WO-P1-765 — SFU26 P3 Consolidation: Follow-up Hardening Backlog

Identity schema: GITHUB_ISSUE_V1
Issue: #765
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (tests-focused hardening + one bounded typed-degradation behavior on the monitor frame path)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `b9b93707da96094aeb31c6384e551455b407d967` (origin/main verified at bootstrap; bootstrap typo fail-closed once, resumed with operator-confirmed pin).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo765-p3consolidation`; branch `fix/wo765-p3-consolidation`.
- Program authority: SFU26 roadmap follow-up backlog (advisories recorded on closed cards 01/#746, 02/#750, 06/#752, 03/#763) — consolidated now because no self-unblocked roadmap lanes remain.
- Exclusive files: `tests/test_web_api.py`, `src/a_conductor/monitor_live_provider.py` + `tests/test_monitor_live_provider.py`, `src/a_conductor/route_telemetry_projection.py` + `tests/test_route_telemetry_projection.py`, `src/a_conductor/fleet_projection.py` + `tests/test_fleet_projection.py`, this WO. EXCLUDED (design/behavior decisions beyond P3): collector-notes surfacing, dynamic kill-switch, sentinel distribution changeover.

## Work Items (from recorded checkpoints)

1. **Card-01 → tests/test_web_api.py**: (a) methods-attr visibility assertion — the route-policy test should assert method visibility via the app's actual router table attribute semantics (pin how methods are derived, so a framework change cannot silently weaken the completeness check); (b) per-method unknown-path pin — assert the unknown-path response shape for EACH allowed method verb (not just one).
2. **Card-02 → monitor live path** (src `monitor_live_provider.py` + test): frame-size bound — worst-case composed monitor child ≈399KB exceeds `web_api.MAX_FRAME_BYTES` (262,144). Add a bounded projection: when the composed monitor child exceeds a documented byte bound (reuse MAX_FRAME_BYTES constant semantics; do not duplicate the number — import or define once), degrade to a typed `MONITOR_PAYLOAD_TOO_LARGE` child (keep {mode, monitor:{error/gate}}-shaped marker consistent with existing typed failures; siblings intact) instead of letting the frame encode fail or truncate silently. RED test: oversized fixture child → typed marker; normal path unchanged (byte-compat for small children).
3. **Card-06 → route_telemetry_projection.py + test**: (a) remove dead `_MAX_IDENTITY_LENGTH` constant; (b) harden correlation comparison — replace `str()` duck comparison with type-strict check (both sides must be str already per upstream `_safe_identity`; non-str → typed rejection instead of str()-coerce compare); (c) document blank-wall-stamp policy (raise, consistent with fail-closed text conventions) in the docstring.
4. **Card-03 → fleet_projection.py + test**: guard the two-faced-subclass residuals — (a) wrap `isoformat()` and `now - parsed` subtraction in `_parse_stamp`/`_validate_session` paths (raising on second call → typed TIMESTAMP rejection, no escape); (b) narrow text checks against str-subclasses with raising `__iter__`/`__len__` (use `type(value) is str` fast-path or safe containment probing → typed rejection on raise).

## Acceptance

- RED-first per behavior item (frame-size bound; correlation hardening; two-faced guards) verbatim; pure test-additions (card-01 items) verified by mutation-style checks where feasible (temporarily weaken → observe fail) recorded in the checkpoint.
- Per-file green: `tests/test_web_api.py`, `tests/test_monitor_live_provider.py`, `tests/test_route_telemetry_projection.py`, `tests/test_fleet_projection.py`, `tests/test_work_order_identity.py` (incl. this WO), plus `tests/test_web_api_mutations.py`/`p1`/`p2_gaps` regression; `python3 -m compileall -q src/a_conductor`; npm untouched; diff = the listed files only.
- Delivery gate: frozen local commit → independent review → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI (macOS capacity rerun precedent) → checkpoint + close on #765.

## Checkpoint

- 2026-11-15: lane bootstrapped @`b9b9370`; issue #765; four work groups defined from recorded advisories; implementation pending.
- 2026-11-15: implementation complete (local commit, NO push). Author lane ran RED-first on b9b9370 (baselines re-verified at head before reliance).

### Phase 0 — baselines @ b9b9370 (per-file pytest, `PYTHONPATH=src python3 -m pytest tests/<f>.py -q`)

- tests/test_web_api.py: 100 passed
- tests/test_web_api_mutations.py: 10 passed
- tests/test_web_api_p1_gaps.py: 10 passed
- tests/test_web_api_p2_gaps.py: 18 passed
- tests/test_work_order_identity.py: 33 passed
- tests/test_monitor_live_provider.py: 12 passed
- tests/test_route_telemetry_projection.py: 13 passed
- tests/test_fleet_projection.py: 95 passed

### Phase 1 — RED verbatim (new tests first, run against unmodified src)

- frame-size (`tests/test_monitor_live_provider.py`): `test_oversized_composed_child_degrades_to_typed_marker_with_mode_shape` FAILED (provider returned `mode == "live"` — no bound existed; fixture = 128 maxed tool rows + 128 hook rows ≈ composed child well past 262,144 B); `test_frame_bound_is_the_web_transport_bound_not_a_magic_duplicate` FAILED (`ImportError: cannot import name 'MAX_FRAME_BYTES' from 'a_conductor.monitor_live_provider'`); `test_small_children_stay_live_and_byte_compatible_under_the_bound` FAILED (same ImportError).
- correlation (`tests/test_route_telemetry_projection.py`): `test_wo765_non_str_correlation_identity_is_typed_rejected_not_coerced` FAILED — `DID NOT RAISE <class 'ValueError'>` (semantic `request_id=7` vs row `"7"` passed via `str()`-coercion through the duck-typed shape seam, bypassing upstream `_safe_identity`).
- two-faced guards (`tests/test_fleet_projection.py`): 4 FAILED with raw escapes — `test_flip_flop_tzinfo_raising_at_isoformat_is_typed_rejection` (`RuntimeError: flip-flop utcoffset` escaped at `parsed.isoformat()`), `test_flip_flop_tzinfo_raising_at_now_subtraction_is_typed_rejection` (escaped at `now - parsed` on third utcoffset read), `test_raising_iter_session_id_is_typed_rejection_not_escape` (`RuntimeError: liar __iter__` escaped in `_check_text`), `test_raising_len_tunnel_suffix_is_typed_rejection_not_escape` (`RuntimeError: liar __len__` escaped at the suffix length check).
- card-01 (test-only pins, expected pinned-pass): `test_unknown_path_shape_pinned_per_allowed_method` initially failed for POST/PATCH/DELETE — material discovery, see decisions.

### Decisions

- **Bound value/definition (card-02):** 262,144 B. `web_api.py` is not an exclusive file, so re-pointing `web_api.MAX_FRAME_BYTES` at the monitor constant was out of scope; a module-level import of `web_api` into `monitor_live_provider` is impossible (web_api already imports monitor_live_provider at module level — genuine import cycle), and a function-level transport-layer import inside the pure producer was rejected as a layering violation. Therefore `MAX_FRAME_BYTES` is defined once at module level in `monitor_live_provider.py` (documented as the monitor-path authority), and `test_frame_bound_is_the_web_transport_bound_not_a_magic_duplicate` pins it equal to `web_api.MAX_FRAME_BYTES` (test-only web_api reference) so the two cannot drift. Follow-up advisory for a future authorized web_api lane: delete the local constant and import this one.
- **Marker name/shape (card-02):** `{"error": "MONITOR_PAYLOAD_TOO_LARGE", "gate": "FRAME"}`, returned as `{"mode": "error", "monitor": ...}` — same {mode, monitor:{error/gate}} wrapper as every other producer failure; gate `FRAME` names the byte-bound boundary (section gates TOOLS/HOOKS/SKILLS and `PROJECTION` stay reserved for their existing failure classes). A child that cannot be serialized at all is a projection failure (unmeasurable ⇒ unframmable) and keeps `MONITOR_LIVE_PROJECTION_FAILED`/gate `PROJECTION`. Sibling snapshot content is untouched by design (producer replaces only the monitor child); size measured with the exact `encode_frame` dumps semantics (ensure_ascii=False, allow_nan=False, compact separators, UTF-8).
- **Correlation strictness (card-06):** `type(sem_value) is not str → ValueError("semantic telemetry correlation identity must be plain text: <name>")`; str-vs-str mismatch keeps the existing "identity mismatch" message (existing pin untouched). Type-strict (`type() is str`) rejects str-subclass identities too, consistent with the WO-P1-738 `type(v) is int` precedent.
- **Dead constant (card-06):** `_MAX_IDENTITY_LENGTH` removed (grep-verified dead: no readers in src or tests).
- **Blank wall-stamp policy (card-06):** documented in `RouteAttemptInput` docstring — blank/whitespace stamps raise at validation like all text fields; absence is expressed only by None.
- **Fleet rejection codes (card-03):** flip-flop stamps → `TIMESTAMP_INVALID`/field `created_at` (both the `isoformat()` and `now - parsed` wraps); raising `__iter__`/`__len__` session ids → `IDENTIFIER_INVALID` via new `_probed_str` probe in `_check_text`; raising `__len__` tunnel suffix → `TUNNEL_SUFFIX_INVALID` via the same probe. Plain-str behavior is byte-identical (`_probed_str` returns the object as-is on the fast path).
- **Card-01 unknown-path discovery:** mutation verbs (POST/PATCH/DELETE) on an unknown path never reach the router 404 handler — the auth read-only boundary (`web_api_auth` pre-routing gate) answers `405 {"error": "MONITOR_READ_ONLY"}`; only GET gets `404 {"error": "MONITOR_NOT_FOUND"}`. This is deliberate fail-closed policy, so the per-method pin records the actual per-verb contract (`UNKNOWN_PATH_METHOD_POLICY`) instead of an assumed uniform 404 shape. web_api_auth.py untouched (out of scope).
- **Card-01 methods-attr pin:** asserts every `/api/*` route on the actual router table exposes a non-empty `set` of uppercase alphabetic `methods`, then re-derives the policy mapping from that attribute — a framework change that hides/renames/lowercases methods fails the pin explicitly.

### Mutation-check evidence (card-01 test-only items; temporary mutations reverted byte-exact, web files confirmed absent from porcelain)

- M1 (methods pin): injected temporary `@app.put("/api/v1/health")` → `test_route_method_derivation_is_pinned_to_router_table_attrs` FAILED (policy-mapping mismatch detected) → restored.
- M2a (unknown-path pin, gate side): weakened the read-only gate so POST passes the boundary → `[POST]` param FAILED (404 shape replaced the pinned 405 read-only shape) → restored.
- M2b (unknown-path pin, router side): changed the 404 handler body to `MONITOR_GONE` → `[GET]` param FAILED → restored.

### Phase 3 — GREEN

- tests/test_web_api.py: 105 passed (100 + 5 new)
- tests/test_web_api_mutations.py: 10 passed; p1_gaps: 10; p2_gaps: 18; test_work_order_identity.py: 33 (incl. this WO)
- tests/test_monitor_live_provider.py: 15 passed (12 + 3); tests/test_route_telemetry_projection.py: 14 (13 + 1); tests/test_fleet_projection.py: 99 (95 + 4)
- `python3 -m compileall -q src/a_conductor` OK; npm untouched; diff = the listed exclusive files only (porcelain verified before commit).
