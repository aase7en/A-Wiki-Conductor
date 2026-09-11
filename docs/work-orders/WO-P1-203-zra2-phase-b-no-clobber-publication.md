# WO-P1-203 — ZRA-2 Phase-B atomic no-clobber repair publication

Status: IMPLEMENTED / CANDIDATE FREEZE PENDING
Parent: WO-P1-195 / WO-P1-165 Phase B / Issue #214
Finding: GPT independent adversarial review, Issue #214 comment `5638342195`
Owner: GPT-5.6 Sol integrator / architecture; implementation executor TBD after release
Risk: R3 — task identity, idempotency, filesystem publication boundary
Base for this packet: `02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971`
Branch: `docs/wo-p1-203-zra2-phaseb-collision-repair-gate`

## 1. Why this successor exists

WO195 Phase B requires deterministic repair-task materialization with this invariant:

- same deterministic path + same exact bytes => reuse;
- same deterministic path + different bytes => typed collision;
- no hidden overwrite, retry, or second authority.

Independent read-only review of the active WO195 WIP found a TOCTOU gap between the materializer's existing-file observation and `NativeFileSystem.write_text()` publication.

Current shape:

1. materializer reads deterministic path;
2. path is absent;
3. materializer calls `NativeFileSystem.write_text(path, content)`;
4. `write_text()` observes target absent;
5. another actor can create the target before final publication;
6. `write_text()` uses `os.replace(temp, target)`;
7. the conflicting target is overwritten;
8. materializer re-reads its own bytes and returns success.

Temp-only deterministic fault injection reproduced:

```text
INJECTED=True
FINAL_IS_CONFLICT=False
OUTCOME=RETURNED_PACKET
```

No W2 files, live runtime, provider, credentials, or production Worker were mutated by that proof.

## 2. Classification

`P1 — authority/idempotency boundary`

Reason:

The deterministic repair path is part of the task identity contract. A different artifact already occupying that identity must never be silently replaced. Allowing last-writer-wins publication means collision detection depends on timing rather than durable bytes.

This is not a cosmetic race and not merely a test flake. It violates the frozen Phase-B acceptance contract directly.

## 3. Why the materializer alone must not bypass the filesystem authority

A tempting repair is direct `Path.open("xb")` or raw `os.open()` inside `zero_relay_repair_materializer.py`.

Do not do that.

Phase B explicitly reuses the existing confined filesystem authority. The materializer must not become a second path-confinement/write authority merely to obtain exclusive-create semantics.

Therefore the safe repair shape is:

`NativeFileSystem gains one narrowly scoped atomic no-clobber publication primitive`

then:

`zero_relay_repair_materializer uses that primitive and maps already-exists to exact-byte reuse or typed collision`.

No scheduler/reviewer/provider/lease/task store is added.

## 4. Dependency / release gate

This packet is PREPARED only.

Do not mutate production source until all are true:

1. current GLM/Worker-2 WO195 Phase-B WIP is frozen to an exact candidate SHA;
2. GPT independent review records the P1 against that exact candidate;
3. current worktree/branch/HEAD/dirty state is re-pinned;
4. no concurrent lane owns the proposed files;
5. GPT explicitly releases a bounded repair claim;
6. source scope below is confirmed compatible with then-current main/parent branch.

Until then:

`SAFE_TO_MUTATE_WO203=NO`

The active GLM lane must not be reset/stashed/rebased/overwritten to consume this packet.

## 5. Proposed bounded source scope after release

Preferred mutable source:

- `src/a_conductor/native_execution.py`
- `src/a_conductor/zero_relay_repair_materializer.py`

Preferred tests:

- `tests/test_native_execution.py`
- `tests/test_zero_relay_repair_materializer.py`

This work order may be appended for checkpoints.

Everything else read-only unless GPT explicitly expands scope after new evidence.

## 6. Required authority behavior

### 6.1 Native filesystem primitive

Add one explicit API whose semantics are unmistakably "publish this new file only if the final target does not already exist".

Naming is implementation-dependent, but semantics must be equivalent to:

```text
create_text_if_absent(relative_path, content)
```

Required properties:

- confined by existing `NativeExecutionScope`;
- requires `mutation_allowed=True`;
- exact UTF-8 byte accounting;
- same file-size limit as existing text writes;
- parent must already exist;
- non-file target fails typed;
- target existence at any point before final publication must never be overwritten;
- successful publication returns existing `NativeWriteResult`-compatible evidence or a similarly bounded existing type only if necessary;
- no caller-supplied absolute target authority;
- no retry loop;
- no hidden fallback to clobbering `os.replace()` semantics;
- errors stay stable and typed without raw path/secret leakage.

The implementation must prove its no-clobber guarantee on Windows and on hosted Linux/macOS CI. Do not assume POSIX `rename()` and Windows `rename()` have identical replacement semantics.

A temp-file + atomic publish strategy is preferred when it can truthfully prove no-clobber. If the chosen platform primitive is unavailable or unsupported, fail typed rather than fall back to overwrite.

### 6.2 Materializer behavior

For the deterministic repair path:

1. optional pre-read may still optimize exact replay;
2. publication must use the new no-clobber filesystem authority;
3. if publication wins, re-read and verify exact bytes/hash/path;
4. if publication reports target-already-exists, re-read through `NativeFileSystem`;
5. if existing bytes/hash match expected, reuse exact existing artifact;
6. if existing bytes/hash differ, raise stable `REPAIR_TASK_COLLISION`;
7. if the path disappears or becomes unverifiable during reconciliation, return typed verification/recovery failure — never blind retry;
8. do not broaden generation, review, provider, or scheduler authority.

