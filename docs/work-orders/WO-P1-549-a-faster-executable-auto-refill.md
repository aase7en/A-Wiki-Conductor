# WO-P1-549 — A-Faster executable auto-refill bridge

Status: R3 MUTABLE FAIL-CLOSED PATCH IN PROGRESS / WO ACCEPTANCE BLOCKED
Issue: #549
Risk: R3 — dispatch/control-plane enforcement
Topology: CONTROL_PLANE_ONLY
Authority repo: A-Wiki-Conductor
Base: c4d4cf4da830cb313a4569a386edcff0a77266c2
Branch: feat/wo-p1-549-a-faster-autorefill
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo549-autorefill

## Goal
Close the accepted A-Faster POLICY_ONLY utilization gap without creating a scheduler or second authority. An active A-Faster/NightShift supervisor must be able to consume the existing deterministic utilization verdict and execute one bounded refill batch through existing scheduler-owned READY assignments, WorkerLease/provider/dedupe authority, PRE_DISPATCH guard, and ParallelReadyExecutor.

## Global invariants
- max 3 simultaneously active mutable lanes; max 1 independent review lane;
- Issue #537 may retain at most 2 borrowed waiting/parked mutable claims, never active writer slots;
- one mutable hotspot = one mutation owner;
- no manufactured work or blind redispatch;
- fresh CoinTH proxy quota + independent upstream readiness before every material GLM dispatch;
- SunDayRemoteMCP remains execution/capability substrate; no execution-repo mutation in this WO;
- model/device identity grants no task/claim/mutation/review/merge/completion authority.

