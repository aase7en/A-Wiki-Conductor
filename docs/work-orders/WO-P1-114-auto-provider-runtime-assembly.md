# WO-P1-114 — Automatic Provider Runtime Assembly (AHA-6A)

Date: 2026-08-30
Owner: GPT-5.6 Sol integrator
Status: ACTIVE / CLAIMED / PLAN_GATE
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-auto-provider-dispatch`
Branch: `feat/wo-p1-114-auto-provider-dispatch`
Base: `origin/main@9d65564eeea4c5085b365de158340285e8c9c657`
Parent: Sunday Family Multi-Model Agent Harness Accelerator

## Priority / why now

`WO-P1-096` remains the highest P0 release gate, but its final live v0.0.13 TTL soak needs a spare Tunnel ID or explicit maintenance authorization for a specific live Worker. That authorization is not inferred from a general roadmap instruction.

While P0 is externally blocked, this slice closes the next highest user-priority gap: the accepted AHA-1..AHA-6 contracts still require a human one-way prompt because provider configuration, secret resolution and observed quota are not assembled into production execution.

AHA-7 UI and AHA-6B elastic capacity do not solve that core message-bus gap, so AHA-6A precedes them.

## Reuse-before-build verdict

Classification: `REUSE + WRAP + EXTEND`.

Reuse:
- A-Wiki `docs/protocols/secrets-global-env.md` as the private Drive secret SSoT/resolution contract;
- existing `SQLiteProviderConfigStore`, `ProviderConfiguration`, `ProviderEndpointConfig`, `ProviderObservation`, `QuotaSnapshot`;
- existing `EnvironmentReferenceResolver` and `ClaudeCodeProviderResolver` protocols;
- existing supervised Claude runner/job backend/job assembly;
- AHA-6 `require_quota` fail-closed semantics and durable graph/job execution authority.

Do not create:
- a second provider registry/database, scheduler, task store, retry loop, lease system or secret vault;
- provider-name-based lifecycle rules;
- a subprocess-based secret fetch path;
- a UI or North-Star duplicate in this slice.

A-Wiki remote main was checked at `71406f8a25079f364face422012e4bdeac5f483e`; its local checkout is dirty/stale and remains read-only.

## Repository / lane safety contract

Allowed implementation scope:
- new `src/a_conductor/provider_runtime_assembly.py`;
- new `src/a_conductor/awiki_environment_resolver.py`;
- new focused tests for those seams;
- this work order;
- bounded checkpoints in `docs/plans/2026-08-28-sunday-family-agent-harness-accelerator.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/agent-collab/AGENT_TASKS.md`, `docs/agent-collab/CAPABILITY_MATRIX.md`.

Forbidden without an explicit scope reopen:
- `graph/scheduler.py`, `graph/dispatch.py`, worker lease/job stores or retry/state machines;
- desktop UI, connector/tunnel/release files, North Star branch-owned files;
- A-Wiki mutation;
- live connector process/port changes;
- plaintext credentials, copied `.env` values, secret-bearing diagnostics;
- provider-global semaphore/store invented inside this slice;
- live GLM/CoinTH dispatch before secret + health + required quota gates are proven.

Current ownership gate: open PRs `0`; A-Wiki live claims `0`; North Star worktree clean and non-overlapping; root checkout remains protected/dirty.

## Acceptance criteria

1. A production `ClaudeCodeProviderResolver` reads profile + endpoint + latest observation from the existing control SQLite database and fails closed on missing/mismatched records.
2. A concrete `EnvironmentReferenceResolver` resolves only approved opaque references. Endpoint refs resolve through existing provider endpoint configuration; secret refs map to approved A-Wiki Drive/env key references. Arbitrary paths/shell syntax are rejected.
3. A-Wiki secret loading follows the current Drive contract natively in Python: explicit drive-root override/configuration first, `secrets/global.env` then optional repo env, no shell evaluation, no subprocess, no value logging.
4. Secret values exist only at the supervised execution boundary and remain redacted from result/evidence/log output.
5. Production assembly reuses `build_supervised_claude_job_backend`; it does not fork Claude/provider lifecycle logic.
6. Automatic-dispatch preflight requires fresh `AVAILABLE` provider evidence. When quota is required, the existing five-field quota completeness rule is reused; missing/incomplete/non-positive quota prevents execution.
7. Provider identity, endpoint identity and task/job identity drift fail closed before provider execution.
8. Fake/injected E2E proves: same control DB -> provider state -> reference resolution -> supervised Claude backend -> bounded result, with zero human result copy-back and zero real secret/network dependency.
9. No new scheduler/provider store/retry/lease/concurrency authority is introduced.
10. Focused + related regressions, compileall, diff/scope/secret/encoding audit pass; independent exact-SHA review precedes PR.
11. Exact-head Windows/Ubuntu/macOS CI including Frozen Setup E2E passes before merge; post-main CI is verified.

## GLM / future-agent lane rule

Fresh official Z.ai GLM-5.3 evidence (2026-08-14) supports bounded repository implementation/review: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, Z.ai Code Bench Max `34.5%`. GPT retains architecture, trust-boundary, integration and merge authority.

Until this work order assembles automatic provider execution, GLM uses only the existing one-way ignored `runs/` bridge: human relays one short task pointer; GLM writes result JSON; GPT reads it directly. External agents never edit tracked SSoT unless an explicit docs-only lane assigns that exact file.

## RED-first slices

A. SQLite-backed provider-state resolver identity/fail-closed tests.
B. Native A-Wiki environment/reference resolver parsing, precedence, path/ref validation and secret non-disclosure tests.
C. Production builder that composes accepted provider store/resolvers with the existing supervised Claude backend.
D. Required-quota preflight adapter/reuse test; no execution when evidence is incomplete/stale/exhausted.
E. Fake supervised vertical E2E plus adversarial secret/identity tests.
F. Independent GLM-5.3 MAX exact-SHA review through durable task/result files; bounded repair if findings are valid.
G. Broad regression/audit -> PR -> exact-head CI -> re-audit -> merge -> post-main proof.

## Claim checkpoint — 2026-08-30

- Isolated worktree created clean from `origin/main@9d65564eeea4c5085b365de158340285e8c9c657`.
- Branch `feat/wo-p1-114-auto-provider-dispatch`; remote `https://github.com/aase7en/A-Wiki-Conductor.git`.
- GitHub open PRs `0`; A-Wiki local claim store `0`; no WO-P1-114 branch/worktree collision.
- Preserved North Star branch `feat/north-star-runtime-sunday-family` is clean; its unique files do not overlap this work order's initial source scope.
- P0 WO-P1-096 remains blocked only on an authorized live v0.0.13 TTL soak; this work order does not touch live connectors.
- Upstream `grill-with-docs` was refreshed 2026-08-30; explicit plan/task/claim gate remains mandatory because current upstream grilling can transition toward implementation without creating this repository's safety authority.

