# A-Conductor — Current Work

Last updated: 2026-08-21 (autonomous night session 2)

## Current phase

**Config surface delivered; leftover decisions cleared. Awaiting user milestone pick.**

## Session summary (2026-08-21 night 2, GLM 5.3/ZCode under user authorization)

All work as small PRs, CI-green before every merge:

- **PR #4 / WO-P1-048** (merge `e420999`): opened the per-worker Serena config surface work order; roadmap item added (§13).
- **PR #5 / WO-P1-048 B-C** (merge `56ca37b`): `WorkerSerenaSettings` typed model (language backend, excluded/included/fixed tools with Serena exclusivity, base modes, tool timeout), full-file renderer, confined atomic applier.
- **PR #6 / WO-P1-048 D-E** (merge `c860c7a`): `serena_worker_settings` store table + facade; desktop **Config** button + CLI-minimal dialog (prefill, validation, nothing persisted on invalid input, "applies on next start" semantics).
- **PR #7 / WO-P1-049** (merge `617fac5`): `build_supervised_native_adapter_resolver` + `DurableJobControlService.open(supervised=True)` — the resilient path is now a tested one-parameter enable; default stays plain until per-job identity plumbing (decision recorded).

## Evidence

- Final main regression: 764 passed, 2 skipped (display-dependent), 0 failed; smoke `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`.
- Supervised integration: real pytest job flow through `supervised=True` → `VERIFYING` + one `execution_records` row `VERIFICATION_REQUIRED` + durable artifacts.
- Known flake (pre-existing, untouched by diffs): `test_real_dummy_process_start_idempotent_stop` once exceeded its real-process deadline under full-suite load; passes in isolation and on rerun.

## Leftover inventory (all cleared or explicitly user-gated)

- Cleared: config surface (P1-048), supervised enabling path (P1-049), packaging/CI/README/notes (prior session PRs #1-3).
- User-gated (cannot be done by an agent): (1) DR-P1-003 live Worker-3 transport validation — requires tunnel creation in the OpenAI Platform web UI, same flow as the wastewater instance prepared on 2026-08-21; (2) flipping `supervised=True` as the deployment default — one parameter once you accept the static per-(repo, argv) dedup identity.

## Next safe action

User picks: (a) authorize/perform Worker-3 tunnel creation for live validation, (b) flip supervised default for your deployments, or (c) continue Phase 1 milestones (next natural chunk: materialize WorkerSerenaSettings into a real worker's SERENA_HOME on start — wiring `apply_worker_serena_settings` into the runtime setup/start flow). Open a new work order + reuse gate first.
