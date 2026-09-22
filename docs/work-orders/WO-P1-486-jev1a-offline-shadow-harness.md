# WO-P1-486 — JEV-1A offline shadow benchmark harness

Status: ACTIVE / R2 / OFFLINE_ONLY
Issue: #486
Parent: #484 / JEV-1
Topology: CONTROL_PLANE_ONLY
Reuse classification: EXTEND

## Lane binding

- Repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo486-jev1a`
- Branch: `feat/wo-p1-486-jev1a-offline-harness`
- Base/current at claim: `1bc617687dd931c537c569cdfa9d031b7a61b974`
- Claim: Issue #486 comment #5779806558
- Owner/integrator: GPT-5.6 Sol
- Global mutable WIP at claim: #480, #482, #486 = 3. Parent #484 docs PR #485 is frozen/non-mutating.

## Goal

Build the smallest deterministic, network-free benchmark harness needed to validate JEV-1 metrics and failure behavior before any live TypeSafe transport or credential use.

## Allowed scope

- `scripts/jev_shadow_benchmark.py`
- `tests/test_jev_shadow_benchmark.py`
- `tests/fixtures/jev_shadow/cases.jsonl`
- `tests/fixtures/jev_shadow/provider_results.json`
- this work-order file only

## Forbidden

- no `src/a_conductor/**` mutation;
- no live network/API call;
- no read/use of `TYPESAFE_API_KEY`;
- no private hospital/pharmacy/estate/user payloads;
- no #480/#482 files;
- no production routing/provider behavior;
- no benchmark result granting claim/mutation/review/merge/completion authority.

## Contract

### Case schema

Each case is versioned and contains:
- stable case ID;
- decision family;
- question type: `choice`, `score`, or `noul`;
- sanitized state;
- bounded options/levels where applicable;
- expected answer;
- risk level;
- policy thresholds for auto-accept vs escalation;
- optional measured baseline latency/cost.

### Provider result schema

A normalized fixture result contains:
- matching question type;
- answer;
- optional confidence;
- optional probabilities;
- model ID;
- latency;
- token usage;
- estimated cost;
- retries;
- optional typed provider error.

No raw credentials or environment dumps are permitted.

### Metrics

Required summary:
- total/valid cases;
- schema failures;
- raw accuracy;
- auto-decision accuracy;
- high-risk false automatic actions;
- escalation rate;
- provider errors/retries;
- p50/p95 latency;
- sequential-equivalent throughput;
- input/output tokens;
- total cost and cost per 1,000 decisions;
- frontier-call avoidance rate;
- per-family breakdown;
- optional baseline p50/p95 and speedup/cost ratios when baseline evidence exists.

## Failure model

Tests must prove fail-safe handling for:
- provider error;
- missing fixture/result;
- wrong result type;
- malformed answer/probability/confidence;
- low-confidence Choice/Score;
- Noul review-band ambiguity;
- secret-shaped state;
- high-risk wrong high-confidence auto action;
- result serialization that excludes raw state.

## Verification

Targeted:
`python -m pytest tests/test_jev_shadow_benchmark.py -q`

CLI fixture smoke:
`python scripts/jev_shadow_benchmark.py --cases tests/fixtures/jev_shadow/cases.jsonl --fixtures tests/fixtures/jev_shadow/provider_results.json`

Repository checks:
- `git diff --check`;
- exact allowed-file diff;
- UTF-8/U+FFFD check;
- secret-shaped added-line scan;
- no network/key references beyond explicit forbidden-contract documentation.

## Acceptance

R2 acceptance requires:
- targeted tests green;
- deterministic CLI smoke green;
- all failure tests fail safely;
- no production behavior changes;
- exact-scope diff;
- independent review if required by current fast-execution policy before merge.

## Checkpoint

- [2026-09-22] Parent #484 docs bootstrap frozen in PR #485.
- [2026-09-22] Current origin/main at claim: `1bc617687dd931c537c569cdfa9d031b7a61b974`.
- [2026-09-22] #480 and #482 live mutable work recovered before claim; this lane occupies the third mutable slot.
- [2026-09-22] Live TypeSafe credential/provider use explicitly deferred to a later R3 slice.

- [2026-09-22] Implemented deterministic offline harness + six sanitized decision-family fixtures with no network or credential reads.
- [2026-09-22] Targeted test suite PASS: `14 passed`.
- [2026-09-22] Fixture CLI smoke PASS. Simulated fixture-only comparison produced raw accuracy 1.0, escalation 1/6, p50 speedup 21.06x, p95 speedup 23.09x, and cost reduction 67.29x. These are harness fixtures, not Jev performance evidence.
- [2026-09-22] `py_compile`, `git diff --check`, UTF-8/U+FFFD and secret-shaped committed-content scans PASS. A committed secret-shaped test literal was caught by the scan and replaced with runtime construction before freeze.

- [2026-09-22] Independent exact-SHA review attempt-0002 on `e9844e844770b537bb001c377e4cb232d7e6991b`: `CHANGES_REQUIRED`, P0/P1=0, P2=2, P3=2. P2 findings: committed failure-model tests did not yet prove all malformed-value/confidence/Score-low-confidence cases; invalid/missing outcomes could contribute fabricated zero latency/cost and partial-baseline populations could overstate comparison ratios. Reviewer independently confirmed 14 tests, CLI fixture numbers, fail-closed runtime behavior and no network/env/credential access.
- [2026-09-22] Repair batch: added malformed answer/confidence/metrics/token and Score/Noul failure tests; headline performance now uses valid responses only; speedup/cost comparison is emitted only for a fully matched all-valid population; partial/failing populations explicitly report comparison as unavailable. Defense-in-depth also rejects secret-shaped fixture values, redacts secret-shaped model/schema diagnostics, and bounds Score tolerance to its declared span.
- [2026-09-22] Post-repair targeted suite: `28 passed`; CLI fixture smoke preserves the simulated-only 21.06x p50 / 23.09x p95 / 67.29x cost ratios for the fully valid six-case fixture corpus. These remain harness fixtures, not live Jev evidence.

## Next safe action

Implement tests/fixtures and offline harness only within the allowlist, run targeted verification, freeze exact SHA, then independent review/CI as required.