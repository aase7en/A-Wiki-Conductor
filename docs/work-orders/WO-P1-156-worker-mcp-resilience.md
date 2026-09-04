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

## GPT-review repair checkpoint — 2026-09-04

- All six review findings repaired RED-first (battery failed on missing APIs before implementation):
  - P1 SECURITY: persistence boundary now sanitizes — `sanitize_worker_recovery_state` (reuses `claude_code_harness._redact_text` for known values) plus a structural credential-shape detector (Authorization/Bearer/cookie/assignment keys/sk-/ghp_/github_pat_/ya29./xox/URL-userinfo) that neutralizes any matching free-text field wholesale; `WorkerRecoveryStore.upsert(state, redaction_values=...)` persists only the sanitized copy; adversarial test upserts deliberately credential-bearing `failure_reason`/`endpoint_ref`/`tunnel_ref` and inspects the persisted FILE.
  - P1 CONCURRENCY: per-path store locks (shared across store instances in-process) + unique `mkstemp` temporaries + `os.replace` atomic publish; explicit documented ownership boundary — same-process lossless, NO cross-process claim (single Conductor owner); concurrent 10-thread/5-worker RED test proves losslessness.
  - P1 IDEMPOTENCY: event dedupe moved into `WorkerRecoveryStore.record_event` (durable, same file, bounded retention 256 with oldest-drop); process restart (fresh store instance, same path) cannot replay a recorded event — RED test covers in-process, restart, and distinct-event paths; the process-local module-global dedupe authority was removed entirely.
  - P1 DETECTION: `detect_fleet_outage(..., recent_failures_by_worker=...)` supports the post-amplification observation: PROCESS_DOWN workers are attributed `TRANSPORT_AMPLIFIED` only with durable transport-evidence (e.g. `TUNNEL_START_FAILED`); simultaneous PROCESS_DOWN without transport evidence returns NO outage (regression test reproduces the WO156 causal chain and both negative controls).
  - P2 ownership-collision test replaced: overlapping-unsafe gates yield AWAIT_OPERATOR for every affected worker; mixed safe/unsafe gates restart only the proven-safe worker.
  - P2 secret test replaced with adversarial payloads + persisted-file inspection (above).
- Incident during repair (recorded): a patch truncation removed the f6f9b4c tail section; restored verbatim from the frozen commit before continuing (verified by diff review + full suite).
- Verification: `tests/test_worker_resilience.py` **42/42 PASS**; related `test_instance_monitor + test_worker_lease + test_worker_lease_recovery` **78 passed / 1 pre-existing skip**; `compileall src/a_conductor` PASS; `git diff --check` PASS; strict UTF-8 PASS. Frozen candidate: next commit; supersedes `f6f9b4c` for review.

## Authority-reconciliation checkpoint — 2026-09-04 (second GPT review)

- Reconciled around the ONE recovery authority already in the base (`connector_recovery.py`, in-base since 18ce7f3/0a3dc4d/dd1d404; `instance_recovery` table in `SQLiteSerenaConfigStore`).
- Classification: REMOVED `WorkerRecoveryStore` (+JSON persistence, durable-event ledger, sanitizer), `BackoffSchedule`, `WorkerCircuit`, `RestartBudget` — all second-authority duplicates of coordinator/store responsibilities. KEPT as pure policy: `WorkerHealthProbes`/`classify_worker`/`WorkerDerivedState`, `RepositoryGate`/`worker_available_for_work`, `WorkerProcessIdentity`, `detect_fleet_outage` (+TRANSPORT_AMPLIFIED). EXTENDED: `CoordinatorDisposition`/`coordinator_disposition` bridge (closed-set reason codes; 429/404/stale → READY observations with recorded reason → zero restarts; tunnel/MCP/process → UNEXPECTED_STOPPED → exactly one authority-governed recovery; ownership/ambiguity/quarantine → suppress), `ObservationDeduper` transition gate (duplicate down-state observations never re-report → no duplicate restarts), `plan_parallel_recovery` over dispositions.
- Module 750→350 lines; no durable state, no restart loop, no broad-kill surface remains in the policy layer. Wrapper `start.ps1` untouched (one-shot by design; central recovery owns policy).
- Verification: `tests/test_worker_resilience.py` **24/24** (classification, dispositions, coordinator bridge incl. exactly-once recovery, manual-stop suppression, duplicate-observation gate, authority backoff binding, conductor-restart restore via store, availability gate, parallel planning, fleet correlation incl. post-amplification ± evidence, PID-reuse identity, closed-set reason codes, no-broad-kill source scan); full required battery **145/145** across `test_connector_recovery`, `test_connector_recovery_visibility`, `test_desktop_control_recovery`, `test_serena_config_store`, `test_instance_monitor`, `test_worker_lease`, `test_worker_lease_recovery`, `test_worker_resilience`; `compileall src/a_conductor` PASS; `git diff --check` PASS; strict UTF-8 PASS.
- CHAOS (sacrificial W1 only; evidence `runs/wo156/chaos_w1.json` + post-verify): exact-PID `taskkill` of W1 tunnel-client 21316 → Serena child 3548 died (pipe teardown) → port not ready → policy classified MCP_DOWN (stale pid-file) with restart_permitted → source `ConnectorRecoveryCoordinator` issued EXACTLY ONE restart via the durable spec → NEW pair tunnel 5388 + serena 2732 → READY → post-state rigorously verified (exactly 1 W1 tunnel process, exactly 1 child, no duplicates, W2/W3/W5 untouched). Script's initial FAIL verdict was two strictness bugs in the harness (state-name narrowness + a silent count query), not a recovery failure — post-verification is the authoritative record.
- Live recurrence during the window: W4's tunnel exited again at 11:02:36 with the same empty-code signature (independent of W1 chaos actions) and the RUNNING 2026-08-26 EXE — which predates the in-source recovery commits — could not self-heal it; W4 was restored from its durable spec (new PID 24088). This is direct evidence the permanent fix requires shipping the in-source recovery chain in the installed app (deployment gap, not code gap).
- ESET: present (`ekrn` PID 2596) but ZERO ESET/ekrn provider events or AV detections matching tunnel/serena in the Application log over 3 days → **ESET_TRIGGER=UNCONFIRMED**. Proposed smallest A/B (operator-executed, no exclusions, no engine changes): enable ESET per-process/detection logging export for one monitored window; correlate each empty-code tunnel exit timestamp against the ESET detection log — a single co-timestamped detection confirms; absence across ≥3 exits rejects.
- Frozen candidate: next commit (supersedes b46f7dd for review).

