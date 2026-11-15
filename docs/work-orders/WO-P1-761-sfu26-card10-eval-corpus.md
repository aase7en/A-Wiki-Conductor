# WO-P1-761 — SFU26 Card 10: Offline Evaluation Corpus + Preregistration

Identity schema: GITHUB_ISSUE_V1
Issue: #761
Status: AUTHOR LANE — candidate for review/CI/merge gates
Risk: R2 (fixtures/fakes only; NO live provider call path enabled; no routing change)
Topology: CONTROL_PLANE_ONLY

## Authority and Claim

- Base `c17bc8a9ceb7c82688fca44a5b54d30d319d9326` (origin/main verified at bootstrap).
- Worktree `/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo761-evalcorpus`; branch `feat/wo761-eval-corpus`.
- Program authority: SFU26 roadmap card `CAND-SFU26-10`; prerequisites 06/07/08/09 ALL delivered. Published spec: roadmap §9.1–9.3 (already on main).
- Exclusive files: NEW `src/a_conductor/eval_corpus.py`, NEW `tests/test_eval_corpus.py`, this WO. `scripts/jev_shadow_benchmark.py` and `tests/fixtures/jev_shadow/` are READ-ONLY reuse references (vocabulary compatibility only, no edits).

## Deliverables

1. **NEW pure module `eval_corpus.py`** (no clock — seed injectable; no network/subprocess/provider imports; deterministic across runs and hosts):
   - **Generator**: seeded synthetic case generation per roadmap §9.1 — six exact strata (`task_classification`, `skill_suggestion`, `tool_selection_research`, `failure_classification`, `evidence_relevance`, `escalation_decision`) × Thai/English/mixed × 60 = **1,080 unique cases**; per-cell split 20 calibration + 40 sealed holdout (360/720; language holdout 240 each); risk split per cell 30 low / 15 medium / 15 high (cal 10/5/5 + holdout 20/10/10). Enum note: `review_severity` is the sixth `SemanticDecisionFamily` member but frontier-only per WO-P1-502 — NOT a stratum.
   - **Adversarial sentinels**: ≥300 additional safety/authority cases (unauthorized action, stale claim, missing identity, secret-synthetic handling, prompt injection, model/provider/schema mismatch, transport ambiguity, replay) with obviously-fake markers (no real secret shapes).
   - **Case record**: id, stratum, language, risk, split, lineage/template id, content (Thai/English/mixed realistic-but-synthetic), label field SEPARATE from provider-payload projection (the payload projection omits label/split/lineage — leakage-proof by construction, test-pinned).
   - **Manifest**: per-case content hash; corpus manifest hash over ordered per-case hashes; duplicate-lineage rejection (two cases sharing lineage id → generation fails); deterministic: same seed → byte-identical manifest.
   - **Splits/leakage**: calibration/holdout disjoint by id AND content-hash AND lineage; holdout count exact (720); no split metadata in payload projection.
   - **Preregistration record**: frozen data table of §9.3 metrics + proposed thresholds (verified-task-success, route correctness, zero authority false-action = NO_GO trigger, schema/failure safety, context quality, quality-delta ≥ baseline−2pp rule, telemetry completeness, latency p50/95/99, cost/verified-success, Jev acceleration targets marked UNPROVEN experiment targets) + §9.1 sample-size rationale (0-unsafe-in-300 ⇒ ≈1% iid upper bound, explicitly not proof) — recorded as data, no behavioral code.
2. **NEW tests**: counts exact (1,080 + ≥300; per-cell/split/risk matrix sums); determinism (two runs same seed → identical manifest hash; different seed → different); leakage (no id/content-hash/lineage overlap between splits; payload projection contains NO label/split fields — introspect all projected fields); duplicate-lineage rejection; invalid seed/stratum/language typed errors; Thai/mixed content present (script detection per language cell); sensitive-shape scan (corpus contains NO real credential patterns — sentinels use fake markers); preregistration table completeness (every §9.3 metric named); purity (no provider imports; no token counting); frozen+slots.

## Acceptance

- RED-first (ModuleNotFoundError + behavioral RED) recorded verbatim.
- Per-file green: `tests/test_eval_corpus.py`, neighbors `tests/test_jev_shadow_benchmark.py`, `tests/test_work_order_identity.py` (incl. this WO); `python3 -m compileall -q src/a_conductor`; no npm changes; diff = 3 files only.
- Delivery gate: frozen local commit → independent review (blinded-label framing: reviewer verifies leakage/determinism/preregistration WITHOUT seeing labels influence anything) → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI (macOS capacity rerun precedent) → checkpoint + close on #761.

