"""WO-P1-216 / ZRA-2 Phase C0 — RED-first matrix for review-task provenance + route binding."""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from a_conductor.zero_relay import ResultIdentity
from a_conductor.zero_relay_review_task import (
    DirectReviewRoute,
    MaterializedReviewTask,
    ReviewTaskRefs,
    ZeroRelayReviewTaskError,
    bind_direct_review_route,
    canonical_review_bytes,
    deterministic_review_refs,
    materialize_review_task,
    render_review_task_markdown,
)
from test_parallel_ready_execution import _task

TASK_REF = "work-order:WO-P1-165"
TASK_SHA = "a" * 64
RESULT_REF = "results/zra2/attempt-1.json"
RESULT_SHA = "b" * 64
AUTHOR = "exec-author-1"
REVIEW_HEAD = "a" * 40


def _identity(**overrides) -> ResultIdentity:
    values = dict(
        task_contract_ref=TASK_REF,
        task_sha256=TASK_SHA,
        result_ref=RESULT_REF,
        result_sha256=RESULT_SHA,
        attempt_id="attempt-1",
        generation=0,
        author_execution_id=AUTHOR,
    )
    values.update(overrides)
    return ResultIdentity(**values)


# ---------- G1 deterministic identity ----------


def test_g1_exact_control_digest_is_stable_and_shaped() -> None:
    refs = deterministic_review_refs(_identity(), REVIEW_HEAD)
    assert refs.digest == hashlib.sha256(canonical_review_bytes(_identity(), REVIEW_HEAD)).hexdigest()
    assert len(refs.digest) == 64
    assert refs.contract_ref == f"zra2-review-v1:{refs.digest}"
    assert refs.task_path == f"runs/zra2-review-{refs.digest}.md"
    assert refs.result_ref == f"runs/zra2-review-result-{refs.digest}.json"


def test_g1_repeat_input_same_identity() -> None:
    assert canonical_review_bytes(_identity(), REVIEW_HEAD) == canonical_review_bytes(_identity(), REVIEW_HEAD)
    assert deterministic_review_refs(_identity(), REVIEW_HEAD) == deterministic_review_refs(_identity(), REVIEW_HEAD)


@pytest.mark.parametrize("field,value", [
    ("task_contract_ref", "work-order:OTHER"),
    ("task_sha256", "c" * 64),
    ("result_ref", "results/other.json"),
    ("result_sha256", "d" * 64),
    ("attempt_id", "attempt-2"),
    ("generation", 1),
    ("author_execution_id", "exec-author-2"),
])
def test_g1_each_field_changes_identity(field: str, value) -> None:
    assert deterministic_review_refs(_identity(**{field: value}), REVIEW_HEAD) != deterministic_review_refs(_identity(), REVIEW_HEAD)


def test_g1_canonical_bytes_use_fixed_keys_and_json_shape() -> None:
    doc = json.loads(canonical_review_bytes(_identity(), REVIEW_HEAD).decode("utf-8"))
    assert doc == {
        "schema": "zra2-review-v1",
        "task_contract_ref": TASK_REF,
        "task_sha256": TASK_SHA,
        "result_ref": RESULT_REF,
        "result_sha256": RESULT_SHA,
        "attempt_id": "attempt-1",
        "generation": 0,
        "author_execution_id": AUTHOR,
        "reviewed_head": REVIEW_HEAD,
    }


def test_g1_unicode_refs_hash_exact_utf8_bytes() -> None:
    identity = _identity(result_ref="results/ไทย-🚀.json")
    raw = canonical_review_bytes(identity, REVIEW_HEAD)
    assert "ไทย-🚀".encode("utf-8") in raw
    assert raw.decode("utf-8", errors="strict").encode("utf-8") == raw


def test_g1_raw_path_input_cannot_affect_deterministic_shape() -> None:
    refs = deterministic_review_refs(_identity(task_contract_ref="../evil/../wo"), REVIEW_HEAD)
    assert "/" not in refs.digest and ".." not in refs.task_path.replace("runs/zra2-review-", "").removesuffix(".md")
    assert refs.task_path.startswith("runs/zra2-review-") and refs.task_path.endswith(".md")


@pytest.mark.parametrize("bad", [None, "identity", 5])
def test_g1_non_result_identity_rejected(bad) -> None:
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        deterministic_review_refs(bad, REVIEW_HEAD)
    assert exc.value.code == "INPUT_INVALID"


# ---------- G2 deterministic rendering ----------


def test_g2_render_binds_every_identity_field_exactly_once() -> None:
    text = render_review_task_markdown(_identity(), REVIEW_HEAD)
    for value in (TASK_REF, TASK_SHA, RESULT_REF, RESULT_SHA, "attempt-1", AUTHOR, REVIEW_HEAD):
        assert value in text
    assert text.count(TASK_SHA) == 1 and text.count(RESULT_SHA) == 1


