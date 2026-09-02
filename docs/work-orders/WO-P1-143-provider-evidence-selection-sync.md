# WO-P1-143 — Provider Evidence Selection Sync Remediation

Date: 2026-09-03
Owner / implementer: GPT-5.6 Sol MAX
Independent reviewer: GLM-5.3 MAX / ZCode Goal after implementation freeze
Status: CLAIMED / RED_FIRST
Priority: P1 dependency blocker for PR #183 / AIP-1
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo143-provider-evidence-selection-sync`
Branch: `fix/wo-p1-143-provider-evidence-selection-sync`
Base: `origin/main@0c437d7ab2ca6bdff99bf926bf93aa8483b25384`

## Trigger

WO134 / PR #188 historically merged and CI passed, but GPT reproduced a post-merge UI contract defect with a real Tk `<<ComboboxSelected>>` event.

Completed-cache switch: the open Evidence dialog remains bound to the old provider and no replacement evidence read occurs.

Pending switch: the old request is invalidated, but no replacement fetch is submitted; the dialog can remain stale/empty until Evidence is clicked again.

Durable predecessor finding: PR #188 comment `issuecomment-5513700777`.

## Goal

When the MODELS & AGENTS provider combobox changes through the real selection event, any already-open Evidence dialog must follow the newly selected provider truthfully and asynchronously, while stale futures remain unable to write.
## Mutable scope

- `src/a_conductor/desktop_ui.py`
- `tests/test_models_agents_panel.py`
- this work order
- `DEFECT_LESSONS.md` for the accepted reusable lesson
- bounded continuity/lane-index text only when checkpointing this WO

## Forbidden scope

- `src/a_conductor/provider_config_store.py`
- `src/a_conductor/provider_selection_observability.py`
- `src/a_conductor/graph/**`
- scheduler/job/execution/parallel/elastic/provider policy/runtime assembly
- `src/a_conductor/owned_process.py` and `tests/test_owned_process.py` (WO140 GLM-owned)
- PR #183 / WO132 AiPASS files
- A-Wiki Review Bridge
- live Workers/tunnels/binaries/credentials and WO096 maintenance
- release/version publication

## Invariants

- `SELECTION_REASON=UNKNOWN` and `FALLBACK_REASON=NOT_EVALUATED` remain unchanged.
- Provider change never creates a second Evidence window.
- Provider change never performs a Tk-thread store read.
- Old completed cache is not rendered for the new provider.
- Old pending future cannot overwrite a newer provider selection.
- Same-provider selection does not create redundant evidence I/O.
- No provider/store/graph authority expansion.
## RED-first acceptance

1. Real `<<ComboboxSelected>>` after completed primary evidence automatically fetches/renders secondary evidence and keeps the same dialog.
2. Real selection event while primary evidence is pending immediately submits a secondary replacement fetch.
3. Completing/polling the invalidated primary future cannot alter the secondary owner/cache/text.
4. Rapid primary → secondary → primary selection leaves only the newest request authoritative.
5. Re-selecting the currently bound provider does not submit duplicate evidence I/O.
6. Existing close, single-flight, language-cache, graph-context, action-refresh, typed-error and secret-sentinel tests stay green.
7. Focused test file, related GUI/i18n/graph matrix, compileall, `git diff --check`, strict UTF-8/U+FFFD, scope and secret audits pass.
8. Real Tk event E2E proves the repaired behavior outside a manually invoked Evidence-button path.
9. Freeze exact SHA and Git-blob SHA-256 pins; independent GLM review must report P0/P1/P2=0 before PR merge.
10. Exact-head CI, remote diff re-audit, expected-head merge and post-main CI/Frozen Setup E2E are required.

## Baseline evidence

Before production mutation, external real-Tk reproducer on the same source tree reported:
- completed cache: `calls=['glm-primary'] owner='glm-primary' second=False`;
- pending fetch: `executor=2->2 owner='glm-primary' pending=False`.

Existing `tests/test_models_agents_panel.py` baseline: `27 passed, 1 local Tcl/Tk environment skip`; the existing switch test manually re-clicks Evidence and therefore does not cover the real combobox event contract.

## Next safe action

Add deterministic real-event regression tests and prove they fail against the untouched production code. Only then implement the smallest selection-sync seam.
## Implementation checkpoint — 2026-09-03

- Claim commit/push: `ef317e7980142b2408c1493ab0dc79610e12d600`; worktree remained clean before RED mutation.
- RED: `python -m pytest tests/test_models_agents_panel.py -q -k wo143` produced exactly `3 failed, 28 deselected`; failures matched completed-cache stale owner, missing pending replacement fetch, and rapid-switch missing requests.
- Repair changes only the real provider combobox event seam in `desktop_ui.py`; existing evidence read/store/graph authority is unchanged.
- GREEN focused: `3 passed, 28 deselected`.
- Full panel file: `30 passed, 1 local Tcl/Tk installation skip`.
- Related desktop-control/UI/i18n/graph matrix: `145 passed`.
- Repeated real event set: 10/10 iterations PASS.
- Defect Lesson #49 records the helper-path-vs-real-event testing failure mode.

Next: exact CI-topology GUI/related regression, compile/diff/UTF-8/secret/scope audit, realistic E2E/self-review, then freeze commit/push and prepare exact Git-blob independent review after the active WO140 GLM mailbox lane releases.