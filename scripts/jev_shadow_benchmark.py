from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


CASE_SCHEMA_VERSION = "jev-shadow.case.v1"
REPORT_SCHEMA_VERSION = "jev-shadow.report.v1"
QUESTION_TYPES = frozenset({"choice", "score", "noul"})
RISK_LEVELS = frozenset({"low", "medium", "high"})

_SECRET_PATTERNS = (
    re.compile(r"apikey_[A-Za-z0-9]{16,}", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{16,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{16,}", re.IGNORECASE),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)"
        r"\s*[:=]\s*[A-Za-z0-9+/=_-]{12,}",
        re.IGNORECASE,
    ),
)


class BenchmarkSchemaError(ValueError):
    """Raised when a benchmark case or provider result violates the harness contract."""


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    decision_family: str
    question_type: str
    state: Any
    expected: Any
    risk: str
    options: tuple[str, ...] = ()
    score_levels: int | None = None
    min_confidence: float | None = None
    decision_threshold: float | None = None
    review_band: tuple[float, float] | None = None
    tolerance: float = 0.0
    baseline_latency_ms: float | None = None
    baseline_cost_usd: float | None = None


@dataclass(frozen=True)
class ProviderResult:
    question_type: str
    answer: Any
    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    retries: int = 0
    confidence: float | None = None
    probabilities: Mapping[str, float] | None = None
    error: str | None = None


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    decision_family: str
    question_type: str
    risk: str
    model: str
    valid_response: bool
    schema_error: str | None
    provider_error: str | None
    raw_correct: bool | None
    escalated: bool
    high_risk_false_action: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    retries: int
    baseline_latency_ms: float | None
    baseline_cost_usd: float | None


class BenchmarkProvider(Protocol):
    def evaluate(self, case: BenchmarkCase) -> ProviderResult:
        ...


class FixtureProvider:
    """Deterministic provider backed by committed, sanitized fixture results."""

    def __init__(self, results: Mapping[str, Mapping[str, Any]]) -> None:
        self._results = dict(results)

    @classmethod
    def from_path(cls, path: Path) -> "FixtureProvider":
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise BenchmarkSchemaError("fixture provider file must contain an object")
        if _contains_secret_shape(data):
            raise BenchmarkSchemaError(
                "fixture provider file contains a secret-shaped value"
            )
        return cls(data)

    def evaluate(self, case: BenchmarkCase) -> ProviderResult:
        raw = self._results.get(case.case_id)
        if raw is None:
            return ProviderResult(
                question_type=case.question_type,
                answer=None,
                model="fixture-missing",
                latency_ms=0.0,
                error="MISSING_FIXTURE",
            )
        if not isinstance(raw, Mapping):
            return ProviderResult(
                question_type=case.question_type,
                answer=None,
                model="fixture-invalid",
                latency_ms=0.0,
                error="INVALID_FIXTURE_RECORD",
            )
        return _provider_result_from_mapping(raw)


def _contains_secret_shape(value: Any) -> bool:
    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    if isinstance(value, Mapping):
        return any(
            _contains_secret_shape(key) or _contains_secret_shape(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_secret_shape(item) for item in value)
    return False


def _require_finite_number(value: Any, *, field: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise BenchmarkSchemaError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise BenchmarkSchemaError(f"{field} must be a finite number")
    if minimum is not None and number < minimum:
        raise BenchmarkSchemaError(f"{field} must be >= {minimum}")
    return number


def _require_probability(value: Any, *, field: str) -> float:
    number = _require_finite_number(value, field=field)
    if not 0.0 <= number <= 1.0:
        raise BenchmarkSchemaError(f"{field} must be between 0 and 1")
    return number


def _optional_nonnegative_number(raw: Mapping[str, Any], key: str) -> float | None:
    value = raw.get(key)
    if value is None:
        return None
    return _require_finite_number(value, field=key, minimum=0.0)


def _case_from_mapping(raw: Mapping[str, Any]) -> BenchmarkCase:
    if raw.get("schema_version") != CASE_SCHEMA_VERSION:
        raise BenchmarkSchemaError(
            f"schema_version must be {CASE_SCHEMA_VERSION!r}"
        )

    case_id = raw.get("case_id")
    decision_family = raw.get("decision_family")
    risk = raw.get("risk")
    question = raw.get("question")
    policy = raw.get("policy", {})
    baseline = raw.get("baseline", {})

    if not isinstance(case_id, str) or not case_id.strip():
        raise BenchmarkSchemaError("case_id must be a non-empty string")
    if not isinstance(decision_family, str) or not decision_family.strip():
        raise BenchmarkSchemaError("decision_family must be a non-empty string")
    if risk not in RISK_LEVELS:
        raise BenchmarkSchemaError(f"risk must be one of {sorted(RISK_LEVELS)}")
    if not isinstance(question, Mapping):
        raise BenchmarkSchemaError("question must be an object")
    if not isinstance(policy, Mapping):
        raise BenchmarkSchemaError("policy must be an object")
    if not isinstance(baseline, Mapping):
        raise BenchmarkSchemaError("baseline must be an object")

    question_type = question.get("type")
    if question_type not in QUESTION_TYPES:
        raise BenchmarkSchemaError(
            f"question.type must be one of {sorted(QUESTION_TYPES)}"
        )

    state = raw.get("state")
    if _contains_secret_shape(state):
        raise BenchmarkSchemaError(f"{case_id}: state contains a secret-shaped value")

    expected = raw.get("expected")
    options: tuple[str, ...] = ()
    score_levels: int | None = None
    min_confidence: float | None = None
    decision_threshold: float | None = None
    review_band: tuple[float, float] | None = None
    tolerance = 0.0

    if question_type == "choice":
        raw_options = question.get("options")
        if (
            not isinstance(raw_options, list)
            or len(raw_options) < 2
            or any(not isinstance(item, str) or not item for item in raw_options)
        ):
            raise BenchmarkSchemaError("choice question.options must contain >=2 strings")
        if len(set(raw_options)) != len(raw_options):
            raise BenchmarkSchemaError("choice question.options must be unique")
        options = tuple(raw_options)
        if expected not in options:
            raise BenchmarkSchemaError("choice expected must be one declared option")
        if "min_confidence" in policy:
            min_confidence = _require_probability(
                policy["min_confidence"], field="policy.min_confidence"
            )
    elif question_type == "score":
        score_levels_raw = question.get("levels")
        if (
            isinstance(score_levels_raw, bool)
            or not isinstance(score_levels_raw, int)
            or not 2 <= score_levels_raw <= 10
        ):
            raise BenchmarkSchemaError("score question.levels must be an integer from 2 to 10")
        score_levels = score_levels_raw
        expected = _require_finite_number(expected, field="expected")
        if not 0.0 <= expected <= float(score_levels - 1):
            raise BenchmarkSchemaError("score expected is outside declared levels")
        tolerance = _require_finite_number(
            raw.get("tolerance", 0.0), field="tolerance", minimum=0.0
        )
        if tolerance > float(score_levels - 1):
            raise BenchmarkSchemaError(
                "score tolerance cannot exceed the declared score span"
            )
        if "min_confidence" in policy:
            min_confidence = _require_probability(
                policy["min_confidence"], field="policy.min_confidence"
            )
    else:
        if not isinstance(expected, bool):
            raise BenchmarkSchemaError("noul expected must be boolean")
        decision_threshold = _require_probability(
            policy.get("decision_threshold", 0.5),
            field="policy.decision_threshold",
        )
        raw_band = policy.get("review_band")
        if (
            not isinstance(raw_band, list)
            or len(raw_band) != 2
        ):
            raise BenchmarkSchemaError(
                "noul policy.review_band must be [lower, upper]"
            )
        lower = _require_probability(raw_band[0], field="policy.review_band[0]")
        upper = _require_probability(raw_band[1], field="policy.review_band[1]")
        if lower > upper:
            raise BenchmarkSchemaError("noul review band lower must be <= upper")
        review_band = (lower, upper)

    baseline_latency_ms = _optional_nonnegative_number(baseline, "latency_ms")
    baseline_cost_usd = _optional_nonnegative_number(baseline, "cost_usd")

    return BenchmarkCase(
        case_id=case_id,
        decision_family=decision_family,
        question_type=question_type,
        state=state,
        expected=expected,
        risk=risk,
        options=options,
        score_levels=score_levels,
        min_confidence=min_confidence,
        decision_threshold=decision_threshold,
        review_band=review_band,
        tolerance=tolerance,
        baseline_latency_ms=baseline_latency_ms,
        baseline_cost_usd=baseline_cost_usd,
    )


def load_cases(path: Path) -> list[BenchmarkCase]:
    cases: list[BenchmarkCase] = []
    seen: set[str] = set()
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BenchmarkSchemaError(
                f"{path}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(raw, Mapping):
            raise BenchmarkSchemaError(
                f"{path}:{line_number}: case must be an object"
            )
        case = _case_from_mapping(raw)
        if case.case_id in seen:
            raise BenchmarkSchemaError(f"duplicate case_id: {case.case_id}")
        seen.add(case.case_id)
        cases.append(case)
    if not cases:
        raise BenchmarkSchemaError("benchmark corpus is empty")
    return cases


def _provider_result_from_mapping(raw: Mapping[str, Any]) -> ProviderResult:
    question_type = raw.get("type")
    if not isinstance(question_type, str):
        question_type = ""
    model = raw.get("model", "fixture")
    if not isinstance(model, str) or not model:
        model = "fixture-invalid"

    latency_ms = raw.get("latency_ms", 0.0)
    if isinstance(latency_ms, bool) or not isinstance(latency_ms, (int, float)):
        latency_ms = float("nan")

    def _integer(name: str) -> int:
        value = raw.get(name, 0)
        if isinstance(value, bool) or not isinstance(value, int):
            return -1
        return value

    cost = raw.get("cost_usd", 0.0)
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        cost = float("nan")

    confidence = raw.get("confidence")
    if confidence is not None and (
        isinstance(confidence, bool) or not isinstance(confidence, (int, float))
    ):
        confidence = float("nan")

    probabilities = raw.get("probabilities")
    if probabilities is not None and not isinstance(probabilities, Mapping):
        probabilities = {"__invalid__": float("nan")}

    error = raw.get("error")
    if error is not None and not isinstance(error, str):
        error = "INVALID_ERROR_FIELD"

    return ProviderResult(
        question_type=question_type,
        answer=raw.get("answer"),
        model=model,
        latency_ms=float(latency_ms),
        input_tokens=_integer("input_tokens"),
        output_tokens=_integer("output_tokens"),
        cost_usd=float(cost),
        retries=_integer("retries"),
        confidence=float(confidence) if confidence is not None else None,
        probabilities=probabilities,
        error=error,
    )


def _validate_probabilities(
    probabilities: Mapping[str, float] | None,
    *,
    expected_keys: Sequence[str],
) -> None:
    if probabilities is None:
        raise BenchmarkSchemaError("probabilities are required")
    if set(probabilities) != set(expected_keys):
        raise BenchmarkSchemaError("probability keys must match declared answer space")
    total = 0.0
    for key in expected_keys:
        total += _require_probability(
            probabilities[key], field=f"probabilities[{key!r}]"
        )
    if not math.isclose(total, 1.0, abs_tol=1e-6):
        raise BenchmarkSchemaError("probabilities must sum to 1")


def validate_provider_result(
    case: BenchmarkCase, result: ProviderResult
) -> ProviderResult:
    _require_finite_number(result.latency_ms, field="latency_ms", minimum=0.0)
    _require_finite_number(result.cost_usd, field="cost_usd", minimum=0.0)
    if result.input_tokens < 0 or result.output_tokens < 0 or result.retries < 0:
        raise BenchmarkSchemaError("tokens/retries must be non-negative integers")
    if result.error is not None:
        if not result.error.strip():
            raise BenchmarkSchemaError("provider error must be a non-empty string")
        return result

    if result.question_type != case.question_type:
        raise BenchmarkSchemaError(
            f"result type {result.question_type!r} does not match {case.question_type!r}"
        )

    if case.question_type == "choice":
        if not isinstance(result.answer, str) or result.answer not in case.options:
            raise BenchmarkSchemaError("choice answer must be a declared option")
        if result.confidence is None:
            raise BenchmarkSchemaError("choice confidence is required")
        _require_probability(result.confidence, field="confidence")
        _validate_probabilities(result.probabilities, expected_keys=case.options)
    elif case.question_type == "score":
        answer = _require_finite_number(result.answer, field="score answer")
        assert case.score_levels is not None
        if not 0.0 <= answer <= float(case.score_levels - 1):
            raise BenchmarkSchemaError("score answer is outside declared levels")
        if result.confidence is None:
            raise BenchmarkSchemaError("score confidence is required")
        _require_probability(result.confidence, field="confidence")
        keys = tuple(str(index) for index in range(case.score_levels))
        _validate_probabilities(result.probabilities, expected_keys=keys)
    else:
        _require_probability(result.answer, field="noul answer")
        if result.probabilities is not None:
            raise BenchmarkSchemaError("noul result must not carry probabilities")

    return result


def _raw_correct(case: BenchmarkCase, result: ProviderResult) -> bool:
    if case.question_type == "choice":
        return result.answer == case.expected
    if case.question_type == "score":
        return abs(float(result.answer) - float(case.expected)) <= case.tolerance
    assert case.decision_threshold is not None
    observed = float(result.answer) >= case.decision_threshold
    return observed is case.expected


def _should_escalate(case: BenchmarkCase, result: ProviderResult) -> bool:
    if result.error is not None:
        return True
    if case.question_type in {"choice", "score"}:
        if case.min_confidence is None or result.confidence is None:
            return True
        return result.confidence < case.min_confidence
    assert case.review_band is not None
    value = float(result.answer)
    lower, upper = case.review_band
    return lower <= value <= upper


def evaluate_case(case: BenchmarkCase, provider: BenchmarkProvider) -> CaseOutcome:
    result = provider.evaluate(case)
    schema_error: str | None = None
    provider_error = result.error
    if provider_error is not None and _contains_secret_shape(provider_error):
        provider_error = "[REDACTED_PROVIDER_ERROR]"

    try:
        validate_provider_result(case, result)
    except BenchmarkSchemaError as exc:
        detail = str(exc)
        schema_error = (
            "[REDACTED_SCHEMA_ERROR]"
            if _contains_secret_shape(detail)
            else detail
        )

    valid_response = schema_error is None and provider_error is None
    raw_correct = _raw_correct(case, result) if valid_response else None
    escalated = True
    if valid_response:
        escalated = _should_escalate(case, result)

    high_risk_false_action = bool(
        valid_response
        and case.risk == "high"
        and not escalated
        and raw_correct is False
    )

    latency_ms = result.latency_ms
    if not math.isfinite(latency_ms) or latency_ms < 0:
        latency_ms = 0.0
    cost_usd = result.cost_usd
    if not math.isfinite(cost_usd) or cost_usd < 0:
        cost_usd = 0.0

    return CaseOutcome(
        case_id=case.case_id,
        decision_family=case.decision_family,
        question_type=case.question_type,
        risk=case.risk,
        model=(
            "[REDACTED_MODEL]"
            if _contains_secret_shape(result.model)
            else result.model
        ),
        valid_response=valid_response,
        schema_error=schema_error,
        provider_error=provider_error,
        raw_correct=raw_correct,
        escalated=escalated,
        high_risk_false_action=high_risk_false_action,
        latency_ms=latency_ms,
        input_tokens=max(result.input_tokens, 0),
        output_tokens=max(result.output_tokens, 0),
        cost_usd=cost_usd,
        retries=max(result.retries, 0),
        baseline_latency_ms=case.baseline_latency_ms,
        baseline_cost_usd=case.baseline_cost_usd,
    )


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= percentile <= 1.0:
        raise ValueError("percentile must be between 0 and 1")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return ordered[lower_index]
    fraction = position - lower_index
    return (
        ordered[lower_index] * (1.0 - fraction)
        + ordered[upper_index] * fraction
    )


def _safe_ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _summarize(outcomes: Sequence[CaseOutcome], *, include_families: bool) -> dict[str, Any]:
    total = len(outcomes)
    valid = [item for item in outcomes if item.valid_response]
    correct = [item for item in valid if item.raw_correct is True]
    auto = [item for item in valid if not item.escalated]
    auto_correct = [item for item in auto if item.raw_correct is True]

    # Headline performance metrics intentionally use only valid semantic responses.
    # Provider/schema failures remain visible in their own counters and escalation rate;
    # fabricated zeroes from missing/malformed outcomes must never make latency/cost look
    # better than the successfully measured population.
    latencies = [item.latency_ms for item in valid]
    valid_costs = [item.cost_usd for item in valid]
    p50 = _percentile(latencies, 0.50)
    p95 = _percentile(latencies, 0.95)
    total_latency_ms = sum(latencies)
    valid_cost_total = sum(valid_costs)
    provider_cost_per_1000 = (
        valid_cost_total / len(valid) * 1000.0 if valid else None
    )

    latency_pairs = [
        (item.latency_ms, item.baseline_latency_ms)
        for item in valid
        if item.baseline_latency_ms is not None
    ]
    cost_pairs = [
        (item.cost_usd, item.baseline_cost_usd)
        for item in valid
        if item.baseline_cost_usd is not None
    ]
    latency_comparable = (
        bool(outcomes)
        and len(valid) == total
        and len(latency_pairs) == total
    )
    cost_comparable = (
        bool(outcomes)
        and len(valid) == total
        and len(cost_pairs) == total
    )

    baseline_latencies = [baseline for _, baseline in latency_pairs]
    baseline_costs = [baseline for _, baseline in cost_pairs]
    baseline_p50 = _percentile(baseline_latencies, 0.50)
    baseline_p95 = _percentile(baseline_latencies, 0.95)
    baseline_cost_per_1000 = (
        sum(baseline_costs) / len(baseline_costs) * 1000.0
        if baseline_costs
        else None
    )

    comparison_provider_p50 = (
        _percentile([provider for provider, _ in latency_pairs], 0.50)
        if latency_comparable
        else None
    )
    comparison_provider_p95 = (
        _percentile([provider for provider, _ in latency_pairs], 0.95)
        if latency_comparable
        else None
    )
    comparison_provider_cost_per_1000 = (
        sum(provider for provider, _ in cost_pairs) / len(cost_pairs) * 1000.0
        if cost_comparable
        else None
    )

    result: dict[str, Any] = {
        "total_cases": total,
        "valid_cases": len(valid),
        "schema_failures": sum(item.schema_error is not None for item in outcomes),
        "provider_errors": sum(item.provider_error is not None for item in outcomes),
        "raw_accuracy": (len(correct) / len(valid)) if valid else None,
        "auto_decisions": len(auto),
        "auto_decision_accuracy": (
            len(auto_correct) / len(auto) if auto else None
        ),
        "high_risk_false_actions": sum(
            item.high_risk_false_action for item in outcomes
        ),
        "escalation_rate": (
            sum(item.escalated for item in outcomes) / total if total else None
        ),
        "frontier_call_avoidance_rate": (len(auto) / total) if total else None,
        "latency_ms": {
            "scope": "valid_responses",
            "measured_cases": len(valid),
            "p50": p50,
            "p95": p95,
            "sum": total_latency_ms,
        },
        "sequential_equivalent_throughput_per_sec": (
            len(valid) * 1000.0 / total_latency_ms
            if total_latency_ms > 0
            else None
        ),
        "input_tokens": sum(item.input_tokens for item in outcomes),
        "output_tokens": sum(item.output_tokens for item in outcomes),
        "retries": sum(item.retries for item in outcomes),
        "cost_usd": {
            "scope": "valid_responses",
            "measured_cases": len(valid),
            "total": valid_cost_total,
            "per_1000_decisions": provider_cost_per_1000,
        },
        "baseline": {
            "latency_measured_cases": len(latency_pairs),
            "cost_measured_cases": len(cost_pairs),
            "latency_ms": {
                "p50": baseline_p50,
                "p95": baseline_p95,
            },
            "cost_per_1000_decisions": baseline_cost_per_1000,
        },
        "comparison": {
            "latency_population_matched": latency_comparable,
            "cost_population_matched": cost_comparable,
            "p50_speedup_x": (
                _safe_ratio(baseline_p50, comparison_provider_p50)
                if latency_comparable
                else None
            ),
            "p95_speedup_x": (
                _safe_ratio(baseline_p95, comparison_provider_p95)
                if latency_comparable
                else None
            ),
            "cost_reduction_x": (
                _safe_ratio(
                    baseline_cost_per_1000,
                    comparison_provider_cost_per_1000,
                )
                if cost_comparable
                else None
            ),
        },
    }

    if include_families:
        families: dict[str, list[CaseOutcome]] = {}
        for item in outcomes:
            families.setdefault(item.decision_family, []).append(item)
        result["families"] = {
            name: _summarize(items, include_families=False)
            for name, items in sorted(families.items())
        }

    return result


def build_report(cases: Sequence[BenchmarkCase], provider: BenchmarkProvider) -> dict[str, Any]:
    outcomes = [evaluate_case(case, provider) for case in cases]
    summary = _summarize(outcomes, include_families=True)
    safe_outcomes = [
        {
            "case_id": item.case_id,
            "decision_family": item.decision_family,
            "question_type": item.question_type,
            "risk": item.risk,
            "model": item.model,
            "valid_response": item.valid_response,
            "schema_error": item.schema_error,
            "provider_error": item.provider_error,
            "raw_correct": item.raw_correct,
            "escalated": item.escalated,
            "high_risk_false_action": item.high_risk_false_action,
            "latency_ms": item.latency_ms,
            "cost_usd": item.cost_usd,
            "retries": item.retries,
        }
        for item in outcomes
    ]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "offline_fixture",
        "authoritative_for_production": False,
        "summary": summary,
        "cases": safe_outcomes,
    }


def run_fixture_benchmark(cases_path: Path, fixtures_path: Path) -> dict[str, Any]:
    cases = load_cases(cases_path)
    provider = FixtureProvider.from_path(fixtures_path)
    return build_report(cases, provider)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the JEV-1A deterministic offline shadow benchmark."
    )
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = run_fixture_benchmark(args.cases, args.fixtures)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
