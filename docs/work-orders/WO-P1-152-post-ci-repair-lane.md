# WO-P1-152 post-CI repair lane

Status: RED_FIRST
Owner: GPT-5.6 Sol MAX
Base candidate: `d5dae16281d2927aef92273e82190f56027d6919`
Branch: `fix/wo-p1-152-post-ci-boundary-repair-gpt`

This is an isolated temporary repair lane for PR #204. It must not be merged to `main` directly.

Temporary allowed scope:
- `src/a_conductor/aipass_discovery.py`
- `tests/test_aipass_discovery_post_ci_repair.py`
- this repair-lane checkpoint file

The temporary focused test file must be folded into `tests/test_aipass_discovery.py` and this checkpoint removed before the final WO152 candidate is accepted. Final PR #204 scope remains the original three files.

RED families:
1. quoted/object-shaped generic credentials;
2. canonical `configuration_generation` upper bound;
3. embedded public endpoint tokens in display metadata;
4. endpoint-shaped model IDs with dotted-model positive controls;
5. huge integer stale-budget OverflowError escape;
6. extreme timezone-aware UTC-normalization OverflowError escape.

No live AiPASS traffic, credential resolution, provider mutation, readiness/auth/admission/execution authority, Worker/tunnel maintenance, or shared SSoT mutation is authorized.

Next: hosted RED proof -> minimal decoder repair -> focused/broad verification -> exact-SHA independent review. If base/head drifts, stop and re-pin.