"""WO-P1-752 — pure route/usage telemetry baseline projection tests.

The projection composes per-attempt evidence from injected inputs only. It
owns no clock, network, or store; absent evidence stays typed-unavailable and
is never fabricated into zero.
"""

from __future__ import annotations

import ast
import builtins
import copy
import json
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from a_conductor.provider_fallback_policy import (
    REASON_ELIGIBLE_NOT_SELECTED,
    REASON_QUOTA_EXHAUSTED,
    REASON_SELECTED,
    CandidateEvaluation,
    ProviderFallbackSelectionResult,
    SelectionOutcome,
    SelectionStage,
)
from a_conductor.semantic_admission import (
    SemanticAdmissionTelemetry,
    SemanticDecisionFamily,
    SemanticDecisionMode,
    SemanticDecisionReason,
    SemanticDisposition,
    SemanticFallbackReason,
)
from a_conductor.route_telemetry_projection import (
    COST_REASON_CURRENCY_ABSENT,
    COST_REASON_PRICING_ABSENT,
    COST_REASON_USAGE_ABSENT,
    COST_STATE_KNOWN,
    COST_STATE_UNKNOWN,
    EVIDENCE_STATE_AVAILABLE,
    EVIDENCE_STATE_UNAVAILABLE,
    LATENCY_CLOCK_MONOTONIC,
    RECEIPT_STATUS_ACCEPTED,
    RECEIPT_STATUS_QUARANTINED,
    SELECTION_ABSENT_REASON,
    TELEMETRY_ABSENT_REASON,
    TOKEN_USAGE_ABSENT_REASON,
    USAGE_STATE_MEASURED,
    WALL_STAMP_CLOCK,
    RouteAttemptInput,
    RouteUnitPricing,
    project_route_telemetry,
)


def make_semantic(**overrides) -> SemanticAdmissionTelemetry:
    data = dict(
        family=SemanticDecisionFamily.TASK_CLASSIFICATION,
        mode=SemanticDecisionMode.OFF,
        disposition=SemanticDisposition.BYPASS,
        decision_reason=SemanticDecisionReason.MODE_OFF,
        fallback_reason=SemanticFallbackReason.MODE_OFF,
        input_usage=None,
        output_usage=None,
        latency_ms=None,
    )
    data.update(overrides)
    return SemanticAdmissionTelemetry(**data)


def make_evaluation(
    provider_id="provider-a",
    model_id="model-a",
    stage=SelectionStage.AUTHORIZED,
    eligible=True,
    reason_code=REASON_ELIGIBLE_NOT_SELECTED,
    generation=7,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        provider_id=provider_id,
        model_id=model_id,
        expected_configuration_generation=generation,
        stage=stage,
        eligible=eligible,
        reason_code=reason_code,
    )


def make_selection(
    *evaluations,
    outcome=SelectionOutcome.SELECTED,
    provider_id="provider-a",
    model_id="model-a",
    reason_code=REASON_SELECTED,
    generation=7,
) -> ProviderFallbackSelectionResult:
    selected = outcome is SelectionOutcome.SELECTED
    return ProviderFallbackSelectionResult(
        outcome=outcome,
        provider_id=provider_id if selected else None,
        model_id=model_id if selected else None,
        expected_configuration_generation=generation if selected else None,
        requested_effort="DEFAULT",
        reason_code=reason_code if selected else outcome.value,
        evaluations=tuple(evaluations),
    )


def test_wo752_duplicate_identity_dedup_with_duplicate_of_pointer() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_QUARANTINED,
            ),
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_ACCEPTED,
            ),
        )
    )
    assert evidence.attempts[0].duplicate_of is None
    assert evidence.attempts[1].duplicate_of == 0
    assert evidence.attempted_attempt_count == 1
    assert evidence.duplicate_row_count == 1
    # the retried row's ACCEPTED receipt is honored once, never double-counted
    assert evidence.accepted_attempt_count == 1
    assert evidence.attempts[0].accepted is False
    assert evidence.attempts[1].accepted is True


