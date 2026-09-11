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
