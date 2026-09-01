# WO-P1-126 — Models & Agents Settings Display

Date: 2026-09-01
Owner: GPT-5.6 Sol integrator
Status: CLAIMED / RED_FIRST
Priority: P1 AHA-7B
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo126-models-agents-settings`
Branch: `feat/wo-p1-126-models-agents-settings`
Base: `origin/main@23b988764a3529f0721375f5d0a0c885b715ad46`

## Predecessor evidence

WO125 PR #178 merged as `23b988764a3529f0721375f5d0a0c885b715ad46` after GLM exact-head review PASS (P0/P1/P2=0), exact-head CI `33528331266` SUCCESS, integrator adversarial audit, and post-main CI `33534118110` SUCCESS including Windows packaging/Frozen E2E.
## Goal

Add a compact read-only `MODELS & AGENTS` section to the existing Settings surface. It consumes only `DesktopControlService.provider_operator_rows()` and the accepted immutable `ProviderOperatorRow` projection. It must show truthful provider status without creating a second store/router/policy/readiness/quota authority or exposing endpoint/credential values.

## Accepted shaping input

GLM long-goal task `wo125-glm-goal-review-001`, task SHA `2c5eb5c8507f46d8243e21b4d706e01d536da5836722f7b247c3f27c0286cdaa`, reviewed WO125 and then shaped WO126 Stage B. The result is implementation-ready and read-only; GPT remains mutation/merge authority.

## Mutable scope

- `src/a_conductor/desktop_ui.py`
- `src/a_conductor/i18n.py`
- `tests/test_models_agents_panel.py` (new)
- bounded additions to `docs/USER-GUIDE.md`, `docs/USER-GUIDE-EN.md`, `CHANGELOG.md`
- this work order plus `CURRENT-WORK.md`, `handoff.md`, `docs/agent-collab/AGENT_TASKS.md` for checkpoints.
## Forbidden scope

- `provider_operator_view.py`, `provider_config_store.py`, `desktop_control.py`
- provider policy/routing/readiness/quota/execution/capacity authorities
- provider Edit/Disable/Test mutation (WO127)
- selection/fallback policy computation (WO128)
- secret resolver/source, endpoint/credential display, subprocess/network probe launch
- WO096 live tunnel/client/fleet mutation or release/version changes

## Required behavior

1. Reuse the existing Preferences/Toplevel visual language; no second dialog framework.
2. Fetch provider rows only off the Tk thread through the existing background executor.
3. Single-flight refresh: repeated Refresh must not stack provider reads.
4. Stale completion after a newer request or closed dialog must not update widgets.
5. Empty, loading, unavailable/schema/read/corrupt error states are visually distinct; corruption must never render as empty.
6. READY does not imply task authorization; `NOT_EVALUATED` remains explicit.
7. Stale/disabled/rate-limited/unavailable/UNKNOWN trust-egress values remain truthful text states, not color-only meaning.
8. No endpoint, credential reference/value, or raw provenance may appear in labels/tooltips/logs.
## RED-first matrix

- empty store -> explicit empty state;
- delayed read -> loading state, no Tk freeze;
- store unavailable / schema unavailable / read failed / corruption -> typed panel error;
- stale observation, disabled provider, rate-limited provider, UNKNOWN trust/egress -> truthful row text;
- every READY row still shows authorization `NOT_EVALUATED`;
- quota absent vs present/reset formatting;
- safe provenance enum rendering only;
- rapid refresh coalesces to one in-flight read;
- stale generation/completion cannot overwrite newer render;
- close Preferences during delayed refresh -> no dead-widget TclError;
- language change re-renders the panel;
- rendered widget text/repr/loggable data contains no endpoint/credential sentinel.

## Verification gates

RED evidence -> smallest UI repair -> focused tests -> GUI/related regression -> realistic delayed-executor and copied-SQLite smoke -> self review -> independent exact-head review -> diff/UTF-8/secret/compile audits -> PR/CI -> latest-SHA re-audit -> merge -> post-main -> SSoT checkpoint.

P0/P1/P2 findings block merge. Optional auto-refresh is deferred unless deterministic evidence shows it is needed; manual Refresh is sufficient for the first accepted slice.