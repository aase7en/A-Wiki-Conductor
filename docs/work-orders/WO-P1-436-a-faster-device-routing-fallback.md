# WO-P1-436 — A-Faster device routing, GLM-first labor, Sol fallback

Status: ACTIVE / CLAIMED
Issue: #436
Risk: R2 — routing/governance behavior
Topology: CONTROL_PLANE_ONLY

## Binding
- Authority repo: `aase7en/A-Wiki-Conductor`
- Worktree: `/Users/aase7en/Desktop/A-Wiki-Conductor-wo436-a-faster-routing`
- Branch: `docs/wo-p1-436-a-faster-device-routing`
- Base / claim head: `de8b037cfd78e4513656b726981caee05d5bb39b`
- Claim: `WO-P1-436-A-FASTER-DEVICE-ROUTING-001`
- Owner/integrator: GPT-5.6 Sol
- Evidence: Issue #436 + Git/GitHub exact-SHA evidence

## Goal

Make one `use A-Faster` / `ใช้ A-Faster` invocation automatically apply the user's preferred Windows/macOS execution routing, GLM-first long-running labor, GPT-5.6 Sol fallback, and cross-device collision synchronization without repeated prompts.

This extends A-Faster routing only. It creates no scheduler, task store, claim/lease store, review/completion authority, provider authority, or shadow SSoT.

## Exact mutable scope
- `.agents/skills/a-faster/SKILL.md`
- `.agents/skills/a-faster/references/multidevice.md`
- `docs/work-orders/WO-P1-436-a-faster-device-routing-fallback.md`

Everything else is read-only.

## Required behavior

1. Windows prefers exposed SunDay-Worker 1..5 as its primary repo/code execution surface; RDC is secondary for inspection, recovery, machine operations, and fallback.
2. macOS uses RDC as the default chat-visible execution surface; local Serena may exist but is not required or assumed as a primary surface.
3. On both devices, eligible long-running bounded labor prefers Kilo/Claude CLI with GLM-5.3 MAX or GLM-5.3-Flash after exact route, quota, claim, scope, and worktree gates.
4. MAX is default for implementation/repair/R2-R3/high-reasoning work. Flash is bounded read-only assistance and never substitutes for a required MAX/qualified review.
5. If GLM is blocked by proven quota exhaustion, route/admission failure, auth/entitlement, transport, or unavailable harness, classify the cause accurately and let GPT-5.6 Sol directly continue any eligible safe task rather than leaving it idle.
6. `QUOTA_UNKNOWN` must never be treated as exhausted. Never silently switch model/provider/harness.
7. Reconstruct the global lane occupancy/collision projection at material lifecycle boundaries across all devices/sessions. Preserve global `3 mutable + 1 review` and `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`.
8. Cross-device updates use durable Work Order/Issue/branch/exact-SHA/run-pointer evidence. The user is not a relay.
9. Collision checking is lifecycle/event driven within active invocations; do not claim plain ChatGPT self-wakes or continuously polls after a turn ends.
10. A-FastTask remains router/binder only; A-Faster remains an overlay.

## Collision pulse boundaries
At minimum refresh/reconcile before A-Faster entry allocation, before material dispatch, before mutation, after material lane state transition/harvest, before Windows↔Mac handoff, before freeze, before fan-in/merge, and after material remote-main drift is observed.

## Verification
- exact three-path scope
- `git diff --check`
- strict UTF-8 / no U+FFFD
- A-Faster frontmatter/reference integrity
- `tests/test_work_order_identity.py`
- added-line secret-shaped scan
- independent exact-SHA R2 review
- exact-head hosted CI
- GPT-5.6 Sol exact-SHA acceptance, merge, post-main verification

## Replay / continuity safety

Fresh sessions recover Issue #436, this WO, actual Git/worktree state, active delegated-run pointers, and current remote main before dispatch or mutation. A transport/chat timeout never grants replay authority.

## Initial checkpoint

Collision census before claim found no recent local A-Faster pointer on Mac or Windows. Historical A-Faster branches `WO256`, `WO260`, `WO387`, and `WO404` are all fully behind current main with zero commits ahead. Open PR search found no current branch owning this exact A-Faster hotspot. The claim therefore owns only the exact mutable scope above.
