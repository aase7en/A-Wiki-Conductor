# WO-P1-118 — Provider Configuration Generation + Trust/Egress Policy Gate

Date: 2026-08-31
Owner: split — GLM-5.3 MAX (118A implementation), GPT-5.6 Sol integrator (118B architecture/merge)
Status: ACTIVE — WO-P1-118A COMPLETE / MERGED / POST_MAIN_GREEN / RELEASED; WO-P1-118B BLOCKED_ON_WO-P1-120
Repository: `aase7en/A-Wiki-Conductor`
Priority: P1 before automatic live provider dispatch

## Goal

Bind provider health/admission to the exact configuration generation that was observed, and make declared trust/egress metadata an actual fail-closed production policy input before secret resolution or launch.

## Evidence

Ultra R3/R4 were source-confirmed by the integrator:
- endpoint/profile rows overwrite independently and current observations bind only `provider_id`, not a configuration generation;
- changing endpoint/model/credential-reference/trust can therefore leave an older health observation apparently usable;
- `trust_class` / `egress_boundary` occur in configuration and tests, but no production `src/` policy consumer was found outside the configuration/storage boundary.

Classification: `EXTEND` existing provider configuration/observation/admission authority. Do not create another provider registry, secret store, quota ledger or router.
## Expected scope

- `src/a_conductor/provider_configuration.py`
- `src/a_conductor/provider_config_store.py`
- `src/a_conductor/provider_runtime_assembly.py`
- one bounded additive policy evaluator/decision type only if RED proves no accepted seam exists
- focused provider configuration/runtime tests

## Acceptance direction

1. Endpoint/provider saves are versioned or CAS-protected so stale editor/probe completion cannot authorize a newer configuration.
2. Provider observations carry and validate exact configuration generation; mismatched/stale generation is unavailable, never ready.
3. Admission and launch revalidate enabled/config generation before secret resolution/use.
4. Actual task trust/egress policy denial occurs before credential access, provider launch and elastic expansion.
5. Missing/unknown policy or quota evidence fails closed with typed reasons.
6. No endpoint health for one route authorizes another route/proxy/model implicitly.
7. Installed DB migration preserves existing user provider state and old rows become conservative/unknown until re-observed.

## Ordering

Do not implement concurrently with WO-P1-117 because both own `provider_config_store.py`. Begin only after WO-P1-117 releases that file and its admission-lifetime contract is stable. May overlap later UI read-model work if central provider store files are read-only to the UI lane.
## Integrator shaping checkpoint — 2026-08-31

Source inspection after WO-P1-117 merged proved the original WO spans two ownership seams and must be executed in two bounded slices rather than expanding scope silently.

### WO-P1-118A — READY / disjoint from PR #162

Allowed source scope remains provider-local only: `provider_configuration.py`, `provider_config_store.py`, `provider_runtime_assembly.py`, optional additive `provider_policy.py`, and focused provider tests.

118A owns:
- store-owned provider/endpoint generations with CAS on updates;
- endpoint update atomically invalidating every provider generation that references it;
- observation generation provenance and conservative migration of legacy observation rows;
- provider resolver/readiness rejecting generation mismatch before secret resolution;
- provider-admission persistence/revalidation seam for configuration generation, with backward-compatible caller wiring deferred to 118B;
- a pure deterministic trust/egress evaluator consuming task-contract security vocabulary only; no scheduler/lease/elastic mutation.

### WO-P1-118B — BLOCKED on PR #162

The accepted task authority already exists in `task-contract/v1`: `privacy_class` (`PUBLIC/INTERNAL/SENSITIVE/SECRET`), `network_policy` (`DENIED/ALLOWLISTED/INHERIT`), `network_allowlist`, and `secret_access`.

Actual pre-elastic enforcement cannot be completed inside the original provider-only scope: `ParallelReadyNodeContract` / `assemble_parallel_ready_tasks()` currently materialize provider execution and are also in WO-P1-120 / PR #162 ownership. Therefore 118B begins only after #162 merges and exact scope is re-gated.

118B must wire the accepted 118A policy decision into the existing scheduler/parallel/worker-candidate execution path so denial occurs before provider admission, worker lease, elastic expansion, credential resolution, or process launch. It must reuse `NodeEligibility`/existing dispatch gates rather than create a second scheduler or router.

### Deterministic RED already reproduced

With persisted provider state, changing the endpoint and credential reference while retaining the old observation produced `STALE_OBSERVATION_STILL_READY=True`. This is the generation-binding RED for 118A. No live provider/credential was used.

