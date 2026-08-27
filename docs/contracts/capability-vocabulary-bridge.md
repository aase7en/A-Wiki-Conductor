# Capability Vocabulary Bridge — A-Wiki `awiki-task/v1` ↔ A-Conductor

Status: C0 mapping contract / WO-P1-086

## 1. Authority

A-Wiki owns canonical task/agent capability intent. Its source is `schemas/awiki-task/v1.schema.json`.

A-Conductor owns observed execution supply: workers, runtimes, providers, tools, authority, availability, dispatch and evidence.

The two vocabularies are related but are not the same namespace.

Do not rename A-Wiki capabilities to match a provider. Do not promote runtime/tool feature strings into brain policy merely because a provider exposes them.

## 2. Three dimensions

Eligibility is the intersection of independent dimensions:

1. **Task/actor requirement** — stable A-Wiki capability intent.
2. **Execution supply** — observed Conductor runtime/provider/tool features.
3. **Policy/authority** — project/workspace identity, mutation permission, approval, cost/egress and current health.

A match in one dimension never implies the others.

Example: `filesystem.write` does not by itself satisfy `repository-write`; the worker must also be bound to the correct project/workspace and have positive mutation authority.
## 3. Canonical A-Wiki capability classes

### Execution/tool-facing

- `repository-read`
- `repository-write`
- `shell`
- `tests`
- `web-research`
- `data-analysis`

### Cognitive/agent-facing

- `code-review`
- `deep-reasoning`
- `architecture-review`
- `security-review`
- `long-context`
- `documentation`
- `translation`
- `independent-judgement`

### Semantic code-context

- `project-code-context`
- `symbol-search`
- `call-graph`
- `blast-radius`

### Brain/memory

- `memory-read`
- `memory-write`
## 4. Observed execution-supply mapping

The operational dot-names below are verified on the accepted/integrated North Star branch; they are not all present on `main` yet. This C0 document maps the seam without importing that implementation into this branch.

| A-Wiki requirement | Conductor supply seam | Rule |
|---|---|---|
| `repository-read` | `repo.tools` or scoped `filesystem.read` | project scope required |
| `repository-write` | `repo.tools` or `filesystem.write` | plus exact project/workspace identity + mutation authority |
| `shell` | `process.execute` | fixed/bounded operation authority still applies |
| `tests` | `process.execute` + project/repo access | no dedicated runtime capability yet; do not infer test competence from shell alone |
| `web-research` | GAP on accepted main | future research provider must be explicit and observable |
| `data-analysis` | `data.analysis` | tool supply only; task quality still needs capable actor when reasoning is required |
| `project-code-context` | `semantic.code` | aggregate semantic seam; operation-level support must be verified |
| `symbol-search` | `semantic.code` | same aggregate seam |
| `call-graph` | `semantic.code` | same aggregate seam; fail closed if runtime cannot actually trace calls |
| `blast-radius` | `semantic.code` | same aggregate seam; evidence required |
| `memory-read` | A-Wiki brain bridge | not a runtime-catalog capability |
| `memory-write` | A-Wiki brain bridge + promotion/policy gate | never direct runtime truth mutation |

The cognitive/agent-facing requirements have **no valid runtime-only mapping**. They must be satisfied by actor/model capability evidence independently of tool availability.
## 5. Version and drift rules

- Bridge version starts at `awiki-task/v1 ↔ conductor-capability-bridge/v1`.
- A-Wiki remains the source for the 20 task-capability values; Conductor's copied Graph tuple is a compatibility mirror, not an independent authority.
- A future parity test or generation step should detect drift between A-Wiki `awiki-task/v1` and Conductor's Graph mirror without requiring A-Wiki at runtime.
- Runtime/provider capability strings remain open implementation metadata and may evolve independently behind this bridge.
- A mapping may be `EXACT`, `COMPOSITE`, `ACTOR_ONLY`, `BRAIN_ONLY`, or `UNMAPPED`; `UNMAPPED` is non-selectable.
- Capability aliases must be versioned and explicit; silent fuzzy matching is forbidden.
- Provider/vendor/model names never become stable task capability IDs.

## 6. Scheduler consequence

Scheduler eligibility must eventually require all applicable checks:

`task capability satisfied ∧ actor capability satisfied ∧ runtime supply satisfied ∧ identity/authority satisfied ∧ gate/provider health satisfied`

This contract does not authorize scheduler changes. PR #104 remains the owner of GE-6 implementation semantics.

## 7. Known gaps for later slices

- no accepted-main research provider yet for `web-research`;
- no dedicated runtime feature proving `tests` beyond bounded process/repo operations;
- semantic aggregate `semantic.code` is coarser than A-Wiki's four semantic requirements;
- actor/model capability evidence needs an explicit observed source rather than vendor-name assumptions;
- memory read/write must remain behind the A-Wiki bridge and its promotion/privacy policy.

These gaps are intentional fail-closed inputs to C1/C2, not reasons to widen C0 into implementation.