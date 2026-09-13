# WO226 combined candidate — CHANGES_REQUIRED, one remaining R1/AF2 regression

Reviewer: Poppy Javis / GPT Astra, 2026-09-13.
Candidate cc398d6b1bff329d7145d0a98662add108b423ab, PR314; predecessor609a878.
Claim WO226-ASTRA-COMBINED-REVIEW-001 (Issue214 comment5649883456).

**AF1–AF4 original counterexamples now PASS.** Do not repeat their old open counts.
One P1 remains where the new AF2 terminal cleanup bypasses preserved R1 generation
binding. This is a composition regression within the existing released two-file
repair, not a new feature or scope expansion.

## Closed original cases and verification

Original probes copied byte-for-byte from5df9ebe: **4 passed**, 0.48s; original-af.txt.
Focused WO226/assembly/composition plus GraphDispatch, JobExecution, provider
execution authority, lease/recovery, ParallelReady and ZCode runner/authority
assembly: **282 passed, 6 skipped**, 2.12s; regression.txt. Six skips are Windows
real-helper integration tests on macOS/Python3.12. No full battery/live model run
by Astra. GLM's2900 total is its handback claim, not an independently rerun total.

| Original finding | Exact current result |
|---|---|
| AF1 | Concurrent losing dispatch retains barrier-paused winner's ACTIVE resources. |
| AF2 | FAILED terminal with exact generation releases resources without handoff. |
| AF3 | Foreign-worker post-run record yields recovery and no handoff. |
| AF4 | TASK_NETWORK_DENIED fails before any synthetic effect or resource acquire. |

## CR1 — P1: terminal-unusable cleanup drops required generation authority

Source `src/a_conductor/zero_relay_review_execution.py`, function
`_terminal_unusable_cleanup`, lines1140–1174. Its call to the R1 read-only lookup
passes **expected_generation=None** (line1161), despite caller
`reconcile_review_execution` receiving the required current generation. This
explicitly disables the R1 unknown/mismatch checks. The helper also consumes typed
identity errors without returning their reason; preserve typed evidence in repair.

Reproduction uses canonical SQLite stores and public APIs, no SQL injection,
network, fake admission-store port or source changes:

1. Exact completed-equivalent record and active lease, provider/execution/batch
   all match the plan; provider snapshot generation1.
2. Canonical acquire_admission persists a NULL generation when called without the
   optional expected generation (same supported fixture as the accepted R1 RED).
3. Durable record becomes FAILED, PARTIAL, or CANCELLED; call execute_review_dispatch.
4. Observe RECOVERY_REQUIRED/EQUIVALENT_TERMINAL_NOT_USABLE with **admission RELEASED
   and lease released**, despite required generation1 versus persisted NULL.

R1 explicitly requires unknown generation to retain both resources: identity is
unproven. Terminality authorizes cleanup only after exact resource authority is
proven. The result does not create a usable handoff; the defect is premature
resource release contrary to that identity gate. No second model call observed.

The nine-case cross-product proves **3 failed, 6 passed** (0.31s):

| Terminal state | Exact gen1 | Missing generation | Wrong batch |
|---|---|---|---|
| FAILED | PASS: releases | FAIL: releases, must retain | PASS: retains |
| PARTIAL | PASS: releases | FAIL: releases, must retain | PASS: retains |
| CANCELLED | PASS: releases | FAIL: releases, must retain | PASS: retains |

See test_terminal_binding.py and terminal-binding.txt. Three REDs are one root
cause. Wrong-generation checks are disabled by the same None argument by source
inspection; the executable matrix here proves missing generation specifically.

## Reproduce

```sh
python3 -m pytest -q -s docs/reviews/wo226-astra-combined/test_adversarial.py
python3 -m pytest -q -s docs/reviews/wo226-astra-combined/test_terminal_binding.py
```

First command passes4; second fails3/passes6 on frozen cc398d6. Text outputs have
only trailing spaces normalized. identity.json pins source and original probe.
Source/tests untouched relative to candidate; git diff-check and UTF-8 pass.

## Existing-owner bounded continuation

Sol/Astra verdict: CHANGES_REQUIRED on cc398d6; retain acceptance/merge gate.
Original WO-P1-226-REPAIR-R1-GLM-001 owner resumes the already-released packet:
`A:/GitHub/_worktrees/A-Wiki-Conductor-wo226-repair-r1/docs/prompts/GLM-WO226-REPAIR-R1.md`.

Within existing source/test scope, carry expected generation from the caller into
terminal-unusable cleanup and its exact read-only admission lookup; unknown or
wrong required generation must retain both resources, no handoff/relaunch/new rows.
Keep canonical typed mismatch/read/cleanup reasons available to reconciliation.
Do not infer generation from the admission row or invent new policy/store authority.
Port the cross-product REDs, preserve exact-generation cleanup and wrong-batch
retention plus all4 original AF tests and R1. Cover required wrong generation with
a truthful applicable fixture/authority path too, then freeze one new exact SHA
for independent review. No new human scope permission is needed for preserving
already-released R1 in AF2; original DESIGN_GAP/scope-expansion stops still apply.

Update runs/WO-P1-226/result.md in original owner worktree; Sol/Astra read it
directly. No duplicate GLM session or merge. Root continuity remains Sol-owned.
