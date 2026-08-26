# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-26 (GPT-5.6 Sol MAX — v0.7.0 integrator checkpoint)

## Current objective

Finish the bounded GE-6/GE-7 design PR, repair the GE-5 ReadySet conflict mismatch, then hand GE-6 production implementation to GLM. In parallel, publish the user-designated v0.7.0 release from exact candidate `be8a45d384b4679ff5c93230d06cbfc17a060b48`, perform installed/visual acceptance, and complete the requested UI design decisions/cleanup.

## Repository / worktree identity

- repository: `aase7en/A-Wiki-Conductor`
- shared `A:\GitHub\A-Wiki-Conductor` worktree: local `main` was clean but stale at `f4ecf9a`; **do not mutate/fast-forward it** because it is shared by workers.
- actual `origin/main`: `4956760765caab60ae8efe1a48d6edf807cdecce` after merged PR #96 (GE-5).
- v0.7.0 release candidate: **pin to `be8a45d384b4679ff5c93230d06cbfc17a060b48`**. Current main is intentionally not the release target because it contains later GE-5 plus a known readiness defect.
- active GPT design worktree: `A:\GitHub\A-Wiki-Conductor-ge-scheduler-design`, branch `docs/ge-scheduler-dispatch-design`, reconciled to `4956760` before docs mutation.
- Worker 1 transport terminated during read-only inspection; work was checkpoint-safe and continued on Worker 4 against the same worktree/branch. This is TRANSPORT_FAILURE, not task/code failure.
- A-Wiki is HOLD and was inspected only through authoritative GitHub read-only sources for the reuse gate; no A-Wiki mutation occurred.

## Graph Engineering state

Verified merged implementation:
- GE-1a/1b domain + acyclic assembly — PR #91.
- GE-2 durable graph SQLite store — PR #92.
- GE-3 Kahn DAG/ready levels/cycle naming — PR #94.
- GE-4 glob-aware hidden conflict analyzer — PR #95.
- GE-5 ReadySet — PR #96, CI green and merged, but a post-merge contract defect blocks GE-6 implementation until repaired.

Accepted design decisions:
- **ADR GE-0006:** event-driven/re-entrant deterministic scheduler core; no hot polling/background scheduler thread; current capacity policy `max_parallel=5`; worker capability/project/mutation-authority matching; same-batch + running conflict closure; pure SchedulePlan output only.
- **ADR GE-0007:** graph dispatch REUSE/WRAPs existing `DurableJobControlService`, `SQLiteJobStore`, `DurableJobExecutionCoordinator`, supervised execution, recovery, and dedup; dispatch identity includes `{graph_id, graph_run_id, node_id}`; no second lifecycle/store.
- A-Wiki brain bridge stays gate/policy seam only; A-Wiki agent-claim TTL is not Conductor execution-reservation ownership.

### Blocking GE-5 repair before GE-6 code

Merged `graph/ready.py` compares running write sets by literal equality while GE-4 is glob-aware. Example `src/**/*.py` vs `src/specific.py` can be incorrectly marked safe. Repair ticket: `docs/work-orders/WO-GE-005A-readyset-glob-conflict-repair.md`. Integrator evidence is recorded on PR #96 comment `5420827136`.

After that repair merges green, GLM may implement GE-6 from ADR GE-0006. GE-7 follows ADR GE-0007. Do not add scheduler workarounds for the GE-5 defect.

## Release state

- v0.6.0 remains published and verified historically.
- v0.7.0 is **not yet published** at this checkpoint.
- Exact candidate for v0.7.0 remains `be8a45d` as explicitly handed to the integrator; do not include later GE-5/design changes in that release merely because `main` advanced.
- PR #93 (`dab8f32`) singleton-dialog/release consolidation merged with Windows/Ubuntu/macOS CI green; PR #90 connector clarity and PRs #91–#95 graph/UI foundations are included as appropriate in the candidate line.

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
