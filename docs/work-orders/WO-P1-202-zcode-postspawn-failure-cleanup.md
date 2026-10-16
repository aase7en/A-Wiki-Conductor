# WO-P1-202 — ZCode helper post-spawn failure cleanup / lifecycle determinism

Status: PREPARED / BACKLOG / NO SOURCE MUTATION AUTHORIZED
Owner: GPT-5.6 Sol integrator
Base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-202-zcode-postspawn-cleanup`
Parent evidence: PR #275 independent review; WO193 source repair already merged via PR #268
Risk: R2/R3 process-lifecycle cleanup boundary

## Defect statement

Independent Windows rerun of the GLM WO193 validation campaign exposed a timing-dependent B07 failure.
The helper launches the child and then has several post-spawn failure branches that call `return _fail(...)` directly. The bounded child cleanup/wait logic is only reached through the `_HelperExit` exception handler.

Observed source shape at the merged WO193 base:
- child is created with `subprocess.Popen(...)`;
- child identity persistence happens after spawn;
- `IDENTITY_WRITE_FAILED` can return directly after spawn;
- cleanup/wait of an existing child occurs under `except _HelperExit`.

Therefore a post-spawn failure may let the helper return before child shutdown / receipt observation has deterministically converged. GLM's B07 test passed hosted CI and then failed once during independent Windows rerun before passing 10 focused reruns, demonstrating timing sensitivity.

This behavior predates WO193's byte-integrity source repair and is not a regression from PR #268.

## Why it matters

A-Conductor's supervised execution contract requires deterministic ownership/reaping truth. Failure paths after a child exists must not depend on scheduler timing to establish whether the child was shut down, whether a receipt appeared, or whether a replay is safe.

## Intended future repair

After a fresh source claim, route every post-spawn helper failure through one bounded cleanup path. Prefer reuse of the existing `_HelperExit` mechanism or a single structured finally/cleanup seam rather than duplicating termination logic.

Do not change successful protocol behavior, byte-output semantics, provider/model authority, retry policy, result schema, or process ownership authority.

## RED-first obligations

Before source repair, deterministically reproduce at least:
- identity write failure after confirmed child spawn;
- PID-file write failure after confirmed child spawn;
- child identity unavailable/mismatch after spawn where applicable;
- any other direct `return _fail(...)` reachable after child creation;
- child that remains alive long enough to prove cleanup is actually responsible for termination;
- bounded natural shutdown success;
- shutdown timeout/error remains typed and does not authorize replay;
- no second spawn/send/retry;
- no result publication on failure;
- successful path unchanged.

Use synchronization/barriers rather than sleeps for race proof where practical.

## Scope proposal after release

Preferred source:
- `src/a_conductor/zcode_supervised_helper.py`

Preferred focused tests:
- existing helper lifecycle tests and/or one new focused lifecycle test module;
- repair B07 validation evidence only if useful, without making PR #275 the product-source author.

Any broader file list requires integrator approval.

## External gates

Do not implement from this docs branch.
Do not preempt ZRA-2 Phase B/C critical path.
Do not mutate PR #275 source scope.
Do not merge source repair without exact-SHA independent review + hosted CI.

This work order converts the finding into executable prevention while keeping it off the current critical path.
