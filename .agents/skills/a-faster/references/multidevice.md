# A-Faster reference — multi-device / multi-harness lane matrix

This reference is an A-FastTask routing projection only. It grants no mutation,
provider, cleanup, merge, or acceptance authority.

## Lane matrix

| Surface | Typical role | Required proof before mutation/dispatch |
|---|---|---|
| SunDay-Worker 1..5 / Windows | code, docs, tests, Git/local files | exact project/worktree/branch/HEAD/task/claim/scope + dirty/process state |
| RDC / macOS | Mac filesystem, shell, repo/worktree, tests, CLI | exact device id + online/runtime truth + per-lane repo gate |
| GitHub connector | remote Issue/PR/SHA/CI/merge truth | callable authenticated connector + exact repo/ref |
| Kilo Code CLI (GLM-5.3 MAX) | R2/R3 implementation, complex repair, independent R3 review | fresh CoinTH quota/readiness + exact model route + durable pointer |
| Claude Code CLI (GLM-5.3 MAX) | R2/R3 implementation, complex repair, independent R3 review | fresh CoinTH readiness + exact `glm-5.3 --effort max` live route + durable pointer |
| Kilo Code CLI (GLM-5.3-Flash) | bounded read-only assist: reconnaissance, census assistance, dependency/scope scans, task-packet shaping, compatibility precheck, advisory pre-review | exact Flash route + durable pointer; no mutation authority; never satisfies a required MAX/qualified review |
| Claude Code CLI (GLM-5.3-Flash) | same bounded read-only assist classes | exact Flash live route + durable pointer; same no-authority limits |

A missing surface blocks only dependent work.

## Mandatory substantial-session readiness sweep

For every substantial A-Sunday Conductor engineering session, attempt READ-ONLY
readiness discovery for SunDay-Worker 1, 2, 3, 4 and 5 individually, plus RDC
device discovery. Record the actual result per surface. If a direct Worker tool
is not exposed in the current harness, record `PLUGIN_NOT_EXPOSED_TO_CHAT`
instead of claiming invocation. If both Windows and macOS are available and
independent READY scopes exist, prefer splitting work across devices; otherwise
keep work on the safe ready device.

All discovered Workers/devices share the same capacity below. Extra Workers are
standby/read-only/recovery helpers unless an actual global WIP slot is free.

## Global capacity

One project-wide budget:

`3 mutable + 1 independent read-only review`

All ChatGPT sessions, devices, and harnesses for the project share this one
budget. Each invocation reconstructs occupancy from durable evidence; a
session or tool timeout is not failure and never resets occupancy. Do not
allocate this budget independently on each machine or session.

## Safe parallel examples

- Windows lane edits A-Wiki docs; Mac lane edits a separate claimed SRM adapter
  in another worktree; review lane is read-only.
- Kilo owns one mutable scope while Claude Code owns a different mutable scope.
- Kilo authors; Claude Code performs read-only review after freeze.
- Two GLM-5.3 MAX authors run on two non-overlapping worktrees (M1/M2) while
  the R1 review lane reviews a frozen third candidate — each lane holds a
  different claimed hotspot, and the review target is an exact frozen SHA.
- A GLM-5.3-Flash lane assists read-only with census/pointer recovery,
  dependency/scope scans, or task-packet shaping; it obtains no mutation or
  acceptance authority, and the required independent R3 review still goes to
  a MAX/qualified reviewer.

## Unsafe examples

- Windows and Mac push edits to the same mutable branch at the same time.
- Kilo and Claude both edit the same hotspot because one appears idle.
- Reusing a branch/worktree after chat timeout without recovering the old run.
- Deleting a merged worktree whose ignored review/result files were never
  folded elsewhere.
- Stale PID reuse: a recycled OS PID happens to match the number recorded in
  an old pointer, and the session declares the old GLM runner `RUNNING`
  without matching creation/command identity — the census must treat a bare
  PID number as unknown, never as liveness proof.
- Duplicate redispatch after session loss: a fresh chat sees no result in its
  own context and relaunches the same packet although the prior session's GLM
  run is still RUNNING or TERMINAL_UNHARVESTED; census + harvest must come
  before any new dispatch.

## External advisory tools

Per-device desired state:

- `ponytail@ponytail` Claude Code plugin at user scope. Verify first; if
  missing and authorized, use the upstream two-step Claude flow:
  `/plugin marketplace add DietrichGebert/ponytail`, then
  `/plugin install ponytail@ponytail`.
- GitHub `JuliusBrussee/caveman` **skill-only** install. Verify first; when
  missing, `npx skills add JuliusBrussee/caveman -g` is the supported
  skill installer path. Do not install the optional proxy/engine just to meet
  A-Faster readiness.
- Preserve the device's existing local Grill Me skill. Never replace a
  customized `grill-me` merely to normalize devices; invoke it only when real
  intent/architecture ambiguity remains after tool/codebase/authority research.

Per-device installation must be independently verified. Windows installation is
not evidence of Mac installation. Advisory helper availability never grants
mutation, acceptance, merge, cleanup or provider authority.

## Cleanup proof

For each target path preserve:

- task/WO and claim release;
- merge/accepted ref evidence;
- unique-commit/content preservation proof;
- process liveness check;
- full dirty/untracked/ignored inventory disposition;
- exact registered worktree path.

Only then call non-force `git worktree remove <path>`.
