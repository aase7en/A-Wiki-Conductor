"""WO-P1-246 — author-attempt provenance seam tests (RED contract §8).

Covers: the proof-carrying ``AuthorProvenanceBinding`` (no public
construction), the single classification factory (generation 0 only at this
base; repair family fails closed, never silently downgrading), the opaque
attempt-id mint, the exact-record ``ResultIdentity`` composition seam, and
the pure repair-identity derivation parity with ``materialize_repair_task``.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import replace
from pathlib import Path

import pytest

from a_conductor.agent_change_packets import AgentRepairRequest
from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.zero_relay_author_provenance import (
    AuthorProvenanceBinding,
    AuthorProvenanceError,
    bind_original_author_provenance,
    classify_author_provenance,
    compose_result_identity,
    derive_generation1_repair_binding,
    is_repair_family_contract_ref,
    mint_author_attempt_id,
)
from a_conductor.zero_relay_repair_materializer import (
    RepairTaskMaterializationRequest,
    derive_repair_task_identity,
    materialize_repair_task,
)


TASK_SHA = "1" * 64
RESULT_SHA = "2" * 64
ATTEMPT_RE = re.compile(r"^author-attempt-v1:[0-9a-f]{32}$")


def repair_request() -> AgentRepairRequest:
    return AgentRepairRequest(
        task_id="repair-001",
        provider_id="provider-a",
        model_id="model-a",
        base_head="a" * 40,
        source_result_ref="runs/source/result.json",
        result_destination_ref="runs/repair/result.json",
        review_findings=("P1: exact result digest did not match",),
    )


def materialization_request() -> RepairTaskMaterializationRequest:
    return RepairTaskMaterializationRequest(
        repair_request=repair_request(),
        rejected_task_sha256=TASK_SHA,
        rejected_result_sha256=RESULT_SHA,
        review_reason_id="P1:DIGEST_MISMATCH",
        generation=1,
    )


def make_record(
    execution_id: str = "exec-author-001",
    *,
    work_order_ref: str = "WO-P1-246-ZRA2-AUTHOR",
    result_ref: str = "runs/exec-author-001/result.json",
    fingerprint: str = "b" * 64,
    attempt: str | None = "author-attempt-v1:" + "a" * 32,
    generation: int | None = 0,
):
    return new_execution_record(
        execution_id=execution_id,
        job_id="job-001",
        work_order_ref=work_order_ref,
        project_id="project-1",
        worker_id="a-worker-01",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root=r"A:\GitHub\example",
        branch="main",
        head_before="h" * 40,
        operation_ref="zcode-task-v1:" + "c" * 64,
        command_fingerprint=fingerprint,
        command_summary="zcode author turn",
        runtime_profile_ref="zcode-runtime-v1:" + "d" * 64,
        run_dir_ref=f"runs/{execution_id}",
        stdout_ref=f"runs/{execution_id}/stdout.log",
        stderr_ref=f"runs/{execution_id}/stderr.log",
        result_ref=result_ref,
        report_ref=None,
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.SUCCEEDED,
        author_attempt_id=attempt,
        author_generation=generation,
    )


# ---------------- §3.6 binding: no public construction (test 33) -----------

def test_direct_binding_construction_raises_typed_error() -> None:
    with pytest.raises(AuthorProvenanceError) as raised:
        AuthorProvenanceBinding(
            author_generation=0,
            task_contract_ref="WO-P1-246-ZRA2-AUTHOR",
            task_packet_sha256=TASK_SHA,
        )
    assert raised.value.code == "AUTHOR_PROVENANCE_BINDING_CONSTRUCTION_FORBIDDEN"


def test_replace_cannot_forge_a_binding() -> None:
    binding = classify_author_provenance(
        task_contract_ref="WO-P1-246-ZRA2-AUTHOR",
        packet_sha256=TASK_SHA,
    )
    with pytest.raises(AuthorProvenanceError):
        replace(binding, author_generation=1)


def test_generation0_binding_carries_no_lineage() -> None:
    binding = classify_author_provenance(
        task_contract_ref="WO-P1-246-ZRA2-AUTHOR",
        packet_sha256=TASK_SHA,
    )
    assert binding.author_generation == 0
    assert binding.task_contract_ref == "WO-P1-246-ZRA2-AUTHOR"
    assert binding.task_packet_sha256 == TASK_SHA
    assert binding.rejected_execution_id is None
    assert binding.rejected_task_sha256 is None
    assert binding.rejected_result_sha256 is None
    assert binding.review_reason_id is None
    assert binding.repair_packet_sha256 is None


def test_factory_rejects_invalid_inputs() -> None:
    with pytest.raises(AuthorProvenanceError):
        classify_author_provenance(task_contract_ref=" ", packet_sha256=TASK_SHA)
    with pytest.raises(AuthorProvenanceError):
        classify_author_provenance(
            task_contract_ref="WO-X", packet_sha256="not-a-sha"
        )
    with pytest.raises(AuthorProvenanceError):
        bind_original_author_provenance(
            task_contract_ref="WO-X", task_packet_sha256=("a" * 64).upper()
        )


# ---------------- §3.3 classification: repair family fails closed ----------

def test_repair_family_detection_is_broad_prefix_based() -> None:
    assert is_repair_family_contract_ref("zra2-repair-v1:" + "e" * 64)
    assert is_repair_family_contract_ref("zra2-repair-v2:" + "e" * 64)
    assert is_repair_family_contract_ref("zra2-repair-bogus")
    assert not is_repair_family_contract_ref("WO-P1-246-ZRA2-AUTHOR")
    assert not is_repair_family_contract_ref("zra2-repai")  # not the family prefix


@pytest.mark.parametrize(
    "ref",
    [
        "zra2-repair-v1:" + "e" * 64,           # valid grammar: lineage missing
        "zra2-repair-v1:" + "E" * 64,           # uppercase digest
        "zra2-repair-v1:" + "e" * 63,           # short digest
        "zra2-repair-v2:" + "e" * 64,           # unsupported future version
        "zra2-repair-v1:",                       # empty digest
        "zra2-repair-",                          # bare family prefix
        "zra2-repair-v1:gggggggggggggggggggggggggggggggggggggggggggggggggggggggggggg",  # non-hex
    ],
)
def test_repair_family_never_classifies_as_generation0(ref: str) -> None:
    with pytest.raises(AuthorProvenanceError):
        classify_author_provenance(task_contract_ref=ref, packet_sha256=TASK_SHA)


def test_valid_v1_repair_grammar_fails_as_lineage_unavailable(ref: str | None = None) -> None:
    with pytest.raises(AuthorProvenanceError) as raised:
        classify_author_provenance(
            task_contract_ref="zra2-repair-v1:" + "e" * 64,
            packet_sha256=TASK_SHA,
        )
    assert raised.value.code == "REPAIR_LINEAGE_UNAVAILABLE"


@pytest.mark.parametrize(
    "ref",
    [
        "zra2-repair-v1:" + "E" * 64,
        "zra2-repair-v1:" + "e" * 63,
        "zra2-repair-v2:" + "e" * 64,
        "zra2-repair-v1:",
        "zra2-repair-",
        "zra2-repair-v1:not-hex-at-all",
    ],
)
def test_malformed_repair_family_fails_as_unsupported(ref: str) -> None:
    with pytest.raises(AuthorProvenanceError) as raised:
        classify_author_provenance(task_contract_ref=ref, packet_sha256=TASK_SHA)
    assert raised.value.code == "REPAIR_CONTRACT_UNSUPPORTED"


def test_generation1_reconstruction_home_is_blocked_at_this_base() -> None:
    with pytest.raises(AuthorProvenanceError) as raised:
        derive_generation1_repair_binding(
            rejected_execution_id="exec-rejected-001"
        )
    assert raised.value.code == "REPAIR_LINEAGE_UNAVAILABLE"


# ---------------- §3.2 mint -------------------------------------------------

def test_mint_format_is_opaque_uuid4_and_unique() -> None:
    first = mint_author_attempt_id()
    second = mint_author_attempt_id()
    assert ATTEMPT_RE.fullmatch(first)
    assert ATTEMPT_RE.fullmatch(second)
    assert first != second


# ---------------- §3.5 exact-record composition (tests 23-28) ---------------

def test_exact_proven_record_composes_all_seven_fields() -> None:
    record = make_record()
    identity = compose_result_identity(
        record=record,
        task_contract_ref=record.work_order_ref,
        task_sha256=TASK_SHA,
        result_ref=record.result_ref,
        result_sha256=RESULT_SHA,
    )
    assert identity.attempt_id == record.author_attempt_id
    assert identity.generation == 0
    assert identity.author_execution_id == record.execution_id
    assert identity.task_contract_ref == record.work_order_ref
    assert identity.task_sha256 == TASK_SHA
    assert identity.result_ref == record.result_ref
    assert identity.result_sha256 == RESULT_SHA


def test_unprovenanced_record_fails_author_provenance_unknown() -> None:
    record = make_record(attempt=None, generation=None)
    with pytest.raises(AuthorProvenanceError) as raised:
        compose_result_identity(
            record=record,
            task_contract_ref=record.work_order_ref,
            task_sha256=TASK_SHA,
            result_ref=record.result_ref,
            result_sha256=RESULT_SHA,
        )
    assert raised.value.code == "AUTHOR_PROVENANCE_UNKNOWN"


def test_task_contract_mismatch_fails_typed_identity_mismatch() -> None:
    record = make_record()
    with pytest.raises(AuthorProvenanceError) as raised:
        compose_result_identity(
            record=record,
            task_contract_ref="WO-SOMEONE-ELSE",
            task_sha256=TASK_SHA,
            result_ref=record.result_ref,
            result_sha256=RESULT_SHA,
        )
    assert raised.value.code == "AUTHOR_PROVENANCE_IDENTITY_MISMATCH"


def test_result_ref_mismatch_fails_typed_identity_mismatch() -> None:
    record = make_record()
    with pytest.raises(AuthorProvenanceError) as raised:
        compose_result_identity(
            record=record,
            task_contract_ref=record.work_order_ref,
            task_sha256=TASK_SHA,
            result_ref="runs/other/result.json",
            result_sha256=RESULT_SHA,
        )
    assert raised.value.code == "AUTHOR_PROVENANCE_IDENTITY_MISMATCH"


def test_same_fingerprint_records_cannot_cross_compose(tmp_path: Path) -> None:
    # pre-existing duplicate-fingerprint TOCTOU shape: two distinct records,
    # one fingerprint, distinct attempt ids (§5.3 non-mixing property)
    left = make_record(execution_id="exec-left", attempt="author-attempt-v1:" + "1" * 32)
    right = make_record(
        execution_id="exec-right",
        result_ref="runs/exec-right/result.json",
        attempt="author-attempt-v1:" + "2" * 32,
    )
    assert left.command_fingerprint == right.command_fingerprint
    assert left.author_attempt_id != right.author_attempt_id

    left_identity = compose_result_identity(
        record=left,
        task_contract_ref=left.work_order_ref,
        task_sha256=TASK_SHA,
        result_ref=left.result_ref,
        result_sha256=RESULT_SHA,
    )
    right_identity = compose_result_identity(
        record=right,
        task_contract_ref=right.work_order_ref,
        task_sha256=TASK_SHA,
        result_ref=right.result_ref,
        result_sha256=RESULT_SHA,
    )
    assert left_identity.author_execution_id != right_identity.author_execution_id
    assert left_identity.attempt_id != right_identity.attempt_id

    # no fingerprint lookup substitutes the other record's provenance/results
    with pytest.raises(AuthorProvenanceError) as raised:
        compose_result_identity(
            record=left,
            task_contract_ref=left.work_order_ref,
            task_sha256=TASK_SHA,
            result_ref=right.result_ref,  # foreign result artifact
            result_sha256=RESULT_SHA,
        )
    assert raised.value.code == "AUTHOR_PROVENANCE_IDENTITY_MISMATCH"


# ---------------- §8 test 31: pure derivation parity ------------------------

def test_pure_derivation_parities_materializer_with_zero_writes(tmp_path: Path) -> None:
    (tmp_path / "runs").mkdir()
    fs = NativeFileSystem(
        NativeExecutionScope(root=tmp_path, mutation_allowed=True)
    )
    request = materialization_request()

    before = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    identity = derive_repair_task_identity(request)
    after = sorted(str(p.relative_to(tmp_path)) for p in tmp_path.rglob("*"))
    assert before == after  # ZERO filesystem effects from the pure helper

    packet = materialize_repair_task(request, filesystem=fs)
    assert packet.path == identity.path
    assert packet.task_contract_ref == identity.task_contract_ref
    assert packet.sha256 == identity.content_sha256
    materialized_bytes = (tmp_path / packet.path).read_bytes()
    assert materialized_bytes == identity.content.encode("utf-8")
    assert hashlib.sha256(materialized_bytes).hexdigest() == identity.content_sha256


# ---------------- boundaries (tests 32/33 production-surface scan) ----------

def test_only_the_assembly_references_the_classification_factory() -> None:
    source_root = Path("src/a_conductor")
    offenders: list[str] = []
    for path in sorted(source_root.glob("*.py")):
        if path.name in ("zero_relay_author_provenance.py",
                         "zcode_production_assembly.py"):
            continue
        source = path.read_text(encoding="utf-8")
        if "classify_author_provenance" in source or "bind_original_author_provenance" in source:
            offenders.append(path.name)
    assert offenders == []


def test_review_and_closeout_modules_remain_consumers_only() -> None:
    for name in ("zero_relay.py", "goal_closeout.py",
                 "zero_relay_review_execution.py",
                 "zero_relay_review_verification.py",
                 "zero_relay_review_task.py",
                 "zero_relay_review_evidence.py"):
        path = Path("src/a_conductor") / name
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module != "a_conductor.zero_relay_author_provenance", name
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "a_conductor.zero_relay_author_provenance", name


def test_provenance_authority_never_uses_substitute_counters() -> None:
    """Test 30: retry/provider/CAS counters, timestamps, and review fields
    are not provenance authority anywhere in the seam."""
    source = Path("src/a_conductor/zero_relay_author_provenance.py").read_text(
        encoding="utf-8"
    )
    for banned in (
        "attempt_count",
        "configuration_generation",
        "created_at",
        "finished_at",
        "review_verdict",
        "review_findings",
    ):
        assert banned not in source, banned
