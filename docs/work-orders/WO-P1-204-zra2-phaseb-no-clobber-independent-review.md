# WO-P1-204 — Independent exact-SHA review of repaired ZRA-2 Phase-B no-clobber publication

Status: PREPARED / WAIT_PR281_TERMINAL_CI
Owner: independent GLM-5.3 / ZCode reviewer only
Integrator: GPT-5.6 Sol
Parent authority: WO-P1-165 / Issue #214
Parent candidate: PR #280 / `865ef3c18ebc5f4fb0f34f40dcee6851295baee4`
Repair candidate: PR #281 / `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`
Review branch: `review/wo-p1-204-zra2-phaseb-no-clobber`
Packet base: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Risk: R3 independent acceptance review

## 1. Purpose

Perform a genuinely independent review of the repaired Phase-B tree without becoming a co-author of the candidate.

The reviewer must answer whether the combined tree represented by exact repair SHA `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` closes the independently reproduced deterministic-path clobber race while preserving all existing authority boundaries.

This is a review lane, not an implementation lane.

## 2. Immutable review target

Review exactly:

- parent GLM candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4`;
- bounded GPT repair: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`;
- stacked PR #281 base/head relationship must match those identities.

If PR head/base drifts, hosted CI is not terminal green, or the branch no longer represents that stack, record `SOURCE_DRIFT` / `EXTERNAL_GATE` and STOP. Do not silently review a different tree.

## 3. Writable scope

Reviewer may write only review-lane evidence:

- `runs/WO-P1-204/**` (ignored/local evidence as repository policy permits);
- `docs/reviews/WO-P1-204-zra2-phaseb-no-clobber-review.md`;
- append-only checkpoint/result text in this WO if needed.

Candidate source/tests in PR #280/#281 are READ-ONLY.

Do not commit any change to:

- `src/a_conductor/native_execution.py`;
- `src/a_conductor/zero_relay_repair_materializer.py`;
- `tests/test_native_execution.py`;
- `tests/test_zero_relay_repair_materializer.py`;
- parent/repair branches.

Do not merge, rebase, reset, cherry-pick, amend, or force-push candidate branches.

## 4. Review context

Phase B materializes exactly one deterministic generation-1 repair task using existing authorities.

Frozen contract:

- deterministic path and `task_contract_ref` bind exact rejected task/result/reason/generation/rendered bytes;
- same exact identity + same bytes => idempotent reuse;
- same deterministic path + different bytes => typed `REPAIR_TASK_COLLISION`;
- generation exactly one;
- no second scheduler/review/provider/lease/retry/filesystem authority;
- persisted bytes must equal returned `TaskPacketFile.sha256`.

Independent review of the parent candidate found a P1 TOCTOU gap:

1. initial read observes deterministic target absent;
2. materializer calls existing `NativeFileSystem.write_text()`;
3. another actor creates different bytes after target precheck but before final `os.replace()`;
4. `os.replace()` silently clobbers that artifact;
5. materializer re-reads its own bytes and returns success.

Exact-parent reproducer reported:

```text
INJECTED=True
FINAL_IS_CONFLICT=False
OUTCOME=RETURNED_PACKET
```

The repair adds an additive `NativeFileSystem.create_text_if_absent()` and changes only the materializer publication call/reconciliation path. Existing `write_text()` semantics must remain unchanged.

## 5. Required independent questions

The review must explicitly answer all of these.

### A. Exact identity / stack

1. Does local target HEAD equal `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`?
2. Is its parent history rooted in exact GLM Phase-B candidate `865ef3c18ebc5f4fb0f34f40dcee6851295baee4`?
3. Does PR #281 still point base `feat/wo-p1-195-zra2-phase-b-materializer` and exact head above?
4. Are all hosted CI jobs terminal `SUCCESS` for exact repair SHA before substantive acceptance review proceeds?

If any answer is no/unknown: STOP external/drift gate.

### B. Authority architecture

5. Is `create_text_if_absent()` an additive method under existing `NativeFileSystem` / `NativeExecutionScope`, rather than a new independent path authority?
6. Does the materializer avoid raw `Path.open`, `os.open`, `os.link`, `os.replace`, or absolute path publication?
7. Are scheduler/provider/review/lease/job/retry authorities unchanged?
8. Is existing `NativeFileSystem.write_text()` behavior byte-for-byte/semantic-compatible with the parent candidate?

### C. No-clobber semantics

