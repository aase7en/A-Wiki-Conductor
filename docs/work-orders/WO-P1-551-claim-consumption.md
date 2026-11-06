# WO-P1-551 Claim Consumption Candidate

Issue: #551
Status: IMPLEMENTATION_CANDIDATE / NOT_RUNTIME_ACCEPTED.
Claim: WO-P1-551-CONSUMPTION-001, issue comment 6687970206.
Risk: R3. Topology: CONTROL_PLANE_ONLY. Reuse: WRAP -> EXTEND.
Base: 746a380. Branch: feat/551-claim-consumption.
Worktree: A:/GitHub/AWC-551-claim.

## Boundary And Acceptance

Implement only `src/a_conductor/awiki_claim_reader.py` and
`tests/test_awiki_claim_reader.py`, plus this packet. Do not modify the existing
PR #552 packet, COLLAB, CURRENT-WORK, handoff, or orchestration receiver,
dispatcher, or guards. Shared continuity remains with the integrator.
User directly assigned this executor; no extra provider dispatch is needed.
This candidate cannot activate mutable refill or replace WorkerLease, #498,
DEX receipts, provider admission, scheduling, or the runtime mutation gate.

Pin the upstream interface to A-Wiki PR #75 merge
`79f793788bc807e66d8e31f2e390c7d6475c8784`,
`conductor.state.read_canonical_claim_strict` and `awiki-claim-reader/v1`
(state.py blob `8bd3c75a6ded0c0ca7c8adbfd2cf78df6483919e`). This supersedes
the original PR #67 lenient-reader pin `4c817f2d5a8663501c0158fd49e054877c4cdad7`
/ blob `abd95923ef6d34a64287dba55d148de01c4daa11`. Do not parse COLLAB in
Conductor. The strict reader delegates generation to `claim_generation_strict`;
never add a lenient fallback. This repin does not resolve the stale durable
release decision or certify upstream/downstream CI acceptance.
The reader takes a repository root; that root determines `repository`, task,
branch, generation and scope. A claim in A-Wiki is NOT a claim for AWC.
The upstream CLI has no external-target flag for `claims`; wrap the published
Python reader function with a fixed, isolated subprocess, not a guessed CLI flag.

Task binding is exact, not fuzzy: task_id is the canonical row's complete chunk
string, not an issue-number alias. Pin claim_id, positive integer generation,
repository, agent, full declared scope, branch and full 40-character HEAD.
Consumer worktree is independently observed using the existing read-only Git
runner before and after reading. The upstream marker
`CONSUMER_VERIFY_REQUIRED` never proves a local path. Scope equality is
conservative; this slice does not invent cross-glob containment semantics.
The trusted upstream checkout must match its configured exact revision and be
clean; no cache/fallback reader and no claim writes are permitted.

RED-first tests: absent claim, stale SHA, foreign owner, valid binding; expand
to schema/identity/generation/scope/worktree/transport failures and drift.
Run focused and full local pytest, record failures truthfully, then freeze,
push and open PR without merging. Independent R3 review and exact-head hosted
CI remain acceptance gates. This unwired adapter proves only a claim
precondition, never complete runtime mutation admission or a durable fence.

## Reconciliation Evidence (2026-11-06)

Protected A-Wiki root remains dirty and untouched. Read-only verified mirror
is at PR #67 merge above. GitHub live main is 66f0c16; live COLLAB still contains
`Issue #58 claim authority convergence`, owner `chatgpt-sol`, branch
`fix/issue-58-claim-convergence`, despite Issue #58 being closed by PR #67.

Commands in `A:/GitHub/_verified-sync/A-Wiki`:

- `python -m conductor status --json`: exit 0, returns the stale row unchanged.
- `python -m conductor claims --task-id 'Issue #58 claim authority convergence' --json`:
  exit 1, `GIT_HISTORY_SHALLOW: fetch full history before resolving durable claim generation`.
- `python -m conductor --help`: writer is `claim` (append/create or exact-owner
  refresh); no durable release/reconcile command is exposed.
- Source inspection: bridge.add_claim serializes durable creation and cache
  refresh. No durable release/remove/reconcile API exists in conductor.

Outcome: DECISION_REQUIRED / DURABLE_RELEASE_WRITER_UNAVAILABLE.
No writer invoked: refresh would retain ownership, not release a merged task;
local TTL release cannot release durable authority. Before/after durable row
is identical. No A-Wiki source, COLLAB or claim cache was intentionally changed.
Do not reinterpret merged #58 as permission for mutable refill. Integrator must
obtain an upstream-owned explicit durable release mechanism/action, hydrate
full claim history in an authorized checkout, and rerun the canonical reader.

## Checkpoint

