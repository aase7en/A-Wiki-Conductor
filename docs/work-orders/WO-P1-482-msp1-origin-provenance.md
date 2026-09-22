# WO-P1-482 — MSP-1 privacy-preserving origin provenance

Issue: #482
Parent: #475 / MSP-1
Claim: WO-P1-482-MSP1-WINDOWS-001
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: PHASE_A_GREEN_UNCOMMITTED
Exact base: 5d6cc12f8dfdcb069b2b4b8d9cd09aae76d54bf4
Dispatch HEAD (bootstrap accepted + claim bound): cbc05c0325f5cb71637e953dabc8284f637127ea
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

## Implementation evidence — attempt-0001-47757f98e87b (2026-09-22)

Dispatch HEAD `cbc05c0` matched the committed bootstrap; mutation gate re-run
by the dispatcher authorized Phase A mutation of the five allowed paths only.

### Design decisions

- `src/a_conductor/origin_provenance.py`: pure stdlib (hashlib, hmac, re, unicodedata).
  Public API: `derive_origin_chat_session_ref(key, *, key_version, origin_surface, raw_session_ref)`,
  `validate_origin_chat_session_ref`, `parse_origin_chat_session_ref`, `ORIGIN_REF_DOMAIN`,
  `ORIGIN_REF_PREFIX`, `ORIGIN_REF_PATTERN`, `ORIGIN_SURFACES`, `OriginProvenanceError(ValueError)` with code-only messages.
- Domain label: `a-conductor/msp1/origin-chat-session-v1`; HMAC-SHA256 over
  NUL-separated `domain \0 key_version \0 origin_surface \0 NFC(raw)`.encode("utf-8").
- Durable grammar: `origin-chat-v1:<key-version>:<64-lower-hex>`; key version
  `^[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$` (1-32 chars, alnum edges).
- Raw input: NFC canonicalization; UTF-8; fail-closed on empty/whitespace-only,
  leading/trailing whitespace, Cc/Cf/Cs/Co/Cn, Zl/Zp, non-ASCII Zs, surrogates,
  >256 chars / >1024 UTF-8 bytes. Errors echo codes only, never raw input.
- Key floor: injected `bytes` only, >=32 bytes. No secret read, no custody added.
- `ORIGIN_SURFACES = {a-conductor, srm, claude-code, kilo, rdc}` — mirrors the
  Hook Contract v1 `source` enum (current control-plane evidence vocabulary).
  `chatgpt` deliberately absent until a separately accepted ingress child; set
  is extensible by code change only.
- Hook extension: `ControlHookContext` gains optional `origin_surface` /
  `origin_chat_session_ref`; both validated (enum membership / derived-grammar
  fullmatch) and projected as observation-only envelope fields when present;
  absent fields keep envelopes byte-identical to the old contract (authority
  neutrality proven by test). No second command-ID namespace; correlation_id /
  causation_id unchanged. Parent candidate `origin_command_ref` deferred.

### RED evidence

1. Author RED suite + extended adapter tests before any production module:
   `2 collection errors — ModuleNotFoundError: a_conductor.origin_provenance`.
2. After the module existed but before the adapter extension:
   `41 failed / 258 passed` — every failure is a missing adapter origin seam.

### GREEN evidence (final on-disk state)

- `python -m pytest tests/test_origin_provenance.py tests/test_control_hook_adapter.py -q` -> `282 passed`.
- `python -m pytest tests/test_lifecycle_assembly.py tests/test_control_events.py -q` -> `30 passed`.
- `py -3.13 -m py_compile src/a_conductor/origin_provenance.py src/a_conductor/control_hook_adapter.py` -> OK.
- `git diff --check` -> clean (CRLF normalization warnings only).
- Full suite: `3 failed / 4335 passed / 243 skipped`; the 3 failures
  (test_gpu_particle_logo x2, test_graceful_shutdown x1) have no import
  relationship to the seam and are pre-existing environment failures.
- Dirty tracked scope: exactly the five allowed paths.

### Lane-collision disclosure (blocker for adjudication)

During final verification an unidentified parallel writer overwrote
`tests/test_origin_provenance.py` twice (23:00:21, 23:00:57 local) inside this
attempt's claimed mutable scope, replacing the author's RED/GREEN suite. The
parallel-authored suite is contract-compatible with the author implementation
(identical public API, domain label, error codes) and is fully green, so it was
left in place rather than triggering an edit war. Author's original suite,
hashes and timeline are preserved under
`runs/WO-P1-482/implementation/attempt-0001-47757f98e87b/collision-evidence/`.
No second attempt lane exists under runs/WO-P1-482 and no peer announced
itself. Ownership of the final test-file content needs GPT adjudication before
merge; the worktree must be checked for further foreign writes before freeze.

### Residual risks

