"""WO-P1-216 / ZRA-2 Phase C0 — RED-first matrix for review-task provenance + route binding."""
from __future__ import annotations

import dataclasses
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path

import pytest
import jsonschema

from a_conductor.claude_code_harness import MutationIntent, TaskPacketFile
from a_conductor.native_execution import NativeExecutionError, NativeExecutionScope, NativeFileSystem
from a_conductor.provider_execution_authority import ProviderExecutionRequirement
from a_conductor.provider_configuration import ProviderEndpointConfig
from a_conductor.provider_policy import (
    ProviderPolicyTaskSecurity, TaskNetworkPolicy, TaskPrivacyClass, evaluate_provider_policy,
)
from a_conductor.zcode_runner import ZCodeTaskPacketIdentity
from a_conductor.worker_lease import LeaseMutationIntent
from a_conductor.zero_relay import ResultIdentity
from a_conductor.zero_relay_review_task import (
    DirectReviewRoute,
    MaterializedReviewTask,
    MaterializedReviewV2Task,
    ReviewTaskRefs,
    ZeroRelayReviewTaskError,
    bind_direct_review_route,
    bind_direct_review_v2_route,
    canonical_review_bytes,
    canonical_review_v2_authority_bytes,
    canonical_review_v2_bytes,
    deterministic_review_refs,
    deterministic_review_v2_refs,
    materialize_review_task,
    materialize_review_v2_task,
    render_review_task_markdown,
    render_review_v2_task_markdown,
)
from test_parallel_ready_execution import _profile, _task

TASK_REF = "work-order:WO-P1-165"
TASK_SHA = "a" * 64
RESULT_REF = "results/zra2/attempt-1.json"
RESULT_SHA = "b" * 64
AUTHOR = "exec-author-1"
REVIEW_HEAD = "a" * 40


def _v2_security(*, host: str = "provider.example") -> ProviderPolicyTaskSecurity:
    return ProviderPolicyTaskSecurity(
        privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.ALLOWLISTED,
        network_allowlist=(host,),
        secret_access=False,
    )


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


class _FakeNative(NativeFileSystem):
    """Minimal in-memory NativeFileSystem double honoring the real contract."""

    def __init__(self, *, mutation_allowed: bool = True, preexisting: str | None = None,
                 vanish_on_read: bool = False, parent_missing: bool = False,
                 target_is_dir: bool = False, root: str = "A:/wt/review"):
        from a_conductor.native_execution import NativeExecutionError
        self._err = NativeExecutionError
        self._fake_root = Path(root)
        self.mutation_allowed = mutation_allowed
        self.store: dict[str, str] = {}
        if preexisting is not None:
            self.store["runs/pre"] = preexisting
        self.vanish_on_read = vanish_on_read
        self.parent_missing = parent_missing
        self.target_is_dir = target_is_dir

    @property
    def root(self) -> Path:
        return self._fake_root

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
        if self.vanish_on_read:
            raise self._err("FILE_READ_FAILED")
        if path not in self.store:
            raise self._err("FILE_NOT_FOUND")
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
        mutation_intent=MutationIntent.READ_ONLY,
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
    # WO225: the direct-review route carries a REAL READ_ONLY lease with the
    # exact review contract as its task id (empty mutable scope by invariant).
    lease = dataclasses.replace(
        base.lease_request,
        task_id=materialized.refs.contract_ref,
    )
    if dispatch.mutation_intent is MutationIntent.READ_ONLY:
        lease = dataclasses.replace(
            lease,
            mutation_intent=LeaseMutationIntent.READ_ONLY,
            allowed_scope=(),
            mutable_scope=(),
        )
    return dataclasses.replace(
        base, dispatch_request=request, harness_dispatch=dispatch,
        task_packet=packet, lease_request=lease,
    )


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


def test_g4_duck_typed_filesystem_cannot_mint_route_authority() -> None:
    task, fs = _materialized()

    class DuckFilesystem:
        root = fs.root

        def read_text(self, relative_path):
            return fs.read_text(relative_path)

    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_route(
            _route_task(task),
            review=task,
            author=_identity(),
            filesystem=DuckFilesystem(),
        )
    assert exc.value.code == "FILESYSTEM_INVALID"


