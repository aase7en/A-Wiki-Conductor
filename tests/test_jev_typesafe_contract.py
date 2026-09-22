from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import jev_shadow_benchmark as shadow  # noqa: E402
import jev_typesafe_contract as contract  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "jev_shadow"
CASES = FIXTURES / "cases-expanded.jsonl"
QUESTIONS = FIXTURES / "typesafe_questions.json"


@pytest.fixture(scope="module")
def cases() -> list[shadow.BenchmarkCase]:
    return shadow.load_cases(CASES)


@pytest.fixture(scope="module")
def specs() -> dict[str, contract.QuestionSpec]:
    return contract.load_question_specs(QUESTIONS)


def get_case(
    cases: list[shadow.BenchmarkCase], case_id: str
) -> shadow.BenchmarkCase:
    return next(case for case in cases if case.case_id == case_id)


def test_expanded_corpus_is_balanced_unique_and_complete(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    assert len(cases) == 60
    assert len({case.case_id for case in cases}) == 60

    counts = Counter(case.decision_family for case in cases)
    assert counts == {
        "task_classification": 10,
        "skill_suggestion": 10,
        "failure_classification": 10,
        "review_severity": 10,
        "evidence_relevance": 10,
        "escalation_decision": 10,
    }
    assert set(specs) == set(counts)

    for case in cases:
        contract.validate_case_against_spec(case, specs[case.decision_family])


def test_all_expanded_cases_build_pinned_model_requests(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    manifest = contract.build_request_manifest(cases, specs)

    assert len(manifest) == 60
    for item in manifest:
        assert item["schema_version"] == contract.MANIFEST_SCHEMA_VERSION
        assert "expected" not in item
        assert "expected" not in item["request"]
        request = item["request"]
        assert request["model"] == contract.PINNED_BENCHMARK_MODEL
        assert set(request) == {"state", "model", "questions"}
        assert set(request["questions"]) == {contract.DEFAULT_QUESTION_ID}


def test_choice_request_matches_exact_family_criteria(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "taskx-001")
    spec = specs[case.decision_family]

    request = contract.build_typesafe_request(case, spec)
    question = request["questions"]["decision"]

    assert question["type"] == "choice"
    assert list(question["criteria"]) == list(case.options)
    assert question["instructions"].startswith("Classify")


def test_score_request_preserves_ordered_four_level_rubric(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "reviewx-003")
    spec = specs[case.decision_family]

    request = contract.build_typesafe_request(case, spec)
    question = request["questions"]["decision"]

    assert question["type"] == "score"
    assert len(question["criteria"]) == 4
    assert question["criteria"][0] == "No material defect."
    assert "Critical" in question["criteria"][3]


def test_noul_request_has_true_false_criteria_without_confidence_semantics(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "evidx-001")
    spec = specs[case.decision_family]

    request = contract.build_typesafe_request(case, spec)
    question = request["questions"]["decision"]

    assert question["type"] == "noul"
    assert set(question["criteria"]) == {"true", "false"}
    assert "confidence" not in question


@pytest.mark.parametrize("model", ["jev-latest", "jev-preview", "jev-1.13", "gpt-5.6"])
def test_benchmark_builder_rejects_moving_or_nonversioned_model_ids(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
    model: str,
) -> None:
    case = cases[0]

    with pytest.raises(
        contract.TypeSafeContractError,
        match="pinned versioned Jev model",
    ):
        contract.build_typesafe_request(
            case,
            specs[case.decision_family],
            model=model,
        )


def test_case_spec_mismatch_fails_closed(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "taskx-001")

    with pytest.raises(contract.TypeSafeContractError, match="decision family"):
        contract.build_typesafe_request(case, specs["failure_classification"])


def test_choice_response_normalizes_into_existing_provider_result(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "taskx-001")
    payload = {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "choice",
                "choice": "bugfix",
                "confidence": 0.91,
                "probabilities": {
                    "bugfix": 0.92,
                    "feature": 0.03,
                    "docs": 0.02,
                    "review": 0.03,
                },
            }
        },
        "usage": {"input_tokens": 392, "output_tokens": 40},
    }

    result = contract.normalize_typesafe_response(
        case,
        specs[case.decision_family],
        payload,
        elapsed_ms=120.0,
        input_price_per_million_usd=0.042,
    )

    assert result.answer == "bugfix"
    assert result.confidence == pytest.approx(0.91)
    assert result.input_tokens == 392
    assert result.output_tokens == 40
    assert result.cost_usd == pytest.approx(392 * 0.042 / 1_000_000)


