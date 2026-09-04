# WO-P1-156 Live Tunnel Upgrade + Logical-Worker Chaos Runbook

Date: 2026-09-04
Status: PREPARED / W1 CANARY EXECUTED / FULL FLEET + INSTALLED SELF-HEAL NOT YET EXECUTED
Authority: GPT-5.6 Sol MAX acceptance/integration; implementation candidate must be independently reconciled before use.
Incident: `docs/incidents/2026-09-04-worker-tunnel-teardown.md`

## Purpose

Close the recurring Sunday Worker disappearance by addressing both confirmed deployment gaps:

1. the live fleet still has unresolved legacy `tunnel-client 0.0.11` controls; W1 alone is on the isolated checksum-verified 0.0.14 canary and W4 is currently down after its 18:31 control failure;
2. the installed A-Sunday Conductor predates the accepted bounded connector auto-recovery source path.

This runbook is an operational acceptance procedure, not a new recovery authority.

## Proven current facts

- W1 canary binds the checksum-verified 0.0.14 binary:
  `C:\AI\dwb-serena-tunnel-starter\canary\0.0.14\tunnel-client\tunnel-client.exe`
- W2/W3/W5 remain live on the shared legacy binary; W4 remains configured to it but was down at the 19:53 checkpoint after the 18:31 failure:
  `C:\AI\dwb-serena-tunnel-starter\tunnel-client\tunnel-client.exe`
- shared legacy version:
  `0.0.11+8d55683eeef80bc5e360d95abf4692454fafc615`
- shared legacy SHA-256:
  `7D3C7D492CE84B52835E11865A835A8A5BCD4A669DEE84E169AA11B314DC952A`
- W1 canary version / SHA-256:
  `0.0.14` / `FCC85A69EC0AD82518E4F8964F60C45E31787957782A0FC9C1B0C44E82D61B9B`
- repository safe floor:
  `>=0.0.12`
- temp-only checksum-verified installer proof on 2026-09-04 resolved:
  - version `0.0.14`
  - SHA-256 `FCC85A69EC0AD82518E4F8964F60C45E31787957782A0FC9C1B0C44E82D61B9B`
- current source baseline recovery tests:
  `52/52 PASS`
- live DB currently lacks `instance_recovery`.
- copied-live-DB migration adds `instance_recovery`, preserves existing table counts, and returns `integrity_check=ok`.

## Mandatory gates before live execution

Do NOT execute the live upgrade until all are true:

- GLM WO156 candidate has a frozen exact SHA.
- GPT has reviewed the exact SHA and accepted the single-authority architecture.
- No duplicate `WorkerRecoveryStore` / retry/backoff/circuit authority remains where it overlaps existing `ConnectorRecoveryCoordinator`.
- relevant WO156 + connector-recovery tests are green.
- source candidate builds successfully.
- copied-live-DB migration proof passes again on the exact candidate.
- each Worker has fresh task/claim/worktree/dirty-state reconciliation.
- every ambiguous task outcome is checkpointed as `UNKNOWN`; no blind replay.
- a rollback copy of the old shared binary is prepared and hashed.
- no Worker is stopped merely because its Active Project looks idle.

## Phase 1 — Exact fleet preflight

For Sunday-Worker-1..5 record:

- Worker ID
- project
- active task/work order
- claim/lease owner
- worktree/branch/HEAD when git-backed
- dirty state
- recent runtime activity
- wrapper PID
- tunnel-client PID
- Serena PID
- health port
- remote MCP state

Classify each:

`READY_TO_DRAIN / TASK_CHECKPOINT_REQUIRED / OWNERSHIP_BLOCKED / UNKNOWN`

If any state is UNKNOWN, do not proceed with a fleet-wide replacement.

## Phase 2 — Backup and candidate preparation

Never copy secrets into repository evidence.

Record current binary:

- path
- size
- version
- SHA-256
- file timestamp

Create a local operational backup outside the repo, for example under a bounded incident backup directory.

Candidate must be obtained through the existing checksum-verified installer path:

`Installer.install_tunnel_client(target_dir=<controlled temp dir>)`

Verify candidate:

- version >= repository safe floor
- expected SHA from checksum-verified download
- executable launches with `--version`
- temp install leaves no unexpected files

Do not replace the shared live binary while any Worker still owns a process using it.

## Phase 3 — Controlled fleet drain

Because all five Workers bind the same shared legacy executable, replacement requires a controlled drain.

For each Worker, one at a time:

1. persist task/claim/continuity state;
2. verify exact wrapper/tunnel/Serena process identity;
3. issue the existing exact-instance stop authority;
4. verify that Worker's wrapper/tunnel/Serena processes are gone;
5. verify no unrelated process was terminated.

After all five are drained:

- verify ports 18011–18015 have no stale listeners;
- verify no `tunnel-client.exe` process command line references a Sunday Worker profile;
- verify no unexpected task is still RUNNING without a checkpoint.

No broad `taskkill /IM tunnel-client.exe`, Python kill, Serena kill, Node kill, or ZCode kill.

## Phase 4 — Replace the shared binary once

Use the existing installer/version-validation authority with explicit target directory:

`C:\AI\dwb-serena-tunnel-starter\tunnel-client`

Requirements:

- checksum required;
- candidate version >= safe floor;
- atomic replacement;
- fail closed if file is unexpectedly locked;
- no manual unverified download.

