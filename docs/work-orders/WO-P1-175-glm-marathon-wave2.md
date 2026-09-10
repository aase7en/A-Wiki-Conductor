# WO-P1-175 — GLM Marathon Wave 2

Date: 2026-09-10 (Asia/Bangkok)
Status: ACTIVE / DOCS-ONLY PACKET BOOTSTRAP
Owner: GPT-5.6 Sol integrator documentation lane
Risk: R2 governance / agent-execution documentation
Priority: P0-supporting; Zero-Relay and active exact-SHA gates remain ahead of deferred roadmap work
Repository: `aase7en/A-Wiki-Conductor`
Branch: `docs/wo-p1-175-glm-marathon-wave2`
Base at bootstrap: `origin/main@577d9483720c857a89a5d2c9ea9359f9c0aa50b5`
Durable coordination authority: Issue #233
Execution prompt: `docs/prompts/GLM-MARATHON-5H-WAVE2.md`

## Goal

Create one successor long-run GLM-5.3 MAX packet after `GLM-MARATHON-5H-001` completed.
Wave 2 must start from current durable evidence rather than rerunning Wave 1.

The packet is designed for sustained work through the available provider/session window while
maximizing useful evidence, not token consumption. It must continue autonomously across
read-only stages when a mutation lane is unavailable.

## Reuse-before-build

REUSE + EXTEND only:
- `00-AGENT-ENTRY.md` universal entry;
- `PROJECT-GRAPH.yaml` routing;
- `AGENTS.md` repository contract;
- `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md` risk-tier delivery;
- `docs/agent-collab/CAPABILITY_MATRIX.md` model routing;
- WO-P1-155 + Issues #213–#216 for Zero-Relay;
- Issue #233 for cross-repo authority/evidence checkpoints;
- WO-P1-172 / `GLM-MARATHON-5H-001` as historical Wave-1 execution evidence;
- WO-P1-171 / PR #244 as the evidence/AEET roadmap source;
- A-Wiki PR #59 as the companion Phase 12–17 roadmap source.

No new scheduler, task store, claim/lease system, review lifecycle, memory authority,
provider registry, model policy, retry authority, or trace authority is introduced.

## Brain / governance gate

- Gain: sustained GLM archaeology, review, debugging, fixture design, and bounded packet shaping.
- Shape: one on-demand prompt + one work order; no always-loaded instruction growth.
- Weight: additive docs only; existing execution protocols remain authoritative.
- Safety: no private data/secrets; no live DB/provider/process mutation from this WO.
- Verify: exact two-file scope, UTF-8, diff/whitespace, link/pointer review, credential-pattern scan.

## Live state observed at bootstrap

These are observations, not future authority. GLM must re-pin them before use.

- A-Conductor `main`: `577d9483720c857a89a5d2c9ea9359f9c0aa50b5`.
- PR #246 / WO173 R5: Draft/Open/Mergeable, head
  `ff996e1ff39d92ee8fc3b021b24661c78540c50b`; exact-head CI run `34487038722` SUCCESS.
- PR #246 has not yet produced an independent exact-SHA review at bootstrap.
- PR #247 / WO174: docs-only delivery workflow, head
  `146723c2d55ba6ee951c49634c81cc5bb000222a`; independent docs review already reported PASS;
  hosted CI was still in progress when this WO was created.
- Wave-1 result on Issue #233 found PR #242 R4 `CHANGES_REQUIRED`, P0=0/P1=0/P2=1;
  native Windows reproduction confirmed the P2 and led to WO173/R5.

## Mutable scope for this WO

Only:
- `docs/work-orders/WO-P1-175-glm-marathon-wave2.md`
- `docs/prompts/GLM-MARATHON-5H-WAVE2.md`

Everything else is read-only for this docs lane.

