# GLM WAVE 12 — 20-HOUR WINDOWS WORKER RUNTIME RESILIENCE `/goal`

## MASTER `/goal`

Execute WO-P1-192 on Windows host `DESKTOP-7IB57R4` to eliminate the recurring Worker 1–5 disappearance caused by tunnel-client exits, using the accepted central recovery architecture rather than a second PowerShell watchdog.

This is a useful-work envelope up to roughly 20 hours, not a requirement to consume 20 hours. Finish as soon as the operational acceptance gate is genuinely satisfied. Never burn time/tokens with repeated unchanged probes.

Primary target:

`tunnel transient/exit -> durable central detection -> exactly one bounded recovery -> healthy Worker again -> preserved task/claim -> useful crash evidence survives`

Not the target:

`PowerShell window never closes`.

---

# FRESH GPT EVIDENCE OVERRIDE — 2026-09-11

Reuse these already-proven facts; do not repeat them unless a driftable fact changed:

- installed A-Sunday Conductor is 0.6.0; current source/candidate is 0.7.0 at `origin/main@46f90b329d4991211f5c8a26406f3aca2162e9a7`;
- recovery-focused current-source tests passed `45/45`;
- copied-live DB migration is proven integrity-safe and adds `instance_recovery` without changing pre-existing row counts; live DB hash remained unchanged;
- frozen 0.7.0 portable under `%TEMP%` passed smoke against a copied live DB;
- 0.7.0 Setup candidate is built but not installed;
- do not run the clean-host frozen installer E2E on this active 0.6.0 host because the HKCU uninstall key is occupied;
- artifact output under `A:/GitHub/.../runs` inherited NTFS `Compressed` and hit `ERROR_ACCESS_DENIED`; the `%TEMP%` build was readable/runnable, and `compact /U` on the ignored A-drive candidate restored hash/read/`--smoke`. Use an uncompressed build/output path for deployment artifacts. Do not generalize this packaging-path finding into a Worker tunnel root cause or an ESET verdict;
- W1-W5 were all ready at the latest recheck; W1=0.0.14 canary, W2-W5=0.0.11 legacy.

Before live deployment, refresh ownership/task/lease/process/health and installed/version state. Do not reinterpret this checkpoint as authority to disrupt a busy Worker.

---

# 0. COLD START

Read in this order:

1. `00-AGENT-ENTRY.md`
2. routed nodes from `PROJECT-GRAPH.yaml`
3. `AGENTS.md`
4. `docs/work-orders/WO-P1-192-worker-runtime-selfheal.md`
5. `docs/work-orders/WO-P1-156-worker-mcp-resilience.md`
6. `docs/runbooks/wo156-live-tunnel-upgrade-and-chaos.md`
7. relevant release/installer/materialization docs selected by project graph
8. `DEFECT_LESSONS.md` before any source mutation

Then re-pin actual:

- Windows host identity and OS;
- repo/worktree/branch/HEAD/origin/main/dirty state;
- installed A-Sunday Conductor process/path/artifact identity;
- live Control Center DB path/schema/integrity;
- exact Worker 1–5 wrapper/tunnel/Serena process trees;
- ports 18011..18015;
- `/readyz` and remote MCP callability;
- current project/task/claim/lease/readiness for every Worker;
- tunnel-client path/version/hash per Worker;
- launcher/template/materialization versions/hashes;
- current open claims/PRs that could affect deployment.

Write the complete preflight matrix to `runs/WO-P1-192/checkpoint.md`.

Unknown ownership, dirty-state meaning, task outcome, or exact PID identity fails closed for mutation.

---

# 1. ROLE

You are GLM-5.3 MAX operating/debugging lane on the Windows host.

You may:

- inspect runtime/repo/Git/GitHub state;
- run deterministic read-only diagnostics;
- build/package from an exact accepted source SHA using documented repo procedures;
- make copied-DB migration/rollback proofs;
- deploy the already-accepted runtime only after all WO192 gates pass;
- perform exact-PID canary chaos only on a Worker freshly proven sacrificial/eligible;
- checkpoint evidence;
- repair operational configuration/materialization only through supported mechanisms authorized by WO192.

You may not:

- invent a second restart/watchdog authority;
- broad-kill process names;
- destroy/reset/stash unexplained work;
- expose credentials/tunnel secrets;
- globally disable security software;
- blindly update all five Workers simultaneously;
- replay an active/unknown task;
- self-approve a new source repair;
- merge/release source changes.

