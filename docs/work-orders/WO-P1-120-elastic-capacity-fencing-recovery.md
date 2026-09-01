# WO-P1-120 — Elastic Capacity Fencing + Recovery Hardening

Date: 2026-08-31
Owner: GPT-5.6 Sol integrator after GLM-5.3 MAX bounded implementation/repair
Status: RELEASED
Repository: `aase7en/A-Wiki-Conductor`
Priority: P2/P3 hardening before production elastic wiring; independent of fixed-worker first canary

## Goal

Harden the merged AHA-6B elastic-capacity seam before any production caller can rely on it: preserve single-store authority, prevent reservation handoff theft, persist every post-provision ambiguity, and make bounded capacity recoverable without age-only automatic release.

## Evidence

GLM `glm53-capacity-hardening-001` confirmed four P3s; GPT integrator independently confirmed the source. Ultra additionally identified R6/R9:
- reservation lifetime has no safe reconcile/release surface for stale failure residue;
- assembler/coordinator single-store composition is not enforced;
- direct `provision_ready()` can bypass scheduler eligibility evidence;
- no regression pins successful `CAPACITY` as consuming `max_extra_workers`;
- a provisioned worker may become observable before its reservation is safely owner-bound (architecture/interleaving risk; requires RED proof before repair);
- full re-observation/reschedule/runner failures after `PROVISIONED_READY` can return recovery without marking the reservation `RECOVERY_REQUIRED`.
## Allowed scope

- `src/a_conductor/worker_lease.py`
- `src/a_conductor/worker_candidate_assembly.py`
- `src/a_conductor/elastic_worker_capacity.py`
- focused worker/elastic tests
- this WO only; shared SSoT remains integrator-owned

## Forbidden scope

- `parallel_ready_execution.py` provider-admission semantics (WO-P1-117)
- provider config/policy/output files (WO-P1-118/119)
- scheduler semantics, UI, live worker/connector/tunnel mutation, A-Wiki mutation
- automatic release based on age alone, background sweeper/thread, second capacity authority
- `PROVISIONED -> RELEASED` shortcut without typed recovery evidence

## RED-first slices

A. Pin successful `CAPACITY` → second owner `LIMIT_WAIT` at `max_extra_workers=1`.
B. Production composition with different authority DBs fails typed; sanctioned builder shares one store.
C. Raw/direct provisioning cannot proceed without accepted eligibility evidence.
D. Every post-`PROVISIONED_READY` observation/reschedule/runner uncertainty persists `RECOVERY_REQUIRED` before returning.
E. Reproduce the publication/mark-provisioned interleaving; repair only if the barrier test proves another owner can steal the new worker.
F. Add typed stale-failure-residue inspection/reconcile using deterministic owner/lease evidence; CAPACITY retirement stays a separate lifecycle decision.
## Acceptance

1. No over-provision across sequential or racing successful capacity handoffs.
2. No competing session can lease a worker while another exact owner holds PROVISIONED/uncertain handoff authority.
3. Owner-scoped re-observation remains exact; generic assembly remains fail-closed.
4. Failure residue can be reconciled only from typed deterministic evidence; fresh/mid-handoff/wrong-owner/CAPACITY records are not age-released.
5. AHA-4B invariants remain: staleness is evidence, not automatic ownership release; no blind retry/rebind.
6. Existing fixed-pool behavior is unchanged when elastic is disabled.
7. Focused/related concurrency+restart regressions, compileall, diff/scope/secret audit pass; exact-SHA independent review + 3-OS CI before merge.

## Concurrency

May run concurrently with WO-P1-117 and WO-P1-119. If the R6 RED test requires changing registry/publication semantics outside the allowed three source files, report `SCOPE_REOPEN_REQUIRED` and stop rather than expanding authority silently.


## Implementation checkpoint — 2026-08-31

