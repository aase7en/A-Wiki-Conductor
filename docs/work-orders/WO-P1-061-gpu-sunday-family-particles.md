# WO-P1-061 — GPU Sunday Family Particle Portrait

Created: 2026-08-24 · Owner: GPT-5.6 Sol + SunDay-Worker 2 (resumed from Workers 4/5) · Status: LOCAL_VERIFIED — FINAL_CI_PENDING

## Goal

Upgrade the A-Sunday Conductor desktop header portrait from a CPU Tk Canvas
prototype to a native GPU/OpenGL particle renderer while keeping the application
a normal installable desktop `.exe` (not a WebView/Web app).

The source image is `assets/sunday-family-particle.png` (1448×1086): monochrome
white particles on black, with the `Sunday Family` particle label and framed
margin already baked into the chest area.

## User-required interaction

- Preserve the detailed family particle portrait.
- Mouse proximity distorts/repels nearby particles in the style of the supplied
  CodePen particle-image reference.
- Pointer velocity adds a short tangential trail/swirl response.
- Six family eye regions subtly look toward the mouse while the pointer is
  anywhere inside the A-Sunday Conductor window.
- Idle portrait remains alive with very small organic drift.
- Black background + white/neutral-gray particles only; no cyan/orange/accent colors.
- Fine/small dots preserve maximum recognizable fidelity to the source asset.
- `Sunday Family` label/frame must not cover faces.

## Implementation boundary

- Keep Tkinter as the desktop application shell.
- Embed native OpenGL through `pyopengltk`; shader/buffer API through ModernGL.
- GPU renderer is isolated in `src/a_conductor/gpu_particle_logo.py`.
- Existing `InteractiveLogo` remains the safe Tk Canvas fallback.
- No browser, WebView, Electron, or Three.js runtime is introduced.
- Windows installs receive GPU dependencies; unsupported platforms retain the
  fallback path.

## Repository identity

- Reconciled baseline: `main` @ `a3868c45b2e75ffee0aedc06e3038cfe7be86b5b`
  (PR #76 merged the prior `fix/ui-panel-sizing-logo` branch).
- Working branch: `feat/gpu-sunday-family-particles-clean` from `main` @ `5b77d112`.
- Prior mixed branch was not merged wholesale; only WO-owned files were recovered.

## Dependencies

- `Pillow>=10`
- `moderngl>=5.12` on Windows
- `pyopengltk>=0.0.4` on Windows

The GPU dependencies were first verified via an ephemeral `uv run`; no
machine-wide environment was changed.

## Acceptance criteria

1. Real Tk/OpenGL smoke reports `renderer = gpu-opengl` with the family asset.
2. The 120px production widget uses an adaptively bounded particle count so dots
   remain visibly separated instead of collapsing into a white mass.
3. Mouse repulsion, velocity trail/swirl, gaze tracking, and idle drift are
   executed by the GPU shader; no per-particle Python animation loop on GPU path.
4. If imports/context/shader/buffer creation fails, the app falls back to
   `InteractiveLogo` without crashing.
5. The baked `Sunday Family` label is not duplicated by the Canvas fallback.
6. Asset is bundled by the existing portable build asset rule.
7. Targeted tests, packaging validation, and `git diff --check` pass.
8. CURRENT-WORK.md and handoff.md record final evidence before PR/merge.

## Evidence so far

- Asset verified: PNG 1448×1086; bright-pixel chroma average ~3.12, max 35, so the source is effectively grayscale.
- Family asset is explicitly classified monochrome by contract in the Tk fallback; neutral fallback color is `#f2f2f2` (`R=G=B`).
- GPU fragment output is `vec3(intensity)` and point size was reduced for fine separated dots; gaze changes geometry, not color.
- Real native OpenGL E2E after final tuning: PASS.
  - renderer: `gpu-opengl`
  - production 120px particles: 9,360
  - GPU error: none
- Forced GPU-disabled fallback E2E: PASS.
  - renderer: `tk-canvas-fallback`
  - particles: 2,600
- GPU shutdown cleanup fixed: pending pyopengltk `after()` display callback is cancelled before widget destruction; clean-destroy smoke PASS.
- Targeted particle regression after grayscale fix: 16 passed, 3 environment skips (Tk/GPU availability only).
- Python compile + `git diff --check`: PASS.
- Portable PyInstaller build: PASS, `A-Sunday Conductor.exe` 24,153,546 bytes (~24.15 MB).
- PyInstaller TOC confirms bundled `assets/sunday-family-particle.png`, `a_conductor.gpu_particle_logo`, ModernGL native module, and `pyopengltk`.
- Fresh frozen `--smoke` on this workstation: BLOCKED_LOCAL_SECURITY (`Access is denied`), matching the repository's existing ESET/fresh-PE lock pattern. Final frozen/full-suite authority is GitHub CI; do not alter production behavior to bypass local antivirus.

## Next safe action

Freeze WO-P1-061 implementation, checkpoint it in Git, transfer shared UI ownership to WO-P1-062, then run final combined GitHub CI after the responsive UI work. WO-P1-061 is not marked merged/DONE until that CI is green.

## Resume checkpoint — 2026-08-24 Worker 5

- Reconciled actual repo: clean `main` @ `5b77d11` before resume.
- Prior GPU work verified present in local branch `feat/gpu-sunday-family-particles`, but that branch also contained unrelated monitor-performance commits and tracked `.pytest-*` artifacts.
- Created clean branch `feat/gpu-sunday-family-particles-clean` from latest main and recovered only WO-P1-061-owned files.
- Added explicit WO-P1-061 claim in `COLLAB.md`.
- Next safe action: run deterministic targeted regression + real OpenGL smoke, then package/build/E2E review.
