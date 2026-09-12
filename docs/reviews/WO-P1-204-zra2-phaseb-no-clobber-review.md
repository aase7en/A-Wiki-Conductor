# WO-P1-204 — Independent exact-SHA review: repaired ZRA-2 Phase-B no-clobber publication

```text
VERDICT=PASS  (P3 advisories only; merge_performed=false)
```

- Repo/remote: `aase7en/A-Wiki-Conductor` (verified). Review lane: `review/wo-p1-204-zra2-phaseb-no-clobber` (this branch). Candidate inspected READ-ONLY at `A:\GitHub\_worktrees\A-Wiki-Conductor-wo203-zra2-phaseb-no-clobber`, HEAD = exact target.
- Parent GLM Phase-B candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` (PR #280).
- **Repair under review: `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e`** (PR #281, head verified == this SHA, base `feat/wo-p1-195-zra2-phase-b-materializer`, state OPEN).
- Hosted CI for exact `1c8c159` (run 34630182525): macos-latest **pass**, ubuntu-latest **pass**, windows `test` **pass** (11m29s) — all terminal SUCCESS (re-pinned this session; #280 also all-pass, run 34629110195).
- Reviewer disclosure: the parent base `865ef3c` was completed/frozen by this same GLM lane under WO200/Q1. The repair commit `1c8c159` is GPT-authored and is the review target; this review independently re-derived the failure mechanism, wrote its own probes (below), and would have failed the repair on any P0–P2. GPT-5.6 Sol owns final adjudication.
- Host: DESKTOP-7IB57R4 / Windows 11 x64 / Python 3.11.15.

## Repair diff summary (exact `865ef3c..1c8c159`)

5 files, +505/−9: additive `NativeFileSystem.create_text_if_absent()` (+50 lines in `native_execution.py`); materializer publication call `write_text` → `create_text_if_absent` and race signal `OVERWRITE_PRECONDITION_REQUIRED` → `FILE_ALREADY_EXISTS` (2-line semantic change, 4-line diff); new tests (+111 native_execution, +71 materializer); WO203 doc. `write_text` itself is untouched (the only `−` line in `native_execution.py` is the diff header) — legacy semantics preserved by construction and by probe R1.

`create_text_if_absent` mechanism: existing scope checks (mutation/content/size) → `resolve_relative` confinement → parent dir check → existing target → typed `FILE_ALREADY_EXISTS` (`FILE_TARGET_INVALID` for non-file) → same-directory exclusive temp (`.name.<uuid>.tmp`, mode `"xb"`) → write + flush + **fsync** → **`os.link(temp, target)`** as the atomic create-if-absent publish (`FileExistsError` → `FILE_ALREADY_EXISTS`; any other `OSError` → `FILE_WRITE_FAILED`, **no fallback**) → temp unlinked best-effort in `finally` (never the target) → `NativeWriteResult(created=True)`.

## A–F answers

### A. Exact identity / stack — PASS
1. Candidate worktree HEAD == `1c8c159bba74346dce60e6abb7d01ecbd1c17b4e` — verified.
2. Parent history rooted at exact `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` (single repair commit on top) — verified.
3. PR #281 base `feat/wo-p1-195-zra2-phase-b-materializer`, head `1c8c159…` — verified via GitHub.
4. All hosted CI jobs for the exact SHA terminal SUCCESS — verified (re-pinned; no polling).

### B. Authority architecture — PASS
5. `create_text_if_absent` is an additive method under existing `NativeFileSystem`/`NativeExecutionScope`; no new path authority (uses the single `resolve_relative` confinement seam).
6. Materializer has **zero** raw filesystem APIs (grep: 0 hits for `os.link|os.replace|os.open|.open(`; imports only `agent_change_packets`, `claude_code_harness.TaskPacketFile`, `native_execution`).
7. Scheduler/provider/review/lease/job/retry authorities unchanged (diff touches only the two files above + tests + doc; candidate's AST import-fence test retained and passing).
8. `write_text()` semantics unchanged: source untouched; probe **R1** proves the legacy replace-window still behaves exactly as the parent did (mechanism control, below) — the fix is the seam choice, not a global FS behavior change.

### C. No-clobber semantics — PASS
9. Never replaces: publish is `os.link`; existing name (including one created after precheck) ⇒ `FileExistsError` ⇒ typed refusal. Proven by code, by PR #281 tests, and independently by probes R2/R3/R5.
10. Raced target survives: probes R2 (materializer, conflicting bytes byte-exact intact) and R3 (real 16-process kernel race) both prove it.
11. `FileExistsError` mapped to bounded typed `FILE_ALREADY_EXISTS` — code + tests + probes.
12. Unsupported/other link errors fail closed as `FILE_WRITE_FAILED` with **no clobber fallback** (candidate test monkeypatches an unsupported link; verified, and no replace/rename path exists in the method).
13. Temp is same-directory, fully written, flushed **and fsynced** before publish (code order: write→flush→fsync inside the `"xb"` context, then link).
14. Temp cleanup unlinks only `temporary` (`missing_ok=True`, best-effort); the final target name is never passed to unlink. Post-conflict probes confirm zero leftover temps.
15. Publication exposes complete bytes atomically (the linked inode was fully written+fsynced before the link became visible under the target name).

### D. Materializer reconciliation — PASS
16. `FILE_ALREADY_EXISTS` → `_read_existing` re-read; exact same bytes ⇒ same logical `TaskPacketFile` (candidate test + my R4 8-thread same-input convergence: one packet identity, one physical file).
17. Different bytes ⇒ `REPAIR_TASK_COLLISION` (probe R2, independent binary-writer injector).
18. Missing/vanished raced state fails closed (`REPAIR_TASK_VERIFY_FAILED`; candidate VanishingWriter test retained and passing; no blind retry anywhere).
19. Two concurrent same-input callers converge without clobber — R4 (8 threads, real FS) and candidate barrier test.
20. Generation==1 and all digest/reason/path contracts retained (parent validation code untouched; focused suite green).

### E. Adversarial / portability — PASS with P3 notes
21. Different-byte race independently reproduced on the repaired tree: conflicting bytes survive, `REPAIR_TASK_COLLISION`, no packet returned (R2).
22. Same-path concurrent creators: R3 = **16 real processes** (no monkeypatch, real kernel race through `os.link`): exactly **1 winner, 15 typed `FILE_ALREADY_EXISTS` losers**, target bytes intact, zero temp residue; R5 = 8-way barrier threads: 1 winner / 7 typed.
23. Same-input materializer concurrency converges repeatedly (R4).
24. Confinement inherited: `resolve_relative` resolves symlinks/junctions (`resolve(strict=False)`) then `relative_to(root)`; **N1b**: a dangling symlink inside root whose referent lies OUTSIDE root ⇒ typed `PATH_OUTSIDE_ROOT`, nothing written — confinement held.
25. Mutation-disabled / missing parent / directory target / size bound / invalid content all typed as before (independently re-checked in C1).
26. Exact UTF-8 size/hash incl. Thai + emoji (C1; candidate UTF-8 test green).
27. Portability: `os.link` is standard on Windows NTFS (natively proven here), Linux and macOS; temp is same-directory ⇒ same volume (avoids EXDEV); unsupported filesystems (network shares/some reparse/FAT configurations) raise `OSError` ⇒ fail-closed `FILE_WRITE_FAILED` — honestly scoped, no network guarantees claimed. Directory hard-link attempts are pre-checked (`FILE_TARGET_INVALID`).
28. New-TOCTOU search: the publish primitive itself is atomic (link). The residual class is **resolve-then-act** (path resolved at T, acted at T+ε): probe **N3** (parent becomes junction in-window) observed **fail-closed** in the tested variant (`FILE_WRITE_FAILED`); a variant that re-materializes the source could land outside at the same lexical path. This class is **inherited** (identical exposure in `write_text`/existing scope design), not introduced by the repair; anchored handle-based create remains future hardening (matches WO196 L06 findings). Classified P3-1. UNKNOWN never becomes SAFE anywhere in the diff.

### F. Test quality / falsification — PASS
29. Race tests exercise real `NativeFileSystem` publication up to the `os.link` seam (monkeypatch only injects the racing writer at the seam — production code path runs); my R3 supersedes with a no-monkeypatch multiprocess race.
30. Barrier-driven concurrency tests present (2-way FS creators; 2-way materializer); no sleep-dependent assertions.
31. Vacuity check: injectors patch `os.link` only after real temp creation/fsync inside the method; assertions verify surviving bytes, typed codes, and temp cleanup — a naive replace-based implementation would fail them; my independent R3 confirms the property with no patching at all.
32. Positive controls retained; legacy `write_text` regression coverage untouched (parent tests unchanged; floor suites green).
33. **Novel counterexamples attempted (not in PR #281)**: R3 multiprocess kernel race; N1/N1b dangling-symlink referent behavior incl. outside-root escalation attempt (confined); N3 parent-junction-swap window (fail-closed variant); R1 legacy-seam control. One behavioral note emerged (P3-2): with an in-root dangling symlink at the target, publication materializes the referent and returns its resolved relative path — confined and identity-truthful, but surprising; worth a future test.

## Verification floor (exact `1c8c159`, Windows)

| Command | Result |
|---|---|
| `pytest -q tests/test_native_execution.py tests/test_zero_relay_repair_materializer.py` | **65 passed** (4.13 s) |
| `pytest -q tests/test_agent_change_packets.py tests/test_claude_code_harness.py` | **107 passed, 1 skipped** (POSIX FIFO) |
| `pytest -q tests/test_zero_relay.py tests/test_review_mailbox_adapter.py tests/test_goal_closeout.py` | **149 passed** |
| `python -m compileall -q src/a_conductor/native_execution.py src/a_conductor/zero_relay_repair_materializer.py` | OK |
| `git diff --check 865ef3c..1c8c159` | clean |

Independent probes: `runs/WO-P1-204/probes/wo204_adversarial.py` → `runs/WO-P1-204/probe-results.json` (R1–R5, N1/N1b/N2/N3, C1 — all recorded, elapsed seconds).

## Findings

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| P3-1 | advisory | Inherited resolve-then-act window (N3): an actor able to mutate a parent directory inside root between resolve and link can influence where a path-act lands; tested variant fails closed. Anchored (handle-based) create is future hardening. | non-blocking; forward to integrator with WO196 L06 evidence |
| P3-2 | advisory | In-root dangling symlink at the deterministic target: publication materializes the referent (confined; returned `relative_path` is the resolved path, so no identity lie). | non-blocking; suggest a future pinned test |
| P3-3 | advisory | fsync covers the file, not the parent directory (crash-durability nuance); the contract never claims power-loss durability. | non-blocking |

**P0 = 0, P1 = 0, P2 = 0.** The independently reproduced P1 clobber race of the parent is closed at the exact repaired SHA by an atomic `os.link` publish with typed reconciliation and no clobber fallback.

## Boundary

`merge_performed=false`. This review recommends only; GPT-5.6 Sol owns final R3 adjudication, merge, and post-main verification. Reviewer authored the parent base (disclosed above) but not the repair; probes and verdict are independently derived.

**Next safe action:** GPT-5.6 Sol adjudicates PR #281 at exact `1c8c159` using this review; on acceptance+merge, proceed to post-main verification and the Issue #214 Phase-C release gate (WO206 Q3 conditions).
