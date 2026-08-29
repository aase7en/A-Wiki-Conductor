# WO-P1-072 — AI EXECUTION SLOTS live operator model

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — design + implementation + visual/release integration
Status: COMPLETE / MERGED
Branch: `feat/ai-execution-slots-live`
Dependency satisfied: PR #99 merged as `e8195b1`; branch reconciled to that main line

## User problem / outcome

The current main screen shows `WORKERS` and `CONNECTORS` as if they were two comparable live process tables. The user sees logical workers as `STOPPED` while connectors are `READY`, cannot tell what can actually be controlled, and cannot see which Serena project a connected ChatGPT worker is actively using.

Desired operator model:

`PROJECT -> AI EXECUTION SLOT -> CONNECTION -> ACTIVE PROJECT -> TASK`

The user should not need to understand registry/runtime/tunnel internals to answer: **which AI slot is connected, what project is it actually using, and what can I control?**

## Verified facts

- Worker registry state is logical scheduler/lifecycle state, not connector health. It is not 1:1 with the five Sunday-Worker connector instances.
- Connector `/readyz` is the authoritative live connection health source.
- `instance.ps1` is the authoritative connector **BOUND PROJECT** source.
- Serena logs `Activating <name> at <path>` whenever `activate_project` switches the server-wide active project. This allows read-only observation of the actual **ACTIVE PROJECT** without invoking an MCP tool or mutating a chat.
- Real observed example: Sunday-Worker-1 was bound to `A-Wiki-Conductor` while Serena active project had switched to `pharmacy`; the old UI could not express this drift.
- CONNECTORS already has a 15 s single-flight background refresh. Monitoring must remain native/file-based with no periodic subprocess.

## Product decision (user-approved 2026-08-26)

1. Main operator surface becomes **AI EXECUTION SLOTS — LIVE** and is connector/runtime-centric.
2. Logical Worker Registry remains required for GE-6/scheduler and CRUD but becomes **Advanced**, collapsed by default rather than the primary table.
3. Live slot columns prioritize:
   - SLOT
   - CONNECTION
   - ACTIVE PROJECT
   - BOUND PROJECT
   - LAST SWITCH
   - PORT
   - masked TUNNEL
   - AUTO
   - EDIT
4. `ACTIVE PROJECT` comes only from observed Serena activation telemetry. Missing/unreadable evidence -> `UNKNOWN`; never infer or invent.
5. If normalized active path differs from bound path, display `[DRIFT]` and a non-color-only text marker.
6. User-facing actions name the actor explicitly: `Start Worker` vs `Start Connector`; ambiguous `Activate` becomes `Copy Activate`.
7. Existing logical worker functionality survives; this is an information-architecture change, not deletion of scheduler/runtime abstractions.

## Scope

Allowed:
- `src/a_conductor/serena_activity.py`
- bounded `src/a_conductor/desktop_ui.py` layout/status/table/action semantics
- `src/a_conductor/i18n.py` help/tooltips
- focused UI/telemetry tests
- `DESIGN.md`, this WO, guide docs as needed

Forbidden:
- GE-6 scheduler implementation
- graph/job lifecycle changes
- A-Wiki mutation
- secrets/full Tunnel IDs
- periodic PowerShell/cmd/subprocess probes
- pretending a ChatGPT turn can be server-pushed through the tunnel

## Stable seams / tests

- `observe_serena_activity(instance_root) -> SerenaActivityObservation` is pure/read-only and bounded-tail.
- Existing connector refresh pipeline enriches each `(instance, health)` with activity off the Tk thread.
- Treeview preserves legacy internal TUNNEL/AUTO value indexes where practical; `displaycolumns` controls operator order.
- Advanced registry preserves existing `worker_tree` CRUD/lifecycle behavior.

## Acceptance

- [ ] Main UI no longer presents logical WORKERS as a competing live-status table by default.
- [ ] Five connector slots can show READY/STOPPED from live health.
- [ ] ACTIVE PROJECT is observed from Serena runtime logs, BOUND PROJECT remains separate.
- [ ] Drift is visible as text (`[DRIFT]`), not color-only.
- [ ] Unknown telemetry is honest (`UNKNOWN`).
- [ ] Refresh <=15 s via existing single-flight connector refresh; no periodic subprocess.
- [ ] Worker Registry remains reachable as Advanced and all existing worker CRUD/lifecycle capabilities remain functional.
- [ ] Action labels disambiguate Worker vs Connector.
- [ ] TH/zh-CN/EN help explains the model.
- [ ] 700/900/1280+/maximized layout checks pass; no critical action clipping.
- [ ] Real-system read-only E2E confirms actual five connectors and at least one observed active-project/drift case when available.
- [ ] Full Windows/Ubuntu/macOS CI green before merge.
- [ ] Installed/frozen visual acceptance completed before v0.7.0 publication.

## Failure behavior

- Missing/rotated/unreadable Serena log -> `UNKNOWN`; connection health remains independently visible.
- Parser errors never stop connector refresh.
- STOPPED connector does not claim an active project even if stale log entries exist.
- Telemetry never writes runtime files and never invokes Serena tools.

## Real-system E2E checkpoint — 2026-08-26

Read-only E2E used an online SQLite backup of the real user DB plus the real `C:\AI\serena-instances` fleet. The harness did **not** call `start_background_operations()` and therefore did not autostart/stop connectors. Post-run live health matched pre-run state.

Observed fleet at capture time:
- Sunday-Worker-1: READY, bound `A-Wiki-Conductor`, active `pharmacy` -> `[DRIFT]`;
- Sunday-Worker-2: READY, bound `pharmacy`, active `sunday-estate-webapp` -> `[DRIFT]`;
- Sunday-Worker-3: READY, bound `env-wastewater-webapp`, active `env-wastewater-webapp-review-worker3` -> `[DRIFT]`;
- Sunday-Worker-4: STOPPED -> active project intentionally suppressed as `—`;
- Sunday-Worker-5: READY, bound/active `sunday-estate-webapp` -> aligned.

Header/overview evidence: `SLOTS 4/5 · REGISTRY 8`, Registry collapsed by default, three live drifts. A real 1600x900 screenshot was captured privately for visual review; screenshot/DB evidence is intentionally not committed because it contains local paths.

E2E found three defects before PR:
1. a fixed 256 KiB tail missed older-but-current activation events after heavy runtime noise; repair scans backward in 64 KiB chunks with a 2 MiB hard ceiling and stops at the newest real activation;
2. renamed connectors retained legacy runtime filenames (`phase6-runtime.stderr.log`, `wastewater-runtime.stderr.log`); repair chooses the newest `*-runtime.stderr.log`;
3. broad matching could treat tool/test output that *quoted* `Activating ...` as live truth; repair requires the exact `serena.agent:_activate_project:<line>` provenance signature.

Regression coverage pins all three cases. Focused latest result: `148 passed, 1 host-Tk skip`; `tests/test_serena_activity.py` = 7 passed.

## Next micro-step

Clean private E2E artifacts, final diff/spec review, push `feat/ai-execution-slots-live`, audit remote PR diff, require Windows/Ubuntu/macOS CI green, then merge/fetch and perform frozen/installed visual acceptance before v0.7.0 publication.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #101 merged into main as `4ad0b8e48ecd07686d1c090aa8153215cbf4632f`.
