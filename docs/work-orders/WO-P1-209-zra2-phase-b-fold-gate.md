# WO-P1-209 — ZRA-2 Phase-B accepted-tree fold gate

Status: PREPARED / HOLD UNTIL WO204 PASS + GPT ACCEPTANCE
Parent: WO-P1-165 / Issue #214
Integrator owner: GPT-5.6 Sol
Base at packet creation: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-209-zra2-phaseb-fold-gate`
Risk: R3 integration / reviewed-tree preservation

## 1. Purpose

Define the only safe integration path for ZRA-2 Phase B after independent review of the repaired stack.

The Phase-B source history is stacked on an old base:

- activation commit: `a1ec5eafba30640dd583b345756e931e41305661`;
- GLM parent candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` / PR #280;
- GPT no-clobber repair: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` / PR #281.

Independent GPT review already proved the parent candidate has a P1 publication TOCTOU/clobber defect. Therefore PR #280 must never be merged into `main` as an accepted standalone state, even temporarily.

If WO204 independently accepts exact repaired SHA `1c8c159...`, integration must preserve the reviewed source bytes while rebasing the accepted changes onto fresh `origin/main` through an explicit fold candidate.

This packet does not itself authorize the fold mutation.

## 2. External release gate

Do not create the source fold candidate until all of these are durably true:

1. WO204 review exists on its review branch and targets exact repaired SHA `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`.
2. WO204 verdict is exactly `PASS` with no unresolved P0/P1/P2 blocker.
3. GPT/integrator independently consumes that result and records `PHASE_B_REPAIRED_TREE_ACCEPTED` on Issue #214 / PR #281.
4. PR #281 exact SHA still has terminal-success hosted CI.
5. `origin/main` is freshly fetched/re-pinned.
6. No overlapping mutable lane owns the six Phase-B paths.
7. Fresh fold branch/worktree/claim is published with exact base SHA and scope.

Until then:

`SAFE_TO_FOLD_PHASE_B=NO`

## 3. Why direct PR merge is forbidden

PR #281 is stacked on PR #280. The exact history is:

```text
46f90b3  historical merge-base
  |
  +-- a1ec5ea  Phase-B activation docs
      |
      +-- 865ef3c  GLM Phase-B materializer (known P1 defect by itself)
          |
          +-- 1c8c159  GPT no-clobber repair (review target)
