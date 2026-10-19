# WO-P1-684: BWA Core Input Validation Repair

Identity schema: GITHUB_ISSUE_V1
Issue: #684
Status: DOCS_BOOTSTRAP_ONLY / SOURCE_GATE_CLOSED / ACCEPTANCE_UNMET
Parent: WO-P1-457 / BWA-1A, private extension PR #1
Bootstrap risk: R0, capture of root-adjudicated scope only
Future source risk: R3 / CROSS_REPO
Owner: root GPT integrator; source author NOT ASSIGNED by this packet
SAFE_TO_MUTATE_BWA_REPAIR=NO

## 1. Authority And Exact Binding

- Authority repository: `aase7en/A-Wiki-Conductor`, control-plane/contract authority.
- Authority snapshot: `9cd58c787a2acfbb290e380543eaac2e5ac6e2e8` (`9cd58c7`).
- Docs worktree: `A:\GitHub\_worktrees\AWC-wo684-bwa-core-repair`.
- Docs branch: `docs/wo684-bwa-core-repair`; initial HEAD equals authority snapshot; clean before bootstrap.
- Bootstrap claim: `WO-P1-684-DOCS-BOOTSTRAP-001`, comment `6271911602` on the driving issue.
- Exact bootstrap mutable scope: ONLY new `docs/work-orders/WO-P1-684-bwa-core-input-validation-repair.md`. This is not a source claim.
- Execution repository: existing private `aase7en/sunday-family-extension`, TypeScript MV3 core and Python 3.11 stdlib host. Repository/visibility/language were authorized under parent comment `5763751554`; no new repository decision is needed.
- Frozen old candidate: `ef0c05f1b647533dc56ec888746d0145bfea5cdc`, compared with base `921d4c34d24928bfa5f23f8a1a5623b734823571`.
- Extension current main: `9f9e516797842ab5f33dca50ddc6c5a4b2ac7993`, governance-pointer-only drift, not a source replacement or repaired candidate.
- Retained frozen review worktree: `A:\GitHub\_archive\worktrees\wo457\sunday-family-extension-review-wo457-ef0c05f`. Retained author/review worktrees and their candidate stay unchanged. No checkout, switch, reset, clean, rebase, or source repair there.
- Future repair tuple: root MUST select and claim a NEW clean isolated execution worktree/branch, exact starting HEAD and four-file scope AFTER reviewing this packet. Neither a source branch nor a source lease is granted here. Reconcile pointer-only main drift explicitly when binding that tuple; do not silently update the frozen comparison set.

Root source framing is the driving issue body read on 2026-10-19: four independently reproduced P2 input-validation defects; reuse accepted BWA0 vocabulary; preserve valid vectors; bounded offline repair only; freeze and independently review a new exact SHA; no merge while specifically required GLM acceptance is unmet. Actual state/ownership and user safety constraints outrank historical summaries.

## 2. Goal And Reuse

Repair the existing offline helper entry points so hostile or malformed JSON/state cannot escape typed failure handling or produce a positive binding/resend/effect decision before validation. Preserve all valid pinned BWA0 vectors and existing control-plane authority.

Classification: REUSE accepted BWA0 schema/scalar/version vocabulary and existing tests; EXTEND the two current validators and two focused test files only. No replacement protocol, parallel status system, credential subsystem, or new coordination primitive.

References:

