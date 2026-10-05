# WO-P1-188 — GLM Wave 9 frontier campaign

Status: READY / DOCS-ONLY ORCHESTRATION
Risk: R0 parent transport; child work retains its own risk
Owner: GLM-5.3 MAX sustained campaign after dispatch
Integrator: GPT-5.6 Sol
Durable coordination: GitHub Issue #233
Base at publication: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`

## Purpose

Provide the next long-horizon execution tree after Wave 8 completed, without re-running consumed work.

Wave 9 is delta-focused around current unresolved evidence:
- WO165 / ZRA-2 Phase-A independent exact-SHA review;
- IR1 duplicate physical execution / recovery-path evidence;
- Windows owned-process CI observation race;
- ZRA-2 Phase B/C/D after dependency gates;
- ZRA-3 then ZRA-4;
- independent review, defect-memory, security, CI, continuity, and hygiene work while critical gates are blocked.

## No-repeat boundary

Wave 1–8 completed/consumed units must not be regenerated merely to create work. Wave 8 result on Issue #233 is predecessor evidence.

## Parent mutable scope

Exactly:
- `docs/work-orders/WO-P1-188-glm-wave9-frontier-6000.md`
- `docs/prompts/GLM-MARATHON-WAVE9-FRONTIER-6000.md`

No parent-wave authority over product source, tests, shared SSoT, provider/lease/job stores, live DB, secrets, A-Wiki, processes, or merge.

## Execution pointer

Tracked program:
`docs/prompts/GLM-MARATHON-WAVE9-FRONTIER-6000.md`

Run as one sustained `/goal` with nested child goals and automatic continuation.

## Critical predecessor truth

- publication main: `f964afced5fbe0905c3667b1a6552a6fdafc09cb`
- ZRA-1 real-provider proof: accepted; do not rerun
- WO165 Phase A: frozen candidate `5f95fe16e95c90faaa4a36686e286515e4641708`
- Phase-A exact-head CI: green across Windows/full, Ubuntu, macOS
- Phase-A independent review: required; no valid verdict yet
- IR1: RECOVERY_REQUIRED evidence only, no review verdict
- Wave 8: complete; author mutation claim released
- PR #259 Windows failure: owned-process idempotent-start observation issue on a docs-only PR; targeted failed-job rerun requested after classification

## Mutation rule

Every mutable child must recover actual state and establish a compatible child claim with exact repo/worktree/branch/HEAD/scope/owner/overlap. Unknown or conflicting ownership fails closed. GLM does not self-merge. GPT retains final architecture, trust, exact-SHA acceptance, merge, and release authority.

## Acceptance for this WO

This WO succeeds when:
- the packet is durably published;
- GLM can resume from it without chat history;
- every executed child has evidence-based disposition;
- consumed Wave-8 work is not repeated;
- critical-path preemptions are honored;
- no blanket mutation or live-provider authority is inferred from the parent packet;
- final report exposes one exact NEXT_SAFE_ACTION and releases any child claims it owned.

The packet itself is transport/orchestration and need not merge before use.