Next safe action: persist this claim/roadmap checkpoint, then write RED tests for slices A-B before source implementation.
## Scope reopen — defect memory

During RED adversarial testing, malformed UTF-8 in A-Wiki `.drive-path` escaped as a raw `UnicodeDecodeError`. This is reusable fail-closed configuration-boundary knowledge, so this work order explicitly adds one bounded `DEFECT_LESSONS.md` entry to its documentation scope. No other hotspot/source scope is reopened.

Evidence after repair:
- focused WO-P1-114: `15 passed`;
- related provider/harness/AHA-6 regression: `211 passed`;
- full local suite: `1714 passed, 5 skipped, 2 known GPU dependency failures`;
- the two failures are unchanged local environment issues in `tests/test_gpu_particle_logo.py` (Pillow import coupling and missing `OpenGL`), outside this work order.

Automatic provider dispatch is **not** yet declared production-ready: the installed desktop process does not currently expose `A_WIKI_DRIVE_PATH`, and AHA-6 cross-batch provider admission still requires serialized admission or an existing atomic provider-capacity authority. WO-P1-114 supplies the provider DB/reference/supervised backend assembly only; those remaining gates must stay explicit.

## GPT trust-boundary review repair — 2026-08-30

Before external review, GPT found and RED-reproduced two authority-boundary defects:
- invalid explicit `A_WIKI_DRIVE_PATH` could fall through to another locator;
- corrupted persisted provider data could escape as raw typed-decoding `ValueError`.

Repairs are bounded to the two new WO-P1-114 source modules. Explicit override now fails closed, and corrupt provider/endpoint state resolves as unavailable. Focused suite is `17 passed`; related provider/harness/AHA-6 regression is `224 passed`. `DEFECT_LESSONS.md #27` records the reusable rule.

The previously generated ignored GLM task at HEAD `c94abfc755a279f873cd0745eb8cdb131103ef84` was never dispatched and is superseded. A fresh exact-SHA review packet must be generated only after this repair is committed and pushed.

## Exact repaired-snapshot audit — 2026-08-30

After GPT trust-boundary repairs, the exact working snapshot passed focused `17`, related `224`, and full local `1716 passed / 5 skipped / 2 failed`. The only failures remain the same local GPU dependency cases (`Pillow` import coupling and missing `OpenGL`) outside WO-P1-114. No new WO-P1-114 regression appeared. Next gate is repair commit/push followed by a fresh exact-SHA external review packet.

## Independent GLM review handoff prep - 2026-08-30

Task ID: `wo114-glm-review-002`.

Routing evidence was re-checked on 2026-08-30 against official Z.ai GLM-5.3 material: Terminal-Bench 3.0 `28.3`, DeepSWE v1.1 `66.9`, Z.ai Code Bench Max `34.5%`. This supports bounded repository/security review, not merge authority. GPT remains integrator/reviewer-of-record.

The GLM lane is read-only. It must review the exact branch snapshot, verify provider/secret/fail-closed boundaries and tests, and write only `runs/wo114-glm-review-002/result.json`. It must not edit source, tests, SSoT, Git, branch, commit, PR or live provider configuration.

Automatic provider dispatch is not yet authorized because runtime Drive binding, fresh required quota evidence, and provider-global serialized/atomic admission are still explicit blockers. If automatic execution remains unavailable, the human relays one short task-pointer prompt only; GPT reads the result file itself.

Next gate: commit/push this tracked handoff checkpoint, generate the ignored task packet from that exact HEAD, re-read literal identity/hash/result fields, then dispatch the independent review.
