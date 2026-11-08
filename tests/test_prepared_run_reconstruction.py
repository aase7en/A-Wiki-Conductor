"""WO-P1-736 — read-only prepared-run reconstruction seam (offline deterministic).

Fixture-owned store/digest/project ports only. No network, no live runtime,
no durable writes. Every blocker case asserts the exact typed reason code.

Repair round 1 (WO-P1-736 review findings):
- F1: contract/packet digest lookups must be bound to the resolved durable
  project root; wrong-project evidence with identical refs must not validate.
- F2: every port/boundary failure (unexpected store exceptions, malformed
  binding iterables, project/digest port exceptions) maps to a typed blocker.
- F3: all prepared identity markers are validated against store text and
  SHA-256 rules, not merely non-None checks.
- F4: fixtures own their project roots via tmp_path and expected resolved
  paths are computed independently of the production resolver.

Repair round 2 (focused re-review findings):
- R2-F1: a relative root returned by the project authority must yield the
  typed PREPARED_RUN_PROJECT_UNAVAILABLE blocker BEFORE any resolution use,
  and the digest port must observe zero invocations.
- R2-F2: a packet-path resolution failure after both digest ports succeed
  (e.g. a self-referential symlink loop) must map to the typed
  PREPARED_RUN_PACKET_UNAVAILABLE blocker, never escape raw.
- R2-F3: the cross-project mismatch test is rebuilt end-to-end over two
  REAL tmp trees with the same relative refs but different file bytes,
  a real sha256-over-file-bytes digest port, and recorded invocations
  proving every digest query received the ABSOLUTE resolved durable root.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from a_conductor.graph.store import (
    GraphRunBindingRecord,
    GraphRunRecord,
    GraphStoreError,
)
from a_conductor.prepared_run_reconstruction import (
    PreparedRunReconstructionError,
    reconstruct_prepared_activation_request,
)

GRAPH_ID = "graph-demo"
PROJECT_ID = "project-demo"
RUN_ID = "graph-run-v1:" + ("a" * 32)
NODE_A = "node-a"
NODE_B = "node-b"
CONTRACT_REF = "contracts/node-a.contract.md"
PACKET_REF = "packets/node-a.packet.json"


def _sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


CONTRACT_SHA = _sha("contract-v1")
PACKET_SHA = _sha("packet-v1")


def make_run(**overrides: object) -> GraphRunRecord:
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "graph_id": GRAPH_ID,
        "status": "pending",
        "created_at": "2026-11-08T00:00:00.000Z",
        "completed_at": None,
        "project_id": PROJECT_ID,
        "graph_definition_sha256": _sha("graph-def-v1"),
        "preparation_ref": "graph-run-preparation-v1:" + ("b" * 32),
        "preparation_sha256": _sha("preparation-v1"),
    }
    values.update(overrides)
    return GraphRunRecord(**values)  # type: ignore[arg-type]


def make_binding(
    node_id: str = NODE_A,
    *,
    contract_sha: str = CONTRACT_SHA,
    packet_sha: str = PACKET_SHA,
    **overrides: object,
) -> GraphRunBindingRecord:
    values: dict[str, object] = {
        "run_id": RUN_ID,
        "node_id": node_id,
        "runtime_kind": "serena",
        "task_contract_ref": CONTRACT_REF,
        "task_contract_sha256": contract_sha,
        "task_packet_ref": PACKET_REF,
        "task_packet_sha256": packet_sha,
        "provider_id": "provider-x",
        "model_id": "model-x",
        "effort_level": "MAX",
        "bound_at": "2026-11-08T00:00:00.000Z",
    }
    values.update(overrides)
    return GraphRunBindingRecord(**values)  # type: ignore[arg-type]


class FakeRunStore:
    """Fixture-owned stand-in for the GraphStore read seam (store.py:1061/:1084)."""

    def __init__(self) -> None:
        self.runs: dict[str, GraphRunRecord] = {}
        self.bindings: dict[str, object] = {}
        self.run_reads = 0
        self.binding_reads = 0
        self.writes = 0
        self.run_error: Exception | None = None
        self.binding_error: Exception | None = None
        self.run_override: object = None

    def load_graph_run(self, run_id: str) -> GraphRunRecord:
        self.run_reads += 1
        if self.run_error is not None:
            raise self.run_error
        if self.run_override is not None:
            return self.run_override  # type: ignore[return-value]
        record = self.runs.get(run_id)
        if record is None:
            raise GraphStoreError("GRAPH_RUN_NOT_FOUND")
        return record

    def load_graph_run_bindings(self, run_id: str) -> tuple[GraphRunBindingRecord, ...]:
        self.binding_reads += 1
        if self.binding_error is not None:
            raise self.binding_error
        return self.bindings.get(run_id, ())  # type: ignore[return-value]


class UniterableBindings:
    """Malformed binding iterable: iteration itself explodes."""

    def __iter__(self):
        raise TypeError("malformed binding iterable")


class FakeProjectRoots:
    def __init__(
        self,
        roots: dict[str, str],
        *,
        error: Exception | None = None,
    ) -> None:
        self._roots = roots
        self._error = error

    def project_root(self, project_id: str) -> str | None:
        if self._error is not None:
            raise self._error
        return self._roots.get(project_id)


class FakeArtifactDigests:
    """Project-root-bound digest authority (F1) with injectable failure (F2)."""

    def __init__(self, digests: dict[tuple[str, str], str]) -> None:
        self._digests = digests
        self.calls: list[tuple[str, str]] = []
        self.error: Exception | None = None

    def current_digest(self, project_root: str, ref: str) -> str | None:
        self.calls.append((project_root, ref))
        if self.error is not None:
            raise self.error
        return self._digests.get((project_root, ref))


class FileBackedDigests:
    """R2-F3 — REAL file-backed digest authority, no precomputed constants.

    Computes sha256 over the raw bytes of ``<project_root>/<ref>``; a
    missing file yields None (unavailable). Records every invocation so
    tests can prove which root was actually consulted.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def current_digest(self, project_root: str, ref: str) -> str | None:
        self.calls.append((project_root, ref))
        target = Path(project_root) / ref
        if not target.is_file():
            return None
        return hashlib.sha256(target.read_bytes()).hexdigest()


