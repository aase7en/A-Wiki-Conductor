# WO-P1-603 — P8 ACT-1 Command Gateway (slice A: pure admission authority)

Issue: #603
(Roadmap §P8. This WO is the governance bootstrap + contract freeze; source
mutation is gated to the separate source claim below. Authority seam — the
highest-scrutiny R3 class.)
Class: CONTROL_PLANE_ONLY
Risk: R3 (consequential command / authorization / ownership / replay boundary)
Executor route: Windows ZCode + GLM-5.3 MAX primary session
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo603-act1-bootstrap`
Branch: `docs/wo-p1-603-act1-gateway`
Bootstrap base: `32188f50b4d354becc788a9786a7a83741786cea` (= origin/main)

## Goal — slice A (pure admission authority)

The smallest accepted Command Gateway slice is the **admission boundary
itself**: one pure module that turns a consequential operator command
request into either a typed ADMISSION (bound to the exact existing authority
evidence set) or a typed REJECTION — with ZERO side effects. Execution
dispatch/wiring (slice B) is separately claimed later against accepted
adapters and must consume this admission; it is out of scope here.

## REUSE archaeology (2026-10-07, main 32188f5) — binding inventory

| Seam | Symbols (verified on main) | Class |
|---|---|---|
| operator.v1 vocabulary | `operator_protocol.py`: `OPERATOR_PROTOCOL_VERSION`, `OperatorAction` (status/job.get/job.events/job.create/job.ready/job.claim/job.gate/job.checkpoint/job.execute), `OperatorRequest`, `OperatorResponse`, `parse_operator_request`, `OperatorProtocolError` | REUSE |
| dispatch seam | `operator_dispatch.py`: `dispatch_operator_request`, `OperatorJobControl` protocol | REUSE (slice B) |
| replay/dedupe authority | `execution_deduplication.py`: `ExecutionFingerprintSpec`, `DuplicateExecutionDecision` | REUSE |
| identity guard (#498A) | `pre_dispatch_guard.py`: `LiveWorktreeIdentity`, `LiveWorktreeObserver`, `LiveWorktreeObservationError` | REUSE |
| lease + MSP-2 fence | `worker_lease.py`: `WorkerLease`, `LeaseMutationIntent`, `HotspotFenceKind`, lease store authority | REUSE |
| result visibility | `hook_bus.py` / `hook_stm.py` / `monitor_api.py` (read-only projection) | REUSE |
| admission decision | — no existing pure request→admission authority seam found (grep across src: none) | NEW (one module) |

No second scheduler/task DB/claim store/retry machine/review/completion
authority is created. Slice A performs NO process/Git/network side effects
at all — it only admits or rejects.

## Frozen source scope (source claim)

- NEW `src/a_conductor/command_gateway.py`
- NEW `tests/test_command_gateway.py`
- nothing else.

## Frozen contract (v1)

1. `GatewayCommandRequest` (frozen dataclass): the already-parsed
   `operator_protocol.OperatorRequest` plus required authority evidence
   fields: `repo_root`, `worktree`, `branch`, `head_sha`, `mutation_intent`
   (operator read-only actions are admitted intent=READ_ONLY without lease
   evidence), `task_ref`, `claim_ref`, `fence_ref` (required iff
   intent=MUTATE).
2. `admit_command(request, *, authorities) -> GatewayAdmission` where
   `authorities` is a frozen injected bundle (no ambient lookup):
   `validate_lease(claim_ref, task_ref, scope) -> LeaseEvidence|None`,
   `dedupe_decision(fingerprint) -> DuplicateExecutionDecision`,
   `observe_worktree(repo_root) -> LiveWorktreeIdentity`,
   `fence_status(fence_ref) -> FENCE_OPEN|FENCE_HELD_HERE|FENCE_STALE|None`.
   The module NEVER calls these itself outside `admit_command`, never
   retries, never caches authority state.
3. Admission outcome (frozen dataclass): `ADMIT` with bound evidence
   digest, or typed `DENY` with reason code
   `GATEWAY_…` (REQUEST_MALFORMED / TASK_MISSING / CLAIM_MISSING /
   CLAIM_STALE / IDENTITY_DRIFT / SCOPE_DRIFT / FENCE_MISSING /
   FENCE_STALE / DUPLICATE_UNKNOWN / INTENT_ESCALATION / AUTHORITY_ERROR).
4. Truth rules (failure floor → RED matrix):
   a. malformed/unknown request or action ⇒ DENY REQUEST_MALFORMED, zero calls to authorities;
   b. missing/stale task/claim/lease/owner ⇒ fail closed;
   c. repo/worktree/branch/HEAD drift vs observed identity ⇒ DENY IDENTITY_DRIFT (observed identity is the only truth; request claims never override observation);
   d. scope drift (requested scope not ⊆ claim's lease scope) ⇒ DENY SCOPE_DRIFT;
   e. UNKNOWN dedupe decision ⇒ DENY DUPLICATE_UNKNOWN — never relaunch;
   f. MUTATE intent without open fence held by this claim ⇒ DENY FENCE_MISSING/STALE;
   g. READ_ONLY intent can never acquire MUTATE authority (no escalation path exists; request mutation_intent=MUTATE with a read-only action is INTENT_ESCALATION deny);
   h. authority callable raising ⇒ DENY AUTHORITY_ERROR (gateway failure changes no truth; exception never escapes);
   i. browser/UI payloads are untrusted: everything arrives as data; no code path treats provenance as authority;
   j. secrets: no credential/secret field exists in request/admission; evidence digest covers identity tuples only;
   k. admission is pure: same inputs ⇒ same outcome; no global state; direct bypass of the gateway implies nothing and `GUARD_ENFORCED` can only be claimed by consuming an admission's exact digest.
5. The module imports only stdlib + `operator_protocol` (+ dataclasses for
   evidence types). No I/O, no subprocess, no sockets, no persistence.

## Non-goals

Execution dispatch (slice B), MSP-2 fence acquisition itself (worker_lease
authority owns it — gateway only CHECKS status), #498B/#498D guard wiring,
browser/extension action APIs, SRM/Worker runtime paths, any UI change.

## Acceptance criteria (bootstrap)

Docs-only: this WO merges with identity-fixture + CI green; contract frozen;
source work gated to the next claim with full R3 review/CI/merge/post-main.

## Claim

Bootstrap claim: `WO-P1-603-ACT1-BOOTSTRAP-WIN-001` (released on merge).
Source claim: `WO-P1-603-ACT1-SOURCE-WIN-001` (posted under #603 after the
mutation gate rerun).