GPT-5.6 Sol retains architecture/source-repair acceptance and final operational adjudication.

---

# 2. PROVE THE CURRENT FAILURE MODEL

First determine whether current evidence still supports:

`tunnel-client exit -> start.ps1 WaitForExit/Fail -> wrapper closes -> Serena child loses stdio -> Worker disappears`

Recover today's and retained logs without destroying them.

Distinguish:

- initiating tunnel exit cause;
- wrapper amplification;
- missing installed self-heal;
- missing schema/migration;
- stale launcher materialization;
- legacy binary exposure;
- logging/forensic evidence loss.

Do not call PowerShell itself the root cause unless evidence proves PowerShell crashed independently.

---

# 3. GAP CLASSIFICATION

For every relevant layer classify exactly one or more:

- `SOURCE_GAP`
- `DEPLOYMENT_GAP`
- `MATERIALIZATION_GAP`
- `BINARY_GAP`
- `SCHEMA_GAP`
- `TELEMETRY_GAP`
- `OWNERSHIP_BLOCK`
- `NO_GAP`

Explicitly compare current installed behavior with current accepted source and WO156.

If source is already correct, do not modify source to solve a deployment gap.

---

# 4. SAFE DEPLOYMENT PREP

Before live mutation:

- choose exact accepted source SHA;
- run focused recovery/installer/materialization tests appropriate to that SHA;
- build/package by repository-supported procedure;
- hash the built artifact;
- preserve a rollback copy/reference to current installed artifact;
- back up live DB/config metadata according to runbook without exposing secret values;
- migrate a COPY of the live DB first;
- prove integrity/data preservation/expected recovery schema/rollback on the copy;
- compare generated launcher/materialization behavior to current live launchers;
- preserve current Worker/tunnel/project binding identities.

Do not mutate live DB if copied migration/rollback proof is not green.

---

# 5. TELEMETRY REQUIREMENT

A restart must not erase the best evidence of why the previous process died.

Verify or establish through supported accepted materialization:

- numeric tunnel-client exit code when available;
- typed reason when exit code cannot be recovered;
- rotated/timestamped stdout/stderr instead of destructive overwrite;
- useful runtime lifecycle timestamps;
- no secret-bearing logs;
- exact Worker/process identity correlation.

Do not independently hand-patch five PowerShell scripts unless the supported materializer is unavailable and the existing runbook explicitly permits a bounded emergency path.

---

# 6. SELECT ONE SACRIFICIAL CANARY

For each Worker 1–5 build:

`Worker | project | task | claim/lease | repo/worktree | dirty | recent activity | wrapper PID | tunnel PID | Serena PID | health | eligibility`

Only a Worker classified `ELIGIBLE_SACRIFICIAL` may be disrupted.

A Worker is NOT eligible merely because:

- plugin responds;
- project looks idle;
- old chat said it was free;
- PowerShell window is visible;
- task outcome is unknown.

If none are eligible, do not inject chaos. Complete all safe deployment/preparation work and return `OWNERSHIP_BLOCKED` with exact blocker.

---

# 7. CANARY DEPLOYMENT

On exactly one eligible Worker:

1. checkpoint current identity/state;
2. deploy the accepted runtime/materialization/binary changes needed by the proven gap;
3. start from durable supported Worker spec;
4. verify exactly one wrapper + one tunnel + one Serena chain;
5. verify health port and `/readyz`;
6. verify remote MCP tool callability;
7. verify no task replay occurred;
8. verify recovery state/registration exists.

Do not proceed to chaos until normal canary behavior is green.

---

# 8. EXACT-PID FAILURE INJECTION

Immediately before destructive test re-read exact:

- PID;
- process creation time;
- executable path;
- command line/profile identity;
- Worker ownership/eligibility.

Terminate ONLY the exact sacrificial tunnel-client process using the existing WO156 chaos procedure.

Then require:

- old tunnel PID gone;
- old Serena child reconciled/gone as expected;
- central Conductor observes failure;
- exactly one bounded restart;
- exactly one new tunnel process;
- exactly one new Serena child;
- health returns;
- remote MCP reconnects;
- no duplicate wrapper/process tree;
- task/claim/worktree binding preserved;
- no blind task replay;
- durable restart count/reason correct;
- failure logs survive restart;
- numeric/typed failure evidence is useful.

