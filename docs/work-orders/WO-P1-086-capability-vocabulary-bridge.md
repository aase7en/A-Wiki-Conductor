# WO-P1-086 — Capability vocabulary bridge C0

Status: COMPLETE / MERGED
Owner: GPT-5.6 Sol integrator
Parent: `WO-P1-085` / Capability Fabric C0
Repository: `aase7en/A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-capability-c0`
Branch: `docs/wo-p1-086-capability-vocabulary`
Base: `origin/main@9106da2`

## Goal

Define a small versioned mapping contract between A-Wiki's canonical `awiki-task/v1` required-capability vocabulary and A-Conductor's execution/runtime capability vocabulary without creating a second skill registry, scheduler, or brain taxonomy.

This slice is docs/contract only. It does not change scheduler/runtime behavior.

## Repository / ownership gate

`SAFE_TO_MUTATE = YES` only for this isolated worktree and the additive files in this WO.

Allowed:
- this work order;
- `docs/contracts/capability-vocabulary-bridge.md`.

Forbidden: production code/tests/schemas, shared continuity hotspots, PR #104 Graph scope, release/installer worktrees, North Star mutable files, and all A-Wiki mutation.
## Evidence basis

A-Wiki was inspected read-only at local/remote `main@290626ba`; its worktree is dirty in unrelated generated/wiki files, so no A-Wiki mutation is permitted here.

Verified canonical A-Wiki source:
- `config/awiki.yaml` points capability vocabulary to `schemas/awiki-task/v1.schema.json`;
- the schema defines exactly 20 vendor-neutral capability values and says it is the only capability definition.

Verified Conductor surfaces:
- `graph/domain.py` currently embeds the same 20 values for TaskNode validation;
- core `domain.Capability` is intentionally open/provider-neutral;
- North Star runtime work introduces operational names such as `semantic.code`, `repo.tools`, `filesystem.*`, `process.*`, `data.analysis`, and `remote.device`.

## Acceptance

- distinguish brain/task requirements from runtime/tool supply;
- preserve A-Wiki 20-value vocabulary unchanged as canonical task intent;
- define deterministic mapping/gap rules without vendor names;
- unknown or partial mappings fail closed;
- cognitive/model requirements cannot be satisfied merely by a runtime tool;
- mutation authority remains a policy gate, not a capability-name alias;
- no registry/state duplication;
- `git diff --check` passes and changed files remain docs-only.
## Checkpoint — C0 draft contract (2026-08-28)

- A-Wiki local/remote `main` identity matched at `290626ba`; inspection was read-only despite unrelated dirty generated/wiki files.
- Conductor base was exact `origin/main@9106da2` after PR #109 merged.
- New contract separates task/actor requirement, execution supply, and policy/authority instead of conflating them.
- The 20-value A-Wiki vocabulary remains canonical; Conductor Graph copy is treated only as a compatibility mirror.
- Runtime dot-names from the accepted North Star branch are mapped as implementation supply, not promoted into A-Wiki policy.
- `git diff --check`: PASS; bounded secret-pattern scan: PASS.
- Commit: `572d3a2`; Draft PR: #110.

Next safe action: independent review of PR #110; no C1/C2 production mutation until the mapping contract is accepted and current North Star/GE ownership is reconciled.

## Repo-health reconciliation - 2026-08-29

- Historical execution text above is preserved as evidence; the stale status is superseded by accepted GitHub state.
- PR #110 merged into main as `6487cb2b796bbd4351cf8c65ce9c6e90de8d96f3`.