def test_g3_duck_typed_filesystem_cannot_materialize_authority() -> None:
    class DuckFilesystem:
        def create_text_if_absent(self, relative_path, content):
            raise AssertionError("must reject before use")

    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_task(DuckFilesystem(), _identity(), REVIEW_HEAD)
    assert exc.value.code == "FILESYSTEM_INVALID"


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


# ══════════ WO225: READ_ONLY lease/task binding at the C0 binder ══════════
from a_conductor.worker_lease import LeaseMutationIntent  # noqa: E402


def _review_lease(task):  # build a proper READ_ONLY review lease from the route
    return dataclasses.replace(
        task.lease_request,
        mutation_intent=LeaseMutationIntent.READ_ONLY,
        allowed_scope=(),
        mutable_scope=(),
        task_id=task.task_packet.task_contract_ref,
    )
def _mutation_lease(task, *, task_id=None):
    """Forge the §1 defect shape: same route, MUTATION lease with runs/**."""
    return dataclasses.replace(
        task.lease_request,
        mutation_intent=LeaseMutationIntent.MUTATION,
        allowed_scope=("runs/**",),
        mutable_scope=("runs/**",),
        task_id=task_id if task_id is not None else task.lease_request.task_id,
    )
def test_wo225_red1_mutation_lease_with_readonly_harness_rejected():
    """The mutation-lease/read-only-harness mismatch fails at task creation."""
    real, fs = _materialized()
    task = _route_task(real)
    with pytest.raises(ValueError, match="lease and harness mutation intent mismatch"):
        dataclasses.replace(task, lease_request=_mutation_lease(task))
def test_wo225_red2_mutation_scope_cannot_mint_readonly_route():
    real, fs = _materialized()
    from a_conductor.claude_code_harness import MutationIntent
    task = _route_task(real, mutation_intent=MutationIntent.PROJECT_MUTATION)
    route = None
    with pytest.raises(ZeroRelayReviewTaskError):
        route = bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert route is None
def test_wo225_green3_readonly_lease_empty_scope_exact_task_binds():
    real, fs = _materialized()
    task = _route_task(real)
    task = dataclasses.replace(task, lease_request=_review_lease(task))
    route = bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert route.mutation_intent == "READ_ONLY"
    assert route.review_contract_ref == real.refs.contract_ref
def test_wo225_red4_readonly_lease_foreign_task_rejected():
    real, fs = _materialized()
    task = _route_task(real)
    lease = dataclasses.replace(_review_lease(task), task_id="task-something-else")
    task = dataclasses.replace(task, lease_request=lease)
    with pytest.raises(ZeroRelayReviewTaskError) as raised:
        bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert raised.value.code == "REVIEW_LEASE_TASK_MISMATCH"
def test_wo225_red5_same_everything_wrong_lease_task_rejected():
    """Same worker/provider/model/project/worktree/branch/head, only the lease
    task id differs -> still rejected."""
    real, fs = _materialized()
    task = _route_task(real)
    lease = dataclasses.replace(_review_lease(task), task_id=f"task-{real.refs.digest[:8]}")
    task = dataclasses.replace(task, lease_request=lease)
    with pytest.raises(ZeroRelayReviewTaskError) as raised:
        bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert raised.value.code == "REVIEW_LEASE_TASK_MISMATCH"
def test_wo225_red6_mutation_lease_with_review_contract_task_still_rejected():
    """The binder still checks lease intent if state drifts after construction."""
    real, fs = _materialized()
    task = _route_task(real)
    object.__setattr__(task, "lease_request", _mutation_lease(
        task, task_id=real.refs.contract_ref))
    assert task.lease_request.mutation_intent is LeaseMutationIntent.MUTATION
    assert task.lease_request.task_id == real.refs.contract_ref
    with pytest.raises(ZeroRelayReviewTaskError) as raised:
        bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert raised.value.code == "REVIEW_LEASE_NOT_READ_ONLY"
def test_wo225_regression_harness_project_mutation_still_rejected():
    from a_conductor.claude_code_harness import MutationIntent
    real, fs = _materialized()
    task = _route_task(real, mutation_intent=MutationIntent.PROJECT_MUTATION)
    with pytest.raises(ZeroRelayReviewTaskError) as raised:
        bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert raised.value.code == "REVIEW_ROUTE_NOT_READ_ONLY"


