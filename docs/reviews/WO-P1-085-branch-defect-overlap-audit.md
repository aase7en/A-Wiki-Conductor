# WO-P1-085 — Branch / Defect / Overlap Audit

Date: 2026-08-27
Reviewer: GPT-5.6 Sol via Remote Desktop Commander
Repository: `aase7en/A-Wiki-Conductor`
Reference main: `origin/main@64bc628e233a6fb596a7dc6d188f7cdef35b3bbe`

## Verdict

`CHANGES_REQUIRED` before Graph Engineering merge/release integration.

No current branch produced a textual merge conflict against `origin/main` in `git merge-tree --write-tree` checks. That does **not** mean the lanes are integration-safe: the audit found branch-lineage contamination, a duplicated work-order ID, two Graph semantic/spec defects despite green CI, and a release-safety defect in installer target ownership.

## Worker safety

No SunDay Worker was reassigned or invoked for this audit.

Observed ownership made Worker 1/2/3/5 unsafe to borrow; Worker 4 lacked enough positive evidence for mutation ownership despite being the least busy candidate. Repo-wide inspection therefore used Remote Desktop Commander only. Any later GLM task must use its existing explicitly-owned branch/worktree or a newly preflighted isolated lane; it must not borrow a Worker owned by another Project.

## Branch topology summary

- shared `main@f4ecf9a`: 65 commits behind remote and dirty (`assets/donate-promptpay-qr.png`) — protected/read-only.
- PR #102 `fix/ge-005a-glob-conflict@dabca86`: open, mergeable/CLEAN, current 3-OS checks green.
- PR #104 `feat/ge-6-scheduler@43cd20f`: open, mergeable/CLEAN, current 3-OS checks green; PR #102 tip is its ancestor.
- PR #108 `fix/v070-installer-target-ownership@67f35b6`: open, mergeable/CLEAN, current 3-OS checks green.
- `feat/north-star-dc-contract-glm@6676dbf`: clean local bounded GLM N3 lane; no PR, awaiting integrator review.
- `feat/north-star-runtime-sunday-family@88c7d5b`: active/dirty WO-P1-078 checkpoint — do not overlap.
- `fix/v070-installer-powershell-path-quoting`: active GPT lane with untracked WO-P1-084 — do not overlap.

## Finding F1 — capability-plan branch contamination [P1 / FIXED]

The first pushed branch `docs/wo-p1-083-capability-upgrade-plan@8ee6458` was based on North Star `88c7d5b`, not main. Relative to current main it was behind 2 / ahead 9 and exposed 22 changed files, including runtime/UI/tests unrelated to the docs plan.

A PR from that branch would have mixed North Star implementation with the capability-planning change. The branch remains a remote backup only and must not be used for PR/merge.

Repair: created `docs/wo-p1-085-capability-upgrade-plan` from current `origin/main@64bc628` and carried only the planning documentation forward.

## Finding F2 — duplicated WO-P1-083 identity [P1 / FIXED]

The first capability plan used `WO-P1-083`, but the live installer target-ownership lane already uses `WO-P1-083-v070-installer-target-ownership.md` / PR #108. Two unrelated durable tasks sharing the same WO number would make handoff/claims/evidence ambiguous.

Repair: capability plan renumbered to **WO-P1-085**. Installer retains WO-P1-083; path quoting retains WO-P1-084.

## Finding F3 — PR #102 overlap algorithm is unsafe for two globs [P0]

Current `write_sets_overlap()` reuses one seam, but `paths_overlap()` approximates intersection by normalizing `**`, applying `fnmatch` in both directions, then substring matching.

Read-only proof on PR #102 code:
- `src/*/a.py` vs `src/x/*.py` -> **False**, although both can match `src/x/a.py` (unsafe false negative).
- `src/a.py` vs `src/a.py.bak` -> **True**, although the two literal files are distinct (false positive).

Because GE write sets are path-glob sets, CI coverage is incomplete. PR #102 must not merge until the authoritative overlap seam gets intersection-safe regressions and a deterministic correction without creating another matcher.

## Finding F4 — PR #104 does not yet satisfy accepted GE-0006 scheduler contract [P0]

Current scheduler tests are green, but direct spec comparison found missing accepted behavior:

- worker choice follows supplied tuple order rather than stable lexical worker ID;
- node ordering is `priority -> lexical id`, omitting earlier DAG/topological rank;
- explicit worker binding is not enforced;
- mutating work checks `mutation_authorized` but does not fail closed on project/workspace identity mismatch/absence;
- scheduler does not consume typed gate/provider eligibility snapshots, so NO-GO/human/provider/rate-limit eligibility cannot be represented as required by GE-0006.