- GLM first implementation `962be358f1426086b5b40b113377c82b46d7b614` reproduced and repaired the R6 publication/lease race, enforced scheduler eligibility on direct provisioning, enforced single-store composition, persisted post-provision recovery, and added stale-residue reconciliation.
- GPT integrator found two blockers in that result: bound PROVISIONED residue could release budget without proof the worker disappeared, and a mark-provisioned lease conflict returned recovery while durable reservation remained ACTIVE.
- GLM repair `a1b7ac438364cf41c8804add3e6183f39f8870b0` fixed durable conflict recovery and changed bound stale release to require `worker_decommissioned=True`.
- GPT adversarial review rejected that boolean as decommission authority and found a second bypass: the generic transition matrix still allowed `RECOVERY_REQUIRED -> RELEASED` without reconciliation.
- RED proved both bypasses. Final local repair removes the boolean escape, refuses all bound stale-residue release until a typed runtime/decommission observation seam exists, and forbids generic `RECOVERY_REQUIRED -> RELEASED`. That conclusion was superseded by a later crash-window audit: unbound stale residue is not releasable by age alone because a worker may have been created before its identity was durably bound.
- A final GPT authority audit then proved `release_unstarted()` could retire a successful `CAPACITY` record through the generic transition table. RED reproduced it; `CAPACITY -> RELEASED` is now forbidden until a separate typed retirement lifecycle exists.
- Focused + related worker/elastic/parallel regression after all integrator repairs: `230 passed`; the final positive control proves legitimate ACTIVE `release_unstarted()` still releases and returns budget; compileall and `git diff --check` PASS.
- Remaining gates: source/docs commit + push -> exact-SHA independent review -> 3-OS CI -> merge/post-main verification.
- Later GPT crash-window audit proved stale `ACTIVE + worker_id=None` and `RECOVERY_REQUIRED + worker_id=None` can represent an uncertain post-provision outcome, so owner+age cannot prove runtime absence. RED: two unsafe stale releases failed while explicit `release_unstarted()` positive control passed. Repair returns `PROVISIONING_RUNTIME_ABSENCE_EVIDENCE_REQUIRED` for unbound stale reconcile; known pre-provision cancellation must use explicit `release_unstarted()`. Targeted 3 passed; focused+related 209 passed.
- Exact-head rereview/CI must be regenerated after this repair and after refreshing onto current main.
- Final refresh onto merged WO118A main `0ff914efa2887a0f9c6d330859fa4e49ed921d89` was conflict-free; combined generation/policy/dispatch/lease/elastic/Claude regression = `359 passed`. This is the exact pre-review integration tree.

## Failover review 004 + release-unstarted crash repair — 2026-09-01

GPT-5.6 Sol failover review (used because Ultra003 became quota-blocked; not represented as independent Ultra evidence) found a new P2 on exact head `899d002745b7ae56704c8a6614e7b9a957ab0ba6`: `release_unstarted()` could release `ACTIVE + worker_id=None`, the same durable shape possible after a worker was created but the process died before `mark_provisioned(worker_id)`. Deterministic RED released that row and admitted a second reservation at `max_extra_workers=1` while an external orphan-worker marker still existed.

Repair makes pre-provision provenance durable instead of caller-asserted. New reservations start `PRE_PROVISION`; immediately before invoking the provisioner the coordinator must persist `PROVISIONING`. Only `PRE_PROVISION -> RELEASED` is allowed by `release_unstarted()`. Historical `ACTIVE` is treated as ambiguous legacy residue and cannot release; `PROVISIONING` also cannot release. Both remain capacity-consuming until a future typed runtime-absence/decommission seam proves safe retirement.

Tracked RED initially failed (`DID NOT RAISE`). After repair, the crash-window refusal + safe pre-provision positive control pass; focused fencing file `27 passed`; worker/elastic/candidate focused set `58 passed`; related scheduler/dispatch/lease/elastic set `257 passed`; provider-generation/dispatch/lease/elastic frontier union `312 passed`. Full local suite after repair: `1888 passed / 5 skipped / 2 known environment failures` (`Pillow` unavailable for GPU particle sampling; `OpenGL` unavailable for real WGL framebuffer; the additional skip is local Tk/Tcl availability). No WO120/provider regression. New exact-head independent review + CI remain required after commit.

## Final acceptance / release — 2026-09-01

- Final reviewed source head: `9c3160e4ca4e4baaf9d7cd229a1059f787faac0e`.
- Independent GLM-5.3 MAX rereview005: `PASS`, zero unresolved P0/P1/P2; two P3 operational notes accepted as non-blocking. Task SHA-256: `ef1e85582e4920543bd357e5d077603d332272311a058981fb128cdb84dc808c`; GPT integrator independently revalidated all 9 pinned file hashes.
- Exact-head CI `33463646577`: SUCCESS — Windows full test/packaging/Frozen Setup E2E, macOS smoke, Ubuntu smoke.
- PR #162 merged as `d939a902a0eacae29f417dd1c3581f0f48d4ced0` with expected head locked to `9c3160e...`.
- Post-main CI `33466111330`: SUCCESS on Windows/macOS/Ubuntu, including Windows packaging and Frozen Setup install/uninstall E2E.
- WO-P1-120 is RELEASED. Its worker/elastic seams may now be consumed by WO-P1-118B, but WO118B must establish a fresh exact-main worktree/claim and must not weaken the merged capacity authority.
