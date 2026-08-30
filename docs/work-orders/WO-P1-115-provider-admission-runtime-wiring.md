# WO-P1-115 — Production Provider Admission + Runtime Wiring (AHA-6A.1)

Date: 2026-08-30
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / CLAIMED / IMPLEMENTED / REVIEW_GATE
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-provider-admission`
Branch: `feat/wo-p1-115-provider-admission-runtime`
Base: `origin/main@5a66e100b2f48c061b0677f0b2f39d1b9f23e80b`
Parent: Sunday Family Multi-Model Agent Harness Accelerator

## Priority / why now

`WO-P1-096` remains the higher P0 release blocker, but its remaining live tunnel-client v0.0.13 TTL soak needs a spare Tunnel ID or explicit maintenance authorization for a specific live Worker. All five current Tunnel IDs are occupied, so this work order does not disrupt live connectors.

AHA-6A.1 is the next safe accelerator slice before AHA-6B elastic capacity or AHA-7 UI. It closes infrastructure gaps that still force automatic provider execution to fail closed.

## Reuse-before-build verdict

Classification: `REUSE + WRAP + EXTEND`.

Reuse existing authorities:
- `SQLiteProviderConfigStore` for provider configuration, endpoint and observation persistence;
- `ProviderObservation` / `QuotaSnapshot` freshness and quota semantics;
- WO-P1-114 A-Wiki Drive environment resolver + supervised Claude backend assembly;
- AHA-6 parallel READY execution and its typed capacity-wait outcome;
- A-Wiki work-order/claim and `secrets-global-env` protocols.

Do not create:
- a second provider registry/database, scheduler, job store, retry loop, lease system, quota model or secret vault;
- an independent process-local semaphore as provider-global authority;
- provider-name-based lifecycle rules;
- a Z.ai-specific quota call for a route that is not proven to be Z.ai;
- user-level Claude/CCR configuration mutation inside this repository task.

Architecture decision at plan gate:
- generic `job_store.py` has atomic transactions but no provider identity and remains the job lifecycle authority;
- provider-global capacity therefore extends `SQLiteProviderConfigStore` in the same control DB with atomic admission records rather than broadening generic job semantics or creating a second store;
- existing Drive resolution is sufficient through explicit env/repo linkage/home fallback; no new hard-coded Drive path configuration is required.

## Current production evidence — redacted / read-only

- Installed `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` exists but contains zero `provider_*` tables; safe bootstrap is required before production provider state can exist.
- The current A-Wiki Drive resolver can find an approved private layer without hard-coded production paths; machine evidence confirms existing repo/home resolver signals.
- Current Claude CLI route points at a loopback gateway, but that gateway is not listening at this checkpoint.
- Current local router configuration exposes no active GLM/CoinTH provider or virtual GLM profile. Historical GLM proxy readiness must therefore not be treated as current readiness.
- Direct Z.ai history reached the provider but returned HTTP 429 / insufficient package; live dispatch remains fail closed.
- No secret values were printed, copied or persisted during this preflight.

## Repository / lane safety contract

Current preclaim evidence: GitHub open PRs `0`; A-Wiki live claims `0`; no WO-P1-115 branch/worktree collision; North Star is clean and its unique file scope does not overlap this provider-admission slice.

Allowed implementation scope:
- `src/a_conductor/provider_config_store.py`;
- `src/a_conductor/provider_runtime_assembly.py`;
- `src/a_conductor/parallel_ready_execution.py`;
- at most one additive provider quota/probe adapter module if provider identity makes the adapter authoritative;
- focused tests for those seams;
- this work order plus bounded `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, accelerator plan, `docs/agent-collab/AGENT_TASKS.md`, and `CAPABILITY_MATRIX.md` checkpoints.

Forbidden without explicit scope reopen:
- North Star-owned runtime/UI/GPU files;
- connector/tunnel/release files or live Worker/process/port mutation;
- A-Wiki repository mutation;
- user-level Claude/CCR/profile mutation;
- plaintext secret values or secret-bearing diagnostics;
- unrelated scheduler/job/worker-lease semantics.

## Acceptance criteria

