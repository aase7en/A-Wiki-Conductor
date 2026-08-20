# Serena Runtime Manager Contract

Status: Phase 1 contract baseline
Active work order: `WO-P1-002`
Source basis: validated local multi-Serena deployment and runbook outside this repository, inspected read-only on 2026-08-20.

## 1. Purpose

Define how A-Conductor will manage Serena-backed A-Workers without copying the current project-pinned launcher scripts into the product.

The existing deployment is **validated implementation evidence**. The product target is a reusable worker pool, so stable safety concepts are preserved while machine/project-specific details become data/configuration.

No credential, tunnel identifier, API key, or decrypted secret belongs in this tracked contract.

## 2. Validated evidence from the current prototype

The current two-instance deployment has demonstrated these properties in real operation:

- separate process/runtime profile per concurrent worker instance;
- separate `SERENA_HOME` per instance;
- separate health listener per instance;
- project pinning at startup;
- cross-session active-project isolation;
- targeted stop by owned PID rather than broad process termination;
- idempotent start: an already-owned running instance returns `ALREADY_RUNNING` instead of spawning a duplicate;
- stale PID metadata can be removed when the recorded process no longer exists;
- PID/process/profile mismatch is treated as a hard refusal to stop the process;
- health readiness is checked through a local `/readyz` endpoint;
- startup preflight runs before the long-lived runtime process;
- startup detects occupied health ports;
- Phase6 additionally detects collision risk with the retained legacy tunnel binding;
- logs and runtime PID/profile metadata are separated into per-instance directories;
- rollback/recovery launchers are intentionally retained outside the product repository.

The runbook's verified migration state records both isolated instances ready concurrently and preservation of the Phase6 worktree/branch/HEAD during infrastructure migration.

## 3. Product boundary

### Serena remains responsible for

- semantic code/project tooling;
- LSP-backed code intelligence;
- project-local Serena state/config;
- MCP/tool behavior exposed by the Serena runtime.

### A-Conductor Runtime Manager owns

- reusable worker-slot identity;
- project assignment to a worker;
- per-worker Serena home/runtime profile allocation;
- process lifecycle supervision;
- tunnel binding ownership;
- health-port allocation;
- PID/process ownership verification;
- project-identity verification after startup;
- structured lifecycle/failure state;
- logs/evidence references;
- safe restart/release/recovery.

The Runtime Manager does not become a semantic code engine.

## 4. Reusable worker model vs current prototype

The current prototype is effectively:

`project -> dedicated instance -> dedicated Serena home/profile/port`

The product target is:

`A-Worker slot -> isolated runtime resources -> dynamically assigned Project`

Therefore **ProjectPath must not become permanent worker identity**.

Stable worker-owned resources may include:

- `worker_id` (`a-worker-01`, etc.);
- instance/runtime root;
- isolated Serena home;
- run/PID metadata directory;
- log directory;
- health-port allocation or allocation policy;
- tunnel/profile binding reference when the worker is exposed through that transport.

Assignment-owned resources include:

- `project_id`;
- target worktree path;
- expected repository identity policy;
- generated runtime project binding/profile material;
- active task/work-order references.

A worker may be released and reassigned without changing its stable worker ID.

## 5. RuntimeProfile contract

A future Serena runtime profile should represent at least:

| Field | Meaning | Persistence rule |
|---|---|---|
| `worker_id` | stable reusable worker slot | durable product config |
| `runtime_id` | current runtime instance identity | durable/operational |
| `instance_root` | isolated runtime root | machine-local config |
| `serena_home` | isolated Serena home | machine-local config |
| `assigned_project_id` | current Project metadata ID | operational state |
| `assigned_worktree` | current exact worktree target | machine-local operational state |
| `health_host` | local health bind host | machine-local config |
| `health_port` | worker-owned allocated port | machine-local config/state |
| `tunnel_binding_ref` | opaque reference to worker transport binding | secret-safe local config |
| `credential_ref` | opaque reference to credential material | secret store only |
| `runtime_executable_ref` | tunnel/runtime executable location | machine-local config |
| `profile_template_ref` | template used to render runtime profile | machine-local/product config |
| `run_dir` | generated PID/profile/runtime metadata | ignored local state |
| `log_dir` | worker-local operational logs | ignored local state |
| `startup_timeout_seconds` | bounded ready wait | product policy/config |
| `stop_timeout_seconds` | bounded targeted stop wait | product policy/config |

