# WO-P1-112 — AHA-5 multi-agent review/repair loop

Date: 2026-08-29
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / FILE-BRIDGE GREEN / AUDIT GATE
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-aha5-review-repair`
Branch: `feat/wo-p1-112-aha5-agent-review-repair-loop`
Base: `origin/main@7f9a16f6dfafe17f3795167da22d4886945611e0`
Parent: Sunday Family Harness Accelerator / AHA-5

## Goal

Prove one GPT-plan/review -> GLM-implement/repair vertical slice where task, status,
result, diff and deterministic evidence move through durable repository state rather
than human copy/paste. Human prompt relay is fallback only when direct provider
execution is unavailable.

## Reuse classification

**EXTEND + WRAP** the accepted Claude-Code harness, durable job state, execution
artifacts, provider configuration, supervised native runner and AHA-4B worker lease.
Modernize stale `docs/agent-collab/*`; do not create a second scheduler, memory,
claim system, task store, retry lifecycle or provider-specific orchestration model.
## Lane contract

### GPT integrator lane
- owns architecture, task packet, acceptance criteria, review, merge and release authority;
- may edit coordination/docs plus integration surfaces assigned by this WO;
- must read GLM result/evidence directly from durable files/artifacts;
- must never treat an agent's `DONE` claim as acceptance evidence.

### GLM implementation/repair lane
- receives one immutable task packet reference plus exact worktree/branch/HEAD;
- mutates only its leased allowed scope in an isolated worktree;
- writes status/result to the task's durable result destination;
- records tests, diff summary, blockers and next safe action there;
- never edits GPT-owned coordination files, merges PRs, publishes releases or changes credentials.

### Future-agent lanes
Use the same packet/result contract. Provider/model names are metadata, not lifecycle
semantics. Two mutable lanes may run concurrently only when lease/scope checks prove
non-overlap.

## Required durable packet fields

`task_id`, `goal`, `owner`, `provider`, `model`, `worktree`, `branch`, `expected_head`,
`allowed_scope`, `forbidden_scope`, `acceptance`, `verification`, `evidence_destination`,
`status`, `checkpoint_at`, `result_ref`, `next_safe_action`.
## Acceptance criteria

1. One bounded external-agent implementation task can use automatic dispatch when provider-ready, or the one-prompt human bridge when externally blocked; result copy/paste is never required.
2. Mutation is impossible without exact identity + active compatible worker lease.
3. Mutation is confined to allowed scope; forbidden/overlap/dirty uncertainty fails closed.
4. Result packet/evidence survives process/session/model rotation and is re-readable by GPT.
5. GPT can issue one bounded repair round from failed review without a new human prompt.
6. Timeout/transport loss becomes uncertain ownership/reconciliation, never blind replay.
7. Secret values never enter tracked packets, logs or result artifacts.
8. Stale/hard-coded `docs/agent-collab/*` becomes provider-neutral and points to SSoT.
9. Existing READ_ONLY Claude harness behavior remains backward compatible.
10. Focused + integration + chaos/race tests, compileall, diff/scope/secret audit and
    exact-head Windows/Ubuntu/macOS CI including Frozen Setup E2E pass before merge.

## GLM suitability evidence

Official Z.ai GLM-5.3 evidence reviewed before delegation: Terminal-Bench 3.0 28.3,
DeepSWE v1.1 66.9 and Z.ai Code Bench Max 34.5%; Z.ai recommends max reasoning for
coding and officially supports GLM Coding Plan through Claude Code. This makes GLM
appropriate for bounded implementation/repair, while GPT retains architecture,
trust-boundary review and merge authority.

## Initial implementation gap

The accepted harness already verifies task packet hashes, provider readiness, structured
JSON output, durable job evidence and secret redaction, but deliberately rejects mutation
(`HARNESS_MUTATION_NOT_READY`) and supervised Claude native execution sets
`mutation_allowed=False`. AHA-5 must open only a lease-bound scoped mutation path rather
than bypass these gates.

Next: checkpoint claim -> write RED contract tests -> smallest mutation/result bridge ->
independent review -> real GLM vertical slice -> bounded repair slice -> CI/merge loop.

## Checkpoint — proposal boundary GREEN

- Chosen design is narrower than the initial mutation plan: GLM/other models remain
  read-only and return structured complete-file proposals; only Conductor materializes
  changes through exact owner/task/HEAD + active mutating lease + scope + content-hash gates.
- Added `agent_change_packets.py` with strict proposal/result decoding and deterministic
  lease-bound apply; overwrite proposals require `expected_sha256` to prevent stale/TOCTOU writes.
- A pre-existing untracked `tests/test_agent_proposal_decoder.py` was discovered during
  resume, preserved, reconciled into the same provider-neutral decoder contract, and not overwritten.
- Focused decoder/apply tests: 11 passed. Relevant lease/supervised/Claude integration:
  176 passed. `compileall` and `git diff --check` PASS.
- Live direct GLM probe through raw `subprocess.run(timeout=30)` exposed a Windows process-tree
  hazard: Claude descendant inherited capture handles and delayed parent completion until the
  descendant exited. Production/live AHA-5 execution must therefore use the accepted supervised
  execution service, never a raw subprocess shortcut.
- Next: clean checkpoint commit -> supervised direct-Z.ai GLM vertical slice from exact HEAD ->
  decode proposal -> lease apply -> deterministic review -> bounded repair round.

## Checkpoint — file bridge + repair GREEN / live-provider blocked

- `AgentResultPacket.as_dict()` provides stable durable JSON handoff.
- `AgentResultFileReader` is root-confined through `NativeFileSystem` and verifies task/provider/model identity.
- AHA-5 intentionally permits one mutable file per agent task; broader fan-out/fan-in is AHA-6.
- `AgentRepairRequest` + repair-task Markdown carry deterministic review findings into one bounded repair round using the same task/lease authority.
- Deterministic file-bridge E2E proves result → apply → review-fail → repair packet → repaired result → apply without human result copy/paste.
- `docs/agent-collab/*` is provider-neutral and no longer acts as stale duplicate SSoT.
- Live automatic GLM-5.3 MAX attempt reached Z.ai after fixing user-settings isolation, but provider returned HTTP 429 `[1113]` insufficient resource package.
- Installed ZCode 0.16.5 reports full GLM-5.3 Coding Plan `coding_plan_not_entitled`; Start Plan exposes GLM-5.3-Flash. CLI help also advertises flags that its parser rejects, so it is not accepted as a reliable automatic GLM-5.3 MAX path in this checkpoint.
- The user has a working external Claude-CLI GLM proxy profile, but its credential is not stored or copied into tracked/runtime evidence. Automatic proxy dispatch remains fail-closed until an approved external secret/profile resolver exists.
- User-requested fallback therefore remains first-class: human relays one short prompt pointing to task/result files; integrator reads the result directly.
- Focused bridge/harness tests: 34 passed before SSoT/docs checkpoint.

Next: defect-memory → broad lease/supervised/harness regression + chaos → compile/diff/secret audit → commit/push → Draft PR → remote review/3-OS CI/Frozen Setup → re-audit/merge/post-main.

- AHA-5 audit evidence: related suite 122 passed; CI-equivalent full suite 1687 passed, 1 environment skip, 0 failed; compileall/diff-check/secret-pattern scan PASS.
