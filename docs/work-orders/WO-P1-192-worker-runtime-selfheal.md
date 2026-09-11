# WO-P1-192 — Windows Worker runtime self-heal deployment

Status: READY_FOR_GLM_OPERATIONAL_EXECUTION / GPT-INTEGRATOR CONTROLLED
Date: 2026-09-11 (Asia/Bangkok)
Risk: R3 operational/runtime
Parent incident: WO-P1-156 Worker / MCP Transport Resilience
Repository: `aase7en/A-Wiki-Conductor`
Windows host: `DESKTOP-7IB57R4`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo192-worker-runtime`
Branch: `ops/wo-p1-192-worker-runtime-selfheal`
Bootstrap base: `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`
Execution owner: ZCode / GLM-5.3 MAX on the Windows host
Acceptance / operational adjudication / any source-repair merge: GPT-5.6 Sol integrator
Execution packet: `docs/prompts/GLM-WAVE12-20H-WORKER-RUNTIME-RESILIENCE.md`
Result destination: `runs/WO-P1-192/result.md`
Checkpoint destination: `runs/WO-P1-192/checkpoint.md`

## User outcome

Stop Sunday-Worker 1–5 from disappearing when their `tunnel-client.exe` exits, without creating a second recovery authority or destroying active work.

Observed 2026-09-11 causal chain:

`tunnel-client exits -> start.ps1 WaitForExit/Fail -> PowerShell wrapper closes -> Serena stdio child tears down -> Worker disappears`

The durable fix is not “keep PowerShell open at all costs”. The durable fix is:

1. deploy the already-merged A-Sunday Conductor connector self-heal/recovery path;
2. preserve numeric tunnel exit reason + runtime logs so recurrence is diagnosable;
3. migrate/verify the live runtime state safely with backups and rollback;
4. roll supported tunnel-client binaries through bounded canary/fleet gates;
5. prove exact-PID recovery and manual-stop semantics on a sacrificial eligible Worker;
6. only then expand to the fleet.

## Proven starting evidence

At activation:

- Windows Workers are reachable independently of RDC; RDC is currently attached to macOS and is not the Windows runtime authority;
- Workers 1–5 run through `Start-Sunday-Worker-N.cmd -> start.ps1 -> tunnel-client.exe -> Serena`;
- live Worker health ports are `127.0.0.1:18011..18015`;
- W1 uses checksum-verified tunnel-client `0.0.14` canary;
- W2–W5 are bound to shared legacy tunnel-client `0.0.11`;
- W1 0.0.14 also exited on 2026-09-11, so upgrading the binary alone is not sufficient proof of a complete fix;
- current installed `A-Sunday Conductor.exe` predates the merged WO156 source recovery path;
- live `control-center.sqlite` inspection showed no `instance_recovery` table;
- WO156/PR #218 merged the production recovery path;
- existing runbook `docs/runbooks/wo156-live-tunnel-upgrade-and-chaos.md` is the operational authority to reuse;
- historical launcher hardening work records that old launchers can lose the numeric exit code and overwrite fixed stdout/stderr on restart.

Re-pin all of this before action. Embedded values are observations, not future authority.

## Architecture rule

REUSE the existing `ConnectorRecoveryCoordinator`, installed Control Center recovery state, existing Worker specs, exact-PID process identity, existing launcher materialization, existing runbook, and existing rollback path.

Do NOT add a PowerShell infinite restart loop, watchdog loop, second recovery store, second retry budget, broad process killer, or second Worker supervisor.

One transient tunnel failure must be absorbed by the accepted central recovery authority, not amplified into permanent Worker disappearance.

## Operational safety gates

Before changing a running Worker/runtime:

- identify exact Worker, project, task, worktree/branch/HEAD where applicable;
- verify owner/claim/lease and recent activity;
- verify dirty/untracked state;
- determine whether task outcome is known;
- classify Worker as `ELIGIBLE_SACRIFICIAL`, `ACTIVE_TASK_PROTECTED`, `OWNERSHIP_UNKNOWN`, or `NOT_ELIGIBLE`;
- never infer “free” from Active Project alone;
- exact PID + creation time + executable + command identity are required before process action;
- no broad `taskkill` / process-name kill;
- no live DB replacement without verified backup and copied-DB migration proof;
- no credential contents in logs/evidence;
- no disabling ESET or other security tooling globally;
- no fleet rollout before a one-Worker canary passes.

Unknown state fails closed.

## Phase 0 — recover exact state

Read:

- `00-AGENT-ENTRY.md`;
- `PROJECT-GRAPH.yaml` routed nodes;
- `AGENTS.md`;
- this WO;
- `docs/work-orders/WO-P1-156-worker-mcp-resilience.md`;
- `docs/runbooks/wo156-live-tunnel-upgrade-and-chaos.md`;
- relevant launcher/materialization/release docs;
- `DEFECT_LESSONS.md` before any source mutation.

Collect current:

- Windows host identity/version;
- installed A-Sunday Conductor executable path/hash/timestamp/version if exposed;
- live Control Center DB path/schema/table list/integrity (read-only first);
- exact Worker 1–5 wrapper/tunnel/Serena PIDs and process trees;
- health ports and `/readyz`;
- current tunnel-client path/version/hash per Worker;
- current launcher hashes and whether runtime log rotation/numeric exit capture is present;
- current source `origin/main` and WO156 accepted code/tests;
- Worker task/claim/lease/readiness matrix.

Write the matrix to `runs/WO-P1-192/checkpoint.md` before any operational mutation.

## Phase 1 — determine deployment gap precisely

Prove which of these are true now:

- installed app lacks accepted recovery code;
- live DB lacks required recovery schema;
- installed launcher templates are old;
- materialized Worker scripts are old;
- shared tunnel-client is below supported floor;
- current source has all required fixes and tests;
- any newer accepted release/build supersedes the historical runbook assumptions.

Classify each gap as `SOURCE_GAP`, `DEPLOYMENT_GAP`, `MATERIALIZATION_GAP`, `BINARY_GAP`, `TELEMETRY_GAP`, or `NO_GAP`.

Do not modify source if the problem is already fixed in source and merely not deployed.

## Phase 2 — build/prepare accepted runtime safely

Use repository-supported build/package/install flow only.

Before touching live state:

1. select exact accepted source SHA;
2. run required focused recovery/installer tests for that SHA;
3. build/package using documented procedure;
4. record artifact hash;
5. back up the current installed executable/package as permitted by runbook;
6. make a timestamped backup of the live DB/config metadata without copying secret values into repo evidence;
7. run migration against a copied live DB first;
8. prove table/data preservation + integrity check + rollback;
9. verify the copy gains the expected recovery schema/state;
10. only then authorize live install/migration.

If copied-DB migration or rollback proof fails, do not mutate live DB.

## Phase 3 — launcher telemetry hardening check

For each materialized Worker launcher, verify whether current accepted materialization provides:

- preserved numeric `Process.ExitCode`;
- non-destructive/rotated runtime stdout/stderr;
- timestamped archived failure evidence;
- no secret leakage;
- no duplicate supervisor/retry loop.

If source supports this but existing live materialization is stale, rematerialize using the supported tool/path while preserving Worker identity, tunnel IDs, project bindings, and secret references.

Do not hand-edit five launchers independently unless the repo runbook explicitly requires it as bounded emergency recovery and no supported materialization path exists.

## Phase 4 — one-Worker canary

Choose exactly one Worker proven `ELIGIBLE_SACRIFICIAL` after a fresh ownership/task gate.

Canary sequence:

1. checkpoint task/claim/worktree/process identity;
2. verify current `/readyz` and remote MCP reachability;
3. if binary rollout is needed, update only this Worker first;
4. start through durable supported Worker spec;
5. verify exactly one wrapper, one tunnel-client, one Serena chain and healthy port;
6. exercise normal tool callability;
7. inject the bounded failure specified by WO156 using exact PID only after re-validating PID + start identity;
8. observe central recovery;
9. require exactly one new tunnel/Serena pair;
10. require `/readyz` healthy;
11. require no duplicate/orphan process;
12. require task/claim identity preserved and no blind task replay;
13. require durable restart reason/count evidence;
14. verify old process identity is gone;
15. verify failure telemetry survived restart and includes useful exit/reason information;
16. verify manual Stop remains stopped and is not auto-restarted;
17. restore normal running state only if permitted by the Worker task/owner state.

A failed canary blocks fleet rollout.

## Phase 5 — fleet rollout

Only after canary PASS:

- drain/checkpoint one Worker at a time;
- preserve project/task/claim state;
- apply supported binary/materialization/runtime update;
- start from durable spec;
- verify process tree, port, remote callability, log/telemetry and recovery registration;
- proceed to the next Worker only after the current one is proven healthy.

Never restart all five simultaneously merely for convenience.

W1 0.0.14 history proves that “new binary is alive” is not sufficient; central self-heal and telemetry must also be proven.

## Phase 6 — soak / recurrence evidence

During the available long session:

- observe health transitions without aggressive polling;
- correlate any new tunnel exit with durable telemetry;
- classify cause where evidence permits;
- verify automatic recovery if a spontaneous recurrence happens;
- do not manufacture repeated destructive chaos after acceptance evidence is already sufficient;
- if ESET/security software remains a hypothesis, collect correlation evidence first; do not disable globally.

## Source-repair escape hatch

Default scope is operational deployment, not new product code.

If deterministic evidence proves a remaining source defect on current main:

- do not patch broadly in this ops lane;
- minimize/reproduce it;
- write a bounded child repair proposal in `runs/WO-P1-192/result.md` with exact files/tests/risk;
- source mutation requires a fresh non-overlapping work order/claim;
- GPT-5.6 Sol reviews/accepts any source repair before merge.

## Verification / acceptance

WO192 is operationally accepted only if:

- installed runtime actually contains the accepted self-heal path;
- live DB/schema/state is coherent after verified migration;
- launcher telemetry no longer destroys the only useful crash evidence;
- at least one eligible sacrificial Worker passes exact-PID tunnel failure -> exactly-one self-heal -> healthy remote MCP;
- manual Stop remains suppressed;
- no duplicate/orphan processes exist;
- no active task is blindly replayed;
- fleet rollout, if performed, is one-at-a-time and each Worker is individually verified;
- rollback path remains available;
- no secrets are persisted in repo/issues/log excerpts;
- result contains exact evidence and remaining uncertainty.

## 2026-09-11 GPT pre-deployment evidence checkpoint

This checkpoint supersedes older deployment assumptions but does not authorize live installation by itself.

- installed HKCU uninstall record reports A-Sunday Conductor 0.6.0 at `C:/Users/aase7en/AppData/Local/Programs/A-Sunday Conductor`; current repository source `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7` declares 0.7.0, so accepted recovery source is not yet the installed product;
- current-source focused recovery battery passed `45/45` across connector recovery, visibility, desktop-control recovery, Serena config-store and worker-resilience tests;
- copied-live-DB proof: live DB SHA-256 stayed `34AE10EDE1BE7F60F0655EE498296DAE358D9E423FD9F54C6B8D4F1D1E6E02CF` before/after; copied DB `integrity_check=ok`; `instance_recovery` was the only new table; all pre-existing row counts were preserved;
- frozen 0.7.0 portable built from exact current source under `%TEMP%`, SHA-256 `38B93B011DEE53A5716631964BE4FC5E277E6CEEC6D0F644EF247856C671B862`; `--smoke` passed including against a copied live DB (`A-CONDUCTOR_SMOKE_OK projects=8 workers=8`);
- frozen Setup candidate built but NOT installed: SHA-256 `5CF41659D8BF4E44395111182A3CC86B0ADD7CAFD45A099823BA781FDDB95D76`;
- do not run `verify_frozen_installer_e2e.py` on this active host while 0.6.0 is installed because that verifier requires the HKCU uninstall key to be absent and would collide with the live install; use a clean/sacrificial host or isolated registry-safe proof;
- build output under `A:/GitHub/.../runs` inherited NTFS `Compressed` and became `ERROR_ACCESS_DENIED` for read/hash/execute despite normal ACL; the same source built under uncompressed `%TEMP%` was readable/runnable. Running `compact /U` on the ignored A-drive candidate immediately restored hash/read/`--smoke`, so use an uncompressed build/output path for deployment artifacts. This is a packaging-path/compression interaction and is not evidence that NTFS compression or ESET caused the unrelated Worker tunnel exits;
- Worker health recheck after the 14:39 restart: ports 18011..18015 all returned HTTP 200 `ready`; W1 uses 0.0.14 canary, W2/W3/W4/W5 still use legacy 0.0.11; no new lifecycle failure had been logged at this checkpoint.

GLM should reuse this evidence rather than repeat unchanged probes. Before any live install, re-pin only facts that can drift: installed process/version, DB hash/integrity, Worker task/claim/lease state, exact PIDs/start identities, health, and current source/PR acceptance.

## Result contract

`runs/WO-P1-192/result.md` must include:

- final status;
- current source SHA and installed artifact identity;
- live DB backup/migration proof summary;
- Worker 1–5 before/after matrix;
- tunnel-client path/version/hash per Worker;
- launcher telemetry/materialization verdict;
- chosen canary and why it was eligible;
- exact old/new process identities for chaos proof;
- recovery count/reason and `/readyz`/remote MCP proof;
- manual-stop proof;
- orphan/duplicate-process audit;
- spontaneous recurrence observations if any;
- unresolved initiating-cause hypotheses;
- source repair needed YES/NO;
- rollback state;
- exact next safe action.

Final status must be one of:

- `INSTALLED_SELF_HEAL_ACCEPTED`
- `CANARY_PASS_FLEET_PENDING`
- `DEPLOYMENT_BLOCKED`
- `OWNERSHIP_BLOCKED`
- `SOURCE_REPAIR_REQUIRED`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`

Do not report success merely because PowerShell windows remain visible.
