# WO-P1-090 — Secure Provider Configuration + Observation (AHA-2)

Status: COMPLETE / MERGED
Owner: GPT-5.6 Sol via Remote Desktop Commander
Parent: WO-P1-087 Sunday Family Agent Harness Accelerator
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-provider-config`
Branch: `feat/wo-p1-090-provider-config-observation`
Base: `origin/main@c3ca84c81d901ae844ee40780619a41b46307049`

## Goal

Implement the smallest provider-neutral local configuration and observation seam needed before any live Claude Code/provider execution.

AHA-2 stores only non-secret provider metadata plus opaque `credential_ref`, validates safe endpoint metadata, normalizes injected/fake health and quota evidence, and keeps configuration/readiness/authorization distinct.

## Reuse-before-build

Classification: `EXTEND + WRAP`.

Reuse:
- AHA-1 `provider-harness/v1` schemas/contracts merged in PR #112;
- existing domain `Provider`/`Runtime`/`Capability` vocabulary;
- existing local SQLite control-plane persistence pattern;
- North Star N2 principle that availability is observed, never inferred.

Do not duplicate:
- scheduler/model router/task lifecycle/retry authority;
- North Star runtime catalog;
- provider-specific execution process;
- secret vault or credential values.

## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only in this isolated worktree.

Allowed scope:
- this work order;
- `src/a_conductor/provider_configuration.py`;
- `src/a_conductor/provider_config_store.py`;
- `tests/test_provider_configuration.py`;
- `tests/test_provider_config_store.py`;
- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md` for continuity only.

Forbidden:
- PR #104 / GE-6 and graph scheduler files;
- PR #108 installer files;
- North Star branch/files not already on main;
- desktop UI;
- live network/API/provider/Claude/ZCode execution;
- raw credentials, tokens, authorization headers, or secret-bearing diagnostics.

## Acceptance

1. Provider configuration matches AHA-1 vocabulary and contains no secret-value field.
2. `credential_ref` stays opaque and is never resolved by this slice.
3. External endpoint base URL requires HTTPS; HTTP is accepted only for explicit loopback hosts.
4. Endpoint URLs reject embedded userinfo, query, and fragment components.
5. Configuration persists in the existing control SQLite database, not a new database/product registry.
6. Latest observation is separate from configuration and records timestamp + provenance.
7. Quota values are optional observations; missing values remain unknown.
8. Stale/missing/non-AVAILABLE observation never produces READY.
9. Injected fake probe results normalize typed auth/rate/quota/unavailable/degraded/available states without network I/O.
10. Provider availability never grants task authorization.

## TDD / verification

RED first:
- tests import new seams before implementation and fail for missing module.

GREEN:
- `python -m pytest -q tests/test_provider_configuration.py tests/test_provider_config_store.py tests/test_provider_harness_contract.py tests/test_domain.py`
- `python -m compileall -q src/a_conductor`
- `git diff --check`
- changed-file scope audit + bounded secret-pattern scan.

## Stop condition

Stop AHA-2 after fake/injected observation, non-secret persistence, continuity checkpoint, Draft PR, and green CI. Do not launch Claude Code or call any live provider from this work order.

## Next safe action

Claim continuity hotspots, write failing AHA-2 tests, then implement only enough configuration/store/normalization code to satisfy this contract.

## Checkpoint — AHA-2 GREEN implementation

TDD evidence:
- RED: focused suite failed at collection because `provider_configuration` and `provider_config_store` did not exist.
- GREEN: `39 passed in 0.83s` for provider configuration/store + AHA-1 contract + domain tests using an isolated `--basetemp`.
- An earlier local run completed test bodies but pytest cleanup hit `WinError 5` on the machine-wide `pytest-current` link; isolated basetemp removed that environment-only failure.

Implemented seams:
- closed provider/model/capability enums + dataclasses aligned with AHA-1 vocabulary;
- HTTPS external endpoints, HTTP only for actual loopback hosts, with userinfo/query/fragment rejected;
- opaque `secret-ref:*` validation only; no credential resolution;
- injected probe result normalization for AVAILABLE/DEGRADED/UNAVAILABLE/AUTH_FAILED/RATE_LIMITED/QUOTA_EXHAUSTED;
- freshness-based readiness with no authorization field/side effect;
- same-control-SQLite provider/endpoints/latest-observation tables with explicit non-secret columns.

Verification:
- `python -m compileall -q src/a_conductor` -> PASS;
- `git diff --check` -> PASS;
- bounded live-network/subprocess import scan in AHA-2 modules -> clean;
- bounded credential-value signature scan across all changed files -> `0` hits;
- exact changed-file set remains the eight files authorized by this work order.

Next safe action: commit/push this bounded slice, open Draft PR, inspect remote diff, and require exact-head CI before merge. AHA-3 remains blocked until AHA-2 is merged.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #114 merged into main as `ca4cd986c9d3ad0b9af833350f067ff9056df653`.