Tracked source should contain **references/policies**, not real secret values.

## 6. ProcessOwnership contract

A PID file alone is insufficient ownership proof because PIDs can be reused.

Before treating a process as owned, verify all required fingerprints:

1. PID metadata parses to a valid PID.
2. The PID currently exists.
3. Executable/process identity matches the expected runtime executable.
4. Process command/profile binding matches the expected worker runtime profile or equivalent fingerprint.
5. Where available, the process owns the expected health listener/runtime resources.

Ownership classifications:

- `ABSENT` — no PID metadata;
- `OWNED` — PID exists and expected fingerprints match;
- `STALE` — PID metadata exists but process no longer exists;
- `MISMATCH` — PID exists but belongs to an unexpected process/profile;
- `UNKNOWN` — ownership cannot be established safely.

Rules:

- `STALE` metadata may be reconciled/removed as a bounded recovery action.
- `MISMATCH` and `UNKNOWN` must **not** be stopped automatically.
- broad kill by executable name is forbidden.

## 7. Start contract

`start(worker, assignment)` must be idempotent.

### Preflight order

1. Validate worker/runtime configuration exists.
2. Validate assigned Project/worktree exists.
3. Validate isolated Serena config/home exists or can be created by the authorized provisioning path.
4. Resolve credential and tunnel/profile references without logging secret material.
5. Reconcile PID ownership state.
6. Refuse unexpected owned-process/profile mismatch.
7. Detect tunnel/profile collision with another live worker/legacy owner.
8. Detect health-port collision.
9. Render runtime profile into ignored local run state.
10. Run bounded runtime/tunnel preflight/doctor when supported.
11. Start exactly one long-lived owned runtime process.
12. Poll bounded readiness.
13. Verify assigned project identity after transport/runtime readiness.
14. Emit structured evidence and final state.

### Idempotency

If an already-running process is `OWNED`, bound to the same worker assignment, and identity/health checks pass, return an `ALREADY_RUNNING` success result. Do not create another process.

### READY definition

`READY` requires more than process existence.

For a Serena-backed worker, minimum readiness should include:

- expected owned process exists;
- health endpoint responds successfully;
- assigned project/worktree identity passes the configured identity policy;
- Serena reports the expected active project/allowed project binding where available;
- no collision/mismatch state is active.

A running process whose health never becomes ready is `UNHEALTHY`, not `READY`.

## 8. Stop contract

`stop(worker)` is targeted and idempotent.

1. No PID metadata -> return `NOT_RUNNING` success.
2. Invalid PID metadata -> `PID_MISMATCH`/invalid ownership failure; do not guess.
3. PID metadata whose process is absent -> reconcile stale metadata and return a recoverable stopped result.
4. PID exists but ownership fingerprints do not match -> `PID_MISMATCH`; refuse termination.
5. `OWNED` process -> stop that exact PID only.
6. Wait a bounded timeout for exit.
7. If it does not exit -> `TUNNEL_STOP_FAILED`/runtime stop failure; do not broad-kill unrelated processes.
8. Remove owned PID metadata only after confirmed exit/reconciliation.
9. Re-check health port/resource release and emit evidence.

## 9. Restart contract

`restart` is not `kill + start`.

It is:

`reconcile -> targeted stop -> verify released -> start -> verify READY/project identity`

If stop ownership cannot be proven, restart must fail rather than spawn a competing process.

## 10. Release/reassign contract

A Worker may be reassigned only when:

- no active task/lease still owns the assignment;
- owned runtime process is stopped or explicitly supports safe rebinding;
- health/tunnel resources are reconciled;
- previous project identity is cleared from operational assignment state;
- handoff/evidence for the prior assignment is durable.

Default MVP rule: **stop before reassign**.

A mutating worktree must not be assigned to two workers concurrently unless an explicit future policy proves isolation (for example, separate Git worktrees). Read-only multi-assignment is a future capability, not an MVP default.

## 11. Collision contracts

### Port collision

If the configured health port is already listening and ownership is not the expected worker process:

`PORT_IN_USE`

Do not select another random port silently. Allocation changes must update durable worker configuration/state.

### Tunnel/profile collision

A tunnel/profile binding is an owned resource. Two live workers may not concurrently claim the same binding unless the transport explicitly supports multiplexing and the product has a tested policy for it.

