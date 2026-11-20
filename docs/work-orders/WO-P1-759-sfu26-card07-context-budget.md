# WO-P1-759 — SFU26 Card 07: Context Budget — Evidence Packing Projection

Identity schema: GITHUB_ISSUE_V1
Issue: #759
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (pure offline transformation; no egress/prompt change; no retrieval I/O; no token counting)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `76e0bd299b668933576b0c0a5bea9eebe4362396` (origin/main verified at bootstrap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo759-context`; branch `feat/wo759-context-budget`.
- Program authority: SFU26 roadmap card `CAND-SFU26-07` (cards 06/08/09 delivered; 07 is the last prerequisite of card 10).
- Exclusive files: NEW `src/a_conductor/evidence_pack_projection.py`, NEW `tests/test_evidence_pack_projection.py`, this WO. Everything else UNTOUCHED — in particular: `operator_protocol.py`/`operator_wire.py`/`operator_dispatch.py` (operator.v1 contract), `zero_relay*.py` identity modules, `orchestration.py` codec (orch-signal.v1 bounds are an R3 contract), `context_rollover_guard.py` — consume/import only.

## Verified Inputs (discovery 2026-11-15) — reuse map

- **No (source, span, sha) triple type exists today**; nearest: `DexArtifactDigest(ref, sha256, size_bytes)` (`dex_evidence.py:65-69`, list ≤16), `TaskPacketFile(task_contract_ref, path, sha256)` (`claude_code_harness.py:144-154`), `ResultIdentity` cross-binding (`zero_relay.py:80-105`). Card 07 defines the span field LOCALLY (no existing span type) keeping ref ≤256 printable-ASCII + 64-hex sha conventions.
- **Bounds conventions to mirror**: orchestration.py `SIZE_LIMIT=16384`/`_bounded_tree` pre-encode walk with typed `SIGNAL_*_EXCEEDED` (`:9-14,160-191`); `AgentResultPacket._text(max_length)` caps; monitor dropped/truncated accounting invariant (`monitor_projection.py:206-221`); evidence refs ≤16; canonical JSON `sort_keys, separators=(",",":"), ensure_ascii=True` (`orchestration.py:205`, `dex_evidence.py:61-62`); self-digest over canonical body minus digest field (`dex_evidence.py:163-166`).
- **Mandatory-facts precedents**: `GoalCloseoutFacts`/`CloseoutEvidenceBundle` (evidence never invented), operator.v1 `_ACTION_REQUIRED_FIELDS` (missing mandatory = typed error, no defaults), dispatch guard 1..12 evidence_refs fail-closed. **No abstain-on-overflow precedent exists** — card 07 composes monitor's count-the-loss (optional items) with typed ABSTAIN (mandatory set).
- **Same-path-different-SHA precedent**: `prepared_run_reconstruction._require_current_identity(..., unavailable_code, mismatch_code)` (`:340-363`).
- **Injection pattern**: card-08/09 snapshot-or-loader duck typing; AWC has ZERO retrieval I/O in src (verified) — canonical retrieval results arrive as injected data; A-Wiki read-only.
- **Token-counting prohibition**: `context_rollover_guard.py:3-4` — "does not measure ChatGPT tokens and never fabricates a remaining context percentage". Card 07 budgets are char/item/byte ONLY.

## Deliverables

1. **NEW pure module** (no clock/network/retrieval/store I/O; injected snapshot-or-loader per card-08/09; `now` injectable; frozen+slots; `non_authoritative` init=False pinned):
   - `PackedEvidenceItem(ref, sha256, size_bytes, span, mandatory: bool, source_revision, staleness ∈ {AVAILABLE, STALE, UNKNOWN})` — span locally typed (e.g. byte offsets start/end or line range; document choice).
   - `project_evidence_pack(items, *, budget, now=None) -> EvidencePackOutcome` carrying either a packed `EvidencePack` (self-digest via canonical JSON minus digest; input fingerprint sha256; per-item provenance preserved; dedup by (ref, sha256, span) identity with explicit `duplicate_count` accounting, never double-packed) or a typed abstain/degraded outcome:
     - mandatory items alone exceeding budget (byte or item cap) → `ABSTAIN` with reason `PACK_MANDATORY_BUDGET_EXCEEDED` (never clip mandatory);
     - optional overflow → packed with dropped accounting (`dropped_optional_count`, invariant with truncated flag, monitor-style);
     - malformed item (bad sha/ref/size/span/negative) → typed rejection of THAT item (or whole-input per severity — document choice; mandatory malformed → abstain or typed reject, never silently dropped);
     - duplicate identity → first wins + counted;
     - same (ref) with DIFFERENT sha256/span across items → typed conflict note (mismatch vocabulary), both retained or rejected per documented rule;
     - loader failure → typed degraded outcome, never exception escape (wrap ALL duck-typed attribute access — card-08/09 P2 lesson);
     - budgets: char/item/byte only; injectable with documented defaults; pre-encode walk style.
2. **NEW tests** (inline fixtures): budget edges (exact-at-cap, +1 over, mandatory-only-over); duplicate spans/identity dedup; same-path-different-SHA conflict; staleness carried; Thai + English item content recall through the pack (content is inert data — pack never parses/interprets; assert prompt-injection-looking content round-trips as opaque text with no field promotion); missing source revision → UNKNOWN typed; malformed items (bad hex, oversize ref, negative size, inverted span); loader raising → typed degraded; zero-provider-import + purity structural tests; self-digest determinism (same input → same digest; any field change → different digest); dropped-accounting invariant.

## Acceptance

- RED-first: ModuleNotFoundError + behavioral RED recorded verbatim.
- Per-file green: `tests/test_evidence_pack_projection.py`, regression neighbors `tests/test_orchestration.py`, `tests/test_skill_shortlist_projection.py`, `tests/test_work_order_identity.py` (incl. this WO); `python3 -m compileall -q src/a_conductor`; no npm changes; diff = 3 files only.
- Delivery gate: frozen local commit → independent review → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI (macOS capacity rerun precedent) → checkpoint + close on #759.

## Checkpoint

- 2026-11-15: lane bootstrapped @`76e0bd2`; issue #759; discovery + reuse map recorded; implementation pending.
- 2026-11-15: implementation lane COMPLETE (local commit only, NO push) — RED-first evidence + design decisions:

  **Phase 0 baselines (per-file pytest):** `tests/test_orchestration.py` 84 passed (0.58s); `tests/test_skill_shortlist_projection.py` 33 passed (0.22s); `tests/test_work_order_identity.py` 33 passed (0.26s). All unchanged post-delivery (84/33/33).

  **RED verbatim (two-step):** run 1 — tests authored first; `python3 -m pytest tests/test_evidence_pack_projection.py -q` → collection error, headline `ModuleNotFoundError: No module named 'a_conductor.evidence_pack_projection'`, `1 error in 0.28s`, 0 tests run. Run 2 — signature-only scaffold (full contract surface: constants + frozen-slots dataclasses; `project_evidence_pack` raises `NotImplementedError`) → `39 failed, 2 passed in 0.46s` (the 2 passes are the AST/runtime purity structural tests, legitimately green on the stdlib-only import graph). Disclosed test refinements after RED run 2, before GREEN, coverage unchanged: degraded-outcome `fingerprint` assertion `""` → `()` (type-stable record-tuple ledger); fixture helper guards non-str content when deriving default `size_bytes`.

  **Design decisions (documented in module docstring):**
  - *Span*: `EvidenceSpan(start, end)` — byte offsets into the referenced artifact, `end` exclusive, `0 <= start <= end`; inputs accept an `EvidenceSpan`, a 2-tuple, or a `{"start", "end"}` dict; inverted/negative/non-int → typed `EVIDENCE_SPAN_INVALID`.
  - *Budget defaults*: `DEFAULT_EVIDENCE_BUDGET = EvidenceBudget(max_chars=32768, max_items=16, max_bytes=16384)` (items mirrors orchestration `EVIDENCE_REF_LIMIT`, bytes mirrors `SIZE_LIMIT`); injectable; char/item/byte ONLY, no token measurement; pre-encode accounting over ACTUAL UTF-8 bytes/chars of content; declared `size_bytes` is validated carried provenance, never budget math; non-`EvidenceBudget`/negative caps → typed `DEGRADED BUDGET_INVALID`.
  - *Clipping policy*: none. Mandatory subset alone over any cap → `ABSTAIN PACK_MANDATORY_BUDGET_EXCEEDED` with sorted `exceeded_caps`; optional overflow dropped WHOLE with monitor-style invariant `truncated == (dropped_optional_count > 0)`.
  - *Dedup*: identity `(ref, sha256, span)`; first wins; `duplicate_count` accounts later occurrences; never double-packed.
  - *Conflict rule (documented retain/reject)*: same `ref` with differing sha256 and/or span → RETAIN BOTH + typed `EvidenceConflictNote` (`SHA256_MISMATCH` / `SPAN_MISMATCH`, deterministic ref-sorted order); conflicts never block packing — the pack is non-authoritative inert data and silent evidence loss is worse than over-retention.
  - *Malformed-item policy*: per-item typed rejection (not whole-input) for optional items; field-specific codes (`EVIDENCE_REF_INVALID` ≤256 printable-ASCII 33..126, `EVIDENCE_SHA256_INVALID` 64-lower-hex, `EVIDENCE_SIZE_INVALID` int-not-bool ≥0, `EVIDENCE_SPAN_INVALID`, `EVIDENCE_CONTENT_INVALID`); missing/unreadable required fields (incl. raising attribute access) → `EVIDENCE_ITEM_UNREADABLE`; malformed MANDATORY → `ABSTAIN PACK_MANDATORY_ITEM_MALFORMED` (never silent); invalid `mandatory` flag conservatively treated as mandatory-severity (abstain). Check order documented: unreadable → flag → ref → sha → size → span → content.
  - *Staleness*: carried injected input evidence, never computed; missing/invalid `source_revision` → staleness `UNKNOWN` + revision `None`; invalid staleness word → `UNKNOWN`; `now` accepted for call-site seam parity, intentionally unused in v1.
  - *Digest recipe (dex pattern)*: `EvidencePack.digest` = sha256 over canonical JSON (`sort_keys=True, separators=(",",":"), ensure_ascii=True`) of the pack body MINUS the digest field (body keys: `schema` `evidence.pack.v1`, `items`, `dropped_optional_count`, `truncated`, `duplicate_count`, `conflicts`; test reconstructs the body and re-derives the digest, pinning the recipe exactly). `EvidencePack.fingerprint` = sha256 over canonical normalized per-input records incl. `rejected`/`duplicate` statuses (any field change → different digest AND fingerprint); `EvidencePackOutcome.fingerprint` = the same records as a readable ledger tuple (empty tuple when input unnormalizable, e.g. loader failure).
  - *Duck-typed access*: ALL wrapped (card-08/09 P2 lesson) — loader/snapshot-or-sequence injection; loader raising / garbage return / unusable container (incl. dict, whose `.items` is a method) → typed `DEGRADED EVIDENCE_SNAPSHOT_UNAVAILABLE`, never an exception escape.
  - *Content opacity*: content round-trips byte-exactly, never parsed or promoted; the digest-recipe test pins the exact body/item key sets, proving prompt-injection-looking text exists only under `content`.

  **GREEN + regression:** `tests/test_evidence_pack_projection.py` 41 passed (0.24s); neighbors 84/33/33 (identical to Phase 0); `python3 -m compileall -q src/a_conductor` OK; `git status --porcelain` = exactly this WO + the 2 new in-scope files (zero modifications to existing files).
