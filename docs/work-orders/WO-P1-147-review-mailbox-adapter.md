# WO-P1-147 — Thin cross-repo review mailbox adapter

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: CLAIMED / RED_FIRST
Priority: P1
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo147-review-mailbox-adapter`
Branch: `feat/wo-p1-147-review-mailbox-adapter`
Base: `origin/main@cf2a4e7a57bfd22ec55de79c700ec3e4931dc475`

## Dependency proof
A-Wiki Review Bridge exact head `b04761d580ddcdc7eb682e3a6036078b3b346953` passed independent rereview P0/P1/P2=0, merged as `588a907200e0d4998ec4fbb7fb2178b89d9700b2`, and post-main Core CI `33704270521` is SUCCESS.

## Reuse-before-build
Classification: `REUSE + WRAP`.
- REUSE `AgentMailboxAssignment` / `agent-mailbox/v1` and atomic mailbox publisher.
- REUSE `NativeSubprocessRunner` as the bounded command boundary.
- WRAP only the accepted A-Wiki `python -m conductor review ingest ... --json` CLI.
- Do NOT use `AgentResultFileReader`; it is the code-change packet parser.
- Do NOT import A-Wiki internals, read `.tmp/review-bus`, or create lifecycle/state/scheduler/provider authority.
## Mutable scope
- new `src/a_conductor/review_mailbox_adapter.py`
- new `tests/test_review_mailbox_adapter.py`
- this work order only

Forbidden: shared SSoT/hotspots, PR #183 files, WO145 files, existing mailbox implementation, provider/store/UI/runtime files, A-Wiki files, live Workers/tunnels/credentials.

## Contract
1. Read only the exact `task_ref` and `result_ref` declared by `AgentMailboxAssignment`.
2. Recompute `task_ref` SHA-256 and require equality with `task_sha256`.
3. Bounded result JSON must bind `task_id`, `provider_id`, `model_id`, `reviewed_head`, and `task_sha256` to the assignment.
4. Sanitize to A-Wiki review fields only: task_id, reviewed_head, verdict, findings, model, task_sha256.
5. Never forward reviewer-supplied retest/CI/READY/merge evidence.
6. Invoke only the accepted A-Wiki `conductor review ingest` CLI through injected `NativeSubprocessRunner` with `mutation_intent=True`.
7. Fail closed on timeout, truncation, nonzero exit, malformed/bounded JSON, or response task mismatch.

## Acceptance
RED first for identity mismatches, oversized result, task hash drift, trusted-field stripping, exact argv/mutation intent, and bounded command failures. Then focused + related native execution/mailbox regression, realistic local A-Wiki CLI E2E, compile/diff/UTF-8/secret/scope audits. Independent exact-SHA review remains required before PR merge.


## Checkpoint — 2026-09-03 dependency-blocked unit layer

- RED contract was committed first (`b006fd8e`, then hardening RED `23a1a404`).
- Current adapter unit layer is GREEN: `tests/test_review_mailbox_adapter.py tests/test_native_execution.py tests/test_agent_change_packets.py` = **76 passed**; `py_compile` PASS.
- Adapter validates mailbox task/provider/model/base-head/task-hash, strips reviewer-forged trusted fields, rebuilds the A-Wiki payload, and uses the existing bounded `NativeSubprocessRunner`; it does not use `AgentResultFileReader`.
- Realistic E2E is intentionally BLOCKED: accepted A-Wiki `conductor review` still binds Git truth to A-Wiki itself. GPT opened the existing A-Wiki Review Bridge follow-up lane on `feat/wo-review-target-repo-20260903`; RED there is **9 failed / 62 passed** at `de390f7516563e120aca1e3e3a3ca9c782a989b2`.
- Do not open a WO147 PR or claim completion until the A-Wiki target-repo seam is independently accepted/merged and this adapter forwards `--target-repo <assignment.worktree>` through that approved CLI.
- Next safe action after A-Wiki acceptance: update the forwarder argv, run cross-repo realistic open→ingest→retest→CI→READY E2E, then independent exact-SHA review.
