# Incident 2026-09-04 — Sunday Worker tunnel teardown / missing self-heal

Status: OPEN — root cause layers identified; final fix requires single-authority recovery deployment + chaos verification.
Owner split: GPT-5.6 Sol MAX = integration/acceptance/defect memory; GLM-5.3 MAX/ZCode = bounded implementation/test/repair under WO-P1-156.
Scope freeze: reliability defect only; no unrelated feature work.

## User-visible symptom

- SunDay Workers disappear and later return `MCP Session terminated`, HTTP 404, or HTTP 429.
- The failure repeatedly removes GPT's Windows execution surface until a Worker is manually restarted.
- Worker 4 reproduced after recovery:
  - 2026-09-04 09:52:57 RUNNING PID 14224
  - 2026-09-04 10:21:31 TUNNEL_START_FAILED
  - 2026-09-04 10:21:37 RUNNING PID 8396
  - 2026-09-04 11:02:36 TUNNEL_START_FAILED

## Confirmed evidence

1. **CPU/RAM exhaustion is not supported as the primary cause.**
   - sampled CPU: ~3.9%
   - physical RAM: 15.89 GiB total, ~4.21 GiB free (~26.5%)
   - no Windows Resource-Exhaustion/WHEA/critical memory events found in the inspected 7-day window.

2. **Process tree confirms the transport owns Serena.**
   - `powershell.exe start.ps1`
     -> `tunnel-client.exe`
     -> `serena.exe`
   - Therefore a tunnel-client exit necessarily tears down its Serena child for the current architecture.

3. **Current host wrapper is one-shot.**
   - `start.ps1` starts tunnel-client, waits with `WaitForExit()`, then reports `TUNNEL_START_FAILED` on non-zero/abrupt termination and exits.
   - Serena stderr after the tunnel teardown shows `OSError: [Errno 22] Invalid argument` while flushing stdout, consistent with its transport pipes disappearing.

4. **The deployed A-Sunday Conductor runtime predates the existing self-heal source code.**
   - running executable: `A:\GitHub\A-Sunday-Conductor-Builds\A-Sunday Conductor LATEST.exe`
   - file timestamp: 2026-08-26 14:17:54 +07
   - SHA-256: `96ADA142A2DDB7293C17F140B4CFC4B7D3288599938AD207A57D0A05B40CA201`
   - bounded connector recovery source was added on 2026-08-28:
     - `18ce7f3` add bounded auto-recovery core
     - `0a3dc4d` wire recovery to health refresh
     - `dd1d404` preserve explicit stop metadata

5. **Live recovery schema is not deployed.**
   - all Sunday-Worker-1..5 have `instance_flags.autostart=1`.
   - live DB does not contain the source-era `instance_recovery` table.
   - On a copied live DB, `SQLiteSerenaConfigStore.initialize()` adds `instance_recovery`, preserves existing table row counts, and returns `PRAGMA integrity_check = ok`.
   - The live DB was not mutated by this proof.

6. **ESET is a possible upstream trigger, not a confirmed root cause.**
   - ESET Service, Firewall Helper, and Inspect Connector are active.
   - inspected Windows Application/System logs around the Worker 4 failures contained no event directly naming ESET/tunnel-client blocking or termination.
   - ESET warnlog metadata changed near the incident window, but no direct `tunnel-client` / `Serena` / `blocked` / `firewall` string evidence was found.
   - Do not disable ESET globally based on current evidence.

## Root-cause model

### Confirmed

`tunnel-client exit -> Serena child transport disappears -> logical Worker becomes unavailable`

and

`deployed runtime is older than the source self-heal implementation -> the logical Worker can remain down instead of being automatically recovered`.

### Not yet confirmed

The initiating cause of tunnel-client exit. Ranked hypotheses remain:

1. transient network/tunnel transport failure,
2. remote gateway/session disruption,
3. ESET network/process inspection interference,
4. tunnel-client defect,
5. other host/environment failure.

