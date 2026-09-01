# WO-P1-127 — Provider Edit / Disable / Test

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / RED_FIRST
Priority: P1 AHA-7B
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo127-provider-actions`
Branch: `feat/wo-p1-127-provider-actions`
Base: `origin/main@af7a933fe27d2a3e3f29360abf9214df1e5478c5`

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