def test_wo225_regression_author_alias_still_rejected():
    real, fs = _materialized()
    task = _route_task(real)
    task = dataclasses.replace(task, lease_request=_review_lease(task))
    aliased = dataclasses.replace(task.harness_dispatch,
                                  execution_id=_identity().author_execution_id)
    object.__setattr__(task, "harness_dispatch", aliased)  # post-validation forge
    with pytest.raises(ZeroRelayReviewTaskError) as raised:
        bind_direct_review_route(task, real, author=_identity(), filesystem=fs)
    assert raised.value.code == "AUTHOR_REVIEWER_NOT_DISTINCT"


# ---------- WO223 G2/G3 protocol-v2 RED ----------


def test_wo223_v2_identity_is_distinct_deterministic_and_project_bound() -> None:
    v1 = deterministic_review_refs(_identity(), REVIEW_HEAD)
    v2a = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    v2b = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    other = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="other-project", security=_v2_security())
    assert v2a == v2b
    assert v2a != v1
    assert v2a != other
    assert v2a.contract_ref == f"runs/zra2-review-v2-{v2a.digest}.task.json"
    assert v2a.task_path == f"runs/zra2-review-v2-{v2a.digest}.md"
    assert v2a.result_ref == f"runs/zra2-review-result-v2-{v2a.digest}.json"


def test_wo223_v2_identity_bytes_change_on_protocol_and_keep_v1_bytes_stable() -> None:
    v1_before = canonical_review_bytes(_identity(), REVIEW_HEAD)
    v2 = canonical_review_v2_bytes(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    assert json.loads(v2.decode("utf-8"))["schema"] == "zra2-review-v2"
    assert v2 != v1_before
    assert canonical_review_bytes(_identity(), REVIEW_HEAD) == v1_before



def test_wo223_v2_security_policy_is_identity_bearing() -> None:
    base = deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
    )
    other = deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security(host="other.example")
    )
    assert base != other
    doc = json.loads(
        canonical_review_v2_bytes(
            _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
        ).decode("utf-8")
    )
    assert doc["security"]["network_policy"] == "ALLOWLISTED"
    assert doc["security"]["network_allowlist"] == ["provider.example"]



def test_wo223_v2_semantic_response_contract_is_identity_bearing(monkeypatch) -> None:
    import a_conductor.zero_relay_review_task as module

    base = deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
    )
    doc = json.loads(
        canonical_review_v2_bytes(
            _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
        ).decode("utf-8")
    )
    assert doc["response_contract"] == {
        "schema": "zra2-review-result-v2",
        "verdicts": ["ACCEPTED", "REJECTED"],
        "max_response_bytes": 32768,
        "max_findings": 64,
        "max_finding_chars": 2048,
    }
    monkeypatch.setattr(module, "_V2_RESULT_SCHEMA", "zra2-review-result-v3")
    changed = module.deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
    )
    assert changed != base

