"""WO-P1-761 / SFU26 card 10: offline evaluation corpus + preregistration.

Covers the WO deliverable matrix against the NEW pure module
``a_conductor.eval_corpus`` (no network, no clock, seed injectable):

- exact counts (1,080 base + >=300 sentinels; per-cell/split/risk matrix)
- determinism (same seed -> identical manifest; different seed -> differs)
- leakage (calibration/holdout disjoint by id/content-hash/lineage;
  provider payload projection contains NO label/split/lineage fields)
- duplicate-lineage rejection
- typed errors for invalid seed/stratum/language/sentinel-count inputs
- Thai/English/mixed script detection per language cell
- sensitive-shape scan (no real credential shapes; sentinels use
  obviously-fake markers only)
- preregistration table completeness (every roadmap section 9.3 metric)
- purity (no provider/network/clock imports; no token counting)
- frozen + slots dataclasses
"""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
from pathlib import Path

import pytest

from a_conductor import eval_corpus as ec


# Roadmap section 9.3 metric rows (canonical slugs, one per table row).
SECTION_93_METRICS = (
    "verified_task_success",
    "route_correctness",
    "authority_false_action",
    "schema_failure_safety",
    "context_quality",
    "quality_delta",
    "telemetry_completeness",
    "latency",
    "financial_cost",
    "jev_acceleration_claims",
    "ux_performance",
)

# Secret-shape detectors reused (shape-compatible) from the READ-ONLY
# reference scripts/jev_shadow_benchmark.py: vocabulary compatibility only.
SECRET_PATTERNS = (
    re.compile(r"apikey_[A-Za-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
        r"\s*[:=]\s*[A-Za-z0-9+/=_-]{12,}",
        re.IGNORECASE,
    ),
)

THAI_RANGE = (0x0E00, 0x0E7F)


def _has_thai(text: str) -> bool:
    return any(THAI_RANGE[0] <= ord(ch) <= THAI_RANGE[1] for ch in text)


def _has_latin(text: str) -> bool:
    return any("a" <= ch.lower() <= "z" for ch in text)


@pytest.fixture(scope="module")
def corpus():
    return ec.build_corpus(seed=20261115)


@pytest.fixture(scope="module")
def base_cases(corpus):
    return tuple(c for c in corpus.cases if c.category is None)


@pytest.fixture(scope="module")
def sentinel_cases(corpus):
    return tuple(c for c in corpus.cases if c.category is not None)


# ---------------------------------------------------------------------------
# Strata vocabulary (roadmap section 9.1 enum note)
# ---------------------------------------------------------------------------


def test_strata_are_the_six_exact_corpus_strata():
    assert ec.STRATA == (
        "task_classification",
        "skill_suggestion",
        "tool_selection_research",
        "failure_classification",
        "evidence_relevance",
        "escalation_decision",
    )


def test_review_severity_is_not_a_stratum():
    # review_severity is the sixth SemanticDecisionFamily member but is
    # frontier-only per WO-P1-502; it must never appear as a stratum.
    assert "review_severity" not in ec.STRATA
    for case in ec.build_corpus(seed=7).cases:
        assert case.stratum in ec.STRATA


def test_languages_and_splits_vocabulary():
    assert ec.LANGUAGES == ("thai", "english", "mixed")
    assert ec.RISK_LEVELS == ("low", "medium", "high")
    assert ec.SPLITS == ("calibration", "holdout")


# ---------------------------------------------------------------------------
# Exact counts and matrix
# ---------------------------------------------------------------------------


def test_total_counts_exact(base_cases, sentinel_cases):
    assert len(base_cases) == 1080
    assert len(sentinel_cases) >= 300
    assert len(base_cases) + len(sentinel_cases) == 1080 + len(sentinel_cases)


def test_per_cell_counts_exact(base_cases):
    for stratum in ec.STRATA:
        for language in ec.LANGUAGES:
            cell = [
                c
                for c in base_cases
                if c.stratum == stratum and c.language == language
            ]
            assert len(cell) == 60, (stratum, language)
            cal = [c for c in cell if c.split == "calibration"]
            hold = [c for c in cell if c.split == "holdout"]
            assert len(cal) == 20
            assert len(hold) == 40


