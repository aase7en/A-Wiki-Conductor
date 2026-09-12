/goal

Execute WO-P1-223 only after its conditional release gate is satisfied.

PRIMARY WORK ORDER:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo223-zra2-review-v2-c1\docs\work-orders\WO-P1-223-zra2-review-v2-direct-evidence.md

ROLE:
You are ZCode GLM-5.3 MAX acting as the bounded long-shift implementation/research executor. GPT-5.6 Sol is the architecture, trust-boundary, acceptance, merge and release authority.

PRIMARY REPOSITORY:
A:\GitHub\A-Wiki-Conductor

MASTER OUTCOME:
Close the remaining ZRA-2 direct-review semantic-result gap by versioning the accepted review-task protocol instead of silently changing v1, then compose existing `zero_relay.ReviewEvidence` only from exact durable reviewer execution/artifact truth.

Do not create a second scheduler, provider authority, WorkerLease authority, execution store, review store, mailbox identity system, ReviewBus, retry engine or lifecycle state machine.

## G0 — cold-start recovery / release gate

Before source mutation:

1. Read `00-AGENT-ENTRY.md`.
2. Read `PROJECT-GRAPH.yaml` and route only the nodes relevant to ZRA / engineering / review / release.
3. Read repo `AGENTS.md`.
4. Read `DEFECT_LESSONS.md` before touching `src/a_conductor/`.
5. Read the WO223 file above in full.
6. Re-pin actual `origin/main`, repo/worktree/remote/branch/HEAD/dirty state.
7. Read Issue #214 latest durable checkpoints, especially C0 POST_MAIN_VERIFIED / WO221 RELEASE and the direct-review/ReviewBridge architecture decision.
8. Inspect WO221's actual current handoff/result. Do not trust this prompt's expectation if WO221 found contrary source evidence.
9. Recover live claims/open PRs/worktrees that touch any proposed WO223 mutable path.
10. Verify current source lane is a fresh isolated worktree from then-current main. If this docs packet branch is not the released source lane, create/use a separate clean source branch/worktree only after the claim is published.
11. Verify no overlapping GLM/GPT/Worker lane owns the same source/test paths.

If WO221 has not confirmed the strict semantic-result gap, or it found an existing accepted equivalent reader/schema, or source ownership is UNKNOWN, checkpoint and STOP.

Do not mutate from the old WO221 docs worktree merely because the file exists.

## G1 — production archaeology / reuse map

Trace actual production call paths, constructors and ownership for:

- `zero_relay_review_task.MaterializedReviewTask`
- `zero_relay_review_task.DirectReviewRoute`
- current direct ZCode review route assembly
- `ParallelReadyTask`
- `DurableExecutionRecord`
- execution store terminal-state transitions / rereads
- `ExecutionArtifactService`
- in-process `zcode_runner` report production
- `zcode_supervised_helper` report production + collector path
- `supervised_execution` / `supervised_run_coordinator` when actually used
- any existing strict JSON/duplicate-key parser helpers
- `zero_relay.ReviewEvidence`
- `ReviewDisposition`
- `classify_relay_decision`
- `ReviewMailboxResultReader` / `ReviewResultForwarder` only to prove non-duplication
- any production direct ReviewBus/ReviewBridge caller

Write a compact reuse table:

`seam | exact path/symbol | current authority | REUSE/WRAP/EXTEND/NOT_USED | gap | mutable?`

Fresh architecture facts to test rather than assume:

- accepted v1 binds task provenance/route/HEAD but lacks strict whole-response semantic JSON;
- `zcode_runner` and `zcode_supervised_helper` do not expose identical `zcode-report/1` fields;
- direct C1 does not require fabricated mailbox `agent_id` or mandatory mailbox forwarding;
- raw captured stdout bytes, not replacement-decoded text, are semantic evidence;
- artifact full digest and raw read are separate operations, so C1 must detect digest/raw mismatch on the captured whole response.

If source disproves any premise in a way that changes trust architecture, checkpoint `DESIGN_GAP` with exact evidence and STOP for GPT.

## G2 — RED first: protocol v2

Before production code, add deterministic failing tests for the v2 review protocol.

Required minimum:

- v1 and v2 for same author+HEAD have different contract identity/digest/path/task SHA;
- v1 remains bit-stable and regression-safe;
- v1 artifact cannot bind v2 result;
- v2 task explicitly requires JSON-only whole response;
- v2 result schema/ref/task-hash/reviewed-head semantics are deterministic;
- semantic protocol change changes identity-bearing bytes;
- author ResultIdentity and reviewed HEAD anti-replay remains intact;
- v2 cannot reuse a v1 deterministic path/result destination.

