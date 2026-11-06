# WO-P1-733 ORCH-1/5 External Parent Admission

Identity schema: GITHUB_ISSUE_V1
Issue: #733

Parent: #709 (ORCH-1 foundation).

Status: AUTHOR_VERIFIED_OFFLINE_SUBSET / REVIEW_PENDING / NO_OPERATIONAL_ACCEPTANCE.
Classification: R3 / CONTROL_PLANE_ONLY.
Owner: Windows implementation executor, not architecture acceptance authority.
Claim: ORCH-1-5-EXTERNAL-PARENT-001 / #733 comment 6687958728.
Base: origin/main 746a380d979a0d9d112f15371505b307f7c3b271.
Worktree: `A:/GitHub/AWC-orch1-5`.
Branch: `feat/orch1-external-parent`.
Device: Windows local tools; no device credential inspected or issued.

## Authority And Scope

Explicit user assignment authorizes bounded /5 implementation, RED-first tests,
full local verification, normal push and a review PR. NO merge or live activation.
Binding design: [ORCH-1 foundation](ORCH-1-foundation-design.md), sections 3,
5, 7 and especially the frozen section 8 stop gates.

[Approved naming decision](https://github.com/aase7en/A-Wiki-Conductor/issues/709#issuecomment-6684442546):

> APPROVED (user, 2026-11-06): (a) external Parent caller = operator.v1 wrapper
> (Sunday-owned-issuer device credential per #630 ruling); (b) queue-producer
> serialization owner = conductor runtime orchestration_dispatcher (single-writer;
> external parents submit via operator.v1, never enqueue directly).

The same decision says future Supervisor app calls THROUGH operator.v1, not as
a second external parent. Naming is approved; the missing implementation is not
treated as already-proven ordering authority.

[Accepted issuer boundary](https://github.com/aase7en/A-Wiki-Conductor/issues/630#issuecomment-6128003273)
approves M2 v2 offline design, separating credential authentication from task
admission. No Desktop Commander token or issuer may substitute for Sunday trust.
No new trust anchor, production issuance, key ceremony or secret inspection here.

Original bootstrap mutable allowlist (superseded by approved resumption below):
this new work order and the explicitly requested
local `.status-orch1-5.md` checkpoint only. Product/source/tests remain read-only
until the unresolved frozen authority gates below are reconciled. Proposed later
source scope is an additive operator admission seam plus tests, the existing
dispatcher plus tests, and additive explicit runtime composition, after an exact
allowlist is frozen. No CI, #583/#517 policy or operator protocol changes are
implicitly authorized by this bootstrap.

Shared CURRENT-WORK.md, handoff.md and COLLAB.md stay integrator-owned under
COLLAB_PROTOCOL section 3; this WO and child/parent issue checkpoints carry
fold-back evidence. Protected root and every other worktree stay untouched.

## Frozen Contract And Failure Model

- Only operator.v1 is the named external Parent, authenticated by the existing
  Sunday-owned issuer verifier, with exact issuer and caller binding. Unknown,
  unverified or foreign bindings must fail closed before authority reads.
- External parents never enqueue directly. Dispatcher owns admission and ordering
  across ALL queue producers, including multiple roots/processes/devices.
- Design section 3 explicitly says a local mutex is not cross-device serialization.
  Missing serialization means ORCH_QUEUE_SERIALIZATION_UNPROVEN, not a new ORCH
  lock database/file lease/semaphore or an injected boolean asserting permission.
- Preserve actual receiver pagination and duplicate -> utilization -> authority
  pipeline. A credential is not task/claim/queue permission. #551 stays unchanged.
- Canonical issue/WO aliases, current Parent role, result drift, and interrupted
  or inProgress recovery must be resolved by the owning authority, not guessed.
- Required pre-effect audit must map to an existing owner/checkpoint. Never make
  a fake worker/job record merely to log a pre-job Parent bootstrap.
- One QUEUE_ADD at most per admitted invocation; accepted #583 task key unchanged.
  Timeout after possible append requires reconciliation, never automatic retry,
  resume/start/delete or worker followup. No universal exactly-once claim.
- Offline fixture proof cannot certify a real writer or production activation.
  No newly exposed operator verb or generic signal tunnel without protocol freeze.

## RED Matrix And Acceptance

| Case | Required RED then GREEN evidence |
|---|---|
| Unknown caller | Typed fail-closed refusal, zero authority/effect calls |
| Unverified credential | Typed refusal; issuer and caller binding both checked |
| Wrong issuer/caller/device | No trust substitution or payload-minted admission |
| Direct external enqueue | Typed refusal, zero queue effects |
| operator.v1-routed equivalent | Real registered wrapper -> dispatcher -> existing admission -> one append |
| Duplicate/replay | Existing guard blocks repeats, including later-page duplicate |
| Concurrent producers | Proven shared serialization spans collection/final check/audit/append; no local-lock claim |
| Missing serialization | Typed ORCH_QUEUE_SERIALIZATION_UNPROVEN, zero append |
| Alias/recovery ambiguity | No guessed identity, no interrupted/inProgress replay |
| Pre/post audit loss | Before zero append; after reconciliation retaining observed IDs |
| Timeout after append | No second write; recovery observes existing submission |

Acceptance requires all requested new REDs reproduced before implementation;
targeted/related suites green; full CI-equivalent local suite green; exact scope,
secret/diff checks; committed/pushed candidate SHA and one review PR. Independent
exact-SHA R3 review and hosted CI remain separate gates. NO author merge.

CI entry is `.github/workflows/ci.yml`: Windows GUI group, separate local-instance
and supervised-command suites, then every remaining `tests/test_*.py` file in its
own process, with A_CONDUCTOR_GPU_PARTICLES=0. It is not merely an approximately
1,036-test orchestration selection. Packaging/live tests are separate evidence.

## Authority Gate Evidence

Verified at the base above, not inferred from old continuity text:

| Frozen gate | Current disk evidence | Disposition |
|---|---|---|
| Named caller/writer | #709 c6684442546 approves operator.v1 and orchestration_dispatcher | Naming cleared |
| Existing Parent ordering | orchestration_dispatcher.py:152-300 only implements worker batches; :202-208 rejects Parent/non-worker path; :240-242 checks worker provider max_concurrency only | No existing Parent serialization scope to extend was found |
| Parent pre-job audit | Design :207-213 and section 8 :442 require an integrator-frozen owner/mapping; worker checkpoints at dispatcher :274-296 require an existing job | Parent mapping not frozen by naming comment |
| Canonical aliases/recovery | Design section 8 :443-444 requires owning-authority decision; #583 hashes exact task text and is not alias/recovery authority | Required mapping/boundary not frozen |
| Public operator admission | operator_protocol.py:28-37 contains status and job actions only; operator_dispatch.py:109-216 routes those existing actions | No accepted Parent action mapping; do not invent a signal tunnel |
| Runtime registration | runtime_activation.py:1175 imports the worker Dispatcher; no Parent registration found in that module | New callable alone cannot prove external registration |

The naming comment does not state a Parent audit owner, alias resolver, interrupted
turn reconciliation rule, or an atomic queue-admission implementation. Those are
explicit integrator decisions in the task's frozen contract, not routine naming
choices for this implementation executor. Current code has no existing Parent
admission+serialization ordering to reuse as described in the assignment.

## Checkpoint

### Approved Amendment And Resumption (2026-11-06)

Approval: https://github.com/aase7en/A-Wiki-Conductor/issues/733#issuecomment-6689258402
approves proposal c6688200474 items A/B/C. This supersedes the original blocked
source allowlist below only for the bounded offline subset. Renewed same-lane
claim: c6690621377. User assigned this resumption executor explicitly.

Exact mutable scope: `src/a_conductor/orchestration_parent.py`,
`tests/test_orchestration_parent.py`, this WO, `.status-orch1-5.md`.
No dispatcher, runtime activation, public operator action, policy, shared
continuity, secret, live queue or other worktree changes. R3 remains binding.

- A: reuse real existing governance jobs and version-checked checkpoints with
  `orch-parent-pre:<signal_id>` / `orch-parent-post:<signal_id>` and canonical
  intent/submission evidence refs. No job creation, worker claim or execution.
  Missing/foreign/terminal/version-conflicting job or unresolved pre-checkpoint
  refuses; post-audit loss retains observed IDs and requires reconciliation.
- B: authenticate via an application-bound Sunday issuer verifier port FIRST;
  exact issuer/caller/device/project/repository binding; absent verifier refuses.
  Only the durable owner resolver proves aliases and canonical task identity
  before constructing DTO/context or hashing. No parsing, new registry or crypto.
  Re-read the same owner mapping before returning; drift refuses.
- C: read-only REPLAY reconciliation using complete receiver evidence plus
  owner-backed exact result/recovery binding. Preserve duplicate precedence and
  interrupted history, additionally refuse inProgress. Pending/terminal proof
  may attach a NO_ACTION observation; never replay a write or followup.

Production operator/verifier registration and all-producer serialization are
explicit LATER GATES in the approval. This module is an unwired application seam,
not a public wrapper or external credential implementation. It has NO queue-add
port, serialization boolean, local lock, or effect callback. ENQUEUE that clears
the offline checks returns ORCH_QUEUE_SERIALIZATION_UNPROVEN. Audit adapter
checkpoint sequencing is exercised against fixture-owned real job storage,
not presented as queue serialization or operational Parent admission proof.
No positive append, crash-after-live-append, cross-device ordering or operational
/5 acceptance can truthfully be certified in this subset. Those original matrix
rows remain later gates, not silently passing fixture certificates.

Recovery: original two untracked docs preserved; no source/test implementation
or commits existed. Fresh fetch pins origin/main and HEAD to the original base;
no remote lane branch or existing PR, no commits ahead of origin/main.
Outstanding delegated executions=NONE in the recovered lane packet.
GLM_OFFLOAD=BLOCKED/RESUMPTION_EXECUTOR_BOUND (explicit replacement assignment
after provider quota interruption); no new provider requests or secrets.
Evidence destination: ignored `runs/WO-P1-733/`; shared CURRENT-WORK/handoff/COLLAB
fold-back stays with integrator. Cleanup=NOT_NEEDED. Independent R3 review and
hosted CI remain integrator gates; no merge.

The original checkpoint below is historical evidence, not the current gate.

### Implementation Checkpoint

Implemented additive unwired ParentAdmission + ParentAudit in the two-file
source/test scope. ParentAdmission authenticates before resolver/evidence reads,
uses owner-proven canonical identity before codec/context/#583 keys, collects
full receiver evidence, keeps duplicate/interruption precedence, refuses active
turns/unknown legacy correlations, checks task/utilization and existing job audit
ownership, and rechecks owner/job versions. REPLAY can only attach an exact
owner-proven pending/terminal result with NO_ACTION; unresolved pre-checkpoints
remain durable and never clear themselves. No queue/effect capability is present.
ParentAudit uses the existing job service and exact pre/post refs/evidence/CAS;
it creates no job, claim, worker or provider operation. Its write methods are
not invoked by inspection and are not serialized queue admission.

RED evidence: missing-module collection error; inert seam 67 failed / 1 control
passed; first adversarial wave 2 failed / 74 passed; boundary wave 4 failed / 76
passed; final strict-projection wave 2 failed / 80 deselected. All reproduced
before their respective repairs. Final targeted + direct dependency selection:
**748 passed in 59.71s**, including **82 Parent tests**. Full Windows CI-equivalent
per-process verification in progress under ignored runs/WO-P1-733/verify_ci.py;
GUI group **500 passed / 2 skipped**. No independent review/hosted CI/full-suite
PASS claimed yet. Shared continuity remains integrator-owned.

### Final Author Verification And Handoff

Source/test freeze: `c982d69f442239c40ccbb42ed0358913c74a9fcf`, normally pushed
to `origin/feat/orch1-external-parent`; PR
https://github.com/aase7en/A-Wiki-Conductor/pull/735 . Follow-up documentation
commit records final verification without changing those source/test blobs.

Full local workflow-equivalent test coverage completed all **218 process groups**
in **1234.94s** with **7139 passed / 24 skipped / 2 failed**. The sole failing
suite was `test_gpu_particle_logo.py`: absent optional OpenGL dependencies caused
the grouped GPU import to clear Image and a direct OpenGL import to fail.
Installed only into ignored lane-local `runs/WO-P1-733/test-deps` (moderngl 5.13.0,
pyopengltk 0.0.4, PyOpenGL 3.1.10, glcontext 3.1.0). No global environment or
production files changed. With that directory plus this lane's src in PYTHONPATH
and `A_CONDUCTOR_GPU_PARTICLES=0`, the identical GPU suite passes **17 / 2 skipped**
(replaces 13 passed / 4 skipped / 2 failed). Cumulative verification therefore
is **7143 passed / 22 skipped / 0 unresolved failures**, not a claim of one
uninterrupted green run. Original failure logs remain intact. All 82 new Parent
tests also passed in the full run; GUI group was **500 passed / 2 skipped**.

Application smoke with explicit lane source binding and lane-local DB returned
`A-CONDUCTOR_SMOKE_OK projects=0 workers=3`; bare `python -m a_conductor` initially
failed because this checkout was not installed in the ambient interpreter.
No package/global-config workaround or source repair was made. Packaging/frozen,
real credential verification, real queue effects and live activation are NOT
claimed. Four-file scope/diff checks passed; worker dispatcher, operator action
set, runtime registration and shared coordination artifacts are byte-unchanged.

New composition reason catalog: ORCH_PARENT_CONFIGURATION_INVALID,
ORCH_PARENT_CALLER_DENIED, ORCH_PARENT_CREDENTIAL_DENIED,
ORCH_PARENT_AUDIT_OWNER_REQUIRED, ORCH_PARENT_IDENTITY_UNRESOLVED,
ORCH_PARENT_BINDING_DRIFT, ORCH_PARENT_TURN_ACTIVE,
ORCH_PARENT_PRIOR_SUBMISSION_UNRESOLVED, ORCH_PARENT_RECOVERY_UNRESOLVED,
ORCH_PARENT_RESULT_ATTACHED and ORCH_SUBMISSION_OBSERVED. Existing codec,
guard, audit/reconciliation/version and serialization reasons are preserved.

Remaining gates: independent exact-SHA R3 review, exact-head hosted CI and GPT
integrator acceptance. Production operator/verifier action mapping and proven
ALL-producer serialization are deliberately deferred by approval, not invented
or certified here. No source outside the exact allowlist; no provider/secret
operation, process kill, other-worktree mutation, force push, merge or issue
closure. No outstanding local execution; source claim frozen for review.
Integrator owns shared CURRENT-WORK/handoff/COLLAB fold-back from this WO and
the final #733 checkpoint. Cleanup NOT_NEEDED; retain lane/evidence for review.

2026-11-06: created requested isolated worktree FIRST after fetch. Live origin/main
was 746a380d979a0d9d112f15371505b307f7c3b271, matching new clean branch HEAD.
Read universal entry, graph, repo contract, continuity top entries, full design,
WO716, coordination/risk contracts, actual receiver/guard/dispatcher source,
operator protocol/dispatch and CI. Read parent #709 and child #716 claims/results;
open ORCH issue search showed #709 only before creating child #733. Worktree
census showed this lane and a separate #551 lane, with no second external-Parent
branch. Historical claims are not treated as current admission.

SAFE_TO_MUTATE_SOURCE=NO. This is a governance bootstrap and blocker checkpoint,
not product RED/GREEN, AUTHOR_VERIFIED, a frozen implementation or a live-runtime
certificate. No source/tests modified, no credentials or provider operations,
no queue/worker effects, and no new authority primitives introduced.

GLM_OFFLOAD=BLOCKED / AUTHORITY_GATE_UNRESOLVED: no READY source task to dispatch;
this already-assigned executor performs bounded deterministic investigation only.
Outstanding delegated execution=NONE. Cleanup=NOT_NEEDED; retain requested lane.

Deterministic verification at unchanged base:

- `python -B -m pytest -q -p no:cacheprovider tests/test_work_order_identity.py tests/test_orchestration.py tests/test_orchestration_receiver.py tests/test_orchestration_guards.py tests/test_orchestration_dispatcher.py tests/test_orchestration_outcome.py`:
  **357 passed in 37.72s**. Includes the new untracked WO identity corpus; not a
  new-admission RED/GREEN or a full local-suite certificate.
- Side-effect-free current-API probe constructed Dispatcher with authority-call
  spies, a valid existing Parent signal and matching separate AdmittedContext:
  **DENIED / EVIDENCE_MISSING, zero authority/executor calls**. This confirms
  the existing worker registration does not provide the requested Parent path.
- Live `git ls-remote origin refs/heads/main` still returns the exact base SHA.
- Tracked `git diff --check` passed; new-file content is inspected separately.

No implementation RED tests or full local suite run because source admission is
blocked. No commit/push/PR/merge or independent-review result is claimed. The
two local checkpoint documents are intentionally retained uncommitted for the
same lane; issue #733 receives the externally durable blocker/evidence summary.

Exact next safe action: GPT integrator reconciles the source-backed gate table
against section 8, freezes the existing queue serialization primitive and Parent
audit/alias/recovery mappings (or explicitly approves a bounded contract amendment
and its scope), then re-runs source admission on this same child WO and worktree.
No new issue/worktree/claim or blind replay is needed. Do not widen the trust
anchor or pretend fixture-owned ports discharge the production gate.