def build_fixture(
    tmp_path: Path,
    *,
    root: Path | None = None,
    bindings: tuple[GraphRunBindingRecord, ...] | None = None,
    digest_overrides: dict[tuple[str, str], str] | None = None,
    roots: dict[str, str] | None = None,
    run: GraphRunRecord | None = None,
    root_error: Exception | None = None,
) -> tuple[FakeRunStore, FakeProjectRoots, FakeArtifactDigests, Path]:
    project_root = root if root is not None else tmp_path / "demo-project"
    root_text = str(project_root)
    store = FakeRunStore()
    store.runs[RUN_ID] = run if run is not None else make_run()
    store.bindings[RUN_ID] = (
        bindings if bindings is not None else (make_binding(),)
    )
    project_roots = FakeProjectRoots(
        roots if roots is not None else {PROJECT_ID: root_text},
        error=root_error,
    )
    digests: dict[tuple[str, str], str] = {
        (root_text, CONTRACT_REF): CONTRACT_SHA,
        (root_text, PACKET_REF): PACKET_SHA,
    }
    if digest_overrides is not None:
        digests.update(digest_overrides)
    artifact_digests = FakeArtifactDigests(digests)
    return store, project_roots, artifact_digests, project_root


def reconstruct(
    store: FakeRunStore,
    project_roots: FakeProjectRoots,
    artifact_digests: FakeArtifactDigests,
    **overrides: str,
) -> object:
    return reconstruct_prepared_activation_request(
        run_store=store,
        project_roots=project_roots,
        artifact_digests=artifact_digests,
        graph_id=overrides.get("graph_id", GRAPH_ID),
        run_id=overrides.get("run_id", RUN_ID),
        node_id=overrides.get("node_id", NODE_A),
    )


def assert_blocker(code: str, callable_and_args) -> PreparedRunReconstructionError:
    with pytest.raises(PreparedRunReconstructionError) as excinfo:
        callable_and_args()
    assert excinfo.value.code == code, (
        f"expected {code}, got {excinfo.value.code}"
    )
    return excinfo.value


