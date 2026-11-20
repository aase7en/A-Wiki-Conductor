# WO-P1-174 — Delivery workflow with bounded premium-model use

Status: IMPLEMENTED / FROZEN_FOR_INDEPENDENT_REVIEW / DOCS-ONLY / R2 GOVERNANCE
Date: 2026-09-10
Owner: GPT-6 Astra / Poppy Javis, bounded workflow analysis and integration
Execution: separate workhorse-class subagent for bounded documentation; independent review before delivery
Repository: aase7en/A-Wiki-Conductor
Branch: codex/wo-p1-174-delivery-workflow
Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo174
Base: 577d9483720c857a89a5d2c9ea9359f9c0aa50b5
Claim: WO174-DOCS-WORKFLOW-001; this exact docs scope only

## User outcome and authority

The user requests an evidence-based workflow improvement that accelerates accepted
project delivery, identifies the highest-leverage phase, and minimizes dependency
on GPT-6 Astra. Implement an operating recipe using existing policies, not another
scheduler/model router/claim system. This is documentation governance, not runtime
activation or permission to mutate other work orders. No merge from this lane.

## Mutable scope

- This work order (primary owner only).
- docs/runbooks/cost-first-delivery.md (new operating recipe).
- docs/agent-collab/FAST_EXECUTION_PROTOCOL.md (short discoverability pointer only).
- docs/agent-collab/CAPABILITY_MATRIX.md (short application note/pointer only).
- Ignored runs/WO-P1-174/ evidence.