def test_g2_render_contains_fixed_protocol_requirements() -> None:
    text = render_review_task_markdown(_identity(), REVIEW_HEAD)
    lowered = text.casefold()
    for phrase in ("independent", "read-only", "verdict", "prose is evidence only", "gpt"):
        assert phrase in lowered


def test_g2_render_is_deterministic_no_env_or_time() -> None:
    one = render_review_task_markdown(_identity(), REVIEW_HEAD)
    two = render_review_task_markdown(_identity(), REVIEW_HEAD)
    assert one == two
    import os
    assert os.environ.get("COMPUTERNAME", "X") not in one
    assert "20" not in one.split("zra2-review-v1")[0]  # no year/timestamp preamble


# ---------- G3 no-clobber persistence ----------


class _FakeNative:
    """Minimal in-memory NativeFileSystem double honoring the real contract."""

    def __init__(self, *, mutation_allowed: bool = True, preexisting: str | None = None,
                 vanish_on_read: bool = False, parent_missing: bool = False,
                 target_is_dir: bool = False, root: str = "A:/wt/review"):
        from a_conductor.native_execution import NativeExecutionError
        self._err = NativeExecutionError
        self.root = Path(root)
        self.mutation_allowed = mutation_allowed
        self.store: dict[str, str] = {}
        if preexisting is not None:
            self.store["runs/pre"] = preexisting
        self.vanish_on_read = vanish_on_read
        self.parent_missing = parent_missing
        self.target_is_dir = target_is_dir

    def create_text_if_absent(self, relative_path, content):
        path = str(relative_path)
        if not self.mutation_allowed:
            raise self._err("MUTATION_FORBIDDEN")
        if self.parent_missing:
            raise self._err("PARENT_NOT_FOUND")
        if self.target_is_dir:
            raise self._err("FILE_TARGET_INVALID")
        if path in self.store:
            raise self._err("FILE_ALREADY_EXISTS")
        self.store[path] = content
        return type("R", (), {"relative_path": path, "size_bytes": len(content.encode()),
                              "sha256": hashlib.sha256(content.encode()).hexdigest(), "created": True})()

    def read_text(self, relative_path, *, max_bytes=None):
        path = str(relative_path)
        if self.vanish_on_read or path not in self.store:
            raise self._err("FILE_READ_FAILED")
        content = self.store[path]
        raw = content.encode()
        return type("R", (), {"relative_path": path, "content": content,
                              "size_bytes": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest()})()


def _materialized() -> MaterializedReviewTask:
    fs = _FakeNative()
    return materialize_review_task(fs, _identity(), REVIEW_HEAD), fs


def test_g3_create_persists_exact_bytes_and_sha() -> None:
    task, fs = _materialized()
    content = render_review_task_markdown(_identity(), REVIEW_HEAD)
    assert fs.store[task.refs.task_path] == content
    assert task.persisted_sha256 == hashlib.sha256(content.encode("utf-8")).hexdigest()
    assert task.created is True


def test_g3_same_bytes_second_call_reuses_packet() -> None:
    fs = _FakeNative()
    first = materialize_review_task(fs, _identity(), REVIEW_HEAD)
    second = materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert first.refs == second.refs
    assert first.persisted_sha256 == second.persisted_sha256
    assert second.created is False


def test_g3_divergent_bytes_at_same_path_is_typed_collision() -> None:
    fs = _FakeNative()
    refs = deterministic_review_refs(_identity(), REVIEW_HEAD)
    fs.store[refs.task_path] = "different-bytes"
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == "REVIEW_TASK_COLLISION"


def test_g3_vanished_after_collision_fails_closed() -> None:
    fs = _FakeNative()
    refs = deterministic_review_refs(_identity(), REVIEW_HEAD)
    fs.store[refs.task_path] = "x"
    fs.vanish_on_read = True
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == "REVIEW_TASK_STATE_UNVERIFIABLE"


@pytest.mark.parametrize("attr,code", [
    ("mutation_allowed", "MUTATION_FORBIDDEN"),
    ("parent_missing", "PARENT_NOT_FOUND"),
    ("target_is_dir", "FILE_TARGET_INVALID"),
])
def test_g3_native_failure_codes_pass_through_typed(attr: str, code: str) -> None:
    fs = _FakeNative(**{attr: True} if attr != "mutation_allowed" else {"mutation_allowed": False})
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == code


def test_g3_success_write_result_mismatch_fails_closed() -> None:
    class WrongResultNative(_FakeNative):
        def create_text_if_absent(self, relative_path, content):
            super().create_text_if_absent(relative_path, content)
            return type("R", (), {
                "relative_path": "runs/wrong.md",
                "size_bytes": 1,
                "sha256": "0" * 64,
                "created": True,
            })()

    fs = WrongResultNative()
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == "REVIEW_TASK_VERIFY_FAILED"


