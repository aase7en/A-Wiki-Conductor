# WO-P1-217 — independent exact-SHA rereview: launcher hardening classification boundary

Status: QUEUED / HOLD UNTIL EXACT CANDIDATE CI TERMINAL GREEN
Parent issue: #267
Prior independent review: WO-P1-212 / review commit `3f1c7d27543c9a8bebd8fe3844085d59261638aa`
Source parent stack:
- PR #266 / `8339e4c9e15c8eefd94693245ef9ef4b627c00de`
- PR #285 / `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00`
Repair under rereview:
- PR #293
- exact candidate `525f5fff702735c20011dc02764ea63372997b0a`
Review lane base: `cfcb369fe5ab3a50569defa822289f10f2f38aac`
Review branch: `review/wo-p1-217-launcher-classification-rereview`
Preferred reviewer: GLM-5.3/ZCode independent of GPT repair authorship
Final adjudicator: GPT-5.6 Sol integrator
Risk: R3 source/reliability boundary

## 1. Why this rereview exists

WO212 independently reviewed the GPT-authored launcher stack and returned:

`CHANGES_REQUIRED — P0=0 P1=0 P2=1 P3=3`

The blocking P2 proved that a launcher containing the four apparent hardening marker lines could still retain a legacy wait seam, yet the string transformer could treat it as already hardened and return it unchanged.

WO215 repairs the operation boundary rather than merely changing one marker check. The repair adds typed classification and causes `create_instance()` to refuse ambiguous references before target materialization.

Author-side falsification then found two additional authority defects in the same boundary before independent rereview:

1. broad substring/count checks could elevate comment-only marker text to `ALREADY_HARDENED` or quoted text to structural authority;
2. line anchoring alone still allowed PowerShell block comments / here-strings to supply apparent executable markers or suppress a real legacy seam.

The final candidate therefore adds a same-length executable PowerShell view that masks non-executing regions before any hardening/classification regex receives authority.

This WO exists to independently falsify that final exact candidate. It is not permission to deploy launcher changes.

## 2. External start gate

Before review work, prove all of the following from current Git/GitHub state:

1. PR #293 head is exactly `525f5fff702735c20011dc02764ea63372997b0a`;
2. PR #293 base is the exact #285 branch/head expected by this packet;
3. exact candidate hosted CI is terminal green on Windows/full + Ubuntu smoke + macOS smoke;
4. source candidate worktree is clean/frozen or inspected detached/read-only;
5. no later commit has replaced the target;
6. reviewer is not the author of the candidate source commit;
7. review branch owns only review evidence, not candidate source/tests.

If CI is non-terminal:

`BLOCKED_EXTERNAL_CI`

Checkpoint and STOP. Do not poll in a loop.

If SHA/base/source changed:

`SOURCE_DRIFT`

Checkpoint and STOP rather than silently reviewing a different tree.

## 3. Write authority

Allowed tracked writes on the review lane:

- `docs/reviews/WO-P1-217-launcher-classification-review.md`
- append-only checkpoint updates to this WO if needed

Allowed ignored/scratch evidence:

- `runs/WO-P1-217/**`
- temporary copied launchers under an owned temp directory only

Forbidden:

- candidate `src/**` edits;
- candidate `tests/**` edits;
- PR #293 branch mutation;
- live Worker `start.ps1` writes;
- Worker restart/stop/start;
- credential/API-key reads or printing;
- WO192 deployment mutation;
- merge of #266/#285/#293;
- A-Wiki mutation;
- unrelated backlog implementation.

`merge_performed=false` is mandatory.

## 4. Exact diff boundary

Review the final repair delta from exact parent:

`f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00..525f5fff702735c20011dc02764ea63372997b0a`

Expected changed paths are bounded to:

- `src/a_conductor/instance_create.py`
- `tests/test_instance_create.py`
- `docs/work-orders/WO-P1-215-launcher-hardening-classification.md`
- `DEFECT_LESSONS.md`

Any unexplained additional production path is a scope finding.

## 5. Architecture claims that must be re-derived

Do not accept these claims merely because WO215 states them. Re-derive them from code and tests.

### 5.1 Typed operation boundary

The candidate claims to distinguish:

- `TRANSFORMED`
- `ALREADY_HARDENED`
- `PASSTHROUGH_UNRECOGNIZED`
- `REFUSED_AMBIGUOUS`