After replacement verify:

- exact path unchanged;
- version is the reviewed candidate (currently temp proof found 0.0.14);
- SHA-256 matches checksum-verified candidate;
- old binary backup still exists for rollback.

## Phase 5 — Restart and verify one Worker at a time

For each Worker:

1. start only from its durable existing launch specification;
2. capture new wrapper/tunnel/Serena PIDs and start times;
3. verify `/readyz`;
4. verify remote MCP handshake;
5. run `initial_instructions` and `get_current_config` remotely when available;
6. verify project binding;
7. verify repository/worktree/branch/HEAD/dirty state;
8. verify task/claim state;
9. mark AVAILABLE only if all gates pass.

Do not auto-resume an ambiguous task.

## Phase 6 — Deploy reviewed self-heal build

Only use a reviewed candidate containing:

- existing `ConnectorRecoveryCoordinator` authority;
- durable `SQLiteSerenaConfigStore` recovery state;
- existing `LocalInstanceOrchestrator`;
- accepted WO156 extensions only.

Before first live launch:

- make a consistent backup of the control DB using the repository's normal safe DB procedure;
- rerun copied-DB migration proof on the exact build source;
- verify no schema downgrade path is invoked.

Launch/install the candidate and verify:

- `instance_recovery` appears after normal initialization;
- existing logical data remains intact;
- application starts normally;
- Worker state refresh calls the recovery coordinator.

## Phase 7 — Isolated chaos acceptance

Choose only an idle/sacrificial Worker with:

- no active task claim,
- clean/known worktree state,
- no mutable overlap,
- exact PID identity recorded.

Chaos action:

- terminate ONLY that Worker's exact `tunnel-client.exe` PID after re-validating PID + start time + command identity immediately before termination.

Expected causal behavior:

`tunnel-client exits -> its Serena child may exit -> A-Conductor observes unexpected STOPPED -> existing recovery authority performs one bounded restart -> new tunnel + Serena pair becomes READY`

Required evidence:

- old tunnel PID is gone;
- old Serena child is gone or cleanly reconciled;
- exactly one new tunnel-client exists for that Worker;
- exactly one new Serena child exists;
- `/readyz` returns success;
- remote MCP reconnects;
- project binding remains correct;
- task/claim state is preserved;
- no blind replay occurred;
- durable restart count/reason code is correct;
- no raw credential/error text persisted.

Failure means incident remains OPEN.

## Phase 8 — Adversarial acceptance

Must also verify:

- manual Stop -> zero automatic recovery;
- repeated health observation -> no duplicate restart;
- transient 404/429/session-stale -> no restart storm or duplicate endpoint creation;
- Worker task outcome UNKNOWN -> no replay;
- unsafe/unknown ownership -> not AVAILABLE;
- repeated chaos cycles -> no orphan/duplicate processes;
- A-Conductor restart -> durable recovery state remains coherent;
- network disconnect/reconnect -> logical Worker returns without manual Start, if the remote environment permits deterministic testing.

## ESET decision gate

Do not disable ESET globally.

Only if failures continue after:

1. tunnel-client upgrade,
2. reviewed self-heal deployment,
3. improved exit telemetry,

then run a bounded ESET A/B investigation.

Preferred order:

- increase ESET/network diagnostics first;
- correlate exact tunnel exit timestamps;
- only if evidence remains plausible, consider a temporary exclusion limited to the exact tunnel-client executable;
- remove the exclusion after the test unless reproducible evidence proves it necessary.

## Rollback

Rollback if:

- upgraded tunnel-client cannot establish stable sessions,
- duplicate processes appear,
- recovery storms occur,
- migration changes existing logical data,
- installed candidate fails startup,
- task/claim safety cannot be proven.

Rollback procedure:

1. checkpoint all current Worker/task state;
2. stop exact Worker instances cleanly;
3. restore the backed-up prior binary only as an emergency recovery action;
4. restore application build/database only through the repository's verified rollback procedure;
5. restart Workers one by one;
6. keep incident OPEN and persist failure evidence.

Do not normalize the old 0.0.11 binary as a long-term accepted state after rollback.

## Close condition

WO156/incident can close only when the installed reviewed build + supported tunnel-client pass the isolated logical-Worker self-heal chaos cycle and the critical adversarial checks without human relay.

## A/B interpretation gate - added after 18:31 control recurrence

The W1 0.0.14 canary and W4 0.0.11 control now have a useful divergence, but operational evidence must not be over-interpreted.

Current bounded evidence:

- W1 0.0.14: still LISTEN/remote-reachable after the canary start at 12:46:55;
- W4 0.0.11: exact TTL/deadline -> closed-stdio -> tunnel shutdown -> Serena exit 120 chain at 18:31;
- W2/W3/W5 0.0.11: still alive through the same later checkpoint.

Interpretation:

- supported: legacy 0.0.11 is associated with the already-known TTL/deadline failure family;
- supported: 0.0.14 is compatible with the live W1 profile and has survived the observed canary window;
- not supported: every 0.0.11 instance fails after a fixed uptime;
- not yet proven: 0.0.14 eliminates every possible initiating trigger;
- not yet proven: ESET is the initiating cause.

A future trigger reproducer must use an idle/sacrificial, explicitly claimed Worker. Never inject TTL/deadline/session disruption into a Worker with active work, unknown task outcome, dirty protected worktree, or overlapping mutable scope.
