# WO208 exact repair review — native Mac replay and residual findings

Date: 2026-09-12. Reviewer: Poppy Javis / GPT-6 Astra / home macOS.
Claim: WO208-ASTRA-REPAIR-REVIEW-001.
Candidate: `2482998e19ee439e04adf321cd5d74c1feb94243`.
Verdict: **CHANGES_REQUIRED — four P2 evidence findings (N1–N4)**.
These are lab acceptance findings, not production vulnerability claims.
Sol's original design-only acceptance remains intact. WO205 still owns production
composition, effect-contract decisions and source release. No merge by this lane.

## What is now proved

Native Mac replay used the exact tracked candidate source/bundle bytes, a fresh isolated
worktree, fresh ignored outputs and PYTHONDONTWRITEBYTECODE=1. No old Windows ignored
artifacts were present. All four source blob pins match the original base; src/tests
have no delta. Baseline: 94 passed in 0.50s. All four entrypoints exit zero:
seed, C02 (13 cases/controls), C03/C05/C06 (10), C07 (72 states, seven named mutants).
This closes MAC_REPLAY_PENDING for this candidate's normal run, not lab acceptance.

R1 is resolved: COMPLETE hooks are entered. Raise-before-commit reopens REVIEW_PENDING;
commit-then-raise reopens COMPLETE. Both caller outcomes are JOB_STORE_WRITE_FAILED,
both have two prerequisite checkpoint refs and one effect. Normal completion followed
by ALREADY_COMPLETE also preserves one effect. Fold-checkpoint lost-ack evidence remains.

R4's bounded identity example is improved: the same authority/operation key reuses a
receipt across version 8→9, while different payloads are refused and new operations
are distinct. The separate-file example correctly limits receipt-row atomicity. It is
a deliberate omitted-effect simulation, not an actual process-death experiment.
The gate remains an admission example with a TOCTOU limit, not destination fencing.
Original F1 is correctly retracted; the immutable seed document's hash is correct.

Normal green output does not establish the following adversarial obligations.

## N1 / P2 — verified seed document is not bound to the executed seed

`seed_probe.py:73-103` prefers an existing ignored original or an existing output
`seed_fence_materialized.py`. It calculates those bytes' hashes but never requires
them to match the verified fence before importing and executing them.

Independent Mac control: in a fresh owned output directory, write this file:

```python
def run():
    return {'concurrent': {'effects': 2}, 'stale': {'effects': 1},
            'unknown_reentry': {'effects': 2},
            'positive': {'effects': 1, 'state': 'COMPLETE'}}
```

Run the unmodified tracked seed entrypoint with that output directory and the exact
candidate as --repo-root. It reports `fence_hash_ok=True four_observations_ok=True`
and exits zero, although no seed experiment ran and the imported bytes are not the
canonical fence. This is a synthetic evidence-substitution result, not hostile code
execution against a live system. Reject mismatched executable bytes before import,
or execute only the exact verified fence in owned fresh storage. Do not silently
overwrite unexplained existing evidence. Cover both existing-file search locations.

The delivered manifest also mismatches `c07_model.py`:

| SHA-256 type | Digest |
|---|---|
| manifest expected | 98f8691c8a8d5c8e1fc1dd2c3a766be889d7dd72a6e70c2d5e73bc2ffec284d0 |
| exact candidate actual | 85dd3891f74badba8c45c40c1787dd640b886b8d14d2e787566cdbba09ca8b73 |

The other six manifest entries match. The first manifest assertion correctly failed;
review replay then explicitly used inspected Git-pinned bytes, not a claim of manifest
success. Regenerate the manifest last and enforce it before experiment execution.

## N2 / P2 — transition shape and authority coverage remain incomplete

`c07_model.py::transition` returns a THREE-element next state for EXECUTE_ONCE although
the state schema has four axes. It also counts the first actual effect as zero new
effects. The checker discards next_state, hiding the malformed transition:

```python
s = ('CURRENT', 'NOT_STARTED', 'ABSENT', 'NONTERMINAL_REVIEW')
n, added, _, _ = transition(s, 'EXECUTE_ONCE')
# n == ('CURRENT', 'APPLIED_NO_RECEIPT', 'ABSENT'), added == 0
transition(n, 'RECOVER')  # ValueError: expected 4, got 3
```

