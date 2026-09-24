# WO-P1-509 — JEV-5 production admission and rollback

Status: CLAIMED / IMPLEMENTATION_READY
Issue: #509
Parent: #501
Topology: CONTROL_PLANE_ONLY
Risk: R3
Base: `554ace23b3493563c49685303bccb5228fd684a0`
Branch: `feat/wo-p1-509-jev5-production-admission`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo509-jev5`

## Dependency evidence

JEV-4 was accepted in PR #516: candidate `ae898db4d3aa4df49ecdcb8f3ea7834cbaa370a8`, merged as `84696b2360197c981d6f9fa2f33fb065b7b8ef07`; hosted post-main CI run `35846500955` completed SUCCESS. Issue #508 is administratively still open, but the required held-out implementation/evidence gate is merged and post-main verified.

## Goal

Admit the semantic fast path safely under real provider faults while preserving deterministic fallback and zero authority leakage. `OFF` remains the safe default. `SHADOW` and `ADVISORY` are admitted only per family when held-out evidence satisfies the accepted JEV-4 threshold contract.

## Invariants

- Jev/provider output is evidence only and never grants task, claim, WIP, mutation, review, merge, completion, release, or acceptance authority.
- Deterministic Git/runtime/tests/CI remain authority.
- No secrets, private operational payloads, unrestricted state text, auth headers, or hidden reasoning enter provider telemetry.
- Provider failure does not mutate underlying task/claim/scope.
- Rollback to `OFF` requires no task-state migration.
- Ambiguous transport outcome is never blindly replayed.

## Required behavior

1. Safe default `OFF` with no provider call.
2. Per-family `SHADOW`/`ADVISORY` admission consumes accepted held-out thresholds/evidence and fails closed when proof is missing or inconsistent.
3. Deterministic fallback/escalation for timeout, auth, 429, 529, 5xx, malformed response, identity/schema mismatch, and ambiguous transport.
4. Bounded circuit/cooldown state may suppress provider consultation but creates no scheduler/retry authority.
5. Privacy-safe normalized telemetry records family, mode, provider/model identity, validated disposition, confidence summary, latency/usage where safe, and typed fallback reason only.
6. Runtime kill-switch/rollback to `OFF` is deterministic and independent of provider health.
7. Fault E2E proves no authority leakage and no task-state migration.

## Initial mutable scope

Shape from current main, then keep the implementation bounded to the semantic decision/admission surface, its tests, this WO, and the A-Faster JEV reference only when documentation must reflect executable behavior. Do not modify #498 guard surfaces or unrelated scheduler/claim/lease code.

## Execution policy

A-Faster is active. Normal active compute remains `<=3 mutable + 1 independent review`; this lane owns only its admitted hotspot. Refresh CoinTH proxy quota and upstream provider readiness before every material GLM dispatch. Use GLM-5.3 MAX for eligible R3 implementation/review when admitted. If GLM route is blocked, GPT-5.6 Sol may perform bounded fallback without weakening independent-review requirements.

## Acceptance

- focused deterministic tests PASS;
- related JEV/provider regression suite PASS;
- fault matrix covers auth/429/529/5xx/timeout/ambiguous transport/malformed response;
- exact scope/diff/compile checks PASS;
- independent exact-SHA R3 review PASS with P0/P1/P2=0;
- hosted exact-head CI green;
- merge by expected exact head only;
- post-main CI and focused verification green before COMPLETE / POST_MAIN_VERIFIED.
