# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-26 (GPT-5.6 Sol release closeout)

## Current objective

v0.6.0 release work is complete. Resume Graph Engineering under `docs/work-orders/WO-GE-001-graph-engineering-kickoff.md`, beginning with **GE-1a only**. D1-D5 are accepted; no scheduler implementation is authorized yet. Exact GLM handoff phrase: `D1-D5 ตกลงแล้ว อ่าน WO-GE-001`.

## Repository / release identity

- repository: `aase7en/A-Wiki-Conductor`
- verified v0.6.0 release target: `c8705257344ab6b2890e198074118f028cefdbcf`
- GitHub Release: `https://github.com/aase7en/A-Wiki-Conductor/releases/tag/v0.6.0`
- published: 2026-08-26 Thailand date; six assets present.
- final-main release CI: run `32902558101` — Windows full tests, Portable+Setup build, archive verification, frozen smoke, Ubuntu smoke, macOS smoke all green.
- release-triggered SignPath run `32904214805`: success; signing step no-op'd as designed because `SIGNPATH_API_TOKEN` is not configured.
- release integration PRs merged: #85 PowerShell/BOM/path+CI isolation, #86 GE D1-D5, #87 GPU/Tk repaint corrective fix, #88 v0.6.0 changelog.
- real workstation GPU regression after corrective fix: **19/19 passed**.
- Portable: 24,872,490 bytes; SHA-256 `9432D96E867C486D012AA797C3D764103AABEAA97D8F2C068FAD9D84BAD3AC87`.
- Setup: 32,653,155 bytes; SHA-256 `DF9C61214C235C6386761F177E0F7154885B3DB6614B0B890948B8685163F261`.
- GitHub Actions artifact ZIP digest: SHA-256 `6f06f82044626cc29c9282f1e9a36ee035938ac37a2cca84e9165a8d8df02f49`.
- ESET temporarily locked fresh PE/.ps1 files during local audit/upload. Bounded retry worked; antivirus was not disabled and no unrelated product fix was made for the host race.
- A-Wiki brain repo remains HOLD / untouched for this release work.

## Graph Engineering handoff

D1-D5 are accepted in ADRs GE-0001..GE-0005 via PR #86:
- D1: port A-Wiki `dag_eval` semantics with attribution; no runtime dependency on an A-Wiki checkout.
- D2: graph fields are Conductor-owned; `awiki-task/v1` remains unchanged; dependency relations live in `TaskEdge`/`TaskGraph` rather than duplicated nested TaskNode fields.
- D3: A-Wiki access is bridge-only; direct `.tmp` / `scripts.lib.*` coupling is forbidden.
- D4: retain all 12 DependencyTypes with guardrails; dynamic/resource relations are not blindly persisted as precedence edges; `HUMAN_APPROVAL` is a readiness gate; no cycle exemptions/back-edges.
- D5: first implementation PR is **GE-1a only** (`a_conductor/graph/domain.py` + `tests/test_graph_domain.py`), then GE-1b and GE-3. GE-6/GE-7 remain gated.

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