def test_wo223_v2_prompt_requires_exact_json_only_semantics() -> None:
    text = render_review_v2_task_markdown(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    assert "zra2-review-result-v2" in text
    assert "JSON only" in text
    assert "ACCEPTED" in text and "REJECTED" in text
    assert "Markdown" in text
    refs = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    assert refs.contract_ref in text
    assert refs.result_ref in text


def test_wo223_v2_authority_is_task_contract_v1_and_binds_prompt() -> None:
    refs = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    prompt = render_review_v2_task_markdown(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    raw = canonical_review_v2_authority_bytes(
        _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security(),
        prompt_path=refs.task_path, prompt_sha256=prompt_sha,
        result_ref=refs.result_ref,
    )
    doc = json.loads(raw.decode("utf-8"))
    assert doc["schema_version"] == "1.0.0"
    assert doc["authority"]["mutation_allowed"] is False
    assert doc["target"]["project_id"] == "a-conductor"
    assert doc["target"]["expected_head"] == REVIEW_HEAD
    assert doc["target"]["identity_policy"] == "EXACT"
    assert doc["security"] == {
        "privacy_class": "INTERNAL", "network_policy": "ALLOWLISTED",
        "network_allowlist": ["provider.example"], "secret_access": False,
    }
    metadata = doc["metadata"]
    assert metadata["review_protocol"] == "zra2-review-v2"
    assert metadata["review_prompt_path"] == refs.task_path
    assert metadata["review_prompt_sha256"] == prompt_sha
    assert metadata["semantic_result_ref"] == refs.result_ref
    assert metadata["author_result_sha256"] == RESULT_SHA


def test_wo223_v2_materialization_publishes_prompt_then_authority_and_replays() -> None:
    fs = _FakeNative()
    first = materialize_review_v2_task(
        fs, _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
    )
    second = materialize_review_v2_task(
        fs, _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security()
    )
    assert first.refs == second.refs
    assert first.prompt_sha256 == second.prompt_sha256
    assert first.authority_sha256 == second.authority_sha256
    assert first.created_prompt is True and first.created_authority is True
    assert second.created_prompt is False and second.created_authority is False
    assert first.refs.task_path in fs.store
    assert first.refs.contract_ref in fs.store




def test_wo223_v2_prompt_only_partial_state_recovers_authority(tmp_path: Path) -> None:
    root = tmp_path / "review-root"
    (root / "runs").mkdir(parents=True)
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    security = _v2_security()
    refs = deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
    )
    prompt = render_review_v2_task_markdown(
        _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
    )
    (root / refs.task_path).write_bytes(prompt.encode("utf-8"))
    result = materialize_review_v2_task(
        fs, _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
    )
    assert result.created_prompt is False
    assert result.created_authority is True
    assert (root / refs.contract_ref).is_file()


def test_wo223_v2_authority_without_prompt_fails_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "review-root"
    (root / "runs").mkdir(parents=True)
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    security = _v2_security()
    refs = deterministic_review_v2_refs(
        _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
    )
    prompt = render_review_v2_task_markdown(
        _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
    )
    prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    authority = canonical_review_v2_authority_bytes(
        _identity(), REVIEW_HEAD,
        project_id="a-sunday-conductor", security=security,
        prompt_path=refs.task_path, prompt_sha256=prompt_sha, result_ref=refs.result_ref,
    )
    (root / refs.contract_ref).write_bytes(authority)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_v2_task(
            fs, _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=security
        )
    assert exc.value.code == "REVIEW_V2_AUTHORITY_WITHOUT_PROMPT"
    assert not (root / refs.task_path).exists()



def test_wo223_v2_concurrent_exact_publication_converges(tmp_path: Path) -> None:
    root = tmp_path / "review-root"
    (root / "runs").mkdir(parents=True)
    security = _v2_security()

    def publish():
        fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
        return materialize_review_v2_task(
            fs, _identity(), REVIEW_HEAD,
            project_id="a-sunday-conductor", security=security,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: publish(), range(4)))
    assert len({result.refs for result in results}) == 1
    assert len({result.prompt_sha256 for result in results}) == 1
    assert len({result.authority_sha256 for result in results}) == 1
    assert sum(result.created_prompt for result in results) == 1
    assert sum(result.created_authority for result in results) == 1

