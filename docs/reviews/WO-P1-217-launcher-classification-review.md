# WO-P1-217 — independent exact-SHA rereview: launcher hardening classification boundary

```text
VERDICT=PASS
P0=0 P1=0 P2=0 P3=3
merge_performed=false
```

- Exact candidate: `525f5fff702735c20011dc02764ea63372997b0a` (PR #293 head verified exact; state OPEN, unmerged). Parent: `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00` (PR #285; candidate `ROOTED_AT_F7D23C9` verified). Earlier parent `8339e4c9` (PR #266).
- Hosted CI for exact candidate (run 34666667716): macos-latest **pass**, ubuntu-latest **pass**, windows `test` **pass** (12m22s) — all terminal SUCCESS, re-pinned this session.
- Diff boundary: exactly 4 paths (`instance_create.py` +193/−15, `test_instance_create.py` +189, WO215 doc, `DEFECT_LESSONS.md`) — no unexplained production scope.
- Reviewer independence: this GLM lane authored the prior WO212 review (`3f1c7d2`) but **none of the candidate source** (WO194/WO207/WO215 commits are GPT-authored; verified via commit authors and lane history). Review lane clean; candidate inspected only through a detached read-only worktree at the exact SHA.
- Host: DESKTOP-7IB57R4 / Windows 11 / Python 3.11.15.

## Prior blocker reproduction (WO212 F-P2) — on the exact PARENT

Imported the parent module in isolation and re-ran both original counterexamples: complete marker set + **executable** legacy `Wait-Process` seam, and + **executable** stale method-wait seam → **parent returns byte-identical** (`PARENT-F-P2-waitproc… True`, `PARENT-F-P2-methodwait… True`). On the exact candidate the same inputs now → **`REFUSED_AMBIGUOUS`, text unchanged, and `create_instance` raises `REFERENCE_START_SCRIPT_UNSAFE` before creating the target directory** (A01/A02/A05). The blocker is closed at the operation boundary, not just the marker check.

## Probe matrix results (48/48 enforced, `runs/WO-P1-217/probe-results.json`)

Independent in-memory probes against the detached candidate (not the candidate's own tests):

- **A** refusal: partial-archive and partial-capture markers + legacy seam → REFUSED (A03/A04); refusal leaves **no target directory** (A05).
- **B** positives: method-wait and Wait-Process references TRANSFORM (hardened output verified); canonical hardened → ALREADY_HARDENED byte-identical; `harden(harden(x))==harden(x)` both variants; generic → PASSTHROUGH.
- **C** comments/strings: all markers in line comments / single+double-quoted strings / inline comments never gain authority and never suppress a real legacy seam (C01/C02/C04: seam still TRANSFORMS).
- **D** block comments: markers in `<#…#>` → PASSTHROUGH; nested blocks → PASSTHROUGH; fake markers in block + real seam → TRANSFORM; **mid-line open/close does not corrupt offsets of later seams** (D04 TRANSFORM); block-looking tokens inside quoted strings safe (D05).
- **E** here-strings: markers inside `@"…"@` and `@'…'@` → PASSTHROUGH; **indented fake `"@`/`'@` stays body content**; true column-zero terminator releases following executable seam (TRANSFORM); marker text on opener line has no authority.
- **F** duplicates/reorder/residue: duplicate archive / duplicate capture / reordered markers / generated shape + leftover `Wait-Process` / + stale direct ExitCode branch → **never ALREADY_HARDENED** (REFUSED or re-transform); stray bare wait after generated exit remains the inherited WO212 P3 advisory (dead code after `exit`).
- **G** preservation: DPAPI/credential, tunnel/project validation, SERENA_HOME, `finally` API-key cleanup, ordering, archive-before-STARTING, WaitForExit→Refresh→single capture, numeric logs, `exit $RuntimeExitCode`, stale-branch removal — all sentinels preserved through the supported transformation.
- **H** offset invariants: adversarial Thai/astral comments, Thai block comments, Thai here-strings, CRLF inputs → `len(view)==len(source)`, newline positions identical, no U+FFFD, executable matches in the view select the intended original span (deterministic assertions, not eyeballing). CRLF: pure helper preserves CR as content while production `Path.read_text()` universal-newlines — characterized separately, not conflated (H06).

### Operation boundary (`create_instance`, not just helpers)

Full reference fixtures (start/stop/instance.ps1/cmds/profiles/serena-home): REFUSED input → `InstanceCreateError.code == REFERENCE_START_SCRIPT_UNSAFE` **with no `instances/<slug>` tree created**; generic reference still succeeds; legacy reference materializes hardened (verified on the written `start.ps1`); already-hardened reference materializes byte-identical; a benign lexical reference (markers only in comments/strings/block/here-string) is **not falsely rejected**; source inspection confirms classification runs both **before any target creation** and **again after profile/name substitutions before final write** (candidate lines ~380 and ~429); the source path triggers no Worker deployment/restart side effects.

### Novel counterexamples (eight, beyond candidate tests)

N1 nested block comment containing a here-string-looking sequence + real seam → TRANSFORM; N2 quoted `'<#'` fake open + seam → TRANSFORM; N3 here-string with fake indented terminator + block-comment-looking body + true terminator → TRANSFORM; **N4 unclosed here-string containing all markers → never ALREADY_HARDENED** (masks to EOF; no marker authority); N5 markers split between executable and comment regions → REFUSED (partial executable archive + seam); N6 block comment closing mid-line + executable seam same line → TRANSFORM; N7 backtick-escaped quote + comment marker + seam → TRANSFORM; N8 doubled single-quote + block-looking text → TRANSFORM. All behaved correctly.

### Live read-only check (W1–W5, bytes only, nothing printed/written)

All five real launchers classify **`REFUSED_AMBIGUOUS`** — a deliberate change from the WO212-era "would transform". Diagnosis: the live scripts contain the legacy method-wait seam **plus** executable readiness-loop `$RuntimeProcess.Refresh()` occurrences (×2) and other partial forensics signals; the hardener's output is not the canonical hardened shape, so the classifier refuses instead of half-transforming. This is the fail-safe direction and the intended WO215 behavior, but it is operationally significant: **after merge, creating new instances from the current live reference will fail closed with `REFERENCE_START_SCRIPT_UNSAFE` until the reference launcher itself is updated (WO194 hardened reference deployed first).** Recorded as P3-1 for integrator sequencing; not a safety defect.

## Verification floor (exact candidate, detached worktree)

| Command | Result |
|---|---|
| `pytest -q tests/test_instance_create.py` | **39 passed** |
| `pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py tests/test_desktop_control.py` | **72 passed, 1 warning** |
| `compileall -q src/a_conductor/instance_create.py` | OK |
| `git diff --check f7d23c9..525f5ff` | clean |
| changed-path audit | exactly the 4 declared paths |
| added-line secret-like scan (534 added lines) | 0 hits |
| strict UTF-8 / no U+FFFD (source + tests at exact SHA) | OK |

## Findings

- **P0 = 0, P1 = 0, P2 = 0.**
- **P3-1 (operational advisory):** live W1–W5 references now classify REFUSED_AMBIGUOUS → new-instance creation from the current fleet reference fails closed post-merge until the reference is hardened (sequence with WO192/WO194). Fail-safe direction; integrator scheduling input.
- **P3-2:** malformed/unclosed lexical regions (e.g. unterminated here-string) mask subsequent content from structural signal → such a reference passes through unrecognized rather than being refused. Acceptable because the script is syntactically non-functional in PowerShell anyway (the masked "seam" could not execute); an optional future hardening is to refuse on unclosed regions at EOF. Proven never to produce ALREADY_HARDENED (N4).
- **P3-3:** inherited WO212 stray-bare-wait advisory (dead code after `exit`) — unchanged, unreachable, advisory only.

## Boundary

`merge_performed=false`. This review recommends **PASS** (P3-only, no safety/authority contract violated). GPT-5.6 Sol owns final adjudication, merge, and any WO192 deployment sequencing.

**Next safe action:** GPT-5.6 Sol adjudicates PR #293 at exact `525f5ff` using this review; on acceptance+merge, sequence the hardened-reference update before any new-instance creation (P3-1), then proceed per Issue #267 routing.
