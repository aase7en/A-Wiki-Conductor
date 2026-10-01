# WO-P1-152 — AIP-2 fake/read-only discovery

Date: 2026-09-03
Owner: GPT-5.6 Sol MAX
Status: READY_FOR_INDEPENDENT_REREVIEW / HOSTED_CI_PENDING
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

Shared credit may map to one existing `QuotaSnapshot(window_type="aipass_shared_credits", unit="credits")`. Per-model `free_credit` remains model metadata. Optional video quota must not be collapsed into the shared quota.

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

## Implementation checkpoint — 2026-09-03
- Claim checkpoint: `d95154fcca994f8641a4ed8299e069bfebb6aa06`.
- Module-absent RED: `4131b121cdeba0a83ec2db424022fc180c22e1e1`; collection failed only because `a_conductor.aipass_discovery` did not exist.
- Cached-quota freshness RED: `bf12eb014ed49eb9fea2b725ff1a417264b5d971`; 2 intended failures proved stale/future `fetchedAt` was not yet authority.
- Data-boundary RED: `466fdf74bd4ab663c2ae7e40c7b8fc99e0fe7626`; 2 intended failures proved unsafe display metadata serialization and extreme-number exception escape.
- Source implementation: `7fcf6cff4354c7fe869edc0998634a31cbf1e525`.

Implemented semantics:
- pure supplied-payload decoder only; no network/process/browser/database/filesystem I/O;
- deterministic model inventory sorted by exact model ID;
- unknown `free_credit` remains `None`; unknown optional capability-like fields gain no authority;
- unsafe display metadata falls back to exact model ID rather than crossing the projection boundary;
- shared credits and video quota reuse `QuotaSnapshot` as separate windows;
- quota `fetchedAt` participates in snapshot staleness and cannot be missing/future when quota facts exist;
- numeric quota facts are finite/non-negative and bounded to the JSON/JavaScript safe-number domain;
- discovery remains ephemeral and generation-bound; it never rewrites configured models/readiness/authorization/admission.

Verification at source freeze:
- focused `tests/test_aipass_discovery.py`: **13 passed**;
- provider/store/runtime/service-auth impact matrix: **284 passed**;
- `py_compile`: PASS;
- `git diff --check`: PASS;
- strict UTF-8/U+FFFD: PASS;
- AST/import no-I/O gate: PASS;
- scope remains exactly this WO + new decoder + focused test.

Next gate: commit this documentation checkpoint, push a clean exact review SHA, then require fresh independent exact-SHA review with P0/P1/P2=0 before PR/merge.
## Current-main composition checkpoint — 2026-09-03
- `origin/main` advanced to `b2b624300e9fc8d9e6486f6798b2827995585982` via accepted WO147 / PR #200 while WO152 was in verification.
- PR #200 changed only WO147 work-order/source/test files; overlap with WO152 mutable scope = **0 files**.
- Current main was composed into the isolated WO152 branch as `819772a18efda8979e202498c72060939e55a5c6`.
- All three WO152 Git blobs are byte-identical to pre-compose review checkpoint `684f1bc127369e0e81e351472009adb90a0b4c38`.
- Delta versus current `origin/main` remains exactly the WO152 work order, decoder, and focused test.
- Post-compose focused tests: **13 passed**.
- Post-compose provider/store/runtime/service-auth matrix: **284 passed**.

Review authority must pin the final checkpoint commit created after this note, not `684f1bc...` or `819772a...`.
## GPT P2 repair claim - 2026-09-03
- GPT primary adversarial probe against exact `d9343ad52cce71614009d6a4bbf49c1f1035dbd8` proved untrusted credential-shaped model metadata can cross `AiPassDiscoverySnapshot.to_dict()`: `name=ghp_*`, `name=Bearer ...`, and token-shaped `model_id` remain serialized as `DISCOVERY_OK`.
- Prior exact-review candidate `d9343ad...` and queued `wo152-glm-final-review-002` are stale for acceptance.
- Scope remains exactly this WO, `src/a_conductor/aipass_discovery.py`, and `tests/test_aipass_discovery.py`. No live AiPASS/provider/store/runtime mutation.
- Next: RED-first tests for credential-shaped model ID/display metadata, then the smallest pure decoder repair.