Collision result:

`TUNNEL_COLLISION`

Legacy bindings retained for rollback participate in collision checks while they remain operationally valid.

### Project/worktree collision

Default mutating policy:

one exact worktree -> one active mutating worker assignment.

A conflict must block assignment before process start.

## 12. Health and failure-state mapping

Use the core `HealthState` vocabulary where possible.

| Condition | Product state/result |
|---|---|
| no owned process | `STOPPED` |
| startup in progress | `STARTING` |
| process + ready + project identity pass | `READY` |
| active work executing | `BUSY` |
| graceful stop in progress | `STOPPING` |
| health process exists but readiness fails | `UNHEALTHY` |
| health port owned by unexpected process | `PORT_IN_USE` |
| transport binding already owned | `TUNNEL_COLLISION` |
| PID/process/profile ownership mismatch | `PID_MISMATCH` |
| assigned target missing | `PROJECT_NOT_FOUND` |
| Serena/repository active identity differs from assignment | `PROJECT_IDENTITY_FAILED` |
| evidence insufficient to classify | `UNKNOWN` |

Additional operation-level failures such as `TUNNEL_START_FAILED` or `TUNNEL_STOP_FAILED` should be evidence/error codes attached to the state rather than requiring every failure code to become a long-lived Worker state.

## 13. Status contract

Every A-Worker should expose the same structured status regardless of launcher implementation.

Minimum status:

- worker ID/display name;
- assignment/project ID;
- runtime ID/type;
- process ownership classification + PID when safe to show;
- health state;
- health endpoint state (not credentials);
- assigned project identity result;
- tunnel binding state using opaque/non-secret identity;
- last start/stop/health evidence refs;
- log reference/path;
- last error code/message (secret-redacted).

The current prototype has richer status tooling on one worker than the other; the product should normalize this through A-Conductor rather than maintaining per-project status scripts.

## 14. Secrets and runtime-generated profiles

Rules:

- credentials remain outside source control;
- tracked config stores only opaque credential references;
- decrypted secret material must never be logged;
- generated runtime profiles containing secret material belong only in ignored local runtime state with appropriately restricted access;
- UI/status APIs must redact secret values and avoid echoing sensitive command lines;
- logs should capture error codes/context without copying credentials;
- repository publication must not include machine-private secret paths/identifiers unnecessarily.

## 15. Evidence contract

Each lifecycle operation should emit Evidence Records for relevant steps:

- configuration/preflight result;
- PID ownership classification;
- port/tunnel collision checks;
- process start/stop result;
- readiness/health result;
- project identity verification;
- stale PID reconciliation;
- final lifecycle state;
- warnings/rollback requirement.

An LLM statement such as "worker started" is not sufficient operational evidence.

## 16. Reuse classification

### REUSE

Preserve these proven concepts:

- isolated Serena home per concurrent worker;
- per-worker process/PID metadata;
- per-worker logs;
- dedicated health resource;
- PID + process/profile ownership validation;
- targeted stop;
- idempotent start/stop;
- readiness polling;
- startup preflight;
- stale PID reconciliation;
- collision checks;
- rollback launcher retained outside normal product flow.

### WRAP during migration/debugging

Existing manual `.cmd`/PowerShell launchers may remain operator recovery/debugging tools and can be observed by A-Conductor during transition.

They should not become the long-term product API.

### EXTEND for A-Conductor

Add product-level capabilities not provided by the fixed manual prototype:

- reusable `A-Worker 1..3` slots;
- dynamic project assignment;
- central port/tunnel ownership registry;
- normalized status model;
- project/worktree collision prevention;
- structured evidence;
- task/lease awareness;
- release/reassign lifecycle;
- UI/operator state;
- future non-Serena runtime compatibility.

### DO NOT COPY INTO PRODUCT SOURCE

- hard-coded project-specific worker bindings;
- concrete machine-specific paths as architectural constants;
- real tunnel IDs/profile secrets;
- decrypted credential material;
- legacy secret/config paths as product assumptions;
- broad process-kill patterns;
- "keep this command window open" as the product lifecycle model.

## 17. Next implementation boundary

The next source-code work should implement **pure runtime configuration/ownership/collision validation first**, test-first, without spawning or killing processes.

Only after those deterministic validators are green should A-Conductor implement actual start/stop supervision.
