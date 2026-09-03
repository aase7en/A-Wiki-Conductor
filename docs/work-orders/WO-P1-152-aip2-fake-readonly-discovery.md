# WO-P1-152 — AIP-2 fake/read-only discovery

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: CLAIMED / RED_FIRST
Priority: P1
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo152-aip2-fake-discovery`
Branch: `feat/wo-p1-152-aip2-fake-discovery`
Base: `origin/main@128844c7d719a61c959f2a20df3a8646ddabef8c`

## Goal
Implement the smallest AIP-2 contract proving AiPASS-shaped model/quota discovery with deterministic fake payloads and zero prompt execution.

This work order is a pure decoder/projection slice. It does not connect to AiPASS, start a bridge/browser, access a session, send a message, resolve credentials, or mutate provider configuration/persistence.

## External gate
Official AiPASS Terms effective 2026-08-19 section 3.4 still require explicit written authorization for specified bot/unapproved-software access and direct non-UI API/API-key/token access. Therefore live discovery remains `BLOCKED_EXTERNAL` here.

Current source-reference evidence at claim: `niawjunior/aipass-bridge@d5b9839777276f5363c36bd5a37547a847928e58`, MIT. Source permission is not service authorization.

## Reuse-before-build
Classification: `REUSE + EXTEND`, with one new ephemeral discovery DTO only.

REUSE:
- `QuotaSnapshot` for normalized shared-credit truth;
- existing provider generation semantics; discovery is bound to a positive configuration generation;
- `ProviderConfiguration.models` remains configuration authority and is never silently overwritten by discovery;
- WO148 `SERVICE_AUTHORIZED` remains a separate future live-I/O gate;
- existing provider observation/store/readiness authorities remain untouched.

EXTEND:
- new pure AiPASS-shaped model/quota decoder and immutable ephemeral discovery snapshot.

REJECT:
- new provider store/readiness/quota engine/registry;
- live HTTP/browser/session/cookie/token code;
- automatic model-configuration mutation;
- chat/media/conversation execution;
- endpoint/session values in durable output.

## Mutable scope
- `docs/work-orders/WO-P1-152-aip2-fake-readonly-discovery.md`
- `src/a_conductor/aipass_discovery.py`
- `tests/test_aipass_discovery.py`

All other files are forbidden without an explicit scope amendment. Shared SSoT hotspots are intentionally excluded.

## Contract direction
The upstream reference currently projects `/v1/models` with `id`, `name`, `free_credit`, `thinking`, `kind`, `description`, `is_default`, and optional `options`; `/quota` projects normalized shared-credit fields plus optional video quota.

AIP-2 must preserve only bounded safe facts needed for later routing/operator work. Dynamic model discovery remains ephemeral observation, not capability/configuration authority.

Shared credit may map to one existing `QuotaSnapshot(window_type="shared_credits", unit="credits")`. Per-model `free_credit` remains model metadata. Optional video quota must not be collapsed into the shared quota.

## RED-first acceptance
- module-absent RED before production implementation;
- valid model-list fixture decodes deterministically and preserves model order canonically;
- duplicate/blank/unsafe model IDs fail closed;
- free-credit missing stays `UNKNOWN`/`None`, never invented;
- malformed/unknown optional model fields are bounded or ignored by explicit contract;
- valid shared quota maps exactly to `QuotaSnapshot`; contradictory/non-finite/negative quota fails closed;
- optional video quota is typed separately from shared quota;
- configuration generation is positive and preserved exactly;
- stale/empty/unavailable fixture states are explicit data, not provider readiness;
- serialized discovery contains no URL, cookie, credential, authorization header, raw endpoint, or session/conversation identifiers;
- ordinary fake fixtures require no browser/login/network/process/database I/O.

## Verification
Focused tests, existing provider configuration/store/service-auth regressions, compile, diff-check, strict UTF-8/U+FFFD, exact three-file scope, import/AST no-I/O gate, and adversarial serialization probes.

Independent GLM shaping/review may refine this contract before merge; any P0/P1/P2 finding requires RED-first repair and a new exact-SHA review.
