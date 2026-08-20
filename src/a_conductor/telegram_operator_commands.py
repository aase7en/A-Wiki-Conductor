"""Pure Telegram `/a ...` command mapper for the A-Conductor operator protocol.

This module does not call Telegram, authenticate users, open network sockets,
or execute work. It only maps a deliberately small token grammar into
``operator.v1`` requests.
"""

from __future__ import annotations

import re

from .operator_protocol import (
    OPERATOR_PROTOCOL_VERSION,
    OperatorProtocolError,
    OperatorRequest,
    parse_operator_request,
)


_MAX_COMMAND_LENGTH = 512
_BOT_SUFFIX_RE = re.compile(r"^/a@[A-Za-z0-9_]{5,32}$")
_DECIMAL_RE = re.compile(r"^[0-9]+$")


class TelegramOperatorCommandError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _number(token: str) -> int:
    if not _DECIMAL_RE.fullmatch(token):
        raise TelegramOperatorCommandError("TELEGRAM_NUMBER_INVALID")
    try:
        return int(token)
    except ValueError as exc:
        raise TelegramOperatorCommandError("TELEGRAM_NUMBER_INVALID") from exc


def _request(action: str, **fields: object) -> OperatorRequest:
    try:
        return parse_operator_request(
            {
                "protocol_version": OPERATOR_PROTOCOL_VERSION,
                "action": action,
                **fields,
            }
        )
    except OperatorProtocolError as exc:
        raise TelegramOperatorCommandError(exc.code) from exc


def parse_telegram_operator_command(text: str) -> OperatorRequest:
    if not isinstance(text, str) or not text.strip() or len(text) > _MAX_COMMAND_LENGTH:
        raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
    if "\n" in text or "\r" in text or "\x00" in text:
        raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")

    tokens = text.strip().split()
    if not tokens:
        raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")

    prefix = tokens[0]
    if prefix == "/a":
        pass
    elif prefix.startswith("/a@"):
        if not _BOT_SUFFIX_RE.fullmatch(prefix):
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
    else:
        raise TelegramOperatorCommandError("TELEGRAM_NOT_A_CONDUCTOR_COMMAND")

    if len(tokens) < 2:
        raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")

    command = tokens[1]

    if command == "status":
        if len(tokens) != 2:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request("status")

    if command == "job":
        if len(tokens) != 3:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request("job.get", job_id=tokens[2])

    if command == "events":
        if len(tokens) != 3:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request("job.events", job_id=tokens[2])

    if command == "create":
        if len(tokens) not in {5, 6}:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        payload: dict[str, object] = {
            "job_id": tokens[2],
            "work_order_ref": tokens[3],
            "project_id": tokens[4],
        }
        if len(tokens) == 6:
            payload["max_attempts"] = _number(tokens[5])
        return _request("job.create", **payload)

    if command == "ready":
        if len(tokens) != 4:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request(
            "job.ready",
            job_id=tokens[2],
            expected_version=_number(tokens[3]),
        )

    if command in {"claim", "gate"}:
        if len(tokens) != 5:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request(
            f"job.{command}",
            job_id=tokens[2],
            expected_version=_number(tokens[3]),
            worker_id=tokens[4],
        )

    if command == "checkpoint":
        if len(tokens) not in {5, 6}:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        payload = {
            "job_id": tokens[2],
            "expected_version": _number(tokens[3]),
            "checkpoint_ref": tokens[4],
        }
        if len(tokens) == 6:
            payload["evidence_ref"] = tokens[5]
        return _request("job.checkpoint", **payload)

    if command == "exec":
        if len(tokens) != 6:
            raise TelegramOperatorCommandError("TELEGRAM_COMMAND_INVALID")
        return _request(
            "job.execute",
            job_id=tokens[2],
            expected_version=_number(tokens[3]),
            worker_id=tokens[4],
            operation_ref=tokens[5],
        )

    raise TelegramOperatorCommandError("TELEGRAM_COMMAND_UNSUPPORTED")