Forbidden: src/**, tests/**, CI configuration, PROJECT-PLAN.md, PROJECT-GRAPH.yaml,
AGENTS.md, COLLAB.md, CURRENT-WORK.md, handoff.md, all other WOs and active PRs,
A-Wiki mutation, private data, live provider/runtime/process operations.

## Reuse / ownership proof

REUSE + WRAP: accepted WO154 risk-tier protocol, capability matrix, WO155/ZRA
roadmap, A-Wiki model-switching/cost-gate/cross-agent-work-orders protocols.
EXTEND only the concrete operating recipe and entry pointers. No new authority,
state store, evaluator, scoreboard service, scheduler or model/pricing registry.

Live A-Wiki main verified at 566637ac8d2636d6c63eda2bd6ebe81b55bd3d72;
its local main is ahead and remains untouched. PR59 evidence roadmap is pending.
Conductor main verified at base above. Inspected open PR scopes: WO169/170/171
own separate runbooks, incident, roadmap/PROJECT-PLAN/COLLAB files; WO172 owns its
prompt + WO; WO159/PR222 and PR223 use different files. WO173/R5 holds harness
source/tests on Windows (Issue233 comment 5619928273). No overlap with this scope.
A later READY packet (5619944690) does not revoke that explicit R5 claim.

## Evidence anchors (dated observations, re-pin before execution)

- Issue233 comment 5619553261: GLM marathon completed, R4 Windows P2 and missing
  production dispatch/apply composition seams; recommendation is R5 first.
- PR242 comments 5619318241 and 5619862174: independent Windows reproducer.
- Issue233 comment 5619490874: AEET reuse/gap findings; review evidence, not acceptance.
- Issues 226/233 and 214 remain open; no downstream source gate is lifted here.
- Main source: assemble_zcode_execution is not wired into DesktopControlService;
  existing real-helper E2E and AgentChangeApplier are reusable seams.
- Existing FAST protocol already contains repair budgets, WIP=3+1, exact-SHA
  review, progressive verification and checkpoint economy. Apply, do not replace.
- WO171/PR244 and WO172/PR245 are pending docs; link remotely when absent on main.

## Implementation packet for bounded documentation executor

Read the current FAST/CAPABILITY docs, this WO, WO155 roadmap and cited GitHub
checkpoints as necessary. Write an English runbook, about 150-200 lines maximum,
that another agent/operator can actually execute. Include:

1. Evidence vs inference: wasted recovery/relay, repeated boundary repairs,
   model role confusion and unfinished composition; no invented timing/cost gains.
2. Ranked dependency path: R5 closure/current ownership; reconcile actual
   P0-B/authority gates and the smallest ZRA-1 production composition proof;
   ZRA-2 automatic one-repair loop (first major throughput milestone);
   ZRA-3 accepted NEXT READY continuation; ZRA-4 bounded parallelism. Do not
   force unproven Mac supervision onto an already-valid Windows path; choose a
   currently authorized proven host, preserving cross-platform acceptance.
3. Tiny AEET-0/defect fixture work only if bounded/disjoint and directly removes
   repeated reviews; do not put the whole AEET roadmap before Zero-Relay.
4. Stepwise workflow using existing WO fields/receipts: one current owner and
   pointer, full startup once per scope then targeted re-pin at boundaries,
   complete first-pass boundary matrix incl platform exceptions, RED/repair,
   progressive verification, one frozen evidence batch, review budget/adjudication,
   checkpoint and handoff. No manual result copyback.
5. Routing table: deterministic tools first; currently eligible workhorse for
   lookup/implementation/test mechanics; qualified independent reviewer separate
   from author; integrator for acceptance/ownership. GPT-6 Astra is an escalation
   candidate, not a hardcoded gate or automatic choice for every R3 task. R3
   framing and strongest qualified independent review remain mandatory. Escalate
   on unresolved architecture/trust/large-blast-radius questions or repeated
   same-cause failures; de-escalate after a written decision. No pricing claims
   or fixed unverified model rankings. Quota exhaustion does not transfer a claim.
6. Compact routing entry in the SAME WO/checkpoint (role, reason, capability/
   readiness/cost evidence, effort, escalation trigger, fallback). Not a new form
   required for each tool call. Unknown price/usage stays UNKNOWN, not zero.
7. WIP within existing 3+1 max; recommend 1 critical-path implementation + one
   disjoint fixture/composition slice + one independent reviewer initially;
   no busy audit reruns once the packet is COMPLETE, only new evidence/hypothesis.
8. Measure 10 accepted WOs before/after with existing evidence: READY-to-accept
   lead time, queue/blocked/review delay, actual Astra participation, repair rounds,
   CI runs, manual relay count, escaped defects; unknown/missing explicit. No
   new scoreboard implementation; reuse AEET7 later. No promised 2-3x gain.
9. Clear exit evidence per prioritized phase, remaining gates, one next safe
   implementation action = continue owner-held WO173/R5 (do not claim it here).

Add only concise links to this runbook in FAST and CAPABILITY. Do not rewrite
existing risk/authority/merge/release rules. No additional planning hierarchy.

## Acceptance and verification

- Runbook + two pointers implement the recipe above without policy weakening.
- Relative local links exist at branch HEAD; pending-PR links are explicit URLs.
- Exact scope, strict UTF-8, diff whitespace and no secret-like additions pass.
- Independent R2 exact-SHA review, then clean pushed branch and draft PR.
- No runtime/source/CI/other-lane mutation and no measured speedup claimed.
- Checkpoint/result under this WO/runs; shared continuity fold remains with owner.

## Checkpoint

2026-09-10: startup/remote/claims/reuse audit completed. Clean isolated docs worktree
created from exact main. Primary frames bounded changes here; workhorse executor
will write only the runbook and two pointers, with this WO read-only.

2026-09-10 implementation checkpoint: Sol medium wrote the runbook and two pointers;
primary corrected risk-scaled matrix/acceptance wording and refreshed live R5 state.
Issue233 comment 5620087669 supersedes the earlier active-mutation observation: WO173
source claim is released, PR246 candidate ff996e1ff39d92ee8fc3b021b24661c78540c50b awaits
independent review and exact-head CI. Next safe action there is integrator closure,
then re-pin composition prerequisites; this lane owns no R5/source action.

ROUTE: bounded docs execution=GPT-5.6 Sol/medium, available session tool + exact packet;
architecture/framing=GPT-6 Astra; independent review=separate Sol/medium session at frozen
SHA. Pricing/usage=UNKNOWN. Escalate unresolved policy/trust conflicts to integrator.
No automatic ownership transfer on quota or reviewer substitution.

Verification: strict UTF-8/local-link/scope/pointer-preservation/whitespace/credential-pattern
checks are recorded under ignored runs/WO-P1-174/. Runtime tests are not applicable to
this docs-only change. Frozen SHA, packet hash, review verdict, hosted CI, PR, and exact
next safe action will be bound in runs/WO-P1-174/result.json and the durable draft PR.
No shared continuity mutation is authorized; the integrator owns its acceptance fold.
No runtime acceleration or token/cost reduction has yet been measured.
