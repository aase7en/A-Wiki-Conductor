from __future__ import annotations

from a_conductor.operator_protocol import OperatorResponse
from a_conductor.telegram_operator_render import (
    TELEGRAM_OPERATOR_HELP,
    render_operator_response,
)


def test_success_response_renders_bounded_job_metadata() -> None:
    text = render_operator_response(
        OperatorResponse(
            ok=True,
            code="OK",
            job_id="job-104",
            state="VERIFYING",
            version=5,
            worker_id="a-worker-02",
            attempt_count=1,
            max_attempts=3,
            refs=("native:sha256:abc123",),
        )
    )
    assert text.splitlines()[0] == "A-CONDUCTOR OK"
    assert "code: OK" in text
    assert "job: job-104" in text
    assert "state: VERIFYING" in text
    assert "version: 5" in text
    assert "worker: a-worker-02" in text
    assert "attempt: 1/3" in text
    assert "ref: native:sha256:abc123" in text


def test_failure_response_is_plain_and_code_first() -> None:
    text = render_operator_response(
        OperatorResponse(
            ok=False,
            code="JOB_VERSION_CONFLICT",
            job_id="job-1",
            state="CLAIMED",
            version=4,
        )
    )
    assert text.splitlines()[0] == "A-CONDUCTOR ERROR"
    assert "code: JOB_VERSION_CONFLICT" in text
    assert "version: 4" in text
    assert "<" not in text
    assert ">" not in text


def test_refs_are_capped_and_overflow_is_summarized() -> None:
    refs = tuple(f"evidence:{index}" for index in range(8))
    text = render_operator_response(
        OperatorResponse(ok=True, code="OK", refs=refs),
        max_refs=3,
    )
    assert "ref: evidence:0" in text
    assert "ref: evidence:2" in text
    assert "evidence:3" not in text
    assert "refs: +5 more" in text


def test_zero_ref_cap_only_reports_count() -> None:
    text = render_operator_response(
        OperatorResponse(ok=True, code="OK", refs=("evidence:1", "evidence:2")),
        max_refs=0,
    )
    assert "ref:" not in text
    assert "refs: +2 more" in text


def test_output_length_is_bounded() -> None:
    response = OperatorResponse(
        ok=True,
        code="OK",
        job_id="j" * 160,
        state="VERIFYING",
        worker_id="w" * 160,
        refs=tuple("r" * 160 for _ in range(10)),
    )
    text = render_operator_response(response, max_chars=220)
    assert len(text) <= 220
    assert text.endswith("\n…")


def test_renderer_has_no_raw_output_or_secret_vocabulary() -> None:
    text = render_operator_response(OperatorResponse(ok=True, code="OK"))
    lower = text.lower()
    for forbidden in ("stdout", "stderr", "token", "secret", "prompt", "command", "argv"):
        assert forbidden not in lower


def test_help_lists_only_bounded_commands_and_explains_hermes_macro_boundary() -> None:
    help_text = TELEGRAM_OPERATOR_HELP
    for command in (
        "/a status",
        "/a job <job-id>",
        "/a events <job-id>",
        "/a create",
        "/a ready",
        "/a claim",
        "/a gate",
        "/a checkpoint",
        "/a exec",
    ):
        assert command in help_text
    assert "/a run" in help_text
    assert "Hermes/A-Wiki" in help_text
    assert "not a direct operator command" in help_text


def test_renderer_rejects_invalid_limits() -> None:
    response = OperatorResponse(ok=True, code="OK")
    for kwargs in ({"max_refs": -1}, {"max_chars": 0}, {"max_refs": True}):
        try:
            render_operator_response(response, **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {kwargs}")