def test_score_response_requires_legend_and_normalizes(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "reviewx-003")
    payload = {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "score",
                "score": 2.0,
                "confidence": 0.88,
                "legend": {
                    "0": "none",
                    "1": "minor",
                    "2": "material",
                    "3": "critical",
                },
                "probabilities": {
                    "0": 0.01,
                    "1": 0.05,
                    "2": 0.90,
                    "3": 0.04,
                },
            }
        },
        "usage": {"input_tokens": 410, "output_tokens": 44},
    }

    result = contract.normalize_typesafe_response(
        case,
        specs[case.decision_family],
        payload,
        elapsed_ms=130.0,
        input_price_per_million_usd=0.042,
    )

    assert result.answer == pytest.approx(2.0)
    assert result.confidence == pytest.approx(0.88)


def test_noul_response_has_probability_only_not_invented_confidence(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "evidx-001")
    payload = {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "noul",
                "noul": 0.94,
            }
        },
        "usage": {"input_tokens": 300, "output_tokens": 18},
    }

    result = contract.normalize_typesafe_response(
        case,
        specs[case.decision_family],
        payload,
        elapsed_ms=90.0,
        input_price_per_million_usd=0.042,
    )

    assert result.answer == pytest.approx(0.94)
    assert result.confidence is None
    assert result.probabilities is None


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda payload: payload.update({"model": "jev-1.14.0"}),
            "response model",
        ),
        (
            lambda payload: payload["answers"].update(
                {"extra": payload["answers"]["decision"]}
            ),
            "exactly the requested",
        ),
        (
            lambda payload: payload["answers"]["decision"].update(
                {"type": "score"}
            ),
            "answer type",
        ),
        (
            lambda payload: payload.update(
                {"usage": {"input_tokens": -1, "output_tokens": 10}}
            ),
            "non-negative integer",
        ),
    ],
)
def test_malformed_choice_responses_fail_closed(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
    mutator,
    message: str,
) -> None:
    case = get_case(cases, "taskx-001")
    payload = {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "choice",
                "choice": "bugfix",
                "confidence": 0.90,
                "probabilities": {
                    "bugfix": 0.90,
                    "feature": 0.05,
                    "docs": 0.03,
                    "review": 0.02,
                },
            }
        },
        "usage": {"input_tokens": 300, "output_tokens": 30},
    }
    mutator(payload)

    with pytest.raises(contract.TypeSafeContractError, match=message):
        contract.normalize_typesafe_response(
            case,
            specs[case.decision_family],
            payload,
            elapsed_ms=100.0,
            input_price_per_million_usd=0.042,
        )


def test_noul_response_rejects_invented_confidence(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "evidx-001")
    payload = {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "noul",
                "noul": 0.8,
                "confidence": 0.9,
            }
        },
        "usage": {"input_tokens": 200, "output_tokens": 10},
    }

    with pytest.raises(contract.TypeSafeContractError, match="must not invent"):
        contract.normalize_typesafe_response(
            case,
            specs[case.decision_family],
            payload,
            elapsed_ms=80.0,
            input_price_per_million_usd=0.042,
        )


def _choice_payload() -> dict:
    return {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "choice",
                "choice": "bugfix",
                "confidence": 0.91,
                "probabilities": {
                    "bugfix": 0.92,
                    "feature": 0.03,
                    "docs": 0.02,
                    "review": 0.03,
                },
            }
        },
        "usage": {"input_tokens": 392, "output_tokens": 40},
    }


def _score_payload() -> dict:
    return {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "score",
                "score": 2.0,
                "confidence": 0.88,
                "legend": {
                    "0": "none",
                    "1": "minor",
                    "2": "material",
                    "3": "critical",
                },
                "probabilities": {
                    "0": 0.01,
                    "1": 0.05,
                    "2": 0.90,
                    "3": 0.04,
                },
            }
        },
        "usage": {"input_tokens": 410, "output_tokens": 44},
    }


def _noul_payload() -> dict:
    return {
        "model": contract.PINNED_BENCHMARK_MODEL,
        "answers": {
            "decision": {
                "type": "noul",
                "noul": 0.94,
            }
        },
        "usage": {"input_tokens": 300, "output_tokens": 18},
    }


def _normalize(case: shadow.BenchmarkCase, spec, payload: dict):
    return contract.normalize_typesafe_response(
        case,
        spec,
        payload,
        elapsed_ms=100.0,
        input_price_per_million_usd=0.042,
    )