class TestHappyPath:
    def test_reconstructs_existing_activation_request(self, tmp_path: Path) -> None:
        store, roots, digests, root = build_fixture(tmp_path)
        request = reconstruct(store, roots, digests)
        assert request.graph_id == GRAPH_ID
        assert request.graph_run_id == RUN_ID
        assert request.node_id == NODE_A
        assert request.runtime_kind == "serena"
        # F4: expected resolved paths computed independently of the production
        # resolver (os.path.realpath, not the production Path.resolve call).
        assert request.project_root == os.path.realpath(str(root))
        assert request.task_contract_ref == CONTRACT_REF
        assert request.task_packet_path == os.path.realpath(
            os.path.join(str(root), PACKET_REF)
        )
        assert request.provider_id == "provider-x"
        assert request.model_id == "model-x"
        assert request.effort_level == "MAX"

    def test_is_read_only_over_the_store(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        reconstruct(store, roots, digests)
        assert store.run_reads == 1
        assert store.binding_reads == 1
        assert store.writes == 0


class TestProjectBoundDigestIdentity:
    """F1 — digest evidence must be bound to the resolved durable project root."""

    def test_wrong_project_digest_does_not_validate(self, tmp_path: Path) -> None:
        """R2-F3 rebuild — end-to-end over two REAL project trees.

        Both roots carry the SAME relative refs with DIFFERENT file bytes.
        The durable binding stores project B's REAL digests (so a gate that
        consulted project B's root would validate), while the project
        authority resolves the durable project to project A. The root+content
        gate must yield the typed mismatch, and every digest invocation must
        have received project A's ABSOLUTE resolved root.
        """
        root_a = tmp_path / "project-alpha"
        root_b = tmp_path / "project-beta"
        for base in (root_a, root_b):
            (base / "contracts").mkdir(parents=True)
            (base / "packets").mkdir(parents=True)
        (root_a / CONTRACT_REF).write_bytes(b"alpha-contract-bytes")
        (root_a / PACKET_REF).write_bytes(b"alpha-packet-bytes")
        (root_b / CONTRACT_REF).write_bytes(b"beta-contract-bytes")
        (root_b / PACKET_REF).write_bytes(b"beta-packet-bytes")

        def file_digest(root: Path, ref: str) -> str:
            return hashlib.sha256((root / ref).read_bytes()).hexdigest()

        binding = make_binding(
            contract_sha=file_digest(root_b, CONTRACT_REF),
            packet_sha=file_digest(root_b, PACKET_REF),
        )
        # Same refs, different bytes under project A: real drift evidence.
        assert file_digest(root_a, CONTRACT_REF) != binding.task_contract_sha256
        assert file_digest(root_a, PACKET_REF) != binding.task_packet_sha256

        store = FakeRunStore()
        store.runs[RUN_ID] = make_run()
        store.bindings[RUN_ID] = (binding,)
        roots = FakeProjectRoots({PROJECT_ID: str(root_a)})
        digests = FileBackedDigests()

        assert_blocker(
            "PREPARED_RUN_CONTRACT_DIGEST_MISMATCH",
            lambda: reconstruct(store, roots, digests),
        )

        resolved_a = os.path.realpath(str(root_a))
        assert digests.calls, "digest port must be observed"
        for observed_root, observed_ref in digests.calls:
            assert Path(observed_root).is_absolute(), (
                "digest invocations must receive an ABSOLUTE resolved root"
            )
            assert observed_root == resolved_a, (
                "digest invocations must be bound to project A's resolved root"
            )
            assert observed_ref in (CONTRACT_REF, PACKET_REF)
        # The contract is the first gate consulted; it fired the mismatch.
        assert digests.calls[0] == (resolved_a, CONTRACT_REF)

        # The port genuinely serves both trees: against project B the port
        # returns exactly the durable binding digests, proving this test
        # fails for any implementation that binds evidence to another root.
        assert digests.current_digest(str(root_b), CONTRACT_REF) == (
            binding.task_contract_sha256
        )
        assert digests.current_digest(str(root_b), PACKET_REF) == (
            binding.task_packet_sha256
        )

    def test_digest_queries_bound_to_resolved_durable_root(
        self, tmp_path: Path
    ) -> None:
        store, roots, digests, root = build_fixture(tmp_path)
        request = reconstruct(store, roots, digests)
        resolved_root = os.path.realpath(str(root))
        assert digests.calls, "digest port must be observed"
        for observed_root, _ref in digests.calls:
            assert observed_root == resolved_root, (
                "digest lookup must be bound to the resolved durable project root"
            )
        assert request.project_root == resolved_root


class TestPortFailureContainment:
    """F2 — every port/boundary failure maps to a typed blocker, never raw."""

    def test_unexpected_run_store_exception_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.run_error = ValueError("sqlite driver exploded")
        blocker = assert_blocker(
            "PREPARED_RUN_STORE_BLOCKED",
            lambda: reconstruct(store, roots, digests),
        )
        assert blocker.store_code is None

    def test_unexpected_binding_store_exception_blocked(
        self, tmp_path: Path
    ) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.binding_error = RuntimeError("connection reset mid-read")
        blocker = assert_blocker(
            "PREPARED_RUN_STORE_BLOCKED",
            lambda: reconstruct(store, roots, digests),
        )
        assert blocker.store_code is None

    def test_malformed_binding_iterable_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.bindings[RUN_ID] = UniterableBindings()
        assert_blocker(
            "PREPARED_RUN_STORE_BLOCKED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_project_root_port_exception_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, root_error=KeyError("registry backend unavailable")
        )
        assert_blocker(
            "PREPARED_RUN_PROJECT_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )

    def test_digest_port_exception_contract_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        digests.error = ValueError("digest authority exploded")
        assert_blocker(
            "PREPARED_RUN_CONTRACT_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )

    def test_digest_port_exception_packet_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        real_current = digests.current_digest

        def fail_on_packet(project_root: str, ref: str) -> str | None:
            if ref == PACKET_REF:
                raise ValueError("digest authority exploded")
            return real_current(project_root, ref)

        digests.current_digest = fail_on_packet  # type: ignore[method-assign]
        assert_blocker(
            "PREPARED_RUN_PACKET_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )


class TestPreparedMarkers:
    """F3 — prepared identity markers follow store text + SHA-256 rules."""

    def test_empty_graph_definition_digest_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(graph_definition_sha256="")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_malformed_graph_definition_digest_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(graph_definition_sha256="z" * 64)
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_empty_preparation_sha_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(preparation_sha256="")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_malformed_preparation_sha_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(preparation_sha256="ABCDEF")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_empty_preparation_ref_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(preparation_ref="")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_whitespace_preparation_ref_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(preparation_ref="   ")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_control_char_preparation_ref_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path,
            run=make_run(preparation_ref="prep\nref-injected"),
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_empty_project_id_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(project_id="")
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_non_string_marker_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(preparation_sha256=123)
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )


class TestRunIdentity:
    def test_foreign_graph_identity_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, run=make_run(graph_id="graph-other")
        )
        assert_blocker(
            "PREPARED_RUN_IDENTITY_MISMATCH",
            lambda: reconstruct(store, roots, digests),
        )

    def test_record_identity_drift_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.run_override = make_run(run_id="graph-run-v1:" + ("c" * 32))
        assert_blocker(
            "PREPARED_RUN_RECORD_INVALID",
            lambda: reconstruct(store, roots, digests),
        )

    def test_missing_run_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.runs.clear()
        assert_blocker(
            "PREPARED_RUN_NOT_FOUND",
            lambda: reconstruct(store, roots, digests),
        )

    def test_unprepared_run_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path,
            run=make_run(
                project_id=None,
                graph_definition_sha256=None,
                preparation_ref=None,
                preparation_sha256=None,
            ),
        )
        assert_blocker(
            "PREPARED_RUN_NOT_PREPARED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_store_failure_mapped_fail_closed(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        store.run_error = GraphStoreError("STORE_EXPLODED")
        blocker = assert_blocker(
            "PREPARED_RUN_STORE_BLOCKED",
            lambda: reconstruct(store, roots, digests),
        )
        assert blocker.store_code == "STORE_EXPLODED"


class TestNodeSelection:
    def test_wrong_node_not_bound_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        assert_blocker(
            "PREPARED_RUN_NODE_NOT_BOUND",
            lambda: reconstruct(store, roots, digests, node_id=NODE_B),
        )

    def test_missing_bindings_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path, bindings=())
        assert_blocker(
            "PREPARED_RUN_NODE_NOT_BOUND",
            lambda: reconstruct(store, roots, digests),
        )

    def test_duplicate_binding_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, bindings=(make_binding(), make_binding())
        )
        assert_blocker(
            "PREPARED_RUN_NODE_BINDING_AMBIGUOUS",
            lambda: reconstruct(store, roots, digests),
        )

    def test_unauthorized_runtime_kind_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, bindings=(make_binding(runtime_kind="other"),)
        )
        assert_blocker(
            "PREPARED_RUN_RUNTIME_KIND_UNAUTHORIZED",
            lambda: reconstruct(store, roots, digests),
        )

    def test_corrupt_binding_digest_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path, bindings=(make_binding(contract_sha="not-a-digest"),)
        )
        assert_blocker(
            "PREPARED_RUN_BINDING_RECORD_INVALID",
            lambda: reconstruct(store, roots, digests),
        )

    def test_binding_run_drift_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path,
            bindings=(
                make_binding(run_id="graph-run-v1:" + ("d" * 32)),
            ),
        )
        assert_blocker(
            "PREPARED_RUN_BINDING_RECORD_INVALID",
            lambda: reconstruct(store, roots, digests),
        )