## GPT P2 repair checkpoint - 2026-09-03
- RED `660639b57064d3495a7954f08465f8bd47660703`: 4 intended failures / 13 existing PASS proved credential-shaped model IDs and display metadata could cross serialized discovery output.
- A self-review safe-control then proved an overbroad bearer guard would hide ordinary `Bearer Capacity`; that control failed before the guard was tightened.
- Repair `ca046d04b44f5b29447c6855bf3ad83d0db021c6` rejects high-confidence credential-shaped model IDs, falls unsafe display names back to the safe model ID, and preserves ordinary semantic display text.
- Current main advanced via WO151 / PR #203 to `1ae477f05e597c5027d22fdb2ca4f1496c070db7`; composed WO152 head before this documentation checkpoint is `368e020d811a837f9908ea08eea5e8e78f4a2db0`.
- Post-compose focused `tests/test_aipass_discovery.py`: 18/18 PASS.
- Provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota impact matrix: 344/344 PASS.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST/import no-I/O gate, direct serialization probes, and added-line credential scan: PASS.
- Delta versus current main remains exactly this WO + `src/a_conductor/aipass_discovery.py` + `tests/test_aipass_discovery.py`.
- GitNexus impact is UNVERIFIED: the available A-Wiki-Conductor index is from a stale sibling worktree and FTS has the known Windows OpenSSL DLL limitation; no repository-mutating analyze or DLL install was attempted.
- PR #203 post-main CI `33750907975` is still pending at this checkpoint. Independent review may proceed on the final WO152 SHA, but PR/merge remains blocked until that dependency is terminal green.
- Next safe action: fresh independent exact-SHA review with raw Git-blob pins; P0/P1/P2 must be zero before PR/merge.

## GPT P2 generic `sk-` repair checkpoint — 2026-09-03
- Primary near-neighbor probe after `6c1e554...` found long generic `sk-proj-...` / `sk-...` credential-shaped model IDs still serialized as `DISCOVERY_OK`.
- RED `5992aec0a472617e072c8c8bc9e19b997df5a0ff`: 1 intended failure / 18 existing PASS; semantic controls `sketch-model` and `sk-model-small` remained required-positive cases.
- Repair `6d8b6087b8fb154552b0a4c1b765dfb47619bdb8` adds only a high-confidence long `sk-` credential-shape detector; semantic near-neighbors remain accepted.
- Focused discovery suite: **19/19 PASS**.
- Provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota matrix: **344/344 PASS**.
- compile/diff-check, strict UTF-8/U+FFFD and AST/import no-I/O gates: PASS.
- Scope remains exactly this WO + decoder + focused test; no live AiPASS/store/config/readiness/authorization/admission/runtime mutation.
- All earlier WO152 review tasks/candidates are superseded for acceptance; next gate is a fresh exact-SHA independent review after this checkpoint is committed and pushed.

## GPT P2 expanded credential-prefix repair checkpoint - 2026-09-03
- GPT self-audit against exact `ceb17606ed3f10d515ea4727e20acacad27ba62b` found additional high-confidence credential prefixes (`github_pat_`, Stripe-style `sk_live_` / `sk_test_` / `rk_live_` / `rk_test_`, `glpat-`, `npm_`, `pypi-`, and AWS temporary `ASIA...`) could still cross model ID/display-name serialization.
- RED `481c145`: **18 intended failures / 20 existing PASS**; semantic near-neighbor controls remained green, proving the test boundary was not broad keyword rejection.
- Repair `930ec4c017798a13b3de08117f6c7f5e134d5a27` extends only the high-confidence credential-shape guard. Unsafe model IDs fail typed; unsafe display names fall back to the already-safe model ID.
- Focused discovery suite after repair: **38/38 PASS**.
- Provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota matrix: **344/344 PASS**.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST/import no-I/O, exact-scope audit, **34 malicious serialization checks**, and **10 semantic safe controls**: PASS.
- `origin/main` remains `1ae477f05e597c5027d22fdb2ca4f1496c070db7`; feature delta remains exactly the WO + decoder + focused test.
- Candidate `ceb1760...` and any review pinned to it are superseded for acceptance. The next review must pin the final documentation checkpoint commit after this note.