Implemented the bounded unwired reader and exact binding described above.
Initial RED: pytest collection fails with missing `a_conductor.awiki_claim_reader`.
Focused final matrix: 48 passed, including actual Git repositories and isolated
Python subprocess transport against a synthetic upstream API fixture. Related
reader/identity/native/mailbox/runtime/dispatcher matrix: 191 passed.
Actual accepted upstream reader probe against this AWC worktree correctly raises
`ClaimBindingError: CLAIM_NOT_FOUND` for WO-P1-551; no canonical AWC claim was
invented from issue metadata. The initial shell-quoted probe had a SyntaxError;
the corrected probe executed and produced the expected typed refusal.
Compileall and diff-check pass. Initial full regression: 7098 passed, 21 skipped,
4 failed (696.96s). The WO identity check requires the exact standalone
`Issue: #551` line; corrected here. The other failures were missing optional
GPU dependencies (2) and an orchestration child-import bytecode error (1).
No unrelated source fix or test exclusion is authorized; rerun with isolated
test dependencies/bytecode and the CI GPU fallback setting before final freeze.
Upstream release decision and independent review remain unresolved. No live
claim for AWC #551 is fabricated from the unrelated A-Wiki #58 row.

### PR #734 P1 Repair Evidence (2026-11-06)

Continued the same R3 claim from clean tracked head
`504b322ebf9f042dc6c74e16c5eafea903d39011`. Pre-existing untracked `.test-deps/`
contains optional GPU packages, not an upstream snapshot; left untouched.
Only the two claimed source/test files and this packet changed. Shared
CURRENT-WORK/handoff fold-back remains integrator-owned per this packet.

Pin mechanism: production accepts an operator-approved exact `authority_head`
and checks the authority checkout's HEAD and clean status before/after reading.
There was no built-in SHA/blob constant or vendored upstream snapshot. The
approved revision above is now executable contract-test evidence through
`UPSTREAM_REVISION` / `UPSTREAM_STATE_BLOB` in the reader tests. Tests fetch the
real `conductor/state.py` at that exact public GitHub revision once per module,
verify its Git blob hash before execution, and commit those unchanged bytes in
a disposable authority repository. Fixture Git HEAD is local; the verified blob
is the upstream code pin. Network failure fails the suite, never skips proof.
No upstream source/parser is vendored or reimplemented in Conductor.
GitHub API verified PR #75 MERGED at the exact SHA above and state.py blob match.

Production now calls only `read_canonical_claim_strict`. New upstream table
errors retain code-only `ClaimBindingError` refusals; `GIT_UNAVAILABLE` and
`GIT_HISTORY_SHALLOW` remain typed. Unknown errors still refuse as
`CLAIM_READER_FAILED`, never an empty-claim allowance. Existing response,
transport, ambiguity, local binding and source/consumer drift checks remain.

- RED: real-upstream subset on the lenient binding: 4 failed, 1 passed,
  56 deselected. Both malformed-row cases and injected log/diff failures were
  accepted (DID NOT RAISE). Malformed tests independently match the lenient
  generation 2/claim ID so mismatched expected fields cannot mask the bypass.
- GREEN: `python -m pytest tests/test_awiki_claim_reader.py -q`: 61 passed.
  Includes five real-upstream cases and all upstream typed refusal codes.
- Valid WO-P1-551 + short foreign-owner row: `CLAIM_TABLE_MALFORMED` refusal.
- Valid claim + short Lane row + conflicting row: `CLAIM_TABLE_MALFORMED` refusal.
- Git log and Git diff failure injected separately inside the actual upstream
  subprocess: `GIT_UNAVAILABLE` refusal for each, no generation-1 acceptance.
- Well-formed COLLAB: exact independently computed binding returned.
- Related identity/native/WO/guards/dispatcher matrix: 219 passed via
  `python -m pytest tests/test_project_identity.py tests/test_native_adapters.py tests/test_native_execution.py tests/test_work_order_identity.py tests/test_orchestration_guards.py tests/test_orchestration_dispatcher.py -q`.
- Cheap CI platform-neutral command: 16 passed via
  `python -m pytest tests/test_platform_support.py tests/test_branding.py tests/test_sh_templates.py -q`.

G02: no real COLLAB or A-Wiki content mutations; all upstream and COLLAB fixture
writes stay under pytest temporary directories. Contract cases assert unchanged
COLLAB bytes across adapter calls and unchanged/clean authority source afterward.
No runtime/process management, secrets, refill activation or merge performed.
Full regression was not repeated for this bounded delta; historical full-suite
results above are not a new-head certificate. Next gate: independent focused
R3 re-review and exact-new-head hosted CI, then integrator-only merge/acceptance.
