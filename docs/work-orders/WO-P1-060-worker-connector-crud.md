# WO-P1-060 — Worker & Connector CRUD via UI

Created: 2026-08-22 · Owner: GLM 5.3 · Status: DONE (PRs #42 #43 #44, all CI-green)

## Evidence

- PR #42 worker CRUD: 18 tests; add = auto `a-worker-NN` (max+1), rename =
  display name, delete guarded (unassigned + STOPPED).
- PR #43 connector create: 9 tests; full layout materialized from a live
  reference (shared paths parsed), `Sunday-works N` titles, port auto-allocation.
- PR #44 connector manage: 11 tests; alias table + stop-first zip-backup delete.
- Real-machine round trip (2026-08-22, main `f7911db`): created
  `Serena-Smoketest` on port 18014 from the real `conductor` reference,
  discovery picked it up, delete produced `smoketest-20260822-140647.zip`
  (instance-backups) and the instances root returned to exactly the original
  three. Lesson: instance names normalize to lowercase slug → Title case
  (`smoketest` → `Serena-Smoketest`), matching the existing folder convention.

## Goal (user decisions 2026-08-22)

Remove the manual bottleneck of adding workers/connectors so several chats can
work in parallel, and let sub-agent stacking create workers on demand:

1. **Scope: BOTH** worker slots and connector instances.
2. **Connector rename = display alias only** (DB-stored; folder untouched).
3. **Connector delete = stop → verify → zip backup → remove folder.**
4. Start immediately; TDD per PR; CI green before merge.

## Constraints / facts (from exploration)

- Worker registry is already DB-driven; `3` is only the first-run seed
  (`control_center.py:94`). Ports derive from worker number (18010+n, n≤99).
- Connector create = materialize the validated layout (~8 small files);
  discovery (`Start-*.cmd`/`instance.ps1` glob) picks it up after Rescan.
  Shared `$TunnelClientPath`/`$LegacySecretPath` must be parsed from an
  existing instance (single source of truth on this machine).
- Tunnel ID must come from the OpenAI Platform web UI (CLI provisioning is
  disabled: `tunnel_principal_association_unverified`); the app validates
  (`^tunnel_[0-9a-f]{32}$`) and writes `config/tunnel-id.txt`.
- Rename/delete only when STOPPED (PID-file guard exists in stop.ps1);
  `instance_flags` row must follow; window titles follow the
  `Sunday-works N - <name>` convention established 2026-08-22.
- Reuse gate (A-Wiki): satisfied — building on own validated primitives
  (`register_worker`, `set_instance_tunnel_id`, `instance_rebind`,
  `render_serena_config`, `discover_local_instances`). No A-Wiki mutation.

## PR series

- **PR-A Worker CRUD**: registry `unregister_worker`/`rename_worker`;
  service `add_worker` (auto next `a-worker-NN`), `rename_worker_display`,
  `delete_worker` (guards: STOPPED + unassigned); facade delegates; UI
  buttons เพิ่ม Worker / แก้ชื่อ / ลบ (+ confirm, tooltips).
- **PR-B Connector create**: `instance_create.py` template materializer
  (instance.ps1/start.ps1/stop.ps1/Start|Stop-*.cmd/profiles template/
  serena_config.yml seed via `render_serena_config`/tunnel-id optional);
  next-free-port allocation; guards (unique name, project exists, inside
  root); UI "เพิ่มตัวเชื่อม" dialog; Rescan after create.
- **PR-C Connector rename (alias) + delete (zip)**: `instance_display_names`
  table (PRAGMA-guarded migration); `delete_instance` guard chain (health
  STOPPED → stop if needed → zip to `%LOCALAPPDATA%\A-Conductor\instance-backups\`
  → rmtree → clean flags/alias rows); UI buttons + confirm.

## Acceptance criteria

- Add worker → appears after refresh, persists across reopen, port defaults
  don't collide with existing serena_worker_configs.
- Create connector via UI → Rescan lists it → tunnel ID dialog completes
  setup → Start reaches READY (sandbox-verified in tests, real-machine smoke
  by user).
- Rename connector → UI shows alias immediately, folder/flags intact.
- Delete connector → guarded when running; zip exists; gone from list;
  autostart row cleaned.
- Full suite green; CI green each PR.

## Checkpoint

- 2026-08-22: WO created; PR-A started (branch `chunk/worker-crud`).
