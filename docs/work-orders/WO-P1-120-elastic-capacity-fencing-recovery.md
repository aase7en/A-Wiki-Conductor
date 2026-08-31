# WO-P1-120 — Elastic Capacity Fencing + Recovery Hardening

Date: 2026-08-31
Owner: GPT-5.6 Sol integrator after GLM-5.3 MAX bounded implementation/repair
Status: IMPLEMENTED_LOCAL / REVIEW_PREP
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
