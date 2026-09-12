# WO208 closeout lab — repaired research bundle

Repaired evidence bundle for `WO208-GLM-CLOSEOUT-REPAIR-001` answering the
Astra lab review (`docs/reviews/WO-P1-208-astra-lab-review.md`, R1–R5 + F1).
Everything here is a RESEARCH artifact for review; no production fix, no
source mutation, no CI discovery. Requires only the pinned repository
checkout (stdlib + the repo's own test helpers) and Python 3.11+.

## Files

| File | Purpose | Repairs |
|---|---|---|
| `lab_common.py` | shared helpers: `--repo-root` resolution, owned temps, strict exit discipline, `verify_manifest` preflight gate, `validate_cut_observation` shared validator | R2/R5, N1, S1/S4 |
| `seed_probe.py` | canonical seed rehydration + digest verification + EXECUTABLE-BYTES BINDING (mismatched bytes rejected before import; sentinel proves accepted code ran) + manifest preflight | F1, R5, N1, S1 |
| `wo208_child.py` | child helper: cut markers AT the boundary, distinct 79 fallback exits, restart-aware fsynced effects | R1/R2 |
| `c02_cut_matrix.py` | enforced cut matrix (shared validator) + restarts + concurrent processes + 10 negative controls incl. REAL helper timeout | R2, N3, S5 |
| `c03_c05_c06_suite.py` | fold/COMPLETE lost-ack pairs, stable identity receipts, truthful lease controls + REQUIRED reload-active contradiction experiment | R1/R4/F2, N4, S6 |
| `c07_model.py` | CLOSED four-axis transition model (72 states) + nine named mutants + six bounded traces | R3, N2, S2/S3 |
| `manifest.json` | per-file SHA-256 (regenerated LAST; excludes itself), source blob pins, case identifiers, seeds/timeouts | R5, N1 |
| `replay_suite.py` | one documented batch command: manifest preflight + all four entrypoints + differential/metamorphic batch | S7/S8 |
| `test_lab_contract.py` | pytest suite validating the validators through their real entrypoints (24 tests) | S4/S8 |

## Commands (Windows, from the repository root of the pinned checkout)

```text
python docs/reviews/wo208-closeout-lab/seed_probe.py --repo-root . --output-root <OWNED_OUT>\seed
python docs/reviews/wo208-closeout-lab/c02_cut_matrix.py --repo-root . --output-root <OWNED_OUT>\c02
python docs/reviews/wo208-closeout-lab/c03_c05_c06_suite.py --repo-root . --output-root <OWNED_OUT>\c03c05c06
python docs/reviews/wo208-closeout-lab/c07_model.py --output-root <OWNED_OUT>\c07
```

### One-command batch (preferred, S8)

Windows:
```text
python docs/reviews/wo208-closeout-lab/replay_suite.py --repo-root . --output-root <OWNED_OUT>atch
```
POSIX:
```text
python docs/reviews/wo208-closeout-lab/replay_suite.py --repo-root . --output-root /tmp/wo208-batch
```
The batch runs the manifest preflight, all four entrypoints and the
differential/metamorphic batch (ordering permutation, c07 replay
determinism, corrupt-summary handling, idempotent suite rerun) and appends
`run-N` subdirectories without deleting prior evidence. Expected
observations: `manifest-preflight PASS`, four `entry:* exit=0` lines, four
`diff:*` PASS lines, `batch exit=0`.

### Contract test suite

```text
python -m pytest -q docs/reviews/wo208-closeout-lab/test_lab_contract.py
```
Expected: 24 passed. Environment: Python 3.11+, stdlib only, tracked
contents only, `PYTHONDONTWRITEBYTECODE=1` recommended.

POSIX equivalent: the same commands with `/` paths. Every entrypoint exits 0
ONLY when all enforced expectations and negative controls hold; any unmet
expectation produces exit 1 with a `_failed_checks` list in the summary JSON.

Expected summaries: seed `fence_hash_ok=True four_observations_ok=True`;
C02 13/13 cases+controls; C03/C05/C06 10/10; C07 `conservative_clean=True
all_mutants_caught=True` (7 mutants).

## Baseline

`python -m pytest -q tests/test_goal_closeout.py tests/test_job_store.py`
→ 94 passed on the pinned source (Python 3.11.15, Windows 11).

## OS verification matrix (honest)

| Capability | Windows (this repair) | macOS |
|---|---|---|
| All bundle entrypoints | NATIVE replayed from a clean export (this repair) | MAC_REPLAY_PENDING — reserved for Astra's exact-candidate verification |
| Seed fence digest | NATIVE | verified by reviewer (both hosts agree) |
| Process-cut experiments | NATIVE Windows processes | not claimed |
| SQLite/job-store behavior | NATIVE | same engine expected, not claimed |

## Repairs mapped to review findings

- **R1** `c03_c05_c06_suite.py::c03_complete_lost_ack` — REAL ordered
  prerequisites (fold effect + fold checkpoint via the actual executor,
  `FOLD_REQUIRED` asserted), wrapper hook writes `hook-state.json` at the
  COMPLETE transition (entry + commit recorded), raise-before-commit and
  commit-then-raise variants, both stores reopened, states/refs/effects
  compared; positive normal completion + terminal `ALREADY_COMPLETE` no-op.
- **R2** every driver enforces expectations (`lab_common.require`,
  `fail_nonzero`); `wo208_child.py` writes a `cut-marker-<mode>.txt` AT the
  boundary and uses exit 79 for any returned-past-hook fallback; C02 requires
  marker+exit+counts; negative controls prove the driver fails on wrong exit,
  missing marker, fallback exit, unknown mode; C05 two-process requires both
  exits 0, exact multiset `[CREATED, REUSED_EXACT]`, exactly one row.
- **R3** `c07_model.py` is a transition model (effect/checkpoint/job all
  modeled, actions validated); seven named mutants each caught; unsupported
  action rejected (I6) — the review's injected-`COMPLETE` counterexample now
  fails the model; ack axis documented as equivalence, not extra assurance.
- **R4** `ReceiptDestination` operation identity = `(authority, operation_id)`
  — stable across version advance v8→v9 (`REUSED_EXACT`), divergent payload
  refused, new op distinct, stale-authority case documented as admission
  (C02 gate) not destination-key; `separate-effect-cut` demonstrates receipt
  ≠ external-effect atomicity; no exactly-once/power-loss claim.
- **R5** this tracked bundle + manifest; explicit `--repo-root/--output-root`
  arguments everywhere (no `HERE.parents` assumptions); replayed from a
  clean export on native Windows during this repair.
- **F1** RETRACTED in the corrected review doc: recorded digest
  `bf1136e7…6c1301a579aac` equals the computed fence hash (uniform across
  seed/review/packet documents); the "…6a1301 typo" claim was this lane's
  misreading. The original seed fence is republished verbatim by
  `seed_probe.py` and verified before any observation runs.
- **F2 retained** as a port-contract question: `c06-truthful-active-lease`
  feeds TRUTHFUL ACTIVE lease evidence after the odd both-false port outcome
  and records the contradiction (release checkpoint absent while the executor
  proceeds); the RELEASED positive control is explicitly labelled a SYNTHETIC
  fixture, never an observed release.

## Known limits

Process exits are not power-loss proofs; effects are file receipts; the
receipt INSERT is the entire transactional effect of the synthetic
destination; cross-host/shared-storage coordination out of scope; WO205
retains all option A/B/C and migration decisions.