def test_wo752_fallback_retry_chain_attempted_vs_accepted() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                receipt_status=RECEIPT_STATUS_QUARANTINED,
                semantic=make_semantic(
                    disposition=SemanticDisposition.ESCALATE,
                    decision_reason=SemanticDecisionReason.PROVIDER_ERROR,
                    fallback_reason=SemanticFallbackReason.PROVIDER_RATE_LIMIT,
                ),
            ),
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-2",
                receipt_status=RECEIPT_STATUS_ACCEPTED,
                semantic=make_semantic(),
            ),
        )
    )
    assert evidence.attempted_attempt_count == 2
    assert evidence.accepted_attempt_count == 1
    assert evidence.duplicate_row_count == 0
    assert evidence.attempts[0].fallback_reason == "PROVIDER_RATE_LIMIT"
    assert evidence.attempts[0].disposition == "ESCALATE"
    assert evidence.attempts[0].accepted is False
    assert evidence.attempts[1].accepted is True


def test_wo752_absent_usage_pricing_currency_is_unknown_never_zero() -> None:
    # no semantic telemetry at all
    bare = project_route_telemetry(
        attempts=(RouteAttemptInput(execution_id="exec-1", attempt_id="att-1"),)
    ).attempts[0]
    assert bare.cost.state == COST_STATE_UNKNOWN
    assert bare.cost.reason == COST_REASON_USAGE_ABSENT
    assert bare.cost.amount is None
    assert bare.cost.input_usage is None
    assert bare.cost.output_usage is None
    assert 0 not in (bare.cost.input_usage, bare.cost.output_usage)

    # usage measured, pricing absent
    usage_only = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
            ),
        )
    ).attempts[0]
    assert usage_only.cost.state == COST_STATE_UNKNOWN
    assert usage_only.cost.reason == COST_REASON_PRICING_ABSENT

    # usage + pricing, currency absent
    no_currency = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
            ),
        )
    ).attempts[0]
    assert no_currency.cost.state == COST_STATE_UNKNOWN
    assert no_currency.cost.reason == COST_REASON_CURRENCY_ABSENT

    # everything present -> KNOWN, never silently zero
    known = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=10, output_usage=4),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
                currency="USD",
            ),
        )
    ).attempts[0]
    assert known.cost.state == COST_STATE_KNOWN
    assert known.cost.reason == "COST_KNOWN"
    assert known.cost.amount == pytest.approx(10 / 1000 * 0.5 + 4 / 1000 * 1.5)
    assert known.cost.currency == "USD"
    assert known.cost.to_dict()["state"] == "KNOWN"


def test_wo752_wall_vs_monotonic_labeled_distinctly() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(latency_ms=12.0, input_usage=3, output_usage=1),
                started_at_wall="2026-11-13T10:00:00Z",
                finished_at_wall="2026-11-13T10:00:05Z",
            ),
            RouteAttemptInput(execution_id="exec-1", attempt_id="att-2"),
        )
    )
    first = evidence.attempts[0]
    assert first.latency_ms == pytest.approx(12.0)
    assert first.latency_clock == "MONOTONIC"
    assert first.started_at_wall == "2026-11-13T10:00:00Z"
    assert first.finished_at_wall == "2026-11-13T10:00:05Z"
    assert first.wall_stamp_clock == WALL_STAMP_CLOCK == "WALL"

    second = evidence.attempts[1]
    assert second.latency_ms is None
    assert second.latency_clock == "UNAVAILABLE"
    assert second.started_at_wall is None
    assert second.finished_at_wall is None
    assert second.wall_stamp_clock == "UNAVAILABLE"
    assert first.latency_clock != first.wall_stamp_clock


