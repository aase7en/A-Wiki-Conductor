"""Transport-neutral bounded operator protocol for A-Conductor.

The protocol intentionally contains no network, transport SDK, SQL, scheduler,
planner, router, subprocess, or generic command surface. Transport gateways
parse external input into these bounded requests before invoking application
services.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


OPERATOR_PROTOCOL_VERSION = "operator.v1"
_MAX_IDENTIFIER_LENGTH = 160
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._/@:-]+$")


class OperatorProtocolError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class OperatorAction(str, Enum):
    STATUS = "status"
    JOB_GET = "job.get"
    JOB_EVENTS = "job.events"
    JOB_CREATE = "job.create"
    JOB_READY = "job.ready"
    JOB_CLAIM = "job.claim"
    JOB_GATE = "job.gate"
    JOB_CHECKPOINT = "job.checkpoint"
    JOB_EXECUTE = "job.execute"


def _require_identifier(value: object) -> str:
    if not isinstance(value, str):
        raise OperatorProtocolError("OPERATOR_IDENTIFIER_INVALID")
    if not value or len(value) > _MAX_IDENTIFIER_LENGTH:
        raise OperatorProtocolError("OPERATOR_IDENTIFIER_INVALID")
    if value.startswith("-") or not _IDENTIFIER_RE.fullmatch(value):
        raise OperatorProtocolError("OPERATOR_IDENTIFIER_INVALID")
    if value == ".." or value.startswith("../") or "/../" in value or value.endswith("/.."):
        raise OperatorProtocolError("OPERATOR_IDENTIFIER_INVALID")
    return value


def _optional_identifier(value: object | None) -> str | None:
    if value is None:
        return None
    return _require_identifier(value)


def _require_positive_int(value: object, code: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise OperatorProtocolError(code)
    return value


def _require_attempt_budget(value: object) -> int:
    number = _require_positive_int(value, "OPERATOR_ATTEMPT_BUDGET_INVALID")
    if number > 100:
        raise OperatorProtocolError("OPERATOR_ATTEMPT_BUDGET_INVALID")
    return number


@dataclass(frozen=True, slots=True)
class OperatorRequest:
    protocol_version: str
    action: OperatorAction
    job_id: str | None = None
    work_order_ref: str | None = None
    project_id: str | None = None
    max_attempts: int | None = None
    expected_version: int | None = None
    worker_id: str | None = None
    checkpoint_ref: str | None = None
    evidence_ref: str | None = None
    operation_ref: str | None = None

    def __post_init__(self) -> None:
        if self.protocol_version != OPERATOR_PROTOCOL_VERSION:
            raise OperatorProtocolError("OPERATOR_VERSION_UNSUPPORTED")
        if not isinstance(self.action, OperatorAction):
            raise OperatorProtocolError("OPERATOR_ACTION_UNSUPPORTED")
        for value in (
            self.job_id,
            self.work_order_ref,
            self.project_id,
            self.worker_id,
            self.checkpoint_ref,
            self.evidence_ref,
            self.operation_ref,
        ):
            if value is not None:
                _require_identifier(value)
        if self.expected_version is not None:
            _require_positive_int(self.expected_version, "OPERATOR_VERSION_INVALID")
        if self.max_attempts is not None:
            _require_attempt_budget(self.max_attempts)


@dataclass(frozen=True, slots=True)
class OperatorResponse:
    ok: bool
    code: str
    job_id: str | None = None
    state: str | None = None
    version: int | None = None
    worker_id: str | None = None
    attempt_count: int | None = None
    max_attempts: int | None = None
    refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.ok, bool):
            raise OperatorProtocolError("OPERATOR_RESPONSE_INVALID")
        _require_identifier(self.code)
        for value in (self.job_id, self.state, self.worker_id):
            if value is not None:
                _require_identifier(value)
        if self.version is not None:
            _require_positive_int(self.version, "OPERATOR_RESPONSE_INVALID")
        if self.attempt_count is not None:
            if (
                not isinstance(self.attempt_count, int)
                or isinstance(self.attempt_count, bool)
                or self.attempt_count < 0
            ):
                raise OperatorProtocolError("OPERATOR_RESPONSE_INVALID")
        if self.max_attempts is not None:
            _require_attempt_budget(self.max_attempts)
        object.__setattr__(self, "refs", tuple(self.refs))
        for ref in self.refs:
            _require_identifier(ref)


_BASE_FIELDS = frozenset({"protocol_version", "action"})
_ACTION_REQUIRED_FIELDS: dict[OperatorAction, frozenset[str]] = {
    OperatorAction.STATUS: frozenset(),
    OperatorAction.JOB_GET: frozenset({"job_id"}),
    OperatorAction.JOB_EVENTS: frozenset({"job_id"}),
    OperatorAction.JOB_CREATE: frozenset({"job_id", "work_order_ref", "project_id"}),
    OperatorAction.JOB_READY: frozenset({"job_id", "expected_version"}),
    OperatorAction.JOB_CLAIM: frozenset({"job_id", "expected_version", "worker_id"}),
    OperatorAction.JOB_GATE: frozenset({"job_id", "expected_version", "worker_id"}),
    OperatorAction.JOB_CHECKPOINT: frozenset(
        {"job_id", "expected_version", "checkpoint_ref"}
    ),
    OperatorAction.JOB_EXECUTE: frozenset(
        {"job_id", "expected_version", "worker_id", "operation_ref"}
    ),
}
_ACTION_OPTIONAL_FIELDS: dict[OperatorAction, frozenset[str]] = {
    OperatorAction.STATUS: frozenset(),
    OperatorAction.JOB_GET: frozenset(),
    OperatorAction.JOB_EVENTS: frozenset(),
    OperatorAction.JOB_CREATE: frozenset({"max_attempts"}),
    OperatorAction.JOB_READY: frozenset(),
    OperatorAction.JOB_CLAIM: frozenset(),
    OperatorAction.JOB_GATE: frozenset(),
    OperatorAction.JOB_CHECKPOINT: frozenset({"evidence_ref"}),
    OperatorAction.JOB_EXECUTE: frozenset(),
}


def parse_operator_request(payload: Mapping[str, object]) -> OperatorRequest:
    if not isinstance(payload, Mapping):
        raise OperatorProtocolError("OPERATOR_FIELDS_INVALID")
    keys = set(payload.keys())
    if any(not isinstance(key, str) for key in keys):
        raise OperatorProtocolError("OPERATOR_FIELDS_INVALID")

    version = payload.get("protocol_version")
    if version != OPERATOR_PROTOCOL_VERSION:
        raise OperatorProtocolError("OPERATOR_VERSION_UNSUPPORTED")

    raw_action = payload.get("action")
    if not isinstance(raw_action, str):
        raise OperatorProtocolError("OPERATOR_ACTION_UNSUPPORTED")
    try:
        action = OperatorAction(raw_action)
    except ValueError as exc:
        raise OperatorProtocolError("OPERATOR_ACTION_UNSUPPORTED") from exc

    required = _ACTION_REQUIRED_FIELDS[action]
    optional = _ACTION_OPTIONAL_FIELDS[action]
    allowed = _BASE_FIELDS | required | optional
    if keys != allowed and not (required | _BASE_FIELDS).issubset(keys):
        raise OperatorProtocolError("OPERATOR_FIELDS_INVALID")
    if not keys.issubset(allowed):
        raise OperatorProtocolError("OPERATOR_FIELDS_INVALID")

    values: dict[str, object] = {}
    for field_name in required | optional:
        if field_name in payload:
            values[field_name] = payload[field_name]

    identifier_fields = {
        "job_id",
        "work_order_ref",
        "project_id",
        "worker_id",
        "checkpoint_ref",
        "evidence_ref",
        "operation_ref",
    }
    for field_name in identifier_fields:
        if field_name in values:
            values[field_name] = _require_identifier(values[field_name])

    if "expected_version" in values:
        values["expected_version"] = _require_positive_int(
            values["expected_version"],
            "OPERATOR_VERSION_INVALID",
        )
    if "max_attempts" in values:
        values["max_attempts"] = _require_attempt_budget(values["max_attempts"])
    elif action is OperatorAction.JOB_CREATE:
        values["max_attempts"] = 3

    return OperatorRequest(
        protocol_version=OPERATOR_PROTOCOL_VERSION,
        action=action,
        **values,
    )
