# WO-P1-127 — Provider Edit / Disable / Test

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: RELEASED / MERGED / POST_MAIN_GREEN
Priority: P1 AHA-7B
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo127-provider-actions`
Branch: `feat/wo-p1-127-provider-actions`
Base: `origin/main@9118a289b9fcd87e0bae4e4eb601cc585062856d`

## Goal

Extend the accepted WO126 `MODELS & AGENTS` Settings panel with bounded provider Edit, Disable/Re-enable, and Test actions. Reuse the retained canonical provider store, existing CAS/in-use fencing, accepted observation refresh path, background executor, Tk scheduler, typed errors and i18n.

## Hard non-goals

- no provider delete;
- no `provider_id`, `endpoint_ref`, endpoint or `base_url` mutation;
- no credential resolution/prefill/reveal in UI;
- no new provider store/schema/router/policy/readiness/quota authority;
- no direct network/subprocess from Tk;
- no live Worker/tunnel or WO096 mutation.
## Mutable scope

- `src/a_conductor/desktop_control.py`
- `src/a_conductor/desktop_ui.py`
- `src/a_conductor/error_explanations_en.py`
- `src/a_conductor/i18n.py`
- `tests/test_desktop_control.py`
- `tests/test_models_agents_panel.py`
- `tests/test_i18n.py`
- optional new `tests/test_provider_operator_actions.py`
- bounded `CHANGELOG.md`, `docs/USER-GUIDE.md`, `docs/USER-GUIDE-EN.md`
- this work order only; shared SSoT remains owned by PR #181 until released.

## Forbidden scope

- `provider_config_store.py` (owned by parallel WO128 GLM lane)
- `provider_configuration.py`, `provider_policy.py`, `provider_operator_view.py`
- `provider_runtime_assembly.py`, `zai_quota_probe.py`, `awiki_environment_resolver.py`
- scheduler/parallel/worker/elastic/graph/job/execution source
- `CURRENT-WORK.md`, `handoff.md`, `AGENT_TASKS.md`, README, `DEFECT_LESSONS.md`
- credentials/private Drive data, release/version files.
## Required semantics

1. Edit uses exact expected configuration generation; stale conflict is typed and never blind-retried.
2. Active/expired provider admission refuses configuration mutation through existing store fence.
3. Disable/re-enable is a CAS update; disabled remains configured and truthfully not ready.
4. Mutable profile fields exclude provider/endpoint identity and base URL. Credential reference may only be repointed as a string and is never resolved or displayed after save.
5. Test runs asynchronously through the accepted provider observation refresh path; supported routes persist generation-bound health/quota evidence.
6. Unsupported routes render `UNSUPPORTED`, not pass/fail fiction.
7. A concurrent edit during Test makes the old observation completion generation-stale.
8. Missing/corrupt provider targets fail typed; no partial or best-effort mutation.
9. Close/reopen/stale future completion cannot touch destroyed or newer UI.
10. Every action is text/keyboard reachable and preserves `CONFIGURED != READY != AUTHORIZED`.

## Verification

RED-first facade tests → smallest facade implementation → GUI RED/tests → async/adversarial tests → provider/UI impact matrix → compileall → diff-check → strict UTF-8/secret/scope audit → self-review → independent exact-head review → PR/CI → re-audit → merge/post-main.

P0/P1/P2 block merge. Agent or test PASS alone is not merge authority.


## Checkpoint ? 2026-09-02 local verification

- RED proved missing facade actions and missing GUI controls before production edits.
- Facade/adversarial WO127 tests: **13 passed** on Python 3.13.
- Provider/store/runtime impact matrix: **162 passed** in the isolated test-extra environment.
- GUI/i18n/action bucket: **115 passed** on Python 3.13 with working Tk.
- Models & Agents focused GUI after hardening: **15 passed**; i18n/error focused: **2 passed**.
- Stress: 10 iterations x 4 stale/in-use/Test fence cases = PASS.
- `compileall`, `git diff --check`, strict source scope and sensitive-term review = PASS.
- PR #181 post-main `33571693986` is SUCCESS across Windows/Ubuntu/macOS including Windows packaging and Frozen Setup E2E; shared closeout ownership is released.
- Parallel WO128 GLM lane remains frozen in its separate worktree; this work order did not mutate provider store/runtime/policy authority.
- Next: exact UTF-8/scope audit, commit, reconcile the own branch onto latest main only after merge-base delta proves disjoint, rerun focused verification, then exact-head PR/independent review/CI.

## Independent review repair checkpoint ? 2026-09-02

- GLM exact-head review `wo127-glm-review-001` reviewed `7591af71c8e90b05e2987646a9c84e79a672dde1` and returned `CHANGES_REQUIRED`: P0=0, P1=0, P2=1, P3=4.
- Accepted P2: Thai teaching text for `CONFIG_STORE_UNAVAILABLE` was mojibake. GPT also repaired the adjacent Thai typos noted as P3.
- Added `test_wo127_provider_teaching_errors_have_no_mojibake` so provider teaching rows fail on `??`/replacement-character corruption and verify repaired Thai wording.
- Repair verification: focused i18n 3 passed; real Tk GUI/i18n bucket 93 passed; `git diff --check` PASS.
- Functional/security/concurrency/lifecycle findings from the independent review were otherwise clean, but that result is evidence for the old head only.
- Next gate: freeze/push repaired exact head, rerun CI, then independent exact-head rereview before merge.

## Final acceptance checkpoint — 2026-09-02

- Final exact head: `e91647a7ccaefe522b11ba867719b3186ed5b96d`.
- GLM exact-head rereview `wo127-glm-rereview-002`: **PASS**, P0=0, P1=0, P2=0, P3=3.
- Exact-head CI `33582451656`: SUCCESS across Windows/Ubuntu/macOS.
- PR #182 merged exact head as `b0eed29656cc54031b7442348449d57cf55d23be`.
- Post-main CI `33585602021`: SUCCESS including Windows packaging and Frozen Setup install/uninstall E2E.
- Product/source claim is released. Future provider-action mutation requires a new work order and fresh ownership gate.