### Ordering

`WO-P1-117` is merged and its post-main CI is green. 118A may proceed now. 118B remains blocked until WO-P1-120 / PR #162 releases `worker_candidate_assembly.py` and related capacity seams.

## Integrator repair checkpoint — 2026-08-31

GLM implementation commit `438c0a7ca2368888d35098e3f98fd9502f6f9be8` was independently source-reviewed before acceptance. The reported 51 focused / 166 related tests were not treated as authority.

Deterministic integrator fault injection found two release-blocking classes:

1. **Generation integrity rollback / coercion:** repeated `initialize()` rewrote stored generation `0` to `1`; a generation-1 stale observation became READY again after a generation-2 profile was corrupted to zero. Text generations leaked raw `ValueError`, float `1.5` was coerced through `int()`, and `2^63-1 + 1` became SQLite REAL.
2. **Policy metadata/route mismatch:** `LOCAL_MACHINE` / `NO_EGRESS` trusted the declared boundary without checking a supplied endpoint; a SECRET + network-DENIED task was allowed when the profile claimed local egress but the endpoint was external HTTPS.

A separate CAS hole was also reproduced: supplying `expected_generation=1` after the provider/endpoint row disappeared silently recreated generation 1 instead of failing stale.
Repair stays inside the accepted 118A authority:
- legacy `NULL -> 1` migration occurs only in the transaction where the generation column is first added; later corruption is never auto-healed;
- stored generations are exact SQLite integers in `1..2^63-1`, with typed `PROVIDER_GENERATION_INVALID` / `PROVIDER_GENERATION_EXHAUSTED`; no numeric coercion;
- expected-generation updates cannot recreate a missing row and every CAS update verifies `rowcount == 1`;
- endpoint fan-out validates and bounds every referencing provider generation before any mutation, then advances endpoint/providers atomically;
- `LOCAL_MACHINE` / `NO_EGRESS` with a supplied non-loopback endpoint fails `PROVIDER_EGRESS_ENDPOINT_MISMATCH`; explicit loopback and endpoint-less local seams retain intended eligibility.

Verification after repair:
- generation-integrity RED set: 7 passed after initially reproducing all defects;
- provider policy: 12 passed;
- full 118A focused suite: 61 passed;
- provider/admission/parallel/graph/lease related suite: 191 passed;
- no live provider, credential, installed control DB, Worker or tunnel was touched.

**118A is not overall WO118 completion.** Production callers still omit `expected_configuration_generation`, `is_provider_ready(... expected_generation=...)`, and `evaluate_provider_policy()` has no production caller. Resolver -> credential/launch TOCTOU and pre-elastic enforcement remain binding WO118B acceptance work after WO120 releases the shared candidate/elastic seam.

Status: **WO-P1-118A INTEGRATOR_REPAIRED / REVIEW_PENDING; WO-P1-118B BLOCKED_ON_WO-P1-120.**

## Integrator trust/egress repair checkpoint — 2026-08-31

A second GPT adversarial pass after the first PR #165 head found a real policy-classification downgrade: `TRUSTED_THIRD_PARTY` or `LOCAL` combined with `EXTERNAL_FIRST_PARTY` received first-party SENSITIVE treatment because `trust_class` only denied `UNKNOWN`.

RED: two unsafe trust classes returned `POLICY_ALLOWED_EXTERNAL_EGRESS`; the `FIRST_PARTY + EXTERNAL_FIRST_PARTY` positive control already passed.

Repair: `EXTERNAL_FIRST_PARTY` now requires `ProviderTrustClass.FIRST_PARTY`; otherwise policy fails closed with `PROVIDER_TRUST_EGRESS_MISMATCH`. Conservative `EXTERNAL_THIRD_PARTY` behavior remains unchanged, and explicit loopback local/no-egress paths remain eligible.

Verification after repair: targeted `3 passed`; full policy `15 passed`; broader provider/store/runtime/parallel/graph/lease/elastic/Claude supervised stack `254 passed`. The previously generated `wo118a-independent-review-001` packet for head `036acf29...` is superseded and must not be used.

## Integrator review-002 rejection + repair checkpoint — 2026-08-31

The `wo118a-independent-review-002` reviewer returned `PASS`, but integrator validation rejected that verdict after reproducing two uncovered generation-authority defects on exact reviewed HEAD `729c3133a2c9281fe768793756099c21a2edd933`.

