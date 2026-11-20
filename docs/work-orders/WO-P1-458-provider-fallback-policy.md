# WO-P1-458 — BWA-1B1 Deterministic Pre-Attempt Provider Fallback Policy

Status: CANDIDATE_READY / R3 RECOVERY ATTEMPT 3 / AWAITING EXACT-SHA REVIEW + CI + SOL ACCEPTANCE
Issue: #458
Identity schema: GITHUB_ISSUE_V1
Risk: R3 provider-selection trust boundary (fail-closed policy over authorization/quota/cost evidence)
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Author claim: WO-P1-458-PROVIDER-FALLBACK-WINDOWS-001 (dispatch identity only; no acceptance authority)
Date: 2026-09-21

## Exact binding

- repo: `aase7en/A-Wiki-Conductor`
- worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo458-provider-fallback`
- branch: `feat/wo-p1-458-provider-fallback-policy`
- base/current main: `eb9305957d4bfc71b1e53bca1206b84c9ee1105b`
- pre-mutation state at recovery: clean tree except the two allowed untracked
  partial artifacts from interrupted attempt 1; no commits exist on this lane

## Interrupted-attempt recovery provenance

- Attempt 1 was interrupted mid-flight, leaving untracked partial
  `src/a_conductor/provider_fallback_policy.py` and
  `tests/test_provider_fallback_policy.py` with a reproduced focused state of
  42 PASS / 6 FAIL. The partial work was preserved in place; nothing was
  reset, cleaned, stashed, or discarded.
- Attempt 2 ended TERMINAL_INCOMPLETE with a runner pipe-stall; it was fully
  harvested and no live executor remains. Harness behavior was never treated
  as product evidence.
- Attempt 3 (this recovery) reproduced the exact 42/6 state before any
  mutation, then repaired the test fixture and the authority test only.

## Exact mutable scope (3 tracked files; bounded modification only)

1. `src/a_conductor/provider_fallback_policy.py`
2. `tests/test_provider_fallback_policy.py`
3. `docs/work-orders/WO-P1-458-provider-fallback-policy.md`

Forbidden (READ-ONLY): every other tracked path, including all other `src/**`,
tests, `CURRENT-WORK.md`, `handoff.md`, live provider configuration, and
credentials/secret material. If any fourth tracked file appears modified, work
stops and is reported before further mutation.

## Deliverable

One pure, deterministic, pre-attempt selection policy module plus its focused
test suite: given an explicitly ordered candidate set supplied by the caller,
`select_pre_attempt_provider` selects at most one provider/model before any
admission or launch attempt and returns typed per-candidate stage/reason
evidence (`NOT_CAPABLE` / `CAPABLE` / `READY` / `AUTHORIZED`; `ADMITTED` exists
in the vocabulary only and is never emitted). Serialization is canonical and
byte-stable (`to_json`, `result_sha256`).

## Authority fences preserved

- `provider_cost_preference.py` (WO252) remains advisory ranking only;
  `derive_quota_tier` is reused as conservative quota-tier evidence:
  EXHAUSTED is ineligible and UNKNOWN is never promoted optimistically.
- WO128 `provider_selection_observability.py` truth is untouched: absent
  selection authority remains UNKNOWN and absent fallback authority remains
  NOT_EVALUATED; this policy fabricates no history and never claims ADMITTED.
- `provider_execution_authority.py`, `provider_policy.py`, and
  `provider_service_authorization.py` remain the hard gates; this module
  reuses `evaluate_provider_policy`, `evaluate_provider_service_authorization`,
  and `is_provider_ready` by reference and adds no second authority path.
- The caller's explicit candidate order is never auto-widened, re-ranked, or
  remembered across calls; the first fully eligible candidate in explicit
  order wins.
- Missing observation/service/quota evidence fails closed with typed reasons
  (`READINESS_EVIDENCE_MISSING`, `SERVICE_AUTHORIZATION_REQUIRED`,
  `QUOTA_UNKNOWN`, `COST_CLASS_UNKNOWN`); UNKNOWN cost/quota/readiness is
  never optimistic.
- No I/O, store, network, subprocess, credential resolution, launch, retry,
  or lifecycle mutation; same inputs produce an equal, byte-stable result.
- Issue #340 remains owner of global provider routing; the #215 NEXT_READY
  authority and the WO433 runtime-activation primitive are unchanged and are
  named in prose only — the module's only public function is
  `select_pre_attempt_provider`.

## RED evidence (reproduced before attempt-3 mutation)

- Command: `py -3.13 -m pytest -q tests/test_provider_fallback_policy.py`
- Result: `6 failed, 42 passed`.
- Five failures were test-fixture ambiguity: `make_candidate` used `None`
  both as "use a default" and as "explicitly missing evidence", so cases
  intended to exercise missing observation/service/quota never actually
  passed `None` into `ProviderFallbackCandidate`:
  `test_missing_service_record_fails_closed_for_live_mode`,
  `test_missing_or_stale_readiness_evidence_selects_nothing[None-READINESS_EVIDENCE_MISSING]`,
  `test_bad_quota_evidence_is_ineligible[None-QUOTA_UNKNOWN]`,
  `test_unknown_quota_is_never_promoted_over_known_available`, and
  `test_selection_trips_no_io_probes` (whose `quota=None` rejection leg
  silently received a default quota).
- One failure was a brittle authority test asserting the literal string
  NEXT_READY is absent from module source while the module docstring
  legitimately names that upstream authority.

## Repair (test-side only; no production defect found)

- `make_candidate` now distinguishes omitted (sentinel `_DEFAULT` =>
  construct valid default evidence) from explicit `None` (missing evidence
  passed through to `ProviderFallbackCandidate`). Missing-evidence
  expectations were not weakened.
- The brittle source-text test was replaced by semantic checks: AST fence
  proving the module imports no runtime-authority roots (socket, subprocess,
  os, pathlib, urllib, http, secrets, threading, ...) and defines/references/
  exports no runtime-activation, NEXT_READY-selection, launch, dispatch,
  admission, retry, store, network, secret-resolution, or subprocess
  identifiers; the module's only public function is
  `select_pre_attempt_provider`; runtime `hasattr` fences for
  activate/dispatch/launch/retry/admit. Explanatory docstrings may still name
  upstream authorities.
- Production selector already had explicit fail-closed branches for missing
  observation, service-authorization denial, and UNKNOWN/EXHAUSTED quota;
  the corrected tests verified rather than assumed them, and no production
  change was required.

## GREEN evidence (after repair)

- `py -3.13 -m pytest -q tests/test_provider_fallback_policy.py` -> 48 passed

## Verification battery (author-run, pre-freeze)

- `py -3.13 -m pytest -q tests/test_provider_fallback_policy.py` -> 48 passed
- `py -3.13 -m pytest -q tests/test_provider_cost_preference.py tests/test_provider_selection_observability.py tests/test_provider_execution_authority.py tests/test_provider_policy.py tests/test_provider_service_authorization.py` -> 121 passed
- `py -3.13 -m py_compile src/a_conductor/provider_fallback_policy.py` -> clean
- `py -3.13 -m pytest -q tests/test_work_order_identity.py` -> green (identity guard, including this file)
- `git diff --check` -> clean
- `git status --short` -> exactly the three scope files, nothing else

Interpreter note: the launcher-default `python` (3.14) has no pytest in this
environment; the repo-tested `py -3.13` interpreter was used for all commands
above with identical module paths (`pythonpath = ["src"]`).

## Next gate

Freeze the exact candidate SHA -> fresh independent exact-SHA focused review
(P0/P1/P2 = 0 required) -> exact-head hosted CI green -> GPT-5.6 Sol
acceptance/expected-head merge and post-main verification. The author does
not merge or self-accept.
