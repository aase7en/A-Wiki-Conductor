# WO-P1-580 Consumer Design Packet

Issue: #580

Status: DESIGN_ONLY / PROPOSED; not implementation or activation authority.
Date: 2026-10-23 UTC.
Author lane: design analyst `ses_e99c93518ffel6NNo7pp5WRTZo`.
Claim: [6354636697](https://github.com/aase7en/A-Wiki-Conductor/issues/580#issuecomment-6354636697).
Repository: `https://github.com/aase7en/A-Wiki-Conductor.git`.
Worktree: `A:\GitHub\_worktrees\AWC-wo580-design`.
Branch: `docs/wo580-consumer-design`.
Base: `6d7e7781bc5556ff7e731e77b96cf7ef86aab2ad` (local origin/main and remote main verified equal).
Historical PR550 head: `aa0201180803bcc14339a8c2532787655f78f337`.

## Boundary And Outcome

Only this document is writable in this lane. All source/tests/config are read-only;
CURRENT-WORK.md, handoff.md and COLLAB.md remain integrator-owned. This is an advisory
design for R3 CONTROL_PLANE_ONLY behavior, not an accepted architecture change.
Commit/push are authorized; PR/merge, live queue operations, provider calls, global
hook activation and runtime/process changes are not. GLM offload is not beneficial
for this already-delegated bounded architecture packet; no provider request was made.

Problem: connect the accepted #583 absence/duplicate check to the real enqueue/replay
boundary, without mistaking lifecycle context injection for execution enforcement.
Done for design means a source-backed call graph, alternatives, bounded prospective
scope, evidence/authority contracts, RED-first matrix and explicit unresolved gates.

Recommendation: WRAP the existing admitted enqueue/recovery caller with one bounded
consumer of #576 projections and #583 policy; EXTEND the hook only with compact
pre-effect guidance. Do not put queue transport or bootstrap orchestration in the
hook, or silently change the one-request Goal API translator into a scheduler.
The actual external enqueue owner/registration remains unidentified in accepted repo
source. That is an implementation-admission blocker, not a reason to invent a second
control plane or deliver another uncalled pure helper.

## Evidence And Current Architecture

All source observations below are pinned to the base above unless labeled PR550.
The full body and all 17 pre-claim comments returned by
`gh issue view 580 --json body,comments` were read (18 comments after this lane's
claim was posted). In particular:

- [6271911494](https://github.com/aase7en/A-Wiki-Conductor/issues/580#issuecomment-6271911494): no real guard caller, full pagination and late owner/result drift are required; another renamed pure adapter is insufficient.
- [5982481622](https://github.com/aase7en/A-Wiki-Conductor/issues/580#issuecomment-5982481622): historical Parent was owned by an external `app-server --stdio` writer. This is historical evidence of a transport owner, not proof that its PID/thread is current.
- [6354559024](https://github.com/aase7en/A-Wiki-Conductor/issues/580#issuecomment-6354559024): hook/test overlap released after operator-approved PR550 closure; fresh gate still required.
- GitHub PR550 is CLOSED, closedAt `2026-10-23T00:39:44Z`; its branch is preserved. Closure grants no implementation acceptance and does not clear #551 auto-refill dependencies.

### Where Work Creation Happens

`git grep` across accepted `src`, `.codex`, `scripts` and tests found no production
caller of `evaluate_bootstrap_guard`, `queue_submission_task_key`, or
`CodexGoalApiAdapter`. References outside their definitions are tests. A separate
search for `thread/queue/add`, `thread/queue/list` and `clientUserMessageId` outside
tests found only the translator, guard commentary and DEFECT_LESSONS.md.

Thus neither inspected module is the existing bootstrap orchestrator. The hook
emits JSON and reads a receipt; it does not create a claim/worktree or enqueue work.
The adapter's `execute` invokes an injected request callable once; the caller owns
transport/admission. Queue submission is an effect initiated by that caller, while
the queued instruction's eventual execution can create governance artifacts. Those
are two distinct boundaries. Historical operational comments show supported queue
operations were used outside these repository modules; the precise current launcher
file/owner cannot be established from this source tree. Do not claim it was found.

Conceptual current path, not an executable repository call chain:

```text
external Parent/operator transport owner -> App Server queue/add
  -> queued instruction executes -> existing governance claim/worktree workflow

Codex lifecycle event -> hook JSON context/deny/Stop output
accepted Goal API adapter <- injected request callable (no production wiring found)
accepted #583 guard <- supplied tuples/completeness (no production wiring found)
```

### Hook Events And Functions

Source: `.codex/hooks/a_sunday_lifecycle.py`; registered events in `.codex/hooks.json`.

| Event | Actual behavior | Task-start enforcement relevance |
|---|---|---|
| SessionStart (`startup`, `resume`, `clear`, `compact`) | `_BASE_CONTEXT` via `_context_output` | Session start is not canonical task start; lacks task/thread queue evidence. |
| UserPromptSubmit | Same base context; does not rewrite prompt | Prompt can continue old work; not proof of new task or enqueue intent. |
| PreCompact / PostCompact | `{"continue":true}` | No scheduling or new work. |
| PreToolUse | `_pre_tool`: deny Bash commands matching direct `kilo run`; Sunday tools get dispatch context | Only existing pre-effect interception candidate; current matching is not queue/claim/worktree interception. |
| PostToolUse | Sunday execution tools get harvest/refill context, other tools `{}` | Too late to prevent the preceding effect. |
| Interrupt | Reminder not to infer durable children were cancelled | No cancellation or replay authorization. |
| Stop | `_stop` may block stopping once from an actionable CONTINUE receipt with stop_gate NONE | Same-parent continuation only, not task creation or queue submission. |
| Unknown event | `{}` | Must not invent a TaskStart event. |

`_read_event` bounds stdin to 262144 bytes and returns `{}` on oversized/invalid JSON.
`_emit` serializes output. `_is_sunday_execution_tool` is substring recognition of
dispatch/recover/status/output/harvest/collect; it proves neither tool identity nor
authority. `_receipt_pointer` requires one absolute pointer marker.
`_valid_ref` checks bounded non-URL references. `_load_receipt` resolves a file under
the temp root, bounds it to 65536 bytes, checks an exact v1 field set and canonical
run-directory/file identity plus typed receipt semantics. `_stop` also checks
stop_hook_active, actionable reason and terminal/stop gates. None obtains queue
evidence; a valid NightShift receipt is not an authenticated admission capability.
Existing `test_hook_script_is_read_only_and_has_no_network_or_process_authority`
explicitly protects this stateless/no-transport boundary.

### Guard And Adapter Contracts

`src/a_conductor/codex_queue_submission_guard.py` exports:

- `queue_submission_task_key(task_ref)`: `awc-tsk-v1:` plus the first 16 SHA256 hex characters of an exact validated task reference, stable across attempts/sessions. It does not canonicalize issue/WO aliases.
- `evaluate_bootstrap_guard(task_ref, *, queue_entries, turns, queue_evidence_complete, turn_evidence_complete, queue_next_cursor=None, turn_next_cursor=None)`.
- Exact tuple/type validation, at most 512 entries and 512 turns, unique IDs, bounded identifiers; invalid evidence raises `QueueSubmissionGuardError`.
- Priority: observed same-key duplicate -> DUPLICATE_TASK_SUBMISSION_PENDING; incomplete evidence/cursor -> RECONCILIATION_REQUIRED; interrupted turn -> RECONCILIATION_REQUIRED; otherwise PROCEED.

The guard does not validate thread, observation provenance, freshness, owner state
or task aliases. Turn evidence has no task reference; interrupted turns therefore
block conservatively even when another task might have caused them. PROCEED is not
authority. The guard does not reject `inProgress` by itself: the consumer must apply
the existing active-writer/in-flight reconciliation gate, not infer replay safety.

`src/a_conductor/codex_goal_api_adapter.py` is a pure injected translator admitting
version strings 0.159.0/0.160.0 (not proof of an installed binary). Operations are
GOAL_GET, blocked-to-active GOAL_ACTIVATE, QUEUE_ADD/LIST/DELETE, TURNS_LIST and RESUME
with excludeTurns true. It has no queue/start, pause, schedule or discovery method.
Each execute builds one request, freezes intent for decoding, catches transport
exceptions as UNKNOWN, and returns OBSERVED or UNKNOWN bounded projections.
LIST returns one page, limit at most 32, plus next_cursor; not a complete scan.
QueueEntry carries submission_id/client_user_message_id; TurnEvidence carries
turn_id/status. GoalApiOutcome retains operation/thread_id/state, so the consumer
must validate those before discarding provenance into guard tuples. List replies
do not independently attest a server-side thread identity; transport binding matters.

## Consumer Options

| Approach | Advantages | Costs / failure modes | Disposition |
|---|---|---|---|
| A. Hook context only: add a #583 reminder at prompt/pre-tool/interrupt boundaries | Small, no new I/O or state; safe progressive disclosure | Model can ignore it; cannot observe queues or prevent external enqueue; not consumer wiring | Useful companion, never sufficient acceptance. |
| B. Put paginated App Server transport and enqueue orchestration in the hook | Superficially close to PreToolUse | No current trusted task/transport payload; per-event subprocess is not the canonical writer; adds I/O/trust/discovery/timeouts and races; violates existing hook contract | Reject. |
| C. Wrap the actual admitted caller; reuse adapter for observation and #583 before enqueue/replay; hook remains advisory | Guard sits immediately before real effect; transport stays with current owner; bounded testable composition | Must identify/claim real external caller and serialization boundary; another library alone remains dead code | Recommended, admission gated. |
| D. Make generic adapter.execute(QUEUE_ADD) implicitly run guard/listing | Catches callers using that method | Changes one-action semantics; lacks canonical task, claims/result evidence and writer admission; generic callers may be non-bootstrap; raw transport still bypasses it | Reject implicit behavior; preserve adapter contract. |

All code changes are reversible before activation; queue writes/claim creation are
not reversible by reverting code. Never compensate by deleting submissions or
claims automatically. No new store, lock service, scheduler or persistent retry loop.

## Recommended Bounded Integration

### Evidence Transport And Ordering

Use the existing caller-owned, supported App Server request channel injected into
CodexGoalApiAdapter. Pass decoded GoalApiOutcome objects in memory to the consumer;
do not accept booleans/queue arrays asserted in prompt text, environment variables,
last_assistant_message, NightShift receipts or arbitrary temp JSON as observed truth.
No evidence-file transport is needed. If a future process boundary requires one,
its authenticated producer/consumer binding needs a separate explicit design gate.

1. Recover the current canonical Parent role/thread and canonical repo/task/claim intent from existing authority, never a historical hardcoded thread or model-invented alias. Freeze that binding and the pending action kind.
2. Prove the existing single-writer/serialization and current task admission before any enqueue, claim or worktree effect. A claim for implementation is not admission to operate a live Goal queue.
3. Through the admitted injected channel, execute QUEUE_LIST and TURNS_LIST for that exact thread. Follow each cursor from the previous OBSERVED page until explicit next_cursor None. Require exact operation/thread on every outcome; UNKNOWN is not empty.
4. Bound each scan to 512 items and, as proposed local policy, at most 32 pages per listing, including empty pages. Reject repeated/broken cursor chains and cross-page duplicate IDs. Overflow, inconsistent page or exhausted budget means reconciliation, not truncation/absence proof. Different local limits require explicit WO adjudication, not an asserted server capability.
5. Feed complete ordered tuples and final cursors to evaluate_bootstrap_guard. No duplicate may disappear through set conversion/truncation. Any non-PROCEED/typed error prevents writes. A positively observed same-key duplicate is a stop even if a later scan is incomplete; no automatic deletion.
6. Revalidate existing owner/result/claim/task/thread binding at the last pre-effect boundary. Late terminal result, owner change, active/unknown execution, binding drift or lost writer admission prevents enqueue. An interrupted turn is not cleared just because the queue is empty.
7. Under the same existing serialization scope, submit at most one QUEUE_ADD with client_user_message_id exactly queue_submission_task_key(canonical_task_ref). Do not generate a per-attempt UUID. A local gate PASS does not replace queue correlation.
8. UNKNOWN after a write means reconcile observed queue/turn/result truth before any replay. No automatic retry, queue/start, resume, activation, claim/worktree or provider effect follows. Successful enqueue is not task acceptance or execution completion.
9. When the queued instruction is eventually consumed, rerun normal task/claim/worktree collision and result recovery gates before governance creation. Queue submission checks alone cannot serialize future consumers.

Queue and turn scans are separate observations, not an atomic snapshot. Re-reading
does not eliminate a race with a second writer. If existing ownership cannot exclude
all relevant enqueue writers across scan/recheck/write, return a typed reconciliation
blocker; do not claim exactly-once from #583's pure guard or correlation string.
Current guard rejects any interrupted turn; do not filter historical turns ad hoc
to improve liveness without an accepted reconciliation contract.

### Minimal Hook Change

In `_pre_tool`, add a compact reminder to existing `_DISPATCH_CONTEXT` that bootstrap
enqueue/replay must use the guarded admitted caller, complete OBSERVED queue/turn
pagination and the deterministic task key before governance effects. Add a concise
same rule to Interrupt recovery context. Keep event registration unchanged.
SessionStart/UserPromptSubmit may point to the durable packet without loading the
test matrix; preserve configured context budgets (1800 base, 1000 dispatch/post).
Do not interpret every prompt or Sunday dispatch as a bootstrap intent.

This is the smallest honest hook guard point, an advisory pre-effect handoff. It
cannot itself enforce #583. A permissionDecision deny path is only appropriate if a
separately verified actual bootstrap tool/structured input contract is registered;
there is no such contract in the inspected source. Do not invent `tool_input` fields,
match shell snippets as proof of queue evidence, or claim global queue coverage.
Stop receipt behavior and all existing malformed-input behavior stay unchanged.

### Exact Prospective File Scope

These are proposed paths for a later separately claimed R3 implementation, not files
authorized for mutation in this design lane:

| Path | Proposed change |
|---|---|
| `.codex/hooks/a_sunday_lifecycle.py` | Compact pre-tool/interrupt handoff only; no transport, queue state or scheduler. |
| `tests/test_codex_a_sunday_hooks.py` | Reminder, context-budget and unchanged event/deny/receipt/no-I/O regression tests. |
| `src/a_conductor/codex_bootstrap_submission.py` (new, proposed name) | One bounded callable consumer of the injected adapter plus existing admission/revalidation boundary; collects evidence, invokes #583 and performs at most one admitted queue add. No persistence/new authority. Prefer placing this function in the actual caller if recovery identifies an appropriate existing module. |
| `tests/test_codex_bootstrap_submission.py` (new, proposed name) | Ordered fake-transport and side-effect-spy tests through the actual consumer entry point. |
| Actual existing external enqueue launcher/registration and its test | REQUIRED but exact path UNKNOWN. Recover and name/claim it before implementation admission. It must call the consumer rather than raw queue/add; otherwise the new module is not a delivered consumer. |

Leave codex_queue_submission_guard.py and codex_goal_api_adapter.py unchanged by
default; their accepted APIs suffice for the proposed projection/guard composition.
Do not broaden into runtime_activation.py, elastic_worker_capacity.py, #576 idle
source, quota hooks, shared continuity or A-Wiki changes merely to manufacture a caller.
The final exact mutation allowlist is incomplete until the external owner is named.
No standalone helper-only source WO should be admitted as delivery of this packet.

## PR550 Lessons

The preserved hook adds two lines to `_POST_EXEC_CONTEXT`: route a scheduler-owned
READY plan through an executable auto-refill bridge delegating to existing
ParallelReadyExecutor authority. It adds no hook event, import or invocation.
It does not call the Goal adapter or #583 guard.

The executable work is elsewhere on that branch:
`elastic_worker_capacity.py::_execute_a_faster_plan` assembles selected tasks and
calls `a_faster_auto_refill.py::execute_auto_refill`, with executor=self._executor.
The bridge rederives utilization/WIP, binds READY/schedule/task identities, requires
provider and pre-dispatch authority, bounds selected work and validates returned
outcome identity. Mutable refill explicitly fails closed with
CANONICAL_MUTABLE_CLAIM_AUTHORITY_UNAVAILABLE pending canonical claims; exceptions
after execute become REFILL_EXECUTION_RECONCILE_REQUIRED, not retry permission.

Reuse the separation: hook advertises policy; an actual runtime caller owns effects;
existing executor/claims retain authority. Reuse input/output drift checks and
ambiguous-effect reconciliation. Do not transplant PR550's graph/worker scheduling
into a queue guard, confuse auto-refill with governance enqueue, or infer mutable
auto-refill is unblocked because the hook/test file reservation was released.

## RED-First Test Matrix

All tests below are proposed, NOT run or implemented by this design lane. RED must
exercise the named real caller/registration as well as consumer functions. Existing
pure #583 tests alone are insufficient. Use fake admitted transport, fixture-owned
task/thread binding and spies for queue add/claim/worktree/dispatch/activation.

| Case | Required observable result |
|---|---|
| Complete empty queue/turn evidence, admitted stable owner | Exactly one QUEUE_ADD after both scans and last-boundary recheck; exact deterministic correlation key; zero automatic followups. |
| Same-key duplicate only on later queue page | No queue add, claim or worktree; duplicate ID retained; verify requested cursor sequence. |
| Foreign task only / issue-vs-WO alias ambiguity | Different canonical task does not dedupe; unresolved aliases block before effect rather than hash two owners for one intent. |
| Missing evidence / UNKNOWN response / missing nextCursor / truncated page | No effect; never substitute empty complete evidence. |
| Queue or turn listing still has next cursor | Continue only within bounded read budget; no premature guard PROCEED. |
| Repeated cursor / cross-page duplicate IDs / operation or thread mismatch | Typed reconciliation; zero writes. |
| 512 evidence items / 513 / endless empty pages | Boundary accepted only if complete; overflow/page budget blocks, never truncates. |
| Interrupted turn with empty queue | Reconciliation; no enqueue/claim/worktree; no inferred cancellation. |
| inProgress / unknown existing child execution | Existing owner/replay gate blocks even if pure guard returns PROCEED. |
| Owner/result/task/thread drift just before add | Last-boundary revalidation rejects; spy proves add/claim/worktree count zero. |
| Two writers observe empty queue concurrently | Existing serialization admits at most one effect; missing/unprovable serialization fails closed. No claim of guard-provided CAS. |
| QUEUE_ADD times out after server records submission | UNKNOWN; no second write/resume/start/delete; subsequent recovery finds same-key pending submission. |
| Wrong/missing add correlation in reply | UNKNOWN, preserve observations; never mark success or replay-safe. |
| Forged prompt/temp receipt claims evidence_complete=true | Cannot become observed queue evidence or admission. |
| Generic queue add bypass through registered bootstrap path | Test fails until actual owner routes through consumer; helper-only green suite is not acceptance. |
| Queued work consumed after ownership changed | Existing governance collision gate prevents claim/worktree effect. |
| Hook prompt/compact/post/Stop/Interrupt regression | Same event semantics and receipt recursion guard; no queue/client/process/network/state added. |
| Direct kilo run denial / readiness probe | Existing denial remains; benign probe remains allowed. |
| Hook context budgets / unrelated tools | Compact guidance fits limits; no blanket bootstrap denial or invented tool schema. |

Later verification command, after implementation is separately admitted:
`python -m pytest -q tests/test_codex_bootstrap_submission.py tests/test_codex_a_sunday_hooks.py tests/test_codex_goal_api_adapter.py tests/test_codex_queue_submission_guard.py`.
Add the recovered real caller's integration suite to the exact WO; freeze exact SHA,
independent R3 review and exact-head CI before any acceptance. Trusted hook activation
needs a separate supported operational step and its own evidence.

## Risks, Open Questions And Handoff

- BLOCKER: What is the current supported external Parent enqueue/replay launcher, exact file/registration owner, and transport admission? Historical operational comments are not a live binding.
- BLOCKER: Which existing authority serializes all relevant queue writers through observation and add? A single Codex thread writer does not by itself prove queue producers are serialized.
- BLOCKER: Freeze canonical task reference and issue/WO alias mapping in existing task authority. The accepted guard hashes exact text; do not redefine canonical identity in this module.
- BLOCKER: Establish an accepted interrupted-turn reconciliation boundary. Scanning all history can permanently block; filtering history without evidence can hide a duplicate owner.
- RISK: Pagination is not an atomic snapshot; terminal result/owner drift can occur between pages. Require existing admission plus final revalidation, not optimistic absence claims.
- RISK: QueueEntry lacks task text/thread provenance, and legacy random correlation IDs may conceal same-intent submissions. Unknown legacy queue intent requires reconciliation; do not parse free text as authoritative task identity.
- RISK: The 64-bit truncated task hash is the accepted #583 contract, not a mathematical uniqueness guarantee. Do not change its format here; conflicts conservatively block, and canonical identity remains separately bound.
- RISK: Context injection is bypassable/advisory; a fake evidence field or valid temp receipt is not a capability. Existing repo-local loader executes worktree-local code; preserve trust/hash gates and do not claim current global activation was verified.
- OPEN: #580's broader project-identity/A-Sidecar/A-Audit/watchdog requirements remain separate from this bounded consumer packet. No new watchdog, Parent migration, native Goal pause/resume API or scheduler is designed here.
- OPEN: #551 still gates mutable auto-refill claim binding, but must not be labeled a blanket prerequisite for every read-only queue-guard consumer without a concrete dependency.

Source mutation verdict: NO. Next safe action: integrator recovers and names the
actual enqueue/replay owner and existing serialization/identity evidence, adjudicates
the options, then freezes one exact R3 implementation WO/claim including real caller
registration and RED integration tests. If those facts remain unknown, preserve the
blocker and do not implement a misleading hook-only or uncalled-helper completion.

Design-lane checkpoint: full issue/guard/hook/adapter/PR550 source trace complete;
source, tests, runtime and global config untouched. Delivery is this sole-file
proposal on the requested branch, not #580 completion or R3 acceptance. Shared
continuity fold-back belongs to the integrator after reviewing this packet.

Design verification: sole-file staged diff reviewed; `git diff --cached --check`
passed; packet re-read as UTF-8 with ASCII-only authored content. Existing
`python -B -m pytest -q -p no:cacheprovider tests/test_work_order_identity.py`
passed 33 tests. No consumer behavior, live transport, activation or proposed RED
matrix was executed; those remain later implementation gates.
