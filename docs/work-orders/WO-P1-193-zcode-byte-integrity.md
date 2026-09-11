# WO-P1-193 — ZCode exact-byte response integrity

Status: SOURCE_FROZEN / REVIEW_PENDING / GLM CHILD PREPARED
Date: 2026-09-11
Risk: R3 — cross-platform response evidence boundary
Owner: Poppy Javis / GPT-6 Astra / home macOS Codex
Claim: WO193-ASTRA-BYTE-INTEGRITY-001
Repository: aase7en/A-Wiki-Conductor
Base: 46f90b329d4991211f5c8a26406f3aca2162e9a7
Branch: codex/wo-p1-193-byte-integrity
Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo193
Parent evidence: Issue #233 comment 5631268320, findings 4 and 5.
Integrator acceptance/merge: existing GPT-5.6 Sol integrator; no self-merge.

## Goal

Preserve exactly the UTF-8 response bytes attested by the ZCode report when the helper writes redirected stdout on Windows and macOS. Avoid cp874 encoding failure and Windows newline translation without weakening evidence comparison or replay safety. Astra owns failure-model framing, RED-first bounded repair and freeze. GLM receives a separately isolated, test/evidence-only sustained validation packet after candidate freeze.

## Claim / non-overlap

Docs-only bootstrap first; product mutation only after committed/pushed WO and Issue #233 claim plus fresh state gate. Open PR scope audit on 2026-09-11 found no helper/test overlap. WO191 / PR263 owns continuation, WO192 / PR264 owns operational Worker recovery; neither is touched. WO190 / PR262 is a broad campaign, not blanket source authority; this child reserves only the exact response-output boundary. Wave10 must consume this child evidence rather than duplicate repair. No other Worker is activated or rebound.

Astra mutable paths:
- src/a_conductor/zcode_supervised_helper.py
- tests/test_zcode_stdout_boundary.py (new)
- docs/work-orders/WO-P1-193-zcode-byte-integrity.md
- docs/prompts/GLM-WO193-BYTE-INTEGRITY-MARATHON.md (new)
- docs/reviews/WO-P1-193-byte-integrity-design.md (new)
- ignored runs/WO-P1-193/

Forbidden: all other source/tests; global CURRENT-WORK.md, handoff.md, COLLAB.md, PROJECT-PLAN.md and DEFECT_LESSONS.md (integrator fold only); A-Wiki writes; secrets/private Drive; live providers, ZCode configuration, Worker/process operations; existing GLM campaign files; schema/review/scheduler/admission/lease semantics; merge/release. The active WO plus Issue #233 is the scope-owned continuity handoff pending single-writer global projection fold; do not create concurrent hotspot edits.

## Failure model / invariants

- Provider text is data. Emit its exact UTF-8 bytes, including intentional CR, LF, CRLF, BOM characters and Unicode composition; no stripping, replacement, newline or Unicode normalization.
- Hash report and output refer to the same bytes. Never fix mismatch by weakening verification or rewriting historical failed evidence.
- Existing response budget remains upstream authority. No unbounded buffering, new provider invocation or retries.
- Output transport errors cannot mean successful response delivery. Retain truthful child-exit evidence; helper failure is separate from child completion. No replay of completed provider work.
- Known child exit precedes output; successful write/flush precedes report, which precedes result. Existing report-before-result semantics remain; publication now waits for complete output.
- Missing binary output capability fails explicitly; no ambient text encoding fallback.
- Partial writes must either complete the remaining byte suffix or fail explicitly; do not duplicate an already-written prefix.

## Acceptance / verification

1. RED proves actual helper entry-point output corruption under cp874 and forced CRLF translation using a synthetic completed protocol turn; no provider credentials.
2. GREEN preserves bytes for ASCII, Thai, CJK, emoji, mixed newline, empty and boundary-budget payloads.
3. Bounded write failure/short-write tests preserve failure truth and do not rerun the provider.
4. Focused + related ZCode/supervised suites pass; real local helper/child E2E remains green. Real Windows evidence is separately named, never inferred from simulated TextIOWrapper behavior.
5. Scope/diff/UTF-8 checks pass, candidate clean and pushed, SHA-bound independent review requested, no merge.
6. GLM packet re-read, hash pinned, exact branch/worktree/results/scope preconditions verified before human pointer delivery. Estimated 10–20h is a useful-work envelope, not minimum busy time or a guarantee.

Reference patterns: tests/test_zcode_helper_execution.py, tests/test_zcode_real_helper_e2e.py, existing supervised bounded output handling. Reuse existing WO/checkpoint/Git/assurance protocol; no new scheduler or claim mechanism.

Verify: python -m pytest -q tests/test_zcode_stdout_boundary.py; then related tests/test_zcode*.py and supervised execution/helper tests. Record exact invocation, SHA, host, counts and failures in runs/WO-P1-193. Independent reviewer is not candidate author. New findings outside this scope are reported, not silently repaired.

## Checkpoint

- Bootstrap: clean isolated worktree at base; exact source/test PR overlap audit passed. Preparing public claim before any product/test mutation. Source eligibility remains NO until claim push and recheck.


## Frozen source / child validation handoff

Source candidate: 09d3489296a97c1a16d89b0c6b29edf11b7ffa08.
Claim evidence: https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5631593477.
Astra source lane is FROZEN: no concurrent writes while GLM validates it.
Design and evidence: docs/reviews/WO-P1-193-byte-integrity-design.md.
GLM packet: docs/prompts/GLM-WO193-BYTE-INTEGRITY-MARATHON.md.

GLM child WO193-GLM-BYTE-VALIDATION-001 is PREPARED, not running. A fresh ZCode session
must pass live capacity/owner/branch/hash gates and publish its child claim before test
mutation. Branch codex/wo-p1-193-glm-byte-validation, Windows worktree
A:/GitHub/_worktrees/A-Wiki-Conductor-wo193-glm-byte-validation. User relays one pointer;
integrator reads results directly. Scope is new test_wo193_byte_integrity_campaign.py,
new synthetic fixtures under tests/fixtures/wo193_byte_integrity/, new
scripts/wo193_byte_integrity_probe.py, new docs/reviews/WO-P1-193-glm-byte-integrity-evidence.md,
and append-only child checkpoints in THIS WO on the child branch. The exact packet
is the bounded child contract. All source and Astra tests are immutable to GLM.

- RED: 2 intended codec/newline failures, then 5 publication failures.
- GREEN: focused15; related234 with16 Windows-only skips; canonical-interpreter coordinator13.
- Independent Sol source analysis found the publication bug but hit usage limit before
  finishing review. INDEPENDENT_REVIEW=INCOMPLETE, never PASS.
- Real-Windows synthetic verification and exact-head hosted CI remain separate evidence.
- No merge; acceptance and global CURRENT-WORK/handoff/COLLAB/DEFECT_LESSONS fold remain
  with existing single-writer integrator. This WO + Issue233 is the durable scoped handoff.
- No completed execution may be replayed to repair output evidence. Existing failed
  historical artifacts are preserved. Native Mac proof uses only synthetic children.