def test_per_cell_risk_matrix_exact(base_cases):
    expected_risk = {"low": 30, "medium": 15, "high": 15}
    expected_cal_risk = {"low": 10, "medium": 5, "high": 5}
    expected_hold_risk = {"low": 20, "medium": 10, "high": 10}
    for stratum in ec.STRATA:
        for language in ec.LANGUAGES:
            cell = [
                c
                for c in base_cases
                if c.stratum == stratum and c.language == language
            ]
            for risk, want in expected_risk.items():
                got = [c for c in cell if c.risk == risk]
                assert len(got) == want, (stratum, language, risk)
            for risk, want in expected_cal_risk.items():
                got = [
                    c
                    for c in cell
                    if c.risk == risk and c.split == "calibration"
                ]
                assert len(got) == want, (stratum, language, "cal", risk)
            for risk, want in expected_hold_risk.items():
                got = [
                    c
                    for c in cell
                    if c.risk == risk and c.split == "holdout"
                ]
                assert len(got) == want, (stratum, language, "hold", risk)


def test_global_split_and_language_holdout_totals(base_cases):
    cal = [c for c in base_cases if c.split == "calibration"]
    hold = [c for c in base_cases if c.split == "holdout"]
    assert len(cal) == 360
    assert len(hold) == 720
    for language in ec.LANGUAGES:
        lang_hold = [c for c in hold if c.language == language]
        assert len(lang_hold) == 240, language


def test_case_ids_unique(corpus):
    ids = [c.case_id for c in corpus.cases]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Sentinels
# ---------------------------------------------------------------------------


def test_sentinel_categories_and_counts(sentinel_cases):
    assert set(ec.SENTINEL_CATEGORIES) == {
        "unauthorized_action",
        "stale_claim",
        "missing_identity",
        "secret_synthetic_handling",
        "prompt_injection",
        "model_provider_schema_mismatch",
        "transport_ambiguity",
        "replay",
    }
    assert len(sentinel_cases) == ec.DEFAULT_SENTINEL_COUNT
    assert ec.DEFAULT_SENTINEL_COUNT >= 300
    for category in ec.SENTINEL_CATEGORIES:
        got = [c for c in sentinel_cases if c.category == category]
        assert len(got) >= 1, category


def test_sentinels_have_no_split_but_have_labels(sentinel_cases):
    for case in sentinel_cases:
        assert case.split is None
        assert case.label


def test_base_cases_have_no_category(base_cases):
    for case in base_cases:
        assert case.category is None


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_seed_byte_identical_manifest():
    a = ec.build_corpus(seed=424242)
    b = ec.build_corpus(seed=424242)
    assert ec.corpus_manifest_json(a) == ec.corpus_manifest_json(b)
    assert a.corpus_hash == b.corpus_hash


def test_same_seed_identical_cases():
    a = ec.build_corpus(seed=99)
    b = ec.build_corpus(seed=99)
    assert a.cases == b.cases


def test_different_seed_yields_different_manifest():
    a = ec.build_corpus(seed=1)
    b = ec.build_corpus(seed=2)
    assert a.corpus_hash != b.corpus_hash
    assert a.cases != b.cases


def test_manifest_hash_is_sha256_over_ordered_per_case_hashes(corpus):
    manifest = ec.corpus_manifest(corpus)
    ordered_hashes = [entry["content_hash"] for entry in manifest["cases"]]
    assert len(ordered_hashes) == len(corpus.cases)
    digest = hashlib.sha256("\n".join(ordered_hashes).encode("utf-8"))
    assert corpus.corpus_hash == digest.hexdigest()
    for entry, case in zip(manifest["cases"], corpus.cases):
        per_case = hashlib.sha256(case.content.encode("utf-8")).hexdigest()
        assert entry["content_hash"] == per_case
        assert entry["case_id"] == case.case_id


def test_content_hashes_unique():
    corpus = ec.build_corpus(seed=5)
    all_hashes = [
        hashlib.sha256(c.content.encode("utf-8")).hexdigest()
        for c in corpus.cases
    ]
    assert len(all_hashes) == len(set(all_hashes))


# ---------------------------------------------------------------------------
# Leakage
# ---------------------------------------------------------------------------


def test_splits_disjoint_by_id_content_and_lineage(corpus):
    cal = [c for c in corpus.cases if c.split == "calibration"]
    hold = [c for c in corpus.cases if c.split == "holdout"]
    cal_ids = {c.case_id for c in cal}
    hold_ids = {c.case_id for c in hold}
    assert cal_ids.isdisjoint(hold_ids)
    cal_hashes = {
        hashlib.sha256(c.content.encode("utf-8")).hexdigest() for c in cal
    }
    hold_hashes = {
        hashlib.sha256(c.content.encode("utf-8")).hexdigest() for c in hold
    }
    assert cal_hashes.isdisjoint(hold_hashes)
    cal_lineage = {c.lineage_id for c in cal}
    hold_lineage = {c.lineage_id for c in hold}
    assert cal_lineage.isdisjoint(hold_lineage)


