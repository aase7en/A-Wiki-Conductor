# WO-P1-376 — Kilo Hook Adapter v1 re-pin + canonical identity repair

Status: POST-MAIN VERIFIED / DEPENDENCY REBIND VIA WO-P1-258 POST-MERGE REPAIR
Issue: #376
Identity schema: GITHUB_ISSUE_V1
Risk: R3 contract/conformance
Topology: CONTROL_PLANE_ONLY
Dependency: WO-P1-258 Hook Contract repair exact 0d4f0c3b36ff7fad9ed14636730443119683cb1d
(md blob 25f69a964140c082db9d43b65dd3fcd9dbfc0c3c,
schema blob 98451ee3a4b63b4f07ca7b38525f9f5016916d54)

## Binding
Repo: aase7en/A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo376-kilo-hook-rebind
Branch: fix/wo-p1-376-kilo-hook-rebind
Dispatch HEAD: a98f589b870f6c55f0b6470c6a587109cc2ebdda
(current main 6c49b6d1168372337dac3a18e6894c69436d6f8b merged into dispatch)
Owner: GLM-5.3 repair executor under integrator dispatch
Claim: WO-P1-376-KILO-HOOK-ADAPTER-REBIND-001

## Mutable scope (repair lane)
docs/contracts/kilo-hook-adapter-v1.md
tests/test_kilo_hook_adapter_contract.py
tests/fixtures/hook_adapters/kilo/**
this Work Order (renamed from WO-P1-262-kilo-hook-adapter-v1.md)
Everything else read-only; no src/runtime mutation; Hook Contract
files/schema/tests, Claude adapter files, WO369/WO381/A-Faster/A-FastTask
scope forbidden.

## Goal
Rebind the Kilo Hook Adapter v1 canonical identity from the WO-P1-262
author lane to WO-P1-376 / Issue #376, and re-pin its dependency from the
author-era Hook Contract pin to the accepted Hook Contract 602f6db
(review-001 dedupe identity, stream-domain ordering, adapter-payload
constraint) without changing adapter behavior authority: OBSERVE-only,
GUARD/COMMAND forbidden, ordering/dedupe delegated to Hook Contract
§4/§5, no source+sequence dedupe identity, adapter payload only on
`transport.adapter_capabilities`, version/provider/capability fail-closed
behavior preserved, no new runtime/store/claim/retry/review authority.

## Acceptance
Adapter + Hook Contract suites green on the re-pinned dependency; diff
check clean; strict UTF-8 (no U+FFFD); secret scan clean; scope exactly
the four allowed paths; Claude adapter files and all forbidden scope
proven unchanged; historical WO262 truth preserved verbatim below;
checkpoint appended with prior/new SHAs and evidence; commit only when
green; no self-accept/merge.

Result destination: runs/WO-P1-376/repair/
Replay safety: recover pointer/process/result/Git before redispatch.

## Historical alias / identity migration (WO-P1-262 → WO-P1-376)

This work order file was authored as
`docs/work-orders/WO-P1-262-kilo-hook-adapter-v1.md` and renamed to
`docs/work-orders/WO-P1-376-kilo-hook-adapter-v1.md` by the rebind.
WO-P1-262 is NOT current task authority after this rebind; WO-P1-376 /
Issue #376 is. The following WO-P1-262 facts remain true historical
evidence and are preserved unchanged:

- Historical claim: WO-P1-262-KILO-HOOK-ADAPTER-001.
- Historical lane/owner: GLM-5.3 MAX author under GPT-5.6 Sol.
- Historical worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo262-kilo-hook-adapter
- Historical PR transport branch: `docs/wo-p1-262-kilo-hook-adapter-v1`
  (historical transport naming only; may remain as-is).
- Historical dispatch HEAD: 06377ee0a0a353919c997fc50ca7862af2866c7c.
- Historical adapter candidate SHA: a0c2f71ff8815aeef2780dd36fd01098a2c05ee0.
- Historical dependency pin: Hook Contract exact
  f20fff006aad1e592b150ffdcb52ac331ec00a3a (pre-review-001).
- Historical result destination: runs/WO-P1-262/author/ — all evidence
  paths under `runs/WO-P1-262/...` (including
  `runs/WO-P1-262/author/attempt-0001/kilo-sanitized.ndjson` referenced by
  adapter fixtures and the Kilo capability evidence) remain factual
  historical evidence and were NOT rewritten by the rebind.
- Historical mutable scope was NEW-only: docs/contracts/kilo-hook-adapter-v1.md,
  tests/test_kilo_hook_adapter_contract.py, tests/fixtures/hook_adapters/kilo/**,
  and this work order.

## Checkpoint 2026-09-19 — WO-P1-262 author attempt-0001 READY_FOR_REVIEW (historical)

Delivered exactly the four-path NEW-only scope on top of dispatch HEAD
06377ee0a0a353919c997fc50ca7862af2866c7c (dependency f20fff0 verified as
parent; tree clean before mutation):

- docs/contracts/kilo-hook-adapter-v1.md — adapter contract: safe
  capability evidence (Kilo CLI 7.7.2; `kilo run --format json` raw JSON
  events; `plugin` install surface with UNPROVEN lifecycle vocabulary),
  OBSERVED/ASSUMED/UNKNOWN capability table, fixture grammar, Hook
  Contract v1 mapping, identity/ordering/dedupe (supports_sequence=false,
  arrival order, no synthesized sequence, no second event store), digest-
  only redaction, capability discovery + fail-closed mismatch rules.
- tests/fixtures/hook_adapters/kilo/** — capability doc, 6 native-shaped
  fake streams (basic/redaction/provider-mismatch/version-drift/
  version-unverified/invalid-records), 2 generated expected-envelope
  files, README provenance.
- tests/test_kilo_hook_adapter_contract.py — deterministic reference
  mapper + 21 offline conformance tests (exact expected equality, schema
  validity, dedupe/identity stability, corpus/share-URL exclusion with
  digest verification, unknown type/status/record typed drops, version/
  provider-model/capability fail-closed, metadata-only model proof).

Evidence: adapter suite 21 passed; Hook Contract suite 82 passed (103
total incl. parametrized); `git diff --check` clean; strict UTF-8 decode
of all 20 added files; added-line secret scan 0 non-fake hits (only the
declared fake-secret-corpus/1 and one fake share-URL shape inside native
redaction fixtures); normalized outputs carry no fakes. Kilo capability
evidence recorded at runs/WO-P1-262/author/attempt-0001/
kilo-capability-evidence.md (gitignored). No src/runtime mutation; Hook
Contract files untouched.

Risks/unknowns for review: (1) `tool_use.state.status` vocabulary,
timestamp offsets, and part-field placement are ASSUMED fixture grammar,
not observed — live emission requires capability discovery re-proof;
(2) plugin lifecycle APIs remain UNKNOWN and unmapped by design;
(3) adapter binds to native family 7.7.x (observed 7.7.2) and fails
closed on any other version until re-pinned.

Historical next step (completed by WO-P1-376): independent exact-SHA
review + CI on the branch head; GPT accept/merge authority retained.

## Checkpoint 2026-09-19 — WO-P1-376 rebind/re-pin attempt-0001 READY_FOR_REREVIEW

Executed on dispatch HEAD a98f589b870f6c55f0b6470c6a587109cc2ebdda
(branch fix/wo-p1-376-kilo-hook-rebind, tree clean before mutation;
prior adapter candidate a0c2f71ff8815aeef2780dd36fd01098a2c05ee0
verified as ancestor of HEAD; current main 6c49b6d1168372337dac3a18e6894c69436d6f8b
verified merged into dispatch).

Identity rebind (this file + adapter contract + test module + fixture
README): canonical task/claim/result-destination/test-module identity
rebound WO-P1-262 → WO-P1-376 / Issue #376; exact marker
`Identity schema: GITHUB_ISSUE_V1` added to this work order and asserted
by machine conformance; work-order file renamed
WO-P1-262-kilo-hook-adapter-v1.md → WO-P1-376-kilo-hook-adapter-v1.md
(git rename detection R); Historical alias / identity migration section
added above preserving every WO262 fact (claim, lane/owner, worktree,
transport branch naming, dispatch HEAD, candidate SHA a0c2f71, prior
pin f20fff0, result destination, evidence paths). All
`runs/WO-P1-262/...` evidence pointers in the adapter contract, fixture
stream-meta files, and expected-envelope fixtures were left unchanged as
factual historical provenance.

Contract re-pin (f20fff006aad1e592b150ffdcb52ac331ec00a3a →
602f6db01e170f74456ff77e1b5df01622fb84dd via merge
2a461ae22ab28ad3b48f15660ab818f700faab30): adapter §6 rewritten to
DELEGATE ordering/dedupe identity to Hook Contract §4/§5 (review-001) —
duplicate identity = explicit deliberate `dedupe_key` else global
`event_id`, never `source`+`sequence`; ordering stream domain
`(source, device_id, observed transport/adapter session context)`, never
bare `source`; append-only history and cross-stream k-way merge stay with
the downstream projection. §1 now explicitly forbids GUARD/COMMAND
emission and gate semantics (stream delivery is never an enforcement
point). §5 adds the Hook Contract §14 constraint: `adapter` payload
legal only on the `transport.adapter_capabilities` OBSERVE event
(schema-enforced in 1.0.0). OBSERVE-only payload surface unchanged
(`transport.adapter_capabilities` remains the sole non-mapping payload);
version/provider/capability fail-closed behavior unchanged; no new
runtime/store/claim/retry/review authority anywhere.

Conformance repair/regression pins (Hook Contract tightening caused no
behavioral mapping failures; the dependency-pin assertion and delegation
prose were the drift): test module dependency test re-pinned to 602f6db
with stale-pin rejection (f20fff0 asserted absent from the adapter
contract) and identity-marker assertion; two new regression tests —
`test_replay_identity_is_explicit_dedupe_key_never_source_sequence`
(every envelope carries an explicit `kilo:` dedupe_key, no `sequence`
field, distinct records never collapse identity) and
`test_adapter_payload_is_legal_only_on_capability_event` (negative
schema proof that `adapter` on `tool.execute.before` is invalid).

Evidence: adapter suite 23 passed (21 prior + 2 new); Hook Contract
suite 97 passed; full repo suite 3270 passed / 12 skipped / 2 failed —
both failures pre-existing environmental GPU/OpenGL tests
(tests/test_gpu_particle_logo.py, "Pillow is required for GPU particle
sampling") with zero overlap with adapter scope and src/ proven
unchanged. `git diff --check` clean (unstaged, staged, and full vs
a98f589); strict UTF-8 decode with no U+FFFD on all 4 changed files;
added-line secret scan over 218 added lines: 0 hits. Changed scope
exactly: docs/contracts/kilo-hook-adapter-v1.md,
docs/work-orders/WO-P1-262-kilo-hook-adapter-v1.md →
docs/work-orders/WO-P1-376-kilo-hook-adapter-v1.md (rename),
tests/fixtures/hook_adapters/kilo/README.md,
tests/test_kilo_hook_adapter_contract.py. Forbidden scope proven
unchanged vs a98f589: src/**, docs/contracts/hook-contract-v1.md,
docs/contracts/hook-contract-v1.schema.json, tests/test_hook_contract_schema.py,
Claude adapter files (src/a_conductor/claude_code_harness.py,
src/a_conductor/claude_code_job_assembly.py, Claude work orders/docs)
all show an empty diff.

Risks bounded: mapping behavior and expected envelopes are byte-identical
to the reviewed WO262 candidate (no fixture/expected-file content
change); delegation rewrite is prose-level with machine regression pins;
live-emission unknowns (status vocabulary, timestamp offsets, plugin
lifecycle) remain UNKNOWN per §2.3 and still require capability
discovery before any live use.

Next: integrator fast-forward the original PR transport branch
(docs/wo-p1-262-kilo-hook-adapter-v1) if unchanged → exact-SHA
independent review + CI on this branch head; GPT accept/merge authority
retained. No self-accept/merge.

## Post-merge Hook repair dependency rebind (2026-09-20)

- WO-P1-376 was previously accepted and post-main verified against Hook Contract
  candidate 602f6db01e170f74456ff77e1b5df01622fb84dd.
- WO-P1-258 later required a forward-only post-merge repair. Exact repaired
  contract commit is 0d4f0c3b36ff7fad9ed14636730443119683cb1d with md blob
  25f69a964140c082db9d43b65dd3fcd9dbfc0c3c and schema blob
  98451ee3a4b63b4f07ca7b38525f9f5016916d54.
- Kilo mapping fixtures/runtime semantics remain unchanged; the adapter contract
  and machine conformance now pin the repaired commit plus exact blobs and fail
  closed on future blob drift.
- Prior accepted 602f6db dependency remains explicit historical evidence;
  earlier WO262/f20fff provenance remains unchanged where historically recorded.
- This follow-up is executed inside the bounded WO-P1-258 repair scope expansion
  on Issue #368; Issue #376 remains historical/post-main complete.