def test_wo223_v2_prompt_collision_fails_closed() -> None:
    fs = _FakeNative()
    refs = deterministic_review_v2_refs(_identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    fs.store[refs.task_path] = "foreign prompt"
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_v2_task(fs, _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    assert exc.value.code == "REVIEW_V2_PROMPT_COLLISION"


def test_wo223_v2_authority_collision_fails_closed() -> None:
    fs = _FakeNative()
    first = materialize_review_v2_task(fs, _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    fs.store[first.refs.contract_ref] = "{}"
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        materialize_review_v2_task(fs, _identity(), REVIEW_HEAD, project_id="a-conductor", security=_v2_security())
    assert exc.value.code == "REVIEW_V2_AUTHORITY_COLLISION"



def _materialized_v2_real(tmp_path: Path):
    root = tmp_path / "review-root"
    (root / "runs").mkdir(parents=True)
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    task = materialize_review_v2_task(
        fs, _identity(), REVIEW_HEAD, project_id="a-sunday-conductor", security=_v2_security()
    )
    return root, task, fs


def test_wo223_v2_authority_validates_existing_task_contract_schema(tmp_path: Path) -> None:
    root, task, fs = _materialized_v2_real(tmp_path)
    authority = json.loads(fs.read_text(task.refs.contract_ref).content)
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "task-contract.schema.json")
        .read_text(encoding="utf-8")
    )
    jsonschema.Draft202012Validator(schema).validate(authority)
    assert authority["work_order_ref"] == task.refs.contract_ref


def test_wo223_v2_authority_derives_existing_provider_requirement(tmp_path: Path) -> None:
    root, task, _fs = _materialized_v2_real(tmp_path)
    packet = TaskPacketFile(
        task_contract_ref=task.refs.contract_ref,
        path=str(root / task.refs.task_path),
        sha256=task.prompt_sha256,
    )
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
        packet, trusted_root=str(root)
    )
    requirement = ProviderExecutionRequirement.from_task_contract_file(
        project_root=root,
        provider_id="cointh-glm",
        provider_authority_path=root / "provider.sqlite",
        expected_configuration_generation=7,
        task_contract_ref=task.refs.contract_ref,
        base_operation_ref=packet_identity.canonical_operation_ref(),
        expected_authority_sha256=task.authority_sha256,
    )
    assert requirement.task_contract_ref == task.refs.contract_ref
    assert requirement.base_operation_ref == packet_identity.canonical_operation_ref()
    assert requirement.expected_configuration_generation == 7
    assert requirement.provider_security.secret_access is False
    assert requirement.provider_security.network_policy.value == "ALLOWLISTED"
    assert requirement.provider_security.network_allowlist == ("provider.example",)
    assert requirement.provider_security.privacy_class.value == "INTERNAL"
    profile = _profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example/v1")
    assert evaluate_provider_policy(profile, endpoint, requirement.provider_security).allowed is True


# ---------- WO223 G4 protocol-v2 route/provider-authority binding ----------


def _v2_route_task(root: Path, review: MaterializedReviewV2Task):
    profile = _profile()
    packet = TaskPacketFile(
        task_contract_ref=review.refs.contract_ref,
        path=str(root / review.refs.task_path),
        sha256=review.prompt_sha256,
    )
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
        packet, trusted_root=str(root)
    )
    requirement = ProviderExecutionRequirement.from_task_contract_file(
        project_root=root,
        provider_id=profile.provider_id,
        provider_authority_path=root / "provider.sqlite",
        expected_configuration_generation=7,
        task_contract_ref=review.refs.contract_ref,
        base_operation_ref=packet_identity.canonical_operation_ref(),
        expected_authority_sha256=review.authority_sha256,
    )
    base = _task(
        node_id="review-v2-node", worker_id="reviewer-v2",
        worktree=str(root), branch="feat/review-v2", mutable_scope=("runs/**",),
        profile=profile, require_quota=False,
    )
    key = dataclasses.replace(base.dispatch_request.key, graph_run_id="review-v2-run")
    request = dataclasses.replace(
        base.dispatch_request,
        key=key,
        work_order_ref=review.refs.contract_ref,
        operation_ref=requirement.operation_ref,
    )
    dispatch = dataclasses.replace(
        base.harness_dispatch,
        execution_id=key.job_id,
        task_contract_ref=review.refs.contract_ref,
        project_id=review.project_id,
        worktree_path=str(root),
        expected_branch="feat/review-v2",
        expected_head=REVIEW_HEAD,
        evidence_destination_ref=review.refs.result_ref,
        mutation_intent=MutationIntent.READ_ONLY,
    )
    lease = dataclasses.replace(
        base.lease_request,
        task_id=review.refs.contract_ref,
        project_id=review.project_id,
        worktree=str(root),
        branch="feat/review-v2",
        expected_head=REVIEW_HEAD,
        mutation_intent=LeaseMutationIntent.READ_ONLY,
        allowed_scope=(),
        mutable_scope=(),
    )
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://provider.example/v1")
    return dataclasses.replace(
        base,
        dispatch_request=request,
        lease_request=lease,
        provider_profile=profile,
        provider_endpoint=endpoint,
        provider_security=requirement.provider_security,
        expected_configuration_generation=requirement.expected_configuration_generation,
        provider_requirement=requirement,
        harness_dispatch=dispatch,
        task_packet=packet,
        require_quota=False,
    )