## 7. RED-first obligations

Before production repair, add deterministic failing tests for the current candidate.

Minimum matrix:

### NativeFileSystem

- target absent -> no-clobber create succeeds;
- target already exists with same bytes -> primitive itself does not overwrite it;
- target already exists with different bytes -> primitive does not overwrite it;
- injected target creation between initial observation and final publication -> existing target survives untouched;
- two concurrent creators of same path -> at most one publication winner;
- loser receives stable already-exists/conflict signal;
- target directory/non-file edge cases remain typed;
- mutation disabled remains `MUTATION_FORBIDDEN`;
- parent missing remains typed;
- file-too-large remains typed;
- UTF-8 byte size/hash is exact;
- temp artifacts are cleaned best-effort without deleting another actor's target.

### Repair materializer

- exact same identity/bytes replay reuses;
- pre-existing different bytes => `REPAIR_TASK_COLLISION`;
- TOCTOU injection after pre-read but before publication => `REPAIR_TASK_COLLISION`, conflicting bytes preserved;
- concurrent same request => both callers converge on same packet identity and exact bytes;
- no caller overwrites divergent artifact;
- no second repair generation;
- no second filesystem/path authority in the materializer;
- no retry loop;
- path remains deterministic and project-confined;
- returned `TaskPacketFile.sha256` equals exact persisted bytes.

Positive controls are mandatory beside negative controls.

## 8. Concurrency proof

Do not rely on sleeps as the main proof.

Prefer deterministic synchronization/barriers or a narrowly injected filesystem publication hook in tests.

At least one real concurrent test should demonstrate:

```text
same final path
+ two creators
=> one physical publication winner
=> no clobber
=> loser reconciles existing bytes
```

For divergent-content collision testing, do not attempt to find SHA-256 collisions. Inject an external conflicting artifact at the deterministic final path between observation and publication, as in the independent reproducer.

## 9. Compatibility constraints

Existing `NativeFileSystem.write_text()` behavior is already used elsewhere. Do not silently change its overwrite/CAS contract unless source archaeology proves that change is backward compatible for all callers.

Prefer an additive narrow primitive over semantic mutation of `write_text()`.

If archaeology proves an additive primitive would duplicate an already-existing safe primitive, reuse the existing primitive and document that evidence instead.

## 10. Verification ladder after release

1. RED-only targeted tests proving current failure;
2. focused native filesystem tests;
3. focused Phase-B materializer tests;
4. related `agent_change_packets` / task packet tests;
5. broader native execution regression justified by changed authority;
6. compile/import;
7. diagnostics;
8. `git diff --check`;
9. UTF-8/U+FFFD scan;
10. added-line secret-like scan;
11. exact changed-path audit;
12. Windows targeted stress repeat;
13. hosted CI on frozen SHA;
14. independent exact-SHA review.

No test weakening.

## 11. Acceptance

Eligible for acceptance only if:

- no-clobber publication is demonstrated, not inferred;
- injected different-byte target survives untouched;
- materializer returns typed collision for that case;
- exact replay remains idempotent;
- concurrent same-input callers converge safely;
- existing `write_text()` callers are not accidentally changed;
- no new filesystem/scheduler/review/provider/lease authority is created;
- changed files stay within released scope;
- exact candidate is clean/pushed;
- CI is fully terminal green;
- independent reviewer returns no P0/P1/P2 blocker.

The implementation author does not self-accept or self-merge.

## 12. External gates / stop conditions

Stop and checkpoint immediately on:

- WO195 candidate not frozen;
- missing GPT scope release;
- overlapping owner/claim;
- main/parent drift that changes NativeFileSystem contract;
- platform primitive cannot prove no-clobber semantics;
- non-terminal CI;
- independent review / GPT acceptance / merge gate.

Do not work around a gate by editing unrelated files.


## 13. GPT bounded repair checkpoint — 2026-09-11

- Parent GLM candidate: `865ef3c18ebc5f4fb0f34f40dcee6851295baee4` / PR #280.
- Independent review verdict: `CHANGES_REQUIRED`, P0=0 / P1=1.
- P1 reproduced on exact candidate: raced different-byte target was overwritten and packet success returned.
- Repair lane: `fix/wo-p1-203-zra2-phaseb-no-clobber`, isolated from the frozen GLM worktree.
- Added `NativeFileSystem.create_text_if_absent()` using same-directory temp + fsync + atomic `os.link()` publication. Existing `write_text()` semantics remain unchanged.
- `FILE_ALREADY_EXISTS` is reconciled by the materializer through exact re-read: same bytes reuse, divergent bytes `REPAIR_TASK_COLLISION`, vanished/unverifiable state fails closed.
- Windows native proof: hard-link create succeeds for absent target and raises `FileExistsError` for existing target without replacement.
- Deterministic RED before repair: materializer different-byte race DID NOT RAISE; NativeFileSystem create-if-absent API absent (3 RED failures).
- GREEN focused: no-clobber NativeFileSystem 5 passed; materializer race/concurrency 4 passed.
- Phase-B/native regression: 172 passed, 1 Windows-expected POSIX FIFO skip.
- ZRA-2/review/GoalCloseout regression: 149 passed.
- Compile, `git diff --check`, strict UTF-8/no U+FFFD, and secret-like added-line scan all pass.
- Changed scope before freeze: the four released source/test files plus this WO checkpoint only.
- Implementation author is GPT-5.6 Sol; final candidate requires independent GLM exact-SHA rereview and hosted CI. No merge authorized.