## Frozen mutable scope
Lane A — core bridge:
- src/a_conductor/a_faster_auto_refill.py
- src/a_conductor/a_faster_utilization_guard.py (boundary documentation only)
- src/a_conductor/elastic_worker_capacity.py (accepted production caller only)
- src/a_conductor/parallel_ready_execution.py (reuse #498 PRE_DISPATCH at the lease-to-run seam)
- src/a_conductor/provider_runtime_assembly.py (production guard assembly)
- src/a_conductor/runtime_activation.py (production guard assembly)
- tests/test_a_faster_auto_refill.py
- tests/test_parallel_ready_execution.py (guard + production-caller regressions)

Lane B — Codex/A-Faster integration:
- .codex/hooks/a_sunday_lifecycle.py
- tests/test_codex_a_sunday_hooks.py
- tests/test_a_faster_invocation_contract.py
- .agents/skills/a-faster/SKILL.md

Integrator-only:
- docs/work-orders/WO-P1-549-a-faster-executable-auto-refill.md

Lane C is install/runtime verification only on clean supervisor worktrees and user Codex trust configuration; it owns no tracked repo mutation.

## Bounded acceptance-repair scope extension — claim WO-P1-549-AUTO-REFILL-REPAIR-001

The exact-head Windows CI run found four existing review-execution fixtures that
fail during `ParallelReadyTask` construction after the lease/harness mutation
intent invariant was added. This extension is test-only and limited to:

- `tests/test_zero_relay_review_execution.py` — keep the mutation-lease
  rejection fixture internally consistent so the planner rejection remains
  the behavior under test.
- `tests/test_zero_relay_review_task.py` — make the protocol-v2 read-only
  review fixture's harness intent match its `READ_ONLY` lease.

No production behavior changes are authorized by this extension. Do not alter
other WO223/WO226 tests or source files. Record any newly discovered production
defect in a separate bounded claim before changing it.

## Required executable behavior
1. Accept only an A_FASTER_ACTIVE utilization verdict produced by the existing classifier.
2. Require AUTO_REFILL_REQUIRED and positive FANOUT_TARGET; otherwise launch nothing.
3. Consume an existing scheduler-owned SchedulePlan and exact ParallelReadyTask mapping; never discover/create READY work.
4. Bound selected mutable work to the existing global budget and verdict fanout target; never count borrowed waiting claims as active compute.
5. Delegate the bounded batch only through the injected existing ParallelReadyExecutor path; all lease/provider/dedupe/PRE_DISPATCH truth remains owned by existing authorities.
6. Any malformed/drifted/missing inputs fail closed before execute().
7. Produce a bounded typed refill result/evidence projection only; no durable scheduler/task/claim/retry/review/merge/completion state.
8. Codex hook context must direct the supervisor to the executable bridge when A-Faster markers require refill; the hook itself must not launch or mint authority.

## Acceptance
RED first; focused/related GREEN; py_compile; JSON/hook smoke; diff --check; UTF-8; added-line secret scan; exact-SHA Windows and macOS smoke; independent R3 review; exact-head CI; Sol acceptance and post-main verification. Canonical dirty worktrees are never reset/cleaned/stashed.

## Candidate evidence
- RED: missing bridge module failed collection before implementation.
- Focused Lane A/B: 60 passed.
- Related A-Faster/NightShift/hook suite: 188 passed.
- Existing parallel-ready execution suite: 62 passed.
- py_compile, hooks JSON parse, diff --check, strict UTF-8: PASS.
- Added-line secret signature scan: no matches.
- GLM material author route not used: approved CoinTH resolver returned SECRET_SOURCE_UNAVAILABLE; this is not quota exhaustion.

- Independent R3 review of exact head a22c4503 returned NEEDS_FIX (P0=0, P1=5, P2=1): forged utilization provenance, scheduler/WIP claim provenance, lease/harness intent drift, optional quota/provider authority, missing PRE_DISPATCH enforcement, and raw/ambiguous execution evidence.
- R3 repair re-derives UtilizationVerdict from exact UtilizationFacts, cross-checks ElasticWipFacts, requires exact ReadySet membership plus WIP claim/runtime/scope gates, bounds active/claim headroom through the existing #537 classifier, and requires quota-bound provider authority.
- ParallelReadyTask now fences lease intent to HarnessDispatch intent. Production ParallelReadyExecutor requires the existing #498 WorkerLeasePreDispatchGuard at the lease-to-run launch seam; guard denial never reaches the runner.
- Auto-refill results now project only typed node/kind/reason evidence; post-execute exceptions are RECONCILE_REQUIRED rather than replay/rejection permission.
- Repair regression suites: A-Faster + parallel-ready 86 passed; A-Faster/WIP/Codex-hook contracts 100 passed; elastic/provider/runtime activation 86 passed.
- py_compile, hooks JSON parse, diff --check, strict UTF-8, added-line secret scan: PASS after R3 repair.
- Exact-head PR #550 CI run `36050340753`: Windows `test` failed in four
  `tests/test_zero_relay_review_execution.py` cases at `ParallelReadyTask`
  construction with `lease and harness mutation intent mismatch`; Ubuntu and
  macOS smoke passed. The same four failures reproduce locally on candidate
  `789876bfae4f3f4d94935eea7d4ea721fe79cde2`. Claim
  `WO-P1-549-AUTO-REFILL-REPAIR-001` owns only the two fixture paths above;
  the working-tree repair and evidence are recorded below.

## Acceptance-repair checkpoint — 2026-09-25

- Claim checkpoint: Issue #549 comment `5822135810`.
- Starting candidate: `789876bfae4f3f4d94935eea7d4ea721fe79cde2` on
  `feat/wo-p1-549-a-faster-autorefill`, based on
  `main@c4d4cf4da830cb313a4569a386edcff0a77266c2`.
- RED: the four CI failures reproduced locally. The first fixture constructed
  a mutation lease with a read-only harness; the protocol-v2 read-only review
  fixtures inherited a mutating harness with read-only leases. The new
  `ParallelReadyTask` invariant correctly rejects both inconsistent shapes.
- Repair: migrated only test fixtures in
  `tests/test_zero_relay_review_execution.py` and
  `tests/test_zero_relay_review_task.py`; preserved checks that mismatched
  intent is rejected at construction and that review routes cannot be minted
  from mutation-authorized tasks. No production behavior changed.
- GREEN: review execution + review task suites, `154 passed`.
- GREEN: WO-P1-549 Lane A/B, utilization, elastic capacity/fencing, parallel
  execution, PRE_DISPATCH guard, provider/runtime assembly and activation,
  WorkerLease/recovery, and both review suites: `508 passed`.
- `py_compile`: 14 changed Python files PASS; hooks JSON parse PASS;
  `git diff --check` PASS; strict UTF-8/mojibake scan PASS over 16 changed
  paths; added-line high-confidence secret scan PASS.
- Exact uncommitted repair diff is limited to this WO checkpoint and the two
  claimed fixture files; no production source changed in the repair.
- Next: freeze and push the exact candidate, run exact-head CI, obtain an
  independent R3 review, then continue Sol acceptance and post-main gates.

## Independent R3 review and claim-authority checkpoint — 2026-09-25

- Reviewed candidate: `3f3a87ac23f2de1193f7d09ccc897e5fb5d4cad6`; PR #550,
  base `main@c4d4cf4da830cb313a4569a386edcff0a77266c2`.
- Exact-head CI run `36059479359`: SUCCESS on Windows, Ubuntu, and macOS.
- Independent exact-SHA R3 verdict: `CHANGES_REQUIRED`, P0=0 / P1=1 / P2=0.
- P1: `execute_auto_refill()` checks projected WIP counters/gates but does not
  bind selected node/task IDs to current canonical repo/work-order claim
  records. Mutable claim headroom includes `new_borrow_target`, although the
  bridge does not acquire those claims. Caller-supplied stale or mismatched WIP
  evidence can therefore pass a selected assignment without proving its
  current claim and eligibility.
- Finding and CI evidence are recorded in Issue #549 comments `5822438093` and
  `5822592246`. Candidate `3f3a87a` is not accepted and must not be merged.
- Read-only reuse audit pinned A-Wiki `main` and `origin/main` to
  `25102e44950ccd28c2d22eafc6e6f1d2119f18ad`. The accepted integration
  contract assigns durable `repo_coordination_claim` to A-Wiki as OWNER and
  A-Conductor as ADAPTER; `runtime_lease` is a separate A-Conductor-owned
  authority. A-Wiki Issue #58 is OPEN: durable COLLAB/Git claim identity is the
  canonical repo claim, while the local TTL claim cache is same-machine only.
  No A-Conductor source adapter was found that reads current durable claims and
  binds them to selected auto-refill task IDs. No A-Wiki files were changed.
- Reuse classification: EXTEND/WRAP the existing A-Wiki claim authority and
  A-Conductor runtime admission; do not create a new claim store. The current
  fixture-repair claim does not authorize production changes.
- `SAFE_TO_MUTATE=NO` for the P1 production repair until the existing durable
  claim-reader interface and exact task-to-claim binding are established and a
  fresh source claim is recorded. No production source repair has been made.
- Next safe action: identify the accepted current-claim reader/API and its
  task identity contract. Then create a fresh bounded source claim, add RED
  regressions for stale/foreign/missing claims and projected new claims, repair
  only through existing authorities, and obtain fresh exact-SHA R3 review and
  CI. If no such reader exists, keep mutable auto-refill fail-closed and
  resolve the adapter contract before implementation.

## User-confirmed claim-reader absence and fail-closed repair — 2026-09-25

- User clarified that no runtime reader/API currently binds canonical A-Wiki
  repo/work-order claims to Conductor task IDs. No A-Wiki files were changed;
  do not add a duplicate claim store or reader in this WO.
- Fresh source claim: Issue #549 comments `5822859238` and scope extension
  `5822893729`. Scope is the bridge, production elastic caller, focused tests,
  and this WO / `CURRENT-WORK.md` / `handoff.md` checkpoint.
- Mutable A-Faster refill now returns the typed reason
  `CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE` before executor dispatch.
  `ProductionElasticWorkerExecutor.execute_once()` refuses mutable A-Faster
  context before provider eligibility/admission, scheduling, or capacity work.
  The bridge also refuses direct mutable calls. The independent read-only
  REVIEW lane remains unchanged.
- Projected `new_borrow_target` is no longer counted as existing claim
  headroom. Regression coverage proves a new projected claim cannot authorize
  a mutable task and that the production path does not reach provider checks,
  scheduling, or the executor.
- RED before source repair: four focused fail-closed regressions failed because
  mutable dispatch still executed. GREEN after repair: A-Faster refill,
  elastic capacity/hardening/WIP/fencing, parallel-ready execution, utilization
  guard, provider/runtime assembly, and runtime activation: `238 passed`.
- At this checkpoint, exact-head CI run `36062290255` passed Windows, Ubuntu,
  and macOS on pre-repair `f4b55b2d0934ac9b0de5c625b55728c56c8e6443`; the
  repaired candidate still required its own review and hosted CI. The current
  candidate's completed CI is recorded below.
- The earlier `GLM_ROUTE_BLOCKED` routing statement was too broad: absence of a
  structured MCP tool did not prove that no local Kilo route existed. Fresh
  bounded checks found Kilo 7.7.9, catalog model `cointh-glm/glm-5.3`, and the
  approved `COINTH_GLM_AUTH_TOKEN` environment binding (value not read or
  printed). The prescribed quota GET returned `urllib.error.URLError` without
  an HTTP response, so quota is `UNKNOWN`, not exhausted. Kilo credential
  binding and exact upstream admission remain unverified. No roll-call or
  model invocation occurred; no GLM usage should have been consumed. Corrected result:
  `GLM_OFFLOAD=BLOCKED` for this candidate because quota/upstream admission are
  unknown. See Issue #549 correction comment `5823122823`.
- A-FastTask/A-Faster/A-NightShift recovery and routing guidance was applied,
  but the early GLM route/readiness check was incomplete before Codex authored
  the patch. The supervisor SessionStart hook was verified active and injected
  its contract; it supplies instructions and does not itself dispatch GLM.
- Roadmap check: WO-P1-549 is not a named node in the current P0 Zero-Relay
  sequence. This work follows the existing #549 work order, not a direct P0
  roadmap node. Do not start the next roadmap lane while #549 acceptance is
  blocked.
- The original #549 executable-mutable acceptance remains **NOT MET** while
  this lane is disabled. Keep PR #550 open and do not merge this repair until a
  separately scoped adapter contract can bind current canonical claims to
  selected task IDs and re-enable mutable refill under that authority.
- Source candidate `3aab3dc2f2f0075643ed2a921ec92eecc735dedf` passed exact-head
  CI run `36065183019` on Windows, Ubuntu, and macOS, including Windows
  packaging and install/uninstall E2E. Next: finalize this documentation
  checkpoint, push it, then obtain focused independent exact-SHA R3 review and
  fresh exact-head CI for the resulting PR head. Do not advance to post-main or
  the next roadmap node while #549 acceptance is blocked on the claim-reader
  contract.
