# A-Faster reference — multi-device / multi-harness lane matrix

This reference is an A-FastTask routing projection only. It grants no mutation,
provider, cleanup, merge, or acceptance authority.

## Lane matrix

| Surface | Typical role | Required proof before mutation/dispatch |
|---|---|---|
| SunDay-Worker 1..5 / Windows | code, docs, tests, Git/local files | exact project/worktree/branch/HEAD/task/claim/scope + dirty/process state |
| RDC / macOS | Mac filesystem, shell, repo/worktree, tests, CLI | exact device id + online/runtime truth + per-lane repo gate |
| GitHub connector | remote Issue/PR/SHA/CI/merge truth | callable authenticated connector + exact repo/ref |
| Kilo Code CLI | GLM-5.3 MAX bounded implementation/review | fresh CoinTH quota/readiness + exact model route + durable pointer |
| Claude Code CLI | GLM-5.3 MAX bounded implementation/review | fresh CoinTH quota/readiness + exact `glm-5.3 --effort max` live route + durable pointer |

A missing surface blocks only dependent work.

## Global capacity

One project-wide budget:

`3 mutable + 1 independent read-only review`

Do not allocate this budget independently on each machine.

## Safe parallel examples

- Windows lane edits A-Wiki docs; Mac lane edits a separate claimed SRM adapter
  in another worktree; review lane is read-only.
- Kilo owns one mutable scope while Claude Code owns a different mutable scope.
- Kilo authors; Claude Code performs read-only review after freeze.

## Unsafe examples

- Windows and Mac push edits to the same mutable branch at the same time.
- Kilo and Claude both edit the same hotspot because one appears idle.
- Reusing a branch/worktree after chat timeout without recovering the old run.
- Deleting a merged worktree whose ignored review/result files were never
  folded elsewhere.

## External advisory tools

Windows desired state for WO-P1-256:

- `ponytail@ponytail` Claude Code plugin, user scope;
- GitHub `JuliusBrussee/caveman` skill-only install;
- GitHub `JRA-CodingLab/grill-me` skill-only install.

Per-device installation must be independently verified. Windows installation is
not evidence of Mac installation.

## Cleanup proof

For each target path preserve:

- task/WO and claim release;
- merge/accepted ref evidence;
- unique-commit/content preservation proof;
- process liveness check;
- full dirty/untracked/ignored inventory disposition;
- exact registered worktree path.

Only then call non-force `git worktree remove <path>`.
