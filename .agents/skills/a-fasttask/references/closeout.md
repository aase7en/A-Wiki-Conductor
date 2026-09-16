# A-FastTask reference — temporary-lane closeout (cleanup)

Cleanup is an EXPLICIT end-of-lane action only — never automatic, never a
background queue (WO-P1-245). This reference reuses existing evidence
authorities and adds no cleanup scheduler.

## Preconditions (all required; any UNKNOWN => `SAFE_TO_CLEANUP = NO`)

1. Evidence — the lane's outcome is accepted/reconciled, and where the lane
   produced remote deliverables, post-main evidence exists per the delivery
   gate sequence (exact reviewed head → exact-head CI → expected-head merge →
   post-main CI → checkpoint on the driving issue). An ignored result INSIDE
   the target worktree is NOT durable evidence: before cleanup, material
   review/result evidence must be folded/checkpointed to GitHub/tracked
   authority or to an evidence destination OUTSIDE the target worktree. Local
   ignored artifacts inside the target may disappear with the worktree only
   when explicitly classified disposable AFTER their material facts are
   preserved.
2. No live owner/process — no active claim/lease owner on the lane, and no
   process (editor, test run, watcher, child executor) still executing in or
   against the worktree.
3. Inventory — full dirty + ignored + untracked inventory of the worktree is
   taken and every entry is accounted for: material evidence preserved outside
   the target (GitHub/tracked checkpoint or external evidence destination), or
   explicitly classified disposable with the reason recorded in the lane
   result.
4. Unique-commit/evidence preservation — every unique commit on the lane
   branch is reachable from an accepted ref or explicitly preserved elsewhere.
   A squash or rewritten merge does NOT preserve lane commits as ancestors of
   main: verify the unique work is evidenced in the squashed merge
   (diff/content check) or copied to a durable destination OUTSIDE the target
   worktree BEFORE removal.
5. Exact path identity — the path being removed is the exact registered
   worktree path for that lane per `git worktree list`, not a look-alike.

## Routing cleanup field

Every A-FastTask routing result carries exactly one cleanup state:
`CLEANUP_STATE=NOT_NEEDED|PENDING|BLOCKED|COMPLETE`. When cleanup is
`PENDING`, `BLOCKED`, or `COMPLETE`, include the exact target path plus the
reason/evidence that justifies that state. This is a report field only; it
grants no cleanup authority.

## Removal

Use the canonical command without force:

```
git worktree remove <exact-registered-path>
```

- `-f` / `--force` is FORBIDDEN in this workflow. A dirty or locked worktree
  is a `SAFE_TO_CLEANUP = NO` finding, not a reason to force.
- After removal, verify the path no longer appears in `git worktree list` and
  worktree admin metadata is consistent.

## Branch deletion is separate

Deleting the lane's branch is a LATER, separate decision requiring its own
merge/evidence check. Worktree removal never implies branch deletion.

## Scenario bindings

- Dirty merged lane => cleanup BLOCKED until the dirty state is explained and
  preserved/committed by its owner.
- Detached clean reviewer worktree => cleanup eligible ONLY after its
  review/result evidence is durably checkpointed OUTSIDE the target worktree
  or folded to GitHub/tracked authority; an ignored result inside the target
  worktree is NOT durable and does not satisfy the evidence precondition.
- Any live process, or any unknown dirty/untracked file =>
  `SAFE_TO_CLEANUP = NO` with the inventory and the exact next action.
