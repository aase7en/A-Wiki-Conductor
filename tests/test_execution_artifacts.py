from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from a_conductor.execution_artifacts import (
    ExecutionArtifactError,
    ExecutionArtifactKind,
    ExecutionArtifactService,
)
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore


def create_record(
    tmp_path: Path,
    *,
    stdout_ref: str = "runs/exec-001/stdout.log",
    stderr_ref: str = "runs/exec-001/stderr.log",
    report_ref: str | None = "runs/exec-001/report.txt",
):
    repo = tmp_path / "repo"
    run_dir = repo / "runs" / "exec-001"
    run_dir.mkdir(parents=True, exist_ok=True)
    store = SQLiteExecutionStore(tmp_path / "control.sqlite")
    record = store.create(
        new_execution_record(
            execution_id="exec-001",
            job_id="job-001",
            work_order_ref="wo",
            project_id="project-1",
            worker_id="a-worker-01",
            backend_id="native-local",
            agent_ref=None,
            repo_root=str(repo.resolve()),
            branch="main",
            head_before="a" * 40,
            operation_ref="op:pytest",
            command_fingerprint="b" * 64,
            command_summary="pytest",
            runtime_profile_ref=None,
            run_dir_ref="runs/exec-001",
            stdout_ref=stdout_ref,
            stderr_ref=stderr_ref,
            result_ref="runs/exec-001/result.json",
            report_ref=report_ref,
            transport_state=TransportState.CONNECTED,
            execution_state=ExecutionProcessState.VERIFICATION_REQUIRED,
        )
    )
    return repo, run_dir, store, record


def test_tail_is_bounded_but_digest_covers_full_file(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    payload = (b"line-0123456789\n" * 10000) + b"FINAL-LINE\n"
    path = run_dir / "stdout.log"
    path.write_bytes(payload)
    service = ExecutionArtifactService(store=store)

    result = service.read_tail("exec-001", ExecutionArtifactKind.STDOUT, max_bytes=1024)

    assert result.total_bytes == len(payload)
    assert result.returned_bytes <= 1024
    assert result.truncated is True
    assert result.text.endswith("FINAL-LINE\n")
    assert result.sha256 == hashlib.sha256(payload).hexdigest()
    assert len(result.text.encode("utf-8")) <= 1024


def test_chunk_reads_exact_bounded_window(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    payload = bytes(range(256)) * 20
    (run_dir / "stderr.log").write_bytes(payload)
    service = ExecutionArtifactService(store=store)

    result = service.read_chunk(
        "exec-001",
        ExecutionArtifactKind.STDERR,
        offset=300,
        max_bytes=137,
    )

    assert result.offset == 300
    assert result.returned_bytes == 137
    assert result.raw == payload[300:437]
    assert result.total_bytes == len(payload)
    assert result.truncated is True


def test_read_budget_has_hard_upper_bound(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    (run_dir / "stdout.log").write_text("x", encoding="utf-8")
    service = ExecutionArtifactService(store=store)

    for invalid in (0, -1, 65537, 10**9):
        with pytest.raises(ValueError):
            service.read_tail("exec-001", ExecutionArtifactKind.STDOUT, max_bytes=invalid)


def test_invalid_utf8_decodes_with_replacement_without_losing_raw_digest(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    payload = b"good\xff\xfeend"
    (run_dir / "stdout.log").write_bytes(payload)

    result = ExecutionArtifactService(store=store).read_tail(
        "exec-001", ExecutionArtifactKind.STDOUT, max_bytes=64
    )

    assert "\ufffd" in result.text
    assert result.raw == payload
    assert result.sha256 == hashlib.sha256(payload).hexdigest()


def test_unconfigured_or_missing_artifact_has_explicit_error(tmp_path: Path) -> None:
    _, _, store, _ = create_record(tmp_path, report_ref=None)
    service = ExecutionArtifactService(store=store)

    with pytest.raises(ExecutionArtifactError) as unconfigured:
        service.read_tail("exec-001", ExecutionArtifactKind.REPORT, max_bytes=100)
    assert unconfigured.value.code == "ARTIFACT_NOT_CONFIGURED"

    with pytest.raises(ExecutionArtifactError) as missing:
        service.read_tail("exec-001", ExecutionArtifactKind.STDOUT, max_bytes=100)
    assert missing.value.code == "ARTIFACT_NOT_FOUND"


def test_traversal_ref_is_blocked_before_file_read(tmp_path: Path) -> None:
    _, _, store, _ = create_record(tmp_path, stdout_ref="../outside.log")
    service = ExecutionArtifactService(store=store)

    with pytest.raises(ExecutionArtifactError) as exc_info:
        service.read_tail("exec-001", ExecutionArtifactKind.STDOUT, max_bytes=100)
    assert exc_info.value.code == "ARTIFACT_OUTSIDE_RUN_DIR"


def test_symlink_escape_is_blocked_when_platform_allows_symlink(tmp_path: Path) -> None:
    repo, run_dir, store, _ = create_record(tmp_path)
    outside = tmp_path / "outside.log"
    outside.write_text("secret-outside", encoding="utf-8")
    link = run_dir / "stdout.log"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation unavailable on this Windows configuration")

    with pytest.raises(ExecutionArtifactError) as exc_info:
        ExecutionArtifactService(store=store).read_tail(
            "exec-001", ExecutionArtifactKind.STDOUT, max_bytes=100
        )
    assert exc_info.value.code == "ARTIFACT_OUTSIDE_RUN_DIR"
    assert repo.resolve() not in outside.resolve().parents


def test_pytest_summary_extracts_known_counts_and_duration_from_bounded_tail(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    log = """many lines before\n================ short test summary info ================\nFAILED tests/test_a.py::test_a\n2 failed, 210 passed, 3 skipped, 4 warnings in 66.20s\n"""
    (run_dir / "stdout.log").write_text(log, encoding="utf-8")
    service = ExecutionArtifactService(store=store)

    summary = service.summarize_pytest("exec-001", max_tail_bytes=4096)

    assert summary.passed == 210
    assert summary.failed == 2
    assert summary.skipped == 3
    assert summary.warnings == 4
    assert summary.duration_seconds == 66.20
    assert summary.source_truncated is False


def test_pytest_summary_does_not_invent_missing_counts(tmp_path: Path) -> None:
    _, run_dir, store, _ = create_record(tmp_path)
    (run_dir / "stdout.log").write_text("17 passed in 1.23s\n", encoding="utf-8")

    summary = ExecutionArtifactService(store=store).summarize_pytest(
        "exec-001", max_tail_bytes=1024
    )

    assert summary.passed == 17
    assert summary.failed is None
    assert summary.skipped is None
    assert summary.warnings is None
    assert summary.duration_seconds == 1.23


def test_service_exposes_no_arbitrary_path_or_mutation_surface(tmp_path: Path) -> None:
    _, _, store, _ = create_record(tmp_path)
    service = ExecutionArtifactService(store=store)
    for forbidden in (
        "read_path",
        "open_path",
        "delete",
        "truncate",
        "rotate",
        "write",
        "launch",
        "retry",
        "execute",
        "push",
    ):
        assert not hasattr(service, forbidden)
