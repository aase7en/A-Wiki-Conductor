# WO-P1-787 — Projection/Quota Test Hardening (G1+G2)

Identity schema: GITHUB_ISSUE_V1
Issue: #787
Status: AUTHOR LANE — candidate for review/CI gates; delivery STOPS at PR+CI+evidence (NO self-merge per issue constraint — GPT Integrator merges)
Risk: R2 (test-only; no source/runtime changes; monkeypatched injection only)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `fd48d9c8373c721a039be35507a627c9bf346044` (origin/main re-pinned live post-#786; issue's preflight baseline 7f52cb5 superseded by docs closeout — no overlap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo787-testhardening`; branch `fix/wo787-projection-quota-test-hardening`.
- Claim: #787 c7106249373. Source of need: Kilo gap census #771 c7058122967.
- Exclusive allowlist (issue-verbatim): APPEND `tests/test_route_telemetry_projection.py` (G1), APPEND `tests/test_cointh_quota_pretool.py` (G2 — existing file ~24 tests under WO-P1-564; NOT a new file), NEW this WO doc. FORBIDDEN: src/, scripts/codex_hooks/cointh_quota_pretool.py runtime hook, provider settings, AGENTS/README/CURRENT-WORK/handoff/COLLAB, other repos, unrelated tests, credentials, external calls, actual GLM dispatch, CI config. If an accepted contract FAILS and source mutation would be required: STOP and file the finding, do not widen.

## G1 — route telemetry purity trio (equivalent in meaning to card-07/08/09 sibling contracts, no brittle overconstraining)

1. `test_module_source_imports_are_pure_allowlist` — AST/static source restriction: forbidden provider I/O imports absent (urllib/http/requests/socket/subprocess/provider modules).
2. `test_runtime_import_graph_has_no_provider_modules` — runtime import graph (sys.modules after fresh import in subprocess or importlib isolation) contains no provider modules.
3. `test_projection_performs_no_io_and_does_not_mutate_fixtures` — inject ALL required evidence via monkeypatched fakes; assert no real HTTP/filesystem/credential access (monkeypatch socket/urlopen/open at builtins level with sentinels raising if touched) AND every input fixture object preserved (deep equality pre/post projection).

## G2 — offline CoinTH quota fixtures (append to existing suite; current-code truth only)

- consistent `remaining_5h` positive → `AVAILABLE`; exact valid zero → `EXHAUSTED` (never UNKNOWN).
- contradictory remaining+used vs limit; malformed JSON/types; expired-invalid tuple; transport failure → `UNKNOWN` — no false exhaustion.
- HTTP 401/403 → `UNKNOWN` with `reason=quota_http_error`, `http_status=401|403` per CURRENT verified code — do NOT assert a separate AUTH enum that does not exist in this seam.
- `window_source` pass-through preserves source; no silent stale→fresh promotion; validity as presently defined.
- Mock `subprocess.run` + environment with DUMMY tokens only; never real curl/network/paid APIs/private credentials.
- No regression of the ~24 pre-existing parser/CLI selector tests (run them green).

## Acceptance

- RED-first where the new tests can fail against current code; where current code PASSES by design, document a verified regression pin (no fabricated RED).
- Per-file green: both appended suites + directly related neighbors (`tests/test_route_telemetry_projection.py` whole file; `tests/test_cointh_quota_pretool.py` whole file; `tests/test_work_order_identity.py` incl. this WO). `git diff --check`; exactly 3-file diff; fixtures secret-free.
- Independent NONAUTHORING R2 technical review at frozen SHA; exact-head hosted CI (4 jobs) green.
- Evidence: this issue + #771 pointer. NO self-merge/self-review/auto-release.

## Checkpoint

- 2026-11-23: lane bootstrapped @`fd48d9c`; claim c7106249373; quota seam anchors recorded (scripts/codex_hooks/cointh_quota_pretool.py `_emit_deny`:29, `_read_event`:44, selector helpers :55-:272); implementation pending.
- 2026-11-23: IMPLEMENTATION DONE (test-only; 3-file allowlist held; zero src/ or hook mutations; no STOP-worthy src defect found).
  - Phase 0 baselines: `tests/test_route_telemetry_projection.py` 14 passed; `tests/test_cointh_quota_pretool.py` 26 passed (WO's "~24" estimate superseded by actual 26); `tests/test_work_order_identity.py` 33 passed (already green with this WO doc untracked).
  - G1 trio RED-vs-pin: `test_module_source_imports_are_pure_allowlist` PIN (AST scan: only __future__/math/dataclasses/typing imports, zero forbidden roots incl. `a_conductor.provider*`). `test_runtime_import_graph_has_no_provider_modules` — first run RED from a TEST-HARNESS ARTIFACT, not src: file-location-isolated load must register the probe module in `sys.modules` before `exec_module` or `dataclass()` at src route_telemetry_projection.py:89 raises (`sys.modules.get(cls.__module__)` is None); fixed probe-side, now PIN (subprocess reports zero forbidden modules loaded, empty-attempts projection works). `test_projection_performs_no_io_and_does_not_mutate_fixtures` — first run RED from a TEST-HARNESS ARTIFACT: the mutable duck semantic row lacked value `__eq__`, so the original-vs-deepcopy preservation check failed spuriously; fixed duck-side, now PIN (socket/urlopen/builtins.open/subprocess.run/subprocess.Popen sentinels untouched; fixtures deep-equal pre/post; double projection deterministic). No fabricated RED: both initial REDs were diagnosed, documented, and fixed strictly inside the test file.
  - G2 RED-vs-pin: all 15 new test functions (37 parametrized cases) are PINS — passed against current code on first run; fixtures assert CURRENT truth only (exact reason strings, exact UNKNOWN evidence dicts incl. presence/absence of `http_status` per reason).
  - Seam behaviors verified (cointh_quota_pretool.py anchors): `_quota_state`:310 — missing_credential :313 (+ subprocess never called); quota_request_failed :339 (TimeoutExpired, OSError); quota_response_too_large :343; quota_transport_error :346 (nonzero curl exit, missing status marker, non-digit status); quota_http_error with `http_status` 401/403 :349 — no separate AUTH state exists; quota_malformed_json :354/:356; quota_incomplete_tuple :360; quota_invalid_expiry_flag :362; quota_expired :364; quota_invalid_counter_type :368 (strict `type is int`: str/float/bool/None rejected); quota_inconsistent_tuple :390 incl. `window_reset_at` validity as presently defined (int 0<at<=2^63-1, finite float>0, tz-aware ISO; naive ISO and numeric string rejected); AVAILABLE/EXHAUSTED decision :401 (positive → AVAILABLE, valid exact zero → EXHAUSTED, never UNKNOWN, evidence carries no `reason` key); `window_source` verbatim pass-through :398 (stale never promoted to fresh); credential popped from child env :328 (dummy token flows only via stdin curl config, absent from argv and child env).
  - G2 safety: `subprocess.run` monkeypatched with a recording stand-in only; env token is a DUMMY (`wo787-dummy-token-not-a-real-credential`); no real curl/network/credential touched.
  - Final verification: per-file green — projection 17, cointh 63, identity 33; `git diff --check` clean; porcelain exactly 3 files (2 test files + this WO doc). Delivery stops at PR+CI+evidence per issue constraint (NO self-merge).
