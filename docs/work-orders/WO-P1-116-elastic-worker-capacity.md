# WO-P1-116 — Production Worker Supply + Elastic Capacity (AHA-6B)

Date: 2026-08-30
Owner: GPT-5.6 Sol integrator
Status: COMPLETE / MERGED / POST_MAIN_GREEN / RELEASED
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-elastic-capacity`
Branch: `feat/wo-p1-116-elastic-worker-capacity`
Base: `origin/main@23243651d51780b76dce15cdb24eaba90fce9a99`
Parent: Sunday Family Multi-Model Agent Harness Accelerator

## Priority / why now

`WO-P1-096` remains the P0 release blocker. A stopped Worker4 is now running an isolated
`tunnel-client v0.0.13` maintenance soak without changing the shared v0.0.11 binary used by
Workers 1/2/3/5. READY uptime has exceeded ten minutes, but acceptance still requires a real
remote MCP request after TTL; uptime alone does not close the P0.

While that external request gate remains unresolved, AHA-6B is the next non-overlapping safe
accelerator slice. AHA-6A/AHA-6A.1 are merged and provider-global admission exists, but the
production pipeline still lacks authoritative assembly from durable worker/runtime/Git state
into scheduler/lease candidates and has no bounded elastic expansion path.

## Reuse-before-build verdict

Classification: `REUSE + WRAP + EXTEND`.
Reuse existing authorities:
- `graph.scheduler.WorkerSnapshot` / `SchedulePlan` for pure scheduling;
- `WorkerLeaseCandidate`, `WorkerLeaseBroker`, and `SQLiteWorkerLeaseStore` for worker capacity ownership;
- `ControlCenterService` / registry assignment for logical workers;
- `SQLiteSerenaConfigStore`, `SerenaProjectBinding`, lifecycle observation, and native Git readers;
- existing instance/runtime provisioning only through an injected, bounded adapter;
- A-Wiki work-order/claim/delegation protocols.

Architecture findings at shaping gate:
- `WorkerLeaseCandidate(...)` and `ParallelReadyTask(...)` are currently constructed only by tests;
- `build_sqlite_parallel_ready_executor(...)` exists, so execution has a production builder but worker/task supply does not;
- elastic capacity therefore belongs above the broker: assemble candidates → schedule/lease → on proven capacity exhaustion reserve one bounded provisioning slot → provision → re-observe → re-enter the existing broker;
- two concurrent elastic requests must not over-provision, so provisioning reservation extends the existing worker-capacity SQLite authority rather than using a process-local lock;
- logical/local execution capacity is distinct from a remote ChatGPT connector. Tunnel creation or Tunnel-ID reuse is never implicit.

Do not create:
- a second scheduler/router/task store/worker registry/lease store;
- a process-local semaphore as global elastic-capacity authority;
- implicit Tunnel ID creation/reuse, secret provisioning, or live connector mutation;
- provider-name-specific worker lifecycle rules;
- automatic rebind of busy/owned/dirty workers.

## Repository / lane safety contract
Preclaim evidence:
- `origin/main = 23243651d51780b76dce15cdb24eaba90fce9a99`;
- GitHub open PRs: `0`;
- A-Wiki remote main refreshed; local A-Wiki checkout remains dirty/read-only;
- A-Wiki live claim store: `0` claims;
- North Star worktree is clean and its unique file set does not overlap this slice;
- WO/branch/worktree ID collision: none;
- root checkout remains stale/dirty and protected.

Allowed implementation scope:
- additive `src/a_conductor/worker_candidate_assembly.py`;
- additive `src/a_conductor/elastic_worker_capacity.py`;
- focused tests for those seams;
- bounded extension of `src/a_conductor/worker_lease.py` + tests only for atomic provisioning reservation if RED proves it is required;
- bounded SSoT: this WO, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, accelerator/fallback plans,
  `docs/agent-collab/AGENT_TASKS.md`, `CAPABILITY_MATRIX.md`, and P0 WO evidence checkpoint.

Forbidden without explicit scope reopen:
- scheduler semantics in `graph/scheduler.py`;
- job/graph/provider stores, provider admission, retry/state machines;
- Control Center UI and North Star-owned runtime/UI/GPU files;
- existing worker/connector registry semantics, lifecycle coordinator, or instance scripts;
- A-Wiki mutation;
- live Workers 1/2/3/5 or shared tunnel-client binary;
- plaintext credentials, Tunnel IDs, or secret-bearing diagnostics.

## Acceptance criteria

1. A production assembler derives `WorkerSnapshot` and `WorkerLeaseCandidate` from durable Control Center/runtime/binding/Git/lease evidence; unknown/malformed evidence fails closed.
2. Actual branch/HEAD/dirty state is observed before mutation eligibility; persisted expected identity is not treated as current runtime truth.
3. Active leases/reservations become `reserved` / `active_task` / occupied mutable-scope evidence without inventing ownership.
4. The existing scheduler and broker remain authoritative; assembled candidates cannot bypass their capability, identity, health, scope, or lease gates.
5. Elastic expansion triggers only from typed capacity exhaustion after all existing eligible workers are considered. Capability/gate/provider/identity/policy failures never trigger provisioning.
6. Policy explicitly bounds maximum extra capacity and permitted runtime kinds. `elastic_enabled=False` or limit exhaustion returns typed WAIT/BLOCKED evidence with zero provisioning side effects.
7. Concurrent requests atomically reserve provisioning capacity in the existing worker-capacity SQLite authority so the configured limit cannot be exceeded across processes.
8. Provisioning uncertainty/partial failure becomes typed recovery; no blind retry, duplicate worker creation, or silent cleanup of ambiguous state.
9. A provisioned worker is never leased until it is re-observed with exact project/worktree/branch/HEAD/dirty/health/ownership/capability evidence.
10. Remote connector/tunnel provisioning is disabled by default and requires an explicit transport-capacity authorization surface; no Tunnel ID is inferred or reused.
11. Deterministic E2E proves fixed pool exhausted → exactly one bounded additional local/semantic worker → re-preflight → existing broker lease; a racing request does not over-provision.
12. Existing fixed-pool fallback/RDC/read-only behavior remains unchanged when elastic policy is disabled or inapplicable.
13. No second scheduler, registry, lease system, task store, provider store, retry loop, or memory authority is introduced.
14. Focused + related regression, compileall, diff/scope/secret/encoding audit, concurrency/chaos E2E pass.
15. Independent exact-SHA review precedes PR; exact-head 3-OS CI including Windows Frozen Setup E2E and post-main verification are required before release.

## Multi-agent lane rule

Fresh official Z.ai evidence (2026-08-30) reports GLM-5.3 Terminal-Bench 3.0 `28.3`,
DeepSWE v1.1 `66.9`, and Z.ai Code Bench Max `34.5%`; Z.ai also states meaningful
human-in-the-loop work remains. GLM-5.3 MAX is suitable for bounded implementation,
repository archaeology, adversarial tests, and read-only review after an exact task contract exists.

GPT-5.6 Sol retains architecture, worker/lease authority design, trust-boundary adjudication,
SSoT integration, PR/merge/release authority. Deterministic repository/runtime evidence is final authority.

External-agent communication uses ignored `runs/<task-id>/task.md` and `result.json`.
The human may relay one pointer only when automatic provider dispatch is unavailable; the human
never copies the external agent result back. GPT/Conductor validates task/model/HEAD/hashes and
folds accepted findings into tracked SSoT.

## RED-first slices

A. Production worker candidate/scheduler snapshot assembly from exact durable + live observations.
B. Fail-closed malformed/stale/dirty/identity/active-lease candidate tests.
C. Elastic policy + typed capacity-exhaustion decision; no provisioning for non-capacity failures.
D. Atomic provisioning reservation in existing worker-capacity authority; race test at limit `1`.
E. Injected local/semantic provisioner → re-observe candidate → existing broker lease vertical E2E.
F. Partial/unknown provisioning chaos, disabled policy, limit exhaustion, no-tunnel-default tests.
G. Broad regression/E2E/security audit → exact-SHA independent review → repair → PR/CI/re-audit/merge.

## Remote fallback checkpoint — 2026-08-31

Remote Desktop Commander disconnected after the RED tests were created and after a partial local
`worker_candidate_assembly.py` scratch file was written. Those local uncommitted files are **not
authoritative** and must not be merged/replayed by guesswork. Durable authority remains this
feature branch beginning at claim commit `6f0aa1355d668b82d6ee51c638b7a4e89f60e21c` and subsequent
GitHub commits.

While RDC is disconnected, GitHub is the only mutation surface for this WO. No second branch or
overlapping worker lane may mutate the same source scope. When RDC reconnects, the isolated local
worktree must fetch/recreate from the remote branch before any further mutation; abandoned local
scratch may then be removed only after remote equivalence is verified. Worker 1–5 availability
cannot be re-certified while the host is disconnected, so no SunDay-Worker mutation lane is
claimed from stale READY/process evidence.

Next safe action: continue RED/implementation on this single remote branch, use CI as the temporary
deterministic execution gate, and resume local focused/E2E verification only after RDC reconnects.

## 2026-08-31 implementation / local audit checkpoint

Slices A-F are locally implemented. `SQLiteWorkerLeaseStore` now owns provisioning reservation schema/transactions; the elastic adapter is compatibility-only. Production supply reads durable lease + provisioning reservations, live lifecycle/Git/binding evidence, and supports exact-owner re-observation during the provision?lease handoff.

Adversarial repairs completed: missing scheduler eligibility cannot trigger provisioning; `PROVISIONED`/`RECOVERY_REQUIRED` workers are reserved from competing sessions; successful capacity becomes `CAPACITY`; post-create observation/broker uncertainty becomes durable `RECOVERY_REQUIRED`; remote connector remains disabled without explicit transport authorization.

Verification: related `163 passed`; compileall/diff-check pass; spawned cross-process capacity race at `max_extra=1` yields exactly one winner; realistic fixed-pool E2E begins with one existing reserved worker (`workers_ready=0/1`) and reaches the existing runner on exactly one additional worker. CI-topology local run passed GUI 277 + local-instance 23 + supervised 11 + first 30 isolated core files, then stopped on missing GPU/OpenGL dependency in the shared Hermes venv outside WO scope. Exact-head GitHub CI is required before acceptance.

Worker lane preflight found Worker5 clean/idle and therefore the only fallback candidate, but its project was not rebound because no safe direct SunDay-Worker invocation surface is available in this chat. Workers 1-4 remain unavailable for reassignment for protected/active/dirty/P0 reasons. RDC remains the execution fallback.

Historical pre-release gate is superseded by the final release checkpoint below.

## Final release checkpoint — 2026-08-31

- Exact reviewed implementation head: `d06129ac943ceaa30c398d744b07a0fec9b505e1`.
- Independent GLM-5.3 MAX review: validated PASS; P0/P1/P2 = `0`; four P3 hardening notes are non-blocking follow-up candidates.
- Exact-head PR #157 CI `33352780461`: SUCCESS on Windows/Ubuntu/macOS including Windows Frozen Setup E2E.
- PR #157 merged as `af5a5068aea37ce82875e4b6fff40ac19ac112c5`.
- Post-main CI `33354156749`: SUCCESS on Windows/Ubuntu/macOS including packaging, Portable smoke and Frozen Setup E2E.
- Claim released; no successor mutable AHA lane is claimed by this closeout.
