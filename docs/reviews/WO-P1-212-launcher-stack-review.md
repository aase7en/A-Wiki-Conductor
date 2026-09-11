# WO-P1-212 — Independent launcher-stack review (parent #266 + repair #285)

```text
VERDICT=CHANGES_REQUIRED
P0=0 P1=0 P2=1 P3=3
merge_performed=false
```

- Repo `aase7en/A-Wiki-Conductor`; review lane `review/wo-p1-212-launcher-stack` (this branch). Reviewer: GLM-5.3 lane — **not an author of any candidate commit** (parent #266 and repair #285 are GPT/WO194/WO207 lanes).
- Parent `8339e4c9e15c8eefd94693245ef9ef4b627c00de` / PR #266 (OPEN); child `f7d23c96690f7cdb94d2ebe62cac6d4669ad6f00` / PR #285 (OPEN; base verified = `fix/wo-p1-194-legacy-launcher-forensics` = the #266 branch; head exact).
- Hosted CI: both SHAs **all jobs terminal SUCCESS** (#266 run 34587841847, #285 run 34633783287 — macos/ubuntu smoke + windows test).
- Child diff vs parent: +153/−1 across `instance_create.py` (marker guard), `tests/test_instance_create.py`, WO207 doc — **no unrelated source** (A ✓).
- Candidate source/tests reviewed READ-ONLY at a detached worktree at exact `f7d23c9`; no candidate branch touched; no launcher written; no Worker/process restarted; no secrets read.

## Verification floor (exact child SHA)

| Command | Result |
|---|---|
| `pytest -q tests/test_instance_create.py` | **26 passed** |
| `pytest -q tests/test_setup_wizard.py tests/test_ps1_encoding_and_quoting.py tests/test_doctor_fixes.py` | **38 passed** |
| `compileall -q src/a_conductor/instance_create.py` | OK |
| `git diff --check 8339e4c..f7d23c9` | clean |

## Independent probe matrix (in-memory, exact child function)

Probes: `runs/WO-P1-212/probe_matrix.py` → `probe-results.json`; live read: `live-read-results.json`.

### Marker matrix (packet §mandatory 1–15)

| # | Case | Expected | Actual | |
|---|---|---|---|---|
| M01 | comment with `runtime-archive` | HARDEN | HARDEN | ✓ |
| M02 | quoted free string | HARDEN | HARDEN | ✓ |
| M03 | exact archive assignment only | UNCHANGED | UNCHANGED | ✓ |
| M04 | exact exit-capture only | UNCHANGED | UNCHANGED | ✓ |
| M05 | Refresh only | HARDEN | HARDEN | ✓ |
| M06 | `exit $RuntimeExitCode` only | HARDEN | HARDEN | ✓ |
| M07 | archive+Refresh (no capture/exit) | UNCHANGED | UNCHANGED | ✓ |
| M08 | capture+exit (no archive/refresh) | UNCHANGED | UNCHANGED | ✓ |
| M09 | complete generated hardening | UNCHANGED | UNCHANGED | ✓ |
| M10 | complete + unrelated comments | UNCHANGED | UNCHANGED | ✓ |
| M11 | archive with double quotes | HARDEN | HARDEN | ✓ (not the exact structural form → not partial-migration) |
| M12 | whitespace variant of exact archive line | label said HARDEN | UNCHANGED | ✓ implementation — patterns deliberately tolerate indentation/trailing whitespace, so the variant is still structural (my label was wrong; source is right and conservative) |
| M13 | marker text inside comment | HARDEN | HARDEN | ✓ |
| M14 | duplicated structural marker | UNCHANGED | UNCHANGED | ✓ |
| M15 | complete markers around stale/ambiguous seam | see **F-P2** | UNCHANGED | evidence for F-P2 |

### Seam variants (B), preservation (C), forensics (D), idempotency (F)

- B01 **CRLF method-wait → UNCHANGED** (conservative): the method-wait regex's final `\}[ \t]*$` does not tolerate `\r`; generated launchers are LF (real W1–W5 files are LF), so CRLF is out-of-contract unknown → fail-unchanged is the safe direction → **P3-1** (document; optionally uniform `\r?`, but current behavior never false-rewrites).
- B02 indentation change inside the 3-line method-wait block → UNCHANGED ✓ (same-indent contract enforced).
- B03 unrelated leading lines → HARDENED ✓. B05 incomplete failure block → UNCHANGED ✓. B06 method-wait without stale direct branch → UNCHANGED ✓ (refuses partial seam). B07 duplicate stdout assignment → UNCHANGED ✓. B08 STARTING-before-stdout ordering violation → UNCHANGED ✓.
- B04 **stray duplicate bare `$RuntimeProcess.WaitForExit()` appended after the recognized block → HARDENED with the stray line left as unreachable dead code after `exit`** — no stale decision branch survives; residue only in manually-mangled input → **P3-2**.
- C01: credential/DPAPI, tunnel/project validation, SERENA_HOME, `finally` API-key cleanup — all preserved in order in hardened output ✓ (regex spans cannot reach across: replacements are line-anchored on the seam).
- D01: hardened output verified — archive dir bounded under `$LogsDir 'runtime-archive'`; Move-Item archive **before** STARTING (old evidence preserved pre-truncation); stamped archive names (`$ArchiveStamp + '-' + $Leaf`) (my probe's literal `-$Leaf` check was a probe bug — names are stamped); WaitForExit → Refresh → single capture ordering; `STOPPED ... exit_code=0`; numeric failure log `exit_code={0}`; `exit $RuntimeExitCode`; stale direct `if ($RuntimeProcess.ExitCode -ne 0)` branch **removed** ✓.
- D02: Wait-Process variant hardens, old wait removed, idempotent ✓. F01: noise comment cannot suppress hardening ✓. Idempotency `harden(harden(x)) == harden(x)` for both variants ✓.

### G — live-shape read-only verification

All five real `sunday-worker-1..5/start.ps1` (read bytes only, never written, nothing printed) are **recognized as legacy and would be hardened in memory** — the WO192-era method-wait recognition gap is closed by the combined stack. Summarized booleans in `live-read-results.json`.

### H — no deployment authority

Merging this source changes generation/hardening code only; no path writes existing `start.ps1` or restarts Workers. Deployment remains under WO192 operational gates (task/claim state, process identity, W2 protection, explicit authorization). Reviewer deployed nothing. ✓

## Findings

**F-P2 — complete-marker guard can classify an unsafe stale launcher as already hardened (packet-blocking sentence met; deterministic evidence).**
Repro (N01, also M15): a legacy launcher (`Wait-Process -Id $RuntimeProcess.Id` seam, no archive/no numeric capture) with the four marker lines pasted in as bare lines → guard sees the complete structural set → returns **byte-identical** → the legacy seam is never upgraded, and the file *looks* hardened. Reachability analysis (honest): the hardener itself never produces this state (it replaces the seam when hardening), and the function runs at instance-creation over generated templates — so within the current product call path the state requires manual marker pasting; the pure function also never makes any input worse. However (a) the review packet's own rule makes this classification blocking, (b) the function's `str→str` return cannot distinguish "already hardened" from "refused ambiguous" — downstream migration drivers keyed on unchanged-output would skip an unsafe launcher, and (c) the same ambiguity exists for complete-markers+modified-seam (M15). Minimal fix directions for the repair owner: require, for the *complete* classification, additionally that NO recognized legacy seam (`Wait-Process -Id`/method-wait block) remains; and/or expose a tri-state classification (HARDENED_UNCHANGED / REFUSED_AMBIGUOUS / TRANSFORMED) so callers cannot conflate them. Both keep all existing conservative behaviors.

**F-P3-1** — CRLF input unsupported (final `\}` anchor intolerant of `\r`) → fail-unchanged; safe direction; document or unify `\r?` deliberately.
**F-P3-2** — stray duplicate bare wait line survives hardening as unreachable dead code (B04); cosmetic residue on mangled input.
**F-P3-3** — documentation: WO207 policy "complete → byte-identical" is implemented exactly; the F-P2 tension between that documented policy and the packet's blocking rule is an integrator decision — this review follows the packet as written.

Severity per packet §9: P2 present → **CHANGES_REQUIRED**. P0=0, P1=0.

## Answers A–H (summary)

A: identity/stack/CI/diff-scope all verified exact ✓. B: both legacy forms recognized; ambiguous/partial variants fail unchanged ✓ (CRLF P3; stray-wait P3). C: credential/preflight/finally preservation proven ✓. D: full forensics contract verified incl. archive-before-truncation ordering, Refresh-before-capture, numeric logs, stale-branch removal, idempotency ✓. E: matrix 15/15 behaviorally classified — with F-P2 false-complete boundary proven. F: idempotent both variants; noise cannot suppress ✓. G: all five live launchers recognized as legacy in memory (read-only) ✓. H: no deployment authority ✓.

## Boundary & next safe action

`merge_performed=false`. This review recommends **CHANGES_REQUIRED** (single P2 F-P2 + 3 P3 advisories) for GPT-5.6 Sol adjudication; the integrator may waive F-P2 with an explicit reachability justification, in which case the remaining P3s permit PASS-with-advisory. Next safe action: GPT-5.6 Sol adjudicates PR #285 at exact `f7d23c9` against this review; any repair needs a fresh bounded owner (not this reviewer).