Capture focused RED evidence before implementation.

## G3 — GREEN + falsify protocol v2

Implement the smallest extension in `src/a_conductor/zero_relay_review_task.py` that preserves v1 historical semantics and adds explicit successor protocol identity.

Recommended label: `zra2-review-v2`.

Do not silently modify existing v1 task bytes.

The v2 task must require one bounded JSON-only semantic response. Recommended response contract:

```json
{
  "schema": "zra2-review-result-v2",
  "review_contract_ref": "zra2-review-v2:<digest>",
  "reviewed_head": "<exact normalized git sha>",
  "review_task_sha256": "<exact review task sha256>",
  "verdict": "ACCEPTED|REJECTED",
  "findings": []
}
```

`findings` may be refined only as a bounded evidence field. It may not contain or create lifecycle authority.

After GREEN, attack:

- v1/v2 replay;
- HEAD replay;
- author result/attempt/generation replay;
- Unicode exact-byte behavior;
- raw path/prose injection into refs/path generation;
- semantic schema version differential;
- test vacuity (a silent-v1-mutation implementation must fail).

## G4 — RED first: direct semantic evidence

Create new focused tests for a bounded module such as:

`src/a_conductor/zero_relay_review_evidence.py`

Production code must not exist until intended REDs are captured.

Required RED matrix includes at least:

1. exact ACCEPTED response -> exact existing `ReviewEvidence`;
2. exact REJECTED -> existing `ReviewDisposition.REJECTED`;
3. malformed JSON;
4. duplicate keys;
5. non-object root;
6. invalid UTF-8;
7. Markdown fence/prefix/suffix;
8. unknown schema;
9. wrong review contract;
10. wrong review task SHA;
11. wrong reviewed HEAD;
12. stale old-HEAD response;
13. result rebound to another author result/attempt/generation;
14. alias/truthy verdict (`PASS`, `true`, `1`, lowercase shortcuts);
15. unknown authority-like fields (`ready`, `merge`, `complete`, `retry`, etc.);
16. oversized response;
17. truncated artifact slice;
18. excessive/oversized findings;
19. durable execution id mismatch;
20. reviewer execution == author execution;
21. wrong worker/project/repo/worktree/branch/head/work-order fact;
22. nonterminal execution;
23. failed/cancelled/recovery/verification-required state;
24. missing stdout/report artifact;
25. wrong/unknown report schema;
26. report execution id mismatch;
27. report task packet SHA mismatch;
28. report response byte-count mismatch;
29. report response SHA mismatch;
30. helper report with no task_contract_ref only succeeds if trusted record+route provide the missing contract binding;
31. in-process report task_contract_ref mismatch fails;
32. EXIT_PENDING report fails;
33. artifact full digest != `sha256(captured_raw)` fails closed;
34. captured slice offset != 0 or truncated fails;
35. identical replay is deterministic;
36. parser/composer cannot mutate scheduler/provider/lease/job/execution/review authorities.

At least one RED must deterministically fail on current main for the missing semantic contract, not merely fail because the new module is absent.

## G5 — implement bounded validator/composer

Implement the smallest trusted chain that current source archaeology supports.

Preferred conceptual flow:

```text
accepted author ResultIdentity
+ accepted C0/v2 DirectReviewRoute
+ durable reviewer execution record
+ exact captured report bytes
+ exact captured whole stdout bytes
    -> validate execution identity/state/artifact refs
    -> strict parse report shape actually produced by active path
    -> bind report execution/task-packet/response bytes/hash
    -> prove sha256(captured stdout raw) == artifact full digest
    -> strict UTF-8 decode captured raw
    -> strict duplicate-key-safe JSON parse
    -> validate zra2-review-result-v2
    -> cross-bind contract/task hash/reviewed HEAD
    -> prove reviewer != author execution
    -> map exact ACCEPTED|REJECTED
    -> existing zero_relay.ReviewEvidence
```

Rules:

- use captured `raw` bytes; do not parse replacement-decoded `.text`;
- require the whole response, offset 0, non-truncated;
- reject duplicate JSON keys;
- reject unknown authority-bearing fields;
- never copy author result/task identity from reviewer payload when trusted author ResultIdentity exists;
- never allow reviewer findings/prose to set ready/merge/retry/complete authority;
- never fabricate fields absent from the supervised-helper report;
- when report lacks task_contract_ref, cross-bind via trusted record/route only if current production assembly proves the relation;
- use existing typed record/store/artifact authorities instead of direct arbitrary filesystem reads unless WO223 explicitly permits an injected already-captured raw value in the pure parser layer.

