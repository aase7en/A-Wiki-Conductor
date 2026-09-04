# WO-P1-156 — Worker / MCP Transport Resilience Incident

Date: 2026-09-04
Owner: GLM-5.3 MAX / ZCode (incident investigator + implementer); GPT-5.6 Sol MAX remains acceptance authority
Status: FROZEN CANDIDATE (implementation slice) / incident recovery COMPLETE
Priority: P0 reliability defect (frozen-roadmap dependency, not a new feature)
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo156-worker-resilience`
Branch: `fix/wo-p1-156-worker-resilience`
Base: `origin/main@68079e3d00047ca9432f0aefe3ad667f892614d0`

## Incident summary (evidence-based)

- Observed remotely: Workers 1–4 `MCP Session terminated`; Worker 5 SSE probe 429/sometimes 404.
- Phase A evidence: ZERO sunday-worker / Serena / tunnel-client processes were alive; ports 18011–18015 had no listeners; the running Conductor app was SYN_SENT-probing 18015 (nothing answering).
- Per-instance logs: every worker's terminal event is `TUNNEL_START_FAILED: Tunnel client exited with code .` (empty/unreportable exit code = abrupt termination, not a normal exit) at staggered times — W5 2026-09-02 21:40, W1 09-03 22:22, W2 09-04 06:31, W3 06:46, W4 08:04 (local +07).
- Causal chain (proven by shared stderr capture): per-worker tunnel-client exited → `start.ps1` `Fail TUNNEL_START_FAILED` → wrapper window exit → Serena child died on broken stdio pipes (`OSError 22` flush signature at interpreter shutdown). A transient tunnel-layer event was amplified into full local worker teardown by the wrapper's fail-closed design.
- W5's 429/404 were downstream symptoms of being down since 09-02 (registration expired → 404; repeated probing → 429).

## Hypothesis verdicts

- H1 shared OpenAI/plugin session-gateway termination: UNKNOWN (remote side unobservable here; local chain fully explains the outage without it).
- H2 shared tunnel-client failure: SUPPORTED (mechanism refined: shared v0.0.11 binary, per-worker processes; common cause, staggered single-process exits; fresh connects succeed post-recovery).
- H3 common Serena supervisor crash: REJECTED (no common Serena supervisor exists; each Serena is a tunnel-client child; Serena died AFTER tunnels, from pipe closure).
- H4 host resource exhaustion: UNKNOWN-leaning-REJECTED (no crash events captured in remaining logs; host otherwise stable; not provable from retained evidence).
- H5 connector rate limiting/expiry: SUPPORTED for W5's remote symptoms (404 expired registration; 429 probe limit) as downstream effect, not initiating cause.
- H6 long tool-call/timeout session invalidation: UNKNOWN (no evidence either way in retained logs).

Root-cause classification: PROBABLE (H2 mechanism CONFIRMED at the wrapper-amplification level: tunnel exit ⇒ whole-instance teardown; the tunnel client's own exit reason was not captured because steady-state exit paths log nothing — fixed for the future by this WO's durable failure-reason capture).

## Recovery performed (Phase D/E)

All five workers restarted ONLY from their existing durable launch specifications (`Start-Sunday-Worker-N.cmd`), one at a time, verified after each: W1 PID 15428 @18011, W2 12144 @18012, W3 30440 @18013, W4 14224 @18014, W5 27784 @18015 (all `/readyz` → `ready`, tunnel pid files present, fresh tunnel sessions established — W5 included). No broad kills, no endpoint recreation, no config edits, no live-DB writes, no task replay. Task-level ownership notes preserved: W2 pharmacy cycle and W5 estate continuity remain task-quarantined from automatic dispatch (restoring a surface ≠ resuming a task); W4 remains WO096-reserved.

## Implementation (this candidate)

- New `src/a_conductor/worker_resilience.py`: independent per-layer health probes → single derived worker state (11 states, classification priority pinned by tests); restart-scoped recovery actions (429→BACKOFF_WAIT zero restarts; 404→RECONCILE_ENDPOINT zero recreation; stale→RECONNECT_SESSION; tunnel→RESTART_TUNNEL only; MCP→RESTART_COMPONENT; process→RESTART_FROM_SPEC gated on durable spec + budget; ownership/task-ambiguous→AWAIT_OPERATOR, no replay); `BackoffSchedule` (exponential, capped, jittered, Retry-After honored); `WorkerCircuit` (threshold→OPEN, cooldown→HALF_OPEN, close only after stable healthy window, half-open failure reopens immediately); `RestartBudget` (exhausted ⇒ QUARANTINE); `WorkerProcessIdentity` (pid + start epoch + executable + command hash ⇒ PID reuse rejected); `WorkerRecoveryState`/`WorkerRecoveryStore` (durable, atomic, secret-free by construction); idempotent `record_recovery_event`.
- New `tests/test_worker_resilience.py`: the mandated adversarial battery (simultaneous transport failure ⇒ zero worker restart via action mapping; 429/404 policies; tunnel/MCP/process scoping; anti-flap circuit transitions; budget→quarantine; restart-state restore; PID-reuse rejection; no-broad-kill source scan; secret-free serialization).
- REUSE (no second authorities): pure policy layer over the existing instance lifecycle (`instance_monitor` read_pid/log seams, Start/Stop instance specs, worker registry, leases/claims, orchestrator stop authority) — this module adds no scheduler/registry/lease/retry-process authority.

## Verification

- RED: battery failed on module absence before implementation.
- GREEN: `tests/test_worker_resilience.py` **33/33 PASS**; related regression `test_instance_monitor.py test_worker_lease.py test_worker_lease_recovery.py` **79/79 PASS**; `compileall`, `git diff --check`, strict UTF-8/no-U+FFFD PASS.

## Out of scope / next integration step

Wiring the policy layer into the running app's monitor loop (probe collectors + action executor + store path under `%LOCALAPPDATA%\A-Conductor\`) is the next bounded slice; requires GPT review of this candidate first. The wrapper script (`start.ps1`) hardening (tunnel-only restart instead of instance teardown) is a separate host-script change outside this repo candidate.

## Forbidden

Merges/pushes, broad kills, secret exposure, ZCode config edits, live-DB writes, new roadmap features, bypassing Zero-Relay/Fast-Roadmap ordering, self-acceptance.

## Verification-slice checkpoint — 2026-09-04 (post-verifier)

- Phase E executed per worker (all 5): post-restart process identity recorded (PID/PPID/executable/command/start time — tunnel-client.exe PIDs 15428/12144/30440/14224/27784, staggered starts 09:51:17–09:53:52 local); `/readyz` HTTP 200 on 18011–18015; MCP JSON-RPC is NOT exposed on the local port (`/` = Serena Web UI, `/mcp` = 404 — MCP flows through the tunnel session), so tool-level `initial_instructions`/`get_current_config` are exercised by the remote operator session, not locally — Active Project verified via the durable instance binding (`instance.ps1` ProjectPath + profile) instead.
- Repository state per worker project: W1/W4 → A-Wiki-Conductor root `main@f4ecf9a`, dirty 1 known file (donate-qr asset; protected-root policy); W3 → env-wastewater-webapp `main@7d73814`, dirty 16 (project-local WIP; not safe for blind reassignment); W5 → sunday-estate-webapp `main@0096e65`, dirty 1 (estate continuity); W2 → Drive pharmacy folder is not a git repository (Drive-layer governed; PLAN/PROJECT docs present).
- Claims: repo-side active claims remain WO152/WO155/WO156 lanes (COLLAB); no worker holds a conflicting mutable claim; W2 pharmacy task and W5 estate continuity remain task-quarantined; W4 remains WO096-reserved.
- Runtime activity: fresh `RUNNING` log lines today 09:51–09:53 for all five; Conductor app monitor probing re-established.
- Adversarial cases 2, 9, 20, 21, 22 added as EXPLICIT tests (RED first on missing APIs, then GREEN): five-worker simultaneous transport failure → zero worker-process restarts; unknown dirty state blocks restart/reassignment; recovered worker must pass the repository/ownership gate before mutation; parallel recovery planning is per-worker, deterministic, replay-stable and hard-errors on omissions (no ownership collision); deterministic single-probe-round fleet-outage detection (transport-only mode distinguishes shared-transport from local failures). New APIs: `RepositoryGate`, `worker_available_for_work`, `plan_parallel_recovery`, `detect_fleet_outage`, `recovery_action(gate=...)`.
- Verification at this checkpoint: focused **38/38 PASS**; related regression **79/79 PASS**; compileall/diff-check/strict-UTF-8 PASS. Frozen candidate superseded by the next commit; review must pin the final SHA below.
