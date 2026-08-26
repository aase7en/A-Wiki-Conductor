# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-26 (GPT-5.6 Sol MAX — GE design merged / v0.7.0 disk blocker)

## Current objective

Finish `WO-P1-071` PROJECT DISK async repair, merge it only with green CI, then publish v0.7.0 from the exact post-repair main SHA using clean CI artifacts plus sandbox installed acceptance. In parallel, GE-6 implementation may start immediately from the merged ADR GE-0006; GE-005A is a required merge gate before GE-6 production merge.

## Repository / worktree identity

- repository: `aase7en/A-Wiki-Conductor`
- actual `origin/main`: `15d2b26d959965ff7b32347326e02bbab1f60a8a` after PR #97 merge.
- shared `A:\GitHub\A-Wiki-Conductor` main worktree remains out of mutation scope.
- active release-blocker worktree: `A:\GitHub\A-Wiki-Conductor-disk-async`, branch `fix/project-disk-async-release`, base content includes PR #98 plus final PR #97 design head.
- release-audit worktree: `A:\GitHub\A-Wiki-Conductor-glm-release-audit`, detached at `6f7dfd5`; `.venv-audit/` is protected local tool state and must not be deleted.
- A-Wiki remains HOLD/read-only; no A-Wiki mutation occurred.

## Graph Engineering state

Verified merged implementation:
- GE-1a/1b domain + acyclic assembly — PR #91.
- GE-2 durable graph SQLite store — PR #92.
- GE-3 Kahn DAG/ready levels/cycle naming — PR #94.
- GE-4 glob-aware hidden-conflict analyzer — PR #95.
- GE-5 ReadySet — PR #96.
- GE-6/GE-7 design — PR #97 merged at `15d2b26`; Windows/Ubuntu/macOS CI green.

Accepted execution decisions now on main:
- **GE-0006:** deterministic event-driven/re-entrant scheduler core; `max_parallel=5`; worker capability/project/mutation-authority matching; running + same-batch GE-4 conflict closure; SchedulePlan output only.
- **GE-0007:** reuse/wrap durable job control, SQLite lifecycle, execution coordinator, supervised execution, recovery and dedup. Stable identity includes `{graph_id, graph_run_id, node_id}`.
- Current ChatGPT + Serena + Secure MCP Tunnel workers are **`INTERACTIVE_PULL`**: Conductor persists/offers/reserves work, and the AI in an active chat turn pulls/claims it and acts through Serena/tools. The tunnel is transport, not a server-push model-turn API.
- A local/headless/API surface with a documented invocation interface may be `PROGRAMMATIC_PUSH`.

**Immediate GLM handoff:** `GE-0006/0007 accepted — start GE-6 TDD now; GE-005A must merge before GE-6 production merge.`

GE-005A remains necessary because merged GE-5 compares running write-set strings literally while GE-4 is glob-aware. Do not add a third overlap algorithm in scheduler code.

## Release state / blocker

- v0.7.0 is **not published yet**.
- Exact `6f7dfd5` CI run `32935805411` was green and produced clean Portable/Setup artifacts, but that SHA is no longer safe to publish because PR #98's PROJECT DISK scan performs recursive `os.walk()` synchronously on the Tk UI thread.
- Real reproducer: scanning `A:\GitHub\A-Wiki-Conductor` took **52.1194 s** on this workstation; selecting/refreshing a project can therefore freeze the GUI.
- Active repair `WO-P1-071` moves the scan to a dedicated single-worker executor, separate from the existing one-worker lifecycle/monitor executor; adds cooperative cancellation, request-id/path stale-result guard, cache, pending `…`, and shutdown cleanup.
- Focused deterministic tests after implementation: **10 passed, 4 skipped** because the local audit venv has an unusable Tcl path. Exact GitHub Windows GUI CI is required before merge.
- Publish target becomes the exact **post-WO-P1-071 merged main SHA**, not `6f7dfd5` or older `be8a45d`.

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
