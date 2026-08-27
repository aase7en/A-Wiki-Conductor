# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-27 (GPT-5.6 Sol — repo-health-100 / v0.7.0 closeout)

## Current objective

Finish `docs/repo-health-100`, merge it green, then publish v0.7.0 from that exact reconciled main SHA only after exact-artifact sandbox installation acceptance. Do not reconstruct release state from the old `be8a45d` checkpoint.

## Repository / worktree identity

- repository: `aase7en/A-Wiki-Conductor`
- shared `A:\GitHub\A-Wiki-Conductor` worktree: local `main @ f4ecf9a`, clean but stale; **do not mutate/fast-forward it** because it is shared.
- `origin/main` before repo-health-100: `f9dff0b1ad169af376d102018eb859cdbea36777` after PR #105.
- active GPT closeout worktree: `A:\GitHub\A-Wiki-Conductor-release-v070`, branch `docs/repo-health-100`, based on `f9dff0b1`.
- P5 `A-Wiki-Conductor-guide-html` worktree and `feat/interactive-html-guide` local/remote branch were verified merged via PR #105 and removed.
- old detached `A-Wiki-Conductor-glm-release-audit` worktree remains temporarily because it contains an untracked `.venv-audit/`; remove it only after v0.7.0 closeout if no protected content remains necessary.
- A-Wiki remains HOLD/read-only.

## Verified v0.7.0 implementation line

- PR #99 — async PROJECT DISK release blocker — merge `e8195b1d16799140068abb09297198df4a725149`.
- PR #100 — worker display name — merge `12a4c56db5704706ef3b2b25e291f2639627c05c`.
- PR #101 — live AI Execution Slots / ACTIVE vs BOUND project telemetry — merge `4ad0b8e48ecd07686d1c090aa8153215cbf4632f`.
- PR #103 — PROJECT DISK monochrome particle magnitude — merge `f85ee4763215bbf7c5bf7050f779ec5c48810727`.
- PR #105 — embedded offline HTML Guide — merge `f9dff0b1ad169af376d102018eb859cdbea36777`.
- Exact-main CI run `33005521278` for `f9dff0b1` passed Windows + Ubuntu + macOS; Windows passed GUI/core suites, clean Portable/Setup build, frozen archive verification, Portable executable smoke, and artifact upload.

## Graph Engineering state

Merged foundation remains GE-1a/1b through GE-5 on historical main, but two GLM follow-up branches are intentionally **not** part of v0.7.0:
- PR #102 `fix/ge-005a-glob-conflict` — OPEN; Windows CI FAILURE; Ubuntu/macOS SUCCESS.
- PR #104 `feat/ge-6-scheduler` — OPEN; Windows CI FAILURE; Ubuntu/macOS SUCCESS.

Do not delete their worktrees/branches and do not merge them into the release until their own Windows gates are green and their PRs are re-audited.

## Release state

