# WO-P1-073 — PROJECT DISK monochrome particle magnitude

Status: REVIEW
Owner: GPT-5.6 Sol
Depends on: WO-P1-071 merged (`e8195b1`), WO-P1-072 merged (`4ad0b8e`)
Branch: `feat/project-disk-particle-visual`

## Objective

Upgrade the exact PROJECT DISK text metric with a compact monochrome terminal-style
particle strip without changing filesystem sampling semantics.

## User outcome

The operator still sees the authoritative exact size (for example `1.0 GB`) and gains
a quiet visual cue for order-of-magnitude. The dots are not disk-capacity percentage.

## Invariants

- Exact text remains authoritative.
- 24 bounded dots; no GPU and no animation loop.
- Visual scale is logarithmic magnitude, not `% full`.
- Renderer consumes the already-computed async/cached display value only.
- No new filesystem walk, subprocess, timer, background thread, or network call.
- `—`, `…`, and malformed values render fail-closed/dim.
- Tk rendering is UI-thread only and must tolerate destroyed/unavailable widgets.
- Monochrome colors derive from the existing theme foreground/muted/border palette.
- Tooltip explains the log-magnitude semantics.

## Test seams

1. Pure `disk_particle_levels()` mapping is monotonic from KB→MB→GB→TB and bounded.
2. Unavailable/malformed values produce 24 zero levels.
3. GUI renderer creates at most 24 particle marks and redraws from the same display value.
4. Existing async/stale-result PROJECT DISK tests remain green.
5. GUI usability suite remains green.

## Local evidence

- Pure folder-size/particle mapping: `11 passed`.
- Focused i18n + disk async + particle GUI: `34 passed`.
- System Python 3.13 + real Tk focused GUI: `17 passed`.
- Broad desktop UI/usability suite: `113 passed`.
- `py_compile` and `git diff --check`: PASS.
- Finite Tk visual capture: `CAPTURE_OK` at 1080x680; capture kept out of public Git history.

## Acceptance

- [x] Focused unit + GUI tests green.
- [x] `git diff --check` clean.
- [x] Real UI visual capture produced at desktop size (1080x680); final CI/merge remains pending.
- [ ] PR remote diff audited.
- [ ] Windows/Ubuntu/macOS CI green before merge.
- [ ] Post-merge fetch/reconcile and branch/worktree cleanup.