## GLM-A R3 repair checkpoint — 2026-09-04 (third GPT review)

- Blocking findings repaired:
  - P1 no-production-caller: `worker_resilience.py` reduced to the production-wired policy only — `recovery_hold_active()` + the EXTERNAL_CONTROL_SURFACE contract. All consumer-less shapes DELETED: classify_worker/WorkerHealthProbes/WorkerDerivedState, CoordinatorDisposition bridge, plan_parallel_recovery, ObservationDeduper, RepositoryGate/worker_available_for_work, WorkerProcessIdentity, detect_fleet_outage/FleetOutageReport. Production call graph (existing, now the only path): `DesktopControlService.instance_states_cancellable` → `instance_health_state` (real /readyz HTTP probe) → `reconcile_instance_recovery` → `ConnectorRecoveryCoordinator` → `SQLiteSerenaConfigStore.instance_recovery` → `LocalInstanceOrchestrator`.
  - P1 transient hold ≠ manual stop: new injectable `recovery_hold_provider` seam on `DesktopControlService` (fail-closed on provider error). While a hold is active the refresh loop performs ZERO recovery and never calls `coordinator.suppress()`; durable `recovery_suppressed` stays False; when the hold clears, the same real failure recovers exactly once with no manual start. Verified against real SQLite durability.
  - P1 remote 429/404/session: classified EXTERNAL_CONTROL_SURFACE (module contract) — the local production path's only signal is the /readyz HTTP probe; remote conditions are REMOVED from the local production-recovery claim; no fake READY persistence, no suppress, no second telemetry system; READY never triggers restart regardless of flags (test).
  - P1 production-path test: `tests/test_worker_resilience.py` 9/9 — drives `instance_states_cancellable` end-to-end with a real controllable /readyz HTTP listener (real production probe) + real `SQLiteSerenaConfigStore` temp DB + fake ONLY at the process-launch seam (launcher rebinds the listener, mirroring tunnel-client). Sequence proven: READY → real STOPPED → production detects → exactly one coordinator start → durable restart_count=1 in SQLite → stable refreshes no duplicate → service/store RECREATED from the same SQLite file → no replay duplicate, new real failure recovers exactly once (count=2), manual stop suppression survives recreate, transient holds never poison manual-stop state.
- Chaos harness repaired as scratch evidence: relabeled CORE_PROCESS_PROOF (not installed E2E), process_alive via actual CIM identity (never pid-file alone), process count as deterministic integer with −1 ⇒ FAIL on missing evidence. No new destructive chaos run (prior W1 core-process evidence stands; no fresh ownership requirement proven).
- Verification at freeze: required battery **130/130** (`worker_resilience` 9 + `connector_recovery` + `connector_recovery_visibility` + `desktop_control_recovery` + `serena_config_store` + `instance_monitor` + `worker_lease` + `worker_lease_recovery`); extra `test_desktop_control.py` **34/34**; `compileall src/a_conductor` PASS; `git diff --check` PASS; strict UTF-8 PASS.
- Overlap: changed files are `src/a_conductor/desktop_control.py`, `src/a_conductor/worker_resilience.py`, `tests/test_worker_resilience.py` (+this doc). PR #209 (`docs/wo-p1-156-worker-tunnel-incident` @ cad47bc9) is docs-only — zero file overlap; PR #208 (0fd540c) untouched; no live surfaces touched.
- Frozen candidate: next commit (supersedes 55de87f for review).