def test_wo752_telemetry_absent_degrades_only_its_fields() -> None:
    evidence = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                selection=make_selection(make_evaluation()),
                receipt_status=RECEIPT_STATUS_ACCEPTED,
            ),
        )
    )
    row = evidence.attempts[0]
    assert row.telemetry_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.telemetry_unavailable_reason == TELEMETRY_ABSENT_REASON
    assert row.usage_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.usage_unavailable_reason == TELEMETRY_ABSENT_REASON
    assert row.latency_clock == "UNAVAILABLE"
    # everything else still projects; the object is still returned
    assert row.selection.state == EVIDENCE_STATE_AVAILABLE
    assert row.selection.reason_code == REASON_SELECTED
    assert row.receipt_state == EVIDENCE_STATE_AVAILABLE
    assert row.accepted is True
    assert row.cost.state == COST_STATE_UNKNOWN
    assert row.cost.reason == COST_REASON_USAGE_ABSENT


def test_wo752_semantic_present_but_usage_absent_is_typed_unavailable() -> None:
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(),
            ),
        )
    ).attempts[0]
    assert row.telemetry_state == EVIDENCE_STATE_AVAILABLE
    assert row.telemetry_unavailable_reason is None
    assert row.usage_state == EVIDENCE_STATE_UNAVAILABLE
    assert row.usage_unavailable_reason == TOKEN_USAGE_ABSENT_REASON
    assert row.input_usage is None
    assert row.output_usage is None


def test_wo752_zero_usage_stays_distinguishable_from_absent() -> None:
    zero = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                semantic=make_semantic(input_usage=0, output_usage=0),
                pricing=RouteUnitPricing(
                    input_cost_per_thousand_tokens=0.5,
                    output_cost_per_thousand_tokens=1.5,
                ),
                currency="USD",
            ),
        )
    ).attempts[0]
    assert zero.usage_state == USAGE_STATE_MEASURED
    assert zero.usage_unavailable_reason is None
    assert zero.input_usage == 0
    assert zero.output_usage == 0
    assert zero.cost.state == COST_STATE_KNOWN
    assert zero.cost.amount == pytest.approx(0.0)


def test_wo752_correlation_conflict_fails_closed() -> None:
    with pytest.raises(ValueError, match="correlation identity mismatch"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    semantic=make_semantic(
                        execution_id="exec-9",
                        attempt_id="att-1",
                    ),
                ),
            )
        )
    with pytest.raises(ValueError, match="correlation identity mismatch"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="req-1",
                    semantic=make_semantic(request_id="req-2"),
                ),
            )
        )


def test_wo752_matching_correlation_passes_through() -> None:
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                request_id="req-1",
                semantic=make_semantic(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="req-1",
                ),
            ),
        )
    ).attempts[0]
    assert (row.execution_id, row.attempt_id, row.request_id) == (
        "exec-1",
        "att-1",
        "req-1",
    )


# --- WO-P1-765 card-06: type-strict correlation identity ---


class _DuckSemantic:
    """Shape-conforming semantic telemetry with a non-str correlation id.

    The projection accepts injected semantic rows by shape, not by class, so
    upstream ``_safe_identity`` str validation cannot be assumed for them.
    """

    def __init__(self, request_id: object) -> None:
        self.input_usage = None
        self.output_usage = None
        self.latency_ms = None
        self.execution_id = "exec-1"
        self.attempt_id = "att-1"
        self.request_id = request_id


class _SubStr(str):
    """str subclass carrying a non-plain correlation identity."""


def test_wo765_non_str_correlation_identity_is_typed_rejected_not_coerced() -> None:
    # int 7 vs row "7" previously passed via str()-coercion comparison
    with pytest.raises(ValueError, match="must be plain text"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="7",
                    semantic=_DuckSemantic(request_id=7),
                ),
            )
        )
    # a str subclass is likewise not a plain-text correlation identity
    with pytest.raises(ValueError, match="must be plain text"):
        project_route_telemetry(
            attempts=(
                RouteAttemptInput(
                    execution_id="exec-1",
                    attempt_id="att-1",
                    request_id="req-1",
                    semantic=_DuckSemantic(request_id=_SubStr("req-1")),
                ),
            )
        )


