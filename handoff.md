# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-25 (Codex / GPT-5.6 Sol, WO-P1-063 installed release candidate)

## Current objective

Finish WO-P1-063 through final documentation CI, ready review, merge, fetch/rebuild/reinstall from main, repeated installed visual/interaction E2E, and final SSoT COMPLETE. Visual authority remains `DESIGN.md`; the user reconfirmed its wide near-black command-center reference on 2026-08-25.

## Repository / PR identity

- repository: `aase7en/A-Wiki-Conductor`
- active branch: `fix/terminal-command-center-completion`
- installed-candidate implementation HEAD: `e3d4babb78859b9d5e218354b0ea0b5d14129484`
- base `origin/main`: `9782f933426bbd5970e9e571545da89402c6a9ed`
- active Draft PR: **#79 — fix(ui): complete Sunday Family command center release**
- PR #77 is historical: GitHub marked it merged indirectly through PR #78 while it was still Draft and had no reviews. Do not resume or recreate its implementation.
- one implementation owner: Codex / GPT-5.6 Sol under WO-P1-063. GLM or another agent may review or take only a separately claimed disjoint task.

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

## Remaining release gates

1. Commit/push this bounded release-evidence checkpoint and require all three PR #79 jobs green on that exact documentation HEAD.
2. Mark PR #79 ready, review the final diff, and merge by repository convention only while checks remain green.
3. Fetch merged `main` into an isolated clean verification worktree.
4. Rebuild Portable + Setup from fetched `main`, repeat archive/frozen smoke, reinstall, and rerun the real installed logo/metrics/layout/language/copy/shutdown acceptance.
5. Update WO-P1-063, CURRENT-WORK, handoff, and COLLAB to COMPLETE in a final bounded documentation PR, merge it, then verify clean final `main`.

## Safety / known environment

- Live connectors are out of mutation scope; realistic connector tests use a temporary copied instance tree.
- ESET may temporarily lock fresh PE or `.ps1` files. Bounded retry is allowed; do not disable antivirus and do not change unrelated product behavior for that race.
- Never infer success from context/particle counts alone; the GPU health gate requires visible framebuffer output.
- Do not create another Tk root. Stop metric/logo callbacks and release the native context before destroying the root.
