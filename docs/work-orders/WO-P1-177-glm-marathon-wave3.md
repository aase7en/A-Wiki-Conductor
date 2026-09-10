# WO-P1-177 — GLM Marathon Wave 3

Status: READY / DOCS-ONLY ORCHESTRATION PACKET
Owner: GPT-5.6 Sol integrator
Executor: GLM-5.3/ZCode after the user's current GLM lane reaches a safe checkpoint
Parent evidence: WO-P1-175 / PR #248 Wave 2 result
Critical-path child: WO-P1-176 ZCode authorized runtime model materialization
Bootstrap base: `main@1e2d193db2e7db7763d52cb337e9a3f130d0808e`
Prompt: `docs/prompts/GLM-MARATHON-5H-WAVE3.md`

## Purpose

Keep GLM productive for a long session without requiring repeated human `continue` messages and without weakening claim, review or dependency gates.

Wave 3 has two execution modes:

1. **Mutable critical-path mode** — implement only WO176 after a fresh source claim/worktree gate.
2. **Read-only continuation mode** — after WO176 freezes, continue archaeology, adversarial design and next-packet shaping while an independent reviewer handles the frozen candidate.

This WO does not grant blanket source mutation. Each mutable work order still needs its own current claim and non-overlap proof.

## Inputs to consume, not rerun

- Wave-2 final result: Issue #233 comment `5620813258`.
- Runtime-binding independent audit: Issue #213 comment `5620725176`.
- WO176 task packet on the same branch as this file.
- Zero-Relay roadmap and Issues #214, #215, #216.
- Current repo entry, graph, AGENTS, claims and actual Git state at execution time.

Do not repeat Wave-2 Stages 1–10 unless current state falsifies a prior conclusion.

## Ordered work

### A. Critical path — WO176

Re-pin actual state, obtain/verify a fresh GLM implementation claim, execute WO176 RED-first, run targeted + related + adversarial verification, freeze one candidate SHA and prepare a secret-safe assurance packet.

Stop mutable WO176 work at `READY_FOR_INDEPENDENT_EXACT_SHA_R3_REVIEW`.

### B. Continue productively while review is pending

Without source mutation or self-review acceptance:

1. shape the smallest `ZRA-COMP-1` composition E2E using existing real-helper patterns and zero new production authority;
2. reconcile current ZRA-2 Issue #214 against post-WO176 assumptions and identify one exact composition seam only;
3. revalidate ZRA-3 next-READY continuation seam from Issue #215 without inventing another scheduler/lifecycle;
4. revalidate ZRA-4 bounded parallel/fan-in seam from Issue #216 using existing write-set conflict, provider capacity, lease and replay authorities;
5. shape AEET-0 evaluator corpus seed from Wave-2 KG/KB/ES fixtures;
6. shape SEC-INJECT-1 and SEC-EXFIL-1 test-only packets with positive twins;
7. identify only changed-state SSoT drift since Wave 2; do not edit global hotspots claimlessly;
8. publish a final ranked queue of at most five executable micro-WOs with exact dependency gates.

## Non-negotiable rules

- No merge, release or self-approval by GLM.
- Same GLM implementation lane cannot count as WO176 independent reviewer.
- No source mutation beyond WO176 unless GPT/integrator opens a separate current work order/claim.
- No mutation of A-Wiki from this A-Conductor packet.
- No live provider/config/credential/DB mutation.
- No unrestricted environment dump or hidden reasoning in evidence.
- No broad ZCode config-tree scan while ZCode is running.
- No duplicate scheduler, claim/lease, provider/model authority, review lifecycle, retry engine or memory layer.
- Reuse/WrAP/extend before new implementation.
- Actual state always overrides bootstrap SHAs and stale comments.

## Required checkpoints

GLM should post durable checkpoints to Issue #233 at meaningful stage boundaries, not every micro-step. WO176-specific implementation evidence belongs primarily on Issue #213 / its Draft PR, with a concise pointer on #233.

Each checkpoint should include:

- repo/branch/exact SHA inspected;
- mutation authority: YES/NO and claimed scope;
- what changed since the previous checkpoint;
- deterministic evidence run;
- findings classified P0/P1/P2 where applicable;
- blocker/dependency status;
- one next safe action.

## Final result contract

At the end of Wave 3, publish one `GLM-MARATHON-5H-WAVE3 RESULT` comment to Issue #233 containing:

1. exact repos/SHAs/PRs inspected;
2. WO176 state and frozen candidate SHA if implementation completed;
3. tests/adversarial evidence summary;
4. unresolved findings with severity;
5. whether independent review is pending, accepted or changes-required (never self-awarded);
6. ZRA-COMP-1 packet shape;
7. ZRA-2/3/4 changed-state reconciliation;
8. AEET-0 + SEC-INJECT-1 + SEC-EXFIL-1 packet conclusions;
9. SSoT drift findings limited to changed state;
10. at most five ranked next micro-WOs;
11. blockers requiring human/GPT authority;
12. exactly one `NEXT_SAFE_ACTION`.

No chat-history reconstruction should be necessary for the next agent.