def test_g3_success_reread_missing_fails_closed() -> None:
    fs = _FakeNative(vanish_on_read=True)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == "REVIEW_TASK_STATE_UNVERIFIABLE"


def test_g3_changing_reviewed_head_changes_identity() -> None:
    other_head = "c" * 40
    assert deterministic_review_refs(_identity(), REVIEW_HEAD) != deterministic_review_refs(
        _identity(), other_head
    )
    assert canonical_review_bytes(_identity(), REVIEW_HEAD) != canonical_review_bytes(
        _identity(), other_head
    )


def test_g3_success_reread_divergent_bytes_fails_closed() -> None:
    class DivergentReadNative(_FakeNative):
        def read_text(self, relative_path, *, max_bytes=None):
            result = super().read_text(relative_path, max_bytes=max_bytes)
            raw = b"divergent-after-create"
            return type("R", (), {
                "relative_path": result.relative_path,
                "content": raw.decode("utf-8"),
                "size_bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })()

    fs = DivergentReadNative()
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(fs, _identity(), REVIEW_HEAD)
    assert exc.value.code == "REVIEW_TASK_VERIFY_FAILED"


def test_g3_reviewed_head_is_validated_and_case_normalized() -> None:
    upper = REVIEW_HEAD.upper()
    assert deterministic_review_refs(_identity(), upper) == deterministic_review_refs(
        _identity(), REVIEW_HEAD
    )
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        deterministic_review_refs(_identity(), "not-a-head")
    assert exc.value.code == "REVIEW_HEAD_INVALID"


def test_g3_module_does_not_reimplement_publication(tmp_path: Path) -> None:
    import a_conductor.zero_relay_review_task as module
    source = Path(module.__file__).read_text(encoding="utf-8")
    for banned in ("write_text(", "os.replace", "uuid.uuid4", "tempfile", "shutil"):
        assert banned not in source, banned


# ---------- G4 direct route binding via ParallelReadyTask ----------


def _route_task(materialized: MaterializedReviewTask, **dispatch_overrides):
    base = _task(node_id="review-node", worker_id="reviewer-1",
                 worktree="A:/wt/review", branch="feat/x", mutable_scope=("runs/**",))
    key = dataclasses.replace(base.dispatch_request.key, graph_run_id="review-run-1")
    request = dataclasses.replace(base.dispatch_request, key=key, work_order_ref=materialized.refs.contract_ref)
    defaults = dict(
        execution_id=key.job_id,
        task_contract_ref=materialized.refs.contract_ref,
        evidence_destination_ref=materialized.refs.result_ref,
    )
    dispatch = dataclasses.replace(
        base.harness_dispatch, **{**defaults, **dispatch_overrides}
    )
    packet = dataclasses.replace(
        base.task_packet,
        task_contract_ref=materialized.refs.contract_ref,
        path=f"A:/wt/review/{materialized.refs.task_path}",
        sha256=materialized.persisted_sha256,
    )
    return dataclasses.replace(base, dispatch_request=request, harness_dispatch=dispatch, task_packet=packet)


def test_g4_positive_read_only_route_binds_every_fact() -> None:
    task, fs = _materialized()
    route = bind_direct_review_route(
        _route_task(task), review=task, author=_identity(), filesystem=fs
    )
    assert isinstance(route, DirectReviewRoute)
    assert route.role == "independent-review"
    assert route.mutation_intent == "READ_ONLY"
    assert route.review_contract_ref == task.refs.contract_ref
    assert route.review_task_path.endswith(task.refs.task_path)
    assert route.review_task_sha256 == task.persisted_sha256
    assert route.review_result_ref == task.refs.result_ref
    assert route.author_execution_id == AUTHOR
    assert route.author_result_sha256 == RESULT_SHA
    assert route.reviewer_worker_id == "reviewer-1"
    assert route.dispatch_execution_id.startswith("graph-dispatch-")
    assert route.reviewed_head == base_head_of(_route_task(task))
    assert route.provider_id and route.model_id and route.project_id and route.worktree and route.branch


def base_head_of(route_task) -> str:
    return route_task.harness_dispatch.expected_head


def test_g4_packet_mismatch_rejected() -> None:
    task, fs = _materialized()
    wrong_packet_task = _route_task(task)
    wrong = dataclasses.replace(wrong_packet_task.task_packet, sha256="e" * 64)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            dataclasses.replace(wrong_packet_task, task_packet=wrong),
            review=task, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_PACKET_MISMATCH"


def test_g4_project_mutation_rejected() -> None:
    from a_conductor.claude_code_harness import MutationIntent
    task, fs = _materialized()
    mutated = _route_task(task, mutation_intent=MutationIntent.PROJECT_MUTATION)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            mutated, review=task, author=_identity(), filesystem=fs
        )
    assert exc.value.code == "REVIEW_ROUTE_NOT_READ_ONLY"


def test_g4_author_equals_reviewer_execution_rejected() -> None:
    from a_conductor.graph.dispatch import GraphDispatchKey
    derived = GraphDispatchKey("graph-aha6", "review-run-1", "review-node").job_id
    fs = _FakeNative()
    task = materialize_review_task(fs, _identity(author_execution_id=derived), REVIEW_HEAD)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            _route_task(task), review=task,
            author=_identity(author_execution_id=derived), filesystem=fs
        )
    assert exc.value.code == "AUTHOR_REVIEWER_NOT_DISTINCT"


