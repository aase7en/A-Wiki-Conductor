# WO-P1-482 — MSP-1 privacy-preserving origin provenance

Issue: #482
Parent: #475 / MSP-1
Claim: WO-P1-482-MSP1-WINDOWS-001
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: GOVERNANCE_BOOTSTRAP / SOURCE_MUTATION_HOLD
Exact base: 5d6cc12f8dfdcb069b2b4b8d9cd09aae76d54bf4
Branch: feat/wo-p1-482-msp1-origin-provenance
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo482-msp1

## Goal

Add privacy-preserving, non-authoritative origin/session provenance to existing A-Sunday Conductor hook evidence without creating any session registry, lock, task, claim, lease, scheduler, retry, review or completion authority.

Parent contract:
- origin metadata is privacy-preserving and non-authoritative;
- candidate fields are origin_surface, origin_chat_session_ref and origin_command_ref;
- raw platform IDs are not persisted unless a separately accepted privacy contract allows it;
- chat alias/title is display-only;
- origin fields never block legitimate takeover from another chat;
- reuse existing hook command_ref/correlation/causation instead of a second command-ID namespace.

## Fresh shaping evidence

GLM-5.3 Flash read-only archaeology on main@5d6cc12 returned ADVISORY_PASS:
- CONTROL_PLANE_ONLY for this Phase A;
- reuse control_hook_adapter Hook Contract v1 and lifecycle hook-context injection;
- reuse existing secret resolver/custody surfaces; no raw secret in repo/log/result;
- no existing keyed HMAC helper exists;
- smallest new seam is a pure origin provenance helper with versioned/domain-separated HMAC references;
- no P0/P1/P2; only nonblocking P3 hardening notes.

## Mutable scope after this bootstrap is accepted

Exactly:
- src/a_conductor/origin_provenance.py (new)
- src/a_conductor/control_hook_adapter.py
- tests/test_origin_provenance.py (new)
- tests/test_control_hook_adapter.py
- docs/work-orders/WO-P1-482-msp1-origin-provenance.md

Everything else is read-only.

## Required semantics

1. New durable origin/session references are HMAC-derived, versioned, domain-separated opaque identifiers.
2. Raw platform/chat/session identifiers, tokens, cookies, share URLs and provider/connector secrets are never persisted in repo/log/result/event/task packet/issue/PR/telemetry by this slice.
3. The helper receives key material through dependency injection/testing; production secret custody remains the accepted existing resolver surface. No secret file is read by the delegated author/model.
4. Key rotation produces a new versioned reference. Old references remain opaque-readable without requiring the old key. No automatic re-identification or migration.
5. Errors are code-only and never echo raw origin input.
6. Unicode/canonicalization, empty/control/oversize values, malformed versions and unknown origin surfaces fail closed.
7. origin_* hook metadata is optional observation/context only. It never grants or influences mutation, task, claim, lease, scheduler, retry, review, completion or writer selection.
8. Reuse existing correlation_id / causation_id for command provenance. No new command-ID namespace.
9. No store/DB/session-lock/task/scheduler/claim authority is added.
10. This Phase A does not implement ChatGPT-facing/SRM ingress capture. CROSS_REPO escalation requires a separate accepted child.

## RED-first acceptance

Tests must prove:
- deterministic same key/surface/raw-id/version => same ref;
- key/version/surface/domain changes => different ref;
- NFC-equivalent Unicode canonicalizes deterministically;
- control/surrogate/empty/oversize input fails closed;
- raw-ID/share-URL/token-like material never appears in output/error/repr/serialized hook envelope;
- rotation/no-reidentification behavior;
- malformed/unknown origin metadata fails hook validation;
- hook JSON round-trip preserves only sanitized derived refs;
- authority-neutrality negative tests;
- origin_provenance imports no store/DB/process/network/claim/lease/scheduler authority;
- related focused regression, py_compile and git diff --check pass.

## Delivery gates

RED -> GREEN -> deterministic verification -> exact candidate freeze -> independent GLM-5.3 MAX R3 review -> exact-head hosted CI -> Sol acceptance -> expected-head merge -> post-main verification.

No source mutation is authorized until this docs-only bootstrap is committed/pushed and the mutation gate is re-run against actual Git/GitHub/runtime state.