```

At packet creation, current main is `02d39cb...`, whose merge-base with `1c8c159...` remains `46f90b3...`.

Merging #280 first and #281 second would create a real main commit containing the known defective `865ef3c...` state. That is prohibited even if the interval is brief.

Merging #281 directly through GitHub also depends on stacked-base behavior and can make reviewed provenance harder to establish after base branch movement.

The accepted unit is the *combined repaired tree content*, not the defective parent commit in isolation.

## 4. Preflight drift result at packet creation

Read-only archaeology showed that `origin/main` changed none of the six Phase-B reviewed paths between `46f90b3...` and `02d39cb...`:

- `docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md`
- `docs/work-orders/WO-P1-203-zra2-phase-b-no-clobber-publication.md`
- `src/a_conductor/native_execution.py`
- `src/a_conductor/zero_relay_repair_materializer.py`
- `tests/test_native_execution.py`
- `tests/test_zero_relay_repair_materializer.py`

This makes a clean transplant likely, but this observation is not future authority. Re-run the exact path-drift check against fresh main immediately before fold mutation.

If any reviewed path changed on main after this packet, stop with:

`PHASE_B_FOLD_PATH_DRIFT`

Do not auto-resolve or mechanically rebase reviewed source through conflicting changes. A new composed candidate and independent review may be required.

## 5. Exact reviewed-path byte identities

The following SHA-256 values are over exact file bytes at repaired review target `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`.

| Path | SHA-256 | Git blob |
|---|---|---|
| `docs/work-orders/WO-P1-195-zra2-phase-b-materializer.md` | `512a15349158288d33f7a37f3bab84b471ce1c2fa00d95ee384c86ad6868aa42` | `d993c7c434b968ee62934c421a07a4e59e7391c4` |
| `docs/work-orders/WO-P1-203-zra2-phase-b-no-clobber-publication.md` | `7943dfc99a2f87228c6f6a00eed5577c55de7cc6f66d1dec4c52c1574613072b` | `a1734d7718b725a5562c3d421ba193c59ad2f6bb` |
| `src/a_conductor/native_execution.py` | `a1352143cfcbd0d4ebae786e895c9106e248fffffe280d408b5574234605c229` | `00ba4b07566fa64a44b9e21a23e0ac42891cc5e8` |
| `src/a_conductor/zero_relay_repair_materializer.py` | `693ae092fd3a23d81fcba6302f9b2e9b7298076b1204211ea99d8bbf58e4a304` | `393ac0c7a180f8ed6115847233e30839ad494654` |
| `tests/test_native_execution.py` | `5cb9ec4478d9c7960d9074a776652841dde119ed7f41e31fd12ac2b41ae0fac9` | `a794f54fece1379daa318b5364ab4cdb9dd4047e` |
| `tests/test_zero_relay_repair_materializer.py` | `f93a6c4df134f62238db6274bae5e37d9f8ad0242d92cfcd2cca69e7d8ff8f5a` | `d4dbab3e204029b6b52ebe7cbf42a1fbabfce198` |

The fold candidate must preserve these exact bytes unless a post-review main conflict makes preservation impossible. Any byte drift must be classified before CI and cannot inherit WO204 acceptance automatically.

## 6. Authorized fold shape after release

After release, create a fresh isolated branch/worktree from *then-current* `origin/main`, for example:

- branch: `integrate/wo-p1-209-zra2-phaseb-fold`
- worktree: dedicated new worktree
- owner: GPT integrator

Preferred operation if and only if path-drift preflight is clean:

1. cherry-pick `a1ec5eafba30640dd583b345756e931e41305661`;
2. cherry-pick `865ef3c18ebc5f4fb0f34f40dcee6851295baee4`;
3. cherry-pick `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`;
4. do **not** resolve conflicts by judgment; any conflict means stop and reclassify;
5. verify the six path blob IDs/byte SHA-256 values exactly match the accepted repaired target;
6. verify no unexpected changed path was introduced by the transplant;
7. run the complete Phase-B verification ladder on the fresh-main candidate;
8. freeze one exact fold candidate SHA;
9. push as Draft PR targeting `main`;
10. require hosted CI terminal success on the fold SHA;
11. perform integrator post-transplant provenance verification before merge.

The individual presence of `865ef3c` in fold history is acceptable only because the final candidate includes `1c8c159` before publication/merge to main; the intermediate cherry-pick state exists solely inside the private integration worktree and must never be pushed/PR'd/merged as the accepted head.

If repository policy prefers squashed application, a single squashed fold commit is also acceptable only if exact path bytes and scope are proven against `1c8c159...`. Do not choose squash merely to hide provenance.

## 7. Required scope

Expected source/test/doc scope is exactly the six reviewed paths above plus the fold work order/result metadata explicitly authorized for the integration lane.

Forbidden without a new explicit packet:

- Phase-C source;
- `zero_relay.py` Phase-A state-machine edits;
- review-mailbox source;
- GoalCloseout source;
- ZRA-3/ZRA-4 source;
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md` unless a dedicated coordination owner releases them;
- live Worker/runtime/provider files;
- credentials/configuration stores.

## 8. Fold preflight checks

Before cherry-pick/application:

### Repository identity

- correct remote/repository;
- fresh `origin/main` SHA;
- isolated worktree;
- clean worktree;
- branch unique and unclaimed;
- no unexplained untracked files.

### Review identity

- WO204 result exists;
- WO204 target exactly `1c8c159...`;
- verdict exactly PASS;
- review result branch/commit is pinned;
- no candidate drift after review;
- PR #281 exact hosted CI success still available.

### Path drift

For each of six paths compare:

```text
merge-base -> current main
```

If current main modified any path since merge-base, stop. Do not assume Git can semantically merge an R3 reviewed boundary safely.

### Ownership

Search open PRs/claims/worktrees for overlapping mutable paths. An additive documentation PR that merely references these paths is not source overlap; an active source/test mutation lane is.

