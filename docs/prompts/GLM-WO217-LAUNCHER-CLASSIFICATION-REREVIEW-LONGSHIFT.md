/goal

Execute WO-P1-217 as an independent, adversarial exact-SHA rereview of the final GPT-authored launcher classification repair.

PRIMARY PACKET:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo217-launcher-review\docs\work-orders\WO-P1-217-launcher-classification-independent-rereview.md

REVIEW TARGET:
- PR #293
- exact candidate: 525f5fff702735c20011dc02764ea63372997b0a
- exact parent: f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00
- earlier parent: 8339e4c9e15c8eefd94693245ef9ef4b627c00de
- prior independent review: WO212 / 3f1c7d27543c9a8bebd8fe3844085d59261638aa

REVIEW LANE:
A:\GitHub\_worktrees\A-Wiki-Conductor-wo217-launcher-review
branch: review/wo-p1-217-launcher-classification-rereview

CANDIDATE LANE IS READ-ONLY.
Do not edit PR #293 source/tests. Do not merge. Do not deploy or restart Workers.

## Operating mode

Use the available long work budget aggressively. This is intended to be a deep falsification campaign, not a quick approval pass.

Do not optimize for chat/context length. Persist useful intermediate evidence under the WO217 review lane so later invocations can resume. Keep raw logs/probes under runs/WO-P1-217 and keep the final tracked review concise but evidence-backed.

Follow this loop inside the SAME review goal:

REFRESH ACTUAL STATE
-> RE-DERIVE ARCHITECTURE
-> REPRODUCE PRIOR BLOCKER
-> ATTACK REPAIR ASSUMPTIONS
-> RUN NOVEL COUNTEREXAMPLES
-> VERIFY OPERATION BOUNDARY
-> VERIFY REGRESSIONS/STATIC STATE
-> WRITE REVIEW EVIDENCE
-> CHECKPOINT
-> STOP AT GPT GATE

Do not switch to another backlog item merely because this work finishes early.

## Mandatory startup gate

Before any review experiment:

1. read the WO217 packet completely;
2. re-pin origin/main, PR #293 head/base/state and exact hosted checks;
3. prove PR #293 head is exactly 525f5fff702735c20011dc02764ea63372997b0a;
4. prove base is the expected #285 branch/head rooted at f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00;
5. prove all hosted CI jobs for the exact candidate are terminal SUCCESS;
6. prove candidate source worktree is frozen/clean or inspect detached at the exact SHA;
7. prove this reviewer did not author the candidate source repair;
8. prove review lane has no unexplained dirty state.

If CI is non-terminal, checkpoint BLOCKED_EXTERNAL_CI and STOP. Do not poll.
If source identity differs, checkpoint SOURCE_DRIFT and STOP.

## Review mission

Try to prove the candidate unsafe or semantically incomplete.

The candidate claims it closes the WO212 P2 by introducing typed launcher state and operation-level refusal, then closes author-discovered provenance failures by masking non-executing PowerShell regions before structural regexes run.

Do NOT accept those claims from docs. Re-derive them from exact source and independent probes.

## Required source archaeology

Inspect symbolically and through exact diff:

- _powershell_executable_view
- _is_runtime_forensics_hardened
- _has_runtime_forensics_structural_signal
- _harden_start_script_runtime_forensics
- _classify_start_script_runtime_forensics
- create_instance
- all new/changed tests in tests/test_instance_create.py
- WO215 defect-memory entry

Trace the real production caller. Confirm whether unchanged text, typed state, and pre-materialization behavior mean what the candidate claims.

## Reproduce old failure first

Before inventing novel cases, independently recreate WO212 F-P2 on the exact parent f7d23c9 if practical in a temporary/detached environment:

- complete hardening-looking markers + executable legacy Wait-Process seam;
- complete markers + stale method-wait seam.

Confirm the parent can return unchanged / allow unsafe ambiguity in the production operation path.

Then run the same independent cases against 525f5ff and prove the target directory is not materialized when REFUSED_AMBIGUOUS is returned.

Do not rely only on the candidate's own tests.

## Deep provenance attacks

At minimum perform the full matrix in WO217 §6. Additionally try to falsify the lexical masking implementation itself.

### Comments

Try:
- line comments at column zero;
- indented line comments;
- inline comments after executable code;
- comments containing all generated markers in order;
- Thai/Unicode comments containing marker text;
- marker text after escaped/quoted # characters.

Non-executing comment text must never become hardened authority or suppress a real executable legacy seam.

### Block comments

Try:
- simple <# ... #>;
- nested block comments;
- block open/close mid-line;
- multiple block regions;
- markers before/inside/after nested comments;
- a block comment containing every hardened marker in perfect generated order;
- fake archive/capture marker in block comment followed by a real legacy seam.

Verify executable-view length/newline/offset invariants.

### Here-strings

Test BOTH @"..."@ and @'...'@ forms.

Try:
- every marker inside here-string body;
- a fake indented terminator such as `    "@` that must remain body content;
- later true column-zero terminator;
- marker text immediately after the true terminator;
- opener after assignment;
- multiple here-strings;
- comments/block-comment-looking tokens inside here-string content;
- Unicode/Thai body content;
- malformed/unclosed here-string.

For malformed lexical input, UNKNOWN must never turn into ALREADY_HARDENED. Explain whether the production path passes through or refuses and whether that is fail-safe for the actual create_instance contract.

