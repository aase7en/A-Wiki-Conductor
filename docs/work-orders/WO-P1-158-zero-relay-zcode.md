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

## Closed helper-kind + report_ref confinement checkpoint — 2026-09-06 (GPT1 P1 slice 2)

- NEW `SupervisedHelperKind` CLOSED enum (GENERIC_NATIVE | ZCODE_APP_SERVER_V1) with a fixed repository-owned `_HELPER_MODULE_BY_KIND` mapping inside `supervised_execution.py`; callers select a kind, never a path (`helper_path_for(kind, helper_path=…)` rejects any caller-supplied path and any unknown kind; kinds not enabled for the service reject).
- `SupervisedExecutionService(helper_kinds=…)` allowlist (default = {GENERIC_NATIVE} — existing behavior unchanged); `helper_path_for` resolves only repository-adjacent helper modules.
- NEW `_build_zcode_helper_spec(plan, kind)`: builds the `OwnedProcessSpec` through the SAME `_validate_plan_with_report` confinement + the repository-owned ZCode helper module, passing only bounded verified metadata (execution id, pid/result/report paths, cwd) + the fixed allowlisted app-server argv — prompt/packet content structurally absent (spec-dump test).
- `_validate_plan` split into `_validate_plan_with_report`: `report_ref`, when configured, resolves through the existing runtime-root `_resolve_ref` confinement and MUST land inside run_dir — traversal (`../`) and absolute-outside refs fail closed `RUNTIME_REF_OUTSIDE_RUN_DIR` BEFORE spawn; generic records (`report_ref=None`) validate byte-identically through the delegation (equality test).
- RED matrix (10/10 green): generic paths identical; ZCode kind → fixed repository helper only; arbitrary path inject rejected; unknown kind rejected; report inside run-dir accepted; traversal rejected; absolute outside rejected; prompt absent from the supervisor command; generic validate unchanged with kinds enabled; canonical launch still `store.create` + `controller.start` (source assertions).
- Regression: supervised execution/command-runner/coordinator/child/dedup/artifacts/helper-kind/zcode suites incl. claude supervised runner + lifecycle/transport recovery = **171/171**; compileall/diff-check/UTF-8 PASS.

## child.identity.json recovery consumer checkpoint — 2026-09-06 (GPT1 P1 slice 3)

- NEW `zcode_child_recovery.py`: pure restart-reconciliation under the EXISTING recovery authority — `reconcile_zcode_child(document, observer)` re-observes the live child (PID + creation epoch + executable + parent through the injected observer primitive) and classifies ATTACH (exact match) vs RECOVERY_REQUIRED with typed reasons (`CHILD_PID_GONE`, `CHILD_PID_REUSED` — same PID different creation time is a stale-PID reuse and is NEVER the original child, `CHILD_EXECUTABLE_MISMATCH`, `CHILD_PARENT_MISMATCH`, `IDENTITY_MALFORMED:*`). `read_child_identity_from_run_dir` reads/parses the durable document as evidence only. No kill, no replay, no polling thread, no new store — source-scan test pins the absent surfaces; result.json is never fabricated.
- Matrix (11/11): exact attach; PID reuse reject; executable reject; parent reject; malformed recovery; PID-gone recovery; no replay/kill surface; report-present/result-absent + live child attaches; UNKNOWN keeps result.json absent; two invocations idempotent; unreadable document recovery.
- Regression: recovery + zcode-runner + phase-C + helper-kind + supervised-execution + recovery-reconciliation **90/90**; compileall/diff-check/UTF-8/secret PASS.

## Production assembly + final source freeze — 2026-09-06 (GPT1 P1 slice 4 / final)

