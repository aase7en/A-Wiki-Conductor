from __future__ import annotations

import ast
import hashlib
import os
from dataclasses import replace
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import AgentRepairRequest, build_repair_task_markdown
from a_conductor.native_execution import (
    NativeExecutionError,
    NativeExecutionScope,
    NativeFileSystem,
    NativeReadResult,
)
from a_conductor.zero_relay_repair_materializer import (
    RepairTaskMaterializationError,
    RepairTaskMaterializationRequest,
    materialize_repair_task,
)


TASK_SHA = "1" * 64
RESULT_SHA = "2" * 64


def repair_request(*, task_id: str = "repair-001") -> AgentRepairRequest:
    return AgentRepairRequest(
        task_id=task_id,
        provider_id="provider-a",
        model_id="model-a",
        base_head="a" * 40,
        source_result_ref="runs/source/result.json",
        result_destination_ref="runs/repair/result.json",
        review_findings=("P1: exact result digest did not match",),
    )


def materialization_request(**changes: object) -> RepairTaskMaterializationRequest:
    request = RepairTaskMaterializationRequest(
        repair_request=repair_request(),
        rejected_task_sha256=TASK_SHA,
        rejected_result_sha256=RESULT_SHA,
        review_reason_id="P1:DIGEST_MISMATCH",
        generation=1,
    )
    return replace(request, **changes)


def filesystem(root: Path, *, mutation_allowed: bool = True) -> NativeFileSystem:
    (root / "runs").mkdir(exist_ok=True)
    return NativeFileSystem(
        NativeExecutionScope(root=root, mutation_allowed=mutation_allowed)
    )