def test_strict_response_rejects_unknown_top_level_fields(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "taskx-001")
    payload = _choice_payload()
    payload["pricing"] = {"output_usd_per_million": 0.0}

    with pytest.raises(
        contract.TypeSafeContractError, match="top-level fields"
    ):
        _normalize(case, specs[case.decision_family], payload)


def test_strict_response_rejects_unknown_usage_fields(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "taskx-001")
    payload = _choice_payload()
    payload["usage"]["total_tokens"] = 432

    with pytest.raises(contract.TypeSafeContractError, match="usage fields"):
        _normalize(case, specs[case.decision_family], payload)


@pytest.mark.parametrize("extra", ["reasoning", "choice_label"])
def test_strict_choice_answer_rejects_unknown_fields(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
    extra: str,
) -> None:
    case = get_case(cases, "taskx-001")
    payload = _choice_payload()
    payload["answers"]["decision"][extra] = "because"

    with pytest.raises(
        contract.TypeSafeContractError, match="choice answer fields"
    ):
        _normalize(case, specs[case.decision_family], payload)


@pytest.mark.parametrize("extra", ["legend_rationale", "score_label"])
def test_strict_score_answer_rejects_unknown_fields(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
    extra: str,
) -> None:
    case = get_case(cases, "reviewx-003")
    payload = _score_payload()
    payload["answers"]["decision"][extra] = "note"

    with pytest.raises(
        contract.TypeSafeContractError, match="score answer fields"
    ):
        _normalize(case, specs[case.decision_family], payload)


def test_strict_noul_answer_rejects_unknown_fields_beyond_type_and_noul(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "evidx-001")
    payload = _noul_payload()
    payload["answers"]["decision"]["explanation"] = "aligned with claim"

    with pytest.raises(
        contract.TypeSafeContractError, match="noul answer fields"
    ):
        _normalize(case, specs[case.decision_family], payload)


@pytest.mark.parametrize(
    "legend",
    [
        {"0": 0, "1": "minor", "2": "material", "3": "critical"},
        {"0": "none", "1": 1, "2": "material", "3": "critical"},
        {"0": "none", "1": "minor", "2": 2.0, "3": "critical"},
        {"0": "none", "1": "minor", "2": "material", "3": True},
        {"0": "none", "1": "minor", "2": "material", "3": None},
    ],
)
def test_score_legend_values_must_be_strings(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
    legend: dict,
) -> None:
    case = get_case(cases, "reviewx-003")
    payload = _score_payload()
    payload["answers"]["decision"]["legend"] = legend

    with pytest.raises(
        contract.TypeSafeContractError, match="legend values must be strings"
    ):
        _normalize(case, specs[case.decision_family], payload)


def test_score_legend_keys_must_remain_exact_level_indices(
    cases: list[shadow.BenchmarkCase],
    specs: dict[str, contract.QuestionSpec],
) -> None:
    case = get_case(cases, "reviewx-003")
    payload = _score_payload()
    payload["answers"]["decision"]["legend"] = {
        "0": "none",
        "1": "minor",
        "2": "material",
        "3": "critical",
        "4": "beyond declared levels",
    }

    with pytest.raises(
        contract.TypeSafeContractError, match="legend keys must match"
    ):
        _normalize(case, specs[case.decision_family], payload)


def test_manifest_cli_is_deterministic_and_contains_no_expected_truth(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"

    count1 = contract.emit_request_manifest(CASES, QUESTIONS, first)
    count2 = contract.emit_request_manifest(CASES, QUESTIONS, second)

    assert count1 == count2 == 60
    assert first.read_bytes() == second.read_bytes()

    lines = first.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 60
    for line in lines:
        item = json.loads(line)
        assert "expected" not in item
        assert item["request"]["model"] == contract.PINNED_BENCHMARK_MODEL


def test_contract_module_has_no_network_environment_or_process_surface() -> None:
    source = (SCRIPTS / "jev_typesafe_contract.py").read_text(encoding="utf-8")
    forbidden = [
        "import requests",
        "import httpx",
        "import urllib",
        "import socket",
        "import subprocess",
        "os.environ",
        "getenv(",
        "Authorization",
        "Bearer ",
    ]

    for token in forbidden:
        assert token not in source


def test_question_specs_match_documented_primitive_limits(
    specs: dict[str, contract.QuestionSpec],
) -> None:
    for spec in specs.values():
        if spec.question_type == "choice":
            assert 2 <= len(spec.criteria) <= 255
        elif spec.question_type == "score":
            assert 2 <= len(spec.criteria) <= 10
        else:
            assert set(spec.criteria) == {"true", "false"}
