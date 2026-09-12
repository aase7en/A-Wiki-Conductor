# WO-P1-208 GLM closeout lab — CORRECTED handback (repair cycle 1)

> **SUPERSESSION NOTICE (WO208-GLM-CLOSEOUT-REPAIR-001).** This document
> corrects the original lab handback at candidate `b3a553c` in response to
> the independent Astra lab review (`docs/reviews/WO-P1-208-astra-lab-review.md`,
> verdict CHANGES_REQUIRED — R1–R5 + F1). The original handback is retained
> VERBATIM below this notice as provenance history; superseded/retracted
> claims remain visible there on purpose — do not cite them without the map.
> The corrected, replayable evidence lives in the tracked bundle
> `docs/reviews/wo208-closeout-lab/` (manifest inside). Original ignored
> result files under `runs/WO-P1-208/glm/` remain untouched.

## Correction map (review finding -> original status -> correction -> proof)

| ID | Original status | Correction | Proof (bundle) |
|---|---|---|---|
| R1 COMPLETE lost-ack hooks never reached | reported as valid contrast (both variants `FOLD_CHECKPOINT_MISSING`, hooks not entered) | SUPERSEDED: complete-stage pair now built on REAL ordered prerequisites (fold effect + fold checkpoint through the actual executor; stage decision asserted `FOLD_REQUIRED`; effects==1), wrapper records hook ENTRY and COMMIT at the COMPLETE transition; raise-before-commit -> job REVIEW_PENDING/refs 2, commit-then-raise -> COMPLETE/refs 2, both reopen-verified; positive normal completion + terminal ALREADY_COMPLETE no-op; effects counted across restart | `c03_c05_c06_suite.py::c03_complete_lost_ack` (cases `c03-complete-raise-before-commit`, `c03-complete-commit-then-raise`, `c03-complete-positive`) |
| R2 drivers returned success on failed expectations | exit_matches recorded not enforced; fallback exits reused hook codes; C05 predicate allowed zero CREATED | SUPERSEDED: every driver enforces expectation leaves and exits nonzero otherwise (`lab_common.fail_nonzero`); child writes `cut-marker-<mode>.txt` AT the boundary, distinct exit 79 for returned-past-hook; C02 requires marker+exit+counts+reopened state; negative controls (wrong-exit, missing-marker, fallback-exit, unknown-mode) all detected; C05 two-process requires both exits 0, exact sorted `[CREATED, REUSED_EXACT]`, exactly one row | `c02_cut_matrix.py` 13/13 incl. 4 controls; `wo208_child.py`; `c03_c05_c06_suite.py::c05_two_process` |
| R3 model claims exceeded transitions; unsupported action accepted | 96-tuple decision table, no action validation, only next_effect modeled | SUPERSEDED: `c07_model.py` is a 72-state TRANSITION model (effect, checkpoint AND job-state observable changes; action vocabulary VALIDATED — the review's injected COMPLETE counterexample is now rejected, invariant I6); I1 covers stale-owner effects AND duplicate effects; SEVEN named mutants each caught deterministically (duplicate-unknown-retry, stale-owner-effect, fabricated-checkpoint-complete, contradictory-completion, terminal-repeated-effect, unjustified-initial-blocking, unsupported-action-vocabulary); ack axis documented as an equivalence (error alone never distinguishes commit — proven by the C03 pairs), not duplicate assurance | `c07_model.py` + c07 summary (conservative_clean=True, 7/7 mutants) |
| R4 receipt key included job version (`\|v=8`) | single-version key; version change = CREATED twice | SUPERSEDED: operation identity = `(authority, operation_id)` STABLE across checkpoint version advance v8->v9 (REUSED_EXACT); divergent payload refused; genuinely-new operation distinct; stale-owner rejection explicitly modeled at the ADMISSION gate (C02 stale-gated), not the destination key; `separate-effect-cut` demonstrates a committed receipt does NOT prove an external file effect (receipt PRESENT, file absent) — UNKNOWN stays RECOVERY; no exactly-once/power-loss/cross-host claim | `c03_c05_c06_suite.py::c05_stable_operation_identity` + `c05_separate_effect_cut` |
| R5 bundle not replayable from cold checkout | scripts only in ignored runs/ | SUPERSEDED: tracked bundle `docs/reviews/wo208-closeout-lab/` (7 files + manifest.json with per-file SHA-256, source blob pins, case identifiers, seeds/timeouts); explicit `--repo-root/--output-root` (no HERE.parents assumptions); replayed on native Windows from a CLEAN detached export at the frozen candidate: baseline 94 passed + all four entrypoints exit 0 | bundle + replay summaries in `runs/WO-P1-208/glm-repair/` |
| F1 "recorded seed hash one-char typo" | original finding (P3) | **RETRACTED (false).** The recorded digest is uniformly `bf1136e729cbe8676676031120a586610adeeb3dccca20addda6c1301a579aac` across the seed doc, the Astra review, and the repair packet, and equals the freshly computed SHA-256 of the seed doc's own fence (verified byte-level this repair; the earlier `...6a1301` reading was this lane's own transcription error). The seed fence is republished VERBATIM by `seed_probe.py`, which verifies the digest BEFORE running the four original observations (all four hold on this host). | `seed_probe.py` + seed summary (`fence_hash_ok=True four_observations_ok=True`) |