and to make `create_instance()` reject only `REFUSED_AMBIGUOUS` with stable `REFERENCE_START_SCRIPT_UNSAFE` before creating the target directory.

Verify that `unchanged string` is no longer silently treated as a single semantic state.

### 5.2 Provenance view

The candidate claims `_powershell_executable_view()`:

- preserves total source length;
- preserves newline positions;
- masks non-executing line comments;
- masks nested PowerShell block comments;
- masks here-string bodies and terminators;
- recognizes a real here-string terminator conservatively at column zero;
- preserves executable code and ordinary quoted command arguments;
- preserves regex source offsets so matches against the view can safely slice/replace the original text.

Falsify these properties directly.

### 5.3 Hardener usage

Verify that the original hardener uses the executable view for:

- complete-hardening guard;
- partial marker guard;
- stdout/stderr/start seam discovery;
- Wait-Process seam discovery;
- method-WaitForExit seam discovery;
- post-insertion seam searches.

No raw non-executing marker should be able to suppress or trigger hardening.

### 5.4 Hardened-shape verification

Verify that `ALREADY_HARDENED` requires one real executable generated shape with correct ordering, no remaining legacy `Wait-Process -Id ...`, and no stale direct `$RuntimeProcess.ExitCode` failure branch.

Commented/quoted/non-executing examples must never satisfy the shape.

## 6. Mandatory falsification matrix

At minimum execute independent tests/probes for all cases below. Do not rely solely on candidate tests.

### A — original WO212 blocker

A01. complete apparent markers + executable legacy `Wait-Process` seam => REFUSED before target materialization.

A02. complete apparent markers + executable stale method-wait seam => REFUSED before target materialization.

A03. partial archive marker + legacy seam => REFUSED.

A04. partial exit-capture marker + legacy seam => REFUSED.

A05. no target directory/artifact remains after refusal.

### B — true positive controls

B01. canonical legacy method-wait reference => TRANSFORMED.

B02. canonical legacy Wait-Process reference => TRANSFORMED.

B03. canonical generated hardened launcher => ALREADY_HARDENED and byte-identical logically.

B04. harden(harden(x)) == harden(x) for both supported legacy variants.

B05. generic minimal unrelated reference => PASSTHROUGH_UNRECOGNIZED and create_instance succeeds.

### C — comments and string authority

C01. all marker text in `#` line comments => no hardened authority.

C02. marker text in ordinary single/double quoted strings => no structural authority.

C03. mixed real legacy seam + fake comment markers => real legacy seam still transforms.

C04. inline comments containing marker text cannot change classification.

### D — block comments

D01. all markers inside `<# ... #>` => PASSTHROUGH_UNRECOGNIZED when no real structure exists.

D02. nested block comments containing markers => no authority.

D03. fake archive/capture marker in block comment + real legacy method-wait seam => TRANSFORMED.

D04. block comment opens/closes mid-line without corrupting offsets of later executable seams.

D05. block-comment-like token inside ordinary quoted string must not accidentally erase following executable structure; classify conservatively and record behavior.

### E — here-strings

E01. marker lines inside double-quoted here-string => no authority.

E02. marker lines inside single-quoted here-string => no authority.

E03. an indented `"@` / `'@` inside body must not be treated as a real terminator.

E04. a true column-zero terminator releases following executable code correctly.

E05. fake marker in here-string + real legacy seam after terminator => real seam transforms.

E06. marker-like text on the here-string opener assignment line does not create false authority.

### F — ordering / duplicates / stale residue

F01. duplicate executable archive assignment => not ALREADY_HARDENED.

F02. duplicate exit capture => not ALREADY_HARDENED.

F03. generated markers reordered => not ALREADY_HARDENED.

F04. generated shape plus remaining `Wait-Process -Id ...` => REFUSED.

F05. generated shape plus stale direct `if ($RuntimeProcess.ExitCode -ne 0)` => REFUSED.

F06. stray extra bare wait after generated exit: classify and confirm no unsafe execution assumption; existing WO212 P3 may remain advisory if unreachable/ambiguous only.

### G — preservation

G01. DPAPI / credential preflight sentinel preserved exactly through supported legacy transformation.

G02. tunnel/project validation ordering preserved.

G03. `finally` API-key cleanup preserved.

G04. runtime archive remains before STARTING/truncation.

G05. WaitForExit -> Refresh -> single exit-code capture ordering preserved.

