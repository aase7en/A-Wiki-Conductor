# WO-P1-088 - Provider + Harness Contracts (AHA-1)

Status: ACTIVE / TDD CONTRACT SLICE
Owner: GPT-5.6 Sol integrator via Remote Desktop Commander
Parent: WO-P1-087 / Sunday Family Multi-Model Agent Harness Accelerator
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-provider-harness`
Branch: `feat/wo-p1-088-provider-harness-contracts`
Base: `origin/main@6487cb2b796bbd4351cf8c65ce9c6e90de8d96f3`

## Goal

Define provider-neutral configuration, observation, and harness-dispatch contracts that let A-Sunday Conductor represent a Claude-Code/Anthropic-style coding harness backed by GLM-5.3 first, without hard-coding GLM, storing credentials, adding live network execution, or creating a second scheduler/task lifecycle.

## Reuse-before-build

Classification: `EXTEND + WRAP`.

Reuse accepted main authority:
- `docs/contracts/capability-vocabulary-bridge.md` (C0 / PR #110);
- core `Provider`, `Agent`, `Runtime`, `Capability` domain vocabulary;
- `schemas/task-contract.schema.json` for bounded task authority/scope;
- resilient execution supervisor for transport-vs-execution separation;
- native operation/operator contracts for opaque bounded authority;
- North Star N2/N3 as accepted integration evidence only, without copying its branch into this slice.

## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only in this isolated worktree and additive AHA-1 files.

Allowed mutable scope only:
- this work order;
- `docs/contracts/provider-harness.md`;
- `schemas/provider-profile.schema.json`;
- `schemas/provider-observation.schema.json`;
- `schemas/harness-dispatch.schema.json`;
- `schemas/examples/provider-profile.example.json`;
- `schemas/examples/provider-observation.example.json`;
- `schemas/examples/harness-dispatch.example.json`;
- `tests/test_provider_harness_contract.py`.

Forbidden:
- existing `src/**` production code/domain mutations;
- existing tests/schemas/contracts outside the list above;
- `PROJECT-PLAN.md`, `DESIGN.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`;
- PR #104/GE-6, PR #108 installer, PR #111 priority-plan branch, North Star branch;
- A-Wiki mutation;
- live API/provider calls, Claude Code/ZCode process launch, credential store access;
- plaintext API keys/tokens or screenshot-derived credentials.

## Contract decisions

1. Provider configuration and provider observation are separate: configured does not imply READY.
2. Actor/model capability evidence is separate from runtime/tool supply per C0.
3. Provider/model names never become canonical task capability IDs.
4. `credential_ref` is opaque secret-store identity only; contract has no API-key/token/secret value field.
5. Third-party trust and egress boundary are explicit and independent from health; task authorization remains separate.
6. Quota is optional observed evidence with timestamp/provenance; missing quota is UNKNOWN, not zero/infinite.
7. Harness dispatch references an existing `task_contract_ref`; it does not contain a raw conversational prompt/transcript.
8. Harness strategy is fixed enum metadata, beginning with `CLAUDE_CODE_CLI`; it is not arbitrary executable/argv/shell text.
9. Dispatch must carry project/worktree identity, mutation intent, timeout/output bounds, provider/model identity and stable execution identity.
10. This slice creates no scheduler, retry authority, model router, live subprocess runner, or network client.

## TDD acceptance

Write contract tests first and prove RED because the schemas/contract/examples do not exist. Then implement the smallest files that make them pass.

Tests must mechanically prove at minimum:
- all schemas are closed objects (`additionalProperties: false`);
- provider profile has `credential_ref` but no secret-bearing value fields;
- provider profile has explicit protocol, trust, egress boundary, harness strategy and model profiles;
- model profile carries actor capability evidence metadata separate from execution supply;
- observation has typed health, `observed_at`, provenance and optional quota snapshot;
- quota contains used/remaining/limit/reset observation fields but no bypass semantics;
- harness dispatch requires `task_contract_ref`, execution/project/worktree identity, provider/model/harness identity, mutation intent, timeout and output budget;
- harness dispatch has no `prompt`, `transcript`, `command`, `argv`, `shell`, `executable`, or arbitrary environment field;
- examples contain no secret-like key/token values;
- contract states `CAPABLE != AUTHORIZED`, configured != ready, transport failure != execution failure, and worker DONE is not completion authority.

## Verification

- `python -m pytest -q tests/test_provider_harness_contract.py`
- `python -m compileall -q src/a_conductor`
- `git diff --check`
- bounded changed-file + secret-pattern scan.

## Stop condition

Stop after AHA-1 is locally verified and committed for independent review. Do not start AHA-2 or any live provider process from this work order.

## Checkpoint - AHA-1 local verification

TDD evidence:
- RED: initial `python -m pytest -q tests/test_provider_harness_contract.py` -> 7 failed because the AHA-1 contract/schema/example artifacts did not exist.
- GREEN after minimal implementation: 7 passed, then schema/example validation was added and the focused suite became 8 passed.

Self-review hardening:
- replaced policy-like `data_egress_class` with factual `egress_boundary` so provider configuration does not grant task authority;
- removed arbitrary `metadata` / `details` catch-all payloads from provider, observation, and dispatch schemas to reduce secret/prompt smuggling surfaces;
- kept provider health/quota as separately observed evidence;
- kept `credential_ref` opaque and examples synthetic;
- kept harness dispatch free of raw prompt/transcript/command/argv/shell/executable/environment fields.

Verification at this checkpoint:
- `python -m pytest -q tests/test_provider_harness_contract.py` -> 8 passed;
- `python -m compileall -q src/a_conductor` -> PASS;
- `git diff --check` -> PASS.

Next safe action: run bounded related tests + secret/scope scan, commit/push this additive slice, and open a Draft PR for independent review. Do not start AHA-2 or live provider execution.
## Checkpoint - Draft PR #112

- implementation commit: `1eb8d859bbd69ed0d1d84fd3dd0a97c1383cfacf`;
- Draft PR #112: `feat: define provider-neutral model harness contracts`;
- remote PR base at creation: `main@6487cb2`;
- remote diff audited: exactly the nine additive AHA-1 files listed in this work order; no production `src/**` or existing-file mutation;
- no real proxy credential/endpoints were copied from screenshots; examples use synthetic refs/values only;
- AHA-2/live provider execution remains blocked pending independent review + CI + merge/reconciliation.

Next safe action: inspect PR #112 CI and obtain independent review of the actual remote diff. If changes are required, repair this same bounded slice and re-run focused/schema checks.
