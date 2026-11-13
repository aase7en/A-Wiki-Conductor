# WO-P1-746 — SFU26 Card 01: Web Verification Floor

Identity schema: GITHUB_ISSUE_V1
Issue: #746
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (CI workflow + test repair; product `src/` untouched unless a bounded lazy-import repair proves necessary)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `23050a4fd3171922bfa68fc3649cd75224ff5c9c` (origin/main verified at bootstrap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo746-webfloor`; branch `fix/wo746-web-verification-floor`.
- Program authority: SFU26 roadmap card `CAND-SFU26-01` (`docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md` §8 card 01).
- Allowed scope: `.github/workflows/ci.yml`, `tests/test_web_api.py`, this WO file. `src/` changes ONLY as a bounded lazy-import repair of the headless-import guarantee if diagnosis proves necessary; anything structural = STOP and report instead of widening scope.
- No edits to `web/sunday-family/package.json` scripts/dependencies (use existing `test`/`build` scripts only); no new lint/typecheck/format tooling; no pytest markers or conftest.

## Deliverables

1. CI: a `web` verification job running npm ci + the existing test and build scripts for `web/sunday-family` on a supported runner, consistent with existing workflow conventions (pytest jobs untouched).
2. `tests/test_web_api.py` stale skip #1 (`test_read_only`, ~line 94) replaced by an explicit route/method policy contract test pinning the CURRENT endpoint+method surface (read endpoints GET-only; mutation methods exactly on their SF-WEB-4/6 paths; unknown routes/methods denied) that fails on any unlisted surface change.
3. Stale skip #2 (`test_headless_import`, ~line 275) un-skipped with a meaningful headless guarantee. Diagnose the real failure first (run it un-skipped); bounded lazy-import fix in `src/a_conductor/web_api.py` allowed only if that is the actual cause; STOP and report if the fix would be structural.

## Acceptance

- RED-first evidence: un-skipped old `test_read_only` assertions shown failing against the current surface (or the diagnosis recorded) before replacement; un-skipped `test_headless_import` actual failure captured before any fix.
- `python3 -m pytest tests/test_web_api.py -q` green in the worktree (per-file convention; no markers).
- Local web checks pass: `npm --prefix web/sunday-family run test` and `npm run web:build` (run from repo root of the worktree).
- `.github/workflows/ci.yml` valid YAML; new job name/runner/step style consistent with existing jobs.
- Delivery gate: commit (local) -> independent review at frozen SHA -> push -> PR -> exact-head CI (including the new web job) green -> merge expected head only -> post-main CI -> checkpoint on #746.

## Checkpoint

- 2026-11-13: lane bootstrapped @`23050a4`; issue #746 created; both stale tests captured verbatim on the bootstrap report; implementation pending.
- 2026-11-13: implementation complete (local commit only, no push). Diagnosis: default `python3` lacked the project deps — installed per repo convention `python3 -m pip install -e ".[test]"`; baseline then 52 passed / 6 skipped. Un-skipped RED: 5× `test_read_only[POST|PUT|DELETE|PATCH|OPTIONS]` failed at the route-method completeness assertion (`assert all(route.methods == {"GET"} for route in client.app.routes)` → `assert False`); the per-request 405 check on `/api/v1/snapshot` passed for all 5 methods. `test_headless_import` PASSED un-skipped (returncode 0, empty stderr) → skip removed, assertion strengthened with an `a_conductor.desktop_app` sys.modules guard; `src/` untouched (no lazy-import repair needed). Route surface pinned from `web_api.py` decorators (:291–477): GET health / snapshot / monitor/snapshot / metrics / stream / events / mutations / connectors; POST workers/{worker_id}/command + workers + connectors; PATCH connectors/{connector_id}; DELETE workers/{worker_id} + connectors/{connector_id}. New tests in `tests/test_web_api.py`: `test_route_method_policy` (exact surface completeness + unknown path `MONITOR_NOT_FOUND`), `test_read_endpoints_reject_mutations` (7 pure-GET paths × POST/PUT/DELETE/PATCH/OPTIONS → 405), `test_connector_collection_rejects_other_mutations` (connectors collection: PUT/DELETE/PATCH/OPTIONS → 405; POST is allowed there so excluded). CI: new `web` job (ubuntu-latest, `actions/setup-node@v7` node 20 — no `engines` field in package.json, lockfileVersion 3 present → `npm ci` viable; steps checkout / setup-node / `npm --prefix web/sunday-family ci` / `run test` / `run build`; no caching, matching existing jobs). Verification: test_web_api.py 93 passed (0 skipped); test_web_api_mutations.py 10 passed; test_web_api_p1_gaps.py 10 passed (instructed name `test_web_api_p1.py` does not exist at this base — actual file is `test_web_api_p1_gaps.py`); test_web_api_p2_gaps.py 18 passed; test_work_order_identity.py 33 passed (incl. this WO); `npm --prefix web/sunday-family run test` 70 passed (7 files); `npm run web:build` success (tsc --noEmit + vite build). Files touched: `tests/test_web_api.py`, `.github/workflows/ci.yml`, this WO.