def test_wo752_selection_summary_reason_and_shortlist() -> None:
    selection = make_selection(
        make_evaluation(reason_code=REASON_SELECTED),
        make_evaluation(
            provider_id="provider-b",
            model_id="model-b",
            eligible=False,
            reason_code=REASON_QUOTA_EXHAUSTED,
        ),
    )
    row = project_route_telemetry(
        attempts=(
            RouteAttemptInput(
                execution_id="exec-1",
                attempt_id="att-1",
                selection=selection,
            ),
        )
    ).attempts[0]
    assert row.selection.state == EVIDENCE_STATE_AVAILABLE
    assert row.selection.unavailable_reason is None
    assert row.selection.outcome == "SELECTED"
    assert row.selection.reason_code == REASON_SELECTED
    assert row.selection.selected_provider_id == "provider-a"
    assert row.selection.selected_model_id == "model-a"
    assert row.selection.expected_configuration_generation == 7
    assert len(row.selection.shortlist) == 2
    assert row.selection.shortlist[0].provider_id == "provider-a"
    assert row.selection.shortlist[0].stage == "AUTHORIZED"
    assert row.selection.shortlist[0].eligible is True
    assert row.selection.shortlist[1].reason_code == REASON_QUOTA_EXHAUSTED


def test_wo752_selection_absent_is_typed_unavailable() -> None:
    row = project_route_telemetry(
        attempts=(RouteAttemptInput(execution_id="exec-1", attempt_id="att-1"),)
    ).attempts[0]
    assert row.selection.state == EVIDENCE_STATE_UNAVAILABLE
    assert row.selection.unavailable_reason == SELECTION_ABSENT_REASON
    assert row.selection.reason_code is None
    assert row.selection.shortlist == ()
    assert row.selection.selected_provider_id is None


def test_wo752_empty_attempts_returns_object_with_zero_counts() -> None:
    evidence = project_route_telemetry(attempts=())
    assert evidence.attempts == ()
    assert evidence.attempted_attempt_count == 0
    assert evidence.accepted_attempt_count == 0
    assert evidence.duplicate_row_count == 0


def test_wo752_invalid_inputs_fail_closed() -> None:
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="  ", attempt_id="att-1")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="att-1", receipt_status="RUNNING")
    with pytest.raises(ValueError):
        RouteAttemptInput(execution_id="exec-1", attempt_id="att-1", currency="  ")
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            pricing=RouteUnitPricing(
                input_cost_per_thousand_tokens=-1.0,
                output_cost_per_thousand_tokens=1.5,
            ),
        )
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            selection=("not-a-selection",),
        )
    with pytest.raises(ValueError):
        RouteAttemptInput(
            execution_id="exec-1",
            attempt_id="att-1",
            semantic=("not-a-telemetry",),
        )
    with pytest.raises(ValueError):
        project_route_telemetry(attempts=("not-a-row",))
    with pytest.raises(ValueError):
        project_route_telemetry(attempts=None)


# --- WO-P1-787 G1: route telemetry purity trio ---

MODULE_SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "a_conductor"
    / "route_telemetry_projection.py"
)

# Provider/network/subprocess I/O surfaces the projection must never import
# (WO-P1-787 G1.1). ``a_conductor.provider`` prefixes every provider admission
# module; plain provider-agnostic stdlib imports stay out of scope on purpose.
_FORBIDDEN_IMPORT_ROOTS = (
    "urllib",
    "http",
    "requests",
    "socket",
    "subprocess",
    "ssl",
    "ftplib",
    "smtplib",
    "telnetlib",
    "httpx",
    "aiohttp",
    "urllib3",
    "a_conductor.provider",
)

# Executed in a fresh interpreter (WO-P1-787 G1.2): loads the projection file
# via importlib file-location isolation (no ``a_conductor`` package __init__),
# proves it still composes evidence, and reports any forbidden module that
# entered ``sys.modules`` as a side effect of the import.
_PURITY_PROBE_SCRIPT = """\
import importlib.util
import json
import sys

path = sys.argv[1]
spec = importlib.util.spec_from_file_location("wo787_purity_probe", path)
probe = importlib.util.module_from_spec(spec)
# dataclass() reads sys.modules[cls.__module__]; the probe module must be
# registered before exec_module (importlib documented loading pattern).
sys.modules["wo787_purity_probe"] = probe
spec.loader.exec_module(probe)
evidence = probe.project_route_telemetry(attempts=())
forbidden = (
    "urllib", "http", "requests", "socket", "subprocess", "ssl",
    "ftplib", "smtplib", "telnetlib", "httpx", "aiohttp", "urllib3",
)
loaded = sorted(
    name
    for name in sys.modules
    if name.split(".")[0] in forbidden or "a_conductor.provider" in name
)
print(json.dumps({
    "attempted_attempt_count": evidence.attempted_attempt_count,
    "accepted_attempt_count": evidence.accepted_attempt_count,
    "loaded_forbidden_modules": loaded,
}))
"""


