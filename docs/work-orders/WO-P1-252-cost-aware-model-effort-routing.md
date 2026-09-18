# WO-P1-252 — Cost-aware model and effort routing, slice 1

Status: CLAIMED / IMPLEMENTATION
Issue: #352
Roadmap: GE-0008 P0-E / PNX-4
Risk: R3 CRITICAL — provider preference / quota evidence / execution-routing boundary
Topology: CONTROL_PLANE_ONLY
Classification: EXTEND existing provider evidence; never create a second router/scheduler
Owner/integrator: GPT-5.6 Sol
Implementation lane: SunDay-Worker 5, with GLM-5.3 MAX shaping evidence already harvested

## Binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo252-cost-routing`
- Branch: `feat/wo-p1-252-cost-routing`
- Base SHA: `8dd659df635b50988757414d3eae2f1cf923ba52`
- Durable authority: GitHub Issue #352
- Related roadmap authority:
  - `docs/adr/GE-0008-conductor-pivot-executor-neutral-control-plane.md`
  - `PROJECT-PLAN.md` cost/quota objective
  - `docs/contracts/provider-harness.md`
  - `docs/agent-collab/CAPABILITY_MATRIX.md`
  - `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
  - `.agents/skills/a-fasttask/SKILL.md`

## Reuse-before-build classification

Existing seams already own provider/model/harness and execution authority:

- `provider_configuration.py`
  - `ProviderConfiguration`
  - `ProviderModelConfiguration`
  - provider-neutral `supported_effort_levels` vocabulary
  - `ProviderHealth`, `QuotaSnapshot`, `ProviderObservation`
- `provider_config_store.py`
  - generation-stamped provider configuration persistence
- `provider_policy.py`
  - hard trust/egress policy gate
- `provider_execution_authority.py`
  - exact task/provider/generation/security execution requirement and quota fail-closed authority
- `worker_candidate_assembly.py`, `parallel_ready_execution.py`
  - currently single-pinned provider execution path
- `provider_selection_observability.py`
  - truthful selection/fallback evidence without invented ranking

This slice is therefore `EXTEND`, not `NEW` or `REPLACE`.

## Goal

Add a pure, deterministic **preference-evidence layer** for declared model cost and current quota
shape without changing dispatch, admission, lease, scheduler, task, claim, or provider authority.

Preference ordering may only order candidates that are otherwise eligible. It must never:
- turn an ineligible provider into an eligible one;
- convert UNKNOWN quota/cost into free/available evidence;
- override `ProviderExecutionAuthority.authorize()`;
- launch or fail over providers;
- create a new scheduler/router;
- persist live secret-bearing quota probes.

## Claimed tracked scope

- MODIFY `src/a_conductor/provider_configuration.py`
- NEW `src/a_conductor/provider_cost_preference.py`
- MODIFY `tests/test_provider_configuration.py`
- NEW `tests/test_provider_cost_preference.py`
- NEW `docs/work-orders/WO-P1-252-cost-aware-model-effort-routing.md`

No other tracked file is mutable in this slice.

## Contract

### Declared cost evidence

Extend `ProviderModelConfiguration` with one provider-neutral declared cost class:

- `UNKNOWN`
- `FREE`
- `LOW_COST`
- `STANDARD`
- `PREMIUM`

Requirements:
1. old serialized model rows without the field decode as `UNKNOWN`;
2. invalid values fail closed;
3. the field round-trips through existing `models_json` persistence; no database DDL;
4. cost class is declared configuration, not inferred from provider/model name;
5. saving a changed declared cost class remains generation-stamped through the existing CAS/store path.

### Effort vocabulary

Reuse the existing provider-neutral values:
- `DEFAULT`
- `LOW`
- `HIGH`
- `MAX`

Do not add provider-specific thinking labels to routing contracts.

For a request explicitly pinned to LOW/HIGH/MAX:
- a candidate is eligible for the preference layer only if the model declares that effort level;
- an empty declaration does not prove support;
- DEFAULT means no non-default effort requirement and remains admissible.

This is preference eligibility only; it does not authorize execution.

### Quota preference view

Add a pure derived quota tier over existing `QuotaSnapshot` evidence:

- `AVAILABLE`
- `LOW`
- `EXHAUSTED`
- `UNKNOWN`

Rules:
1. `None` or any structurally incomplete five-hour tuple => `UNKNOWN`;
2. bool-as-number, negative, non-finite, or contradictory quota evidence => `UNKNOWN`, never available;
3. remaining <= 0 => `EXHAUSTED`;
4. LOW/AVAILABLE are derived only from a complete internally-consistent tuple using an explicit deterministic threshold;
5. the derived tier is a preference view only and is never persisted as execution authority;
6. `UNKNOWN` is never treated as unlimited or free.

DEFECT_LESSONS #30/#31 remain binding: remote quota evidence is untrusted until exact-origin,
structurally complete, finite, unambiguous, and internally consistent.

### Candidate preference

Add one pure deterministic ranking function for already-supplied candidate evidence.

It may consider only:
- declared `cost_class`;
- derived quota tier;
- explicitly requested effort support;
- stable provider/model identity tie-breakers.

It must not:
- call providers;
- read secrets/config files;
- mutate provider state;
- perform admission;
- launch jobs;
- inspect global mutable Active Project;
- infer latency/reliability/cost from missing observations.

Preference order:
- eligible beats effort-ineligible;
- better quota evidence beats worse quota evidence;
- lower declared cost may break ties among otherwise comparable evidence;
- UNKNOWN cost/quota must rank conservatively, never as best evidence;
- stable provider/model identity provides the final deterministic tie-break.

Exact numeric billing estimates are explicitly out of scope.

## Failure / unknown semantics

Use explicit types/reasons; never magic numbers or provider-name heuristics.

At minimum preserve:
- `COST_UNKNOWN`
- `QUOTA_UNKNOWN`
- `EFFORT_UNSUPPORTED`
- deterministic eligible preference reasons

Latency/reliability remain `UNKNOWN/NOT_EVALUATED` in this slice and do not affect ranking.

## Security and authority invariants

1. No live quota probe or credential resolution in this module.
2. No secret-bearing output persistence.
3. No provider admission/release mutation.
4. No scheduler/lease/job/task/claim mutation.
5. No fallback launch or replay.
6. Ranking output is advisory preference evidence only.
7. `ProviderExecutionAuthority.authorize()` remains the execution gate.
8. A preferred candidate denied by hard policy/quota authority remains denied.
9. Generation/security/provider-store identity fences remain unchanged.
10. This slice does not touch WO253 Kilo harness files or WO254 Kilo MCP-health files.

## Required deterministic tests

### Provider configuration

- every valid cost class parses and serializes;
- missing cost class decodes as UNKNOWN;
- invalid cost class rejects;
- existing effort validation remains unchanged;
- declared cost changes survive existing serialization round-trip.

### Quota tier

- missing observation/snapshot => UNKNOWN;
- partial five-hour tuple => UNKNOWN;
- bool/non-finite/negative/contradictory tuple => UNKNOWN;
- remaining == 0 => EXHAUSTED;
- complete low-remaining tuple => LOW;
- complete healthy tuple => AVAILABLE;
- repeated identical input => identical result.

### Ranking

- identical candidates produce deterministic stable ordering;
- UNKNOWN cost is never treated as FREE;
- UNKNOWN quota is never treated as AVAILABLE;
- exhausted is never preferred over available;
- lower declared cost breaks only an otherwise comparable tie;
- explicit unsupported effort makes that candidate preference-ineligible;
- empty supported-effort set does not prove explicit LOW/HIGH/MAX support;
- DEFAULT does not require a non-default effort capability;
- provider/model names do not change semantic ranking except final stable tie-break;
- pure ranking has no side effects.

### Authority non-interference

Add a focused proof using existing execution-authority objects or an equivalent invariant:
ranking/preference evaluation does not change the input provider configuration/observation and
does not itself call or bypass `ProviderExecutionAuthority.authorize()`.

No live provider/network tests.

## Verification

Run:
- focused provider configuration tests;
- focused new cost-preference tests;
- directly related provider authority/config persistence tests if the model schema touches them;
- `python -m compileall` on changed source/tests;
- `git diff --check`;
- exact five-path scope check;
- added-line secret/URL scan;
- independent exact-SHA R3 review;
- hosted CI before merge.

## Deferred

Not authorized in this slice:
- multi-provider node contract;
- pre-attempt automatic failover/re-selection wiring;
- scheduler/elastic/parallel executor mutation;
- live CoinTH/Z.ai quota ingestion;
- numeric price/token billing accounting;
- latency/reliability-weighted ranking;
- provider-store DDL;
- operator UI;
- automatic provider switching.

A later slice may wire this pure preference output into pre-attempt selection only after proving
that nothing has launched and that the same task/claim/provider-execution fences are preserved.

## Exit

Freeze one exact candidate SHA with deterministic tests. Independent R3 review must prove that
preference evidence cannot become execution authority and that UNKNOWN evidence never gains
optimistic semantics.