- v0.6.0 remains published historically.
- v0.7.0 is **not yet published**.
- The old `be8a45d` candidate pin is superseded by later user-authorized P1 release work (#99/#100/#101/#103/#105). The final target will be the **exact merge SHA of repo-health-100**, not a moving `main`.
- After repo-health-100 merges green: download Windows artifacts from the CI run for that exact SHA, record hashes, sandbox-install with `--target`, verify installed/frozen behavior without touching live ports 18011–18015, then publish v0.7.0 and verify public assets.

## Verified source state

- Exact brand authority remains `assets/sunday-family-particle.png`.
- Real WGL path: `gpu-opengl`, about 9,360 fine particles, meaningful non-black framebuffer, `GPU_ERROR=None`.
- GPU-disabled path: same master portrait resized once; one Canvas image plus six optional amber eye accents, seven Canvas items total and zero particle ovals.
- Pointer sweep is gentle and returns neutral after leaving the app. Face parallax is lower than gaze; eye-local repulsion is masked.
- Twelve repeated real WGL create/destroy cycles: all native unbind/delete calls returned success after warm-up, GDI/USER counts stayed stable, and no Tk callback errors occurred.
- Real metrics sample populated CPU, RAM, uptime, and bounded CPU history; values are sampled at runtime and never hard-coded.
- Real layouts passed at 700, 900, 1280, 1600, and maximized. Compact workflow wraps; 900+ remains one row. Compact System Overview shortens captions without hiding the first selectable Worker row.
- Add Brain, Add Connector, ordered English actions, TH/zh-CN/EN guidance, copyable read-only logs, assignment replacement, Donate/Check Update, and shutdown/lifecycle contracts remain covered.
- Full repository regression before the final bounded shutdown optimization: **1175 passed**; its focused regression and subsequent GitHub full matrix are green.
- Real-system sandbox E2E: **23 passed**, one network-only test deselected.
- Focused UI/workflow run: **115 passed**, one local portable-Tk environment skip; equivalent GUI coverage also passed inside the clean full suite.

## Fresh package evidence

- Portable: 24,285,453 bytes; SHA-256 `FF55C476BF4FFA852CB78545EFA12EC69399F2E70D28432B303CB69EEE98BD15`.
- Setup: 31,222,411 bytes; SHA-256 `26CEE072C2FFDAF934B11C47CB1D5D5D4CFE67D4CAD1032988E34BE2FA2D2D7D`.
- Frozen Portable smoke: exit 0; isolated SQLite DB created.
- Recursive archive inspection includes both Sunday assets, `a_conductor.gpu_particle_logo`, `a_conductor.system_metrics`, ModernGL/WGL, pyopengltk/PyOpenGL, Pillow imaging, `_tkinter`, Tcl, and Tk.
- Setup archive contains payload branding v0.6.0, Portable executable, guides, notices, and icon without duplicating the full UI/OpenGL graph.
- Windows CI now builds, inspects, smokes, and uploads Portable + Setup. A path-separator false-failure was found locally and fixed by normalizing archive member names before comparison.
- Final implementation run `32789507743` passed Windows test/build/archive/frozen-smoke plus Ubuntu and macOS smoke at `e3d4bab`. Earlier virtual-WGL and archive-separator failures were classified and fixed rather than retried blindly.

## Installed acceptance

- Setup completed on its first attempt; installed executable hash exactly equals the Portable hash and HKCU registration reports A-Sunday Conductor v0.6.0.
- User DB physical hash remained unchanged across install and its logical rows remain identical to the consistent pre-test backup; all five live connectors stayed `STOPPED`.
- Real installed 1096×719 window directly compared with the user-reconfirmed reference: detailed Sunday Family portrait visible, terminal hierarchy/density retained, Add Brain/Guide/Settings reachable, ordered English actions intact, and real CPU/RAM/uptime populated.
- Installed GPU, forced Canvas fallback, 700/900/1280/1600/maximized layouts, pointer return, TH/zh-CN/EN, Add Connector, copy logs, and safe workflow behavior were exercised on the same release line before the shutdown-only final commit.
- Closing during sandbox autostart created the forced-stop marker and removed both PyInstaller processes. The new no-redundant-probe regression is green; source close measured 4,361 ms and final installed close was bounded at 9,235 ms on the security-filtered workstation.

## Staff-review result

All six prior FIX FIRST findings are resolved: activity clipping, material GPU framebuffer threshold, compact brand fallback, stale pointer neutralization, live Copy Path localization, and combined eye displacement. Remaining native cleanup concern was closed by repeated real WGL evidence. The installed shutdown timing finding was also fixed test-first by skipping only the redundant pre-force probe; an independent skeptical review returned GO.

## Release closeout

The v0.6.0 release gates above are complete. This handoff is the bounded continuity closeout after release publication. The only remaining administrative action for this branch is its own docs-only PR/CI/merge; after that, fetch `origin/main` and verify the repository is clean. The v0.6.0 tag intentionally remains pinned to the verified implementation/release SHA `c8705257344ab6b2890e198074118f028cefdbcf`; continuity-only commits may advance `main` afterward.

## Safety / known environment

- Live connectors are out of mutation scope; realistic connector tests use a temporary copied instance tree.
- ESET may temporarily lock fresh PE or `.ps1` files. Bounded retry is allowed; do not disable antivirus and do not change unrelated product behavior for that race.
- Never infer success from context/particle counts alone; the GPU health gate requires visible framebuffer output.
- Do not create another Tk root. Stop metric/logo callbacks and release the native context before destroying the root.