G06. final log includes numeric exit code and `exit $RuntimeExitCode`.

### H — lexical/offset invariants

H01. `len(executable_view) == len(source)` for adversarial Unicode + CRLF/LF inputs.

H02. newline character positions remain identical.

H03. match offsets obtained from executable view select the intended original executable source span.

H04. Thai/Unicode comments/here-string content cannot shift source offsets.

H05. no U+FFFD introduced.

H06. CRLF direct-helper behavior is characterized honestly. Operation-path `Path.read_text()` normalization and pure-helper behavior must not be conflated.

## 7. Novel counterexample requirement

Attempt at least three cases not present in candidate tests.

Prefer combinations such as:

- nested block comment + here-string + real legacy seam;
- escaped quote/backtick sequences near comment delimiters;
- block comment closing mid-line followed by executable legacy seam;
- here-string body containing a fake terminator plus later real terminator;
- duplicate generated markers split between executable and non-executing regions;
- Unicode/Thai marker-adjacent comments;
- malformed/unclosed here-string/block comment.

For malformed lexical regions, UNKNOWN must never become proof of hardened state. Conservative passthrough/refusal behavior must be explained against the actual production call path.

## 8. Operation-level verification

The review must inspect `create_instance()` rather than stopping at private helpers.

Verify:

1. reference `start.ps1` safety is classified before target directories are created;
2. `REFUSED_AMBIGUOUS` yields `InstanceCreateError.code == REFERENCE_START_SCRIPT_UNSAFE`;
3. refusal leaves no target instance directory;
4. generic unrelated reference remains compatible;
5. supported legacy reference is transformed;
6. already-hardened reference remains accepted;
7. classification is repeated after profile/name substitutions before final write;
8. no deployment/restart is triggered by this source path.

## 9. Verification floor

At exact candidate run at least:

- `pytest -q tests/test_instance_create.py`
- `pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py`
- `python -m compileall -q src/a_conductor/instance_create.py`
- `git diff --check f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00..525f5fff702735c20011dc02764ea63372997b0a`
- changed-path audit
- added-line secret-like scan
- UTF-8/no-U+FFFD check

If static diagnostics exist, compare against the exact parent. Pre-existing diagnostics do not automatically block; new diagnostics in the candidate scope do.

## 10. Optional read-only live-shape verification

Only if exact live paths can be discovered without secrets and without changing runtime:

- read W1–W5 `start.ps1` bytes/text only;
- never print file contents;
- summarize only safe booleans/hash-free shape classifications;
- do not write, deploy, restart, stop, start, or touch credentials.

Determine whether each live launcher would be:

- transformed,
- already hardened,
- passthrough unrecognized,
- refused ambiguous.

This is supporting evidence only; no live mutation authority is granted.

## 11. Severity policy

P0/P1/P2 => `CHANGES_REQUIRED`.

P3-only may permit `PASS` with explicit advisories when no safety/authority contract is violated.

Examples of blocking findings:

- non-executing text can still establish `ALREADY_HARDENED`;
- non-executing text can suppress a real legacy transformation;
- ambiguous executable legacy state reaches a new instance;
- refusal occurs only after target materialization and leaves partial state;
- classifier returns hardened for stale/duplicate executable seams;
- executable-view offsets diverge from original source offsets;
- source/test scope drift;
- regression in credential/preflight preservation.

## 12. Required review artifact

Write:

`docs/reviews/WO-P1-217-launcher-classification-review.md`

The first machine-readable block must include exactly one verdict:

- `VERDICT=PASS`
- `VERDICT=CHANGES_REQUIRED`
- `VERDICT=BLOCKED`
- `VERDICT=SOURCE_DRIFT`

Also include:

- exact candidate SHA;
- exact parent SHA;
- exact PR head/base/CI state;
- reviewer independence disclosure;
- P0/P1/P2/P3 counts;
- A–H findings;
- novel probes and their results;
- verification floor results;
- live read-only evidence if performed;
- `merge_performed=false`;
- exact next safe action.

## 13. Stop boundary

If verdict is PASS:

checkpoint `BLOCKED_EXTERNAL_GPT_ACCEPTANCE` and STOP.

If verdict is CHANGES_REQUIRED:

checkpoint `BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY` and STOP.

Do not deploy. Do not merge. Do not continue into WO192 rollout or an unrelated backlog item.