def test_payload_projection_omits_label_split_lineage(corpus):
    allowed_keys = {"case_id", "decision_family", "risk", "content"}
    forbidden_markers = (
        "label",
        "expected",
        "ground_truth",
        "split",
        "lineage",
        "category",
        "sentinel",
    )
    for case in corpus.cases:
        payload = ec.provider_payload(case)
        keys = set(payload.keys())
        assert keys == allowed_keys, (case.case_id, keys)
        lowered = {key.lower() for key in keys}
        for marker in forbidden_markers:
            assert not any(marker in key for key in lowered), (
                case.case_id,
                marker,
            )


def test_payload_projection_values_carry_no_split_or_lineage_strings(corpus):
    for case in corpus.cases:
        payload = ec.provider_payload(case)
        assert case.split not in (payload["case_id"], payload["decision_family"])
        assert case.lineage_id not in json.dumps(
            payload, ensure_ascii=False
        )
        assert payload["decision_family"] == case.stratum


def test_manifest_records_lineage_and_label_but_payload_does_not(corpus):
    manifest = ec.corpus_manifest(corpus)
    entry = manifest["cases"][0]
    assert "lineage_id" in entry
    assert "label" in entry
    assert "split" in entry


# ---------------------------------------------------------------------------
# Duplicate lineage rejection
# ---------------------------------------------------------------------------


def test_duplicate_lineage_rejected():
    a = ec.EvalCase(
        case_id="x-1",
        stratum="task_classification",
        language="english",
        risk="low",
        split="calibration",
        lineage_id="ln:dupe",
        content="first",
        label="bugfix",
        category=None,
    )
    b = dataclasses.replace(a, case_id="x-2", content="second")
    with pytest.raises(ec.DuplicateLineageError):
        ec.check_lineage_uniqueness((a, b))


def test_whole_corpus_passes_lineage_uniqueness(corpus):
    ec.check_lineage_uniqueness(corpus.cases)


# ---------------------------------------------------------------------------
# Typed errors for invalid inputs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_seed", ["42", -1, True, None, 1.5])
def test_invalid_seed_typed_error(bad_seed):
    with pytest.raises(ec.InvalidSeedError):
        ec.build_corpus(seed=bad_seed)


def test_seed_zero_is_valid():
    corpus = ec.build_corpus(seed=0)
    assert corpus.seed == 0
    assert corpus.cases


def test_unknown_stratum_typed_error():
    with pytest.raises(ec.UnknownStratumError):
        ec.build_corpus(seed=3, strata=("task_classification", "bogus"))


def test_unknown_language_typed_error():
    with pytest.raises(ec.UnknownLanguageError):
        ec.build_corpus(seed=3, languages=("klingon",))


def test_unknown_stratum_error_lists_valid_options():
    with pytest.raises(ec.UnknownStratumError) as excinfo:
        ec.build_corpus(seed=3, strata=("nope",))
    assert "task_classification" in str(excinfo.value)


@pytest.mark.parametrize("bad_count", [0, -5, "many", 299.0])
def test_invalid_sentinel_count_typed_error(bad_count):
    with pytest.raises(ec.InvalidSentinelCountError):
        ec.build_corpus(seed=3, sentinel_count=bad_count)


def test_all_errors_share_typed_base():
    for error_type in (
        ec.InvalidSeedError,
        ec.UnknownStratumError,
        ec.UnknownLanguageError,
        ec.InvalidSentinelCountError,
        ec.DuplicateLineageError,
    ):
        assert issubclass(error_type, ec.EvalCorpusError)
        assert issubclass(ec.EvalCorpusError, ValueError)


def test_subset_generation_still_matrix_consistent():
    corpus = ec.build_corpus(
        seed=11,
        strata=("failure_classification",),
        languages=("thai",),
    )
    base = [c for c in corpus.cases if c.category is None]
    assert len(base) == 60
    assert len([c for c in base if c.split == "holdout"]) == 40


# ---------------------------------------------------------------------------
# Language script detection
# ---------------------------------------------------------------------------


def test_script_detection_per_language_cell(base_cases):
    for stratum in ec.STRATA:
        thai = [
            c
            for c in base_cases
            if c.stratum == stratum and c.language == "thai"
        ]
        english = [
            c
            for c in base_cases
            if c.stratum == stratum and c.language == "english"
        ]
        mixed = [
            c
            for c in base_cases
            if c.stratum == stratum and c.language == "mixed"
        ]
        assert thai and all(_has_thai(c.content) for c in thai), stratum
        assert english and all(
            not _has_thai(c.content) for c in english
        ), stratum
        assert mixed and all(
            _has_thai(c.content) and _has_latin(c.content) for c in mixed
        ), stratum


