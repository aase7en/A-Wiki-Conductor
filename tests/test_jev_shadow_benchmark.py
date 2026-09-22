from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import jev_shadow_benchmark as bench  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "jev_shadow"
CASES = FIXTURES / "cases.jsonl"
RESULTS = FIXTURES / "provider_results.json"


def choice_case(
    *,
    case_id: str = "case-1",
    expected: str = "safe",
    risk: str = "medium",
    min_confidence: float = 0.8,
) -> bench.BenchmarkCase:
    return bench.BenchmarkCase(
        case_id=case_id,
        decision_family="test_choice",
        question_type="choice",
        state={"request": "sanitized test request"},
        expected=expected,
        risk=risk,
        options=("safe", "danger"),
        min_confidence=min_confidence,
        baseline_latency_ms=1000.0,
        baseline_cost_usd=0.001,
    )


def choice_result(
    *,
    answer: str = "safe",
    confidence: float = 0.95,
    question_type: str = "choice",
    error: str | None = None,
    probabilities: dict[str, float] | None = None,
) -> dict[str, object]:
    if probabilities is None:
        probabilities = {"safe": 0.95, "danger": 0.05}
    return {
        "type": question_type,
        "answer": answer,
        "confidence": confidence,
        "probabilities": probabilities,
        "model": "fixture-test",
        "latency_ms": 100.0,
        "input_tokens": 100,
        "output_tokens": 10,
        "cost_usd": 0.00001,
        "retries": 0,
        **({"error": error} if error is not None else {}),
    }


def test_committed_fixture_corpus_exercises_all_six_decision_families() -> None:
    report = bench.run_fixture_benchmark(CASES, RESULTS)
    summary = report["summary"]

    assert report["schema_version"] == bench.REPORT_SCHEMA_VERSION
    assert report["mode"] == "offline_fixture"
    assert report["authoritative_for_production"] is False
    assert summary["total_cases"] == 6
    assert summary["valid_cases"] == 6
    assert summary["schema_failures"] == 0
    assert summary["provider_errors"] == 0
    assert summary["raw_accuracy"] == 1.0
    assert summary["auto_decisions"] == 5
    assert summary["auto_decision_accuracy"] == 1.0
    assert summary["high_risk_false_actions"] == 0
    assert summary["escalation_rate"] == pytest.approx(1 / 6)
    assert summary["frontier_call_avoidance_rate"] == pytest.approx(5 / 6)
    assert summary["comparison"]["p50_speedup_x"] > 10
    assert summary["comparison"]["p95_speedup_x"] > 10
    assert summary["comparison"]["cost_reduction_x"] > 10

    assert set(summary["families"]) == {
        "task_classification",
        "skill_suggestion",
        "failure_classification",
        "review_severity",
        "evidence_relevance",
        "escalation_decision",
    }

    skill = next(item for item in report["cases"] if item["case_id"] == "skill-001")
    assert skill["raw_correct"] is True
    assert skill["escalated"] is True


def test_high_risk_wrong_high_confidence_result_is_counted_as_false_action() -> None:
    case = choice_case(risk="high")
    provider = bench.FixtureProvider(
        {
            case.case_id: choice_result(
                answer="danger",
                confidence=0.99,
                probabilities={"safe": 0.01, "danger": 0.99},
            )
        }
    )

    report = bench.build_report([case], provider)
    summary = report["summary"]

    assert summary["raw_accuracy"] == 0.0
    assert summary["auto_decisions"] == 1
    assert summary["high_risk_false_actions"] == 1
    assert summary["frontier_call_avoidance_rate"] == 1.0


def test_low_confidence_choice_escalates_instead_of_auto_accepting() -> None:
    case = choice_case(min_confidence=0.8)
    provider = bench.FixtureProvider(
        {
            case.case_id: choice_result(
                answer="safe",
                confidence=0.55,
                probabilities={"safe": 0.58, "danger": 0.42},
            )
        }
    )

    outcome = bench.evaluate_case(case, provider)

    assert outcome.valid_response is True
    assert outcome.raw_correct is True
    assert outcome.escalated is True
    assert outcome.high_risk_false_action is False