1. **Endpoint insert fan-out gap:** a provider and generation-1 observation could exist while its referenced endpoint row was absent. Inserting that endpoint committed generation 1 without advancing the referencing provider generation, so the old observation became READY for a newly materialized route.
2. **Endpoint generation decode gap:** `load_provider_snapshot()` and `get_endpoint()` consumed endpoint route data without validating the persisted endpoint generation. Raw durable corruption (`generation=0`) plus a changed route therefore resolved the new route together with the old generation-1 observation.

RED evidence: endpoint-insert fan-out regressions = `3 failed`; corrupt endpoint resolver regression = `1 failed`. Existing focused/related suites remained green, proving a coverage gap rather than an unrelated regression.

Repair remains inside WO118A store authority: endpoint insert now pre-validates every referencing provider generation and atomically advances those provider generations in the same transaction; endpoint reads/snapshots validate persisted endpoint generation before returning route authority. Non-insert fixtures that require generation 1 use canonical `endpoint -> provider -> observation` setup rather than weakening the new invariant.

Post-repair evidence: focused WO118A = `68 passed`; dispatch/lease related = `179 passed`; provider/harness/supervised = `111 passed`; combined frontier regression including elastic/candidate = `305 passed`. Deterministic raw-SQL reproduction confirms endpoint insert produces provider gen2 and drops gen1 readiness; corrupt endpoint generation makes resolver return unavailable and direct endpoint read fail typed `PROVIDER_GENERATION_INVALID`.

Status: **WO-P1-118A REPAIRED / EXACT-HEAD REREVIEW REQUIRED.** The old reviewer `PASS` is not merge authority. WO118B remains pending and is not claimed complete.

Full local verification after the review-002 repair: `1843 passed, 5 skipped, 2 failed` in 226.46s. The two failures are the pre-existing local GPU dependency gaps outside WO118A (`Pillow` unavailable for particle sampling; `OpenGL` module unavailable for real WGL framebuffer test). No provider/configuration failure appeared in the full suite.

## Ultra review-003 repair checkpoint — 2026-08-31

Ultra independently returned `CHANGES_REQUIRED` on exact head `2812222590ce3001bdbee3b4bf039f999fdb1626` with two P2 findings. It also confirmed the prior endpoint-insert fan-out and corrupt-endpoint-generation repairs.

1. **Policy endpoint identity binding:** `evaluate_provider_policy()` accepted an unrelated endpoint object and could authorize borrowed loopback/allowlisted routes. RED reproduced both unsafe allows. Repair denies supplied `endpoint.endpoint_ref != profile.endpoint_ref` as `PROVIDER_ENDPOINT_REF_MISMATCH` before trust/egress classification; endpoint-less local behavior remains intentionally supported.
2. **Retry-safe legacy migration:** generation-column `ALTER TABLE` statements could persist before a faulted first backfill, leaving NULL generations that ordinary retry could not recover. RED fault-injected the provider-generation UPDATE and proved columns survived. Repair starts an explicit SQLite `BEGIN IMMEDIATE` before schema introspection/conditional ALTER/backfill so DDL + first backfill roll back as one retryable authority transition.

RED before repair: `2 failed`. Targeted after repair: `2 passed`; full provider configuration/store/policy/runtime focused suite: `70 passed`; related provider/harness/parallel/graph/lease/candidate/elastic-present suite: `196 passed`.

`DEFECT_LESSONS.md` is intentionally not mutated on this PR head while WO121 owns lesson #37 and WO120 still carries a competing historical #37. The accepted findings are durably recorded here; final integrated defect-memory numbering will be reconciled after WO121 merges rather than creating another shared-file collision.

Status: **WO-P1-118A ULTRA-003 REPAIRED / NEW EXACT-HEAD REREVIEW REQUIRED.** WO118B remains pending.
## WO-P1-118A final release checkpoint — 2026-09-01

- Ultra rereview004 returned `PASS` with P0/P1/P2 = `0` on exact head `2bfcdabbb88058784be52cb990ce927b89cd376f`; the separate Spec-axis P3 raw-getter consistency note is non-blocking and has no production caller.
- The reviewer independently closed review003 F1/F2: borrowed endpoint-reference decisions denied across 960 combinations, both migration-backfill fault positions rolled back schema/data and retried successfully, modern NULL/zero/text/REAL/BLOB generations remained fail-closed, and earlier fan-out/CAS/observation/admission protections held.
- Reviewer-fresh verification: focused `70 passed`, related `213 passed`, independent generation probe 25 summarized cases including 12 CAS races, compile/diff/scope/secret-pattern gates PASS. Task SHA-256: `c54264a6041cdf2d2c69a4a605a54fcd536759da5ef7eacefaa813cb0e895238`; ignored local result `runs/wo118a-independent-review-004/result.md` SHA-256: `e7b530ff6eab146230266968af7f5aca01f9790625cceb14a9c816a459f5cf0c`.
- Exact-head CI `33405254844` passed Windows/Ubuntu/macOS. PR #165 merged as `0ff914efa2887a0f9c6d330859fa4e49ed921d89`; exact post-main CI `33417911998` passed all three OS jobs, including Windows packaging, Portable smoke and Frozen Setup install/uninstall E2E.
- **WO-P1-118A is COMPLETE / MERGED / POST_MAIN_GREEN / RELEASED.** This does not complete WO118: WO118B policy/generation enforcement before admission, lease, elastic expansion, credential access and launch remains blocked on accepted WO-P1-120.

