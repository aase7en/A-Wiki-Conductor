# WO-P1-581 — Darwin Boot Identity False-Stale Liveness Repair

Issue: #581
Topology: CROSS_REPO
Risk: R3 — process identity, durable execution state, recovery and replay safety
Status: GOVERNANCE BOOTSTRAP ONLY; product/source mutation requires a fresh full gate
Claim ID: WO-P1-581-DARWIN-BOOT-IDENTITY-CROSSREPO-001
Claim owner: GPT integrator / A-Sunday Conductor
Claim record: Issue #581 comment `5981981579`

## 1. Frozen compatibility set

- AUTHORITY_REPO: `aase7en/A-Wiki-Conductor`
- AUTHORITY_REPO main / SHA_AUTH: `100c94b0308ba33101e00929d7016443f3f7331f`
- EXECUTION_REPO: `aase7en/SunDayRemoteMCP`
- EXECUTION_REPO main / SHA_EXEC: `41a566c845c2629f9771becf68175d71cb7d1aaa`
- Topology freeze: both exact SHAs above form one compatibility set. Any member
  head drift invalidates it; re-pin and inspect the changed delta before work.
- Bootstrap lane: authority repo only; worktree
  `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo581-bootstrap`, branch
  `docs/wo-p1-581-darwin-boot-identity`, base `100c94b0308ba33101e00929d7016443f3f7331f`.

## 2. Symptom and failure model

A live delegated execution was durably classified `INTERRUPTED` after the
Darwin `kern.boottime` identity's seconds matched but microseconds differed.
The recorded and sampled values for `exec-murep77o-pa10qmf9` were
`sec=1790547593,usec=491202` and `sec=1790547593,usec=438805`. The durable
observer rejected liveness before PID/process-tree verification. This risks
orphaned work and duplicate replay. Same-boot tuple samples were stable 5/5;
why capture differed remains **TO PROVE**. Do not treat matching seconds alone
as sufficient reboot identity or weaken process identity checks.

Required invariant: identity uncertainty or mismatch alone must not
terminalize an execution while exact process evidence may still match; reconcile
robust reboot evidence with exact process identity before terminalization.

## 3. Scope and claim boundary

### Bootstrap only — mutable now

- `docs/work-orders/WO-P1-581-darwin-boot-identity-liveness.md`
- This governance claim is recorded in the existing Issue #581 thread; this is the
  durable claim mechanism for this bootstrap, not a new lease store.
- No other file, issue, claim store, runtime, process or repository is writable
  in the bootstrap lane.

### Later execution scope — NOT YET MUTABLE

- SunDayRemoteMCP Darwin boot-identity capture, parse, normalization, compare,
  and execution-liveness reconciliation implementation paths identified by
  source audit after claim/worktree binding.
- Their directly relevant deterministic tests for same-boot microsecond
  variance and genuinely different boots.
- Exact path allowlist is pending read-only source mapping and the full
  post-bootstrap mutation gate. No future source/test path is claimed yet.

Current owner for the governance record: GPT integrator / A-Sunday Conductor.
Future source owner must be bound to a separate isolated SunDayRemoteMCP
worktree, branch, exact HEAD, task claim, and explicit file scope after the
post-bootstrap gate. The two repositories share one global WIP budget.

## 4. Ordered execution and acceptance

1. After bootstrap, rerun the complete mutation/WIP/collision gate and bind an
   exact execution-repo worktree/branch/HEAD/scope before any source mutation.
2. Read-only reproduce the recorded-vs-sampled same-boot mismatch against the
   current implementation; minimize to the capture/parse/compare seam.
3. Prove root cause from implementation and deterministic evidence; do not
   accept the Issue hypothesis as root cause.
4. Add RED deterministic regression coverage first for same-boot microsecond
   variance and genuinely different boot identities.
5. Repair canonical Darwin boot identity handling while preserving fail-closed
   process identity checks and robust different-boot detection.
6. Verify focused regression and related liveness/recovery/cancel tests; inspect
   exact diff, UTF-8, secret scan and scope; freeze the resulting exact SHA.
7. Obtain an independent exact-SHA R3 review, then exact-head CI and required
   post-main verification. GPT integrator retains final defect adjudication,
   merge, runtime/release and acceptance authority.
8. Once proven, fold symptom, impact, trigger, root cause, missing invariant,
   fix, regression and future warning into the existing `DEFECT_LESSONS.md`
   authority and retain executable regression/checker coverage.

## 5. Routing and dispatch gates

- Run current A-Audit exactly once for each independently SAFE_READY eligible
  R2/R3 implementation/repair/review task, after deterministic task, claim,
  exact-scope, collision and WIP gates.
- For eligible heavy implementation/repair/review, perform exactly one fresh,
  task-bound `GLM_OFFLOAD_ASSESSMENT`; if GLM-5.3 MAX is selected, require the
  accepted SundayMCP route and fresh fail-closed CoinTH preflight immediately
  before dispatch. No quota or model inference is authority.
- GPT-6.1 Sol is reserved for difficult architecture/root-cause/adjudication or
  a genuinely GLM-blocked fallback. No dispatch or quota request is part of
  this docs-only bootstrap.
- Preserve at most 3 active mutable lanes plus 1 independent review globally;
  borrowed waiting claims require current Issue #537 semantics. Never replay
  RUNNING, UNKNOWN or terminal-unharvested work.

## 6. Bootstrap prohibition and stop rules

This bootstrap authorizes exactly the governance record above. Do not inspect
or mutate SRM source/runtime as part of bootstrap; do not create the SRM
execution worktree until this WO and Issue #581 claim exist and the complete
post-bootstrap gate independently passes. No process operation, cancellation,
dispatch, tests, PR, merge, claim transfer or scope expansion is authorized by
this bootstrap. Any binding mismatch or unproven WIP/collision/ownership fact
means `SAFE_TO_MUTATE = NO` for product/source work.

## 7. Bootstrap verification and checkpoint

- Bootstrap checks: exact one-file allowlist; `git diff --check`; strict UTF-8
  and no replacement characters; added-line secret scan; no source/test/runtime
  changes; exact worktree/branch/base and remote issue/claim pointer.
- Full mutation gate, new exact SRM path map, execution claim, and separate SRM
  worktree binding are mandatory after this bootstrap is accepted.
- Initial compatibility values were re-pinned by the user for this bootstrap;
  verify live remote main heads again before the post-bootstrap execution gate.