def _collect_import_names(source_text: str) -> list[str]:
    tree = ast.parse(source_text)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def test_module_source_imports_are_pure_allowlist() -> None:
    source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
    violations = [
        name
        for name in _collect_import_names(source)
        if name.startswith(_FORBIDDEN_IMPORT_ROOTS)
    ]
    assert violations == [], (
        "route telemetry projection must not import provider/network/"
        f"subprocess I/O modules; found: {violations}"
    )


def test_runtime_import_graph_has_no_provider_modules() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", _PURITY_PROBE_SCRIPT, str(MODULE_SOURCE_PATH)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["attempted_attempt_count"] == 0
    assert report["accepted_attempt_count"] == 0
    assert report["loaded_forbidden_modules"] == []


class _MutableDuckSemantic:
    """Shape-conforming semantic row that CAN be mutated in place.

    Frozen typed fixtures cannot observe in-place mutation; this duck row can,
    so fixture preservation is actually verified rather than assumed.
    """

    def __init__(self) -> None:
        self.input_usage = 12
        self.output_usage = 5
        self.latency_ms = 42.5
        self.fallback_reason = "PROVIDER_RATE_LIMIT"
        self.disposition = "ESCALATE"
        self.execution_id = "exec-io"
        self.attempt_id = "att-io"
        self.request_id = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _MutableDuckSemantic):
            return NotImplemented
        return vars(self) == vars(other)


def _io_sentinel(what: str):
    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError(f"projection attempted real {what}")

    return _forbidden


def test_projection_performs_no_io_and_does_not_mutate_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selection = make_selection(
        make_evaluation(),
        make_evaluation(
            provider_id="provider-b",
            model_id="model-b",
            eligible=False,
            reason_code=REASON_QUOTA_EXHAUSTED,
        ),
    )
    duck_semantic = _MutableDuckSemantic()
    pricing = RouteUnitPricing(
        input_cost_per_thousand_tokens=0.5,
        output_cost_per_thousand_tokens=1.5,
    )
    attempts = (
        RouteAttemptInput(
            execution_id="exec-io",
            attempt_id="att-1",
            request_id="req-io",
            selection=selection,
            semantic=make_semantic(
                input_usage=10,
                output_usage=4,
                latency_ms=12.0,
                execution_id="exec-io",
                attempt_id="att-1",
            ),
            started_at_wall="2026-11-23T10:00:00Z",
            finished_at_wall="2026-11-23T10:00:02Z",
            receipt_status=RECEIPT_STATUS_ACCEPTED,
            pricing=pricing,
            currency="USD",
        ),
        RouteAttemptInput(
            execution_id="exec-io",
            attempt_id="att-io",
            selection=selection,
            semantic=duck_semantic,
            receipt_status=RECEIPT_STATUS_QUARANTINED,
        ),
    )
    fixture_snapshot = copy.deepcopy(attempts)

    monkeypatch.setattr(socket, "socket", _io_sentinel("socket"))
    monkeypatch.setattr(urllib.request, "urlopen", _io_sentinel("urlopen"))
    monkeypatch.setattr(builtins, "open", _io_sentinel("builtins.open"))
    monkeypatch.setattr(subprocess, "run", _io_sentinel("subprocess.run"))
    monkeypatch.setattr(subprocess, "Popen", _io_sentinel("subprocess.Popen"))

    first = project_route_telemetry(attempts=attempts)
    second = project_route_telemetry(attempts=attempts)

    assert first == second
    assert attempts == fixture_snapshot