## WO-P1-118B integrator + Ultra repair checkpoint ? 2026-09-01

WO120 is released, so 118B was claimed in isolated worktree `A:\GitHub\A-Wiki-Conductor-wo118b-enforcement`. GLM pre-implementation review returned `RED_PLAN_READY` with no P0/P1/P2; Ultra adversarial review returned `CHANGES_REQUIRED` and identified durable-authority, dedup, admission-evidence, TOCTOU and mixed-node elastic gaps. GPT MAX owns the repair while Ultra is unavailable by usage limit.

Accepted repairs:
- `ProviderExecutionRequirement` is derived from exact Task Contract bytes, exact security vocabulary, expected provider generation and canonical provider SQLite identity; production paths reject missing requirements.
- operation identity and Claude supervised runtime profile include requirement/generation identity, preventing cross-generation/security dedup reuse.
- production Claude assembly rejects a requirement bound to a different provider DB and rejects legacy caller-only security/generation wiring.
- provider admission consumers validate exact provider/execution/batch/status/expiry/generation and exact release evidence. ACTIVE generation-bound admission fences public provider/endpoint mutation.
- elastic production reserves provider admission before provisioning and reuses it through lease/runner, so configuration cannot change in the provision->lease gap; uncertainty retains fail-closed authority.
- mixed scheduler output chooses an eligible CAPACITY/NO_WORKERS sibling for one bounded expansion even when another sibling is policy-denied; no second scheduler/provider router was added.
- Claude credential boundary revalidates before secret resolution and again after secret resolution immediately before native launch; the resolved base URL is pinned to the authorized snapshot.

Deterministic evidence so far: provider execution authority 6 tests including store mismatch/dedup identity; elastic fencing 31 passed including mutation-during-provision and mixed-sibling starvation; provider/parallel/Claude boundary matrix 144 passed; expanded 16-file frontier matrix 301 passed; compileall and `git diff --check` pass. A stale full-suite started before the final canonical-DB repair was explicitly terminated and is not evidence. Final current-code full-suite, current-main reconciliation, exact-head independent rereview, CI and post-main verification remain required.

Status: **WO-P1-118B INTEGRATOR_REPAIRED / EXACT_HEAD_REVIEW_PENDING ? DO NOT MERGE YET.**

## WO-P1-118B current-main verification checkpoint ? 2026-09-01

Implementation was checkpointed, then cleanly rebased onto post-WO123-closeout main `b1024b354a6fc45faad618a055a55aef3d9954f5`; the source diff remained the same 18 claimed files with no merge conflict. Rebased implementation commit before this evidence-only checkpoint: `f3b91bd`.

Current-main verification after rebase:
- impacted provider/parallel/elastic/Claude matrix: `211 passed`;
- full repository: `1911 passed, 5 skipped, 2 failed`; both failures are the same local GPU dependency gaps outside WO118B (`Pillow is required for GPU particle sampling`, `No module named OpenGL`);
- `python -m compileall -q src/a_conductor`: PASS;
- `git diff --check`: PASS;
- strict UTF-8 decode of all 18 changed files: PASS;
- refined added-line credential/private-key scan: 0 hits;
- merge/rebase onto current main: conflict-free.

The binding Loop Engineer `detect_changes()` step was attempted with GitNexus but A-Conductor has no GitNexus index yet (`Repository "." not found`); no index was created inside the release worktree. Existing deterministic diff/impact matrices remain the evidence for this slice, and indexing A-Conductor is a separate tooling hardening item rather than permission to mutate the release lane.

Next gates: freeze final SHA, push/open PR, remote diff audit, fresh exact-head GLM independent rereview (Ultra unavailable by 5h limit), 3-OS CI, integrator re-audit, merge, post-main verify, then SSoT closeout.