# ---------------------------------------------------------------------------
# Sensitive-shape cleanliness
# ---------------------------------------------------------------------------


def test_no_real_secret_shapes_in_any_content(corpus):
    for case in corpus.cases:
        for pattern in SECRET_PATTERNS:
            assert pattern.search(case.content) is None, (
                case.case_id,
                pattern.pattern,
            )


def test_no_real_secret_shapes_in_payload_projection(corpus):
    for case in corpus.cases:
        rendered = json.dumps(
            ec.provider_payload(case), ensure_ascii=False
        )
        for pattern in SECRET_PATTERNS:
            assert pattern.search(rendered) is None, case.case_id


def test_sentinels_use_obviously_fake_markers(sentinel_cases):
    fake = [c for c in sentinel_cases if c.category == "secret_synthetic_handling"]
    assert fake
    for case in fake:
        assert "SYNTHETIC-SECRET" in case.content
        for pattern in SECRET_PATTERNS:
            assert pattern.search(case.content) is None, case.case_id


# ---------------------------------------------------------------------------
# Preregistration table (roadmap section 9.3 as frozen data)
# ---------------------------------------------------------------------------


def test_preregistration_covers_every_section_93_metric():
    named = {entry.name for entry in ec.PREREGISTRATION}
    for metric in SECTION_93_METRICS:
        assert metric in named, metric


def test_preregistration_authority_false_action_is_no_go_trigger():
    entry = {e.name: e for e in ec.PREREGISTRATION}[
        "authority_false_action"
    ]
    assert "NO_GO" in entry.gate
    assert "zero" in entry.gate.lower() or "0" in entry.gate


def test_preregistration_quality_delta_rule():
    entry = {e.name: e for e in ec.PREREGISTRATION}["quality_delta"]
    assert "baseline" in entry.gate
    assert "2" in entry.gate


def test_preregistration_latency_percentiles():
    entry = {e.name: e for e in ec.PREREGISTRATION}["latency"]
    for token in ("p50", "p95", "p99"):
        assert token in entry.gate


def test_jev_acceleration_targets_marked_unproven():
    entry = {e.name: e for e in ec.PREREGISTRATION}["jev_acceleration_claims"]
    assert entry.status == "UNPROVEN_EXPERIMENT_TARGET"


def test_preregistration_sample_size_rationale_recorded():
    assert "300" in ec.SAMPLE_SIZE_RATIONALE
    assert "1%" in ec.SAMPLE_SIZE_RATIONALE
    assert "not proof" in ec.SAMPLE_SIZE_RATIONALE


def test_preregistration_entries_are_frozen_slots_records():
    assert ec.PreregistrationMetric.__slots__
    assert ec.PreregistrationMetric.__dataclass_params__.frozen
    entry = ec.PREREGISTRATION[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.name = "mutated"


# ---------------------------------------------------------------------------
# Purity
# ---------------------------------------------------------------------------


def _module_source() -> str:
    return Path(ec.__file__).read_text(encoding="utf-8")


def test_module_imports_are_pure():
    tree = ast.parse(_module_source())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    allowed = {
        "__future__",
        "dataclasses",
        "hashlib",
        "json",
        "random",
        "re",
        "typing",
    }
    assert imported, "module must import something to be scanned"
    assert imported <= allowed, imported - allowed


def test_no_token_counting():
    source = _module_source()
    assert not re.search(
        r"input_token|output_token|token_count|count_tokens|num_tokens|"
        r"tiktoken|encoding_for_model",
        source,
    )


def test_no_clock_usage():
    source = _module_source()
    assert "datetime" not in source
    assert "time.monotonic" not in source
    assert "time.time" not in source
    assert "perf_counter" not in source


# ---------------------------------------------------------------------------
# Frozen + slots records
# ---------------------------------------------------------------------------


def test_eval_case_frozen_and_slots(corpus):
    assert ec.EvalCase.__slots__
    assert ec.EvalCase.__dataclass_params__.frozen
    case = corpus.cases[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        case.label = "mutated"


def test_eval_corpus_frozen_and_slots(corpus):
    assert ec.EvalCorpus.__slots__
    assert ec.EvalCorpus.__dataclass_params__.frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        corpus.seed = 12345


def test_case_record_fields_present(corpus):
    case = corpus.cases[0]
    for field in (
        "case_id",
        "stratum",
        "language",
        "risk",
        "split",
        "lineage_id",
        "content",
        "label",
        "category",
    ):
        assert hasattr(case, field), field


def test_labels_present_and_separate_from_payload(corpus):
    for case in corpus.cases:
        assert isinstance(case.label, str) and case.label
        assert "label" not in ec.provider_payload(case)