Read-only proof: with equivalent workers `(w-z, w-a)`, current code selected `w-z`; a mutating node bound to `worker:w-a` / expected workspace still selected `w-z` whose project/workspace were intentionally wrong.

PR #104 stacks on PR #102 (`dabca86` is an ancestor of `43cd20f`), so PR #102 semantics should be repaired/reviewed first, then PR #104 should receive bounded spec-compliance TDD.

## Finding F5 — PR #108 authorizes uninstall against an unrelated empty target [P0 release safety]

`_uninstall_target_is_managed_or_safe()` returns `True` immediately when `_target_is_empty(target)` is true. Install-to-empty is correctly allowed, but uninstall ownership has a stronger requirement: it must validate managed ownership before deleting global shortcuts/registry/target.

Safe proof called only the predicate, not uninstall side effects, on Windows:
- `target_empty=True`
- `uninstall_authorized=True`

A caller using an unrelated empty/nonexistent target could therefore reach `do_uninstall()`, which removes the product's global shortcuts/registry before deleting that target. Add a RED regression and require ownership evidence for uninstall even when the supplied target is empty/nonexistent.

This remains a GPT/release-owner lane because it crosses destructive installer boundaries and is stacked with active WO-P1-084 path-quoting work. Do not delegate it to an unrelated Worker.

## GLM 5.3 suitability — evidence from this repository

The repository capability matrix is useful background but includes proxy/older benchmark rows, so delegation decisions here use direct project evidence first.

Observed bounded GLM performance:
- N2 runtime catalog: GLM obeyed missing-worktree safety, then delivered bounded pure metadata; independent rerun **32 passed**, compileall/diff-check PASS; its implementation was later integrated by GPT.
- N3 Desktop Commander contract: GLM stayed in allowed schema/docs/tests scope; independent rerun **28 passed**, compileall/diff-check PASS.
- GE-005A / GE-6: current CI reruns are green and independent targeted reruns passed **34/34** and **48/48**, but this audit still found untested semantic/spec gaps.

Verdict: GLM is suitable for **bounded pure-Python TDD, deterministic regression expansion, schema/contracts, static analysis and repository archaeology** with an explicit contract. GLM is not final authority for cross-branch integration, destructive installer/release safety, architecture/trust-boundary decisions, merge decisions, or broad SSoT reconciliation.

## Recommended GLM lanes

1. **GLM-GE005A** — repair F3 on the existing PR #102 branch only. This is a narrow algorithm + regression task and matches GLM's demonstrated strengths.
2. **GLM-GE6** — after F3 is accepted, repair F4 on PR #104 only. It is deterministic pure scheduler TDD with an already-accepted ADR.

Do not give GLM PR #108/WO-P1-084 release-installer work. Do not reuse any SunDay Worker owned by another Project merely to run these prompts.

## Current deterministic evidence

- PR #102 focused graph: `34 passed`.
- PR #104 focused scheduler/graph: `48 passed`.
- N2 runtime catalog: `32 passed`.
- N3 DC contract: `28 passed`.
- PR #108 installer ownership/self-delete/build: `36 passed`.
- PR #102/#104/#108 GitHub 3-OS checks: current green.

Green tests are evidence of covered behavior, not evidence that uncovered contract requirements are satisfied.

## Integration order / anti-overlap gate

Recommended order from current evidence:

1. GPT release owner fixes/reviews PR #108 empty-target uninstall authorization and completes active WO-P1-084 path quoting; preserve their existing worktrees.
2. GLM-GE005A repairs PR #102 in its existing owned worktree; GPT independently reviews exact final HEAD.
3. Only after #102 is accepted, GLM-GE6 repairs PR #104; GPT independently reviews exact final HEAD and stacked ancestry.
4. N3 DC contract `6676dbf` gets independent GPT contract review before integration into the active North Star lane.
5. Do not integrate Capability Fabric production changes until the GE/North-Star ownership gates in WO-P1-085 are reconciled.

## Stale / cleanup candidates — no destructive cleanup authorized

Several merged or superseded worktrees/branches remain locally (repo-health, uninstall fix, detached release-audit, standalone N2). They are not automatically safe to delete because some contain untracked/protected evidence or may be continuity anchors.

This audit therefore performs no reset, clean, branch deletion, worktree removal, rebase, merge, or force-push.

## Final state

The audit is suitable to persist with the clean WO-P1-085 docs branch. The earlier pushed WO-P1-083 capability branch is explicitly superseded and should have no PR. Future agents must re-fetch GitHub and re-check ownership because branch/PR state may change after this snapshot.
