# WO-P1-150 — ODP-1 Orchestration Packet v1

Status: READY_FOR_INDEPENDENT_REREVIEW / CI_RERUN_REQUIRED
Lane/files:
- `src/a_conductor/orchestration_packet.py`
- `tests/test_orchestration_packet.py`
- `docs/contracts/orchestration-decision-plane.md`
- `docs/work-orders/WO-P1-150-orchestration-packet-v1.md`
Branch: `feat/wo-p1-150-orchestration-packet-v1`
Model tier: primary-only for contract; implementation is deterministic-executor sized after contract is fixed

## Goal + Acceptance criteria

Implement a pure, side-effect-free Orchestration Packet v1 projection that gives a future decision provider the minimum execution facts needed to propose a bounded graph/next action without receiving secrets, whole-chat history, provider endpoints, credentials, or mutation authority.

Acceptance:
- packet is built from existing task-contract data + TaskGraph state + explicit repository facts + pre-eligible route candidates;
- READY frontier is derived from the existing `compute_ready_set()` authority;
- graph node summaries preserve objective/scope/capability/status without copying legacy `model_requirement` into canonical routing semantics;
- task contract is allowlist-projected; arbitrary `metadata`, requester/approver identities, raw commands, endpoint/secret values are not copied;
- route candidates are declared already eligible and contain safe identity/capability/trait/evidence metadata only;
- positive integer bounds exist for parallelism and adjudication rounds, default adjudication budget = 3;
- duplicate candidate IDs and malformed inputs fail closed;
- output is deterministic/JSON-safe and contains no live objects;
- no I/O, provider probe, credential resolution, scheduler mutation, job mutation, or graph mutation occurs;
- focused tests pass and relevant graph/task-contract tests remain green.

## Reference pattern

- `schemas/task-contract.schema.json` — existing bounded task authority vocabulary.
- `src/a_conductor/graph/domain.py` — canonical TaskGraph/node/capability metadata.
- `src/a_conductor/graph/ready.py` — READY frontier authority.
- `docs/contracts/a-wiki-a-conductor-integration.md` — `ExecutionRequest`/Policy/Evidence boundary and anti-duplication rule.
- `docs/contracts/capability-vocabulary-bridge.md` — capability authority remains A-Wiki.
- PR #201 / WO149 roadmap — ODP architecture proposal; not required as runtime dependency.

## Steps

1. Write failing focused tests for the packet projection and redaction/invariant boundaries.
2. Run focused RED and record exact failure.
3. Implement the smallest pure projection module.
4. Run focused GREEN.
5. Add the contract document describing authority, fields, exclusions, and future ODP seams.
6. Run related graph/provider/task-contract regression plus compile/diff/UTF-8/secret gates.
7. Self-review actual diff and checkpoint exact evidence.
8. Push/open PR only after current remote/ownership recheck.

## Forbidden

- mutation outside the four declared files;
- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `PROJECT-PLAN.md` mutation;
- PR #199/WO148 provider-service-authorization scope;
- PR #200/WO147 ReviewBus-adapter scope;
- provider selection/admission logic in this slice;
- planner/model invocation in this slice;
- new scheduler/task store/provider registry/review bus;
- hard-coded vendor/model names as canonical task semantics;
- copying task-contract `metadata`, requester/approver identity, allowed/forbidden command strings, credentials, tokens, cookies, endpoint URLs, environment dumps, or chat transcripts into the packet;
- live Worker/provider/AiPASS traffic;
- A-Wiki repository mutation.

## Verify commands

```powershell
python -m pytest -q tests/test_orchestration_packet.py
python -m pytest -q tests/test_graph_domain.py tests/test_graph_ready.py tests/test_provider_execution_authority.py
python -m compileall -q src/a_conductor/orchestration_packet.py
git diff --check
```

Also verify:
- changed files exactly match declared scope;
- UTF-8 decode + U+FFFD = 0;
- added-line credential-shaped scan = 0;
- no provider/model hard-code in production module;
- no source object mutation during projection.

## Checkpoint log

