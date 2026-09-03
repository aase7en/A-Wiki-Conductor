# WO-P1-147 — Thin cross-repo review mailbox adapter

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: READY_FOR_INDEPENDENT_REVIEW
Priority: P1
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo147-review-mailbox-adapter`
Branch: `feat/wo-p1-147-review-mailbox-adapter`
Base reconciled: `origin/main@6e96b773aeb0795807cb65abce93956b7702f33e` via merge commit `f8402d3ea8500b7014bea0ec273c046548c63100`

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
7. Fail closed on timeout, truncation, nonzero exit, malformed/bounded JSON, response schema mismatch, or response task mismatch.

## Acceptance
RED first for identity mismatches, oversized result, task hash drift, trusted-field stripping, exact argv/mutation intent, and bounded command failures. Then focused + related native execution/mailbox regression, realistic local A-Wiki CLI E2E, compile/diff/UTF-8/secret/scope audits. Independent exact-SHA review remains required before PR merge.


## Checkpoint — 2026-09-03 dependency-blocked unit layer

- RED contract was committed first (`b006fd8e`, then hardening RED `23a1a404`).
- Current adapter unit layer is GREEN: `tests/test_review_mailbox_adapter.py tests/test_native_execution.py tests/test_agent_change_packets.py` = **76 passed**; `py_compile` PASS.
- Adapter validates mailbox task/provider/model/base-head/task-hash, strips reviewer-forged trusted fields, rebuilds the A-Wiki payload, and uses the existing bounded `NativeSubprocessRunner`; it does not use `AgentResultFileReader`.
- Realistic E2E is intentionally BLOCKED: accepted A-Wiki `conductor review` still binds Git truth to A-Wiki itself. GPT opened the existing A-Wiki Review Bridge follow-up lane on `feat/wo-review-target-repo-20260903`; RED there is **9 failed / 62 passed** at `de390f7516563e120aca1e3e3a3ca9c782a989b2`.
- Do not open a WO147 PR or claim completion until the A-Wiki target-repo seam is independently accepted/merged and this adapter forwards `--target-repo <assignment.worktree>` through that approved CLI.
- Next safe action after A-Wiki acceptance: update the forwarder argv, run cross-repo realistic open→ingest→retest→CI→READY E2E, then independent exact-SHA review.
## Checkpoint — 2026-09-03 target-repo dependency accepted / realistic E2E GREEN

- A-Wiki target-repo repair PR #51 exact head `8875ecf85b023da32530064d07437d47c49eef38` passed independent GLM rereview P0/P1/P2=0 and all PR gates, merged as `2191f2a1ff4bccc5ebb08b1d2bc87fdbe7ca0826`; post-main Core CI `33715627421` SUCCESS.
- WO147 was reconciled with current A-Conductor main in merge commit `f8402d3ea8500b7014bea0ec273c046548c63100`; feature delta remained exactly this WO + adapter + focused tests.
- New target-forwarding RED commit `7c14041`: focused result **1 failed / 21 passed** because `--target-repo` was absent.
- Source repair commit `047d9f51e4342f27c3ade5b1194605b05aa6bd17`: forwards only `--target-repo <assignment.worktree>` to the accepted A-Wiki CLI. No new review lifecycle or authority.
- GREEN focused = **22/22 PASS**. Related mailbox/native/agent-change/native-operations matrix = **91/91 PASS**. `py_compile`, `git diff --check`, UTF-8/U+FFFD, and three-file scope gates PASS.
- Realistic cross-repo E2E used detached accepted A-Wiki main `2191f2a1...`: mailbox result -> patched forwarder -> A-Wiki ingest -> trusted retest -> trusted CI -> status READY with `allow_complete=true` at reviewed head `047d9f51...`; target worktree remained clean.
- Pre-repair E2E had failed closed as `AWIKI_REVIEW_FORWARD_FAILED`, proving the missing target argument was the actual dependency gap.
- Candidate is now READY_FOR_INDEPENDENT_REVIEW; exact-SHA review + PR/CI + post-main remain mandatory before claim release.
## Checkpoint — 2026-09-03 protocol hardening after GPT exact-head review

- GPT adversarial review found A-Wiki response schema was not pinned: missing schema and `awiki-review-bridge/v2` were accepted.
- RED commit `a992262`: focused **2 failed / 22 passed** on missing/wrong schema.
- Repair commit `aa91f80aa2343aa0e43ae6e5f4e9c612556f75bb` requires exact `awiki-review-bridge/v1`; focused **24/24 PASS**, related matrix **93/93 PASS**.
- Realistic cross-repo E2E repeated against accepted A-Wiki main `2191f2a1...` and reached READY / `allow_complete=true` at reviewed head `aa91f80...`; target worktree remained clean.
- `awiki_root` is a trusted operator/configuration input to the factory, never reviewer/mailbox-controlled. This WO does not create a second repository-identity authority; callers must supply the accepted A-Wiki authority root.
- Final candidate still changes exactly three files. Independent exact-SHA review, PR CI, expected-head merge, and post-main verification remain mandatory.
