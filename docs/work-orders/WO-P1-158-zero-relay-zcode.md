# WO-P1-158 — Zero-Relay ZCode Execution (ZRA-1)

Date: 2026-09-05
Owner: GLM1 / GLM-A (implementation); GPT1 = independent review + acceptance authority
Status: PHASE_A_FROZEN (see checkpoints); stacked on Issue #213 R3 design
Priority: P0 accelerator (ZRA-1)
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo158-zra1`
Branch: `feat/wo-p1-158-zcode-zero-relay`
Base: `origin/main@f0ddd0b9245cef7a7525a670f470e1de595d4615`

## Goal

Production ZRA-1: one authorized synthetic task executes automatically through
the ZCode app-server/GLM route and returns an exact task-bound result —
reusing every existing provider/lease/admission/execution authority, with ONE
shared supervised run lifecycle.

## Phase A — shared SupervisedRunCoordinator (frozen 2026-09-05)

- NEW `src/a_conductor/supervised_run_coordinator.py`: the single shared
  orchestration authority extracted from `SupervisedCommandRunner` — execution
  fingerprint, `DuplicateExecutionGuard`, execution-record creation, run-dir
  identity, launch, poll/timeout (incl. transient-UNKNOWN observation cap),
  collect/version CAS, bounded stdout/stderr artifact mapping.
  `SupervisedRunIdentity` is the durable identity bundle.
- `SupervisedCommandRunner` is now a behavior-preserving adapter (spec/scope
  validation + delegation; two probe-compat delegations `_repo_root` /
  `_poll_until_resolved` kept so existing lifecycle tests observe the same
  surface). No behavior, thread, store, retry, or scheduler authority added.
- NEW `tests/test_supervised_run_coordinator.py` (10 tests): adapter⇄coordinator
  equivalence — same fingerprint/operation_ref; same success result, record
  shape/refs (runs/<exec-id>/{stdout,stderr,result}), identity fields, agent_ref;
  exec-id format `exec-[0-9a-f]{16}`; REUSE_COMPLETED reuses the SAME execution_id
  with zero new launches; exactly one durable record per run; zero new threads;
  identical timeout and recovery classifications; identical 64 KiB stdout cap
  (full-file digest, tail-truncated payload); scope validation unchanged;
  identity/dependency validation fail-closed; no threading/scheduler text in
  the coordinator source.
- No ZCode execution, provider-profile change, `NativeCommandSpec` extension,
  DB DDL, Worker/lease/ReviewBus change, or PR219/220 file touched.

Evidence at freeze: `test_supervised_command_runner + test_supervised_execution +
test_execution_deduplication + test_execution_artifacts + test_supervised_run_coordinator`
= **65/65 PASS**; `test_recovery_reconciliation + test_desktop_control` = **45 passed**;
`compileall` PASS; `git diff --check` PASS; strict UTF-8 PASS.

## Forbidden

Second runner/execution store/poll loop/collect-CAS/guard; ZCode live process before
Phase D gates; task content in argv; secrets in durable state; scheduler/lease/
admission/ReviewBus changes; GPT2 WO157; PR219/220; live DB.

## Phase B — provider runtime binding (frozen 2026-09-05)

- `HarnessStrategy.ZCODE_APP_SERVER` added as the typed strategy (app-server is never generic LOCAL_CLI).
- NEW `HarnessRuntimeBinding` (harness_strategy + runtime_provider_ref + runtime_model_ref, opaque stable refs, bounded charset, dict round-trip with exact-key validation).
- `ProviderModelConfiguration.runtime_binding` travels inside existing `models_json` — **no DB DDL**. `ProviderConfiguration` schema gate is now `1.0.0 | 1.1.0` with the rule: 1.0.0 + any binding ⇒ reject. ProviderObservation stays 1.0.0-only.
- Generation authority: binding changes flow through the canonical `save_provider` CAS path — binding change bumps generation (proved 1→2→3); stale expected_generation fails typed.
- NEW `runtime_selection_sha256`: canonical sanitized digest over strategy + refs + base URL + enabled-state only; secrets/prompts/config-repr excluded by construction (digest composition test pins the exact canonical bytes); display name is never binding authority.
- NEW `tests/test_provider_runtime_binding.py` (16 tests): 1.0 legacy decode w/ empty bindings, 1.1 round trip through real SQLite store, 1.0+binding reject, malformed refs/strategies/extra-keys reject, unknown schema reject, generation bump, stale CAS reject, digest stability/field-sensitivity/secret-exclusion, display-name non-authority, corrupt models_json fail-closed.
- Verification: binding suite **16/16**; provider configuration/config-store/policy/execution-authority regression **115/115 total**; compileall/diff-check PASS. No live provider, no ZCode process, no Worker mutation.

## Phase C — ZCode protocol/helper contract (frozen 2026-09-05)

- NEW `zcode_protocol.py` — `ZCodeProtocolDriver`: bounded JSON-lines turn over an ALREADY-STARTED injected transport. NO lifecycle surface (source-scan test: no `import subprocess/os`, no Popen/terminate/kill/CreateProcess/taskkill; no start/stop/spawn/terminate/kill attributes). Typed bounded errors (`ZCodeProtocolError`) with secret-shape redaction in detail; permission requests denied (READ_ONLY); deadline enforcement; child-exit detection. Wire shape = observed 0.16.5 evidence.
- Output budget: `ZCODE_MAX_RESPONSE_BYTES = 64 KiB`; driver cap cannot exceed the production ceiling; exact-cap passes, +1 byte/delta fails typed `RESPONSE_BUDGET_EXCEEDED`; byte-accurate multibyte boundary (é-deltas counted in UTF-8 bytes).
- NEW `zcode_supervised_helper.py` — lifecycle-half CONTRACT (live supervised spawn arrives with Phase D): fixed 6-token allowlisted app-server argv grammar (prompt/task content cannot appear; extras/exe-swap reject); `ZCodeChildIdentity` (bounded non-secret fields only: schema, execution_id, child_pid, child_created_epoch_ms, executable, parent_pid, target_argv_sha256) with strict exact-field document parsing (smuggled keys reject; wrong schema rejects) + canonical JSON serialization; PID-reuse-proof `matches` (same PID + different creation epoch = MISMATCH); `validate_output_budget` fails BEFORE spawn (`ZCODE_OUTPUT_BUDGET_UNSUPPORTED`).
- Credential boundary (design, enforced at Phase D): accepted external secret-reference at the execution boundary; value through memory/env only; never persisted, printed, or hashed into identity.
- Tests: NEW `test_zcode_phase_c.py` **18/18** (happy path w/o thought; advisory thought-failure still sends; permissions denied; typed failures; secret-redacted detail; malformed line; child exit; turn.failed; exact-cap +1; multibyte boundary; ceiling clamp; lifecycle-free source scan; argv grammar incl. prompt-smuggle reject; identity round-trip + strict parse; PID reuse mismatch; pre-spawn budget; deadline). No live ZCode at any point.

## Phase D — SupervisedZCodeRunner integration (frozen 2026-09-05, Q23)

- NEW `zcode_runner.py` — `SupervisedZCodeRunner` on the ONE shared `SupervisedRunCoordinator`, durable `backend_id = zcode-app-server` (distinct from supervised-native; enforced at construction). Fixed 6-token argv (prompt/task content structurally absent; proven by test); environment carries ONLY `ELECTRON_RUN_AS_NODE=1` (no API-key/env secret — credential value flows through the accepted external secret-reference authority at the execution boundary only).
- Selection double-check: sanitized selection digest validated at preparation AND again at the launch seam; drift ⇒ `ZCODE_SELECTION_DRiftError` before ANY spawn or file write (test proves zero filesystem effects).
- Identity-before-prompt: `child.identity.json` atomically persisted then re-parsed and matched BEFORE the first protocol message; argv-sha binds the exact fixed argv.
- Strict artifact ordering proven by write-order test: identity → stdout (bounded final response) → stderr (append-only redacted codes) → atomic strict report.json → result.json ONLY when a REAL terminal exit code exists. EXIT_PENDING / turn-failure ⇒ typed recovery-required with report-only state; result.json NEVER fabricated (tests).
- Normal shutdown = stdin EOF + bounded natural-exit wait; NO terminate/kill ladder and NO automatic kill (source-scan test: no taskkill/TerminateProcess/.terminate()/.kill()/Stop-Process in zcode_runner.py).
- `PROOF_C` (does app-server exit naturally after stdin EOF on the real host): **NOT_RUN / GPT1_AUTH_REQUIRED** — no unauthorized live proof attempted; the bounded natural-exit wait is the production behavior regardless.
- No scheduler/second store/duplicate guard/poll loop/collect-CAS/admission/lease/ReviewBus authority added; no DB DDL; no Worker mutation; no live ZCode anywhere (all 12 runner tests use a scripted transport).
- Tests: NEW `test_zcode_runner.py` **12/12**; broad battery (zcode runner+phase-c, coordinator, command runner, supervised execution, dedup, artifacts, provider binding+config+store+policy+authority, recovery reconciliation) **221/221**; lease/parallel/provider-runtime-assembly/claude backend+harness **171/171**; compileall/diff-check/UTF-8/added-line secret scan (0 hits) PASS. Changed-file scope = the 10 declared WO158 files.

## GPT2-review repair checkpoint — 2026-09-05 (GLM1, addresses P1-1..P1-9)

- **P1-1 lifecycle bypass CLOSED**: `SupervisedZCodeRunner.run` now routes through `SupervisedRunCoordinator.run` (fingerprint → DuplicateExecutionGuard → durable record via the canonical store → launch → poll → collect/version-CAS). The new `ZCodeBackendAdapter` implements the `SupervisedLauncher` shape: `launch` persists the record through `store.create` (mirroring the native supervisor), executes the bounded ZCode turn, and serves the terminal outcome through the coordinator's canonical `inspect`/`collect` path. The high-level runner never spawns a transport directly.
- **P1-3 canonical result**: `result.json` is the exact six-key `SupervisedChildResult` (schema_version/execution_id/child_pid/exit_code/started_at/finished_at) written ONLY on a real terminal child exit; the coordinator's mapped `NativeCommandResult` derives from the canonical artifacts. Response stays `stdout_ref`; redacted diagnostics `stderr_ref`; protocol metadata `report_ref`.
- **P1-4 task authority**: `ZCodeTaskPacketIdentity.from_task_packet_file` verifies a real `TaskPacketFile` (read/size/hash/decode) — raw prompt strings are rejected; the packet is re-hashed immediately before the protocol send (`ZCODE_TASK_PACKET_TOCTOU`).
- **P1-5 credential authority**: `ZCodeSecretResolver` seam (accepted secret-ref authority only; `secret-ref:` grammar enforced); resolution failure fails closed; the value flows only through the closed transport factory into process memory — never persisted, printed, hashed, or in argv. No ZCode-config credential fallback exists in the module (source-scan test).
- **P1-6 selection authorization**: `authorized_selection_digest(PREP|SEAM)` compares the resolved selection against the accepted `HarnessRuntimeBinding` + authorized base URL — stable-but-wrong now rejects `ZCODE_SELECTION_UNAUTHORIZED` before any spawn; checked at preparation AND at the launch seam.
- **P1-7 identity fail-closed**: missing/invalid child PID/creation-epoch/parent metadata raises `ZCODE_CHILD_IDENTITY_UNAVAILABLE` before any prompt (zero protocol sends); the fabricated-`1` fallbacks are gone.
- **P1-8 derived identity**: execution id + run-dir come from the coordinator's canonical record creation (uuid-based `exec-…` + `runs/<id>` refs through the backend policy); the filesystem seam is run-dir-confined (escape test rejects).
- **P1-9 schema reconciliation**: `provider-profile.schema.json` now versions `1.0.0|1.1.0`, adds `ZCODE_APP_SERVER` to both strategy enums, adds the closed `runtime_binding` model object; `harness-dispatch.schema.json` enum gains `ZCODE_APP_SERVER` with an explicit compatibility description; contract tests updated + new 1.1 contract/example tests; a validated `provider-profile-1.1.0-runtime-binding.example.json` added. Existing 1.0.0 artifacts remain valid (enum-superset only).
- Remaining GPT2 items NOT in this checkpoint (honest scope): AC-RES-002 closed helper-kind seam inside `SupervisedExecutionService` (the adapter currently provides the launcher shape beside it — one lifecycle authority, but the supervised-service-internal helper mapping is the next micro-slice), production recovery consumer for `child.identity.json`, production composition/caller assembly, and `PROOF_C` (still NOT_RUN/GPT1_AUTH_REQUIRED).
- Verification at this checkpoint: zcode-runner **14/14** (canonical lifecycle+dedup no-second-launch, prompt-free argv/env, authorized-not-stable selection, base-URL mismatch, secret-ref only + resolution-failure, missing-metadata fail-closed with zero sends, bounded prompt-free identity doc, exit-pending report-only, turn-failure UNKNOWN report-only, no-kill source scan, EOF natural exit); battery #1 (zcode suites + supervised + dedup + artifacts + binding + harness-contract + provider config/store + recovery-reconciliation) **215/215**; battery #2 (lease/lease-recovery/parallel-ready/provider-runtime-assembly/claude backend+harness/provider policy/authority) **192/192**; compileall/diff-check/UTF-8/secret-scan (991 added lines, 0 hits) PASS.

## Credential-delivery repair checkpoint — 2026-09-06 (GPT1 P1 slice 1)

- **Defect:** `ZCodeBackendAdapter` resolved the secret but never delivered it — the environment reaching `open_transport()` contained only `ELECTRON_RUN_AS_NODE=1`, so the suite proved resolve/non-persist but not authentication delivery.
- **Repair:** NEW typed ephemeral `ZCodeEphemeralCredential` envelope (`repr=False`; bounded env-name grammar; `environment_entry` is the only accessor) + factory-protocol change: `open_transport(argv, environment, credential, execution_id, run_dir_ref)`. The adapter resolves → constructs the envelope → passes it through the closed repository-owned factory seam → drops both references in a `finally`. The factory copies the value into the child environment (the accepted ephemeral runtime channel) inside one launch; nothing serializes it. No ZCode-config apiKey fallback exists in the module (source-scan test for `config.json`/`apiKey`/`Path.home()`/`%USERPROFILE%`).
- **RED matrix (8) — all green:** (1) resolved secret reaches the actual transport runtime channel (child env `ANTHROPIC_API_KEY` + envelope accessor); (2) prompt/packet content never rides the credential channel; (3) secret absent from argv, base environment, every durable artifact (report/identity/result/stdout/stderr — full-run-dir byte scan), and the mapped result; (4) resolver failure ⇒ zero spawn; (5) empty secret ⇒ zero spawn; (6) factory exception does not leak the value (memory-only lifetime proven); (7) no config-credential substitution path in source; (8) generic supervised behavior unchanged (86-test supervised battery green).
- Plus: `ZCodeEphemeralCredential.__post_init__` validation; delivery-key eagerly validated at adapter construction; envelope `repr`/`str` never prints the value.
- Verification: zcode-runner **22/22**; battery (zcode + phase-C + coordinator + command runner + supervised execution + dedup + binding + harness-contract + provider config + recovery-reconciliation) **146/146**; compileall/diff-check/UTF-8 PASS; added-line secret scan (179 lines) 0 hits.
- Remaining GPT1 blockers (unchanged, declared): closed helper-kind seam + report_ref confinement; production composition; child-identity recovery consumer. No live dispatch.