A typed `ValidatedDirectReviewResult` is acceptable only after all durable artifact/result validations have passed.

## G6 — adversarial / fault campaign

After first GREEN, attack the implementation instead of just rerunning tests.

Required campaigns:

- mutate stdout between report creation and validation;
- mutate file between artifact digest pass and raw read using deterministic fault injection;
- old result vs new HEAD;
- old result vs changed author result SHA/attempt/generation;
- another execution's report with same provider/model;
- supervised-helper vs in-process report-shape confusion;
- duplicate-key last-wins attack;
- invalid UTF-8 / embedded NUL / oversized JSON;
- findings carrying lifecycle-looking keys/strings;
- forged route-like/materialized objects where type/provenance gates should reject;
- execution record version/state rollover around validation;
- artifact traversal/symlink attempts through existing artifact authority;
- parser test-vacuity challenge against permissive prose/JSON parser.

Use deterministic barriers/fault doubles; avoid sleep-based correctness when possible.

Any new P0/P1/P2: write reproducer first, repair only if within scope, otherwise checkpoint and STOP.

## G7 — regression / static / architecture fence

Run only suites justified by actual imports/call paths, at minimum:

- `tests/test_zero_relay_review_task.py`
- new `tests/test_zero_relay_review_evidence.py`
- `tests/test_zero_relay.py`
- `tests/test_execution_record.py`
- `tests/test_execution_store.py`
- `tests/test_execution_artifacts.py`
- relevant ZCode runner/helper/supervised execution/coordinator tests
- `tests/test_parallel_ready_execution.py`
- mailbox adapter non-regression if the module is consulted/imported
- relevant Phase-A classifier tests

Also:

- compile changed source;
- LSP diagnostics changed source/tests;
- `git diff --check`;
- strict UTF-8 / no U+FFFD;
- tracked + untracked scope audit;
- added-line secret-like scan;
- AST/import fence proving no new scheduler/provider/lease/store/ReviewBus/A-Wiki internal dependency;
- confirm v1 historical task bytes are unchanged.

Do not run an unrelated giant suite merely to consume time.

## G8 — self-review / candidate freeze

Before commit:

- compare actual diff to exact WO223 mutable scope;
- confirm no shared lifecycle/store authority was introduced;
- confirm no accepted v1 bytes/semantics changed;
- confirm v2 result parser is strict and duplicate-key safe;
- confirm both actual ZCode report paths are handled truthfully or unsupported path is explicitly fail-closed;
- confirm TOCTOU-shaped digest/raw mismatch is tested;
- confirm no mailbox agent id was invented;
- confirm no ReviewBridge clone or hidden mandatory mailbox dependency exists;
- confirm P0/P1/P2 unresolved count = 0.

Freeze one coherent candidate SHA.

Push the WO223 source branch and open/update a Draft PR.

Audit the actual remote diff against local scope.

Trigger normal hosted CI.

If CI is nonterminal: durable checkpoint `BLOCKED_EXTERNAL_CI` and STOP. Do not poll.

If CI fails: inspect once, classify root cause, repair only if clearly within WO223 scope; otherwise checkpoint/STOP.

If CI succeeds: checkpoint `BLOCKED_EXTERNAL_INDEPENDENT_REVIEW` and STOP.

Do not self-accept or merge.

## G9 — durable handoff

Persist a compact handoff containing:

- STATUS
- exact candidate SHA
- repo/worktree/branch/base
- PR
- exact changed paths
- production reuse map
- protocol version decision
- RED evidence
- GREEN evidence
- adversarial/fault findings
- report-path differences and how they were bound
- TOCTOU evidence
- verification results
- P0/P1/P2/P3 counts
- hosted CI state
- `merge_performed=false`
- exact next safe action for GPT-5.6 Sol

## External stop gates

STOP after checkpoint on any:

- WO221 says WO223 is unnecessary;
- architecture/source drift;
- overlap/claim conflict;
- scope expansion outside WO223;
- need to alter execution-store schema, artifact-service semantics, scheduler/provider/lease authority;
- ambiguous report/record binding with no trusted source;
- need to fabricate mailbox identity;
- live credential/runtime/provider action;
- hosted CI nonterminal/failure after freeze;
- independent review gate;
- GPT acceptance/merge/post-main gate;
- UNKNOWN authority.

Do not switch to Phase D, ZRA-3, ZRA-4, ODP or unrelated backlog merely to stay busy.

Use the full useful long-shift budget inside this one released lane, with nested goals and durable checkpoints. Token/context rollover is not a reason to lose state: checkpoint, recover from durable evidence, and continue only if the same WO remains READY.