- Accepted authority `docs/contracts/browser-chat-resume-adapter-v1.md` and matching schema at AWC `9cd58c7`; sections 5, 8, 12 and 13 define binding, replay, typed version rejection and sanitation.
- Execution `vendor/bwa0/PIN.md` and vendored contract/schema remain immutable references; canonical clean-filter blobs equal the authority snapshot: contract `cfd12aeff49b792c0304e301a97ba2a8a4cd72e6`, schema `0a4b0d9bc75384f0e48963a678e7f59241d1cb20`.
- Raw Windows CRLF bytes and Git canonical LF blobs are distinct pin domains; preserve existing raw SHA/size checks and clean-filter behavior. Do not repair fixture failures by rewriting vendor/PIN/vectors.
- Original independent GPT ADVISORY report: `A:\GitHub\_worktrees\AWC-wo683-config-root\runs\WO-P1-457\offline-advisory-20261019\result.md`, SHA256 `8a7f2f5d8179c494f9342b02572075bf30e123156d3126254557a4c8ed39bf26`. Preserve byte-unchanged. Associated reviewer probes are reference evidence, not source authorization or a GLM verdict.
- Binding delivery policy: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`; no downgrade from R3 because the original 18 Python / 11 Node suites passed.

## 3. Exact Future Mutable Scope

ONLY these existing paths in the newly claimed private execution worktree may be proposed for source/test repair:

1. `src/host/bwa_host.py`
2. `src/extension/bwa_cycle.ts`
3. `tests/host/test_bwa_host.py`
4. `tests/extension/bwa_cycle.test.ts`

No other source/test path or new source file is admitted. AWC remains authority/evidence only. Every future source task must rerun entry, actual-state, collision/claim, exact tuple and failure-model gates before its first edit. The source author will be a different newly assigned task, not this docs bootstrap lane.

## 4. Root-Adjudicated Failure Model

| Finding | Observed offline failure at frozen candidate | Required bounded repair |
| --- | --- | --- |
| F1 / P2 | Python array uniqueness uses `set(value)` before item typing; nested object/list values raise TypeError through public validation. | Validate item types before uniqueness; return existing typed invalid through validator and consuming wake/response gates. |
| F2 / P2 | TypeScript untrusted lookup names `constructor`, `__proto__`, `toString` resolve inherited map entries and throw; delivery lookup can return functions/objects. | Require own keys or prototype-free maps for every affected untrusted lookup; reject unknown keys/states typed, with JSON.parse-based tests. |
| F3 / P2 | Empty binding IDs/generation zero yield BINDING_MATCH; malformed pending wake string yields RESEND_AUTHORIZED; Python invalid receipt container raises. | Reuse pinned identity/generation scalar checks and validate receipt/pending inputs before a positive match/resend; return existing invalid/unknown outcomes, never infer truth from malformed state. |
| F4 / P2 | Actual full-envelope path returns INVALID for major 2 while isolated classifier returns VERSION_UNSUPPORTED. | Enforce bounded version precedence at the real envelope boundary, retaining typed unsupported-major rejection and closed-schema rejection. |

These are reproducible helper-core defects, not evidence of live exploitation. DOM/browser/state inputs are untrusted; mere strings, matching malformed records, capability, or a caller-supplied outcome never add authority. Fix validation order and typed propagation, not task semantics. Rejection must not mutate consumed/seen state or create a second effect. Valid duplicate/receipt/ambiguity behavior must remain unchanged.

## 5. RED-First Acceptance Matrix

Run the supported suites first to establish the frozen baseline, then add failing full-entry tests in the two existing focused test files BEFORE production edits. Capture truthful RED outcomes, including escaped exceptions and wrong positive outcomes; do not label fixture/import failures as behavioral RED.

1. F1: exercise every legal array field with object, nested array, null, boolean and numeric elements, mixed arrays, duplicates, non-array containers and oversize bounds. Test public validator plus WakeEffectGate.deliver and ResponseEffectDedupe.apply with their applicable fields. All malformed cases return typed invalid without raising or consuming IDs; a later valid message with the same ID still follows the valid first-effect rule.
2. F2: build extra own keys using JSON.parse for inherited names, not only object literals. Check unknown property/message/delivery names including constructor, __proto__ and toString; no inherited values, exceptions or non-string results. Preserve valid own-field messages and valid delivery outcomes.
3. F3: test missing/empty/wrong-type/invalid-grammar binding IDs; generation zero, negative, fractional, boolean, out-of-range and nonfinite in-memory values where applicable. Check valid stale/ahead/mismatch records remain fail-closed. Test wrong-type receipt containers, pending null/non-object/missing ID/wrong-type or malformed wake ID. Validate all required inputs before a positive binding/resend/effect; retain receipted-wake rejection and valid unreceipted reconciled control. Do not require schema fields absent from the accepted helper interface or introduce a new receipt authority.
4. F4: test full envelopes, not merely classifiers: valid v1; higher-minor inside known vocabulary; different major; malformed/partial/prefixed versions; unknown additive fields. Apply the whole-envelope type/size gate before version handling, so oversized remains OVERSIZED and malformed versions remain INVALID. Different-major rejection must remain typed UNSUPPORTED through applicable consuming entry paths; it never authorizes fallback. Pin precedence and preserve valid v1 closedness.
5. After GREEN, rerun all committed valid vectors and focused suites plus an adversarial batch for F1-F4, unknown/fake fields, credential-shaped strings and arrays, local pointer acceptance, URL/cookie rejection, duplicate wake/response and restart/ambiguity controls. Rejected input produces no second effect; test outcomes must not claim cross-process persistence or live browser behavior.

Acceptable repair evidence requires all four findings closed at public entry points; no regression in valid vectors; no added authority/status vocabulary; exact four-file scope; unchanged vendor/PIN/vectors/package/manifest; no new dependencies; clean diff/encoding/pin checks; frozen repaired SHA and independent post-repair exact-SHA review. Tests verify a narrow offline helper core only, NOT a complete Native Messaging milestone, persistent wake-arm implementation, real restart guarantee or production readiness certificate.

## 6. Verification And Evidence

Future source verification runs ONLY in the newly bound repair worktree, never the retained frozen trees. No npm install is necessary; Node 24 built-in type stripping and Python 3.11 stdlib are the supported test routes. Python3.11.15 / Node24.15.0 were independently observed during the advisory review; re-verify versions in the source lane.

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python --version
node --version
npm run test:host
npm run test:extension
git diff --check
git status --short --untracked-files=all
```

