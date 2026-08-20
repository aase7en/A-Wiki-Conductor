# Lifecycle Integration Test Strategy

Status: Phase 1 pre-live-mutation safety strategy
Decision gate: `DR-P1-002`

## 1. Purpose

Define how A-Conductor will prove concrete lifecycle mutation safely without using an active Conductor/Phase6 worker as the first target.

The strategy is intentionally staged:

1. **Stage A — self-owned dummy runtime process**: prove process/profile/PID/health/checkpoint lifecycle mechanics against a process created solely by the test harness.
2. **Stage B — dedicated isolated A-Worker 3 with Serena/runtime transport**: prove the same lifecycle against a real Serena-backed worker after Stage A is green and dedicated resources are configured.
3. **Stage C — Control Center operator flow**: only after Stage B, exercise assign/start/status/stop/release through the product-facing control path.

No stage may broad-kill processes or reuse an active worker's runtime/tunnel binding.

## 2. Current read-only candidate inventory

Observed on 2026-08-20; these are **candidates, not reservations or approvals**:

- dedicated `a-worker-03` instance root: not present at inspection time;
- candidate health port `18013`: no LISTENING socket observed at inspection time;
- local `serena-test` repository: exists, branch `main`, clean worktree, no Git remote observed;
- current active/validated runtime roots include Conductor and Phase6 and must not be the first mutation targets;
- legacy runtime material remains retained for rollback and participates in collision safety where applicable.

Port/resource availability must be re-checked immediately before any future provisioning or live test. A clean result today is not a reservation.

## 3. Stage A — Self-Owned Dummy Runtime

### Goal

Validate the concrete lifecycle backend's host-mutation mechanics without Serena, tunnel credentials, user repositories, or active AI sessions.

### Test runtime

Use a small test helper process created by the test harness itself. It should:

- have a unique per-test runtime marker/profile marker;
- write/use only a test-owned temporary runtime directory;
- expose a loopback-only `/readyz` endpoint on a test-selected free port;
- remain alive until targeted stop;
- contain no external credentials;
- be identifiable by exact PID plus expected executable/profile marker.

The helper must not impersonate or reuse a real Serena/tunnel process.

### Required test cases

1. Start from reconciled `ABSENT/FREE` state.
2. Verify exact owned PID is captured.
3. Verify health port ownership and `/readyz` READY.
4. Verify idempotent second start returns already-running/no duplicate process.
5. Verify targeted stop terminates only the exact owned PID.
6. Verify stopped health port is released.
7. Verify stale PID metadata produces recovery rather than blind start/stop.
8. Verify PID mismatch refuses termination.
9. Verify occupied test port blocks start before process spawn.
10. Verify checkpoint journal receives every successful symbolic step in order.
11. Inject checkpoint failure after a mutating step and verify no later step executes.
12. Inject backend uncertainty after start/stop and verify `RECOVERY_REQUIRED`.
13. Verify cleanup never falls back to broad process-name termination.

### Stage A evidence

Record only safe test evidence:

- transaction ID;
- symbolic lifecycle plan;
- exact test-owned PID;
- test port;
- ownership classifications;
- checkpoint sequence;
- ready/stop results;
- sanitized stdout/stderr/error codes;
- final process/port reconciliation.

### Stage A success gate

Stage A is complete only when the lifecycle backend can repeatedly pass the above tests without touching any pre-existing process, runtime directory, or repository.

## 4. Stage B — Dedicated A-Worker 3 Serena Integration

Stage B may begin only after Stage A is green.

### Dedicated resource requirements

A-Worker 3 must receive its own:

- stable worker ID: `a-worker-03`;
- instance/runtime root;
- isolated `SERENA_HOME`;
- run/PID metadata directory;
- log directory;
- health port allocated after a fresh collision check;
- dedicated runtime/transport profile;
- dedicated tunnel/transport binding reference if external connector exposure is required;
- credential reference resolved through a secret-safe mechanism, never copied into repository configuration;
- assigned Project/worktree distinct from active Conductor/Phase6 targets.

No resource above may silently reuse a live worker's ownership.

### Candidate health port

`18013` is a current candidate only because no listener was observed during the read-only preflight. It must be revalidated immediately before allocation.

Do not silently fall back to a random port if it becomes occupied. Allocation state must be explicit and durable.

### Candidate project

The existing local `serena-test` repository is currently a reasonable **read-only identity-test candidate** because the inspected worktree was clean and no remote was observed.

Rules:

- re-check branch/HEAD/dirty state immediately before use;
- initial Stage B assignment should be `mutation_allowed = false`;
- do not edit/reset/clean/stash/checkout/switch/rebase/merge the candidate repository;
- if mutation tests are later required, use a disposable dedicated test repository/worktree rather than converting the read-only identity candidate into an ad-hoc mutation target.

## 5. Stage B test sequence

Use one micro-transaction at a time.

### B0 — Identity and ownership gate

Before provisioning/start:

- dedicated worker ID confirmed;
- instance root is either absent or proven owned by A-Worker 3;
- Serena home is unique;
- port is free;
- transport binding is unowned by other workers;
- candidate project exists and expected identity is recorded;
- active Conductor/Phase6 PIDs/resources are captured only as **forbidden-owner baselines**, not targets;
- checkpoint journal is writable;
- rollback/recovery path is documented.

Failure of any gate stops the test.

### B1 — Provision local runtime state

Provision only A-Worker 3-owned local runtime files/directories.

Required constraints:

- no real secret values in tracked files/logs;
- generated secret-bearing profiles remain ignored local state;
- every created path is attributable to A-Worker 3;
- provisioning evidence/checksum recorded where useful.

### B2 — Start

Execute exactly the approved START lifecycle transaction.

Required evidence:

- preflight PASS;
- exact PID ownership;
- no port/tunnel collision;
- READY health;
- expected Serena/project identity;
- durable checkpoint after each successful step.

If a mutating step succeeds but checkpoint persistence fails, stop normal execution and enter recovery.

### B3 — Idempotent start

Repeat START against the verified owned healthy runtime.

Expected result: `NOOP / ALREADY_RUNNING`; no second runtime process.

### B4 — Targeted stop

STOP may execute only if PID/process/profile ownership is proven.

After stop:

- exact owned PID exited;
- health port released;
- no unrelated runtime PID changed;
- owned PID metadata reconciled according to the approved backend contract;
- final checkpoint/evidence recorded.

### B5 — Restart

Only after B2-B4 are individually green, test:

`targeted stop -> verify released -> start -> verify READY/project identity`

Never implement restart as broad kill + spawn.

### B6 — Release/reassign readiness

Confirm worker resources are reconciled and the assignment can be released without modifying the project repository.

A later test may assign another read-only disposable/candidate project to prove worker reuse.

## 6. Forbidden first targets

The following are explicitly forbidden as the **first** concrete lifecycle mutation target:

- active `Sunday-Conducter` worker/session;
- active Phase6 worker/session;
- any process whose PID/profile ownership is ambiguous;
- any runtime/tunnel binding already owned by another worker;
- any dirty user repository as a mutation target;
- any production service or important persistent workload.

This protects the exact control/session infrastructure being used to build A-Conductor.

## 7. Abort conditions

Abort the current lifecycle transaction immediately on any of these:

- PID/process/profile mismatch;
- port collision;
- tunnel/profile collision;
- unexpected active project/worktree identity;
- dirty-state drift in a repository expected to be clean/read-only;
- checkpoint persistence failure after mutation;
- backend outcome uncertainty;
- expected owned process cannot be proven;
- credential or transport binding cannot be resolved safely;
- test scope expands outside the dedicated worker/runtime root;
- another work order/claim begins touching the same runtime surface.

Abort means **stop normal progression and reconcile**. It does not mean broad kill/reset/cleanup.

## 8. Rollback and recovery

Rollback must be ownership-scoped.

- terminate only a process whose ownership fingerprint is proven;
- never broad-kill `python.exe`, `serena.exe`, or `tunnel-client.exe`;
- remove/rewrite only A-Worker 3-owned test runtime metadata after process/resource reconciliation;
- preserve logs/checkpoints needed to explain partial mutation;
- if ownership is `MISMATCH` or `UNKNOWN`, do not terminate automatically;
- if mutation is ahead of journal, enter recovery and reconstruct actual state before retry;
- current validated manual launchers remain recovery/debugging evidence until A-Conductor lifecycle is proven.

## 9. Evidence required to resolve DR-P1-002

`DR-P1-002` may be considered resolved for implementation progression when:

1. Stage A dummy-runtime integration is automated and green.
2. A dedicated A-Worker 3 runtime root/resource set is identified and collision-free at provisioning time.
3. Dedicated Serena/transport profile/binding can be created without reusing Conductor/Phase6 resources.
4. Secrets are referenced through a safe local mechanism and do not enter source control/log output.
5. A read-only/disposable test Project identity is confirmed immediately before Stage B.
6. Rollback/recovery procedure is executable using exact ownership only.
7. Lifecycle checkpoint journal is available and writable.
8. The first Stage B live mutation has explicit bounded scope and is not performed against an active development worker.

## 10. Remaining prerequisite requiring external/user/provider action

Stage A requires no external provider credentials and can be implemented next.

Stage B may require a **dedicated transport/tunnel binding or connector configuration** for A-Worker 3 if the Serena instance must be reachable through the same external ChatGPT transport used by existing workers. That binding must be separate from current Conductor/Phase6 bindings and represented in A-Conductor only by opaque references.

Do not reuse a current connector binding merely to avoid provisioning effort.

If Stage B can first validate Serena locally without external connector exposure, prefer that narrower test before adding the transport layer; external connector/tunnel validation can then be a separate bounded step.

## 11. Next safe implementation step

Implement Stage A only:

- dummy self-owned runtime helper;
- concrete lifecycle mutation backend constrained to test-owned resources;
- unit/integration tests proving exact ownership, targeted stop, idempotent start, checkpoint gating, and recovery behavior.

Do not provision or mutate A-Worker 3 during that work order.
