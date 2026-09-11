# WO193 GLM byte-integrity validation — portable evidence handback

Claim: `WO193-GLM-BYTE-VALIDATION-001` (child of WO-P1-193; packet `docs/prompts/GLM-WO193-BYTE-INTEGRITY-MARATHON.md`, SHA-256 `212eae6e6a93f9fd7d6e74e5f247e69b9cbc63a205e9e18646453a4da056c83a`)

- Repository `aase7en/A-Wiki-Conductor`, branch `codex/wo-p1-193-glm-byte-validation`
- Delivery commit (startup pointer, == Issue #233 handoff): `a862b946b89a76f43e54ee852bddbd1c8a1bc18d`
- Frozen source commit: `f1dbb65212a737f7a4f88dcd88bdb713f190ad51` — verified: `src/a_conductor/zcode_supervised_helper.py` SHA-256 `38f9fb19...` MATCH; `tests/test_zcode_stdout_boundary.py` `f0d3722b...` MATCH
- Host: DESKTOP-7IB57R4, Windows 11 x64, Python 3.11.15 (`python` = hermes venv; `sys._base_executable` == `sys.executable`, so the packet's Mac interpreter caveat does not apply here)
- Status: **COMPLETE_FOR_REVIEW** with one confirmed P3 finding (F1) and one environment note (ENV-1); exact child SHA recorded in `runs/WO-P1-193/glm/result.json` and the child PR

## Verdict on the frozen repair (f1dbb65)

**CONFIRMED on real Windows, synthetic children only**: the repaired helper preserves response bytes byte-for-byte through hostile host configurations and publishes completion strictly after output flush, in report-before-result order, with exactly one spawn/one send per execution and no replay on any failure path. The publication authority boundary (`result.json` presence consumed as completion) held in every fault scenario tested. One typed-diagnostics contract gap (F1) and one host-environment constraint (ENV-1) are recorded below; neither breaks the authority invariants.

## Program dispositions (B00–B10)

| Program | Disposition | Evidence |
|---|---|---|
| B00 consume prior evidence | DONE | Astra focused15 re-run on this host: `15 passed in 4.58s` (startup). Astra Mac native-subprocess cases re-proven natively on Windows by B04 below (Astra's own E2E parametrization also runs on Windows — 15/15 includes it). Windows preflight artifacts consumed (`runs/WO-P1-193/glm/windows-preflight*.txt`). Coverage classification table below. |
| B01 call-path archaeology | DONE | Authority map (below) with exact symbols/lines at f1dbb65. |
| B02 corpus + independent oracle | DONE | `tests/fixtures/wo193_byte_integrity/corpus.json` (5.8 KiB; hex+sha256+length precomputed at fixture creation) + `test_b02_*` (oracle self-agreement, anti-vacuity negatives incl. NFC-collapse and CRLF-transform proofs, helper round-trip for every case under cp874+forced-CRLF wrapper). |
| B03 newline/BOM/control matrix | DONE | `test_b03_*`: lone-CR, trailing-none, consecutive blanks, whitespace-only, NUL-middle, BOM-interior through cp874/cp1252 wrappers with `newline=None` and forced CRLF. Distinct inputs from Astra's six wrapper cases (no duplication). Wrapper cases are labelled simulated; native OS proof is B04. |
| B04 real Windows E2E | DONE | `test_b04_*` (9 tests, 33.7 s): REAL helper subprocess + synthetic fake app-server; production-shaped binary file redirect (`open("ab", buffering=0)` — exactly `owned_process.py:238-239`); hostile `PYTHONIOENCODING=cp874`; corpus byte equality + report attestation; Unicode+spaces Thai parent dir; one-spawn/one-send exact identity (prompt bytes == packet; model binding intact); known nonzero child exit (3) retained truthfully in result while bytes still delivered; EXIT_PENDING (hang after turn) → 30 s bounded wait → EXIT_PENDING report only, no stdout bytes, no result. |
| B05 publication fault injection | DONE | `test_b05_*`: report-write failure after output (result absent, bytes remain as partial evidence, no replay); result-write failure after report (report present + attests flushed bytes, result absent); deterministic collector barrier (flush event + report-write probe + watcher thread: result never visible before report publication); no-second-send on publication failure. Includes labeled F1 characterization. |
| B06 budgets/segmentation | DONE | `test_b06_*`: budget counted in UTF-8 bytes at exact limit / +1 byte for ASCII, Thai (9 B), supplementary emoji (4 B), combining-mark boundary; segmentation invariance (whole vs per-char vs CRLF-split vs grapheme-split deltas → identical bytes+hash); cap validation above `ZCODE_MAX_RESPONSE_BYTES` fails before spawn. Fixed seeds; no random fuzz padding. |
| B07 durable collection / no-replay | DONE | `test_b07_*`: real helper run with unusable artifact dir fails typed `IDENTITY_WRITE_FAILED` after spawn, before any send → collector (`SupervisedExecutionService` over sacrificial `SQLiteExecutionStore`) sees recovery-required, never RESULT_AVAILABLE; successful path: RESULT_AVAILABLE, `collect` consumes exactly once under version CAS (second collect raises `EXECUTION_VERSION_CONFLICT`); no child ever spawned by collect. |
| B08 portable probe | DONE | `scripts/wo193_byte_integrity_probe.py` (stdlib + pinned repo module for runtime-model serialization only): 4 cases (cp874-Thai, cp874-mixed-newlines, utf8-emoji, cp1252-nonzero-exit) → `PROBE_OK`, exit 0; refuses nonempty output dir (exit 2); stages under system TEMP and copies evidence back with read-back verification (ENV-1 mitigation); manifest at `runs/WO-P1-193/glm/probe-final/manifest.json`. |
| B09 test economy | DONE | 74 campaign tests ≈ 35 s; single parametrized matrices with stable IDs; helpers imported from existing test modules (`_invoke`, `_runtime_metadata_env`, `ScriptedTransport`, `make_record`, e2e fake pattern) — zero edits to existing tests; mapping table below. |
| B10 triage/freeze | DONE | This document + `runs/WO-P1-193/glm/result.{json,md}` + child PR (stacked on the Astra branch, draft, no merge). |

## B01 authority map (source references at f1dbb65)

```
ZCodeProtocolDriver.run_turn (zcode_protocol.py:242, deltas accumulated :379-386)
  → response_text + bytes_received (sum of per-delta len(UTF-8); == len(response_text.encode) by construction)
  → budget raised per delta: received > max → RESPONSE_BUDGET_EXCEEDED (:381)
helper.main natural shutdown (zcode_supervised_helper.py:537-543)
  → unknown exit → EXIT_PENDING report ONLY, _fail("EXIT_PENDING") (:565-583)
  → known exit → payload = response_text.encode("utf-8"); sys.stdout.buffer.write, exact int count,
    flush (:594-604); short/invalid → RESPONSE_OUTPUT_INCOMPLETE; write/flush error → RESPONSE_OUTPUT_FAILED
  → publication order: report _write_atomic (:617-618) THEN result _write_atomic (:627)
  → [F1] section-7 _write_atomic calls are unguarded → OSError escapes main untyped
production redirect: owned_process.py:238-239 stdout/stderr open("ab", buffering=0) — binary, byte-preserving
collector: supervised_execution.py:554-560 result_path.exists() → RESULT_AVAILABLE (completion authority);
  collect :654-661 version CAS + read_supervised_child_result (schema == helper result.json: helper :619-626
  vs supervised_child.py:26-37 — exact field match)
coordinator: supervised_run_coordinator.py maps {run}/stdout.log etc. (:128-139)
```

Consumer-side verification limits (documented, per packet §6/§B01): no consumer re-verifies report `response_sha256` against durable stdout bytes at collect time; the hash is attestation for downstream auditors. A post-hoc corrupted `stdout.log` would not be detected by the collector — consistent with the design's stated scope ("does not add artifact tamper attestation to every consumer").

## B00 coverage classification

| Class | Items |
|---|---|
| ALREADY_PROVEN (Astra, f1dbb65/mac + focused15 Windows) | wrapper bypass for 6 codec/newline combos; 5 output fault modes typed + no result; 3 real-helper subprocess encodings; publication-order probe |
| ALREADY_PROVEN (this campaign, native Windows) | production binary file redirect leg; Unicode path; nonzero-exit retention; EXIT_PENDING; one-spawn/one-send identity; collector contract; budget byte semantics; segmentation invariance |
| NEW_GAP→CONFIRMED_DEFECT | F1 (below) |
| UNTESTED (out of this packet) | fsync/power-loss durability; tamper-attestation at every consumer; full Zero-Relay lifecycle; real provider traffic |
| OUT_OF_SCOPE | ZRA-2/3 lanes, WO194 launcher forensics, WO192 runtime deployment |

## Findings

**F1 — CONFIRMED_DEFECT (P3, diagnostics contract; authority invariants hold; PRE-EXISTING on base 46f90b3)**
- Where: `src/a_conductor/zcode_supervised_helper.py:606-627` — the report/result `_write_atomic` calls in the publication section have no typed handler; an OSError escapes `helper.main` as an untyped traceback. This contradicts the in-code contract comment at :591-592 ("typed codes go to stderr in every failure path").
- Invariants that still hold (proven): result never published on artifact-write failure; report-before-result order preserved on the success path; no provider replay; output bytes remain as partial evidence.
- Minimal repro: monkeypatch `helper._write_atomic` to raise on `report.json` (or `result.json`); call `helper.main(...)` in-process → raw `OSError` propagates (tests `test_b05_report_write_failure_after_output_leaves_no_result`, `test_b05_result_write_failure_keeps_report_without_result` characterize this exactly).
- Old main also fails: YES — base `46f90b3` has the same unguarded `_write_atomic` sites (base :582/:601/:610). Not a regression from the frozen repair.
- Suggested owner/shape: Astra/integrator, bounded child of WO193-A: wrap section-7 writes in a typed `RESPONSE_PUBLICATION_FAILED` fail-closed path (result still absent); 2 focused tests; keep replay semantics unchanged.
- Severity rationale: untyped tracebacks impede operator diagnostics and the typed-contract claim, but no completion authority can leak.

**ENV-1 — environment constraint (NOT a WO193 source defect; matches WO192 packaging finding)**
- Spawned Python children whose script lives under the NTFS-compressed `A:/GitHub/_worktrees/.../runs/` path die at startup (`CHILD_EXITED`; helper typed fail) — identical mechanism class to the WO192 `ERROR_ACCESS_DENIED` compressed-`runs` finding. The probe mitigates by staging runs under system TEMP and copying evidence back with byte-identical read-back verification (`output_artifacts_readable` check). pytest tmp_path cases are unaffected.

## Verification record (all on this host, interpreter 3.11.15)

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_zcode_stdout_boundary.py` | 15 passed (3.36 s) |
| `python -m pytest -q tests/test_wo193_byte_integrity_campaign.py` | 74 passed (34.2 s; run twice consecutively — 74/74 both) |
| `python -m pytest -q tests/test_zcode_helper_execution.py tests/test_zcode_real_helper_e2e.py tests/test_zcode_production_assembly.py tests/test_zcode_authority_bound_assembly.py` | 70 passed (53.1 s) |
| `python -m pytest -q tests/test_supervised_execution.py tests/test_supervised_child.py tests/test_supervised_run_coordinator.py` | 41 passed (3.2 s) |
| `python scripts/wo193_byte_integrity_probe.py --output-dir runs/WO-P1-193/glm/probe-final` | 4/4 PASS, `PROBE_OK`, exit 0 |
| `git diff --check` | clean |

## B09 test → invariant → defect-class map (campaign file)

| Tests | Invariant | Defect class guarded |
|---|---|---|
| `test_b02_corpus_oracle_self_agreement`, `test_b02_negative_controls_are_real_negatives` | oracle fixture is self-consistent and discriminative (NFC-collapse, CRLF transform, 1-byte diffs) | vacuous/normalizing oracle |
| `test_b02_helper_main_preserves_corpus_bytes_under_hostile_wrapper` | helper output bytes == oracle under cp874 + forced-CRLF wrapper | codec/newline corruption (the two original Windows defects) |
| `test_b03_newline_and_control_shapes_preserved` | lone CR / trailing-none / blanks / whitespace / NUL / interior BOM preserved | text-wrapper translation |
| `test_b04_*` (9) | real-subprocess byte identity through production binary redirect, Unicode path, exact identity, nonzero exit retained, EXIT_PENDING never fabricates result | locale/newline corruption at OS boundary; premature completion |
| `test_b05_*` (4) | result absent at every publication failure point; barrier ordering; no replay | premature result visibility (the second original defect) |
| `test_b06_*` (13) | budget counts UTF-8 bytes, exact boundaries; segmentation invariance | budget-by-character / reserialization |
| `test_b07_*` (2) | collector never promotes failed publication; collect is CAS-fenced once | completion authority leak; double-collect/replay |

Mechanical duplicates removed during B09: none of Astra's six wrapper inputs, five fault modes, or three real-helper encodings are re-encoded as new tests; the campaign imports Astra's `_invoke`/`_runtime_metadata_env` and the e2e fake *pattern* (self-contained config-driven copy, no edit to the existing module).

## Reproduce

From the child branch worktree (Windows or Mac):

```text
python -m pytest -q tests/test_wo193_byte_integrity_campaign.py
python scripts/wo193_byte_integrity_probe.py --output-dir <empty-dir>
```

Limits: synthetic children only; no fsync/power-loss proof; no tamper attestation at consumers; independent exact-SHA review + hosted CI remain with the integrator (INDEPENDENT_REVIEW by this author = NOT_PERFORMED for its own tests).