Explicitly forbidden:
- `src/**`;
- `tests/**`;
- `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, `PROJECT-PLAN.md`;
- PR #246 / WO173 source or tests;
- PR #247 / WO174 files;
- private Drive data, secrets, credentials;
- live runtime/provider DB;
- Worker/process mutation;
- merge/release/acceptance actions.

The prompt itself grants no source mutation. A separate live WO/claim must authorize every
source/test mutation lane.

## Wave-2 ordered work queue

1. Independent exact-SHA R3 review of the live PR #246 R5 candidate.
2. Re-pin Zero-Relay current frontier and shape one composition E2E proof using existing
   provider admission, WorkerLease, ZCode execution, result packet, change applier, and
   duplicate-execution guard authorities.
3. Audit ZRA-2 automatic review/repair composition and failure model; produce a smallest
   executable packet, not a parallel review system.
4. Audit ZRA-3 automatic NEXT READY continuation and stop/recovery semantics.
5. Audit ZRA-4 bounded parallel dispatch/fan-in and isolation semantics.
6. Mine accepted/rejected WO168 R1–R5 evidence into an AEET-0/P14 evaluator fixture inventory
   and self-test contract; never blend security failures into an aggregate score.
7. Shape P15/AEET-6 adversarial agent-security fixtures and P16 memory-provenance/quarantine
   fixtures using existing owners.
8. Reconcile A-Wiki Phase 12–17 + A-Conductor AEET-0..8 only where live state changed since
   Wave 1; do not repeat the settled REUSE/WRAP/EXTEND matrix without new evidence.
9. Audit SSOT/continuity drift between CURRENT-WORK/COLLAB, active WOs, PRs, Issues and exact
   Git state; report drift but do not edit hotspot files without a separate claim.
10. Produce an accepted-run efficiency/minimality evidence table and at most five next micro-WOs.

A newly recovered higher-priority P0/READY packet may preempt this order at the next safe
checkpoint. Record the reason for the preemption.

## Long-run execution rules

- Recover fresh state before every material stage.
- No human `continue` prompts between safe stages.
- No repeated large-file rereads when exact SHA is unchanged.
- No repeated identical test run unless testing a distinct host/failure hypothesis.
- Provider/auth failure blocks only provider-dependent proof; offline/read-only work continues.
- When context/window limits approach, publish a durable partial checkpoint first.
- Every finding must name repository, exact SHA/ref, file/symbol or contract, evidence type,
  confidence, and smallest next action.
- Agent assertions are not runtime proof; deterministic evidence outranks confidence.
- Never expose hidden reasoning; persist concise evidence and verdicts only.
- Never self-merge or self-accept a candidate authored in the same lane.

## Stage destinations

Primary: A-Conductor Issue #233.
PR-specific blocking review: the exact PR conversation being reviewed.
ZRA-specific detailed findings: Issues #213–#216 as appropriate, with a compact pointer back
on Issue #233.
A-Wiki cross-repo findings: reference A-Wiki PR #59 / its WO, but do not mutate A-Wiki without
its own fresh gate and claim.

Final result heading:
`## GLM-MARATHON-5H-WAVE2 RESULT`

Final result must include:
- exact refs/SHAs inspected;
- PR #246 verdict if still applicable;
- current Zero-Relay smallest executable next step;
- evaluator/security fixture conclusions;
- changed-vs-Wave1 cross-repo gap summary;
- SSOT drift findings;
- accepted-run efficiency observations;
- maximum five evidence-backed future micro-WOs;
- blockers;
- exactly one `NEXT_SAFE_ACTION`.

## Acceptance for this docs packet

- successor prompt exists at `docs/prompts/GLM-MARATHON-5H-WAVE2.md`;
- it does not instruct GLM to repeat the resolved PR #242 review;
- it begins from PR #246/live state after re-pin;
- it supports useful multi-hour continuation even when mutation is unavailable;
- it preserves risk/claim/secret/protected-work/self-review/merge gates;
- it reuses existing Zero-Relay/evaluator/owner-map authorities;
- exact changed scope is only these two docs files;
- branch is Draft-PR only and is not merge-authorized by this WO.

## Checkpoint

Docs-only claim declared on Issue #233 comment `5620243244` before branch creation.
Branch was created from the bootstrap main SHA above. Final candidate SHA, verification and
claim release must be appended after both files are committed and checked.