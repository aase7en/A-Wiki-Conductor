# WO-P1-086 — Capability vocabulary bridge C0

Status: IN_PROGRESS
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