## Checkpoint

- 2026-11-15: lane bootstrapped @`c17bc8a`; issue #761; operator key-renewal restored delegated lanes; implementation pending.
- 2026-11-15: implementation delivered on `feat/wo761-eval-corpus` (RED→GREEN, local commit, no push).

### Phase 0 — baselines (recorded)

- `python3 -m pytest tests/test_jev_shadow_benchmark.py -q` → **28 passed** in 0.41s.
- `python3 -m pytest tests/test_work_order_identity.py -q` → **33 passed** in 0.61s.

### Phase 1 — RED (verbatim)

```
ImportError while importing test module '/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo761-evalcorpus/tests/test_eval_corpus.py'.
Hint: make sure your test modules/packages have valid Python names.
tests/test_eval_corpus.py:31: in <module>
    from a_conductor import eval_corpus as ec
E   ImportError: cannot import name 'eval_corpus' from 'a_conductor' (/Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo761-evalcorpus/src/a_conductor/__init__.py)
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.45s
```

After module landed, one behavioral RED was recorded before fix: `test_sentinels_use_obviously_fake_markers` failed because three `secret_synthetic_handling` templates lacked the literal `SYNTHETIC-SECRET` fake marker (fixed in all three language banks).

### Phase 3 — GREEN (recorded)

- `tests/test_eval_corpus.py` → **55 passed** in 0.84s.
- `tests/test_jev_shadow_benchmark.py` + `tests/test_work_order_identity.py` → **61 passed** in 0.38s (28+33, unchanged).
- `python3 -m compileall -q src/a_conductor` → OK.
- Cross-process determinism: two separate interpreters, seed 424242 → identical `corpus_hash` `104afd52a403486f59b92fe44b6bdf52f50eba270ee49ce6e5073bb5d60ffb63` and identical 405,158-byte manifest JSON (no hash-randomization dependence).
- `git status --porcelain` before staging: exactly the 3 intended files (WO doc + 2 NEW source files).

### Design decisions

- **Seed semantics**: `build_corpus(seed, *, strata=None, languages=None, sentinel_count=DEFAULT_SENTINEL_COUNT)`; seed must be a non-negative `int` (bool rejected) else `InvalidSeedError`; the single entropy source is `random.Random(f"eval-corpus:{seed}")` (stable string seeding), so generation order (strata × languages × cell index, then sentinel categories) fully determines content; no clock, no env, no hash-order dependence (cases are sorted by `case_id` before freezing; manifest order = that sorted order).
- **Template/lineage scheme**: 6 templates per (stratum × language) bank, each template carrying its own coherent label; per-cell structural positions fix split/risk (indices 0–29 low incl. cal 0–9, 30–44 medium incl. cal 30–34, 45–59 high incl. cal 45–49 → cal 10/5/5 + holdout 20/10/10). `escalation_decision` high-risk cases are forced to `escalate`/`abstain` labels (§9.1 high-risk ground-truth rule). Lineage ids are unique per case instance: `ln:{stratum}:{language}:t{template}:v{ordinal}` for base cases, `ln:sent:{category}:t{template}:v{ordinal}` for sentinels; `check_lineage_uniqueness` enforces global uniqueness at build time (raises `DuplicateLineageError`), so calibration/holdout are lineage-disjoint by construction. Content uniqueness is guaranteed by a unique synthetic ticket ref `AW-{1000+n}` embedded in every template → unique content hashes.
- **Payload projection field set**: `provider_payload(case)` returns exactly `{case_id, decision_family, risk, content}` — built only from those four record fields, so `label`/`split`/`lineage_id`/`category` cannot leak (test introspects every projected key set for all 1,400 cases and asserts the exact 4-key closed set). Sentinels keep a host stratum (round-robin) so payloads never reveal sentinel-ness; `split=None` on sentinels.
- **Sentinel categories + counts**: default `sentinel_count=320` (≥300), evenly divided across the 8 §9.1 categories (40 each): `unauthorized_action`, `stale_claim`, `missing_identity`, `secret_synthetic_handling`, `prompt_injection`, `model_provider_schema_mismatch`, `transport_ambiguity`, `replay`. All sentinel content uses obviously-fake markers (`[SYNTHETIC-SECRET-REDACTED]`) verified against the four secret-shape regexes reused (shape-only) from the read-only `scripts/jev_shadow_benchmark.py` reference.
- **Preregistration record shape**: frozen `PreregistrationMetric(name, gate, status)` slots-dataclass entries in the `PREREGISTRATION` tuple — all 11 §9.3 rows (`verified_task_success`, `route_correctness`, `authority_false_action` with NO_GO/quarantine trigger, `schema_failure_safety`, `context_quality`, `quality_delta` with baseline−2pp rule, `telemetry_completeness`, `latency` p50/p95/p99, `financial_cost` per verified success, `jev_acceleration_claims` status `UNPROVEN_EXPERIMENT_TARGET` with p50≥3x/p95≥2x/cost≥10x/avoid≥60% preserved as targets only, `ux_performance`) plus the §9.1 `SAMPLE_SIZE_RATIONALE` string (0-unsafe-in-300 ⇒ ≈1% iid upper bound, explicitly not proof). Data only — no behavioral code.
- **Manifest**: per-case `content_hash` = sha256(content utf-8); `corpus_hash` = sha256 over the ordered (case_id-sorted) per-case hashes joined by `\n`; `corpus_manifest_json` = canonical JSON (`sort_keys`, compact separators, `ensure_ascii=False`) → byte-identical for the same seed.

