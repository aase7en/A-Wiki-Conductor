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
import jev_confidence_cascade as cascade  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "jev_shadow"
HELDOUT = FIXTURES / "cases-heldout-v1.jsonl"
TUNING_CORPORA = [FIXTURES / "cases.jsonl", FIXTURES / "cases-expanded.jsonl"]
QUESTIONS = FIXTURES / "typesafe_questions.json"


# ---------------------------------------------------------------------------
# corpus helpers
# ---------------------------------------------------------------------------


def load_corpus_records() -> list[dict]:
    return [
        json.loads(line)
        for line in HELDOUT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_corpus(tmp_path: Path, records: list[dict], name: str = "corpus.jsonl") -> Path:
    path = tmp_path / name
    path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in records),
        encoding="utf-8",
    )
    return path


def write_results(tmp_path: Path, results: dict, name: str = "results.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(results, sort_keys=True), encoding="utf-8")
    return path


def choice_probabilities(options: list[str], picked: str, confidence: float) -> dict:
    others = [option for option in options if option != picked]
    share = (1.0 - confidence) / len(others) if others else 0.0
    probabilities = {option: share for option in others}
    probabilities[picked] = 1.0 - share * len(others)
    return probabilities


def build_full_results(
    *,
    confidence: float = 0.9,
    wrong_ids: frozenset[str] = frozenset(),
    drop_ids: frozenset[str] = frozenset(),
    corrupt_schema_ids: frozenset[str] = frozenset(),
    latency_for=None,
) -> dict:
    cases = cascade.load_heldout_cases(HELDOUT, TUNING_CORPORA)
    results: dict = {}
    for case in cases:
        if case.case_id in drop_ids:
            continue
        latency = 100.0 if latency_for is None else latency_for(case)
        base = {
            "model": "fixture-heldout",
            "latency_ms": latency,
            "input_tokens": 200,
            "output_tokens": 40,
            "cost_usd": 0.0002,
            "retries": 0,
        }
        if case.case_id in corrupt_schema_ids:
            results[case.case_id] = {
                "type": "choice",
                "answer": "bugfix",
                "confidence": 0.9,
                "probabilities": {"bugfix": 1.0},
                **base,
            }
            continue
        wrong = case.case_id in wrong_ids
        if case.question_type == "choice":
            options = list(case.options)
            if wrong:
                answer = next(option for option in options if option != case.expected)
            else:
                answer = case.expected
            used_confidence = 0.99 if wrong else confidence
            results[case.case_id] = {
                "type": "choice",
                "answer": answer,
                "confidence": used_confidence,
                "probabilities": choice_probabilities(options, answer, used_confidence),
                **base,
            }
        else:
            if wrong:
                answer = 0.02 if case.expected else 0.98
            else:
                answer = 0.93 if case.expected else 0.07
            results[case.case_id] = {"type": "noul", "answer": answer, **base}
    return results


def run_with_results(tmp_path: Path, results: dict, name: str = "results.json") -> dict:
    results_path = write_results(tmp_path, results, name=name)
    return cascade.run_cascade(HELDOUT, results_path, TUNING_CORPORA)


# ---------------------------------------------------------------------------
# corpus shape / separation
# ---------------------------------------------------------------------------


def test_heldout_corpus_shape_is_exact() -> None:
    cases = cascade.load_heldout_cases(HELDOUT, TUNING_CORPORA)
    assert len(cases) == 50
    assert len({case.case_id for case in cases}) == 50

    families = {case.decision_family for case in cases}
    assert families == set(cascade.HELDOUT_FAMILIES)
    assert "review_severity" not in families

    for family in cascade.HELDOUT_FAMILIES:
        family_cases = [case for case in cases if case.decision_family == family]
        assert len(family_cases) == 10
        expected_type = (
            "choice" if family in cascade.CHOICE_FAMILIES else "noul"
        )
        assert all(case.question_type == expected_type for case in family_cases)
        if expected_type == "choice":
            for case in family_cases:
                assert list(case.options) == list(
                    cascade.ACCEPTED_CHOICE_OPTIONS[family]
                )
        else:
            assert all(isinstance(case.expected, bool) for case in family_cases)
        for split in ("cal", "val"):
            split_cases = [
                case for case in family_cases if f"-{split}-" in case.case_id
            ]
            assert len(split_cases) == 5
            indices = sorted(
                int(case.case_id.rsplit("-", 1)[-1]) for case in split_cases
            )
            assert indices == [1, 2, 3, 4, 5]
        assert all(case.question_type != "score" for case in family_cases)
        assert all(
            not isinstance(case.state, dict) or "heldout_tag" not in case.state
            for case in family_cases
        )


def test_choice_templates_match_accepted_typesafe_fixture() -> None:
    specs = json.loads(QUESTIONS.read_text(encoding="utf-8"))["families"]
    for family, options in cascade.ACCEPTED_CHOICE_OPTIONS.items():
        assert specs[family]["type"] == "choice"
        assert tuple(specs[family]["criteria"].keys()) == tuple(options)
    for family in cascade.NOUL_FAMILIES:
        assert specs[family]["type"] == "noul"
    assert specs["review_severity"]["type"] == "score"
    assert "review_severity" not in cascade.HELDOUT_FAMILIES


def test_no_overlap_with_tuning_corpora(tmp_path: Path) -> None:
    tuning_states = set()
    for path in TUNING_CORPORA:
        for case in bench.load_cases(path):
            tuning_states.add(cascade.normalized_state(case.state))

    cases = cascade.load_heldout_cases(HELDOUT, TUNING_CORPORA)
    heldout_states = [cascade.normalized_state(case.state) for case in cases]
    assert len(heldout_states) == len(set(heldout_states))
    assert not (set(heldout_states) & tuning_states)

    records = load_corpus_records()
    stolen = None
    for path in TUNING_CORPORA:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                stolen = json.loads(line)["state"]
                break
        if stolen is not None:
            break
    for record in records:
        if record["case_id"] == "j4-task-cal-01":
            record["state"] = json.loads(json.dumps(stolen))
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="overlap"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_intra_corpus_duplicate_state_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    by_id = {record["case_id"]: record for record in records}
    by_id["j4-task-val-01"]["state"] = json.loads(
        json.dumps(by_id["j4-task-cal-01"]["state"])
    )
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="duplicate"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_secret_shaped_state_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-skill-cal-01":
            record["state"]["request"] += " token " + "sk-" + "abcdefghijklmnop123"
    path = write_corpus(tmp_path, records)
    with pytest.raises(ValueError, match="secret"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_secret_shaped_results_rejected(tmp_path: Path) -> None:
    results = build_full_results()
    results["j4-task-cal-01"]["model"] = "sk-" + "abcdefghijklmnop123"
    path = write_results(tmp_path, results)
    with pytest.raises(ValueError, match="secret"):
        cascade.run_cascade(HELDOUT, path, TUNING_CORPORA)


def test_unsupported_family_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-task-cal-01":
            record["decision_family"] = "review_severity"
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="unsupported family"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_score_question_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-task-cal-01":
            record["question"] = {"type": "score", "levels": 4}
            record["expected"] = 2
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="score"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_noul_center_must_be_fixed_at_half(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-evidence-cal-01":
            record["policy"]["decision_threshold"] = 0.4
            break
    path = write_corpus(tmp_path, records)
    with pytest.raises(
        cascade.CascadeContractError,
        match=r"center/decision threshold must be 0\.5",
    ):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_malformed_split_id_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-task-cal-01":
            record["case_id"] = "j4-task-warmup-01"
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="malformed"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_out_of_range_split_index_rejected(tmp_path: Path) -> None:
    records = load_corpus_records()
    for record in records:
        if record["case_id"] == "j4-task-cal-05":
            record["case_id"] = "j4-task-cal-06"
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="malformed"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


def test_wrong_split_count_rejected(tmp_path: Path) -> None:
    records = [
        record
        for record in load_corpus_records()
        if record["case_id"] != "j4-task-val-05"
    ]
    path = write_corpus(tmp_path, records)
    with pytest.raises(cascade.CascadeContractError, match="5 calibration and 5 validation"):
        cascade.load_heldout_cases(path, TUNING_CORPORA)


# ---------------------------------------------------------------------------
# threshold selection (calibration only)
# ---------------------------------------------------------------------------


def unit_case(case_id: str, family: str, *, expected, risk: str = "low") -> bench.BenchmarkCase:
    if family in cascade.CHOICE_FAMILIES:
        return bench.BenchmarkCase(
            case_id=case_id,
            decision_family=family,
            question_type="choice",
            state={"request": "synthetic unit fixture"},
            expected=expected,
            risk=risk,
            options=cascade.ACCEPTED_CHOICE_OPTIONS[family],
        )
    return bench.BenchmarkCase(
        case_id=case_id,
        decision_family=family,
        question_type="noul",
        state={"situation": "synthetic unit fixture"},
        expected=expected,
        risk=risk,
        decision_threshold=0.5,
        review_band=(0.5, 0.5),
    )


def unit_outcome(case: bench.BenchmarkCase, *, confidence=None, answer=None, correct=True, split="cal"):
    return cascade.CascadeOutcome(
        case=case,
        split=split,
        valid=True,
        provider_error=None,
        schema_error=None,
        confidence=confidence,
        answer=answer,
        raw_correct=correct,
        latency_ms=1.0,
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        retries=0,
    )


def test_choice_threshold_selection_maximizes_zero_false_autos() -> None:
    outcomes = [
        unit_outcome(unit_case("j4-task-cal-01", "task_classification", expected="bugfix"), confidence=0.9),
        unit_outcome(unit_case("j4-task-cal-02", "task_classification", expected="docs"), confidence=0.8),
        unit_outcome(
            unit_case("j4-task-cal-03", "task_classification", expected="bugfix"),
            confidence=0.7,
            answer="feature",
            correct=False,
        ),
    ]
    selection = cascade.select_choice_threshold(outcomes)
    assert selection.feasible is True
    assert selection.threshold == 0.75
    assert selection.auto_decisions == 2
    assert selection.false_auto_decisions == 0


def test_choice_threshold_tie_picks_stricter_threshold() -> None:
    outcomes = [
        unit_outcome(unit_case("j4-task-cal-01", "task_classification", expected="bugfix"), confidence=0.9),
        unit_outcome(unit_case("j4-task-cal-02", "task_classification", expected="docs"), confidence=0.8),
    ]
    selection = cascade.select_choice_threshold(outcomes)
    assert selection.feasible is True
    assert selection.auto_decisions == 2
    assert selection.threshold == 0.8


def test_choice_threshold_infeasible_falls_back_to_strictest() -> None:
    outcomes = [
        unit_outcome(unit_case("j4-task-cal-01", "task_classification", expected="bugfix"), confidence=1.0),
        unit_outcome(
            unit_case("j4-task-cal-02", "task_classification", expected="bugfix"),
            confidence=1.0,
            answer="feature",
            correct=False,
        ),
    ]
    selection = cascade.select_choice_threshold(outcomes)
    assert selection.feasible is False
    assert selection.threshold == 1.0
    assert selection.false_auto_decisions >= 1


def test_noul_band_selection_maximizes_zero_false_autos() -> None:
    outcomes = [
        unit_outcome(unit_case("j4-evidence-cal-01", "evidence_relevance", expected=True), answer=0.95),
        unit_outcome(unit_case("j4-evidence-cal-02", "evidence_relevance", expected=False), answer=0.05),
        unit_outcome(unit_case("j4-evidence-cal-03", "evidence_relevance", expected=False), answer=0.55),
        unit_outcome(unit_case("j4-evidence-cal-04", "evidence_relevance", expected=True), answer=0.45),
    ]
    selection = cascade.select_noul_margin(outcomes)
    assert selection.feasible is True
    assert selection.auto_decisions == 2
    assert selection.false_auto_decisions == 0
    assert selection.margin == 0.4
    assert selection.band[0] == pytest.approx(0.1)
    assert selection.band[1] == pytest.approx(0.9)


def test_noul_band_tie_picks_wider_margin() -> None:
    outcomes = [
        unit_outcome(unit_case("j4-evidence-cal-01", "evidence_relevance", expected=True), answer=0.95),
        unit_outcome(unit_case("j4-evidence-cal-02", "evidence_relevance", expected=False), answer=0.05),
    ]
    selection = cascade.select_noul_margin(outcomes)
    assert selection.feasible is True
    assert selection.auto_decisions == 2
    assert selection.margin == 0.4


# ---------------------------------------------------------------------------
# full-cascade behavior
# ---------------------------------------------------------------------------


def test_validation_cannot_influence_selection(tmp_path: Path) -> None:
    clean = build_full_results()
    corrupted = build_full_results(wrong_ids=frozenset(
        case_id
        for case_id in clean
        if "-val-" in case_id
    ))
    report_a = run_with_results(tmp_path, clean, name="results-a.json")
    report_b = run_with_results(tmp_path, corrupted, name="results-b.json")
    assert report_a["selection"] == report_b["selection"]
    assert report_a["selection"]["scope"] == "calibration_only"
    assert report_a["selection"]["validation_influenced_selection"] is False
    for family, selection in report_a["selection"]["families"].items():
        assert selection["selection_split"] == "calibration"
    assert all(
        verdict == "CANDIDATE"
        for verdict in (
            family["verdict"] for family in report_a["families"].values()
        )
    )
    assert any(
        family["verdict"] == "INCONCLUSIVE"
        for family in report_b["families"].values()
    )


def test_false_auto_and_high_risk_force_inconclusive(tmp_path: Path) -> None:
    report = run_with_results(
        tmp_path,
        build_full_results(
            wrong_ids=frozenset({"j4-task-val-01", "j4-failure-val-03"})
        ),
    )
    task = report["families"]["task_classification"]
    assert task["verdict"] == "INCONCLUSIVE"
    assert "validation_false_auto_decisions" in task["inconclusive_reasons"]
    assert task["high_risk_false_actions"] == 0

    failure = report["families"]["failure_classification"]
    assert failure["verdict"] == "INCONCLUSIVE"
    assert "validation_false_auto_decisions" in failure["inconclusive_reasons"]
    assert "high_risk_false_actions" in failure["inconclusive_reasons"]
    assert failure["high_risk_false_actions"] == 1
    assert failure["validation"]["false_auto_decisions"] == 1


def test_missing_result_forces_inconclusive_with_honest_denominators(
    tmp_path: Path,
) -> None:
    report = run_with_results(
        tmp_path, build_full_results(drop_ids=frozenset({"j4-evidence-val-05"}))
    )
    family = report["families"]["evidence_relevance"]
    assert family["verdict"] == "INCONCLUSIVE"
    assert family["split_counts"] == {"calibration": 5, "validation": 5}
    assert family["total_cases"] == 10
    assert family["valid_cases"] == 9
    assert family["provider_errors"] == 1
    assert any("j4-evidence-val-05" in reason for reason in family["inconclusive_reasons"])
    assert report["aggregate"]["provider_errors"] == 1
    assert report["aggregate"]["valid_cases"] == 49
    assert all(
        report["families"][name]["verdict"] == "CANDIDATE"
        for name in ("task_classification", "skill_suggestion")
    )


def test_schema_failure_forces_inconclusive(tmp_path: Path) -> None:
    report = run_with_results(
        tmp_path,
        build_full_results(corrupt_schema_ids=frozenset({"j4-escalate-val-02"})),
    )
    family = report["families"]["escalation_decision"]
    assert family["verdict"] == "INCONCLUSIVE"
    assert family["schema_failures"] == 1
    assert family["valid_cases"] == 9
    assert any(
        "j4-escalate-val-02" in reason for reason in family["inconclusive_reasons"]
    )
    assert report["aggregate"]["schema_failures"] == 1
    assert report["aggregate"]["valid_cases"] == 49


def test_latency_usage_and_cost_metrics(tmp_path: Path) -> None:
    latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    counter = {"task_classification": 0}

    def latency_for(case: bench.BenchmarkCase) -> float:
        if case.decision_family == "task_classification":
            value = latencies[counter["task_classification"]]
            counter["task_classification"] += 1
            return value
        return 100.0

    report = run_with_results(tmp_path, build_full_results(latency_for=latency_for))
    task = report["families"]["task_classification"]
    assert task["latency_ms"]["measured_cases"] == 10
    assert task["latency_ms"]["p50"] == pytest.approx(55.0)
    assert task["latency_ms"]["p95"] == pytest.approx(95.5)

    aggregate = report["aggregate"]
    assert aggregate["total_cases"] == 50
    assert aggregate["valid_cases"] == 50
    assert aggregate["input_tokens"] == 50 * 200
    assert aggregate["output_tokens"] == 50 * 40
    assert aggregate["cost_usd"]["total"] == pytest.approx(50 * 0.0002)
    assert aggregate["cost_usd"]["per_1000_decisions"] == pytest.approx(0.2)


def test_family_and_aggregate_metrics_are_complete(tmp_path: Path) -> None:
    report = run_with_results(tmp_path, build_full_results())

    for family in report["families"].values():
        assert family["total_cases"] == 10
        assert family["valid_cases"] == 10
        assert family["raw_correct"] == 10
        assert family["raw_accuracy"] == pytest.approx(1.0)
        assert family["auto_decisions"] == 10
        assert family["auto_accuracy"] == pytest.approx(1.0)
        assert family["false_auto_decisions"] == 0
        assert family["high_risk_false_actions"] == 0
        assert family["escalations"] == 0
        assert family["frontier_avoidance"] == pytest.approx(1.0)
        assert family["provider_errors"] == 0
        assert family["schema_failures"] == 0

    aggregate = report["aggregate"]
    assert aggregate["total_cases"] == 50
    assert aggregate["split_counts"] == {"calibration": 25, "validation": 25}
    assert aggregate["valid_cases"] == 50
    assert aggregate["provider_errors"] == 0
    assert aggregate["schema_failures"] == 0
    assert aggregate["raw_correct"] == 50
    assert aggregate["raw_accuracy"] == pytest.approx(1.0)
    assert aggregate["auto_decisions"] == 50
    assert aggregate["auto_accuracy"] == pytest.approx(1.0)
    assert aggregate["false_auto_decisions"] == 0
    assert aggregate["high_risk_false_actions"] == 0
    assert aggregate["escalations"] == 0
    assert aggregate["frontier_avoidance"] == pytest.approx(1.0)


def test_report_carries_no_raw_state(tmp_path: Path) -> None:
    report = run_with_results(tmp_path, build_full_results())
    serialized = json.dumps(report, sort_keys=True)

    def walk_keys(node) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                assert key != "state"
                walk_keys(value)
        elif isinstance(node, list):
            for item in node:
                walk_keys(item)

    walk_keys(report)
    for record in load_corpus_records():
        stack = [record["state"]]
        while stack:
            value = stack.pop()
            if isinstance(value, str):
                if len(value) >= 12:
                    assert value not in serialized
            elif isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)


def test_report_is_non_authoritative(tmp_path: Path) -> None:
    report = run_with_results(tmp_path, build_full_results())
    assert report["authoritative_for_production"] is False
    assert report["production_consequence_forbidden"] is True
    assert report["mode"] == "offline_fixture"
    for family in report["families"].values():
        assert family["verdict"] in {"CANDIDATE", "INCONCLUSIVE"}


def test_candidate_verdict_requires_validation_auto_decisions(tmp_path: Path) -> None:
    report = run_with_results(tmp_path, build_full_results(confidence=0.9))
    for family in report["families"].values():
        assert family["verdict"] == "CANDIDATE"
        assert family["validation"]["auto_decisions"] >= 1
        assert family["validation"]["valid_cases"] == 5
        assert family["validation"]["false_auto_decisions"] == 0
    assert report["aggregate"]["families_candidate"] == 5
    assert report["aggregate"]["families_inconclusive"] == 0
    task = report["families"]["task_classification"]
    assert task["chosen_policy"] == {"kind": "min_confidence", "value": 0.9}
    evidence = report["families"]["evidence_relevance"]
    assert evidence["chosen_policy"]["kind"] == "review_band"
    assert evidence["chosen_policy"]["center"] == 0.5
    assert evidence["chosen_policy"]["margin"] == 0.4


def test_cli_is_deterministic_and_fail_closed(tmp_path: Path) -> None:
    results_path = write_results(tmp_path, build_full_results())
    output_a = tmp_path / "report-a.json"
    output_b = tmp_path / "report-b.json"
    argv = [
        "--heldout", str(HELDOUT),
        "--results", str(results_path),
        "--tuning-cases", str(TUNING_CORPORA[0]),
        "--tuning-cases", str(TUNING_CORPORA[1]),
    ]
    assert cascade.main([*argv, "--output", str(output_a)]) == 0
    assert cascade.main([*argv, "--output", str(output_b)]) == 0
    assert output_a.read_bytes() == output_b.read_bytes()
    payload = json.loads(output_a.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "jev-cascade.report.v1"

    records = load_corpus_records()
    records[0]["case_id"] = records[1]["case_id"]
    bad = write_corpus(tmp_path, records, name="bad-corpus.jsonl")
    bad_results = write_results(tmp_path, build_full_results(), name="bad-results.json")
    exit_code = cascade.main(
        [
            "--heldout", str(bad),
            "--results", str(bad_results),
            "--tuning-cases", str(TUNING_CORPORA[0]),
        ]
    )
    assert exit_code != 0