- NEW `zcode_production_assembly.py`: the thin composition path from EXISTING authorities — `ZCodeExecutionAuthorities` (trusted injected: provider snapshot, secret resolver, repository transport factory, confined filesystem, execution store, lease broker, worker/repo/branch/HEAD/dirty context) + `assemble_zcode_execution(...)` building the accepted chain: verified `TaskPacketFile` intake → provider generation gate (existing CAS number) → `ZCODE_APP_SERVER` strategy + per-model runtime-binding authorization → `_AuthorizedSelection` (endpoint-authority truth, deliberately SEPARATE from the dispatch-declared `authorized_base_url`/`endpoint_base_url` pair so stable-but-wrong endpoints fail `ZCODE_SELECTION_UNAUTHORIZED`) → secret-ref → `ZCodeBackendAdapter` → `SupervisedZCodeRunner` on the ONE coordinator. `verify_execution_context` is the git/worktree gate (`ZCODE_HEAD_DRIFT` / `ZCODE_BRANCH_MISMATCH` / `ZCODE_WORKTREE_DIRTY`). NO scheduler/task/lease/provider store, dedup, retry, supervisor, or review authority added.
- NEW `tests/test_zcode_production_assembly.py` (11/11): HEAD drift, branch mismatch, dirty worktree, generation drift, wrong model, wrong base URL (endpoint truth vs declared → zero spawn), task-packet tamper (zero spawn), secret-resolver failure (zero spawn), full chain executes with credential reaching the runtime channel + zero durable/prompt leak (full-run-dir byte scan + argv scan), duplicate fingerprint zero-second-spawn, turn-failure → recovery mapping.
- Final source-freeze evidence: full battery (assembly + recovery + runner + phase-C + helper-kind + coordinator + command-runner + supervised-execution + dedup + artifacts + binding + harness-contract + provider config/store + recovery-reconciliation + worker-lease) **291/291**; `compileall src/a_conductor` PASS; `git diff --check` PASS; strict UTF-8 PASS; added-line secret scan 0 hits.
- All four GPT1 P1 blockers from comment 5555398220 now have source slices: credential delivery (e736faf), closed helper-kind + report_ref confinement (93a69db), child-identity recovery consumer (cab7970), production assembly (this freeze). PROOF_C remains NOT_RUN/GPT1_AUTH_REQUIRED; live dispatch remains separately gated.

## Q26 real specialized-helper execution checkpoint — 2026-09-06

- `SupervisedLaunchPlan` gained the CLOSED `helper_kind` field (typed `SupervisedHelperKind`, default GENERIC_NATIVE — every existing caller unchanged); `SupervisedExecutionService.launch()` now dispatches by kind: GENERIC_NATIVE → existing `_build_owned_spec()` (byte-compatible), ZCODE_APP_SERVER_V1 → `_build_zcode_helper_spec()` (repository-owned helper); kinds not enabled for the service fail closed `HELPER_KIND_NOT_ENABLED` before any child.
- `zcode_supervised_helper.py` now has a REAL executable bounded CLI (`main()` + `__main__`): metadata-only argv (`--execution-id/--pid-path/--result-path/[--report-path]/--cwd/-- <fixed 6-token app-server argv>`), allowlist grammar enforced before spawn, exactly one child with `ELECTRON_RUN_AS_NODE=1` env, real PID/creation/parent identity written to `child.identity.json` and re-parsed/matched BEFORE any protocol send, bounded protocol turn (64 KiB), bounded stdout / redacted stderr / strict report / canonical six-key result ONLY on a real terminal exit, stdin-EOF + bounded natural-exit shutdown, no kill ladder, typed `ZCODE_HELPER_EXIT code=…` output only (no traceback/argv/env echo). Script-mode sibling import fallback for supervisor invocation.
- Honest scope note (Q27–Q29 inputs): the CLI's prompt source still reads the packet path from the accepted environment channel — the confined on-disk re-read TOCTOU contract and the deterministic task-derived operation identity are the declared next slice (Q27), as is the durable cross-process attach/CAS semantics repair (Q28) and the authority-complete assembly (Q29). ZCodeBackendAdapter's parallel lifecycle remains to be constrained in Q29 per the same GPT1 comment.
- Tests: NEW `test_zcode_helper_execution.py` **13/13** (generic helper selection unchanged; default kind generic; ZCODE kind → specialized helper spec; arbitrary kind rejected at plan + enum; disabled kind rejected at launch typed; executable CLI exists; prompt/credential banned from CLI argv source; real subprocess run rejects non-allowlisted argv typed; identity-write precedes run_turn in source order; report_ref confined + traversal rejected; result-write gated behind real-exit isinstance check; import identity stable). Regression (helper-kind + supervised execution/runner/coordinator/child + zcode runner/phase-C/recovery/assembly + dedup/artifacts) **163/163**; compileall/diff-check/UTF-8/secret(226 lines, 0 hits) PASS.

