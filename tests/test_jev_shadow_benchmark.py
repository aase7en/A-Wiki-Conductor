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