## GPT P2 embedded private-path repair checkpoint - 2026-09-03
- GPT adversarial pass after `259beabe0591836b8b93332c0f95b2d1710e36ec` proved display metadata could still carry absolute private-path/endpoint shapes when preceded by whitespace or ordinary text, including POSIX, Windows drive, UNC, and embedded `/v1/...` route shapes.
- RED `7cdcd73`: **7 intended failures / 39 existing PASS**; semantic slash controls remained green.
- Repair `1215d00` extends only the public-metadata path-shape guard. Path/endpoint-shaped display metadata falls back to the safe model ID while semantic text such as `Vision / Chat` remains accepted.
- Focused discovery suite after repair: **46/46 PASS**.
- Provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota matrix: **344/344 PASS**.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST/import no-I/O, exact-scope audit, path/credential adversarial probes, and semantic safe controls: PASS.
- `origin/main` remains `1ae477f05e597c5027d22fdb2ca4f1496c070db7`; its post-main CI `33750907975` is terminal SUCCESS.
- Candidate `259beab...` and review packet `wo152-glm-final-review-004` are superseded for acceptance. The next independent review must pin the final documentation checkpoint commit after this note.

## GPT P2 opaque-secret/raw-endpoint repair checkpoint - 2026-09-03
- GPT adversarial review after `4f17d83412dde19d7d0968423cf1df1505799f35` proved additional display metadata could cross serialization: Basic-auth material, PEM/SSH key material, credential assignments, prefixed environment-secret assignments, host/port/path endpoints, and standalone hostname/IP/IPv6 endpoint values.
- Test checkpoints: `11d959c8d9cd3b5e37d15d9728a36ec774cfa7c9`, `3bccfcb31d0817f0543de02aba3bf4989af82c2b`, and `863a8d1f4c662873995b80afed48bff2e583cefe`.
- Consolidated detached RED at `863a8d1...`: **31 intended failures / 49 existing PASS**; semantic credential/network text controls remained PASS.
- Repair `5a7cadd9d0d21f4fbd6f24b9ff74c6b90e38db8e` adds bounded high-confidence secret/endpoint guards plus pure stdlib exact IP/hostname recognition; no I/O or provider authority was added.
- Final focused discovery suite: **80/80 PASS**.
- Fresh post-repair provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota matrix: **344/344 PASS**.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST/import no-I/O and exact-scope gates: PASS.
- Delta versus `origin/main@1ae477f05e597c5027d22fdb2ca4f1496c070db7` remains exactly WO152 + decoder + focused tests. Prior review tasks through `wo152-glm-final-review-005` are stale for acceptance because they pin earlier candidates.
- Next gate: freeze this checkpoint, push exact SHA, then require fresh exact-SHA GLM Goal Mode + `[a-loop]` review with P0=P1=P2=0 and exact-head hosted CI before merge.