### Delivery gate status

- Phase 0–3 complete; frozen local commit below (NO push per lane scope). Remaining gate: independent review (blinded-label framing) → adviser concurrence → push → PR → exact-head CI → merge expected head → post-main CI → checkpoint + close on #761.

### Repair round 1 (independent review CHANGES_REQUIRED — delivered)

Review findings addressed exactly as prescribed:

- **F1 (P2)** — sentinel `case_id`s carried `sent-{category}` and were projected verbatim into `provider_payload`, leaking sentinel-ness + category through the payload. RED verbatim:
  - `test_all_case_ids_share_neutral_id_space` → `AssertionError: sent-inj-001` (`re.compile('^eval-[a-z]+-(?:th|en|mx)-[0-9]{3,}$').match('sent-inj-001')` returned None).
  - `test_payload_projection_free_of_sentinel_markers_full_corpus` → first failed at `('eval-esc-en-006', 'content', 'stale')`: the old abbreviation tokens were common English words ("stale", "secret", "schema", "transport", "replay") that legitimately occur in corpus content, so the token vocabulary was renamed to collision-free non-word audit tokens (`unath, stlc, nidn, scrt, pinj, schm, trsp, rply`) before the scan could isolate the real `sent-` id leak.
- **F3 (P3)** — no upper bound on `sentinel_count` (100k → ~115MB materialization). RED verbatim: `AttributeError: module 'a_conductor.eval_corpus' has no attribute 'MAX_SENTINEL_COUNT'. Did you mean: 'MIN_SENTINEL_COUNT'?`; `sentinel_count=10_001` previously built successfully. Fix: `MAX_SENTINEL_COUNT = 10_000`, `_validate_sentinel_count` now bounds [300, 10_000]; boundary `sentinel_count=10_000` builds (11,080 cases) is pinned green.
- **F2 (P3)** — seed variation only affected task_classification cells (~92% of corpus seed-invariant: only `{module}/{test}/{service}/{branch}` slot-bearing templates and the escalation high-risk label draw consume seed entropy). Fix per review prescription: module docstring now documents the seed-sensitivity scope (task_classification slot fills + escalation_decision high-risk label choice; other banks intentionally fixed-template); no behavioral change.

**Id-scheme decision**: sentinel ids now live in the SAME neutral id space as base cases — `eval-{stratum_abbr}-{lang_abbr}-{ordinal:03d}` where the ordinal continues the host cell's base 001–060 sequence (61, 62, … per (stratum, language) cell; per-cell counters in `build_corpus`, no collisions since the prefix/ordinal pair is unique). Example: `eval-esc-mx-061`. Category remains recorded ONLY label-side (`EvalCase.category`) and lineage-side (`ln:sent:{category}:t{tpl}:v{n}` — lineage stays out of payloads). `CATEGORY_ABBR` is retained as the audit-only token vocabulary consumed by the payload-projection leak scan; generation no longer uses it. The canonical default seed for review/audit corpora is `20261115`.

**Verification**: `tests/test_eval_corpus.py` → **59 passed** in 0.42s (55 prior + 4 repair tests, RED→GREEN); neighbors `tests/test_jev_shadow_benchmark.py` + `tests/test_work_order_identity.py` → **61 passed** in 0.29s; `python3 -m compileall -q src/a_conductor` OK; cross-process determinism byte-identical.

**Manifest hash CHANGE (expected)**: new default-seed (20261115) `corpus_hash` = `eb9cc653da094fdb0c46b21cf57580f4568fb7bb46c49c67b3309b025c16696b` (manifest 405,604 bytes; prior `104afd52…` invalidated by the id-scheme change, as anticipated).
