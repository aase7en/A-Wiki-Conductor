# WO-P1-072 — AI EXECUTION SLOTS live operator model

Created: 2026-08-26
Owner: GPT-5.6 Sol MAX — design + implementation + visual/release integration
Status: IN_PROGRESS — user decision settled; telemetry seam proven; implementation branch active
Branch: `feat/ai-execution-slots-live`
Stacked dependency: PR #99 / WO-P1-071 must merge before this PR is finalized

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

## Next micro-step

Complete the main-screen collapse + live slot table against the proven telemetry parser, then run focused tests and reconcile with the post-PR-99 main SHA before opening a PR.
