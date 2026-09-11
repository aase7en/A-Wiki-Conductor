# WO-P1-195 — ZRA-2 Phase B deterministic repair task materializer

Status: CANDIDATE_FROZEN_FOR_INDEPENDENT_REVIEW
Parent: `WO-P1-165` / Issue #214 / ZRA-2 Phase B
Claim: `GPT-ZRA2-PHASEB-MATERIALIZER-001` (Issue #214 comment `5635237771`)
Risk: `R3` — repair identity / idempotency boundary
Base: `46f90b329d4991211f5c8a26406f3aca2162e9a7`
Branch: `feat/wo-p1-195-zra2-phase-b-materializer`
GPT/integrator: architecture, R3 adjudication, exact-SHA acceptance, merge/release
Preferred bounded executor after transfer: Sunday-Worker 2 / GLM-capable implementation lane
Result destination: `runs/WO-P1-195/result.md`

## 1. Why this child exists

Phase A of WO165 is accepted, merged, and post-main verified. Canonical Issue #214 records Phase B as `NEXT_READY`; no durable evidence accepts Phase B/C/D yet. PR #263/WO191 therefore remains dependency-blocked and must not be used as proof that ZRA-2 is complete.

This child implements only the frozen Phase-B contract: turn one already-authorized `AgentRepairRequest` plus exact rejected-artifact/review identity into one deterministic, verified `TaskPacketFile`. It must wrap existing authorities instead of creating another task/review/retry lifecycle.

## 2. Reuse-only authority map

Reuse unchanged:
- `AgentRepairRequest` and `build_repair_task_markdown` from `agent_change_packets.py`;
- `TaskPacketFile` from `claude_code_harness.py`;
- `NativeFileSystem` / `NativeExecutionScope` confinement and bounded UTF-8 IO;
- WO165 Phase-A generation/review decision as upstream input only.

This child owns only deterministic materialization. It owns no scheduler, job store, claim, Worker lease, provider selection, review lifecycle, retry/recovery lifecycle, model policy, or merge authority.

## 3. Mutable scope

Allowed tracked mutation after the full source gate passes:
1. NEW `src/a_conductor/zero_relay_repair_materializer.py`
2. NEW `tests/test_zero_relay_repair_materializer.py`
3. this work order

Everything else is read-only unless GPT/integrator opens a fresh explicit scope change after new evidence.

Forbidden in this child:
- WO191 / PR #263 source or tests;
- WO192 / PR #264;
- WO193 / PR #268;
- WO194 / PR #266;
- WO190 / PR #262 bootstrap/orchestration assumptions;
- live Worker/provider/credential/control-center DB/runtime mutation;
- A-Wiki mutation;
- ZRA-3/ZRA-4 source;
- edits to existing scheduler/review/claim/lease/provider/retry/memory authorities.

## 4. Input contract

The materializer must receive typed inputs sufficient to bind all of:
- the existing `AgentRepairRequest`;
- exact rejected task SHA256;
- exact rejected result SHA256;
- exact review finding/reason identity;
- repair generation, which is valid only when exactly `1`.

No caller-supplied free-form prompt text or arbitrary output path may become authority. Validate exact digest/reason/generation inputs before any write.

## 5. Deterministic output contract

For one valid identity tuple:
1. render bytes only through `build_repair_task_markdown(request)` encoded as UTF-8;
2. derive a deterministic project-confined relative path from validated identity, without trusting raw path fragments from task/review text;
3. derive a deterministic `task_contract_ref` binding the exact rejected task digest, rejected result digest, finding/reason identity, generation, and rendered task identity;
4. materialize through the existing confined filesystem;
5. re-read the exact file through the confined filesystem;
6. verify size/hash/content identity;
7. return a valid `TaskPacketFile` whose SHA256 matches the exact persisted bytes.

Required replay semantics:
- same identity + same path + same bytes => reuse the existing artifact and return the same logical packet;
- same deterministic path + different bytes => fail closed with a stable typed collision code;
- invalid/missing/mismatched identity => fail before dispatch authority is produced;
- post-write/re-read mismatch => fail closed;
- no internal retry loop.

## 6. RED-first matrix

Before production implementation, tests must prove intended failure/absence on the base and then cover at minimum:
- valid generation `1` succeeds;
- generation `0`, `2`, negative, boolean, or non-integer fails closed;
- invalid task/result SHA256 fails closed;
- empty/invalid review reason identity fails closed;
- same exact input twice returns deterministic path/ref/hash/bytes and does not overwrite with divergent content;
- pre-existing same-path same-bytes is reused;
- pre-existing same-path different-bytes produces typed collision;
- task digest change binds to a different contract identity;
- result digest change binds to a different contract identity;
- finding/reason identity change binds to a different contract identity;
- unsafe task/review strings cannot escape the configured root;
- mutation-disabled filesystem fails closed;
- missing parent / invalid target / filesystem error remains typed and does not become retry permission;
- returned `TaskPacketFile.sha256` equals SHA256 of exact UTF-8 bytes on disk;
- no scheduler/provider/review/lease side effect is invoked.

Positive controls are required beside meaningful negative controls.

## 7. Verification ladder

During implementation:
1. focused new test module;
2. related `tests/test_agent_change_packets.py`;
3. related task-packet/harness + native filesystem tests;
4. compile/import check;
5. diff/scope/UTF-8/U+FFFD/secret-like added-line checks.

Before freeze, run only the broader regression actually justified by affected imports/call paths. Do not weaken tests to make GREEN.

## 8. Acceptance

A frozen candidate is eligible for independent R3 review only when:
- changed tracked paths are exactly the allowed scope;
- worktree is clean after candidate commit/push;
- deterministic/replay/collision tests are green;
- related regression is green;
- exact candidate SHA and test evidence are written to `runs/WO-P1-195/result.md`;
- no duplicate authority is introduced;
- no unresolved P0/P1/P2 self-audit defect remains.

Independent review must bind exact SHA. Worker/GLM `DONE` is only evidence. GPT/integrator decides acceptance/repair/merge.

## 9. Dependency closeout

This child completing does **not** accept full ZRA-2. After Phase B acceptance, canonical WO165/Issue #214 must explicitly route Phase C, then Phase D, each with a fresh scope/ownership gate. ZRA-3 source remains blocked until B/C/D are all durably accepted.

## 10. Current gate

Docs bootstrap is allowed under the collaboration bootstrap exception. Product/source mutation remains blocked until:
- an isolated Windows execution worktree is created from this exact branch/base;
- repo/remote/branch/HEAD/dirty state is re-pinned;
- Issue/PR/open-branch/worktree/process overlap is rechecked;
- executor ownership is transferred explicitly;
- `SAFE_TO_MUTATE_WO195=YES` is durably recorded.

Until then: `SAFE_TO_MUTATE_WO195=NO`.


## Freeze checkpoint (2026-09-12, GLM continuation under WO200 Q1)

- Existing WIP preserved and completed (not recreated): the untracked materializer/test files were inspected, mapped to every Phase-B acceptance clause, and extended with write-race pinning tests (concurrent exact-bytes reuse; vanished-file fail-closed) and uppercase-digest normalization identity.
- Verification on Windows host DESKTOP-7IB57R4 / Python 3.11.15: focused `tests/test_zero_relay_repair_materializer.py` **28 passed**; related `test_agent_change_packets.py + test_native_execution.py + test_claude_code_harness.py` **137 passed, 1 POSIX-only skip**; `compileall` OK; `git diff --check` clean; strict UTF-8/no U+FFFD; changed scope exactly the three allowed paths; no secret-like added lines.
- Adversarial matrix re-audited against WO200 Q1.5: generation==int 1 (bool/float/str/0/2/negative fail), exact SHA-256 validation (+casefold normalization pinned), bounded reason identity, deterministic content/path/ref, digest/reason changes bind distinct identity, idempotent exact-bytes reuse (mtime preserved), typed collision on divergent bytes, path authority derived only from identity digest (traversal task_id proven harmless), MUTATION_FORBIDDEN/PARENT_NOT_FOUND fail closed, post-write readback mismatch fails closed, returned `TaskPacketFile.sha256` equals on-disk bytes, AST import fence against scheduler/provider/review/lease/memory authority surfaces. No P0/P1/P2 findings.
- Candidate SHA, PR, and residual risks recorded in `runs/WO-P1-195/result.md`. Independent R3 review + acceptance remain with GPT/integrator.
