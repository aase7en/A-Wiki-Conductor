# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-25 (Codex / GPT-5.6 Sol, WO-P1-063 release validation)

## Current objective

Finish WO-P1-063 through current-HEAD CI, safe installed upgrade, installed visual/interaction E2E, ready review, merge, fetch/rebuild/reinstall from main, and final SSoT COMPLETE. Visual authority remains `DESIGN.md`.

## Repository / PR identity

- repository: `aase7en/A-Wiki-Conductor`
- active branch: `fix/terminal-command-center-completion`
- pushed implementation HEAD before this SSoT checkpoint: `8abf2bfcb62dc435a39765d7c0e8552f50578290`
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
- Full repository regression: **1166 passed**.
- Real-system sandbox E2E: **23 passed**, one network-only test deselected.
- Focused UI/workflow run: **115 passed**, one local portable-Tk environment skip; equivalent GUI coverage also passed inside the clean full suite.

## Fresh package evidence

- Portable: 24,282,484 bytes; SHA-256 `DB4921146FABA1E774B56F342EDE8178EADA3782DC59F669BB513D570206B0CA`.
- Setup: 31,219,212 bytes; SHA-256 `F5C676406C36E265EE293721FB977DFB8C740B52E076BD58AC71A0A851D67574`.
- Frozen Portable smoke: exit 0; isolated SQLite DB created.
- Recursive archive inspection includes both Sunday assets, `a_conductor.gpu_particle_logo`, `a_conductor.system_metrics`, ModernGL/WGL, pyopengltk/PyOpenGL, Pillow imaging, `_tkinter`, Tcl, and Tk.
- Setup archive contains payload branding v0.6.0, Portable executable, guides, notices, and icon without duplicating the full UI/OpenGL graph.
- Windows CI now builds, inspects, smokes, and uploads Portable + Setup. A path-separator false-failure was found locally and fixed by normalizing archive member names before comparison.
- PR #79 run `32783280486`: Ubuntu/macOS passed; Windows generic GUI tests access-violated inside ModernGL while creating the hosted runner's virtual WGL context. This is a runner/platform incompatibility before Python fallback, not a product assertion. The Windows CI job now explicitly exercises Canvas fallback; real WGL remains covered by workstation and installed-app E2E.

## Staff-review result

All six prior FIX FIRST findings are resolved: activity clipping, material GPU framebuffer threshold, compact brand fallback, stale pointer neutralization, live Copy Path localization, and combined eye displacement. Remaining native cleanup concern was closed by the repeated real WGL evidence above.

## Remaining release gates

1. Wait for PR #79 checks on the final documentation HEAD; inspect exact failures before any retry or fix.
2. Before Setup, set/confirm `shutdown_stops_instances=false`, close only the installed A-Sunday Conductor process, and verify live connector processes remain untouched.
3. Hash and copy the user DB at `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`.
4. Run the fresh Setup and require exit 0; verify installed executable hash equals the fresh Portable hash and DB hash remains unchanged.
5. Launch the actual installed shortcut/binary and verify logo/GPU/fallback, real metrics, responsive layouts, Add Brain, Add Connector, copy logs, language switching, assignment/workflow safety, and clean shutdown.
6. Mark PR #79 ready, perform final diff/review, require all checks green, merge by repository convention, and fetch main.
7. Rebuild/reinstall from fetched main and repeat the installed acceptance smoke.
8. Update WO-P1-063, CURRENT-WORK, handoff, and COLLAB to COMPLETE in a final bounded documentation PR if post-merge evidence is not already representable in #79.

## Safety / known environment

- Live connectors are out of mutation scope; realistic connector tests use a temporary copied instance tree.
- ESET may temporarily lock fresh PE or `.ps1` files. Bounded retry is allowed; do not disable antivirus and do not change unrelated product behavior for that race.
- Never infer success from context/particle counts alone; the GPU health gate requires visible framebuffer output.
- Do not create another Tk root. Stop metric/logo callbacks and release the native context before destroying the root.