## Q27 TOCTOU + deterministic dedup identity checkpoint — 2026-09-06

- **Defect A closed (real-file TOCTOU):** `ZCodeTaskPacketIdentity` now retains the authoritative confined `path` + `trusted_root` + expected SHA; `verify_unchanged()` re-reads the REAL file immediately before the first protocol send — resolves against the trusted root (escape/traversal ⇒ `ZCODE_TASK_PACKET_OUTSIDE_TRUSTED_ROOT`), requires a regular file, re-checks size, recomputes SHA (mismatch ⇒ `ZCODE_TASK_PACKET_TOCTOU`), decodes the exact verified bytes, and THOSE bytes (never cached `content`) become the protocol input via the adapter launch.
- **Defect B closed (caller-controlled dedup identity):** `canonical_operation_ref()` derives the operation identity deterministically from trusted task identity — `zcode:{task_contract_ref}:{packet_sha256[:16]}`. `SupervisedZCodeRunner.run` no longer accepts a free `operation_ref`: the derived identity is authoritative; a caller label is accepted only when it exactly matches (any other value ⇒ ValueError). Same task ⇒ same identity across restarts/instances; different packet ⇒ different identity; same caller label with different packets can no longer collide.
- NEW Q27 matrix (8 cases) green: file-changed-after-intake ⇒ typed pre-protocol rejection; unchanged bytes pass; same-path/different-bytes rejected; packet path outside trusted root rejected at intake; caller cannot choose identity; cross-instance identity stable; different packet ⇒ different identity; wrong-hex expected hash rejected.
- Regression: zcode runner(30, includes prior 22 + Q27 8) + assembly + helper-execution + child-recovery + phase-C + helper-kind + supervised execution/runner/coordinator + dedup + artifacts + recovery-reconciliation = **172/172**; compileall/diff-check/UTF-8/secret(210 lines, 0 hits) PASS.
- Remaining from GPT1 5556955230 (declared): Q28 durable error/CAS/timeout semantics; Q29 authority-complete assembly + constrain adapter lifecycle; recovery-consumer composition; Q30 truth audit.

## Q28 durable error/recovery/CAS semantics checkpoint — 2026-09-06

- **Error contract closed:** `ZCodeRunError` now SUBCLASSES `SupervisedExecutionError` (recovery_required=True) — the shared coordinator's EXISTING catch maps ZCode backend failures into the durable supervised contract with zero ZCode-specific catches added anywhere. Expected failures surface as normalized failure results (no raw traceback) — proven by the updated secret-failure/identity/TOCTOU tests asserting the typed codes in the failure `stderr` with zero spawns/protocol sends.
- **Durable-first inspect/collect (no process-local authority):** `inspect`/`collect` now resolve through `_load_durable_outcome` — reconstructing the outcome from the durable store + canonical `result.json` (six-key `SupervisedChildResult`) — with the in-memory `_outcomes` map demoted to a same-process fast path only. After restart, a fresh adapter with only the shared store collects a completed execution from artifacts; a durable record without `result.json` inspects as `SUPERVISOR_EXITED_RESULT_MISSING` + recovery_required (no replay, no fabrication); a missing durable row is typed `ZCODE_EXECUTION_UNKNOWN`.
- **CAS honored:** `collect(expected_version=…)` now checks the durable record's current version — mismatch fails closed `ZCODE_VERSION_CONFLICT`; a matching version collects. No silent collect.
- Honest scope note: the adapter still executes the bounded protocol synchronously inside `launch`; moving the long operation into the helper process (supervisor-owned) with coordinator timeout bounding it remains the declared Q29+ slice (same GPT1 P2 note).
- NEW `tests/test_zcode_durable_semantics.py` (9/9): normalized typed launch error (no traceback); typed unknown inspect; typed unknown collect; restart-with-result collects durably; restart-without-result → recovery not replay; version conflict fails closed; matching version collects; UNKNOWN never fabricates result.json (artifact absent on disk); ZCodeRunError is a SupervisedExecutionError.
- Regression: durable + runner(30) + assembly + helper-execution + child-recovery + phase-C + helper-kind + supervised execution/runner/coordinator + dedup + artifacts + recovery-reconciliation = **181/181**; compileall/diff-check/UTF-8/secret(97 lines, 0 hits) PASS.
