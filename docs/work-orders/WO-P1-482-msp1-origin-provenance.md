# WO-P1-482 — MSP-1 privacy-preserving origin provenance

Issue: #482
Parent: #475 / MSP-1
Claim: WO-P1-482-MSP1-WINDOWS-001
Topology: CONTROL_PLANE_ONLY
Risk: R3
Status: PHASE_A_REVIEWED_REPAIR1_DIRTY_UNCOMMITTED
Exact base: 5d6cc12f8dfdcb069b2b4b8d9cd09aae76d54bf4
Dispatch HEAD (bootstrap accepted + claim bound): cbc05c0325f5cb71637e953dabc8284f637127ea
Reviewed candidate (PR #491 head): 18713ab31b0c4a9ab724ab8a51f02447e5041738
Repair claim: attempt-0001-482482482482 (sole owner; see Repair 1)
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
This is the consolidated record of the collision-affected attempt (two
executor-written evidence blocks were deduplicated in Repair 1); both
collision accounts below are preserved verbatim as material evidence.

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
  causation_id unchanged; lifecycle observability degradation path untouched.
  Parent candidate `origin_command_ref` deferred.

### RED evidence

1. Author RED suite + extended adapter tests before any production module
   (dispatch-HEAD base tree `git archive cbc05c0` into isolated temp copy,
   candidate tests overlaid): `2 collection errors — ModuleNotFoundError:
   a_conductor.origin_provenance` — seam absent at base.
2. After the module existed but before the adapter extension:
   `41 failed / 258 passed` — every failure is a missing adapter origin seam.

### GREEN evidence (final committed state at 18713ab)

- `python -m pytest tests/test_origin_provenance.py tests/test_control_hook_adapter.py -q` -> `282 passed`.
- `python -m pytest tests/test_lifecycle_assembly.py tests/test_control_events.py -q` -> `30 passed`.
- Related impacted: `tests/test_hook_contract_schema.py tests/test_lifecycle_assembly.py tests/test_control_events.py` -> `127 passed`.
- `py -3.13 -m py_compile src/a_conductor/origin_provenance.py src/a_conductor/control_hook_adapter.py` -> OK.
- `git diff --check` -> clean (CRLF normalization warnings only).
- Full suite: `3 failed / 4335 passed / 243 skipped`; the 3 failures
  (test_gpu_particle_logo x2, test_graceful_shutdown x1) have no import
  relationship to the seam and are pre-existing environment failures.
- Dirty tracked scope: exactly the five allowed paths.

### Collision history — duplicate dispatch on claim WO-P1-482-MSP1-WINDOWS-001 (material, preserved)

#### Collision account 1 — lane-collision disclosure (author perspective, post-incident)

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

#### Collision account 2 — execution collision report (executor B, contemporaneous)

Attempt-0001 ran with TWO concurrent executors on claim WO-P1-482-MSP1-WINDOWS-001 (duplicate dispatch; claim admission did not fence the second writer). Timeline (local): module written 22:45:35, adapter/tests 22:45-22:49 + full-suite + py3.13 compiles 22:46 by executor A; executor B (Kilo, this evidence) wrote module-level adversarial tests 22:48:59 and detected the collision 22:50-22:55. Resolution without clobbering: executor A's production seam adopted as canonical (first writer, complete, verified); executor B reconciled `tests/test_origin_provenance.py` to the canonical API, preserving its unique NFC/domain-separation/boundary/no-echo/import-surface/no-reverse-API coverage. Files were hash-guarded during reconciliation; no writes were lost. This incident is direct evidence for the MSP-2 admission-gap thesis (observe→dispatch race across integrators).

### Residual risks at review

1. `docs/contracts/hook-contract-v1.schema.json` is 1.0.0 with
   `additionalProperties:false` and was outside this WO's mutable scope, so
   envelopes carrying `origin_surface`/`origin_chat_session_ref` are not yet
   representable in the frozen schema. A separate contract-schema WO (e.g.
   1.1.0 adding both optional properties) is required before cross-surface
   schema-validated transport; until then existing schema tests intentionally
   omit origin fields. (Deferred by Repair 1 adjudication.)
2. The parallel-authored test suite dropped the author's frozen-construction
   known answer HMAC test, so the exact derivation byte-construction is no
   longer test-frozen. (Resolved by Repair 1: KAT re-added with an
   independently frozen literal.)
3. `chatgpt` origin surface intentionally unsupported in Phase A; adding it
   requires the separately accepted ChatGPT/SRM ingress child WO.
4. Production key custody remains entirely on the existing accepted secret
   resolver surface; nothing in this slice wires the helper to any key source
   (Phase A is derive/validate only; no runtime caller passes real keys; tests
   use fake keys exclusively).
5. `origin_command_ref` from the parent contract is deliberately not
   implemented (Phase A candidate fields limited to surface + session ref);
   origin fields are independently optional — pairing enforcement, if ever
   wanted, is a later contract decision.

Adjudication of the collision accounts above is recorded in Repair 1.

## Repair 1 — independent-review remediation (attempt-0001-482482482482, 2026-09-22)

Independent R3 review of exact candidate `18713ab31b0c4a9ab724ab8a51f02447e5041738`
(PR #491 head): behavior PASS — 409 tests plus adversarial probes green — with
acceptance blocked by:
- P2-1: no Known-Answer Test froze the exact HMAC byte construction/domain
  separation across releases.
- P2-2: the historical duplicate-dispatch collision required explicit
  integrator ownership adjudication in this durable record.
- P3-1: `_KEY_VERSION` and `ORIGIN_REF_PATTERN` duplicated the key-version
  regex fragment (drift risk).
- P3-2: WO header/narrative stale and duplicated after commit/collision.
- P3-3: keyless grammar-only derived-ref validation is BY DESIGN
  observation-only, never authentication.
- P3-4: hook schema 1.0 remains read-only/additionalProperties:false; not
  touched by this repair.

Sol adjudication (durable, closes P2-2 and the collision accounts above): the
final committed test content at `18713ab` was inspected by the integrator; 409
tests green; tree clean at the reviewed head; no live writer on the lane. The
duplicate-dispatch incident is closed with the committed content canonical.
This repair claim (attempt-0001-482482482482) is sole owner of exactly the
three mutable repair paths: `src/a_conductor/origin_provenance.py`,
`tests/test_origin_provenance.py`, and this WO file. The hook-contract schema
residual is explicitly deferred to a separate contract-schema WO; the schema
file was not touched (P3-4).

Repair actions on top of `18713ab` (tree left uncommitted for Sol harvest):
- P2-1: added `test_known_answer_freezes_exact_derivation_construction` with
  fixed fake key/version/surface/raw-ref and a literally frozen expected full
  ref, computed independently (standalone HMAC-SHA256 over the documented
  domain \0 version \0 surface \0 raw message; never recomputed from
  production logic inside the assertion). Companion
  `test_kat_literal_anchors_every_component_and_grammar` proves each component
  (key/version/surface/raw) changes the frozen literal and that the literal
  itself validates/parses under the durable grammar.
- P3-1: key-version grammar now composes one shared `_KEY_VERSION_FRAGMENT`
  used by both `_KEY_VERSION` validation and `ORIGIN_REF_PATTERN`; composed
  pattern verified byte-identical to the prior inline grammar.
- P2-2/P3-2: header status corrected; attempt-0001 evidence consolidated to a
  single section; both collision accounts preserved verbatim; residual-risk
  list merged with schema deferral and KAT resolution annotated.
- P3-3: no behavior change to validate/parse (keyless, observation-only);
  reaffirmed by the existing no-key/no-reverse-API tests.

Repair verification:
- `python -m pytest tests/test_origin_provenance.py tests/test_control_hook_adapter.py tests/test_hook_contract_schema.py tests/test_lifecycle_assembly.py tests/test_control_events.py -q` -> 411 passed.
- `python -m py_compile src/a_conductor/origin_provenance.py` -> OK.
- `git diff --check` -> clean.
- Dirty tracked scope: exactly the three repair paths.
- Added-line secret/session scan: none found.
