# WO-P1-492 — JEV-1C strict response contract hardening

Status: ACTIVE / R2 / OFFLINE_ONLY
Issue: #492
Parent: #484 / JEV-1
Predecessor: #488 (JEV-1B) / #489
Topology: CONTROL_PLANE_ONLY
Reuse classification: EXTEND JEV-1B (`scripts/jev_typesafe_contract.py`, accepted)

## Lane binding

- Authority/execution repo: `A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo492-jev1c`
- Branch: `feat/wo-p1-492-jev1c-strict-response`
- Base/current at claim: `90d92bff51f1547548199be941c85c54d0a9fd3a`
- Owner/integrator: GPT-5.6 Sol (harvest); bounded implementation author executes this packet.

## Goal

Close the non-blocking P3 strictness gaps from the accepted JEV-1B review: reject
undocumented fields at every response layer and require string Score legend
values, while preserving all current behavior and staying fully offline.

## Official TypeSafe response evidence — refreshed by integrator 2026-09-23

- Top-level response documented fields: `model`, `answers`, `usage`.
- `usage`: `input_tokens`, `output_tokens`.
- Choice answer: `type`, `choice`, `probabilities`, `confidence`.
- Score answer: `type`, `score`, `legend`, `probabilities`, `confidence`.
- Score legend: `map<string,string>` — exact level-index keys, string values.
- Noul answer: `type`, `noul`.

## Allowed scope (exact)

- MODIFY `scripts/jev_typesafe_contract.py`
- MODIFY `tests/test_jev_typesafe_contract.py`
- NEW `docs/work-orders/WO-P1-492-jev1c-strict-response-hardening.md`

No `src/a_conductor/**` mutation, no #480/#482 mutation, no commit/push/merge,
no reset/clean/stash/rebase.

## Requirements

1. RED FIRST: failing tests for unknown top-level response fields, unknown
   usage fields, unknown Choice/Score/Noul answer fields, and non-string Score
   legend values.
2. Exact documented-field rejection at each response layer; every violation
   raises `TypeSafeContractError`.
3. Score legend keys remain exact level indices AND every legend value must be
   a string.
4. Preserve: exact model equality, Choice/Score confidence+probabilities,
   Noul no-confidence/no-probabilities rule, non-negative integer usage,
   elapsed validation, explicit input-price cost math, deterministic manifest.
5. Preserve the parameterized versioned-model contract: aliases stay rejected,
   any explicit `jev-X.Y.Z` stays structurally valid. No hard-coded
   `jev-1.13.0` beyond the existing default; live model re-pin is successor
   admission work.
6. This WO records RED/GREEN evidence, scope, residuals, and exact next action.

## Verification plan

- `python -m pytest tests/test_jev_typesafe_contract.py tests/test_jev_shadow_benchmark.py -q`
- 60-record manifest generated twice via CLI, byte-equality proven.
- `py_compile` on changed scripts/tests.
- `git diff --check`.
- Exact three-path dirty scope via `git status --porcelain`.
- No credential/session URL in committed content.

## Checkpoint — implementation complete (2026-09-23)

RED evidence (tests added before implementation, exact base `90d92bff`):
- 12 new failing tests, all `DID NOT RAISE TypeSafeContractError`:
  unknown top-level response field (`pricing`), unknown usage field
  (`total_tokens`), unknown Choice answer fields (`reasoning`,
  `choice_label`), unknown Score answer fields (`legend_rationale`,
  `score_label`), unknown Noul answer field (`explanation`), and five
  non-string Score legend values (int, int, float, bool, None).
- RED run: `12 failed, 50 passed` — every pre-existing test stayed green.

GREEN evidence:
- `python -m pytest tests/test_jev_typesafe_contract.py tests/test_jev_shadow_benchmark.py -q`
  → `62 passed` (50 pre-existing + 12 new strictness tests).

Implementation (additive, `scripts/jev_typesafe_contract.py`):
- `_reject_unknown_fields` helper + documented field-set constants
  (`_RESPONSE_TOP_LEVEL_FIELDS`, `_RESPONSE_USAGE_FIELDS`,
  `_CHOICE_ANSWER_FIELDS`, `_SCORE_ANSWER_FIELDS`, `_NOUL_ANSWER_FIELDS`).
- Top-level payload and `usage` objects now reject any undocumented key.
- Choice/Score answers reject any undocumented key; Noul answers reject
  everything beyond `type`/`noul` while preserving the dedicated
  "must not invent confidence or probabilities" error for those two fields.
- Score legend: keys must remain exact level indices AND every value must
  be a string.
- No behavior change to model equality, confidence/probabilities rules,
  usage integer validation, elapsed/price/cost math, manifest determinism,
  or the versioned-model contract (aliases rejected; any `jev-X.Y.Z`
  structurally valid; default stays `jev-1.13.0`).

Verification (all PASS):
- Targeted pytest: `62 passed`.
- Manifest CLI run twice over the 60-case corpus: 60 records each,
  byte-identical (SHA-256 `37FF6958AC5C5FC4097505FB68A503B4F425AD123021C80C46D8F73CADBC4878`,
  46038 bytes both) — evidence under gitignored
  `runs/WO-P1-492/implementation/attempt-0001-492492492492/`.
- `py_compile` on `scripts/jev_typesafe_contract.py`,
  `scripts/jev_shadow_benchmark.py`, both test files.
- `git diff --check`: clean.
- Dirty scope exactly the three allowed paths:
  `M scripts/jev_typesafe_contract.py`,
  `M tests/test_jev_typesafe_contract.py`,
  `?? docs/work-orders/WO-P1-492-jev1c-strict-response-hardening.md`.
- Diff scan: only benign `*_tokens` substrings; no credential, session URL,
  or network/environment surface (static forbidden-token test also green).

## Residuals

- Credential rotation gate was rechecked by the integrator on 2026-09-23 and now passes without exposing the value: the approved `TYPESAFE_API_KEY` binding differs from the credential previously exposed in chat. This WO remains **offline-only** by contract; live Jev calls require a separate R3 successor claim and fresh provider/model/transport admission.
- Live model re-pin (e.g., moving off `jev-1.13.0`) remains successor
  admission work; this slice keeps the versioned-model contract parameterized.
- Strictness is offline-contract-level only; live transport retry/error
  mapping (401/422/429/529) is later scope.
- If TypeSafe later documents new response fields, `_RESPONSE_*` /
  `_*_ANSWER_FIELDS` constants must be updated with refreshed official
  evidence before live admission.

## Integrator harvest checkpoint — 2026-09-23

- Recovered this lane as `COMPLETE_UNCOMMITTED`; no live author process remained.
- Integrator rerun: `62 passed`.
- Expanded 60-case manifest generated twice with byte-identical output.
- `py_compile`, `git diff --check`, added-line credential/session scan, and static forbidden network/environment/process scan: PASS.
- Credential rotation gate now passes, but no TypeSafe network call occurred in this WO.

## Next safe action

Freeze this exact three-path candidate as a commit, push/open PR, perform independent exact-SHA R2 review plus hosted CI, merge with expected-head protection, then post-main verify. A separate R3 successor WO may perform bounded live Jev smoke/benchmark using only sanitized/public corpus inputs.