Two additional supported-action mutants escape all I1–I6 checks. Each overrides only
the named tuple, then delegates other states to decide_conservative:

| Input tuple | Mutant action | Detected violations |
|---|---|---|
| CURRENT, NOT_STARTED, ABSENT, NONTERMINAL_BLOCKED | EXECUTE_ONCE | zero |
| STALE, APPLIED_RECEIPT, PRESENT_EXACT, NONTERMINAL_REVIEW | COMPLETE | zero |

The latter changes the modeled job to TERMINAL_COMPLETE with stale ownership. These
are checker counterexamples, not evidence that production performs these actions.
Make transitions closed over the declared schema, count actual effects, and evaluate
state changes through bounded traces, including blocked/stale completion and execution.
The documentation also calls COMPLETE unsupported while ACTIONS now includes it; the
named mutant actually uses COMPLETE_UNMODELED. Correct the distinction. Keep bounded
availability claims explicit; do not infer full lifecycle liveness from one start tuple.

## N3 / P2 — negative controls do not exercise the failing validator

C02's wrong-exit/missing-marker/fallback controls inspect their deliberately altered
inputs and then mark themselves successful. They do not feed those observations to
the same validation path and demonstrate a failing experiment command. The unknown
mode argument rejection is not the requested finite helper-timeout/cleanup proof.

Independent mutation control on an ignored copy:

1. Change cut0's expected exit from 10 to 99.
2. Replace only the main cut predicate `code == want_exit and marker_ok` with `True`.
3. Leave all declared negative controls unchanged and run the driver on fresh outputs.

The result still exits zero, marks cut0 passed with actual exit10/wanted99, and reports
all four controls passed. This tests whether the claimed negative controls catch the
validator defect; it is not a claim that the original positive predicate ignored exits.
Route positive and negative observations through the same validation function, assert
expected failure, and mutation-test removal of each critical predicate. Include a
real bounded owned-helper timeout and sibling cleanup, not a parser error substitute.

## N4 / P2 — lease report contradicts the observed journal and omits reload

The native C06 output has `release_checkpoint_present_after=true` but its prose says
the executor proceeded without a durable release checkpoint. `released_any` means
the port was called, not that release happened. The expected predicate never checks
the asserted journal fact. This confuses the WO205 port-contract decision.

The required truthful ACTIVE-lease-after-checkpoint test is still missing: C06 calls
execute_next with ACTIVE facts before release, then switches to a synthetic RELEASED
positive fixture. Independent replay of the missing next step shows:

| Step | Result |
|---|---|
| First ACTIVE call, odd port returns both false | RELEASE_REQUIRED, release checkpoint present |
| Reopen job/events; retain ACTIVE lease; execute again | RECOVERY_REQUIRED / LEASE_RELEASE_CONTRADICTION |
| Total release calls; resulting job | 1; REVIEW_PENDING |

This supports the existing fail-closed reconciliation gate. Keep F2 as the separate
question that the release outcome flag is ignored; do not infer a COMPLETE bypass.
Derive facts from reopened state, assert no repeated effect, and describe the actual
checkpoint rather than injecting one while labeling it observed.

## Evidence and next action

Ignored reviewer evidence under `runs/WO-P1-208/rereview/`:
`native-mac/replay.json` plus entry logs/summaries; `controls.py` and
`controls/proof.json`; `lease-truth/proof.json`. Reduced reproductions above are durable
and refer only to the tracked exact candidate, so no Windows ignored files are needed.
All experiments used owned synthetic stores/files/processes; no providers, secrets,
real leases, source mutation, power-loss or cross-host effect safety claims.

The user explicitly requests further sustained GLM work. Issue one same-WO finalization
packet targeting N1–N4 and end-to-end oracle validation. Do not rerun already accepted
R1/R4 archaeology or create another controller. Packet:
[GLM-WO208-CLOSEOUT-FINALIZATION.md](../prompts/GLM-WO208-CLOSEOUT-FINALIZATION.md).
The prior bounded repair stopped for this independent adjudication; the new packet is
an explicit next pass, not an automatic retry or scope expansion into production.
WO220/219/221/222 remain Sol-owned; no duplicate C0 review. Parent final acceptance
and global CURRENT-WORK/handoff fold remain with the existing integrator.