1. Opening the shared control DB safely bootstraps provider tables without modifying or dropping existing Control Center tables/data.
2. `SQLiteProviderConfigStore` provides atomic provider admission/reservation in the same DB/store authority, enforcing `ProviderConfiguration.max_concurrency` across independent concurrent batches/processes.
3. Reservations carry exact provider + execution/batch identity, bounded expiry/reconciliation metadata, and cannot be double-released or silently stolen.
4. Known completion releases capacity; uncertain runner/transport state does not blindly free capacity before reconciliation/expiry.
5. AHA-6 production execution consumes the atomic admission authority; two concurrent same-provider batches at max concurrency 1 prove exactly one runner starts and the other receives typed provider-capacity wait.
6. Existing batch-local `provider_inflight` remains only a compatible deterministic seam where appropriate; it cannot be mistaken for provider-global authority.
7. Production runtime assembly initializes/reads provider state through existing stores and uses the accepted A-Wiki Drive resolver without adding a machine-specific path setting.
8. Quota probing is provider-matched: unsupported/unknown gateway/provider routes remain typed fail-closed; no endpoint is inferred from model name alone.
9. If an explicit supported Z.ai route is configured, a bounded adapter may normalize authoritative quota evidence into the existing full five-hour tuple. Otherwise this criterion remains fail-closed rather than fabricated.
10. Installed-style preflight with an empty provider schema proves safe bootstrap + no automatic provider execution until profile/endpoint/fresh observation/quota/admission gates are all satisfied.
11. No second concurrency, quota, provider, secret, scheduler or retry authority is introduced.
12. Focused + related regression, compileall, diff/scope/secret/encoding audit pass; concurrency/adversarial E2E passes.
13. Independent exact-SHA review precedes PR; GLM-5.3 MAX is eligible for bounded read-only security/concurrency review after the snapshot is pinned.
14. Exact-head Windows/Ubuntu/macOS CI including Frozen Setup E2E passes before merge; post-main CI is verified.

## Multi-agent lane rule

Official Z.ai GLM-5.3 evidence was refreshed on 2026-08-30: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, and Z.ai Code Bench Max `34.5%`. Z.ai also notes these coding pipelines still require meaningful human-in-the-loop work. GPT retains architecture, security/concurrency adjudication and merge authority.

GLM/future agents receive only bounded task packets. Read-only review writes to ignored `runs/<task-id>/result.json`; human fallback relays only the task pointer, never the result. GPT/Conductor validates task/model/HEAD/hashes and folds accepted findings back into tracked SSoT.

## RED-first slices

A. Safe provider-table bootstrap on an existing non-provider control DB.
B. Atomic provider admission acquire/release/expiry/reconcile tests in the existing provider store.
C. Cross-batch concurrency race test (`max_concurrency=1`) before parallel executor integration.
D. Integrate AHA-6 with reservation authority; preserve typed wait/no-replay semantics.
E. Installed-style runtime assembly + Drive-resolution fail-closed tests.
F. Provider-matched quota adapter/probe contract; unsupported current local gateway remains unavailable rather than guessed.
G. Broad regression/adversarial E2E → exact-SHA independent review → repair if valid → PR/CI/re-audit/merge.

Historical plan-gate instruction (completed): claim/SSoT was committed before RED slice A-B; current authority is the implementation checkpoint below.

## Implementation checkpoint — exact source snapshot

Implementation commit: `4e66cdeefbc31bd0513c8bd32ff322dc6230641b` (pushed).

Deterministic evidence:
- focused provider-store/runtime/parallel/quota suite: `59 passed`;
- related provider/harness/lease/graph/execution regression: `253 passed`;
- full local suite: `1750 passed, 4 skipped, 2 known GPU/Pillow/OpenGL environment failures` outside this work order;
- compileall + `git diff --check` + bounded source/scope/secret/encoding audit: PASS;
- installed-control-DB copy E2E: existing tables `12`, provider tables added `4`, live DB hash unchanged;
- independent-process admission E2E: `ADMITTED,CAPACITY_WAIT` at `max_concurrency=1`.

Trust-boundary repairs found during GPT adversarial review:
- admission backend exceptions/malformed/future result kinds are isolated per task and cannot erase sibling batch evidence;
- unsafe reason codes and invalid admission records fail closed before lease/runner;
- active admission timestamps are decoded/validated before expiry/capacity reconciliation; corrupt durable time cannot masquerade as capacity wait;
- Z.ai quota transport forbids redirects, accepts only exact supported HTTPS host/path/default port, rejects non-finite numeric evidence, and requires a complete reset-bearing five-hour tuple.

Current production readiness remains fail-closed. Official Z.ai tooling confirms the quota endpoint and raw-token auth surface, while upstream issue #20 states the current quota-limit response lacks reset time. The current local loopback GLM route is also not proven active. No full quota tuple means no automatic dispatch.

Next gate: commit this SSoT/review-prep checkpoint, then generate and re-read `runs/wo115-glm-review-001/task.md` from the resulting exact HEAD. GLM-5.3 MAX owns read-only adversarial security/concurrency review only; result goes to `runs/wo115-glm-review-001/result.json`. GPT validates exact identity/hashes and owns any repair, PR, CI and merge action.