Capture individual exit codes; do not hide an earlier failure with a later command's success. Record RED, GREEN, adversarial outputs, exact input/expected outcomes, unchanged pin hashes, changed-path inventory, repo/worktree/branch/base/head and reviewer identity/provenance under existing ignored authority `runs/WO-P1-684/`. Any synthetic HOME/USERPROFILE or test-cache state must use temporary fixtures, not true user-home state. Evidence is not a second task/status/receipt store.

Bootstrap-only verification (AWC docs worktree):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m pytest tests/test_work_order_identity.py -q -p no:cacheprovider --basetemp '<fresh temporary directory>'
git diff --check
git diff --name-only
git ls-files --others --exclude-standard
```

Require 33 identity tests green with the new untracked WO included by the existing corpus collector, exactly one identity declaration matching the filename, strict UTF-8/no replacement characters, no trailing whitespace, and exactly this new WO as the only changed/untracked non-ignored file. Since new files are untracked, ordinary git diff alone is insufficient; inspect the added-file diff or explicit content checks too. Rehash the earlier report and require its original SHA256 unchanged. No staging/commit is authorized by these commands.

## 7. Routing, Ownership And Stop Gates

- Bootstrap is R0 docs capture only. Future source work remains R3 CROSS_REPO and `SAFE_TO_MUTATE_BWA_REPAIR=NO` until root packet review, fresh isolated execution tuple, non-overlap proof and exact four-file source claim.
- Current GLM route: `GLM_OFFLOAD=BLOCKED:SECRET_SOURCE_UNAVAILABLE`; approved env-only credential is absent. Do not search disk, secret stores, accounts or keychains, change global/project settings, probe credentials, or call providers to bypass it. GPT fallback may implement/advise only after source authorization.
- Original specifically-required independent GLM-5.3 MAX acceptance remains UNMET. GPT fallback results are not GLM identity or a GLM PASS. NO MERGE of the original or repaired candidate while that gate remains unmet; only root can adjudicate any later authority change.
- Independent post-repair reviewer must differ from the source author and review an immutable exact repaired SHA. Source edits after review invalidate that SHA's verdict and require focused re-review. Root retains final acceptance/merge authority.
- Two bounded repair cycles maximum before root-cause/adjudication reset if the same material failure persists; no blind retry or scope expansion.
- PR550 retains shared continuity reservation. CURRENT-WORK.md, handoff.md, COLLAB.md, DEFECT_LESSONS.md, all PR550 paths and WO683 are forbidden to this lane. Use this WO, its driving issue and ignored runs evidence; blocked shared continuity is not permission to overwrite it.
- No task/protocol/schema/status/store/scheduler/provider/claim/lease/retry/completion authority may be added. No vendor/PIN/vectors/package/manifest changes or new source files. No framing, Native Messaging host registration, Origin transport, service-worker, browser/DOM, persistent wake-arm or doctor integration in this repair.
- No live endpoints, provider calls, cookies/accounts/session/share URLs/trust credentials, global settings, true-user-home inspection or runtime changes. No commits, pushes, PRs, claims or issue posts by the bootstrap author. Future publication requires separate root authorization.

## 8. Checkpoint And Next Safe Action

- 2026-10-19: root opened the driving issue and docs-only claim after independently reproduced advisory findings F1-F4; source gate remains closed. Bootstrap writer verified the clean authority tuple, read root framing and captured this packet only. Earlier advisory report remains immutable; bootstrap verification results are returned separately, not pre-claimed here.
- NEXT_SAFE_ACTION: root reviews this packet and rechecks actual ownership/WIP, then may bind a different source-author task to a newly isolated private execution branch/worktree and exact four-file claim. Until then perform no BWA repair source mutation. After a repaired freeze, independent exact-SHA review and still-required GLM acceptance remain separate gates; no new acceptance claim is made by this packet.