class TestContractPacketIdentity:
    def test_changed_contract_digest_blocked(self, tmp_path: Path) -> None:
        root = tmp_path / "demo-project"
        store, roots, digests, _r = build_fixture(
            tmp_path,
            root=root,
            digest_overrides={(str(root), CONTRACT_REF): _sha("contract-v2")},
        )
        assert_blocker(
            "PREPARED_RUN_CONTRACT_DIGEST_MISMATCH",
            lambda: reconstruct(store, roots, digests),
        )

    def test_changed_packet_digest_blocked(self, tmp_path: Path) -> None:
        root = tmp_path / "demo-project"
        store, roots, digests, _r = build_fixture(
            tmp_path,
            root=root,
            digest_overrides={(str(root), PACKET_REF): _sha("packet-v2")},
        )
        assert_blocker(
            "PREPARED_RUN_PACKET_DIGEST_MISMATCH",
            lambda: reconstruct(store, roots, digests),
        )

    def test_contract_unavailable_blocked(self, tmp_path: Path) -> None:
        root = tmp_path / "demo-project"
        store, roots, digests, _r = build_fixture(
            tmp_path,
            root=root,
            digest_overrides={(str(root), CONTRACT_REF): ""},
        )
        assert_blocker(
            "PREPARED_RUN_CONTRACT_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )

    def test_packet_unavailable_blocked(self, tmp_path: Path) -> None:
        root = tmp_path / "demo-project"
        store, roots, digests, _r = build_fixture(tmp_path, root=root)
        digests._digests.pop((str(root), PACKET_REF))
        assert_blocker(
            "PREPARED_RUN_PACKET_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )

    def test_packet_path_resolution_failure_blocked(self, tmp_path: Path) -> None:
        """R2-F2 — packet path resolution failure after both digest ports
        succeed must map to the typed packet blocker, never escape raw."""
        root = tmp_path / "demo-project"
        packets_dir = root / "packets"
        packets_dir.mkdir(parents=True)
        loop_ref = "packets/loop.packet.json"
        loop_sha = _sha("loop-packet")
        try:
            (root / loop_ref).symlink_to(root / loop_ref)
        except (NotImplementedError, OSError):
            pytest.skip("symlink creation unsupported on this host")
        store, roots, digests, _r = build_fixture(
            tmp_path,
            root=root,
            bindings=(
                make_binding(task_packet_ref=loop_ref, packet_sha=loop_sha),
            ),
            digest_overrides={(str(root), loop_ref): loop_sha},
        )
        blocker = assert_blocker(
            "PREPARED_RUN_PACKET_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )
        assert blocker.store_code is None


class TestProjectAuthority:
    def test_project_unavailable_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path, roots={})
        assert_blocker(
            "PREPARED_RUN_PROJECT_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )

    def test_relative_project_root_blocked_before_resolution_use(
        self, tmp_path: Path
    ) -> None:
        """R2-F1 — a relative root from the project authority must yield the
        typed project blocker BEFORE any resolution use, with zero digest
        invocations (Path.resolve() must never bind to the process CWD)."""
        store = FakeRunStore()
        store.runs[RUN_ID] = make_run()
        store.bindings[RUN_ID] = (make_binding(),)
        roots = FakeProjectRoots({PROJECT_ID: "proj/demo"})
        digests = FakeArtifactDigests({})
        blocker = assert_blocker(
            "PREPARED_RUN_PROJECT_UNAVAILABLE",
            lambda: reconstruct(store, roots, digests),
        )
        assert blocker.store_code is None
        assert digests.calls == [], (
            "relative project root must be rejected before any digest use"
        )


class TestInputIdentity:
    def test_blank_run_id_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        assert_blocker(
            "PREPARED_RUN_INPUT_INVALID",
            lambda: reconstruct(store, roots, digests, run_id="   "),
        )

    def test_blank_node_id_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        assert_blocker(
            "PREPARED_RUN_INPUT_INVALID",
            lambda: reconstruct(store, roots, digests, node_id=""),
        )

    def test_blank_graph_id_blocked(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(tmp_path)
        assert_blocker(
            "PREPARED_RUN_INPUT_INVALID",
            lambda: reconstruct(store, roots, digests, graph_id=""),
        )


class TestRestartStability:
    def test_re_read_is_stable_and_never_mutates(self, tmp_path: Path) -> None:
        store, roots, digests, _root = build_fixture(
            tmp_path,
            bindings=(make_binding(), make_binding(node_id=NODE_B)),
        )
        first = reconstruct(store, roots, digests)
        second = reconstruct(store, roots, digests)
        assert first == second
        assert store.run_reads == 2
        assert store.binding_reads == 2
        assert store.writes == 0