def test_noul_review_band_escalates_even_when_raw_binary_answer_is_correct() -> None:
    case = bench.BenchmarkCase(
        case_id="noul-review",
        decision_family="test_noul",
        question_type="noul",
        state={"text": "sanitized"},
        expected=True,
        risk="medium",
        decision_threshold=0.5,
        review_band=(0.3, 0.7),
    )
    provider = bench.FixtureProvider(
        {
            case.case_id: {
                "type": "noul",
                "answer": 0.55,
                "model": "fixture-test",
                "latency_ms": 50.0,
            }
        }
    )

    outcome = bench.evaluate_case(case, provider)

    assert outcome.valid_response is True
    assert outcome.raw_correct is True
    assert outcome.escalated is True


def test_wrong_provider_result_type_fails_closed_as_schema_failure() -> None:
    case = choice_case()
    provider = bench.FixtureProvider(
        {
            case.case_id: choice_result(
                question_type="score",
                answer="safe",
            )
        }
    )

    report = bench.build_report([case], provider)
    item = report["cases"][0]

    assert report["summary"]["schema_failures"] == 1
    assert report["summary"]["auto_decisions"] == 0
    assert item["valid_response"] is False
    assert item["escalated"] is True
    assert "does not match" in item["schema_error"]


def test_probability_distribution_must_match_answer_space_and_sum_to_one() -> None:
    case = choice_case()
    provider = bench.FixtureProvider(
        {
            case.case_id: choice_result(
                probabilities={"safe": 0.60, "danger": 0.30},
            )
        }
    )

    outcome = bench.evaluate_case(case, provider)

    assert outcome.valid_response is False
    assert outcome.escalated is True
    assert outcome.schema_error == "probabilities must sum to 1"


def test_provider_error_and_missing_fixture_both_fail_safe_to_escalation() -> None:
    error_case = choice_case(case_id="provider-error")
    missing_case = choice_case(case_id="missing")
    provider = bench.FixtureProvider(
        {
            error_case.case_id: {
                "type": "choice",
                "answer": None,
                "model": "fixture-test",
                "latency_ms": 75.0,
                "error": "OVERLOADED",
            }
        }
    )

    report = bench.build_report([error_case, missing_case], provider)

    assert report["summary"]["provider_errors"] == 2
    assert report["summary"]["schema_failures"] == 0
    assert report["summary"]["auto_decisions"] == 0
    assert report["summary"]["frontier_call_avoidance_rate"] == 0.0
    assert all(item["escalated"] for item in report["cases"])


