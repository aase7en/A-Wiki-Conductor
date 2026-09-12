# GLM Goal — WO-P1-226 Repair R1

Execute only this bounded repair. Do not merge.

## Bootstrap

1. Read `00-AGENT-ENTRY.md` -> `PROJECT-GRAPH.yaml` -> `AGENTS.md`.
2. Re-pin actual Git/GitHub state.
3. Read Issue #214 latest WO226 comments, PR #314, and:
   - `docs/work-orders/WO-P1-226-repair-r1-admission-replay-binding.md`
   - original WO226 packet/history as needed.
4. Verify PR #314 current exact head and that no other source owner is mutating the repair scope.
5. Create/publish a new bounded repair claim before source mutation. Reuse the existing WO226 source worktree/branch only if clean, owner-released, and exact-head matches GitHub; otherwise create a fresh isolated repair worktree/branch from PR #314 head.

## Repair target

The exact candidate `78ec598b9830d802f54eb47642130693a038a39c` was rejected by independent GPT R3 review because read-only replay accepts a provider admission with correct provider/execution but wrong `batch_id` and can produce `REUSE_COMPLETED` handoff with that wrong batch.

Canonical `SQLiteProviderConfigStore.acquire_admission()` treats batch drift / required generation drift as recovery. WO226 replay must preserve the same identity authority without acquiring a new admission.

Implement the smallest fail-closed repair:

- read-only admission replay must prove exact plan `provider_id`, `dispatch_execution_id`, `batch_id`, and required configuration generation BEFORE release/handoff;
- wrong batch, wrong generation, or missing required generation => typed `RECOVERY_REQUIRED`;
- do not release the mismatched admission or lease as if it were the current attempt;
- no usable handoff;
- zero new lease/admission acquisition caused by replay;
- exact identity replay remains valid and cleans up once.

## RED-first tests

Use real canonical stores. Add non-vacuous REDs for:

1. wrong batch;
2. wrong generation;
3. unknown generation when expected;
4. exact batch+generation positive replay;
5. zero new resource rows/acquisition on rejected replay.

Preserve every prior WO226 trust obligation and regression. Do not add schema/store/lock/journal or semantic C1 parsing.

## Expected mutable scope

Normally ONLY:

- `src/a_conductor/zero_relay_review_execution.py`
- `tests/test_zero_relay_review_execution.py`

If another path is truly required, STOP `SCOPE_EXPANSION_REQUIRED` with exact evidence before modifying it.

## Verification and handback

Run focused + directly related authority regressions, compile/import, diff-check, scope and secret-shape checks. Freeze one exact SHA and push PR #314. Record exact tests/results in the WO/Issue #214 and `runs/WO-P1-226/result.md` if that existing result surface is available.

Stop at `CANDIDATE_FROZEN_FOR_INDEPENDENT_REVIEW` with exact SHA and exact-head CI state. Never self-accept or merge.
