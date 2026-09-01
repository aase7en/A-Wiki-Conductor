# WO-P1-125 - AHA-7B Provider Operator Read Service

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / RED_FIRST
Priority: P1 AHA-7 next READY source slice
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo125-provider-read-service`
Branch: `feat/wo-p1-125-provider-operator-read-service`
Base: `origin/main@fae5c0d8a36a41eb172e2acb8dc88ca04658c4e9`

## Dependency / parallel-lane boundary

- WO124/AHA-7A is accepted and merged; WO129 reliability is accepted and merged.
- PR #177 / WO130 is docs-only closeout at `e3f8e912d265f1a28a656fb2908e689ad5cf4147`; its source/test overlap with this lane is zero.
- Until PR #177 merges, this lane must not mutate shared `CURRENT-WORK.md`, `handoff.md`, `README.md`, `DEFECT_LESSONS.md`, or `docs/agent-collab/AGENT_TASKS.md`.
- WO096 remains a separate P0 release blocker and grants no live connector mutation authority.

## Architecture review authority

GPT Ultra reviewed exact HEAD `c1cfbe780e76d3a64fb692e91dde851824bd8033` with task SHA `655bacc0ef384d2818ae54d8fe9729a00061040448d817a65df1872be6db3303`.
Result SHA-256: `47c5208e6f7c09681e79a0e850011b0f23deaa8237673b26889f6b93321428b8`.
Verdict: `CHANGES_REQUIRED`; P0=0, P1=4, P2=2. Relevant source/test blobs were revalidated unchanged on current base after WO129 merge, so findings are accepted and non-stale.
## Goal

Expose a truthful read-only provider operator service on the existing control database, using the accepted WO124 `ProviderOperatorRow` projection, without creating a second provider store/router/policy/readiness/quota authority or exposing endpoint/credential data.

## Required architecture

1. `DesktopControlService.open()` canonicalizes the control DB once with `expanduser().resolve(strict=False)` and passes the exact absolute `Path` to registry/settings/lifecycle/provider assemblies.
2. Retain one private `SQLiteProviderConfigStore`; initialize it once at bootstrap, never in the provider-list hot path.
3. `list_provider_snapshots()` uses an existing-file read-only SQLite connection, bounded busy timeout, deferred `BEGIN`, and no DDL/write/`BEGIN IMMEDIATE`.
4. Bulk list uses one connection/transaction and fixed-count SELECTs; providers order by `provider_id COLLATE BINARY ASC`; no public per-provider N+1 calls.
5. One shared typed `_snapshot_from_rows()` decoder serves single and list reads, validates generations/scalars/JSON/domain/identity, and maps corruption to stable code-only `ProviderConfigStoreError`.
6. One corrupt participating provider aborts the whole list; unrelated orphan endpoint/observation rows do not poison it.
7. `provider_operator_rows()` uses one retained store, one aware UTC clock value, one list call and one projection call; returns only immutable `ProviderOperatorRow` values.
8. Empty initialized store is `()`; missing/unavailable/busy/corrupt/schema failure stays typed and never collapses to empty/partial/stale/cache.
9. Normalize/withhold raw observation provenance before it crosses the facade; endpoint/base URL/credential sentinels must not appear in rows, reprs, or public error strings.
10. Preserve `configured`, `runtime_ready`, and `task_authorization=NOT_EVALUATED` as separate truths; no UI policy recomputation.
## Mutable scope

Allowed:
- `src/a_conductor/provider_config_store.py`
- `src/a_conductor/desktop_control.py`
- `src/a_conductor/provider_operator_view.py` only for the accepted provenance secrecy repair
- `tests/test_provider_config_store.py`
- `tests/test_desktop_control.py`
- `tests/test_provider_operator_view.py` only for secrecy/provenance regression
- this work order

Forbidden: `desktop_ui.py`, provider policy/routing/readiness/quota/execution/capacity authorities, secret resolver/source, provider edit/test/disable actions, network/subprocess probe launch, a second DB/store/router/cache, and shared closeout SSoT while PR #177 is open.

## RED-first matrix

- Pure zero-provider read with no DDL/write/`BEGIN IMMEDIATE`; missing DB does not create files and fails typed.
- Deterministic binary provider order; one connection/deferred transaction/fixed SELECT count; public `load_provider_snapshot()` must not be called by list.
- Single/list decoder parity; missing endpoint/observation and disabled provider remain truthful values.
- Corrupt generations/JSON/enums/models/URL/timestamps/scalars/relational identities fail code-only and abort participating list.
- Corrupt orphan endpoint/observation does not poison unrelated providers; WAL interleaving returns wholly old or wholly new snapshot.
- Canonical relative-path assembly remains fixed after cwd change; one retained provider store; repeated reads see commits and are uncached.
- Empty vs unavailable/corrupt remain distinct; hostile endpoint/credential/provenance sentinels never escape through rows/repr/errors.
- READY with UNKNOWN trust/egress still leaves `task_authorization=NOT_EVALUATED`.
## Verification / release gates

1. All new behavior tests must demonstrably RED before production repair.
2. Focused provider-store/operator/desktop suites pass after repair.
3. Impact-expanded provider configuration/policy/runtime and desktop regressions pass.
4. Realistic SQLite concurrency/coherence evidence passes on the supported local platform.
5. Self review, independent exact-head review, `git diff --check`, compileall, UTF-8 and added-line secret audit pass.
6. Reconcile/merge current `origin/main` after PR #177 before source freeze; then rerun focused and impact-expanded tests.
7. Commit -> PR -> remote diff audit -> exact-head CI -> re-audit latest SHA -> merge -> post-main CI -> tracked SSoT checkpoint.
8. P0/P1/P2 independent-review findings block merge.

## Next safe action

Write RED tests only. Do not modify production source until the RED matrix has failed for the intended missing/unsafe behaviors.
## RED checkpoint - 2026-09-01

Focused `-k wo125` result: **8 failed / 66 deselected**; test files compile cleanly.

Observed RED causes:
- `SQLiteProviderConfigStore` has no bulk `list_provider_snapshots()` API.
- malformed `models_json` escapes as raw `JSONDecodeError`.
- invalid persisted endpoint URL escapes as raw `ValueError`.
- `DesktopControlService.open("control.sqlite")` forwards a lexical relative path instead of one canonical absolute authority.
- `DesktopControlService` has no retained provider-store/operator-row facade.
- `ProviderOperatorRow.provenance` exposes hostile raw persisted provenance in the row/repr.

This is accepted failing evidence. Production repair may now begin; tests must not be weakened to make the slice green.
## Implementation checkpoint - 2026-09-01

Status: `IMPLEMENTED / CURRENT-MAIN_RECONCILE_PENDING`.

Accepted Ultra P1/P2 repairs now implemented:
- canonical absolute control-DB identity and retained provider store;
- one-time provider-store bootstrap at DesktopControl open;
- read-only bulk provider snapshots with one deferred transaction and no DDL/write hot path;
- shared typed snapshot decoder with strict persisted scalar/JSON/generation/identity validation;
- code-only corruption errors with decoder cause suppression;
- no N+1 public snapshot calls; deterministic binary provider ordering;
- safe operator provenance categories instead of raw persisted provenance;
- direct facade cross-DB authority mismatch refusal;
- no cache, no endpoint/credential exposure, and `task_authorization=NOT_EVALUATED` preserved.

Verification on base `fae5c0d8...`:
- original RED matrix: 8 intended failures;
- focused suite after repair: 89 passed;
- impact-expanded provider/runtime/elastic/Claude matrix: 264 passed;
- realistic WAL interleaving: all-old snapshot followed by all-new snapshot, never mixed;
- full local: 1966 passed / 4 skipped / 2 known optional-GPU dependency failures (Pillow/OpenGL only);
- compileall, diff-check, UTF-8 and added-line secret-value audit: PASS.

Next: commit this bounded checkpoint, merge current `origin/main` after WO130 docs-only closeout, update shared continuity/Defect Memory, then rerun exact-head verification before external review.
