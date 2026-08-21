# Design — One-App Instance Orchestration (2026-08-21)

Status: approved for implementation (user delegated autonomous night session; alternatives and trade-offs recorded below)

## Goal (user, verbatim intent)

เปิดโปรแกรม A-Conductor ตัวเดียวแล้วทำงานได้เลย — ไม่ต้องไล่เปิด serena cmd เดิมทีละตัว (สูงสุด 3 ตัว) ผู้ใช้ตั้งค่าผ่าน UI ว่าจะทำงานกับโปรเจ็คใด หรือออโต้; เวลาเรียก plugin ใน GPT (อนาคต gemini/claude/อื่นๆ) เชื่อมกับ active repo ได้

## Approaches considered

1. **MCP multiplexer gateway** (one local server, one tunnel port, any plugin connects, routes tool calls to per-project Serena instances). Deferred: requires a new MCP-protocol proxy subsystem (session state, tool namespace collisions), risks a second orchestration universe against the reuse-before-build gate, and Serena already supports multi-project activation inside one instance. Recorded as a future ADR-worthy direction (`DECISION_REQUIRED`).
2. **One-app orchestration of validated instances** (chosen): the Control Center auto-discovers the validated instance directories, shows health + Start/Stop per instance, and can auto-start flagged instances on launch. Reuses the existing validated start/stop scripts (DPAPI credential handling, doctor preflight, PID-ownership checks stay in the scripts — the app only invokes them hidden and parses results).
3. Re-implement `start.ps1` in Python. Rejected: duplicates credential-bearing logic with no gain.

## Design (approach 2)

### Discovery — `local_instances.py`

- `discover_local_instances(instances_root)` scans first-level directories containing `instance.ps1` and parses `$InstanceName`, `$ProjectPath`, `$HealthListenAddress` (our own validated format). Default root: `C:\AI\serena-instances`. Zero-config UX.
- Result: `LocalInstance` records (name, project path, health address, instance root).

### Health — reuse `LoopbackReadyzHttpProbe`

- `instance_state(instance) -> STOPPED | READY | UNKNOWN` via the existing HTTP probe against `http://<addr>/readyz` (injectable for tests).

### Orchestration — `LocalInstanceOrchestrator`

- `start(instance)` / `stop(instance)` invoke the instance's validated `Start-*.cmd` / `Stop-*.cmd` via an injectable command runner (`subprocess` with `CREATE_NO_WINDOW`, captured stdout/stderr tail, bounded timeout, never `shell=True`).
- Returns a structured outcome (exit code, key line like `RUNNING`/`ALREADY_RUNNING`/`PORT_IN_USE`/`FAILED:<code>`, output tail). No process is ever killed directly by the orchestrator — lifecycle stays inside the validated scripts.
- Safety: refuses instance roots outside the configured instances root; never touches other processes (no broad kills by construction).

### Persistence — autostart flags

- `instance_flags` table in `SQLiteSerenaConfigStore` (instance name → autostart bool). UI checkbox writes the flag; app launch auto-starts flagged instances through the background executor.

### UI — INSTANCES panel (CLI-minimal per PROJECT-PLAN §6)

- Compact strip panel under the WORKERS area: columns NAME / PORT / STATE / AUTO, semantic status colors, buttons Start / Stop / Start-All / Rescan. State ● from the health probe on refresh.
- Desktop facade: `instances()`, `instance_action(name, action)`, `set_instance_autostart(name, enabled)`, `autostart_instances()`.

### Testing

- Fake instance trees in tmp dirs (fake `instance.ps1` + fake `.cmd` scripts that write marker files / emit `RUNNING`) + injectable probe/runner → deterministic service tests.
- UI tests follow the existing Tk patterns (explicit `_update` calls, fakes).
- Real-machine verification is read-only: discovery over the real `C:\AI\serena-instances`, health probe against the live wastewater instance; real start/stop is user-driven (live instance belongs to the user).

## Explicit non-goals tonight

- No MCP gateway/proxy (future ADR).
- No changes to the validated scripts or tunnel/credential logic.
- No real instance start/stop inside automated tests.

## Spec self-review

- Placeholders: none. Consistency: single chosen approach with deferred alternative recorded. Scope: three PR-sized chunks (docs / core service / persistence+UI). Ambiguity: "auto" mode = per-instance autostart flags honored at app launch (not OS boot); OS-level is a future Task Scheduler option already documented in the runbook.