- [2026-09-03] GPT-5.6 Sol: claimed local A-Wiki coordination lease `01b8c52dd31b` for exactly the four declared files. Isolated clean worktree `A:\GitHub\A-Wiki-Conductor-wo150-orchestration-packet`, branch `feat/wo-p1-150-orchestration-packet-v1`, base `origin/main@6e96b773aeb0795807cb65abce93956b7702f33e`. Open PR #199 and #200 scopes checked; no overlap. Current `DEFECT_LESSONS.md` read before source mutation. Next action: write RED tests only, run them, then implement.- [2026-09-03] GPT-5.6 Sol RED: `python -m pytest -q tests/test_orchestration_packet.py` failed during collection with `ModuleNotFoundError: No module named a_conductor.orchestration_packet` before production implementation. Test credential sentinel was normalized to a non-credential-shaped value before GREEN so repository secret scanners are not trained to tolerate key-like fixtures.
- [2026-09-03] GPT-5.6 Sol GREEN + self-review: initial focused GREEN = 10/10. Self-review added three RED regressions for nested routing-extra leakage, READY/status default mismatch, and malformed sequence TypeError; RED = 3 failures / 10 passes, then repaired to 13/13 PASS. A transient PowerShell edit inserted literal newline escape text and produced a SyntaxError; repaired immediately with no scope growth. Related graph/domain/ready/scheduler/dispatch/store/provider-authority matrix = 131/131 PASS; compileall PASS; `git diff --check` PASS; production model-name hard-code scan PASS; added-line credential-shaped scan PASS; UTF-8 normalized. Fresh fetch confirms base still equals `origin/main@6e96b773aeb0795807cb65abce93956b7702f33e`. No provider invocation, selection/admission logic, scheduler mutation, or live traffic was added.
- [2026-09-03] GPT primary adversarial review reproduced a task-contract authority bypass: malformed schema version, risk class, authority/security booleans, budget, required-evidence and scope policy values were projected instead of rejected. GPT owns a bounded RED-first repair in the existing four-file WO150 scope; no provider/runtime/live-I/O scope growth.

- [2026-09-03] GPT RED repair cycle: authority-drift RED `c18c95f` reproduced 7/7 malformed task-contract controls being projected; GREEN `edb8dbd` added bounded validation for projected v1 authority semantics. A second adversarial probe proved raw path/credential-like free text could cross fields documented as references; RED `56ff1e5` reproduced that boundary plus non-boolean routing traits. Final repair requires bounded safe namespaced refs for repository/worktree/policy/evidence seams and validates routing control types. Focused current = 22/22 PASS; related graph/domain/ready/scheduler/dispatch/store/provider-authority matrix = 121/121 PASS; compile/diff/UTF-8 PASS. Process deviation: GitNexus impact was not run before the first production edit and must be recorded as a late gate, never rewritten as pre-edit evidence.
- [2026-09-03] GitNexus late gate after local index: detect-changes = 4 files / 18 symbols / 5 affected flows / MEDIUM. FTS remained unavailable because the existing Windows OpenSSL runtime dependency is missing; no DLL was installed. `gitnexus analyze` unexpectedly appended GitNexus instructions to tracked `AGENTS.md` and created `.claude/**` + `CLAUDE.md`; pre-call status proved those paths were clean/absent, so GPT restored only those tool-generated artifacts. `AGENTS.md` hash is byte-equivalent to HEAD and the generated untracked artifacts are absent. This is recorded as a tool-side-effect/process deviation, not hidden as a clean pre-edit impact gate.
- [2026-09-03] Production + contract repair frozen as `51a92f1b9395eeb42a353c68305161a23baf7052`. Current exact local evidence after repair: focused packet **22/22 PASS**; related graph/domain/ready/scheduler/dispatch/store/provider-authority **99/99 PASS** (121/121 including focused); `compileall`, `git diff --check`, strict UTF-8/U+FFFD and deterministic added-line credential scan **0 hits**. GitNexus late detect-changes = MEDIUM, 4 files / 18 symbols / 5 flows. This candidate still requires a fresh independent exact-SHA rereview and hosted CI on the final checkpoint SHA before merge. The previously dispatched GLM Phase E pin `5c6d803...` is intentionally stale and must not be treated as review of this repair.

- [2026-09-03] GPT RED3 semantic-reference review found that generic `namespace:anything` still accepted raw path/URL/environment and credential-shaped payloads (`file:C:/...`, `https:...`, `env:...`, `evidence:Bearer_*`). RED `9b40e1f438cdcf1a5307be7aabb1629c87a2fbee` reproduced 7/7 unsafe values while one declared semantic reference case remained valid. Repair switched to field-specific namespace allowlists plus bounded payload checks and added cross-field namespace regressions. Current local evidence: reference subset 10/10 PASS; focused packet 31/31 PASS; related graph/dispatch/store/provider matrix 81/81 PASS; broad packet+graph+parallel/provider matrix 174/174 PASS; compileall/diff-check/strict UTF-8 PASS; added-line credential scan 0 hits; GitNexus detect-changes 2 working files / 17 symbols / 3 affected flows / MEDIUM with the same FTS runtime limitation. Candidate `84b12eb...` is stale after this RED3 repair and must not be independently accepted.
- [2026-09-03] RED3 production/contract repair frozen as `9b9593f49a9bacd95c65f6778f35066cdf8b04ab`. Next safe action: fresh hosted CI plus independent exact-SHA rereview of the final checkpoint SHA; no merge authority is implied by local GREEN evidence.
