# WO-P1-023: Stage B Dedicated Worker Preflight

Status: blocked_external
Lane/files: `PROJECT-PLAN.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-023-stage-b-preflight.md`
Branch: main
Model tier: mid

## Goal

Determine whether a dedicated A-Worker 3 live Serena/tunnel integration target can be established without touching active Sunday-Conducter/Phase6 resources or silently provisioning an external transport resource.

## Read-only evidence — 2026-08-20

- candidate root `C:\AI\serena-instances\a-worker-03`: absent;
- candidate health port `18013`: free at preflight time;
- runtime executable exists at `C:\AI\dwb-serena-tunnel-starter\tunnel-client\tunnel-client.exe`;
- filesystem scan found a local `tunnel-id.txt` only under the active conductor instance; no third unique local tunnel reference was found;
- previously noted `A:\GitHub\serena-test` candidate is currently absent;
- validated conductor provisioning script contains an explicit `provision` flow and credential handling, therefore provisioning is an external/credential-bearing side effect rather than a pure local setup step.

## Decision gate — DR-P1-003

A-Conductor must not silently reuse an active worker's tunnel binding and must not automatically invoke the external tunnel-provisioning flow merely because credentials/scripts exist locally.

A Stage B live test may proceed only after a **dedicated unique transport binding** exists or explicit authorization is given for the external provisioning action. The test target must also use a disposable/read-only project target created specifically for A-Conductor validation.

This gate blocks only live Stage B validation. It does **not** block local process-manager, control-center service, desktop shell, Projects/Workers UI, or dummy-runtime integration work.

## Safety

- no active Conductor/Phase6 process mutation performed;
- no tunnel ID value read into tracked source;
- no credential value read or logged;
- no cloud provisioning command executed;
- no test repository mutated.

## Next safe action

Continue Phase 1 local Control Center implementation. Revisit this gate before Worker 3 live start/restart/stop validation.
