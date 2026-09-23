from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import jev_shadow_benchmark as bench


REPORT_SCHEMA_VERSION = "jev-cascade.report.v1"

HELDOUT_FAMILIES = (
    "task_classification",
    "skill_suggestion",
    "failure_classification",
    "evidence_relevance",
    "escalation_decision",
)
CHOICE_FAMILIES = frozenset(
    {"task_classification", "skill_suggestion", "failure_classification"}
)
NOUL_FAMILIES = frozenset({"evidence_relevance", "escalation_decision"})

ACCEPTED_CHOICE_OPTIONS: Mapping[str, tuple[str, ...]] = {
    "task_classification": ("bugfix", "feature", "docs", "review"),
    "skill_suggestion": (
        "repo_semantic",
        "pdf",
        "slides",
        "spreadsheet",
        "none",
    ),
    "failure_classification": (
        "CODE_FAILURE",
        "TEST_FAILURE",
        "TRANSPORT_FAILURE",
        "RATE_LIMITED",
        "AUTH_FAILURE",
    ),
}

_ID_PREFIX = {
    "task_classification": "task",
    "skill_suggestion": "skill",
    "failure_classification": "failure",
    "evidence_relevance": "evidence",
    "escalation_decision": "escalate",
}
_CASE_ID_RE = re.compile(
    r"^j4-(task|skill|failure|evidence|escalate)-(cal|val)-(0[1-5])$"
)


class CascadeContractError(ValueError):
    """Raised when held-out confidence-cascade evidence violates its contract."""


@dataclass(frozen=True)
class CascadeOutcome:
    case: bench.BenchmarkCase
    split: str
    valid: bool
    provider_error: str | None
    schema_error: str | None
    confidence: float | None
    answer: Any
    raw_correct: bool
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float
    retries: int


@dataclass(frozen=True)
class ChoiceSelection:
    feasible: bool
    threshold: float
    auto_decisions: int
    false_auto_decisions: int


@dataclass(frozen=True)
class NoulSelection:
    feasible: bool
    margin: float
    band: tuple[float, float]
    auto_decisions: int
    false_auto_decisions: int


