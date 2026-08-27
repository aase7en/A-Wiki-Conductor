# WO-P1-076 — Sunday Family v2 evidence

Date: 2026-08-27
Branch: `feat/north-star-runtime-sunday-family`
Relevant implementation: `63ac2fa feat(ui): refine Sunday Family particle motion`
Evidence capture HEAD: `131a8b2`

## Real WGL visual gate

- renderer: `gpu-opengl`
- production size: 120 px
- actual particles: 17,280
- framebuffer verified: true
- GPU error: none
- scheduled frame interval: 24 ms (~41.7 FPS ceiling)
- master asset: `assets/sunday-family-particle.png`

Deterministic framebuffer sweep (left -> right):
- face 1 centroid dx: +0.339 px
- face 2 centroid dx: +0.362 px
- face 3 centroid dx: +0.276 px
- chest/badge centroid dx: 0.000 px
- returned-neutral delta: 0.000 px

## Performance / lifecycle gate

10-second phases in the isolated real-WGL process:
- idle process CPU: ~5.779%
- active pointer process CPU: ~6.875%

5-minute continuous active stability:
- RSS delta from stability start to end: -1,572,864 bytes
- RSS observed span: 2,125,824 bytes
- no monotonic growth trend

12 repeated real WGL create/destroy cycles:
- post-destroy GDI span after warm-up: 0
- post-destroy USER span after warm-up: 0
- RSS cycle 2 -> cycle 12: +1,773,568 bytes
- combined with the 5-minute negative RSS delta, this is consistent with bounded allocator/cache warm-up, not cumulative renderer leakage.

Forced GPU-disabled fallback:
- renderer: `tk-canvas-fallback`
- Canvas items: 7
- Python particle ovals: 0
- 3-second active CPU: ~2.600%
- RSS delta during measured fallback phase: 0

## Visual fidelity conclusion

At 120 px, the GPU output keeps all three faces recognisable and preserves fine particle separation. A direct 120 px downscale of the master raster also makes the `Sunday Family` badge naturally tiny, so increasing particle count further would not recover source-resolution text detail; the current 17,280-point budget is retained instead of spending more GPU/CPU for negligible information gain.

Durable image evidence:
- `docs/evidence/WO-P1-076-motion-contact-sheet.png`
- `docs/evidence/WO-P1-076-gpu-neutral-5x.png`
- `docs/evidence/WO-P1-076-source-120-5x.png`

## Regression

Corrected repo-root focused regression:
`tests/test_gpu_particle_logo.py`, `test_interactive_logo.py`, `test_build_installer.py`, `test_desktop_ui.py`, `test_graceful_shutdown.py`, `test_system_metrics.py`, `test_splash.py`
-> **138 passed, 2 skipped**.

The two skips are local Tcl/Tk test-environment limitations. They are not WGL acceptance gaps: the real Windows WGL framebuffer test and the dedicated visual/resource harnesses above created a real Tk/WGL surface and passed.

Source-level verdict: **PASS**. Frozen/install comparison remains a release-integration gate unless it can be executed without changing the live installation or violating the v0.7 release boundary.
