from __future__ import annotations

import json

import pytest

from a_conductor.dex_fake_substrate import (
    FakeSrmCollectionError,
    FakeSrmCollectionProducer,
)


def _producer() -> FakeSrmCollectionProducer:
    return FakeSrmCollectionProducer(
        execution_id="exec-001",
        attempt_id="attempt-001",
        binding_digest="d" * 64,
        claim_generation=1,
        authority_sha="a" * 40,
        execution_sha="b" * 40,
        host_id="host-01",
        boot_id="boot-01",
        pid=777,
        creation_id="created-777",
    )


def test_repeated_collect_is_byte_identical_and_immutable() -> None:
    producer = _producer()
    kwargs = dict(
        result_bytes=b"result",
        stdout_bytes=b"stdout",
        stderr_bytes=b"stderr",
        exit_code=0,
    )
    first = producer.collect(**kwargs)
    assert producer.collect(**kwargs) == first
    with pytest.raises(FakeSrmCollectionError, match="FAKE_COLLECTION_IMMUTABLE"):
        producer.collect(**{**kwargs, "exit_code": 1})


def test_fake_emits_substrate_facts_not_control_plane_decisions() -> None:
    raw = _producer().collect(
        result_bytes=b"result",
        stdout_bytes=b"",
        stderr_bytes=b"",
        exit_code=0,
    )
    payload = json.loads(raw)
    forbidden = {
        "accepted",
        "completed",
        "receipt",
        "retry_authorized",
        "task_status",
        "review",
    }
    assert forbidden.isdisjoint(payload)
    assert payload["schema"] == "dex.srm.collection.v1"
    assert payload["process"]["pid"] == 777


def test_fake_rejects_unbounded_artifact_input() -> None:
    producer = _producer()
    with pytest.raises(FakeSrmCollectionError, match="FAKE_COLLECTION_ARTIFACT_TOO_LARGE"):
        producer.collect(
            result_bytes=b"x" * (1024 * 1024 + 1),
            stdout_bytes=b"",
            stderr_bytes=b"",
            exit_code=0,
        )


@pytest.mark.parametrize("bad_id", ["exec\nsmuggled", "exec\x00smuggled"])
def test_fake_rejects_control_characters_in_identity(bad_id: str) -> None:
    with pytest.raises(ValueError, match="execution_id is invalid"):
        FakeSrmCollectionProducer(
            execution_id=bad_id,
            attempt_id="attempt-001",
            binding_digest="d" * 64,
            claim_generation=1,
            authority_sha="a" * 40,
            execution_sha="b" * 40,
            host_id="host-01",
            boot_id="boot-01",
            pid=777,
            creation_id="created-777",
        )