## 9. Byte-preservation proof

After creating the fold candidate, recompute both:

- Git blob ID;
- SHA-256 over exact bytes.

Every reviewed path must match Section 5 exactly.

Also prove:

```text
git diff --exit-code 1c8c159...:<path> FOLD_SHA:<path>
```

or equivalent exact byte comparison for every path.

Do not use line-count/stat equality as byte proof.

## 10. Verification ladder on fold candidate

At minimum:

1. `tests/test_zero_relay_repair_materializer.py`;
2. `tests/test_native_execution.py`;
3. `tests/test_agent_change_packets.py`;
4. `tests/test_claude_code_harness.py`;
5. `tests/test_zero_relay.py`;
6. `tests/test_review_mailbox_adapter.py`;
7. `tests/test_goal_closeout.py`;
8. any additional tests named by WO204 PASS result;
9. compile relevant source;
10. `git diff --check`;
11. strict UTF-8 / no U+FFFD;
12. secret-like added-line scan;
13. exact changed-path audit;
14. repeat the no-clobber adversarial reproducer on fresh-main fold candidate;
15. hosted CI on exact fold SHA.

Any behavioral failure on the fresh-main candidate means WO204's old-base acceptance is insufficient for integration. Stop and classify; do not patch silently inside the fold lane.

## 11. Merge gate

Even after local verification, fold PR stays Draft until hosted CI is terminal success and integrator verifies:

- fold SHA exact;
- accepted reviewed path bytes exact;
- scope exact;
- no hidden conflict resolution;
- no new blocking review finding;
- current main has not advanced into a conflicting reviewed path.

If main advances only in unrelated paths after fold CI, normal merge ancestry may still be acceptable, but post-merge exact tree/path verification is mandatory.

If main advances in a reviewed path, do not merge stale fold PR.

## 12. Post-merge proof

After merge to main:

1. fetch exact merge commit;
2. prove six reviewed path bytes still equal Section 5 identities;
3. prove merge tree contains the fold candidate changes;
4. run/observe required post-main CI if project policy requires it;
5. record merge commit and post-main evidence on Issue #214;
6. only then classify Phase B `ACCEPTED + MERGED + POST_MAIN_VERIFIED`;
7. only then may Issue #214 release Phase C `NEXT_READY`.

Phase-C source mutation before this sequence completes is forbidden.

## 13. Failure classifications

Use explicit typed state in handback:

- `BLOCKED_WO204_NOT_ACCEPTED`
- `BLOCKED_REPAIR_SHA_DRIFT`
- `BLOCKED_REPAIR_CI`
- `BLOCKED_MAIN_PATH_DRIFT`
- `BLOCKED_SCOPE_OVERLAP`
- `BLOCKED_CHERRY_PICK_CONFLICT`
- `BLOCKED_BYTE_IDENTITY_DRIFT`
- `BLOCKED_LOCAL_REGRESSION`
- `BLOCKED_FOLD_CI`
- `BLOCKED_MAIN_ADVANCED_REVIEWED_PATH`
- `READY_FOR_FOLD_MERGE`
- `PHASE_B_POST_MAIN_VERIFIED`

Unknown evidence never becomes READY.

## 14. Durable result

The eventual fold lane must write a durable result containing:

- old accepted repair SHA;
- WO204 review evidence ref/SHA;
- fresh main base SHA;
- exact fold candidate SHA;
- transplant method;
- changed paths;
- six before/after blob IDs and SHA-256 values;
- local verification commands/results;
- hosted CI URLs/status;
- merge status;
- post-main merge/tree/CI proof;
- next-safe-action;
- explicit Phase-C release state.

## 15. Current state

At packet creation:

- `origin/main = 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`;
- PR #281 head = `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`;
- PR #281 hosted CI = all SUCCESS / merge state CLEAN;
- WO204 independent GLM review has been invoked by the user but result is not yet accepted by GPT;
- main has no changes on the six reviewed Phase-B paths since merge-base `46f90b3...`.

Therefore:

`SAFE_TO_FOLD_PHASE_B=NO`

Next safe action: wait for durable WO204 handback, independently consume it, then either release this fold packet or return the repaired candidate for further repair.