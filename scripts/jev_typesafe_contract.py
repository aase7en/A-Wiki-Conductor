from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from jev_shadow_benchmark import (
    BenchmarkCase,
    BenchmarkSchemaError,
    ProviderResult,
    load_cases,
    validate_provider_result,
)


QUESTION_SPEC_SCHEMA_VERSION = "jev-typesafe.questions.v1"
MANIFEST_SCHEMA_VERSION = "jev-typesafe.request-manifest.v1"
PINNED_BENCHMARK_MODEL = "jev-1.13.0"
DEFAULT_QUESTION_ID = "decision"
_VERSIONED_JEV_RE = re.compile(r"^jev-\d+\.\d+\.\d+$")

_RESPONSE_TOP_LEVEL_FIELDS = frozenset({"model", "answers", "usage"})
_RESPONSE_USAGE_FIELDS = frozenset({"input_tokens", "output_tokens"})
_CHOICE_ANSWER_FIELDS = frozenset(
    {"type", "choice", "probabilities", "confidence"}
)
_SCORE_ANSWER_FIELDS = frozenset(
    {"type", "score", "legend", "probabilities", "confidence"}
)
_NOUL_ANSWER_FIELDS = frozenset({"type", "noul"})


class TypeSafeContractError(ValueError):
    """Raised when offline TypeSafe request/response contract data is invalid."""


@dataclass(frozen=True)
class QuestionSpec:
    decision_family: str
    question_type: str
    instructions: Any
    criteria: Any


