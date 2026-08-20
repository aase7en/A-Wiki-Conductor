# Native Git Transaction Contract

Status: first bounded Git mutation layer
Owner: A-Conductor
Depends on: `native-execution-core.md`, `native-execution-adapters.md`

## Transaction model

Git mutation is never inferred from a stale chat/session view. The caller first obtains a `GitMutationSnapshot` containing:
- exact current HEAD;
- short-status result + full-output SHA-256;
- cached-diff result + full-output SHA-256.

A stage or commit request must provide all three expected values. The adapter re-observes immediately before mutation and refuses if any value differs. Drift is distinguished as HEAD, index, or status drift.

## Git read hardening used by transactions

Snapshot/read commands disable `core.fsmonitor` and Git diff commands disable both external diff and textconv execution. This prevents repository/global Git configuration from silently turning a read observation into external program execution.

## Stage

- Requires project mutation authority.
- Requires one or more explicit relative file pathspecs.
- `.` and directory pathspecs are refused to prevent blanket staging.
- Missing file pathspecs are allowed so an already-deleted tracked file can be explicitly staged; the adapter itself never deletes it.
- Paths are root-confined and passed after `--`.
- Before `git add`, the adapter uses `git check-attr filter` for the exact pathspecs. If any selected path activates a filter whose effective Git config defines `filter.<name>.clean` or `filter.<name>.process`, staging is refused. Merely having an unused global filter such as Git LFS installed does not block unrelated files.
- Mutation commands override `core.hooksPath` to a fresh empty temporary directory so stage cannot trigger Git hooks such as `post-index-change`.

## Commit

- Requires project mutation authority and exact preconditions.
- Requires a non-empty cached diff.
- Uses a fixed commit command with an empty temporary `core.hooksPath`, `--no-verify`, `commit.gpgSign=false`, and `--no-gpg-sign` for deterministic noninteractive execution.
- This suppresses pre/prepare/post commit hooks in the first implementation rather than silently trusting repository hook code.
- Hook/sign policy is deliberately deferred; it must not be silently enabled by model output.
- Commit success must change HEAD; otherwise the postcondition fails.

## Excluded Git families

No reset, clean, checkout/switch, stash, rebase, merge, cherry-pick, revert, push, fetch, pull, remote mutation, force option, or generic argv passthrough belongs to this adapter.
