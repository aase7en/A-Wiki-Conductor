# ORCH-1/2 Receiver And Evidence Collection

Issue: #713

Status: AUTHOR_VERIFIED / freeze for independent R3 acceptance.
Risk: R3 / CONTROL_PLANE_ONLY.
Authority: explicit AUTHOR receiver task under parent #709; design ORCH-1-foundation-design.md
receiver and section 5, codec accepted on main through PR #711.
Owner: ses_e95c86be9ffeMKp2RWTfeHG5m1.
Claim: ORCH-1-2-RECEIVER-001 / issue comment 6372970700.
Base: origin/main 12eddb2; worktree A:\GitHub\_worktrees\AWC-orch1-receiver.
Branch: feat/orch1-receiver.
Device: ff685af5-9031-4b3b-84ff-61dc8f1a840c / Windows.

## Scope And Failure Model

Only orchestration_receiver.py, test_orchestration_receiver.py and this child WO
are mutable. Codec, guard, runtime, stores, hooks, providers, shared CURRENT-WORK,
handoff and COLLAB stay read-only. Integrator folds shared continuity from this
WO and issue checkpoint. No PR, merge or live activation.

Receiver admission means evidence collected, NOT effect permission. There is no
effect port, persistence, listener, retry, scheduler or production registration.
Source strings and producer timestamps are not authentication/freshness authority.
The admitted composition root must authenticate before invoking this boundary.
Missing/unknown/invalid/stale evidence and identity drift block. Pages are bounded
at 32 and queue/turn records at 512; no truncation, cursor cycles or duplicate IDs.
Partial validated evidence survives refusal, with completeness flags false.

Binding is resolved by an injected callable(task_ref, binding_ref) returning an
EvidenceBinding. It supplies current authoritative task/ref/thread/operation and
observed_at; no raw signal metadata is interpreted as a thread or capability.
This bounded offline slice supports Parent enqueue/replay only; other targets
and observation kinds return NOT_APPLICABLE without listing another thread.

QueueReader.list_queue_items(thread_id, cursor) returns a plain page dict with
items, nextCursor and a binding EvidenceBinding. TurnReader.list_turns(thread_id)
returns a complete list of TurnEvidence. Both ports are injected, read-only and
must enforce their own transport admission; no real adapter is wired here.
The turn list freshness/provenance is supplied separately by
TurnReader.evidence_binding(thread_id), read after list_turns, and must describe
that exact complete listing (not a new unrelated timestamp). This preserves the
requested list API while refusing bare unproven empty/stale cached listings.
Queue/turn bindings must match the resolved task/ref/thread/operation and be fresh
at collection completion using an injected aware clock. Max age defaults to 60s;
future/naive/invalid time is never accepted. Producer timestamp is not consulted.

Typed reasons: EVIDENCE_COLLECTED, EVIDENCE_MISSING, EVIDENCE_STALE,
EVIDENCE_OVERFLOW, RECONCILIATION_REQUIRED, NOT_APPLICABLE; invalid signal retains
the codec's exact SIGNAL_* reason. No effect safety/exactly-once claim follows.

## Verification And Routing

RED-first deterministic fake-reader/clock tests: multi-page, empty, missing,
stale, >32 pages, exact boundary, missing/cyclic cursor, wrong task/thread/ref/
operation, malformed records, duplicate IDs, 512/513 bounds, read exceptions,
late expiry and unsupported target. Related codec/guard/adapter/identity tests.
GLM_OFFLOAD=NOT_BENEFICIAL for already delegated bounded AUTHOR task; no provider
subdispatch. Worker1..5 tools PLUGIN_NOT_EXPOSED_TO_CHAT; RDC device discovered
online, native local Git/gh/tests used. No runtime execution outstanding in lane.
Hook enforcement POLICY_ONLY, not GUARD_ENFORCED. Cleanup PENDING exact-SHA
independent review; retain branch/worktree. Acceptance and hosted CI not claimed.

The codec already owns canonical WO-P1-709. Child issue #713 supplies the distinct
canonical identity; no identity-policy exception or naming bypass is added.

## Author Verification Checkpoint

Initial RED: focused receiver suite failed collection with missing module.
Initial combined run: 373 passed, one identity failure (duplicate WO709), repaired
by canonical child issue #713, not checker changes. Adversarial advancing-time
RED: 56 passed/one failed; page freshness initially compared to collection start,
rejecting legitimate observations taken during collection. Fixed by validating
page identity immediately and all freshness against the completion clock.

Final command:
`python -B -m pytest -q -p no:cacheprovider tests/test_orchestration_receiver.py tests/test_orchestration.py tests/test_work_order_identity.py tests/test_codex_goal_api_adapter.py tests/test_codex_queue_submission_guard.py tests/test_a_faster_utilization_guard.py tests/test_hook_bus.py tests/test_hook_stm.py`

Result: 616 passed (57 receiver tests plus 559 directly related tests), 36.87s.
No real network/file/process reader, production effect or runtime registration.
Source/ports are intentionally unregistered; this is not #580 consumer delivery,
queue serialization proof, authentication, replay permission or live acceptance.
TurnReader must attest complete enumeration rather than adapt one paged outcome
as an entire list. Its separate provenance call is a local injected contract,
not a fabricated existing transport capability. Final USE authority remains
dispatcher-owned; evidence snapshots do not eliminate concurrent-producer races.

Next: commit/push exact candidate, independent R3 review and integrator acceptance.
Shared CURRENT-WORK/handoff/COLLAB folding remains integrator-owned. Author claim
will freeze on #709 with exact commit and remote verification; retain worktree.