Retained unchanged (per the review's disposition): the four original seed
observations; the process-cut matrix results (now enforced); the stale gate;
the receipt-row concurrency experiment (now strict predicates); F2 retained
as a source-seam port-contract question — now with the TRUTHFUL ACTIVE-lease
control recorded against the actual release checkpoint (`c06-truthful-active-lease`)
and the RELEASED positive control explicitly labelled a SYNTHETIC fixture
(`c06-synthetic-released-positive`; never an observed release; no production
bypass claimed).

## Repair verification (native Windows, clean detached export at frozen candidate)

- `pytest -q tests/test_goal_closeout.py tests/test_job_store.py` -> **94 passed**
- `seed_probe.py` -> fence verified + four observations -> **exit 0**
- `c02_cut_matrix.py` -> 13/13 cases+controls -> **exit 0**
- `c03_c05_c06_suite.py` -> 10/10 -> **exit 0**
- `c07_model.py` -> conservative clean + 7/7 mutants -> **exit 0**
- MAC_REPLAY_PENDING: native Mac replay of this exact candidate remains with
  the reviewer (Astra) per the repair packet; no simulated Mac evidence claimed.

## Known limits (explicit)

Windows-only native replay; process exits are not power-loss proofs; receipts
are synthetic destinations whose entire transactional effect is one INSERT;
cross-host/shared-storage coordination out of scope; WO205 retains all
option A/B/C effect-contract and migration decisions; no production fix or
source mutation was made in this repair.

──────────────────────────── provenance boundary ────────────────────────────
*(everything below is the ORIGINAL handback, retained verbatim; its C03
complete-stage row, C05 identity definition, C07 description and finding F1
are superseded/retracted per the map above)*

# WO-P1-208 GLM closeout crash/recovery lab — portable evidence handback

Claim `WO208-GLM-CLOSEOUT-LAB-001` (child of WO-P1-208; design owner Poppy Javis/GPT-6 Astra; parent WO205/Issue #214 retains Phase-D authority). Windows executor: GLM-5.3, delivery `b1d52d0c03100f0bfffd9a4adca0c6240f43ac2c` (worktree HEAD verified == pointer), claim commit `6001abf`, final candidate recorded below. **EVIDENCE ONLY — no source/test mutation, no product implementation.**

- Identity: packet SHA-256 `849d7c870c0139d6587e39e32d5e5ffda479e8db987f8ab710b95da31de93639`; proposal `5c3dcd5533e5e247d35a2ceb9f94fcfc82e4d9d2c519ef4c1d4ed52091add7d2`; seed doc `96a5bbc1d02efc5ea179ae461edf2ec57c623416dc0473656e962598d0e0b6b6`; all four source/test **blob IDs MATCH** (`goal_closeout 0acdf8c9`, `job_store bde34b6f`, `job_state 816784b4`, `test_goal_closeout b4055cae`).
- Host: DESKTOP-7IB57R4 / Windows 11 x64 / Python 3.11.15 / SQLite (stdlib). Baseline `pytest -q tests/test_goal_closeout.py tests/test_job_store.py` → **94 passed** (once, per packet).
- Probes (ignored, this lane): `runs/WO-P1-208/glm/{seed_probe.py, wo208_child.py, c02_cut_matrix.py, c03_c05_c06_suite.py, c07_model.py}` + `*-results.json`. Temp roots `wo208-*` (retained for audit).

## Result matrix (native Windows; child cuts are REAL `os._exit` process deaths, not thread simulations)

| Case | Observation | Classification (proposal matrix) |
|---|---|---|
| C01 seed on Windows | all four Astra observations reproduce exactly (2-effects/1-checkpoint; stale-effect→BLOCKED; unknown-reentry 2 effects; positive 1 effect→COMPLETE→ALREADY_COMPLETE) | BASELINE_SEAM_COUNTEREXAMPLE (reopened-store class) |
| C01 negative control | wrong claimed effect count → AssertionError exit 1 | harness non-vacuous |
| C02 cut0 before-effect | exit 10, 0 effects, refs 1, REVIEW_PENDING | established unstarted; next stage may execute |
| C02 cut1 effect-commit | exit 11, 1 effect (fsync+close), journal ABSENT | external truth = receipt only; journal alone cannot distinguish attempted |
| C02 cut2 fold-response | exit 12, 1 effect, journal ABSENT | same durable knowledge as cut1 |
| C02 cut3 checkpoint-commit | exit 13, 1 effect, fold checkpoint PRESENT (refs 2) | consume ordered event + current facts; do NOT repeat effect |
| C02 restart-SAFE (from cut3 DB) | truthful facts → **1 effect total, COMPLETE** | restart reconciliation suppresses replay |
| C02 restart-UNSAFE (from cut2 DB, lost UNKNOWN history) | **2 effects** (real crash then re-entry) | BASELINE_SEAM_COUNTEREXAMPLE at process level |
| C02 cut4 COMPLETE-commit | exit 14 inside transition, state COMPLETE, 1 effect | terminal commit before response loss → reload no-op |
| C02/C04 stale-gated (lab owner precondition) | **0 effects**, gate refused (version/state moved) | effect suppressed at boundary; compare seed where it landed; gate TOCTOU remains → DESIGN_DECISION_REQUIRED |
| C02/C04 concurrent 2 processes (file barrier) | **2 effects**, 1 checkpoint, one child RECOVERY `CHECKPOINT_AFTER_EFFECT_FAILED` | BASELINE_SEAM_COUNTEREXAMPLE at process level (real processes) |
| C03 fold-checkpoint commit-then-raise | caller sees `RECOVERY/CHECKPOINT_AFTER_EFFECT_FAILED`, reopened refs=2 (committed) | identical caller view; **only reopened journal distinguishes** |
| C03 fold-checkpoint raise-before-commit | identical caller view, reopened refs=1 (NOT committed) | error return alone can never decide commit-vs-not |
| C03 complete-stage both variants | `FOLD_CHECKPOINT_MISSING` recovery (precondition before transition) | existing fail-closed preserved; COMPLETE cut covered by C02 cut4 |
| C05 destination-enforced idempotency | CREATED / REUSED_EXACT / REFUSED_DIVERGENT; query PRESENT/ABSENT; **two processes → one CREATED one REUSED_EXACT, no duplicate** | the destination must enforce idempotency; a request digest alone proves nothing |
| C06 odd lease port (`released=False, already_released=False`) | executor treats as successful release (reads only `already_released`) | port-contract question for integrator; NOT a COMPLETE bypass (LeaseEvidence still gates) |
| C07 finite model (96 states) | conservative policy **0 violations** on I1–I5; unsafe blind-retry policy 8×I1 (seed class) | bounded oracle with working negative control |

Fold-contradiction cases in C06 (merge/task contradiction, effect-complete-no-checkpoint, checkpoint-with-UNKNOWN-evidence) are already pinned by the existing suite (`FOLD_IDENTITY_MISMATCH`, `FOLD_CHECKPOINT_MISSING`, `FOLD_CHECKPOINT_CONTRADICTION` — green in the 94-passed baseline); consumed, not retold.

## Replayable reduced excerpts

Child cut (the publication-boundary instrumentation; full code in `runs/WO-P1-208/glm/wo208_child.py`):

```python
class CutStore(SQLiteJobStore):            # lab-only wrapper; no source patch
    def checkpoint(self, job_id, *, checkpoint_ref, expected_version, evidence_ref=None):
        result = super().checkpoint(...)   # real commit first
        os._exit(13)                       # response lost AFTER commit
```

Owner-gate (lab model of an accepted-owner precondition inside the effect boundary):

```python
class VersionGate:
    def check(self):
        current = self.store.get_job(JOB)
        if current.version != self.expected or current.state is not TaskState.REVIEW_PENDING:
            raise RuntimeError("EFFECT_STALE_OWNER_REFUSED")
```

Idempotent destination (the enforcement that a request digest alone cannot provide):

```python
with self.connection:                       # SQLite UNIQUE(identity) PRIMARY KEY
    self.connection.execute("INSERT INTO receipts VALUES (?,?,?)", (identity, payload, "APPLIED"))
# IntegrityError -> compare stored payload: REUSED_EXACT or REFUSED_DIVERGENT_PAYLOAD
```

## Findings

- **F1 (P3, documentation):** the seed evidence doc records probe SHA-256 `...6a1301...` but the doc's own fenced content hashes to `...6c1301...` — single-hex-char difference ⇒ transcription typo in the recorded hash (avalanche excludes content drift). The fence content itself is the authority; extracted and executed verbatim.
- **F2 (observation, design input):** `GoalCloseoutExecutor` reads only `already_released` from `LeaseReleaseOutcome`; a port returning `released=False, already_released=False` is treated as a successful release. Not a COMPLETE bypass (LeaseEvidence still gates), but the port contract should be pinned before Phase D.
- **F3 (design input):** `FoldRequest(task_id, candidate_sha, checkpoint_ref)` cannot carry job/version/owner fencing facts — an effect boundary cannot today prove "still authorized"; C02's lab gate shows the value and its residual TOCTOU. → DESIGN_DECISION_REQUIRED (intent record or fenced adapter under existing authority).
- No production GoalCloseoutExecutor consumer exists under `src` at the base (matches Astra's finding) — all observations remain composition-seam counterexamples, not proven reachable production failures.

## C08 implementation decision packet (for WO205)

| Invariant | Actual consumer/port today | Native evidence | Gap | Minimal accepted-authority extension | Owner/dependency |
|---|---|---|---|---|---|
| No duplicate external effect across crash/concurrency | `GoalCloseoutExecutor` + effect ports; no effect-side idempotency | C02 restart-unsafe (2 effects after real crash); concurrent 2-proc (2 effects); seed | effect owner cannot enforce identity | Option B/C of proposal: destination-enforced idempotent receipt (C05 pattern) or journal intent record — both under existing store authority | WO205 + Phase B/C accepted, Issue #214 release, fresh R3 |
| Commit-vs-error disambiguation | `JobStoreError` surfaces only | C03: identical outcomes, journal decides | callers must reopen + read ordered events | document/require reopen-then-decide contract in the executor's recovery projection | WO205 |
| Stale-owner effect suppression | none at effect boundary | C02 stale-gated (0 effects) vs seed (1 effect) | lab gate has its own TOCTOU | version-bound intent checkpoint in the SAME job journal before effect (proposal option C) | WO205 + integrator decision |
| Terminal no-op + reload | ALREADY_COMPLETE path | C02 cut4 + restart-safe | none observed | — | — |
| Lease port truthfulness | executor reads `already_released` only | C06 odd-port | released=False accepted | pin port contract / typed release evidence | WO205 (small) |

**Decisions pending (integrator):** (1) choose among proposal options A/B/C for supported effects; (2) whether UNKNOWN queries exclude mutation entirely; (3) intent-record placement (job journal vs effect receipt) and migration fencing; (4) lease-port contract pinning; (5) whether Phase-D initial scope restricts to already-idempotent effects.

## Limits

Windows/NTFS + stdlib SQLite only; no power-loss/fsync-crash claims (process exit ≠ power loss); thread-lock conclusions are single-process (cross-process proven via real child processes, cross-host NOT); C05 receipts are a lab oracle, not a proposed production store; fold/lease/review facts were labelled fixtures throughout; WO201/205 source HOLD untouched; no other lane modified.

## Verdict

**COMPLETE_FOR_PARENT_REVIEW** — every program C00–C08 dispositioned with native evidence + controls; WO205 now has the concrete cut-matrix, acknowledgment matrix, idempotency pattern and finite-model inputs it required. Product implementation remains with the parent integrator.