## GPT final broad verification checkpoint - 2026-09-03
- Candidate before this documentation freeze: `9b763532ed74c24ac05bd1d5467ea03fa2d66b58`.
- Focused `tests/test_aipass_discovery.py`: **80/80 PASS**.
- Provider/config/store/service-auth/execution-authority/runtime/parallel/harness/job/quota matrix (12 files): **305/305 PASS**.
- Full repository suite: **2242 PASS / 4 SKIP / 2 FAIL**; the only failures are GPU particle tests requiring unavailable optional Pillow/OpenGL runtime components.
- Both GPU failures reproduce unchanged on detached `origin/main@1ae477f05e597c5027d22fdb2ca4f1496c070db7`; therefore they are classified BASELINE_ENVIRONMENT, not WO152 regressions.
- Strict UTF-8/U+FFFD, `compileall`, `git diff --check`, AST/import no-I/O, exact-scope audit, opaque-secret/path/endpoint adversarial probes, and semantic safe controls: PASS.
- `wo152-glm-final-review-005` reviewed stale candidate `4f17d834...` and returned CHANGES_REQUIRED only for Basic-auth display metadata; current repair lineage closes that P2 and supersedes review 005 for acceptance.
- Next gate: push the final documentation freeze, require fresh exact-SHA hosted CI and independent GLM Goal Mode + `[a-loop]` review with P0=P1=P2=0 before merge.

## GPT P2 factory-authority repair checkpoint — 2026-09-03
- Exact candidate `7ebe60db3cc468fd8395a86505fc3ffa4d30c9c1` still allowed direct construction of `AiPassDiscoveredModel` / `AiPassDiscoverySnapshot`; forged session/credential-shaped metadata could therefore bypass decoder guards and serialize through `to_dict()`.
- Deterministic reproducer serialized `name=session_id=sentinel-secret` from a directly constructed snapshot, violating the WO serialized-discovery boundary.
- RED before production repair: **2 failed / 80 passed**; only the two direct-constructor authority tests failed.
- Repair reuses the accepted `ProviderExecutionRequirement` factory-authority pattern: `@dataclass(..., init=False)` plus one private `_FACTORY_TOKEN`; only the internal pure decoder supplies the token. No sanitizer/validator was duplicated in `to_dict()`.
- Focused discovery suite after repair: **82/82 PASS**.
- Focused + provider/config/store/service-auth/execution/runtime/parallel/harness impact matrix: **447/447 PASS**.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, and AST forbidden-I/O import gate: PASS.
- `wo152-glm-final-review-006` is superseded for acceptance because it pins pre-repair `7ebe60db...`; any result from that task is stale evidence.
- Next safe action: commit/push this exact repair freeze, create a fresh detached exact-SHA review candidate, require hosted CI green and independent P0=P1=P2=0 before merge.

## GPT P2 glued-boundary repair checkpoint — 2026-09-03
- Post-constructor candidate `8edf7b69cbc7ab160fe3f66ee2cd989e5073d497` still serialized credential/path material when a word character was glued directly before an otherwise high-confidence credential or private-path shape.
- Reproducers included `a+ghp_<36>`, `x+sk-ant-<24>`, `x+AKIA<16>`, `x+npm_<32>`, a glued JWT-header shape, plus `cache/home/alice/.ssh/id_ed25519`, `endpoint/v1/models`, glued Windows-drive and UNC paths.
- RED before repair: **13 failed / 83 passed**; the dedicated semantic-near-neighbor control remained green.
- Repair adds a separate length-qualified embedded-credential detector and removes only the leading-word lookbehind from the existing high-confidence multi-segment path alternative. Existing semantic controls such as `highp_model`, `Rakia1`, `sketch-model`, `Vision / Chat`, `Home / Research`, and credential-themed prose remain accepted.
- Focused discovery suite after repair: **96/96 PASS**.
- Focused + provider/config/store/service-auth/execution/runtime/parallel/harness impact matrix: **461/461 PASS**.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, and AST forbidden-I/O import gate: PASS.
- Candidate `8edf7b69...` and detached review worktree `wo152-glm-final-review-007` are stale for acceptance; no review packet was published for that stale tree.
- Next safe action: commit/push this repair freeze, create a fresh detached exact-SHA review packet with new blob pins, require hosted CI green and independent P0=P1=P2=0 before merge.

