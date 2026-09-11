# WO-P1-196 GLM physical identity lab — portable evidence handback

Claim `WO196-GLM-C1-LAB-001` (child of WO-P1-196 / Issue #216 GPT1-ZRA4-PREFLIGHT-001; design owner Poppy Javis/GPT-6 Astra). Windows executor: GLM-5.3 under the user-started goal, delivery `10dca359568c216983199a6899b0af3863b5e9d7`, claim commit `9aa45a3` on `codex/wo-p1-196-glm-identity-lab`. Product implementation remains **HOLD** everywhere in this document.

- Packet SHA-256 `24f5969b2fbd252809187d52158ad72a8ee5f17290d892dbd1e66f072fbe44fe`; design SHA-256 `b131c0248a7f9f9aa12f49991d8576cd2a7e7ec3d70a20b4c5a5eb48537babc3`.
- Source blob IDs verified MATCH at delivery: `registry.py 5a50d3d6`, `worker_lease.py dad529bb`, `graph/analyze.py 670b5e84`.
- Host: DESKTOP-7IB57R4, Windows 11 x64, Python 3.11.15, git 2.x. Baseline `python -m pytest -q tests/test_worker_lease.py` → **36 passed** (run once, per packet).
- All experiments live under ignored `runs/WO-P1-196/glm/` with `wo196-` prefixed tempfile labs (retained for audit; links removed per protocol). Probe SHA-256 (first 16 hex): observer `2f3f6331`, L01 `9eef5bc3`, L02 `3a73028f`, L04 `4f6b2bd1`, L05 `9e31e8f3`, L06 `821a03e4`, L07 `efa8827a`, L08/L09 `43ac33e3`.

## Compact result matrix (native Windows evidence)

| # | Experiment | Native result | Meaning |
|---|---|---|---|
| L01 | junction alias vs real root | lexical key ≠, realpath =, **native SAME** | names miss physical equality |
| L01 | nested junction (two hops) | lexical ≠, **native SAME** | alias chains collapse natively |
| L01 | `\\?\C:\...` literal prefix | lexical ≠, **realpath ≠, native SAME** | NEW Windows vector: defeats realpath too |
| L01 | trailing `\`, `/`, case, dot-segments | lexical =, native SAME | normcase/normpath handle these |
| L01 | 8.3 short name | `NO_SHORTNAME` on this volume | recorded SKIPPED-class |
| L02 | real broker/store, alias spellings, same scope `src/a.py` | **LEASED + LEASED, 2 active rows** | conflict masked — native Windows RED |
| L02 | control: same spelling, same scope | LEASED + REFUSED `MUTABLE_SCOPE_OVERLAP` | existing protection is spelling-bound |
| L02 | alias + different project label | **LEASED + LEASED** | project label adds no protection |
| L04 | `write_sets_overlap` corpus (16 cases) | **10 false-negative semantic gaps**: separators, dot/current segments, abs-vs-rel, drive-relative, trailing dot/space, ADS stream, case-fold, NFC≠NFD | glob language itself preserved (star/globstar/`?` correct, symmetric, disjoint control correct) |
| L05 | hardlink across "independent" roots | roots DISTINCT, file ids **SAME object** (nlink 2) | root identity never proves file disjointness |
| L05 | nested root inside parent | ids DISTINCT | footprint ⊂ parent; ids alone insufficient |
| L05 | nonexistent leaf | `UNKNOWN(OPEN_FAILED)` | nearest-anchored-parent + suffix disposition |
| L05 | atomic replace vs in-place on hardlink pair | replace **breaks** alias (new id; link keeps v1) | operation class is a decision input |
| L06 | alias open in retarget window | write landed in **forbidden sentinel** | TOCTOU escape demonstrated |
| L06 | resolved-path open in same window | landed in observed object (this instance) | redirected-proof here, NOT an authority |
| L06 | pre-swap file-handle write | landed in observed object; sentinel untouched | anchored candidate (file-level; dir_fd variant `SKIPPED_NOT_SUPPORTED` on Windows CPython) |
| L07 | linked git worktrees | data roots DISTINCT, per-wt git dirs DISTINCT, **common dir SAME, objects dir SAME** | shared-Git-metadata resource domain is real |
| L08 | migration policy model (9 scenarios, INV1 = ≤1 active owner/resource) | only baseline-lexical and **delete-active-rows** migrations violate INV1 | drain→fence, mixed-rows typed refusal, rollback-block, UNKNOWN-refusal all safe |
| L09 | exhaustive 108-state model check | lexical-baseline **9 violations**; physical-conservative **0** | conservative policy satisfies the invariant within the modeled bounds |

## Key replay excerpts

Observer core (native id read; fallback documented — on THIS host `GetFileInformationByHandleEx(FileIdInfo)` failed for both dirs and files, so verdicts used the legacy `BY_HANDLE_FILE_INFORMATION` volume-serial+index pair, a valid within-volume comparator; `FileIdInfo` support remains volume-dependent → UNKNOWN policy still required in production):

```python
_kernel32.CreateFileW(path, FILE_READ_ATTRIBUTES,
    FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,
    None, OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None)   # dirs need BACKUP_SEMANTICS
info = _BY_HANDLE_FILE_INFORMATION()
_kernel32.GetFileInformationByHandle(handle, ctypes.byref(info))
legacy_id = (info.dwVolumeSerialNumber, info.nFileIndexHigh << 32 | info.nFileIndexLow)
# FileIdInfo(18) -> 128-bit id when supported; failure => legacy fallback
```

Broker RED (real authorities only; full probe `l02_broker_alias_red.py`):

```python
store = SQLiteWorkerLeaseStore(fresh_sacrificial_db)          # per case
store.try_acquire(request("s1", "t-s1", real_root),  candidate("a-worker-1", real_root),  lease_id="lease-s1", acquired_at=NOW_ISO)
store.try_acquire(request("s2", "t-s2", junction_alias), candidate("a-worker-2", junction_alias), ...)
# control same-spelling: MUTABLE_SCOPE_OVERLAP; alias spellings: both LEASED (2 active)
```

All commands bounded (≤ 60 s each; whole lab ≈ seconds). Every case got a fresh SQLite DB; no live table was read or written; junction/hardlink fixtures only ever targeted sacrificial local dirs and were removed before cleanup.

## Lexical-key writer/reader map (source, blob-pinned)

`windows_worktree_key` consumers at the pinned source: `registry.py` (definition + AssignmentRecord), `persistence.py` (assignments table column), `agent_change_packets.py` (snapshot/lease binding ×3), `continuity_guard.py` (snapshot↔lease key equality ×3), `control_center.py`, `lifecycle_assembly.py`, `parallel_ready_execution.py` (worktree identity check), `runtime_safety.py`, `runtime_setup.py`, `worker_candidate_assembly.py`, `worker_lease.py`, `zcode_production_assembly.py`. Migration must treat all of these as one authority family; the L08 model says: fence writers, refuse mixed rows, never delete active rows as "migration".

## Observer support table (Windows, this host)

| API | Result |
|---|---|
| CreateFileW dir open (backup semantics, share-all) | works |
| GetFileInformationByHandle (legacy 64-bit index) | works — verdict basis here |
| GetFileInformationByHandleEx FileIdInfo (128-bit) | **fails on this volume** → policy must treat as UNKNOWN-domain, not assume |
| os.open(directory) for dir_fd anchoring | PermissionError → `SKIPPED_NOT_SUPPORTED`; file-handle anchoring works |
| 8.3 short names | none generated on the temp volume |

Observer provenance rule honored: identity never comes from caller-supplied `verified=True`/`host_id`; the observer opens the object itself.

## Implementation-readiness matrix (decision inputs for the parent integrator)

| Slice | Likely source consumers | Status |
|---|---|---|
| Native observer adapter (typed SAME/DISTINCT/UNKNOWN, provenance from opened handle) | new adapter module + `worker_lease`/candidate assembly consumption | LAB-PROVEN on Windows (legacy-id basis); Mac uses Astra evidence; FileIdInfo-unsupported volumes must return UNKNOWN |
| Physical conflict reservation in lease store | `worker_lease.py` store conflict query + `persistence.py` schema | RED exists (L02); needs stopped-intake migration + version fence per L08; **new source claim required** |
| Scope projection validation (separators/dots/case/Unicode/ADS) | `graph/analyze.py` paths_overlap inputs | 10 gap classes enumerated (L04); fnmatch language must be preserved; **new source claim required** |
| Per-file/replace-aware footprint + anchored writer | future writer path | counterexamples + candidate demonstrated only (L05/L06); farthest from ready |
| Git common-metadata domain | `registry`/worktree adapters | domain map ready (L07); no reservation semantics designed yet |

Pending decisions for the integrator: (1) whether physical reservation lands in the existing lease store vs a reserved capacity row family; (2) whether UNKNOWN observations exclude mutation entirely or allow read-only; (3) migration fence sequencing (drain window length); (4) whether the observer is consulted at candidate assembly, lease acquire, or both.

## Limits (honest)

- This lab proves behavior on ONE Windows host/volume (NTFS, `%TEMP%`); SMB/ReFS/network shares are UNSUPPORTED and were not tested — no SMB claims are made from NTFS evidence.
- Legacy 64-bit file indexes are unique only within a volume and can be reused after deletion; the 128-bit API failed here — production must classify unsupported volumes as UNKNOWN.
- The anchored-writer demonstration is one file-level pattern on junctions, not a generic safe writer; `os.open(dir_fd=...)` anchoring is unsupported on Windows CPython.
- The L08/L09 models are policy abstractions over exactly the enumerated axes; they are not a whole-OS or whole-product model.
- Source and tests were never modified; nothing here accepts or implements ZRA-4; WO200/other lanes untouched.

## Verdict

**READY_FOR_PARENT_DESIGN_REVIEW** with the L02-class hazard reproduced natively on Windows, all conservative policies model-proven, and each implementation slice mapped to consumers + open decisions. Product implementation stays HOLD pending parent acceptance, ZRA-3 acceptance, and a fresh R3 source claim.