CPU/RAM exhaustion currently has weak/negative evidence.

## Architecture decision

There must be **one durable recovery authority**.

Reuse the existing source path:

- `ConnectorRecoveryCoordinator`
- `ConnectorRecoveryRecord`
- `ConnectorRecoveryStore` / `SQLiteSerenaConfigStore`
- existing instance orchestration and exact process ownership

Do not introduce a second independent restart/backoff/store authority.

The host `start.ps1` may stay one-shot if A-Conductor owns restart policy. It must emit bounded, non-secret exit reason evidence. Do not add an independent infinite restart loop to each wrapper unless the repository architecture explicitly changes and the single-authority invariant is preserved.

## Corrective plan

### P0-A — Reconcile WO-P1-156 to existing authority

- remove/avoid duplicate recovery store, retry/backoff, circuit, and idempotency authorities;
- retain only missing multi-layer classification, repository/ownership gate, exact identity, fleet correlation, and safe remote-session dispositions;
- persist only bounded reason codes, never raw credentials/errors.

### P0-B — Deploy the recovery source path

- build from a reviewed source SHA containing the existing connector recovery path plus accepted WO156 repairs;
- migration proof must run on a copy before any live DB migration;
- deployment must initialize `instance_recovery` without altering existing logical data;
- verify health loop calls the existing recovery coordinator for unexpected STOPPED states.

### P0-C — Logical Worker self-heal

For an unexpected tunnel-client exit:

1. detect STOPPED / recent transport exit evidence;
2. preserve exact worker/task/claim identity;
3. classify ambiguous task outcomes as UNKNOWN — no blind replay;
4. use existing bounded recovery authority;
5. restart exact worker launch specification (tunnel-client will spawn a new Serena child);
6. verify local readiness, remote MCP/session readiness, project binding, worktree/dirty state, task/claim state;
7. only then mark the Worker AVAILABLE.

Manual stop must remain suppressed and must not auto-restart.

### P0-D — Trigger diagnosis without weakening security

- add/retain timestamps, exact process identity, tunnel exit reason code, network state, and recovery outcome;
- use reason codes rather than raw stderr in durable state;
- if ESET remains suspected, perform a bounded A/B experiment only after logging is sufficient:
  - never disable ESET globally;
  - first prefer ESET diagnostic/network logging;
  - if necessary, test an exclusion limited to the exact `tunnel-client.exe` executable;
  - compare repeated failure/recovery behavior with and without that narrow exclusion;
  - remove the exclusion if it provides no reproducible benefit.

## Regression / acceptance gates

The incident remains OPEN until all applicable gates pass:

1. unit/integration tests for the existing connector recovery authority and WO156 extension;
2. migration on a copied live DB preserves all existing rows and integrity;
3. exact-PID chaos test: terminate only a sacrificial/isolated tunnel-client and prove the logical Worker returns READY through the single recovery authority;
4. no broad kill, no duplicate worker processes, bounded restart budget/backoff;
5. manual STOP never auto-restarts;
6. task outcome UNKNOWN blocks replay/resume until reconciled;
7. network disconnect/reconnect scenario recovers without manual Worker restart;
8. 404/429/session-stale scenarios do not create restart storms or duplicate endpoints;
9. post-recovery repository/ownership gate must pass before mutation;
10. repeated chaos cycles must not leak processes or accumulate duplicate state;
11. installed/frozen build, not only source tests, must pass the same critical self-heal scenario;
12. remaining ESET hypothesis is either reproduced/mitigated or explicitly closed as unsupported by evidence.

## Operational fallback before the fix is deployed

- restart only the exact failed Sunday Worker from its durable `start.ps1`/launcher after proving no listener/process already owns that instance;
- never broad-kill Python, Serena, Node, ZCode, or tunnel-client processes;
- reconcile task outcome before replaying interrupted work.

## Close condition

Close this incident only when a reviewed installed build self-recovers an intentionally interrupted Worker through the existing A-Conductor recovery authority, with deterministic evidence and no manual relay.
