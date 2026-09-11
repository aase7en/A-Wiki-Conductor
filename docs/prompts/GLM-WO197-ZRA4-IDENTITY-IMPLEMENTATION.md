# GLM task packet — WO-P1-197 ZRA-4 identity implementation

STATUS: HOLD — DO NOT EXECUTE PRODUCT MUTATION UNTIL RELEASED BY ISSUE #216.

When released, read in this order:

1. `00-AGENT-ENTRY.md`
2. `PROJECT-GRAPH.yaml`
3. repository-local `AGENTS.md`
4. `docs/work-orders/WO-P1-197-zra4-identity-implementation-gate.md`
5. accepted WO196 design from exact SHA `10dca359568c216983199a6899b0af3863b5e9d7`:
   - `docs/work-orders/WO-P1-196-physical-workspace-identity.md`
   - `docs/plans/2026-09-11-physical-workspace-identity-contract.md`
   - `docs/prompts/GLM-WO196-PHYSICAL-IDENTITY-LAB.md`
6. parent Issue #216 release/claim evidence and accepted ZRA-3 SHA(s).

## Goal

Close C1/C1b before ZRA-4 parallel mutation fan-out:

- physical workspace/resource identity must prevent alias-based double mutation;
- Windows scope spelling aliases must collide deterministically;
- existing Worker lease transaction remains the atomic reservation authority;
- unknown/unsupported identity fails closed;
- authorization scope must never be widened by canonicalization.

## Mandatory starting checks

Before editing, record:

- repo/worktree/branch/HEAD/origin-main;
- clean/dirty state and explanation;
- parent accepted ZRA-3 SHAs;
- Issue #216 implementation release comment;
- open PR overlap for intended files;
- owner/claim/lease/mutable scope;
- `SAFE_TO_MUTATE=YES` only if all material state is compatible.

If release evidence is absent, write only a checkpoint with `BLOCKED_ZRA3_ACCEPTANCE` and stop.

## RED-first requirements

Implement the exact RED matrix in WO197. At minimum, RED must prove current failures for:

```text
write_sets_overlap(('src\\a.py',), ('src/a.py',)) == False
write_sets_overlap(('SRC/a.py',), ('src/a.py',)) == False
```

and native alias double-lease cases from WO196 where the platform supports them.

Do not weaken tests to fit current implementation.

## Implementation constraints

- Prefer one versioned identity/resource projection consumed by existing seams.
- Do not add a second scheduler/conflict engine/lease registry.
- Keep allowed/forbidden scope authorization separate from conservative mutation reservation.
- Use OS-backed identity for physical equality; do not infer cross-host equality from remote URL/path text.
- Junction/symlink/reparse/8.3/drive aliases must have explicit outcomes.
- Hardlink handling must not claim name-level independence when file-object equality is known.
- Nonexistent targets must inherit a conservative parent/resource disposition.
- UNKNOWN != DISTINCT.
- Legacy/unversioned lease identities must be fenced or migrated explicitly.
- No live Worker/process/provider/ZCode credential changes.

## Verification

Run the WO197 verification floor plus any narrower regression suites required by touched seams. Preserve exact command/output summaries in `runs/WO-P1-197/result.md`.

Before freezing candidate:

- compile/import pass;
- `git diff --check` pass;
- strict UTF-8/no U+FFFD;
- added-line secret scan clean;
- exact changed-scope audit;
- worktree state explained;
- commit/push only the declared branch;
- hosted CI on candidate exact SHA.

## Handback

Do not merge or self-accept.

Freeze strongest verified candidate and report only durable pointers:

- branch;
- exact SHA;
- PR;
- `runs/WO-P1-197/result.md`;
- remaining P0/P1/P2 findings.

GPT-5.6 Sol retains integration and exact-SHA acceptance. ZRA-4 fan-out stays disabled until C2 batch identity and live 2–3 lane proof are separately accepted.
