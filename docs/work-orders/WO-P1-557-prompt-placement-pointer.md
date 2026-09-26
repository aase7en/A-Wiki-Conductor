# WO-P1-557 — Universal prompt placement pointer

Status: IN_REVIEW
Issue: #557
Risk: R0 — docs-only governance pointer
Task topology: CONTROL_PLANE_ONLY

## Binding

Authority repo: `A-Wiki-Conductor`
Branch: `docs/wo-p1-557-prompt-placement-pointer`
Owner/integrator: GPT-5.6 Sol

## Goal

Expose the canonical A-Wiki prompt-placement protocol from the A-Sunday Conductor entry contract so prompts handed to users always state exact placement/mode/timing.

## Allowed scope

- `AGENTS.md`
- this Work Order
- PR/Issue metadata for review and closeout

## Forbidden scope

- `src/a_conductor/**`
- active #433 / #429 source or claims
- PR #556 Sunday Family roadmap scope
- SunDayRemoteMCP
- provider/model/runtime configuration

## Acceptance

- AGENTS references `aase7en/A-Wiki:docs/protocols/prompt-placement-protocol.md`.
- The pointer explicitly preserves existing task/claim/routing/review/acceptance authority.
- Diff is docs-only and `git diff --check` / hosted CI pass.
- Expected-head merge and post-main verification confirm the pointer on `main`.