def test_g4_foreign_author_cannot_bind_others_packet() -> None:
    task, fs = _materialized()
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            _route_task(task), review=task,
            author=_identity(result_sha256="f" * 64), filesystem=fs
        )
    assert exc.value.code == "AUTHOR_IDENTITY_MISMATCH"


def test_g4_result_destination_mismatch_rejected() -> None:
    task, fs = _materialized()
    wrong_dest = _route_task(task, evidence_destination_ref="runs/other.json")
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            wrong_dest, review=task, author=_identity(), filesystem=fs
        )
    assert exc.value.code == "REVIEW_DESTINATION_MISMATCH"


def test_g4_forged_materialized_sha_cannot_mint_route() -> None:
    task, fs = _materialized()
    forged = dataclasses.replace(task, persisted_sha256="0" * 64)
    route_task = _route_task(forged)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            route_task, review=forged, author=_identity(), filesystem=fs
        )
    assert exc.value.code == "REVIEW_TASK_VERIFY_FAILED"


def test_g4_foreign_worktree_packet_path_rejected() -> None:
    task, fs = _materialized()
    route_task = _route_task(task)
    foreign = dataclasses.replace(
        route_task.task_packet,
        path=f"A:/wt/OTHER/{task.refs.task_path}",
    )
    route_task = dataclasses.replace(route_task, task_packet=foreign)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            route_task, review=task, author=_identity(), filesystem=fs
        )
    assert exc.value.code == "REVIEW_PACKET_PATH_MISMATCH"


def test_g4_old_packet_cannot_bind_new_reviewed_head() -> None:
    task, fs = _materialized()
    route_task = _route_task(task)
    other_head = "c" * 40
    candidate = route_task.candidates[0]
    route_task = dataclasses.replace(
        route_task,
        lease_request=dataclasses.replace(route_task.lease_request, expected_head=other_head),
        candidates=(dataclasses.replace(candidate, head=other_head),),
        harness_dispatch=dataclasses.replace(
            route_task.harness_dispatch, expected_head=other_head
        ),
    )
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            route_task, review=task, author=_identity(), filesystem=fs
        )
    assert exc.value.code == "REVIEW_HEAD_MISMATCH"


def test_g4_materialized_object_without_persisted_bytes_rejected() -> None:
    task, _ = _materialized()
    empty_fs = _FakeNative()
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            _route_task(task), review=task, author=_identity(), filesystem=empty_fs
        )
    assert exc.value.code == "REVIEW_TASK_STATE_UNVERIFIABLE"


def test_g4_filesystem_root_must_match_selected_worktree() -> None:
    task, _ = _materialized()
    foreign_fs = _FakeNative(root="A:/wt/OTHER")
    foreign_fs.store[task.refs.task_path] = render_review_task_markdown(
        _identity(), REVIEW_HEAD
    )
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            _route_task(task), review=task, author=_identity(), filesystem=foreign_fs
        )
    assert exc.value.code == "REVIEW_FILESYSTEM_ROOT_MISMATCH"


def test_g4_route_is_immutable() -> None:
    task, fs = _materialized()
    route = bind_direct_review_route(
        _route_task(task), review=task, author=_identity(), filesystem=fs
    )
    with pytest.raises(Exception):
        route.role = "independent-review-x"


# ---------- G5 authority/import fence ----------


def test_g5_no_second_authority_imported_or_defined() -> None:
    import ast
    import a_conductor.zero_relay_review_task as module
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    banned_modules = {"subprocess", "socket", "http", "requests", "shutil", "tempfile",
                      "uuid", "os", "a_conductor.job_store", "a_conductor.review_mailbox_adapter",
                      "a_conductor.provider_config_store"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                assert root not in {m.split(".")[0] for m in banned_modules}, alias.name
                assert alias.name not in banned_modules, alias.name
        elif isinstance(node, ast.ImportFrom):
            assert node.module not in banned_modules, node.module
        elif isinstance(node, ast.ClassDef):
            assert node.name not in {"ReviewEvidence", "ReviewBus", "ReviewBridge",
                                     "Scheduler", "RetryEngine"}, node.name