### Quotes / escaping

Try ordinary single/double quoted strings, doubled single quotes, PowerShell backtick escapes, literal marker strings, and marker-adjacent escaped quote characters.

Attempt to trick the scanner into opening/closing block comments or here-strings from inside a normal quoted string.

### Structural shape

Try executable:
- duplicate markers;
- reordered markers;
- stale Wait-Process plus new block;
- stale direct ExitCode branch plus new block;
- extra WaitForExit before/after generated exit;
- wrong archive directory assignment;
- altered Move-Item destination;
- altered log text;
- missing Refresh;
- two captures;
- two exits.

No stale/duplicate executable shape may be promoted to ALREADY_HARDENED.

## Offset invariants

This is important because the hardener matches against a masked view but slices the original source.

Independently assert for adversarial inputs:

- len(view) == len(source);
- every CR/LF position remains identical;
- positions of real executable matches in the view map to the intended original characters;
- Unicode code points before a seam do not move character offsets;
- block/here-string masking never deletes/adds characters;
- transformations replace the intended real seam, not a nearby non-executing lookalike.

Use deterministic assertions, not eyeballing.

## Operation boundary

Inspect and test create_instance, not only helpers.

You must prove:

- safety classification of the reference start.ps1 happens before target directory creation;
- REFUSED_AMBIGUOUS raises InstanceCreateError with code REFERENCE_START_SCRIPT_UNSAFE;
- no partial target tree remains after refusal;
- generic unrelated reference still succeeds;
- known legacy reference still transforms;
- already hardened reference remains accepted;
- comment/quoted/block/here-string examples cannot falsely reject a generic reference unless there is real executable ambiguity;
- after profile/name substitutions the script is classified again before final write;
- no Worker runtime or deployment side effect occurs.

## Preservation attacks

Use sentinel-driven tests/probes to prove supported transforms retain:

- DPAPI/credential handling;
- tunnel validation;
- project validation;
- SERENA_HOME/environment semantics;
- finally API-key cleanup;
- runtime archive before STARTING/truncation;
- WaitForExit -> Refresh -> one capture ordering;
- numeric STOPPED/failure logging;
- final exit $RuntimeExitCode.

Attempt to find a regex span that accidentally crosses unrelated preflight logic.

## CRLF and platform honesty

Characterize pure-helper CRLF behavior separately from Path.read_text() production behavior.

Do not upgrade a P3 pure-helper limitation into a production blocker without reachability evidence. Conversely, do not dismiss a reachable Windows PowerShell behavior merely because candidate tests use LF strings.

Use the exact Windows host for relevant proof and rely on hosted macOS/Linux CI for portability signals, while keeping launcher-runtime claims honestly Windows-scoped.

## Live read-only optional check

If Sunday Worker launcher paths can be discovered safely, read W1–W5 start.ps1 only.

Rules:
- never print contents;
- never print secrets/credential material;
- never write files;
- never restart/stop/start a Worker;
- never change runtime state.

Report only safe classification booleans/state summaries. This is supporting evidence, not deployment authorization.

## Candidate verification floor

Run at minimum:

pytest -q tests/test_instance_create.py
pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py
python -m compileall -q src/a_conductor/instance_create.py
git diff --check f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00..525f5fff702735c20011dc02764ea63372997b0a

Also:
- inspect exact changed paths;
- strict UTF-8/no-U+FFFD;
- added-line secret-like scan;
- compare static diagnostics against parent;
- confirm no unrelated production scope.

Do not weaken tests or edit candidate files if anything fails. Record the failure as review evidence.

## Novel counterexamples

At least THREE novel cases not present in candidate tests are mandatory.

Prefer cases that combine lexical states rather than just changing whitespace.

Examples:
- nested block comment containing a here-string-looking sequence then real legacy code;
- normal quoted string containing `<#` followed by executable legacy seam;
- here-string containing an indented fake terminator then a block-comment-looking marker then true terminator;
- block comment closes mid-line, followed by code on the same line;
- multiple fake generated markers split across executable and non-executing regions;
- malformed/unclosed lexical regions.

For each novel probe, state what bug it would expose and include a positive/negative control where useful so the probe is not vacuous.

## Review result

Write final tracked evidence only to:

docs/reviews/WO-P1-217-launcher-classification-review.md

Use one verdict only:
VERDICT=PASS
VERDICT=CHANGES_REQUIRED
VERDICT=BLOCKED
VERDICT=SOURCE_DRIFT

Include exact P0/P1/P2/P3 counts.

P0/P1/P2 means CHANGES_REQUIRED.
P3-only may PASS with explicit advisory if no safety/authority contract is violated.

Include:
- exact target SHA;
- exact parent/base/PR/CI state;
- review independence;
- original F-P2 reproduction/control;
- A-H matrix results;
- novel attacks;
- test/static results;
- optional live read-only result;
- merge_performed=false;
- next safe action.

## Stop rule

At the FIRST external gate, finish only the current atomic safe step, write durable checkpoint/evidence, then STOP.

If PASS:
BLOCKED_EXTERNAL_GPT_ACCEPTANCE
STOP.

If CHANGES_REQUIRED:
BLOCKED_EXTERNAL_GPT_REPAIR_AUTHORITY
STOP.

No merge. No deployment. No WO192 rollout. No unrelated backlog work.