def normalized_state(state: Any) -> str:
    return json.dumps(state, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _load_raw_jsonl(path: Path) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CascadeContractError(
                f"{path}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(item, Mapping):
            raise CascadeContractError(f"{path}:{line_number}: case must be an object")
        records.append(item)
    if not records:
        raise CascadeContractError("held-out corpus is empty")
    return records


def _split_from_case_id(case_id: str, family: str) -> str:
    match = _CASE_ID_RE.fullmatch(case_id)
    if match is None:
        raise CascadeContractError(f"{case_id}: malformed held-out split id")
    prefix, split, _index = match.groups()
    if prefix != _ID_PREFIX[family]:
        raise CascadeContractError(
            f"{case_id}: malformed family/split id for {family}"
        )
    return "calibration" if split == "cal" else "validation"


def load_heldout_cases(
    heldout_path: Path,
    tuning_paths: Sequence[Path],
) -> list[bench.BenchmarkCase]:
    raw_records = _load_raw_jsonl(heldout_path)
    for raw in raw_records:
        family = raw.get("decision_family")
        if family not in HELDOUT_FAMILIES:
            raise CascadeContractError(f"unsupported family: {family!r}")
        question = raw.get("question")
        if isinstance(question, Mapping) and question.get("type") == "score":
            raise CascadeContractError("score/review_severity is not admitted in JEV-4")

    try:
        cases = bench.load_cases(heldout_path)
    except bench.BenchmarkSchemaError as exc:
        raise CascadeContractError(str(exc)) from exc

    family_counts: dict[str, dict[str, int]] = {
        family: {"calibration": 0, "validation": 0} for family in HELDOUT_FAMILIES
    }
    seen_states: set[str] = set()
    for case in cases:
        if case.decision_family not in HELDOUT_FAMILIES:
            raise CascadeContractError(
                f"unsupported family: {case.decision_family!r}"
            )
        expected_type = (
            "choice" if case.decision_family in CHOICE_FAMILIES else "noul"
        )
        if case.question_type != expected_type:
            if case.question_type == "score":
                raise CascadeContractError("score questions are forbidden")
            raise CascadeContractError(
                f"{case.case_id}: question type does not match admitted family"
            )
        if case.decision_family in CHOICE_FAMILIES:
            if case.options != ACCEPTED_CHOICE_OPTIONS[case.decision_family]:
                raise CascadeContractError(
                    f"{case.case_id}: Choice options do not match accepted template"
                )
        else:
            if not isinstance(case.expected, bool):
                raise CascadeContractError(
                    f"{case.case_id}: Noul expected value must be boolean"
                )
            if case.decision_threshold is None or not math.isclose(
                float(case.decision_threshold), 0.5, rel_tol=0.0, abs_tol=1e-12
            ):
                raise CascadeContractError(
                    f"{case.case_id}: Noul center/decision threshold must be 0.5"
                )

        split = _split_from_case_id(case.case_id, case.decision_family)
        family_counts[case.decision_family][split] += 1

        state_key = normalized_state(case.state)
        if state_key in seen_states:
            raise CascadeContractError(
                f"{case.case_id}: duplicate normalized held-out state"
            )
        seen_states.add(state_key)

    for family, counts in family_counts.items():
        if counts != {"calibration": 5, "validation": 5}:
            raise CascadeContractError(
                f"{family}: requires exactly 5 calibration and 5 validation cases"
            )
    if len(cases) != 50:
        raise CascadeContractError("held-out corpus must contain exactly 50 cases")

    tuning_states: set[str] = set()
    for path in tuning_paths:
        try:
            tuning_cases = bench.load_cases(path)
        except bench.BenchmarkSchemaError as exc:
            raise CascadeContractError(str(exc)) from exc
        tuning_states.update(normalized_state(case.state) for case in tuning_cases)
    overlap = seen_states & tuning_states
    if overlap:
        raise CascadeContractError(
            f"held-out corpus overlaps tuning corpus on {len(overlap)} state(s)"
        )
    return cases


def _valid_choice_outcomes(outcomes: Iterable[CascadeOutcome]) -> list[CascadeOutcome]:
    return [
        outcome
        for outcome in outcomes
        if outcome.valid
        and outcome.confidence is not None
        and math.isfinite(float(outcome.confidence))
    ]


def _choice_stats(
    outcomes: Sequence[CascadeOutcome], threshold: float
) -> tuple[int, int]:
    auto = [
        outcome
        for outcome in outcomes
        if outcome.confidence is not None
        and float(outcome.confidence) >= threshold
    ]
    return len(auto), sum(not outcome.raw_correct for outcome in auto)


def select_choice_threshold(outcomes: Sequence[CascadeOutcome]) -> ChoiceSelection:
    valid = _valid_choice_outcomes(outcomes)
    if not valid:
        return ChoiceSelection(False, 1.0, 0, 0)

    incorrect = [float(o.confidence) for o in valid if not o.raw_correct]
    correct = [float(o.confidence) for o in valid if o.raw_correct]
    if not incorrect:
        threshold = min(correct) if correct else 1.0
        auto, false_auto = _choice_stats(valid, threshold)
        return ChoiceSelection(True, threshold, auto, false_auto)

    max_wrong = max(incorrect)
    safe_correct = [value for value in correct if value > max_wrong]
    if not safe_correct:
        auto, false_auto = _choice_stats(valid, 1.0)
        return ChoiceSelection(False, 1.0, auto, false_auto)

    nearest_safe = min(safe_correct)
    threshold = (max_wrong + nearest_safe) / 2.0
    auto, false_auto = _choice_stats(valid, threshold)
    return ChoiceSelection(false_auto == 0, threshold, auto, false_auto)


def _noul_auto(answer: float, margin: float) -> bool:
    lower = 0.5 - margin
    upper = 0.5 + margin
    return answer < lower or answer > upper


def select_noul_margin(outcomes: Sequence[CascadeOutcome]) -> NoulSelection:
    valid = [
        outcome
        for outcome in outcomes
        if outcome.valid
        and isinstance(outcome.answer, (int, float))
        and not isinstance(outcome.answer, bool)
        and math.isfinite(float(outcome.answer))
    ]
    margins = [step / 20.0 for step in range(0, 11)]
    feasible: list[tuple[int, float, int]] = []
    for margin in margins:
        autos = [o for o in valid if _noul_auto(float(o.answer), margin)]
        false_auto = sum(
            ((float(o.answer) >= 0.5) is not bool(o.case.expected))
            for o in autos
        )
        if false_auto == 0:
            feasible.append((len(autos), margin, false_auto))

    if feasible:
        best_auto = max(item[0] for item in feasible)
        best_margin = max(
            item[1] for item in feasible if item[0] == best_auto
        )
        autos = [o for o in valid if _noul_auto(float(o.answer), best_margin)]
        return NoulSelection(
            True,
            best_margin,
            (0.5 - best_margin, 0.5 + best_margin),
            len(autos),
            0,
        )

    margin = 0.5
    autos = [o for o in valid if _noul_auto(float(o.answer), margin)]
    return NoulSelection(
        False,
        margin,
        (0.0, 1.0),
        len(autos),
        sum(
            ((float(o.answer) >= 0.5) is not bool(o.case.expected))
            for o in autos
        ),
    )


def _outcome_for_case(
    case: bench.BenchmarkCase,
    provider: bench.FixtureProvider,
) -> CascadeOutcome:
    split = _split_from_case_id(case.case_id, case.decision_family)
    result = provider.evaluate(case)
    if result.error is not None:
        return CascadeOutcome(
            case=case,
            split=split,
            valid=False,
            provider_error=result.error,
            schema_error=None,
            confidence=result.confidence,
            answer=result.answer,
            raw_correct=False,
            latency_ms=float(result.latency_ms),
            input_tokens=int(result.input_tokens),
            output_tokens=int(result.output_tokens),
            cost_usd=float(result.cost_usd),
            retries=int(result.retries),
        )
    try:
        checked = bench.validate_provider_result(case, result)
    except bench.BenchmarkSchemaError as exc:
        return CascadeOutcome(
            case=case,
            split=split,
            valid=False,
            provider_error=None,
            schema_error=str(exc),
            confidence=result.confidence,
            answer=result.answer,
            raw_correct=False,
            latency_ms=float(result.latency_ms),
            input_tokens=int(result.input_tokens),
            output_tokens=int(result.output_tokens),
            cost_usd=float(result.cost_usd),
            retries=int(result.retries),
        )
    return CascadeOutcome(
        case=case,
        split=split,
        valid=True,
        provider_error=None,
        schema_error=None,
        confidence=checked.confidence,
        answer=checked.answer,
        raw_correct=bench._raw_correct(case, checked),
        latency_ms=float(checked.latency_ms),
        input_tokens=int(checked.input_tokens),
        output_tokens=int(checked.output_tokens),
        cost_usd=float(checked.cost_usd),
        retries=int(checked.retries),
    )


def _auto_for_outcome(
    outcome: CascadeOutcome,
    selection: ChoiceSelection | NoulSelection,
) -> bool:
    if not outcome.valid:
        return False
    if isinstance(selection, ChoiceSelection):
        return (
            outcome.confidence is not None
            and float(outcome.confidence) >= selection.threshold
        )
    return _noul_auto(float(outcome.answer), selection.margin)


def _split_metrics(
    outcomes: Sequence[CascadeOutcome],
    selection: ChoiceSelection | NoulSelection,
) -> dict[str, Any]:
    valid = [o for o in outcomes if o.valid]
    auto = [o for o in valid if _auto_for_outcome(o, selection)]
    false_auto = [o for o in auto if not o.raw_correct]
    return {
        "cases": len(outcomes),
        "valid_cases": len(valid),
        "raw_correct": sum(o.raw_correct for o in valid),
        "raw_accuracy": (
            sum(o.raw_correct for o in valid) / len(valid) if valid else None
        ),
        "auto_decisions": len(auto),
        "auto_accuracy": (
            sum(o.raw_correct for o in auto) / len(auto) if auto else None
        ),
        "false_auto_decisions": len(false_auto),
        "high_risk_false_actions": sum(
            o.case.risk == "high" for o in false_auto
        ),
        "escalations": len(outcomes) - len(auto),
        "frontier_avoidance": len(auto) / len(outcomes) if outcomes else 0.0,
    }


def _family_report(
    family: str,
    outcomes: Sequence[CascadeOutcome],
) -> tuple[dict[str, Any], dict[str, Any]]:
    calibration = [o for o in outcomes if o.split == "calibration"]
    validation = [o for o in outcomes if o.split == "validation"]

    if family in CHOICE_FAMILIES:
        selection: ChoiceSelection | NoulSelection = select_choice_threshold(calibration)
        chosen_policy = {"kind": "min_confidence", "value": selection.threshold}
        selection_payload = {
            "kind": "min_confidence",
            "value": selection.threshold,
            "feasible": selection.feasible,
            "selection_split": "calibration",
        }
    else:
        selection = select_noul_margin(calibration)
        chosen_policy = {
            "kind": "review_band",
            "center": 0.5,
            "margin": selection.margin,
            "lower": selection.band[0],
            "upper": selection.band[1],
        }
        selection_payload = {
            **chosen_policy,
            "feasible": selection.feasible,
            "selection_split": "calibration",
        }

    cal_metrics = _split_metrics(calibration, selection)
    val_metrics = _split_metrics(validation, selection)
    valid = [o for o in outcomes if o.valid]
    latencies = [o.latency_ms for o in valid]
    provider_errors = [o for o in outcomes if o.provider_error is not None]
    schema_failures = [o for o in outcomes if o.schema_error is not None]
    false_auto = [
        o for o in valid if _auto_for_outcome(o, selection) and not o.raw_correct
    ]
    high_risk_false = sum(o.case.risk == "high" for o in false_auto)

    reasons: list[str] = []
    for outcome in provider_errors:
        reasons.append(
            f"{outcome.case.case_id}: provider_error:{outcome.provider_error}"
        )
    for outcome in schema_failures:
        reasons.append(
            f"{outcome.case.case_id}: schema_error:{outcome.schema_error}"
        )
    if not selection.feasible:
        reasons.append("calibration_policy_infeasible")
    if cal_metrics["false_auto_decisions"]:
        reasons.append("calibration_false_auto_decisions")
    if val_metrics["false_auto_decisions"]:
        reasons.append("validation_false_auto_decisions")
    if high_risk_false:
        reasons.append("high_risk_false_actions")
    if val_metrics["valid_cases"] != 5:
        reasons.append("validation_valid_cases_not_5")
    if val_metrics["auto_decisions"] < 1:
        reasons.append("validation_has_no_auto_decision")

    verdict = "CANDIDATE" if not reasons else "INCONCLUSIVE"
    auto_decisions = cal_metrics["auto_decisions"] + val_metrics["auto_decisions"]
    false_auto_decisions = (
        cal_metrics["false_auto_decisions"] + val_metrics["false_auto_decisions"]
    )
    auto_correct = auto_decisions - false_auto_decisions
    escalations = cal_metrics["escalations"] + val_metrics["escalations"]
    report = {
        "verdict": verdict,
        "inconclusive_reasons": reasons,
        "chosen_policy": chosen_policy,
        "split_counts": {"calibration": 5, "validation": 5},
        "total_cases": len(outcomes),
        "valid_cases": len(valid),
        "provider_errors": len(provider_errors),
        "schema_failures": len(schema_failures),
        "high_risk_false_actions": high_risk_false,
        "raw_correct": sum(o.raw_correct for o in valid),
        "raw_accuracy": (
            sum(o.raw_correct for o in valid) / len(valid) if valid else None
        ),
        "auto_decisions": auto_decisions,
        "auto_accuracy": (
            auto_correct / auto_decisions if auto_decisions else None
        ),
        "false_auto_decisions": false_auto_decisions,
        "escalations": escalations,
        "frontier_avoidance": (
            auto_decisions / len(outcomes) if outcomes else 0.0
        ),
        "calibration": cal_metrics,
        "validation": val_metrics,
        "latency_ms": {
            "measured_cases": len(latencies),
            "p50": bench._percentile(latencies, 0.50),
            "p95": bench._percentile(latencies, 0.95),
        },
        "input_tokens": sum(o.input_tokens for o in valid),
        "output_tokens": sum(o.output_tokens for o in valid),
        "cost_usd": sum(o.cost_usd for o in valid),
        "retries": sum(o.retries for o in valid),
    }
    return report, selection_payload


def run_cascade(
    heldout_path: Path,
    results_path: Path,
    tuning_paths: Sequence[Path],
) -> dict[str, Any]:
    cases = load_heldout_cases(heldout_path, tuning_paths)
    try:
        provider = bench.FixtureProvider.from_path(results_path)
    except bench.BenchmarkSchemaError as exc:
        raise CascadeContractError(str(exc)) from exc

    outcomes = [_outcome_for_case(case, provider) for case in cases]
    by_family = {
        family: [o for o in outcomes if o.case.decision_family == family]
        for family in HELDOUT_FAMILIES
    }

    family_reports: dict[str, Any] = {}
    family_selections: dict[str, Any] = {}
    for family in HELDOUT_FAMILIES:
        family_report, selection_payload = _family_report(
            family, by_family[family]
        )
        family_reports[family] = family_report
        family_selections[family] = selection_payload

    valid = [o for o in outcomes if o.valid]
    total_cost = sum(o.cost_usd for o in valid)
    total_decisions = len(outcomes)
    auto_decisions = sum(
        int(item["auto_decisions"]) for item in family_reports.values()
    )
    false_auto_decisions = sum(
        int(item["false_auto_decisions"]) for item in family_reports.values()
    )
    auto_correct = auto_decisions - false_auto_decisions
    aggregate = {
        "total_cases": total_decisions,
        "split_counts": {"calibration": 25, "validation": 25},
        "valid_cases": len(valid),
        "provider_errors": sum(
            int(item["provider_errors"]) for item in family_reports.values()
        ),
        "schema_failures": sum(
            int(item["schema_failures"]) for item in family_reports.values()
        ),
        "raw_correct": sum(o.raw_correct for o in valid),
        "raw_accuracy": (
            sum(o.raw_correct for o in valid) / len(valid) if valid else None
        ),
        "auto_decisions": auto_decisions,
        "auto_accuracy": (
            auto_correct / auto_decisions if auto_decisions else None
        ),
        "false_auto_decisions": false_auto_decisions,
        "high_risk_false_actions": sum(
            int(item["high_risk_false_actions"]) for item in family_reports.values()
        ),
        "escalations": total_decisions - auto_decisions,
        "frontier_avoidance": (
            auto_decisions / total_decisions if total_decisions else 0.0
        ),
        "input_tokens": sum(o.input_tokens for o in valid),
        "output_tokens": sum(o.output_tokens for o in valid),
        "retries": sum(o.retries for o in valid),
        "cost_usd": {
            "total": total_cost,
            "per_1000_decisions": (
                total_cost / total_decisions * 1000.0
                if total_decisions
                else None
            ),
        },
        "latency_ms": {
            "measured_cases": len(valid),
            "p50": bench._percentile([o.latency_ms for o in valid], 0.50),
            "p95": bench._percentile([o.latency_ms for o in valid], 0.95),
        },
        "families_candidate": sum(
            item["verdict"] == "CANDIDATE" for item in family_reports.values()
        ),
        "families_inconclusive": sum(
            item["verdict"] == "INCONCLUSIVE" for item in family_reports.values()
        ),
    }

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "offline_fixture",
        "authoritative_for_production": False,
        "production_consequence_forbidden": True,
        "heldout_cases": len(cases),
        "selection": {
            "scope": "calibration_only",
            "validation_influenced_selection": False,
            "families": family_selections,
        },
        "families": family_reports,
        "aggregate": aggregate,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate JEV-4 held-out confidence cascade evidence."
    )
    parser.add_argument("--heldout", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--tuning-cases",
        type=Path,
        action="append",
        required=True,
        dest="tuning_cases",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        report = run_cascade(args.heldout, args.results, args.tuning_cases)
        payload = json.dumps(
            report, indent=2, sort_keys=True, ensure_ascii=False
        ) + "\n"
        if args.output is not None:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0
    except (CascadeContractError, bench.BenchmarkSchemaError, OSError, ValueError) as exc:
        print(f"JEV_CASCADE_INVALID: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