## GPT P2 scale-dependent quota repair checkpoint — 2026-09-03
- Exact candidate `267c99081d685a4e16072a4b6a4534e8a119dd86` still accepted contradictory large quota tuples because `_consistent()` used `math.isclose(..., rel_tol=1e-9)`; allowed error therefore grew with quota magnitude.
- Deterministic reproducers included `limit=10^12, used=10^12-500, remaining=0`, `limit=10^15, used=10^15-100000, remaining=0`, and a 1,000,000-credit gap near the JSON safe-integer ceiling; all incorrectly projected `DISCOVERY_OK` before repair.
- RED `c28892b03ca79dc3411103b0f0e66f5b73f95161`: **3 failed / 96 passed**; each failure was the intended large-quota contradiction and included valid `fetchedAt` so the test reached quota consistency rather than failing earlier.
- Repair `a77a83a319732d11ffaa817db474a7fabb521d34` removes scale-dependent relative tolerance while preserving the existing fixed `abs_tol=1e-6` for ordinary floating arithmetic.
- Focused `tests/test_aipass_discovery.py`: **99/99 PASS**.
- Broad provider/config/store/service-auth/execution/runtime/parallel/harness/job/quota impact matrix: **634/634 PASS across 29 files**.
- Full repository suite: **2260 PASS / 5 SKIP / 2 FAIL**; both failures are unchanged optional GPU environment failures (Pillow/OpenGL) and reproduce on detached `origin/main@1ae477f05e597c5027d22fdb2ca4f1496c070db7`.
- Deterministic extra probes: valid fractional quota arithmetic stays OK; contradictory fractional/large shared and video quota fail closed; 1,000 randomized exact tuples plus randomized contradictory tuples across shared/video paths PASS.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST forbidden-I/O scan, runtime no-I/O monkeypatch probe, and exact three-file scope: PASS.
- Review packet `wo152-glm-final-review-008` is stale for acceptance because it pins pre-repair `267c990...`.
- Next safe action: commit/push this documentation freeze, create a fresh detached exact-SHA review with new raw blob pins, require exact-head hosted CI SUCCESS and independent GLM P0=P1=P2=0 before Ready/Merge.

## GPT P2 generic glued-credential repair checkpoint — 2026-09-03
- Exact pushed candidate `c2cfae0767a75885c82dcb68382b15b5d0b91a83` still serialized generic credential/auth material when a word character was glued before the sensitive key/scheme.
- Reproducers: `xsession_id=...`, `xauth=...`, `xcookie=...`, `xpassword=...`, `xBearer <16+>`, and `xBasic <base64>`; `xclient_secret=...` was already rejected by the existing environment-secret guard.
- RED before repair: **6 failed / 101 passed**; semantic controls remained green, including `Taxonomy`, `Authentication Model`, `Bearer Capacity`, `Basic Research`, `xBearer Capacity`, `xBasic Research`, `Session Analysis`, and `Token Budget`.
- Repair adds one length-qualified embedded generic credential/auth-scheme detector used only for display metadata. It does not broaden model-ID syntax, duplicate sanitization in `to_dict()`, or reject credential-themed prose without credential material.
- Focused `tests/test_aipass_discovery.py`: **107/107 PASS**.
- Broad provider/config/store/service-auth/execution/recovery/parallel/harness/job/quota matrix: **581/581 PASS** across the independently selected existing-file set.
- `compileall`, `git diff --check`, strict UTF-8/U+FFFD, AST forbidden-I/O import gate, runtime I/O poison, caller-input immutability, deterministic repeat-output, and exact three-file feature scope: PASS.
- Review packets through `wo152-glm-final-review-008` are stale for acceptance because they pin pre-repair candidates.
- Next safe action: commit/push this checkpoint, mint a fresh detached exact-SHA independent review with raw Git-blob pins, require exact-head hosted CI SUCCESS and GLM P0=P1=P2=0 before Ready/Merge.