def test_wo223_v2_route_binds_task_provider_and_dispatch_authority(tmp_path: Path) -> None:
    root, review, fs = _materialized_v2_real(tmp_path)
    task = _v2_route_task(root, review)
    route = bind_direct_review_v2_route(
        task, review=review, author=_identity(), filesystem=fs
    )
    assert route.review_contract_ref == review.refs.contract_ref
    assert route.review_task_sha256 == review.prompt_sha256
    assert route.review_result_ref == review.refs.result_ref
    assert route.project_id == review.project_id
    assert route.reviewer_worker_id == "reviewer-v2"
    assert task.provider_requirement is not None
    assert task.provider_requirement.authority_sha256 == review.authority_sha256
    assert task.provider_requirement.provider_security == review.security
    assert task.dispatch_request.work_order_ref == review.refs.contract_ref
    assert task.lease_request.task_id == review.refs.contract_ref


def test_wo223_v2_route_rejects_authority_sidecar_drift(tmp_path: Path) -> None:
    root, review, fs = _materialized_v2_real(tmp_path)
    task = _v2_route_task(root, review)
    (root / review.refs.contract_ref).write_text("{}", encoding="utf-8")
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_v2_route(task, review=review, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_V2_AUTHORITY_COLLISION"


def test_wo223_v2_route_rejects_security_rebound(tmp_path: Path) -> None:
    root, review, fs = _materialized_v2_real(tmp_path)
    task = _v2_route_task(root, review)
    object.__setattr__(task, "provider_security", _v2_security(host="other.example"))
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_v2_route(task, review=review, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_V2_PROVIDER_SECURITY_MISMATCH"


def test_wo223_v2_route_rejects_requirement_authority_or_packet_operation_rebound(tmp_path: Path) -> None:
    root, review, fs = _materialized_v2_real(tmp_path)
    task = _v2_route_task(root, review)
    requirement = task.provider_requirement
    assert requirement is not None
    object.__setattr__(requirement, "authority_sha256", "f" * 64)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_v2_route(task, review=review, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_V2_PROVIDER_AUTHORITY_MISMATCH"

    task = _v2_route_task(root, review)
    requirement = task.provider_requirement
    assert requirement is not None
    object.__setattr__(requirement, "base_operation_ref", "zcode-task-v1:" + "e" * 64)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_v2_route(task, review=review, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_V2_PROVIDER_OPERATION_MISMATCH"



def test_wo223_v2_route_requires_complete_provider_authority(tmp_path: Path) -> None:
    root, review, fs = _materialized_v2_real(tmp_path)
    task = _v2_route_task(root, review)
    object.__setattr__(task, "provider_requirement", None)
    with pytest.raises(ZeroRelayReviewTaskError) as exc:
        bind_direct_review_v2_route(task, review=review, author=_identity(), filesystem=fs)
    assert exc.value.code == "REVIEW_V2_PROVIDER_AUTHORITY_MISSING"


# ---------- WO223 R3 repair RED: Astra F3 ----------

def test_r3_exact_concurrent_publication_forced_interleaving_converges(tmp_path: Path) -> None:
    root = tmp_path / "review-root"
    (root / "runs").mkdir(parents=True)
    security = _v2_security()

    class PausedReader(NativeFileSystem):
        triggered = False

        def read_text(self, relative_path):
            try:
                return super().read_text(relative_path)
            except NativeExecutionError:
                if str(relative_path).endswith(".md") and not self.triggered:
                    self.triggered = True
                    materialize_review_v2_task(
                        NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True)),
                        _identity(), REVIEW_HEAD,
                        project_id="a-sunday-conductor", security=security,
                    )
                raise

    result = materialize_review_v2_task(
        PausedReader(NativeExecutionScope(root=root, mutation_allowed=True)),
        _identity(), REVIEW_HEAD,
        project_id="a-sunday-conductor", security=security,
    )
    assert result.created_prompt is False
    assert result.created_authority is False