1. `docs/contracts/hook-contract-v1.schema.json` is 1.0.0 with
   `additionalProperties:false` and was outside this WO's mutable scope, so
   envelopes carrying `origin_surface`/`origin_chat_session_ref` are not yet
   representable in the frozen schema. A separate contract-schema WO (e.g.
   1.1.0 adding both optional properties) is required before cross-surface
   schema-validated transport; until then existing schema tests intentionally
   omit origin fields.
2. The parallel-authored test suite dropped the author's frozen-construction
   known-answer HMAC test, so the exact derivation byte-construction is no
   longer test-frozen. Re-adding it (see collision-evidence/author suite) is
   recommended at adjudication because durable refs must never drift.
3. `chatgpt` origin surface intentionally unsupported in Phase A; adding it
   requires the separately accepted ChatGPT/SRM ingress child WO.
4. Production key custody remains entirely on the existing accepted secret
   resolver surface; nothing in this slice wires the helper to any key source.

## Phase A implementation evidence (2026-09-22, attempt-0001-47757f98e87b)

### Executed seam

- `src/a_conductor/origin_provenance.py`: pure HMAC-SHA256 derivation with domain label `a-conductor/msp1/origin-chat-session-v1`; grammar `origin-chat-v1:<key-version>:<64-lowercase-hex>`; key floor 32 bytes; raw-ref cap 256 chars / 1024 UTF-8 bytes post-NFC; Cc/Cf/Cn/Co/Cs + Zl/Zp + non-space Zs + C0/DEL + surrogate rejection; leading/trailing/whitespace-only rejection; typed code-only errors (`ORIGIN_PROVENANCE_{KEY,KEY_VERSION,SURFACE,SESSION_REF}_*`, ValueError base); public API derive/validate/parse only — parse takes no key.
- `src/a_conductor/control_hook_adapter.py`: optional `origin_surface` / `origin_chat_session_ref` context fields; surface must be in `ORIGIN_SURFACES`; ref must fullmatch the derived grammar; absent fields stay absent (backward compatible); correlation_id/causation_id remain command provenance; lifecycle observability degradation path untouched.
- `ORIGIN_SURFACES` = `{a-conductor, srm, claude-code, kilo, rdc}` (current Hook Contract v1 `source` evidence; `chatgpt` intentionally NOT accepted in Phase A — extendable by code change when ingress capture exists).

### RED evidence

Dispatch-HEAD base tree (`git archive cbc05c0` into isolated temp copy, candidate tests overlaid):
`python -m pytest tests/test_origin_provenance.py tests/test_control_hook_adapter.py -q` →
`ModuleNotFoundError: No module named 'a_conductor.origin_provenance'` — 2 collection errors, 0 run. Seam absent at base.

### GREEN evidence (worktree)

- `python -m pytest tests/test_origin_provenance.py tests/test_control_hook_adapter.py -q` → 282 passed.
- Related impacted: `tests/test_hook_contract_schema.py tests/test_lifecycle_assembly.py tests/test_control_events.py` → 127 passed.
- `py -3.13 -m py_compile src/a_conductor/origin_provenance.py src/a_conductor/control_hook_adapter.py` → OK.
- `git diff --check` → clean.
- Dirty tracked scope: exactly the five allowed paths (3 modified, 2 new).

### Execution collision report (material)

Attempt-0001 ran with TWO concurrent executors on claim WO-P1-482-MSP1-WINDOWS-001 (duplicate dispatch; claim admission did not fence the second writer). Timeline (local): module written 22:45:35, adapter/tests 22:45-22:49 + full-suite + py3.13 compiles 22:46 by executor A; executor B (Kilo, this evidence) wrote module-level adversarial tests 22:48:59 and detected the collision 22:50-22:55. Resolution without clobbering: executor A's production seam adopted as canonical (first writer, complete, verified); executor B reconciled `tests/test_origin_provenance.py` to the canonical API, preserving its unique NFC/domain-separation/boundary/no-echo/import-surface/no-reverse-API coverage. Files were hash-guarded during reconciliation; no writes were lost. This incident is direct evidence for the MSP-2 admission-gap thesis (observe→dispatch race across integrators).

### Residual risks

1. `docs/contracts/hook-contract-v1.schema.json` (read-only in this WO) pins `additionalProperties: false` at 1.0.0 without origin properties: origin-bearing envelopes pass adapter/JSON-round-trip validation but are rejected by strict schema validators until a schema minor-bump slice declares `origin_surface`/`origin_chat_session_ref`.
2. Production key custody injection site does not exist yet (Phase A is derive/validate only; no runtime caller passes real keys). Tests use fake keys exclusively.
3. `origin_command_ref` from the parent contract is deliberately not implemented (Phase A candidate fields limited to surface + session ref).
4. Origin fields are independently optional (surface without ref accepted); pairing enforcement, if ever wanted, is a later contract decision.
