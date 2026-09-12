/goal

Execute WO-P1-221 only after its external release gate is explicitly OPEN.

PRIMARY WORK ORDER:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo221-zra2-direct-review-result\docs\work-orders\WO-P1-221-zra2-direct-review-result-contract.md

ROLE:
You are ZCode GLM-5.3 working as the long-shift implementation/research executor under GPT-5.6 Sol integration authority. This packet is deliberately HOLD unless WO220 adjudication and GPT release say otherwise.

STARTUP / AUTHORITY GATE:
1. Read repository entry/governance routing, AGENTS.md and DEFECT_LESSONS.md as required.
2. Re-pin actual origin/main, repo/worktree/branch/HEAD/dirty state, Issue #214, WO220 verdict, C0 accepted exact SHA, C0 merge/post-main state, owner/claim/scope and hosted CI.
3. Read WO221 completely and compare its creation-time archaeology with current source.
4. If WO220 has not confirmed a bounded direct-review result-contract gap OR GPT has not explicitly released WO221 OR C0 is not accepted+merged+post-main-verified: write durable checkpoint and STOP.
5. Do not reinterpret an old packet SHA as current authority after source drift.

LONG-SHIFT CONTRACT:
Use the full useful work budget inside the one currently authorized WO221 scope. Keep durable rolling notes/checkpoints/evidence so context compression or another invocation can resume without restarting. Do not poll external gates and do not switch to unrelated backlog.

OBJECTIVE IF RELEASED:
Close the direct ZCode reviewer-result provenance gap without fabricating mailbox identity, duplicating execution/review stores, importing A-Wiki internals, or weakening READ_ONLY review execution.

PREFERRED ARCHITECTURE TO TEST/FALSIFY FIRST:
- exact reviewer response bytes come from durable ZCode stdout artifact;
- zcode-report/1 binds execution_id + task_contract_ref + task_packet_sha256 + response_bytes + response_sha256;
- DurableExecutionRecord supplies trusted reviewer execution/job/project/worker/repo/branch/head/state/artifact refs;
- accepted C0 DirectReviewRoute supplies exact author/review contract/head/provider/model/project/worktree/branch/execution bindings;
- C1 strictly parses one machine-readable review result schema and composes existing zero_relay.ReviewEvidence;
- no reviewer prose may mint ready/merge/complete/retry authority.

PROTOCOL VERSION RULE:
If the accepted C0 task currently lacks a strict machine-readable response contract and task bytes must change, do NOT silently change bytes under the same zra2-review-v1 identity/path. Introduce an explicitly versioned review protocol identity so deterministic contract ref/task path/result identity also changes with protocol semantics. If doing this requires C0 source re-open/re-review, checkpoint that exact dependency and STOP rather than pretending C1 can repair it downstream.

ARCHAEOLOGY FIRST:
Trace actual production ownership and call paths for:
- C0 DirectReviewRoute or final accepted equivalent;
- zcode_runner / zcode_supervised_helper stdout + report persistence;
- DurableExecutionRecord and execution store terminal-state semantics;
- execution_artifacts confinement/hash behavior;
- any existing direct result parser/reader;
- ReviewMailboxResultReader and ReviewResultForwarder only to avoid duplicate lifecycle, not as forced direct-route dependencies;
- ReviewEvidence + classify_relay_decision consumers;
- whether ReviewBridge confirmation is policy-mandatory for direct ZCode results.

If an existing trusted reader/composer already solves the problem, reuse/wrap it. Do not build a parallel lifecycle.

RED-FIRST REQUIREMENTS IF SOURCE IS RELEASED:
Before implementation, create failing tests for at least:
1. exact ACCEPTED result -> exact ReviewEvidence;
2. exact REJECTED result -> ReviewDisposition.REJECTED;
3. stdout SHA mismatch vs zcode report;
4. response byte-count mismatch;
5. wrong report execution id;
6. wrong review task contract/hash;
7. wrong reviewed HEAD / stale old-head response;
8. wrong review contract ref;
9. author result/attempt/generation replay;
10. reviewer execution equals author execution;
11. wrong worker/project/repo/worktree/branch/head durable execution identity;
12. nonterminal / RECOVERY_REQUIRED / VERIFICATION_REQUIRED / FAILED / PARTIAL / CANCELLED execution cannot authorize ACCEPTED;
13. missing stdout/report/result artifact as applicable;
14. malformed JSON, duplicate-key ambiguity, non-object root;
15. unknown schema / truthy verdict aliases / arbitrary authority fields;
16. oversized, binary or invalid UTF-8 reviewer response;
17. TOCTOU-shaped durable artifact mutation around validation;
18. same result rebound to another C0 route;
19. deterministic identical replay;
20. no mutation of scheduler/provider/lease/job/review/execution authorities by the pure validator/composer.

TEST VACUITY:
At least one new independent probe must discriminate pre-repair vs repaired behavior. Prefer deterministic byte mutation, controlled temp roots, exact hashes and typed state transitions over sleeps.

IMPLEMENTATION BOUNDARY:
Prefer a narrow pure/bounded module such as src/a_conductor/zero_relay_review_evidence.py with focused tests. A validated DirectReviewResult typed value is acceptable only after durable artifact verification. Do not mutate ReviewMailboxResultReader merely to force direct ZCode into mailbox semantics.

FORBIDDEN WITHOUT SEPARATE GPT SCOPE RELEASE:
- A-Wiki repository mutation or internal imports;
- fabricated AgentMailboxAssignment / mailbox agent_id mapping;
- new execution store, review store, result store or lifecycle state machine;
- scheduler/provider/lease/job authority redesign;
- Phase D / ZRA-3 / ZRA-4 source;
- live Worker/provider/runtime/credential changes;
- changing accepted C0 protocol bytes under the same version/identity;
- self-acceptance, merge or release of downstream phases.

VERIFICATION FLOOR AFTER GREEN:
Run focused tests plus relevant zero_relay, ZCode stdout/report, execution record/store/artifacts, supervised execution, C0 route, mailbox adapter (non-regression only) and Phase-A decision tests justified by actual call paths. Run compile/import, diff/scope, strict UTF-8/U+FFFD and secret-like added-line checks. Expand only from a concrete hypothesis.

HANDOFF:
Freeze one exact candidate SHA/PR with durable work-order/result evidence. Report exact base/head, changed paths, RED evidence, GREEN/regression evidence, any architecture gap, P0/P1/P2/P3 count, hosted CI state and next safe action.

At FIRST external gate (CI nonterminal/failure, GPT acceptance, merge, missing authorization, source drift, ownership conflict, ReviewBridge policy decision, or UNKNOWN authority), persist checkpoint and STOP. Do not poll/wait or jump to another backlog item.