def test_case_loader_rejects_secret_shaped_state(tmp_path: Path) -> None:
    case_file = tmp_path / "cases.jsonl"
    case_file.write_text(
        json.dumps(
            {
                "schema_version": bench.CASE_SCHEMA_VERSION,
                "case_id": "secret",
                "decision_family": "test",
                "question": {"type": "choice", "options": ["a", "b"]},
                "state": {"message": "Authorization: Bearer " + ("x" * 26)},
                "expected": "a",
                "risk": "low",
                "policy": {"min_confidence": 0.8},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(bench.BenchmarkSchemaError, match="secret-shaped"):
        bench.load_cases(case_file)


def test_case_loader_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    raw = {
        "schema_version": bench.CASE_SCHEMA_VERSION,
        "case_id": "dup",
        "decision_family": "test",
        "question": {"type": "choice", "options": ["a", "b"]},
        "state": {"message": "sanitized"},
        "expected": "a",
        "risk": "low",
        "policy": {"min_confidence": 0.8},
    }
    case_file = tmp_path / "cases.jsonl"
    case_file.write_text(
        json.dumps(raw) + "\n" + json.dumps(raw) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(bench.BenchmarkSchemaError, match="duplicate case_id"):
        bench.load_cases(case_file)


def test_safe_report_never_serializes_raw_case_state() -> None:
    report = bench.run_fixture_benchmark(CASES, RESULTS)
    rendered = json.dumps(report, sort_keys=True)

    assert '"state"' not in rendered
    assert "After a refactor" not in rendered
    assert "TYPESAFE_API_KEY" not in rendered


def test_cli_can_write_deterministic_json_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"

    exit_code = bench.main(
        [
            "--cases",
            str(CASES),
            "--fixtures",
            str(RESULTS),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    first = json.loads(output.read_text(encoding="utf-8"))
    assert first["summary"]["total_cases"] == 6

    exit_code = bench.main(
        [
            "--cases",
            str(CASES),
            "--fixtures",
            str(RESULTS),
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    second = json.loads(output.read_text(encoding="utf-8"))
    assert second == first



@pytest.mark.parametrize(
    ("mutator", "expected_message"),
    [
        (lambda raw: raw.update(answer="unknown"), "choice answer must be a declared option"),
        (lambda raw: raw.update(confidence="high"), "confidence must be a finite number"),
        (lambda raw: raw.update(confidence=-0.1), "confidence must be between 0 and 1"),
        (lambda raw: raw.update(confidence=1.1), "confidence must be between 0 and 1"),
        (lambda raw: raw.update(latency_ms=-1.0), "latency_ms must be >= 0.0"),
        (lambda raw: raw.update(cost_usd=float("nan")), "cost_usd must be a finite number"),
        (lambda raw: raw.update(input_tokens=1.5), "tokens/retries must be non-negative integers"),
    ],
)
def test_malformed_provider_values_fail_closed(
    mutator, expected_message: str
) -> None:
    case = choice_case()
    raw = choice_result()
    mutator(raw)
    provider = bench.FixtureProvider({case.case_id: raw})

    outcome = bench.evaluate_case(case, provider)

    assert outcome.valid_response is False
    assert outcome.escalated is True
    assert outcome.high_risk_false_action is False
    assert expected_message in (outcome.schema_error or "")


def test_out_of_range_score_and_boolean_noul_fail_closed() -> None:
    score_case = bench.BenchmarkCase(
        case_id="score-invalid",
        decision_family="test_score",
        question_type="score",
        state={"text": "sanitized"},
        expected=1.0,
        risk="medium",
        score_levels=3,
        min_confidence=0.8,
    )
    noul_case = bench.BenchmarkCase(
        case_id="noul-invalid",
        decision_family="test_noul",
        question_type="noul",
        state={"text": "sanitized"},
        expected=True,
        risk="medium",
        decision_threshold=0.5,
        review_band=(0.3, 0.7),
    )
    provider = bench.FixtureProvider(
        {
            score_case.case_id: {
                "type": "score",
                "answer": 4.0,
                "confidence": 0.99,
                "probabilities": {"0": 0.0, "1": 0.0, "2": 1.0},
                "model": "fixture-test",
                "latency_ms": 50.0,
            },
            noul_case.case_id: {
                "type": "noul",
                "answer": True,
                "model": "fixture-test",
                "latency_ms": 50.0,
            },
        }
    )

    score_outcome = bench.evaluate_case(score_case, provider)
    noul_outcome = bench.evaluate_case(noul_case, provider)

    assert score_outcome.valid_response is False
    assert score_outcome.escalated is True
    assert "outside declared levels" in (score_outcome.schema_error or "")
    assert noul_outcome.valid_response is False
    assert noul_outcome.escalated is True
    assert "finite number" in (noul_outcome.schema_error or "")


def test_low_confidence_score_escalates() -> None:
    case = bench.BenchmarkCase(
        case_id="score-low-confidence",
        decision_family="test_score",
        question_type="score",
        state={"text": "sanitized"},
        expected=1.0,
        risk="medium",
        score_levels=3,
        min_confidence=0.8,
    )
    provider = bench.FixtureProvider(
        {
            case.case_id: {
                "type": "score",
                "answer": 1.0,
                "confidence": 0.45,
                "probabilities": {"0": 0.1, "1": 0.8, "2": 0.1},
                "model": "fixture-test",
                "latency_ms": 50.0,
            }
        }
    )

    outcome = bench.evaluate_case(case, provider)

    assert outcome.valid_response is True
    assert outcome.raw_correct is True
    assert outcome.escalated is True


def test_invalid_outcomes_do_not_improve_headline_performance_metrics() -> None:
    valid_case = choice_case(case_id="valid")
    missing_case = choice_case(case_id="missing")
    provider = bench.FixtureProvider(
        {
            valid_case.case_id: choice_result(),
        }
    )

    report = bench.build_report([valid_case, missing_case], provider)
    summary = report["summary"]

    assert summary["total_cases"] == 2
    assert summary["valid_cases"] == 1
    assert summary["provider_errors"] == 1
    assert summary["latency_ms"]["scope"] == "valid_responses"
    assert summary["latency_ms"]["measured_cases"] == 1
    assert summary["latency_ms"]["p50"] == 100.0
    assert summary["latency_ms"]["p95"] == 100.0
    assert summary["sequential_equivalent_throughput_per_sec"] == 10.0
    assert summary["cost_usd"]["scope"] == "valid_responses"
    assert summary["cost_usd"]["measured_cases"] == 1
    assert summary["cost_usd"]["per_1000_decisions"] == pytest.approx(0.01)
    assert summary["comparison"]["latency_population_matched"] is False
    assert summary["comparison"]["cost_population_matched"] is False
    assert summary["comparison"]["p50_speedup_x"] is None
    assert summary["comparison"]["p95_speedup_x"] is None
    assert summary["comparison"]["cost_reduction_x"] is None


def test_partial_baseline_coverage_disables_comparison_ratios() -> None:
    measured = choice_case(case_id="measured")
    unmeasured = bench.BenchmarkCase(
        case_id="unmeasured",
        decision_family="test_choice",
        question_type="choice",
        state={"request": "sanitized test request"},
        expected="safe",
        risk="medium",
        options=("safe", "danger"),
        min_confidence=0.8,
    )
    provider = bench.FixtureProvider(
        {
            measured.case_id: choice_result(),
            unmeasured.case_id: choice_result(),
        }
    )

    summary = bench.build_report([measured, unmeasured], provider)["summary"]

    assert summary["valid_cases"] == 2
    assert summary["baseline"]["latency_measured_cases"] == 1
    assert summary["baseline"]["cost_measured_cases"] == 1
    assert summary["comparison"]["latency_population_matched"] is False
    assert summary["comparison"]["cost_population_matched"] is False
    assert summary["comparison"]["p50_speedup_x"] is None
    assert summary["comparison"]["cost_reduction_x"] is None


def test_fixture_file_rejects_secret_shaped_provider_values(tmp_path: Path) -> None:
    fixture_file = tmp_path / "provider.json"
    fixture_file.write_text(
        json.dumps(
            {
                "case": {
                    "type": "choice",
                    "answer": "safe",
                    "model": "apikey_" + ("x" * 24),
                    "latency_ms": 10.0,
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(bench.BenchmarkSchemaError, match="secret-shaped"):
        bench.FixtureProvider.from_path(fixture_file)


def test_in_memory_secret_shaped_diagnostics_are_redacted_from_report() -> None:
    case = choice_case()
    provider = bench.FixtureProvider(
        {
            case.case_id: {
                **choice_result(),
                "model": "apikey_" + ("x" * 24),
                "type": "Bearer " + ("y" * 24),
            }
        }
    )

    report = bench.build_report([case], provider)
    rendered = json.dumps(report, sort_keys=True)

    assert "apikey_" not in rendered
    assert "Bearer " not in rendered
    assert report["cases"][0]["model"] == "[REDACTED_MODEL]"
    assert report["cases"][0]["schema_error"] == "[REDACTED_SCHEMA_ERROR]"


def test_score_tolerance_cannot_exceed_declared_span(tmp_path: Path) -> None:
    case_file = tmp_path / "cases.jsonl"
    case_file.write_text(
        json.dumps(
            {
                "schema_version": bench.CASE_SCHEMA_VERSION,
                "case_id": "wide-tolerance",
                "decision_family": "test",
                "question": {"type": "score", "levels": 3},
                "state": {"message": "sanitized"},
                "expected": 1.0,
                "tolerance": 5.0,
                "risk": "low",
                "policy": {"min_confidence": 0.8},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(bench.BenchmarkSchemaError, match="score span"):
        bench.load_cases(case_file)


@pytest.mark.parametrize(
    ("values", "percentile", "expected"),
    [
        ([100.0], 0.50, 100.0),
        ([10.0, 20.0], 0.50, 15.0),
        ([10.0, 20.0, 30.0, 40.0], 0.95, 38.5),
    ],
)
def test_percentile_is_deterministic(
    values: list[float], percentile: float, expected: float
) -> None:
    assert bench._percentile(values, percentile) == pytest.approx(expected)