def test_materializes_exact_verified_task_packet(tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    request = materialization_request()

    packet = materialize_repair_task(request, filesystem=fs)

    written = tmp_path / packet.path
    expected = build_repair_task_markdown(request.repair_request).encode("utf-8")
    assert packet.path.startswith("runs/zra2-repair-")
    assert packet.path.endswith(".md")
    assert packet.task_contract_ref.startswith("zra2-repair-v1:")
    assert written.read_bytes() == expected
    assert packet.sha256 == hashlib.sha256(expected).hexdigest()


def test_same_identity_reuses_existing_exact_bytes_without_rewrite(tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    request = materialization_request()
    first = materialize_repair_task(request, filesystem=fs)
    target = tmp_path / first.path
    old_ns = 1_600_000_000_000_000_000
    os.utime(target, ns=(old_ns, old_ns))

    second = materialize_repair_task(request, filesystem=fs)

    assert second == first
    assert target.stat().st_mtime_ns == old_ns


def test_same_deterministic_path_with_different_bytes_is_collision(tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    request = materialization_request()
    packet = materialize_repair_task(request, filesystem=fs)
    (tmp_path / packet.path).write_text("tampered\n", encoding="utf-8")

    with pytest.raises(RepairTaskMaterializationError) as raised:
        materialize_repair_task(request, filesystem=fs)

    assert raised.value.code == "REPAIR_TASK_COLLISION"


@pytest.mark.parametrize("generation", [0, 2, -1, True, False, 1.0, "1"])
def test_only_integer_generation_one_is_valid(generation: object) -> None:
    with pytest.raises(RepairTaskMaterializationError) as raised:
        RepairTaskMaterializationRequest(
            repair_request=repair_request(),
            rejected_task_sha256=TASK_SHA,
            rejected_result_sha256=RESULT_SHA,
            review_reason_id="P1:DIGEST_MISMATCH",
            generation=generation,  # type: ignore[arg-type]
        )

    assert raised.value.code == "REPAIR_GENERATION_INVALID"


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("rejected_task_sha256", "bad", "REJECTED_TASK_SHA256_INVALID"),
        ("rejected_result_sha256", "g" * 64, "REJECTED_RESULT_SHA256_INVALID"),
    ],
)
def test_rejected_artifact_digests_are_exact_sha256(
    field: str, value: str, code: str
) -> None:
    kwargs = {
        "repair_request": repair_request(),
        "rejected_task_sha256": TASK_SHA,
        "rejected_result_sha256": RESULT_SHA,
        "review_reason_id": "P1:DIGEST_MISMATCH",
        "generation": 1,
    }
    kwargs[field] = value

    with pytest.raises(RepairTaskMaterializationError) as raised:
        RepairTaskMaterializationRequest(**kwargs)  # type: ignore[arg-type]

    assert raised.value.code == code


@pytest.mark.parametrize("reason", ["", "   ", "bad reason", "../escape", "x" * 129])
def test_review_reason_identity_is_bounded_token(reason: str) -> None:
    with pytest.raises(RepairTaskMaterializationError) as raised:
        RepairTaskMaterializationRequest(
            repair_request=repair_request(),
            rejected_task_sha256=TASK_SHA,
            rejected_result_sha256=RESULT_SHA,
            review_reason_id=reason,
            generation=1,
        )

    assert raised.value.code == "REVIEW_REASON_ID_INVALID"


@pytest.mark.parametrize(
    "change",
    [
        {"rejected_task_sha256": "3" * 64},
        {"rejected_result_sha256": "4" * 64},
        {"review_reason_id": "P1:OTHER_REASON"},
    ],
)
def test_exact_identity_changes_bind_to_distinct_packet(change: dict[str, object], tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    baseline = materialize_repair_task(materialization_request(), filesystem=fs)
    changed = materialize_repair_task(materialization_request(**change), filesystem=fs)

    assert changed.path != baseline.path
    assert changed.task_contract_ref != baseline.task_contract_ref


def test_unsafe_task_identifier_never_becomes_path_authority(tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    request = materialization_request(
        repair_request=repair_request(task_id="../../outside/repair")
    )

    packet = materialize_repair_task(request, filesystem=fs)

    assert packet.path.startswith("runs/zra2-repair-")
    assert ".." not in packet.path
    assert not (tmp_path.parent / "outside").exists()


def test_mutation_disabled_filesystem_fails_closed(tmp_path: Path) -> None:
    fs = filesystem(tmp_path, mutation_allowed=False)

    with pytest.raises(NativeExecutionError) as raised:
        materialize_repair_task(materialization_request(), filesystem=fs)

    assert raised.value.code == "MUTATION_FORBIDDEN"


def test_missing_fixed_parent_fails_closed_without_creating_directories(tmp_path: Path) -> None:
    fs = NativeFileSystem(
        NativeExecutionScope(root=tmp_path, mutation_allowed=True)
    )

    with pytest.raises(NativeExecutionError) as raised:
        materialize_repair_task(materialization_request(), filesystem=fs)

    assert raised.value.code == "PARENT_NOT_FOUND"
    assert not (tmp_path / "runs").exists()


class CorruptingVerificationFileSystem(NativeFileSystem):
    def read_text(self, relative_path, *, max_bytes=None):  # type: ignore[no-untyped-def]
        result = super().read_text(relative_path, max_bytes=max_bytes)
        return NativeReadResult(
            relative_path=result.relative_path,
            content=result.content + "corrupt",
            size_bytes=result.size_bytes + len("corrupt"),
            sha256=result.sha256,
        )


def test_post_write_reread_mismatch_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "runs").mkdir()
    fs = CorruptingVerificationFileSystem(
        NativeExecutionScope(root=tmp_path, mutation_allowed=True)
    )

    with pytest.raises(RepairTaskMaterializationError) as raised:
        materialize_repair_task(materialization_request(), filesystem=fs)

    assert raised.value.code == "REPAIR_TASK_VERIFY_FAILED"


def test_module_does_not_import_parallel_authority_surfaces() -> None:
    source = Path("src/a_conductor/zero_relay_repair_materializer.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)

    forbidden = (
        "a_conductor.graph",
        "a_conductor.review_mailbox_adapter",
        "a_conductor.worker_lease",
        "a_conductor.provider_",
        "a_conductor.memory",
    )
    assert all(
        not any(module == prefix or module.startswith(prefix) for prefix in forbidden)
        for module in imported
    )


class ConcurrentWriterFileSystem(NativeFileSystem):
    """Simulates another writer landing the exact bytes between our read-miss
    and our write: the precondition fires, the raced re-read must reuse."""

    def write_text(self, relative_path, content, *, expected_sha256=None):  # type: ignore[no-untyped-def]
        super().write_text(relative_path, content, expected_sha256=expected_sha256)
        raise NativeExecutionError("OVERWRITE_PRECONDITION_REQUIRED")


class VanishingWriterFileSystem(NativeFileSystem):
    """Precondition fires but the file is gone on re-read: fail closed."""

    def write_text(self, relative_path, content, *, expected_sha256=None):  # type: ignore[no-untyped-def]
        raise NativeExecutionError("OVERWRITE_PRECONDITION_REQUIRED")


def test_write_race_with_exact_concurrent_bytes_is_reused(tmp_path: Path) -> None:
    fs = ConcurrentWriterFileSystem(
        NativeExecutionScope(root=tmp_path, mutation_allowed=True)
    )
    (tmp_path / "runs").mkdir()

    packet = materialize_repair_task(materialization_request(), filesystem=fs)

    expected = build_repair_task_markdown(
        materialization_request().repair_request
    ).encode("utf-8")
    assert (tmp_path / packet.path).read_bytes() == expected
    assert packet.sha256 == hashlib.sha256(expected).hexdigest()


def test_write_race_with_vanished_file_fails_closed(tmp_path: Path) -> None:
    fs = VanishingWriterFileSystem(
        NativeExecutionScope(root=tmp_path, mutation_allowed=True)
    )
    (tmp_path / "runs").mkdir()

    with pytest.raises(RepairTaskMaterializationError) as raised:
        materialize_repair_task(materialization_request(), filesystem=fs)

    assert raised.value.code == "REPAIR_TASK_VERIFY_FAILED"


def test_uppercase_digests_normalize_to_the_same_identity(tmp_path: Path) -> None:
    fs = filesystem(tmp_path)
    lowercase = materialize_repair_task(materialization_request(), filesystem=fs)
    uppercase = materialize_repair_task(
        materialization_request(
            rejected_task_sha256=TASK_SHA.upper(),
            rejected_result_sha256=RESULT_SHA.upper(),
        ),
        filesystem=fs,
    )

    assert uppercase.path == lowercase.path
    assert uppercase.task_contract_ref == lowercase.task_contract_ref
    assert uppercase == lowercase
