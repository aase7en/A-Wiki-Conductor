# Native Git Transaction Contract

Status: first bounded Git mutation layer
Owner: A-Conductor
Depends on: `native-execution-core.md`, `native-execution-adapters.md`

## Transaction model

Git mutation is never inferred from a stale chat/session view. The caller first obtains a `GitMutationSnapshot` containing:
- exact current HEAD;
- short-status result + full-output SHA-256;
- cached-diff result + full-output SHA-256.

A stage or commit request must provide all three expected values. The adapter re-observes immediately before mutation and refuses if any value differs.

## Stage

- Requires project mutation authority.
- Requires one or more explicit relative file pathspecs.
- `.` and directory pathspecs are refused to prevent blanket staging.
- Missing file pathspecs are allowed so an already-deleted tracked file can be explicitly staged; the adapter itself never deletes it.
- Paths are root-confined and passed after `--`.

## Commit

- Requires project mutation authority and exact preconditions.
- Requires a non-empty cached diff.
- Uses a fixed commit command with repository hooks skipped and GPG signing disabled for deterministic noninteractive execution.
- Hook/sign policy is deliberately deferred; it must not be silently enabled by model output.

## Excluded Git families

No reset, clean, checkout/switch, stash, rebase, merge, cherry-pick, revert, push, fetch, pull, remote mutation, force option, or generic argv passthrough belongs to this adapter.
