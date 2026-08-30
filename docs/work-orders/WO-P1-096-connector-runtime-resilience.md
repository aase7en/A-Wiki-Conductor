# WO-P1-096 — Connector Runtime Resilience / v0.7.0 Stability Gate

Date: 2026-08-28
Owner: GPT-5.6 Sol (documentation/architecture capture only in this branch)
Status: ACTIVE / P0 RELEASE BLOCKER
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-connector-resilience`
Branch: `docs/wo-p1-096-connector-runtime-resilience`
Base: `main@5cc417c92450eba796fa9af1cf3da037663b1eea` (PR #119 merged)

## Goal

Make connector/runtime failures recoverable without the user noticing a vanished CMD window and manually pressing Start. This work is a v0.7.0 stability gate, not a new feature lane.

## Incident summary

A real Sunday-Worker-5 failure was captured on 2026-08-28:

1. tunnel-client reported `MCP connection TTL reached; stopping response forwarding`;
2. the shared stdio path then failed with `stdio MCP command stdin write failed` / `write |1: file already closed`;
3. tunnel-client requested whole-process shutdown;
4. the PowerShell launcher returned and its `cmd.exe /c ...` wrapper exited, so the visible CMD window disappeared;
5. lifecycle logging later recorded `TUNNEL_START_FAILED: Tunnel client exited with code .` with the exit code missing;
6. Serena logs showed orderly shutdown, and Windows Application/System logs did not show a corresponding native crash.

The user's A-Sunday activity log also corrects an earlier interpretation: the 16:24 restart was manual (`START-INST`), not automatic recovery. Current `AUTO-START` behavior starts configured connectors when Control Center starts; it is not evidence of a runtime watchdog that restarts an unexpectedly dead connector.

Observed Worker-5 sequence:

```text
16:16:49  START-INST   Sunday-Worker-5 QUEUED
16:16:55  START-INST   Sunday-Worker-5 RUNNING
16:19:01  tunnel-client: MCP connection TTL reached
16:19:01  tunnel-client: stdio stdin write failed: file already closed
16:19:16  lifecycle: TUNNEL_START_FAILED
16:24:17  START-INST   Sunday-Worker-5 QUEUED   # user manually pressed Start
16:24:23  START-INST   Sunday-Worker-5 RUNNING
```

Similar unexpected connector exits were observed on Workers 1-5 at other times, so this is a fleet reliability problem rather than a single-window problem.

## Root-cause status

### Proven

- CMD disappearance is a downstream symptom of the launcher chain exiting: `cmd.exe /c -> powershell.exe -> tunnel-client.exe -> Serena/stdio`.
- tunnel-client version observed: `0.0.11+8d55683eeef80bc5e360d95abf4692454fafc615`.
- the tunnel profile did not contain a local TTL override; current environment did not expose `MCP_CONNECTION_MAX_TTL`.
- `tunnel-client run --help` reports default `--mcp.connection-max-ttl 10m0s`.
- a live failure occurred after a shorter effective deadline/TTL. The exact upstream source of that shorter deadline is not yet proven.
- tunnel-client treated the closed stdio write as fatal to the whole connector process.
- current lifecycle logging loses the real tunnel-client exit code in this path.

### Not yet proven

- whether the shorter effective TTL originates in OpenAI control-plane request lifetime, tunnel-client internal request state, or another upstream connection deadline;
- whether a newer tunnel-client release already changes the fatal stdio/TTL behavior;
- whether the correct repair belongs in tunnel-client configuration, a Conductor supervisor, the generated launcher/profile, or a combination.

Do not claim those unknowns as root cause without a deterministic reproducer or upstream evidence.

## Reuse-before-build classification

`EXTEND + WRAP` existing lifecycle/owned-process/monitor/recovery foundations and the resilient-execution contract. Do not create a second job store, scheduler, worker model, or independent orchestration state machine.

Relevant existing authority:
- `PROJECT-PLAN.md` §19 Resilient Execution Supervisor;
- `docs/contracts/resilient-execution-supervisor.md`;
- existing worker lifecycle / owned-process / monitor code;
- `DEFECT_LESSONS.md` for regression memory.

## P0 repair slices

### CR-1 — Preserve connector service across request/connection TTL

A request/connection TTL or response deadline must end only the affected forwarding/request context. It must not silently destroy a healthy long-lived connector service.

If stdio child transport is truly dead, classify state and recreate/reconcile it safely. Never blind-replay an execution whose start/completion state is unknown.

### CR-2 — Runtime supervisor / bounded auto-recovery

For connectors configured for automatic operation, unexpected process death must be detected and recovered without operator intervention.

Required semantics:
- explicit user Stop must remain stopped and must not trigger recovery;
- unexpected exit -> `RECOVERING` -> bounded backoff -> restart -> health/project-identity verification;
- restart budget, e.g. 3 failures in 5 minutes, then `DEGRADED` / operator-visible intervention instead of an infinite restart storm;
- restart must preserve exact instance/PID/tunnel/project ownership checks;
- activity log must distinguish `AUTO-START`, `AUTO-RECOVER`, `START-INST`, and `START-ALL`.

### CR-3 — Durable incident telemetry

Each connector run must preserve:
- run/start identity;
- PID/process chain ownership;
- start/stop timestamps;
- real exit code;
- shutdown reason/classification;
- restart count/backoff state;
- bounded stdout/stderr tail and timestamped/rotated per-run logs.

Do not overwrite the only forensic log on restart. Fix blank `Tunnel client exited with code .` reporting.

### CR-4 — Operator state

The Control Center should expose enough state that the user does not need to infer health from a CMD window:
- `READY / RECOVERING / DEGRADED / STOPPED`;
- last exit reason/time;
- restart count;
- next retry/backoff when applicable.

Visible CMD launchers remain debugging/recovery surfaces, not the liveness authority.

### CR-5 — Path-with-spaces regression

Worker 2 has a project path under `L:\My Drive\...`; at least one Serena invocation was observed parsing it as `L:/My`. Reverify all generated/profile launch paths use argument-safe quoting/serialization. Keep this separate from the fleet-wide TTL failure classification, but close it in the same stability milestone if still reproducible.

## Verification / acceptance

Deterministic first; live fleet last.

1. fault-injection fake tunnel/stdio backend: force response TTL/deadline while service stays alive; next MCP request succeeds without connector process death;
2. force stdio child closure: supervisor classifies, recreates/reconciles, and returns READY without blind replay;
3. explicit Stop: no auto-restart;
4. repeated crash: bounded backoff + restart budget -> DEGRADED, no restart storm;
5. telemetry test: non-empty exit code/reason and separate per-run logs survive restart;
6. path-with-spaces test for `L:\My Drive\...`;
7. focused lifecycle/recovery suites green, then full repository test matrix green on Windows/Ubuntu/macOS;
8. isolated sacrificial connector E2E only — do not use an active development connector for the first mutation test;
9. live soak must exceed the effective/default transport TTL repeatedly and require zero manual Start actions.

## v0.7.0 release gate

Repository source currently reports `0.7.0`, while GitHub Releases still show `v0.6.0` as Latest at this checkpoint. Treat connector resilience as a **P0 pre-release stabilization gate** for v0.7.0.

Do not publish v0.7.0 as stable until:
- CR-1 through CR-4 are implemented and verified;
- CR-5 is either fixed or proven not reproducible;
- exact-head 3-OS CI is green;
- isolated real connector recovery E2E passes;
- branch/release audit confirms no stale/superseded branch is accidentally used as release source.

## Branch topology / anti-confusion checkpoint

Verified before creating this worktree:

- authoritative remote `main`: `5cc417c92450eba796fa9af1cf3da037663b1eea` (PR #119);
- shared `A:\GitHub\A-Wiki-Conductor` checkout: local `main@f4ecf9a8...`, behind remote by 119 commits and dirty at `assets/donate-promptpay-qr.png` -> PROTECTED / DO NOT MUTATE;
- `A:\GitHub\A-Wiki-Conductor-aha4-bridge`: `feat/wo-p1-095-aha4-harness-durable-bridge`, dirty active implementation -> protected;
- PR #108: `fix/v070-installer-target-ownership`, open release/installer safety lane -> protected;
- `feat/north-star-runtime-sunday-family`: preserved independent integration lineage -> protected;
- detached/older audit and v0.7 helper worktrees may be cleanup candidates, but some contain untracked evidence -> no destructive cleanup authorized.

Canonical integration rule for this incident:

`remote main -> isolated WO-P1-096 docs/architecture capture -> implementation work order(s) from fresh accepted main -> independent review -> CI/E2E -> release`

Never base this stability fix on the stale shared `main` checkout or on a feature branch merely because it looks newer locally.

## Allowed scope for this documentation slice

Allowed:
- `PROJECT-PLAN.md`
- `DEFECT_LESSONS.md`
- `docs/work-orders/WO-P1-096-connector-runtime-resilience.md`

Forbidden in this branch:
- `CURRENT-WORK.md`, `COLLAB.md`, `handoff.md` (AHA-4 bridge is actively editing these coordination surfaces);
- `src/**`, `tests/**`;
- installer PR #108 scope;
- North Star / AHA-4 implementation scope;
- live `C:\AI\serena-instances` mutation.

## Next safe implementation action

After this documentation branch is integrated and active coordination surfaces are reconciled, create a fresh bounded implementation WO from then-current remote main for CR-1 + CR-3 first: deterministic reproducer, exit-code/log preservation, and request-TTL isolation. Add CR-2 supervisor only against the accepted lifecycle seam so recovery does not mask or duplicate the causal repair.

## Evidence refresh - 2026-08-28 after WO-P1-097 / PR #125 review

This checkpoint supersedes the earlier root-cause unknowns where newer upstream behavior had not yet been verified.

### Closed or source-complete

- CR-1 causal source mitigation: PR #122 merged as `ceee9bb7aa361aef6d0ecfc210c25b564578d552`; A-Sunday now rejects known-bad tunnel-client 0.0.11 and requires `>=0.0.12`.
- Upstream `openai/tunnel-client` issue #34 documents the same 0.0.11 chain observed here: response deadline -> shared stdio closed -> `file already closed` -> process-wide shutdown. Current protocol explicitly preserves shared stdio child pipes for non-`initialize` response deadlines.
- Latest verified upstream artifact is `v0.0.13` (`4b5267f823be0b046bb883aacb51603cfde3a0ea`). Full Windows amd64 zip SHA256 `17113162b353906bbb884c3ed7620facba5cc72b5fdc94fd54fd7208c7166edb` matches upstream `SHA256SUMS.txt`. The executable is not Authenticode-signed, so checksum/provenance verification remains required.
- CR-3 source telemetry: generated launchers now rotate fixed runtime stdout/stderr logs and preserve numeric tunnel-client exit codes; legacy-reference materialization receives the same hardening.
- CR-5 path-with-spaces regression is green for `L:\My Drive\...` quoted project arguments.
- WO-P1-097 is `SOURCE SLICE COMPLETE / MERGED`; PR #123 closeout merged as `dec80993f7c567e370d09288386ebb87e7f3f4e9`. Post-merge main CI run `33173477868` passed Windows/Ubuntu/macOS plus Windows packaging/frozen smoke.

### Still blocking v0.7.0 stable

- CR-2 / CR-4 implementation is active in Draft PR #125 (`fix/wo-p1-099-connector-auto-recovery`). Independent snapshot verification passed 28 focused tests and 117 broader lifecycle/control/monitor tests.
- P0 review finding on PR #125: `DesktopControlService.reconcile_instance_recovery()` currently has no production caller. The 15-second connector refresh path only observes health; therefore STOPPED connectors do not yet invoke recovery automatically. Review `5051679381` records the required single-flight/cancellable production wiring.
- Real connector E2E/TTL soak remains blocked by fleet ownership, not by missing investigation: Sunday-Worker 1-5 are all READY and using the shared live binary. Private tunnel inventory contains exactly 5 configured IDs, all 5 are in use, and there are 0 unused IDs. No sacrificial connector can be created without adding a new Tunnel ID or taking one existing Worker through an explicit maintenance window.
- Live shared tunnel-client remains intentionally unchanged until that maintenance window; source verification must not be confused with operational rollout.
- CR-4 operator visibility (`READY / RECOVERING / DEGRADED / STOPPED`, last exit, restart count, next retry) remains incomplete until the recovery path is accepted and surfaced.

### Release decision

`v0.7.0` remains BLOCKED. Do not publish stable until PR #125 or its accepted successor has real production recovery wiring, CR-4 is operator-visible, and one isolated/authorized connector completes the v0.0.13 deadline/TTL soak with zero manual Start actions.

## Upstream v0.0.13 CI verification - 2026-08-28

Independent source review of `openai/tunnel-client@4b5267f823be0b046bb883aacb51603cfde3a0ea` closes the remaining source-level uncertainty around the shared-stdio deadline fix:

- the release workflow's `Test` job runs `make test`, and `make test` runs `go test -race ./...`;
- commit `4b5267f...` has successful upstream `Test` checks plus successful Windows/Linux/macOS release builds;
- `TestHarnessStdioResponseDeadlineKeepsServingAfterTimedOutRequest` injects a 2-second response timeout, then sends a recovery command through the same stdio server; both commands must reach the server and the recovery response must succeed;
- that E2E explicitly fails if logs contain `stdio MCP command stdin write failed` or `file already closed`;
- dispatcher/unit coverage separately requires a response deadline to retire the logical shared-MCP lifecycle without closing the physical shared connection;
- serialized-stdio coverage requires the next request to write/read successfully after a retired deadline without triggering the stdio write-failure callback.

Local source execution was not repeated because this workstation has no Go toolchain installed; no toolchain was installed solely for this audit. Upstream exact-commit CI is therefore the executable source-level evidence, while A-Sunday's authorized real connector soak remains the operational acceptance gate.

PR #125 re-review on head `f6fdb5d9dcee493a0ae5104db0d660eb44f50b08` confirms `09bf1ab` improves manual-intent serialization, but the production-caller P0 remains open: `reconcile_instance_recovery()` still has no caller from the existing health/refresh loop. Review `5051827379` records the unchanged blocker.

## Checksum/provenance hardening closeout - 2026-08-28

WO-P1-101 closes the A-Sunday-owned checksum fail-open gap identified during v0.0.13 provenance review:

- PR #128 (`fix(setup): require tunnel-client checksum`) merged as `cbaadb757f71e2b304a1c8ec4ca58f1ae1466679`;
- tunnel-client install/upgrade now requires release `SHA256SUMS.txt` and a valid 64-hex entry for the selected Windows artifact before the ZIP is downloaded for installation;
- checksum metadata download failure, missing checksum asset/entry, or SHA256 mismatch fails closed before extraction/replacement;
- an existing tunnel-client binary remains byte-for-byte unchanged on verification failure, and checksum/ZIP scratch files are removed;
- local evidence: setup suite 26 passed; broader setup/instance/control regression 106 passed; compile/diff/secret gates passed;
- exact-head GitHub Actions run `33180188339` passed Windows, Ubuntu, and macOS before merge.

This closes the checksum/provenance sub-gate only. `v0.7.0` remains BLOCKED: PR #125 head `f6fdb5d9dcee493a0ae5104db0d660eb44f50b08` still has no production caller for `reconcile_instance_recovery()`, CR-4 operator visibility remains incomplete, and no unused Tunnel ID exists for the required isolated/live TTL soak.
## Authoritative release-gate refresh - 2026-08-29

This checkpoint supersedes earlier statements in this file that CR-2 had no production caller or that CR-4 was still incomplete.

Source state verified from accepted main:
- CR-1: source complete via PR #122; setup rejects tunnel-client 0.0.11 and requires >=0.0.12. Checksum/provenance fail-closed hardening merged via PR #128.
- CR-2: source complete via PR #125. DesktopControlService.instance_states_cancellable() calls reconcile_instance_recovery() from the existing health loop; explicit STOP suppression, bounded retry budget and DEGRADED semantics remain under the accepted coordinator.
- CR-3: source complete in generated/legacy launcher hardening: timestamped runtime-log archive and numeric tunnel-client exit code are preserved.
- CR-4: source complete via PR #133. MONITOR exposes recovery state, restart/failure counters, last exit and next retry; AUTO-RECOVER is emitted from durable restart evidence.
- CR-5: source tests cover quoted project paths with spaces including L:\My Drive\... .

Operational state is NOT complete:
- the live shared binary at C:\AI\dwb-serena-tunnel-starter\tunnel-client\tunnel-client.exe is still 0.0.11;
- the installed public app is still v0.6.0;
- no sacrificial/idle tunnel has yet been proven available for the required v0.0.13 deadline/TTL soak without disrupting another active chat/worker;
- v0.7.0 publication therefore remains blocked until an authorized isolated live upgrade/soak requires zero manual Start actions, followed by exact-main artifact install/smoke/uninstall acceptance.

Release rule: source-complete CR-1..CR-5 may be reported as merged, but WO-P1-096 stays ACTIVE / P0 RELEASE BLOCKER until the operational soak and release E2E gates pass.

## Pre-authorization operational gate refresh — 2026-08-29

Accepted exact main is `047326966ded5d2941d57411782f8a85b6d9121a` (PR #145). Main CI `33248070680` is green on Windows, Ubuntu, and macOS and Windows now includes real frozen Setup install/uninstall E2E. Exact-main frozen artifact acceptance is therefore complete; it is no longer an outstanding WO-P1-096 blocker.

Live operational state was re-verified read-only: ports 18011-18015 are all READY, all five use the shared live tunnel-client `0.0.11+8d55683eeef80bc5e360d95abf4692454fafc615`. Private inventory was checked without exposing IDs: configured Tunnel IDs = 5, READY ports = 5, spare by count = 0.

Upstream latest release remains `v0.0.13`. The Windows amd64 ZIP was staged outside the live binary path and verified against upstream SHA256SUMS: `17113162b353906bbb884c3ed7620facba5cc72b5fdc94fd54fd7208c7166edb`. No live Worker or shared tunnel-client binary was stopped, replaced, or upgraded.

Only remaining WO-P1-096 acceptance action: an authorized isolated/live v0.0.13 deadline/TTL soak that exceeds the relevant transport TTL repeatedly, shows zero manual Start actions, and returns the chosen Worker to its verified ownership/configuration state. Because there are zero spare IDs and all five ports are active, this requires either a new spare Tunnel ID or explicit maintenance authorization to take one specific Worker offline temporarily. Until then `v0.7.0` remains blocked.


## 2026-08-30 isolated v0.0.13 live-soak checkpoint

- Read-only fleet preflight found Worker4 unexpectedly STOPPED while Workers 1/2/3/5 remained READY; Worker4 had no tunnel PID and its persistent autostart flag remained enabled.
- Worker4 was selected as the isolated maintenance target without stopping or rebinding another live Worker. The shared tunnel-client binary used by Workers 1/2/3/5 was not changed.
- Worker4 was started with the staged `tunnel-client v0.0.13` binary through a temporary path override; `instance.ps1` was restored byte-for-byte immediately after launch.
- Runtime identity verified the Worker4 tunnel process executable is the staged v0.0.13 binary and `/readyz` returned HTTP 200 beyond the default ten-minute TTL.
- This is partial acceptance evidence only. A real hosted/remote MCP request must still succeed after TTL with zero manual Start action before the live-soak gate can close.
- Do not record or expose Tunnel IDs in tracked evidence. Workers 1/2/3/5 and the shared v0.0.11 binary remain outside this maintenance mutation lane.
