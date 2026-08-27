# WO-P1-076 — Sunday Family fidelity + gaze/head motion v2

Status: FROZEN_ACCEPTED
Owner: GPT-5.6 Sol
Branch: `feat/north-star-runtime-sunday-family`
Base: `c72a550287a8c59d2361112b489e528639adeaa6`

## Trigger

User acceptance on 2026-08-27 explicitly reopens the Sunday Family visual work: the portrait still needs finer visible particles and convincing but gentle eye/head pointer-follow. This newer acceptance signal overrides prior closeout claims that the logo was complete.

## Goal

Make the master Sunday Family portrait materially more detailed at the real 120 px header size while remaining lightweight, and make each face/head react locally to pointer direction instead of translating the entire portrait as one flat image.

## Authority / constraints

- Master asset remains `assets/sunday-family-particle.png`.
- Tk/Ttk desktop architecture remains; GPU work stays bounded to the logo.
- GPU path performs particle displacement in the shader; no per-particle Python animation loop.
- Canvas fallback remains deliberately cheap: one raster + at most six eye accents.
- No periodic subprocess, network call, filesystem walk, or second Tk root.
- Motion must stay subtle/non-uncanny and return to neutral after pointer leave.

## Acceptance criteria

1. Normal 120 px GPU budget is adaptive and materially denser than the prior ~9,360-point baseline while remaining bounded by `GPU_MAX_PARTICLES`.
2. Particle points remain fine; density must not be faked with larger dots.
3. Six eye regions retain weighted gaze; combined eye movement remains <= 3 px at 120 px.
4. Three face/head regions receive smooth local parallax in the pointer direction; chest/badge/background particles remain substantially anchored.
5. Face/head movement target is about 1–2 px at 120 px and remains less than gaze.
6. Pointer leave decays both gaze/head response to neutral without stale re-entry.
7. GPU framebuffer health gate still proves observable output.
8. GPU-disabled family fallback stays bounded to <= 7 Canvas items and remains responsive.
9. Existing packaging, lifecycle cleanup, and terminal command-center behavior regressions stay green.

## Verification

- RED tests first for local face weighting, denser adaptive particle budget, and motion bounds.
- Targeted: `pytest -q tests/test_gpu_particle_logo.py tests/test_interactive_logo.py`.
- Real Windows WGL framebuffer test when available.
- `git diff --check`.
- Independent diff review before merge.

## Forbidden scope

- Do not touch GE-005A / GE-6 graph code or their worktrees.
- Do not mutate A-Wiki.
- Do not merge this branch into `main` before the pinned v0.7.0 release closeout completes.

## Checkpoint — 2026-08-27

Implementation is locally verified on the isolated North Star worktree.

- TDD RED: missing `adaptive_particle_budget` and `_face_weight` failed exactly as expected (2 failed).
- GPU vertex contract extended from 5 to 6 floats with local `face_weight`.
- Three soft elliptical head regions now drive shader parallax; chest/badge/background remain anchored.
- 120px budget: 17,280 actual particles, 414,720-byte packed vertex buffer, one-time source build ~205.7 ms on this workstation.
- Head parallax ~0.96 px, gaze ~1.68 px, combined head+gaze+idle <=3 px at 120px.
- Explicit North Star source test: 45 passed, 1 Tk-environment skip.
- `compileall` PASS; `git diff --check` PASS.

Status: LOCAL_VERIFIED — independent review / visual installed acceptance still required before merge.

## Source acceptance checkpoint — 2026-08-27

Status: SOURCE_ACCEPTED. Real Windows source-renderer acceptance is complete; frozen/install comparison remains an N8 release-integration gate unless it can be executed without disturbing the live install or v0.7 release boundary.

Evidence is durable in `docs/evidence/WO-P1-076-sunday-family-v2.md` plus three framebuffer comparison PNGs.

Key results:
- real WGL: `gpu-opengl`, 17,280 particles, framebuffer verified, no GPU error;
- deterministic left/right sweep: all three face regions move locally while chest/badge stays at 0.000 px translation and return-neutral is 0.000 px;
- 5-minute active stability: RSS delta -1,572,864 bytes, no monotonic growth;
- 12 create/destroy cycles: post-warm GDI and USER spans both 0;
- forced fallback: 7 Canvas items, 0 particle ovals, bounded CPU/RSS;
- corrected repo-root focused regression: 138 passed, 2 local Tcl/Tk environment skips;
- no evidence-backed reason to increase density beyond 17,280 at 120 px; the direct master raster downscale is itself pixel-limited at badge text size.

No further source/UI tuning is justified without new visual acceptance evidence. Do not widen scope merely to make motion more noticeable; current movement is deliberately subtle/non-uncanny by design.

## Frozen / sandbox-installed checkpoint — 2026-08-27

Status: FROZEN_ACCEPTED. Build HEAD before evidence-only edits: `4f5c9a9a9ab773ca8ca16a1255ebc56026b59d3f`.

- Portable build: 31,143,854 bytes; SHA-256 `fa7e324e74539b4856d53177239589991bcb0ceca975761fc7ff640f77ce477b`.
- Frozen isolated smoke: `A-CONDUCTOR_SMOKE_OK projects=0 workers=3`, exit 0.
- Setup build: 38,098,517 bytes; SHA-256 `43dc50f5e1f43ad4f48e5ff9481821def5146423bf0449f760249b3ed5cc0ec9`.
- Setup archive contains the Portable payload, guides, notices, icon and installer branding metadata.
- Sandbox-installed executable hash exactly equals the Portable hash; isolated installed smoke passed.
- Direct installed GUI capture opened `A-Sunday Conductor v0.7.0` at 1096x719, rendered the Sunday Family header + real command-center metrics, and closed cleanly.
- Verification deliberately avoided running Setup integration against the user's live Start Menu/registry/install; the payload was materialized under `C:\Temp` instead.

Durable evidence: `docs/evidence/WO-P1-076-sunday-family-v2.md` and the frozen/installed window PNGs.

N1 implementation + source + WGL + resource + fallback + frozen/sandbox-installed acceptance are complete. Independent final PR review/CI remain N8 integration gates; do not reopen visual tuning without new user-visible evidence.