def _finite_number(value: Any, *, field: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeSafeContractError(f"{field} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise TypeSafeContractError(f"{field} must be a finite number")
    if minimum is not None and number < minimum:
        raise TypeSafeContractError(f"{field} must be >= {minimum}")
    return number


def _nonnegative_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TypeSafeContractError(f"{field} must be a non-negative integer")
    return value


def _validate_text_tree(value: Any, *, field: str) -> None:
    if isinstance(value, str):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_text_tree(item, field=f"{field}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeSafeContractError(f"{field} object keys must be non-empty strings")
            _validate_text_tree(item, field=f"{field}.{key}")
        return
    raise TypeSafeContractError(
        f"{field} must contain text-only leaves in strings, objects, or arrays"
    )


def _validate_versioned_model(model: str) -> None:
    if not isinstance(model, str) or not _VERSIONED_JEV_RE.fullmatch(model):
        raise TypeSafeContractError(
            "benchmark model must be a pinned versioned Jev model ID"
        )


def _reject_unknown_fields(
    mapping: Mapping[str, Any], allowed: frozenset[str], *, context: str
) -> None:
    unexpected = set(mapping) - allowed
    if unexpected:
        raise TypeSafeContractError(
            f"{context} must be exactly {', '.join(sorted(allowed))}; "
            f"unexpected: {sorted(unexpected)}"
        )


def _question_spec_from_mapping(
    decision_family: str, raw: Mapping[str, Any]
) -> QuestionSpec:
    question_type = raw.get("type")
    instructions = raw.get("instructions")
    criteria = raw.get("criteria")

    if question_type not in {"choice", "score", "noul"}:
        raise TypeSafeContractError(
            f"{decision_family}: unsupported question type {question_type!r}"
        )
    _validate_text_tree(instructions, field=f"{decision_family}.instructions")

    if question_type == "choice":
        if not isinstance(criteria, Mapping):
            raise TypeSafeContractError(
                f"{decision_family}: choice criteria must be an object"
            )
        if not 2 <= len(criteria) <= 255:
            raise TypeSafeContractError(
                f"{decision_family}: choice criteria must contain 2..255 options"
            )
        for key, value in criteria.items():
            if not isinstance(key, str) or not key:
                raise TypeSafeContractError(
                    f"{decision_family}: choice option keys must be non-empty strings"
                )
            if value is not None:
                _validate_text_tree(
                    value, field=f"{decision_family}.criteria.{key}"
                )
    elif question_type == "score":
        if not isinstance(criteria, list) or not 2 <= len(criteria) <= 10:
            raise TypeSafeContractError(
                f"{decision_family}: score criteria must contain 2..10 ordered levels"
            )
        for index, value in enumerate(criteria):
            _validate_text_tree(
                value, field=f"{decision_family}.criteria[{index}]"
            )
    else:
        if criteria is not None:
            if not isinstance(criteria, Mapping):
                raise TypeSafeContractError(
                    f"{decision_family}: noul criteria must be an object"
                )
            if set(criteria) != {"true", "false"}:
                raise TypeSafeContractError(
                    f"{decision_family}: noul criteria must contain true and false"
                )
            _validate_text_tree(
                criteria["true"], field=f"{decision_family}.criteria.true"
            )
            _validate_text_tree(
                criteria["false"], field=f"{decision_family}.criteria.false"
            )

    return QuestionSpec(
        decision_family=decision_family,
        question_type=question_type,
        instructions=instructions,
        criteria=criteria,
    )


def load_question_specs(path: Path) -> dict[str, QuestionSpec]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise TypeSafeContractError("question spec file must contain an object")
    if raw.get("schema_version") != QUESTION_SPEC_SCHEMA_VERSION:
        raise TypeSafeContractError(
            f"schema_version must be {QUESTION_SPEC_SCHEMA_VERSION!r}"
        )
    families = raw.get("families")
    if not isinstance(families, Mapping) or not families:
        raise TypeSafeContractError("families must be a non-empty object")

    specs: dict[str, QuestionSpec] = {}
    for decision_family, value in families.items():
        if not isinstance(decision_family, str) or not decision_family:
            raise TypeSafeContractError("family names must be non-empty strings")
        if not isinstance(value, Mapping):
            raise TypeSafeContractError(
                f"{decision_family}: question spec must be an object"
            )
        specs[decision_family] = _question_spec_from_mapping(
            decision_family, value
        )
    return specs


def validate_case_against_spec(case: BenchmarkCase, spec: QuestionSpec) -> None:
    if case.decision_family != spec.decision_family:
        raise TypeSafeContractError(
            f"{case.case_id}: decision family does not match question spec"
        )
    if case.question_type != spec.question_type:
        raise TypeSafeContractError(
            f"{case.case_id}: question type does not match question spec"
        )
    _validate_text_tree(case.state, field=f"{case.case_id}.state")

    if case.question_type == "choice":
        assert isinstance(spec.criteria, Mapping)
        if tuple(spec.criteria.keys()) != case.options:
            raise TypeSafeContractError(
                f"{case.case_id}: choice options must exactly match criteria order"
            )
    elif case.question_type == "score":
        assert isinstance(spec.criteria, list)
        if case.score_levels != len(spec.criteria):
            raise TypeSafeContractError(
                f"{case.case_id}: score levels must match criteria length"
            )


def build_typesafe_request(
    case: BenchmarkCase,
    spec: QuestionSpec,
    *,
    model: str = PINNED_BENCHMARK_MODEL,
    question_id: str = DEFAULT_QUESTION_ID,
) -> dict[str, Any]:
    _validate_versioned_model(model)
    if not isinstance(question_id, str) or not question_id:
        raise TypeSafeContractError("question_id must be a non-empty string")
    validate_case_against_spec(case, spec)

    question: dict[str, Any] = {
        "type": spec.question_type,
        "instructions": spec.instructions,
    }
    if spec.criteria is not None:
        question["criteria"] = spec.criteria

    return {
        "state": case.state,
        "model": model,
        "questions": {question_id: question},
    }


def _answer_mapping(
    payload: Mapping[str, Any],
    *,
    question_id: str,
) -> Mapping[str, Any]:
    answers = payload.get("answers")
    if not isinstance(answers, Mapping):
        raise TypeSafeContractError("answers must be an object")
    if set(answers) != {question_id}:
        raise TypeSafeContractError(
            "answers must contain exactly the requested question id"
        )
    answer = answers[question_id]
    if not isinstance(answer, Mapping):
        raise TypeSafeContractError("answer must be an object")
    return answer


def normalize_typesafe_response(
    case: BenchmarkCase,
    spec: QuestionSpec,
    payload: Mapping[str, Any],
    *,
    elapsed_ms: float,
    input_price_per_million_usd: float,
    expected_model: str = PINNED_BENCHMARK_MODEL,
    question_id: str = DEFAULT_QUESTION_ID,
    retries: int = 0,
) -> ProviderResult:
    validate_case_against_spec(case, spec)
    _validate_versioned_model(expected_model)

    if not isinstance(payload, Mapping):
        raise TypeSafeContractError("response payload must be an object")
    _reject_unknown_fields(
        payload, _RESPONSE_TOP_LEVEL_FIELDS, context="response top-level fields"
    )
    model = payload.get("model")
    if model != expected_model:
        raise TypeSafeContractError("response model does not match pinned model")

    elapsed = _finite_number(elapsed_ms, field="elapsed_ms", minimum=0.0)
    price = _finite_number(
        input_price_per_million_usd,
        field="input_price_per_million_usd",
        minimum=0.0,
    )
    retry_count = _nonnegative_int(retries, field="retries")

    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        raise TypeSafeContractError("usage must be an object")
    _reject_unknown_fields(
        usage, _RESPONSE_USAGE_FIELDS, context="usage fields"
    )
    input_tokens = _nonnegative_int(
        usage.get("input_tokens"), field="usage.input_tokens"
    )
    output_tokens = _nonnegative_int(
        usage.get("output_tokens"), field="usage.output_tokens"
    )

    answer = _answer_mapping(payload, question_id=question_id)
    if answer.get("type") != case.question_type:
        raise TypeSafeContractError("answer type does not match benchmark case")

    confidence: float | None = None
    probabilities: Mapping[str, float] | None = None

    if case.question_type == "choice":
        _reject_unknown_fields(
            answer, _CHOICE_ANSWER_FIELDS, context="choice answer fields"
        )
        raw_answer = answer.get("choice")
        confidence = answer.get("confidence")
        probabilities = answer.get("probabilities")
    elif case.question_type == "score":
        _reject_unknown_fields(
            answer, _SCORE_ANSWER_FIELDS, context="score answer fields"
        )
        raw_answer = answer.get("score")
        confidence = answer.get("confidence")
        probabilities = answer.get("probabilities")
        legend = answer.get("legend")
        if not isinstance(legend, Mapping):
            raise TypeSafeContractError("score legend must be an object")
        expected_keys = {
            str(index) for index in range(case.score_levels or 0)
        }
        if set(legend) != expected_keys:
            raise TypeSafeContractError(
                "score legend keys must match declared levels"
            )
        for key, value in legend.items():
            if not isinstance(value, str):
                raise TypeSafeContractError(
                    "score legend values must be strings; "
                    f"legend[{key!r}] is not a string"
                )
    else:
        if set(answer) - _NOUL_ANSWER_FIELDS:
            if set(answer) & {"confidence", "probabilities"}:
                raise TypeSafeContractError(
                    "noul answer must not invent confidence or probabilities"
                )
            _reject_unknown_fields(
                answer, _NOUL_ANSWER_FIELDS, context="noul answer fields"
            )
        raw_answer = answer.get("noul")

    result = ProviderResult(
        question_type=case.question_type,
        answer=raw_answer,
        model=model,
        latency_ms=elapsed,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=input_tokens * price / 1_000_000.0,
        retries=retry_count,
        confidence=confidence,
        probabilities=probabilities,
    )
    try:
        return validate_provider_result(case, result)
    except BenchmarkSchemaError as exc:
        raise TypeSafeContractError(str(exc)) from exc


def build_request_manifest(
    cases: Sequence[BenchmarkCase],
    specs: Mapping[str, QuestionSpec],
    *,
    model: str = PINNED_BENCHMARK_MODEL,
) -> list[dict[str, Any]]:
    _validate_versioned_model(model)
    manifest: list[dict[str, Any]] = []
    for case in cases:
        spec = specs.get(case.decision_family)
        if spec is None:
            raise TypeSafeContractError(
                f"{case.case_id}: missing question spec for {case.decision_family}"
            )
        manifest.append(
            {
                "schema_version": MANIFEST_SCHEMA_VERSION,
                "case_id": case.case_id,
                "decision_family": case.decision_family,
                "request": build_typesafe_request(case, spec, model=model),
            }
        )
    return manifest


def emit_request_manifest(
    cases_path: Path,
    question_specs_path: Path,
    output_path: Path,
    *,
    model: str = PINNED_BENCHMARK_MODEL,
) -> int:
    cases = load_cases(cases_path)
    specs = load_question_specs(question_specs_path)
    manifest = build_request_manifest(cases, specs, model=model)
    rendered = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for item in manifest
    )
    output_path.write_text(rendered, encoding="utf-8")
    return len(manifest)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit deterministic offline TypeSafe request JSONL."
    )
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=PINNED_BENCHMARK_MODEL)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    count = emit_request_manifest(
        args.cases,
        args.questions,
        args.output,
        model=args.model,
    )
    print(f"wrote {count} request records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