9. Does publication ensure an already-existing target is never replaced?
10. Does a target created after precheck but before publication survive untouched?
11. Is `FileExistsError`/equivalent mapped to a bounded typed `FILE_ALREADY_EXISTS` signal?
12. Are unsupported/other hard-link errors fail-closed as `FILE_WRITE_FAILED` rather than falling back to clobbering rename/replace?
13. Is the temporary file same-directory, fully written, flushed and fsynced before publish?
14. Is temp cleanup bounded/best-effort and unable to delete the final target?
15. Does successful publication expose complete bytes atomically rather than a partially written final file?

### D. Materializer reconciliation

16. On `FILE_ALREADY_EXISTS`, does exact re-read of same bytes return the same logical `TaskPacketFile`?
17. Do different bytes map to `REPAIR_TASK_COLLISION`?
18. Does missing/vanished/unverifiable raced state fail closed rather than blind retry?
19. Can two concurrent same-input callers converge on one packet without clobber?
20. Does the repair retain generation=1 and all prior exact digest/reason/path contracts?

### E. Adversarial/portability questions

21. Reproduce the different-byte target race independently on the repaired candidate and prove the conflicting bytes survive.
22. Run same-path concurrent creators repeatedly and check exactly one physical create winner at `NativeFileSystem` level.
23. Verify materializer same-input concurrency converges repeatedly.
24. Challenge symlink/root confinement: the new primitive must inherit the existing scope boundary and must not create outside root.
25. Check directory/non-file target, missing parent, mutation disabled, file-size bound and invalid content behavior.
26. Check exact UTF-8 size/hash including non-ASCII text.
27. Reason explicitly about `os.link` semantics on Windows and hosted Linux/macOS; do not claim unsupported network/remote filesystem guarantees.
28. Look for a new TOCTOU introduced by resolving a path before hard-link publication. Classify any unsupported filesystem/reparse/shared-network case honestly; UNKNOWN must not become SAFE.

### F. Test quality / falsification

29. Are race tests testing real `NativeFileSystem` publication rather than only fake subclass behavior?
30. Is at least one concurrency test barrier-driven rather than sleep-dependent?
31. Could any monkeypatch accidentally make the test pass without exercising production code?
32. Does the test suite include positive controls and preserve legacy `write_text()` regression coverage?
33. Attempt at least one new counterexample not authored in PR #281.

## 6. Verification floor

Run at minimum on exact target:

```text
python -m pytest -q tests/test_native_execution.py tests/test_zero_relay_repair_materializer.py
python -m pytest -q tests/test_agent_change_packets.py tests/test_claude_code_harness.py
python -m pytest -q tests/test_zero_relay.py tests/test_review_mailbox_adapter.py tests/test_goal_closeout.py
python -m compileall -q src/a_conductor/native_execution.py src/a_conductor/zero_relay_repair_materializer.py
git diff --check <parent>..<repair>
```

Then run focused adversarial repetitions where useful. Do not mutate tests in the candidate to make them pass.

## 7. Severity rules

- P0/P1/P2 blocking finding => `CHANGES_REQUIRED`.
- P3 only => may PASS with advisory if all R3 obligations hold.
- test/CI/source drift => `BLOCKED` / `SOURCE_DRIFT`, not PASS.
- unsupported environment claim => retain as gap; do not fabricate proof.

A candidate authored by GPT must not be accepted merely because GPT's local tests are green.

## 8. Required review result

Write a durable review document containing:

- exact repo/branch/target SHA;
- parent candidate SHA;
- PR #281 base/head and terminal CI evidence;
- commands/tests and results;
- independent counterexamples attempted;
- findings table with P0/P1/P2/P3;
- explicit answers to sections A–F;
- verdict: exactly one of `PASS`, `CHANGES_REQUIRED`, `BLOCKED`, `SOURCE_DRIFT`;
- `merge_performed=false`;
- next safe action.

The review document must not claim source mutation or merge authority.

## 9. Stop gates

STOP immediately after durable checkpoint if:

- PR #281 CI is non-terminal or failing;
- target SHA/base drifted;
- required repo/worktree is dirty for unexplained reasons;
- review would require source mutation;
- candidate behavior is ambiguous/UNKNOWN;
- GPT acceptance/merge/post-main verification is next.

Do not poll CI in a loop. Do not switch to unrelated work to bypass a gate.

## 10. Acceptance boundary

This WO can independently recommend PASS/CHANGES_REQUIRED only.

GPT/integrator owns final R3 adjudication and any merge/release decision after consuming this exact-SHA review.