If any acceptance item fails, stop fleet rollout and diagnose.

---

# 9. MANUAL-STOP SEMANTICS

Prove that an intentional/manual Stop does NOT trigger unwanted auto-recovery.

This is mandatory because a recovery system that cannot distinguish operator stop from unexpected failure is unsafe.

After proof, return the canary to the correct state only when its task/owner policy allows it.

---

# 10. FLEET ROLLOUT

Only after canary PASS.

Proceed one Worker at a time:

`CHECKPOINT -> DRAIN/PROTECT -> APPLY -> START -> VERIFY PROCESS TREE -> VERIFY HEALTH -> VERIFY REMOTE MCP -> VERIFY RECOVERY STATE -> NEXT`

Never update all five simultaneously.

If a Worker has active/unknown task state, skip it and record `ACTIVE_TASK_PROTECTED` rather than forcing rollout.

Remember: W1 running 0.0.14 has also exited historically, so binary version alone is not the acceptance criterion.

---

# 11. SOAK / SPONTANEOUS RECURRENCE

Use remaining useful session time to observe, not to spam probes.

If a spontaneous tunnel exit occurs:

- preserve telemetry first;
- correlate process/runtime/network/security evidence;
- verify self-heal acts once;
- classify initiating cause only to the level evidence supports;
- update checkpoint/result.

Do not disable ESET globally. If ESET remains plausible, use bounded correlation/diagnostic evidence before any exclusion experiment.

---

# 12. SOURCE DEFECT ESCAPE HATCH

If current accepted source still contains a deterministic defect:

1. reproduce/minimize it;
2. do not patch broadly in this ops branch;
3. write a bounded source-repair proposal in `runs/WO-P1-192/result.md`;
4. name exact files/tests/risk/root cause;
5. classify `SOURCE_REPAIR_REQUIRED`;
6. preserve operational rollback state.

A fresh source work order/claim and GPT acceptance are required before merge.

---

# 13. LONG-SESSION LOOP

Repeat:

`RECOVER -> OBSERVE -> CLASSIFY -> PROTECT ACTIVE WORK -> APPLY SMALLEST SAFE CHANGE -> VERIFY -> CHAOS ONLY WHEN ELIGIBLE -> CHECKPOINT -> ROUTE`

Checkpoint after:

- initial state recovery;
- copied-DB migration proof;
- artifact build;
- live install/migration;
- launcher/materialization changes;
- canary normal verification;
- chaos result;
- manual-stop result;
- each fleet Worker rollout;
- any spontaneous recurrence;
- before context/session cutoff.

Do not use chat/session memory as authority.

---

# 14. STOP CONDITIONS

Stop mutation for:

- `OWNERSHIP_BLOCKED`
- `AUTHORIZATION_REQUIRED`
- `SAFETY_BLOCK`
- `DEPLOYMENT_BLOCKED`
- `SOURCE_REPAIR_REQUIRED`
- `RECOVERY_REQUIRED` with no safe action
- `NO_SAFE_NEXT_ACTION`
- successful `INSTALLED_SELF_HEAL_ACCEPTED`
- provider/context cutoff after durable checkpoint

Debugging difficulty by itself is not a stop condition.

---

# 15. FINAL RESULT

Write `runs/WO-P1-192/result.md` with:

- final status;
- source SHA + installed artifact identity;
- DB before/copy/live migration evidence;
- Worker 1–5 before/after matrix;
- tunnel version/hash/path per Worker;
- launcher telemetry verdict;
- canary eligibility proof;
- exact old/new PIDs + creation identities;
- chaos sequence and recovery count;
- `/readyz` + remote MCP proof;
- manual-stop proof;
- orphan/duplicate audit;
- active Workers skipped/protected;
- initiating-cause evidence and remaining uncertainty;
- rollback state;
- whether source repair is required;
- exact next safe action.

Allowed final statuses:

- `INSTALLED_SELF_HEAL_ACCEPTED`
- `CANARY_PASS_FLEET_PENDING`
- `DEPLOYMENT_BLOCKED`
- `OWNERSHIP_BLOCKED`
- `SOURCE_REPAIR_REQUIRED`
- `RECOVERY_REQUIRED`
- `NO_SAFE_NEXT_ACTION`

Do not claim success because a PowerShell window stayed open for a long time.
