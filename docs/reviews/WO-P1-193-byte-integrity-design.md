# WO193 — Byte integrity and completion publication design

Status: SOURCE CANDIDATE / INDEPENDENT REVIEW PENDING
Owner: Poppy Javis / GPT-6 Astra
Source candidate: f1dbb65212a737f7a4f88dcd88bdb713f190ad51
Base: 46f90b329d4991211f5c8a26406f3aca2162e9a7

## The difficult boundary

Issue #233 comment 5631268320 records two Windows defects: cp874 cannot encode the
completed response, and UTF-8 text stdout still translates LF to CRLF. The report hashes
UTF-8 response bytes; its hash can therefore diverge from durable stdout even after a
successful provider turn. This is an execution-evidence boundary, not presentation.

Source tracing found a second condition that a codec-only fix would miss. The helper
published result.json before writing output. SupervisedExecutionService.inspect treats
result presence as RESULT_AVAILABLE, collect interprets the child's exit code, and
SupervisedRunCoordinator maps collected artifacts. A helper failure on stderr after
publication therefore cannot reliably revoke success. Partial output could become
available to the caller alongside a successful child result.

Read-only Sol analysis identified that publication hazard; it stopped on usage limit
before a complete exact-SHA review. It is finding evidence, not an independent PASS.

## Chosen change

Reuse the existing helper, binary stdout handle, report schema and atomic result writer.
After a known terminal child exit: encode UTF-8, perform one bounded-payload binary
write, demand an exact integer count, flush, publish report, then publish result.
Short/invalid count returns RESPONSE_OUTPUT_INCOMPLETE. Missing binary handle, write or
flush error returns RESPONSE_OUTPUT_FAILED. No retry and no text/locale fallback.

The helper does not promote child completion to response delivery until bytes were
written and flushed. Output failure leaves child identity and partial output available
for reconciliation, but publishes no new terminal report/result. EXIT_PENDING still
uses its pre-existing nonterminal report and never emits a successful result.

| Event | Output | Report/result | Permitted interpretation |
|---|---|---|---|
| Known child exit + write/flush success | Exact UTF-8 | report then result | Collect with original child exit code |
| Short write or invalid count | Possibly prefix | Neither newly published | Incomplete delivery; reconcile, no replay |
| Write/flush failure | Absent/partial/full but unconfirmed | Neither newly published | Delivery failed; reconcile |
| Child exit unknown | No response emission | EXIT_PENDING report only | Recovery required |
| Report write fails after output | Bytes may exist | No terminal result | Incomplete publication; no replay |
| Result write fails after report | Bytes/report may exist | No terminal result | Incomplete publication; no replay |

Exact byte identity preserves intentional newline mixtures, whitespace, NUL, BOM and
Unicode composition. No normalization is added to a consumer/hash verifier. Credential
routing, filesystem confinement, provider admission, process ownership and protocol
budget are unchanged. Source mutation is one file; source diff against base is small.

## Evidence

- First RED 38501ba5326fa6ada577b610d8901b888506ef24: two actual-main tests fail with
  cp874 UnicodeEncodeError and CRLF expansion. The fixture initially had an invalid
  execution ID; that setup failure was corrected before accepting RED evidence.
- Publication RED 7dd992adf59eb2059cbaba7bd9a97598d08c6389: five fault cases prove
  premature result visibility even after the intermediate binary-only output fix.
- Final source f1dbb65212a737f7a4f88dcd88bdb713f190ad51: focused 15 PASS including
  three native macOS helper+synthetic-child subprocess cases (ascii/cp874/utf-8).
- Related ZCode/supervised matrix: 234 PASS / 16 Windows-only skips.
- Coordinator: 13 PASS using the canonical Python 3.12 executable.
- Initial default-interpreter coordinator run: five EXECUTABLE_NOT_ALLOWED failures;
  same failures reproduced on unchanged main. Fixture mixes sys.executable basename
  with _base_executable. No source/test allowlist was changed to suppress this.
- Evidence: ignored runs/WO-P1-193/red.txt, red-output-publication.txt,
  green-focused.txt, green-related.txt, coordinator-canonical-interpreter.txt.

Only synthetic data and subprocesses were used. Native Windows results, full hosted CI
and independent exact-SHA review must be recorded separately before final acceptance.

## Limits and integrator decisions

Flush is not fsync or power-loss durability. This repair does not add consumer-side
raw artifact attestation, alter durable lifecycle schemas, or validate arbitrary external
artifact tampering. Existing launch/run-directory identity prevents normal reuse; manual
reinvocation into a foreign/stale result directory is outside the declared execution
contract and must not be used as a replay workaround. Report any uncovered lifecycle
hole with a minimized reproducer rather than growing this helper scope silently.

The existing caller may classify absence of result as recovery rather than a terminal
failed-delivery record; no second lifecycle is created here. The GLM campaign explicitly
challenges these collector/restart semantics through sacrificial stores.

Global continuity and defect-memory fold is delegated to the existing single-writer
integrator. Suggested defect lesson: terminal result presence is an authority-bearing
publication event; flush exact response bytes before publishing completion. Codec repair
without publication-order proof is insufficient.

ZRA dependency observation: PR258 accepted Phase A, while Issue233 comment5631356759
still calls Phase B NEXT_READY. WO191 activation describes ZRA2 as cleared. This source
repair does not adjudicate that discrepancy; integrator must reconcile it before
claiming fully operational continuation. WO191 is left untouched.

Native Windows preflight at delivery982fb84: 14 PASS / 2 pytest setup/teardown errors.
The 64KiB parameter's autogenerated test ID exceeded Windows' 32767-character
environment-variable limit via PYTEST_CURRENT_TEST. Candidate f1dbb65 uses concise
explicit case IDs; production helper bytes are unchanged. Reverify native Windows
on the updated delivery before describing it as PASS. This is test portability,
not evidence that the payload budget should be weakened.
