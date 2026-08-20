"""Plain-text Telegram presentation for bounded A-Conductor operator metadata.

No Telegram SDK, parse mode, network, token, SQL, or execution dependency is
present here. The renderer accepts only the bounded ``OperatorResponse`` type.
"""

from __future__ import annotations

from .operator_protocol import OperatorResponse


TELEGRAM_OPERATOR_HELP = """A-CONDUCTOR /a commands
/a status
/a job <job-id>
/a events <job-id>
/a create <job-id> <work-order-ref> <project-id> [max-attempts]
/a ready <job-id> <version>
/a claim <job-id> <version> <worker-id>
/a gate <job-id> <version> <worker-id>
/a checkpoint <job-id> <version> <checkpoint-ref> [evidence-ref]
/a exec <job-id> <version> <worker-id> <operation-ref>

/a run ... is not a direct operator command. Conversational goals belong to Hermes/A-Wiki, which may translate approved intent into bounded A-Conductor operations.
"""


def _require_limit(value: int, *, allow_zero: bool) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("render limit must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ValueError("render limit is out of range")
    return value


def render_operator_response(
    response: OperatorResponse,
    *,
    max_refs: int = 5,
    max_chars: int = 3500,
) -> str:
    if not isinstance(response, OperatorResponse):
        raise TypeError("response must be an OperatorResponse")
    max_refs = _require_limit(max_refs, allow_zero=True)
    max_chars = _require_limit(max_chars, allow_zero=False)

    lines = ["A-CONDUCTOR OK" if response.ok else "A-CONDUCTOR ERROR"]
    lines.append(f"code: {response.code}")
    if response.job_id is not None:
        lines.append(f"job: {response.job_id}")
    if response.state is not None:
        lines.append(f"state: {response.state}")
    if response.version is not None:
        lines.append(f"version: {response.version}")
    if response.worker_id is not None:
        lines.append(f"worker: {response.worker_id}")
    if response.attempt_count is not None and response.max_attempts is not None:
        lines.append(f"attempt: {response.attempt_count}/{response.max_attempts}")
    elif response.attempt_count is not None:
        lines.append(f"attempt: {response.attempt_count}")
    elif response.max_attempts is not None:
        lines.append(f"max-attempts: {response.max_attempts}")

    visible_refs = response.refs[:max_refs]
    for ref in visible_refs:
        lines.append(f"ref: {ref}")
    hidden_count = len(response.refs) - len(visible_refs)
    if hidden_count > 0:
        lines.append(f"refs: +{hidden_count} more")

    rendered = "\n".join(lines)
    if len(rendered) <= max_chars:
        return rendered
    if max_chars == 1:
        return "…"
    suffix = "\n…"
    if max_chars <= len(suffix):
        return suffix[-max_chars:]
    return rendered[: max_chars - len(suffix)] + suffix
