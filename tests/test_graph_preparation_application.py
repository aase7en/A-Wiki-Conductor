"""WO-P1-470 — RED-first Child-B preparation + binding application contract.

These tests pin the frozen Child-B seam contract from WO-P1-470 §3-§6,
WO-P1-467 §5 and WO-P1-452 §13-§14 before any production code exists:

- one injectable ``PreparationApplication`` service object;
- fail-closed verify-before-prepare over durable JobStore checkpoint evidence;
- exactly one ``GraphStore.prepare_run`` per call after all checks pass;
- typed ``RuntimeActivationRequest`` reconstruction from trusted binding and
  current registry authorities with fresh digest checks;
- zero JobStore writes, job creation, provider selection, NEXT_READY or
  runtime activation authority.

The production module ``a_conductor.graph.preparation_application`` does not
exist yet.  Every test imports it lazily so each case independently reports
RED (ModuleNotFoundError) until the implementation lands, and the observed RED
evidence is preserved per WO-P1-470 §6/§8.
"""

from __future__ import annotations

import dataclasses
import hashlib
import importlib
import sqlite3
from pathlib import Path

import pytest

from a_conductor.domain import Project, TaskState
from a_conductor.graph.domain import DependencyType, TaskEdge, TaskNode
from a_conductor.graph.graph import build_graph
from a_conductor.graph.store import GraphRunBindingSpec, GraphStore, GraphStoreError
from a_conductor.job_store import SQLiteJobStore
from a_conductor.provider_config_store import ProviderConfigurationSnapshot
from a_conductor.provider_configuration import (
    EgressBoundary,
    HarnessStrategy,
    ProtocolFamily,
    ProviderConfiguration,
    ProviderModelConfiguration,
    ProviderTrustClass,
)
from a_conductor.registry import RegistryNotFoundError
from a_conductor.runtime_activation import RuntimeActivationRequest


GRAPH_ID = "graph-wo470"
PROJECT_ID = "project-wo470"
WORK_ORDER_REF = "WO-P1-470"
JOB_ALPHA = "job-wo470-alpha"
JOB_BETA = "job-wo470-beta"
PROVIDER_ID = "cointh-glm"
PROVIDER_DISABLED = "disabled-provider"
MODEL_ID = "glm-5.3"
MODEL_ALT = "glm-5.3-air"
EFFORT = "LOW"
EVIDENCE_PREFIX = "graph-run-preparation:"


def _app():
    return importlib.import_module("a_conductor.graph.preparation_application")


def _ref(seed: str) -> str:
    return f"graph-run-preparation-v1:{hashlib.sha256(seed.encode()).hexdigest()[:32]}"


REF_A = _ref("wo470-ref-a")
REF_B = _ref("wo470-ref-b")


def _canonical_evidence(ref: str) -> str:
    return EVIDENCE_PREFIX + ref


def _node(node_id: str, *, worker_requirement: tuple[str, ...] = ()) -> TaskNode:
    return TaskNode(
        id=node_id,
        objective=f"objective {node_id}",
        expected_outputs=("out.md",),
        read_set=("src/**",),
        write_set=("docs/out.md",),
        worker_requirement=worker_requirement,
        model_requirement=None,
        priority=5,
        timeout_seconds=600,
        retry_policy_ref="default",
        artifacts=("artifact.json",),
    )


def _provider_profile(*, enabled: bool = True) -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id=PROVIDER_ID,
        display_name="GLM test profile",
        provider_type="remote",
        protocol_family=ProtocolFamily.OPENAI_COMPATIBLE,
        endpoint_ref="endpoint-test-glm",
        credential_ref="credential-test-glm",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.DIRECT_API,),
        max_concurrency=2,
        models=(
            ProviderModelConfiguration(
                model_id=MODEL_ID,
                display_name="GLM 5.3",
                supported_effort_levels=("LOW", "HIGH", "MAX"),
            ),
            ProviderModelConfiguration(
                model_id=MODEL_ALT,
                display_name="GLM 5.3 Air",
                supported_effort_levels=("LOW", "HIGH", "MAX"),
            ),
        ),
        enabled=enabled,
    )


class _ReadonlyJobPort:
    """Spy exposing only the accepted read-only JobStore surface."""

    def __init__(self, store: SQLiteJobStore) -> None:
        self._store = store
        self.get_job_calls: list[str] = []
        self.list_events_calls: list[str] = []

    def get_job(self, job_id: str):
        self.get_job_calls.append(job_id)
        return self._store.get_job(job_id)

    def list_events(self, job_id: str):
        self.list_events_calls.append(job_id)
        return self._store.list_events(job_id)

    def __getattr__(self, name: str):
        raise AssertionError(f"Child B must not touch JobStore.{name}")


class _PrepareSpyGraphStore:
    """Spy exposing only the accepted GraphStore read + prepare surface."""

    def __init__(self, store: GraphStore) -> None:
        self._store = store
        self.prepare_calls: list[dict] = []

    def load_graph(self, graph_id: str):
        return self._store.load_graph(graph_id)

    def prepare_run(self, **kwargs):
        self.prepare_calls.append(kwargs)
        return self._store.prepare_run(**kwargs)

    def load_graph_run(self, run_id: str):
        return self._store.load_graph_run(run_id)

    def load_graph_run_bindings(self, run_id: str):
        return self._store.load_graph_run_bindings(run_id)

    def __getattr__(self, name: str):
        raise AssertionError(f"Child B must not touch GraphStore.{name}")


class _V1BindingGraphPort(_PrepareSpyGraphStore):
    """Simulates an unmigrated v1 store at the binding-read boundary."""

    def load_graph_run_bindings(self, run_id: str):
        raise GraphStoreError("GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE")


class _FakeRegistry:
    def __init__(self, projects: dict[str, Project]) -> None:
        self._projects = projects

    def get_project(self, project_id: str) -> Project:
        try:
            return self._projects[project_id]
        except KeyError:
            raise RegistryNotFoundError(project_id) from None


class _FakeProviderAuthority:
    def __init__(self, snapshots: dict[str, ProviderConfigurationSnapshot]) -> None:
        self._snapshots = snapshots
        self.calls: list[str] = []

    def get_provider_snapshot(self, provider_id: str):
        self.calls.append(provider_id)
        return self._snapshots.get(provider_id)

    def __getattr__(self, name: str):
        raise AssertionError(f"Child B must not touch provider authority .{name}")


class _Env:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp_path = tmp_path
        self.root = tmp_path / "proj-root"
        (self.root / "contracts").mkdir(parents=True)
        (self.root / "packets").mkdir(parents=True)
        self.contract_sha: dict[str, str] = {}
        self.packet_sha: dict[str, str] = {}
        for node_id in ("a", "b"):
            contract_bytes = f'{{"task_contract":"wo470-{node_id}"}}'.encode()
            packet_bytes = f'{{"task_packet":"wo470-{node_id}"}}'.encode()
            (self.root / "contracts" / f"node-{node_id}.json").write_bytes(
                contract_bytes
            )
            (self.root / "packets" / f"node-{node_id}.json").write_bytes(packet_bytes)
            self.contract_sha[node_id] = hashlib.sha256(contract_bytes).hexdigest()
            self.packet_sha[node_id] = hashlib.sha256(packet_bytes).hexdigest()
        self.job_db = tmp_path / "jobs.sqlite"
        self.graph_db = tmp_path / "graphs.sqlite"
        self.job_store = SQLiteJobStore(self.job_db)
        self.job_store.initialize()
        self.graph_store = GraphStore(self.graph_db)
        self._versions: dict[str, int] = {}

    def seed_graph(self, nodes) -> None:
        self.graph_store.save_graph(build_graph(list(nodes), []), GRAPH_ID)

    def make_job(
        self,
        job_id: str,
        *,
        project_id: str = PROJECT_ID,
        work_order_ref: str = WORK_ORDER_REF,
    ):
        state = self.job_store.create_job(
            job_id=job_id,
            work_order_ref=work_order_ref,
            project_id=project_id,
        )
        self._versions[job_id] = state.version
        return state

    def checkpoint(self, job_id: str, checkpoint_ref: str):
        state = self.job_store.checkpoint(
            job_id,
            checkpoint_ref=checkpoint_ref,
            expected_version=self._versions[job_id],
        )
        self._versions[job_id] = state.version
        return state

    def cancel(self, job_id: str) -> None:
        state = self.job_store.transition(
            job_id,
            TaskState.CANCELLED,
            expected_version=self._versions[job_id],
        )
        self._versions[job_id] = state.version

    def baseline(self) -> None:
        self.seed_graph([_node("a"), _node("b")])
        self.make_job(JOB_ALPHA)
        self.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))

    def registry(self) -> _FakeRegistry:
        return _FakeRegistry(
            {PROJECT_ID: Project(PROJECT_ID, "WO470 project", str(self.root))}
        )

    def provider_authority(self) -> _FakeProviderAuthority:
        return _FakeProviderAuthority(
            {
                PROVIDER_ID: ProviderConfigurationSnapshot(
                    profile=_provider_profile(),
                    endpoint=None,
                    generation=1,
                    observation=None,
                ),
                PROVIDER_DISABLED: ProviderConfigurationSnapshot(
                    profile=_provider_profile(enabled=False),
                    endpoint=None,
                    generation=1,
                    observation=None,
                ),
            }
        )

    def build_app(
        self,
        *,
        job_port: _ReadonlyJobPort | None = None,
        graph_port: _PrepareSpyGraphStore | None = None,
        project_registry: _FakeRegistry | None = None,
        provider_authority: _FakeProviderAuthority | None = None,
    ):
        job_port = job_port or _ReadonlyJobPort(self.job_store)
        graph_port = graph_port or _PrepareSpyGraphStore(self.graph_store)
        project_registry = project_registry or self.registry()
        provider_authority = provider_authority or self.provider_authority()
        app = _app().PreparationApplication(
            job_store=job_port,
            graph_store=graph_port,
            project_registry=project_registry,
            provider_authority=provider_authority,
        )
        return app, job_port, graph_port, project_registry, provider_authority

    def job_row_counts(self) -> tuple[int, int]:
        with sqlite3.connect(self.job_db) as conn:
            records = conn.execute("SELECT COUNT(*) FROM job_records").fetchone()[0]
            events = conn.execute("SELECT COUNT(*) FROM job_events").fetchone()[0]
        return int(records), int(events)

    def graph_row_counts(self) -> tuple[int, int]:
        with sqlite3.connect(self.graph_db) as conn:
            runs = conn.execute("SELECT COUNT(*) FROM graph_runs").fetchone()[0]
            bindings = conn.execute(
                "SELECT COUNT(*) FROM graph_run_bindings"
            ).fetchone()[0]
        return int(runs), int(bindings)


@pytest.fixture()
def env(tmp_path: Path) -> _Env:
    return _Env(tmp_path)


def _binding(mod, env: _Env, node_id: str = "a", **overrides):
    fields = dict(
        node_id=node_id,
        runtime_kind="serena",
        task_contract_ref=f"contracts/node-{node_id}.json",
        task_contract_sha256=env.contract_sha[node_id],
        task_packet_ref=f"packets/node-{node_id}.json",
        task_packet_sha256=env.packet_sha[node_id],
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        effort_level=EFFORT,
    )
    fields.update(overrides)
    return mod.NodeBindingIntent(**fields)


def _intent(
    mod,
    env: _Env,
    *,
    ref: str = REF_A,
    job_id: str = JOB_ALPHA,
    graph_id: str = GRAPH_ID,
    project_id: str = PROJECT_ID,
    work_order_ref: str = WORK_ORDER_REF,
    bindings=None,
):
    if bindings is None:
        bindings = (_binding(mod, env),)
    return mod.PreparationIntent(
        preparation_ref=ref,
        driving_job_id=job_id,
        graph_id=graph_id,
        project_id=project_id,
        work_order_ref=work_order_ref,
        bindings=tuple(bindings),
    )


def _prepare(env: _Env, intent):
    app, job_port, graph_port, _, _ = env.build_app()
    return app.prepare(intent), job_port, graph_port


def _fails(env: _Env, intent, *, code: str):
    mod = _app()
    app, job_port, graph_port, _, _ = env.build_app()
    with pytest.raises(mod.PreparationApplicationError) as excinfo:
        app.prepare(intent)
    assert excinfo.value.code == code
    assert graph_port.prepare_calls == []
    return job_port, graph_port


INVALID_REFS = [
    "graph-run-preparation-v1:" + "A" * 32,
    "graph-run-preparation-v1:" + "a" * 31,
    "graph-run-preparation-v1:" + "a" * 33,
    " graph-run-preparation-v1:" + "a" * 32,
    "graph-run-preparation-v1:" + "a" * 32 + " ",
    "graph-run-preparation:" + "a" * 32,
    "graph-run-prep-v1:" + "a" * 32,
    "graph-run-preparation-v1:project-wo470:" + "a" * 32,
    "GRAPH-RUN-PREPARATION-V1:" + "a" * 32,
    "graph-run-preparation-v1:" + "g" * 32,
    "",
    "   ",
]


@pytest.mark.parametrize("bad_ref", INVALID_REFS)
def test_noncanonical_preparation_ref_fails_before_any_read(env, bad_ref):
    app = _app()
    env.baseline()
    job_port, graph_port = _fails(
        env, _intent(app, env, ref=bad_ref), code="PREPARATION_REF_INVALID"
    )
    assert job_port.get_job_calls == []
    assert job_port.list_events_calls == []
    assert graph_port.prepare_calls == []


NONCANONICAL_EVIDENCE = [
    REF_A,
    _canonical_evidence("graph-run-preparation-v1:" + "A" * 32),
    _canonical_evidence("graph-run-preparation-v1:" + "a" * 31),
    _canonical_evidence("graph-run-preparation-v1:" + "a" * 33),
    " " + _canonical_evidence(REF_A),
    "graph-run-preparation: " + REF_A,
    _canonical_evidence(REF_A) + " ",
    "other-run-preparation:" + REF_A,
    _canonical_evidence(REF_A) + ":extra",
]


@pytest.mark.parametrize("bad_evidence", NONCANONICAL_EVIDENCE)
def test_noncanonical_checkpoint_evidence_cannot_establish_provenance(
    env, bad_evidence
):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, bad_evidence)
    _fails(env, _intent(app, env), code="PREPARATION_PROVENANCE_MISSING")


def test_zero_canonical_refs_fails_provenance_missing(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    _fails(env, _intent(app, env), code="PREPARATION_PROVENANCE_MISSING")


def test_duplicate_same_ref_rows_are_idempotent_evidence(env):
    app = _app()
    env.baseline()
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    result, _, graph_port = _prepare(env, _intent(app, env))
    assert len(graph_port.prepare_calls) == 1
    assert graph_port.prepare_calls[0]["preparation_ref"] == REF_A
    assert result.run.preparation_ref == REF_A


def test_two_distinct_refs_fail_provenance_ambiguous_before_prepare(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_B))
    _fails(env, _intent(app, env), code="PREPARATION_PROVENANCE_AMBIGUOUS")


def test_ambiguous_failure_is_order_independent(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_B))
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env), code="PREPARATION_PROVENANCE_AMBIGUOUS")


def test_ambiguous_failure_is_not_resolved_by_submitted_ref(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_B))
    _fails(env, _intent(app, env, ref=REF_B), code="PREPARATION_PROVENANCE_AMBIGUOUS")


def test_submitted_ref_differs_from_sole_durable_ref_fails_mismatch(env):
    app = _app()
    env.baseline()
    _fails(env, _intent(app, env, ref=REF_B), code="PREPARATION_PROVENANCE_MISMATCH")


def test_sole_canonical_ref_recovered_after_decoy_rows_no_latest_or_first_choice(
    env,
):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, "other-run-preparation:" + REF_A)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    env.checkpoint(JOB_ALPHA, "graph-run-preparation:not-a-ref")
    result, _, graph_port = _prepare(env, _intent(app, env))
    assert len(graph_port.prepare_calls) == 1
    assert result.run.preparation_ref == REF_A


def test_ref_checkpointed_on_other_job_cannot_establish_provenance(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    env.make_job(JOB_BETA)
    env.checkpoint(JOB_BETA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env), code="PREPARATION_PROVENANCE_MISSING")


def test_missing_driving_job_propagates_job_not_found(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA)
    _fails(env, _intent(app, env, job_id="job-wo470-missing"), code="JOB_NOT_FOUND")


def test_terminal_driving_job_fails_closed(env):
    app = _app()
    env.baseline()
    env.cancel(JOB_ALPHA)
    _fails(env, _intent(app, env), code="DRIVING_JOB_TERMINAL")


def test_driving_job_project_binding_mismatch_fails_closed(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA, project_id="project-other")
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env), code="DRIVING_JOB_PROJECT_MISMATCH")


def test_driving_job_work_order_binding_mismatch_fails_closed(env):
    app = _app()
    env.seed_graph([_node("a"), _node("b")])
    env.make_job(JOB_ALPHA, work_order_ref="WO-OTHER")
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env), code="DRIVING_JOB_WORK_ORDER_MISMATCH")


def test_missing_project_registration_fails_closed(env):
    app = _app()
    env.baseline()
    empty_registry = _FakeRegistry({})
    mod = _app()
    application = mod.PreparationApplication(
        job_store=_ReadonlyJobPort(env.job_store),
        graph_store=_PrepareSpyGraphStore(env.graph_store),
        project_registry=empty_registry,
        provider_authority=env.provider_authority(),
    )
    with pytest.raises(mod.PreparationApplicationError) as excinfo:
        application.prepare(_intent(app, env))
    assert excinfo.value.code == "PROJECT_AUTHORITY_UNAVAILABLE"


def test_missing_graph_fails_closed(env):
    app = _app()
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env, graph_id="graph-missing"), code="GRAPH_UNAVAILABLE")


def test_binding_node_not_in_graph_fails_closed(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, node_id="zz"),)),
        code="BINDING_NODE_INVALID",
    )


def test_nonempty_worker_requirement_fails_capability_gate(env):
    app = _app()
    env.seed_graph([_node("a", worker_requirement=("repository-read",)), _node("b")])
    env.make_job(JOB_ALPHA)
    env.checkpoint(JOB_ALPHA, _canonical_evidence(REF_A))
    _fails(env, _intent(app, env), code="RUNTIME_CAPABILITY_AUTHORITY_UNAVAILABLE")


BAD_REFS = [
    "/abs/contract.json",
    r"C:\abs\contract.json",
    "contracts\\node-a.json",
    "../outside.json",
    "./contracts/node-a.json",
    "contracts//node-a.json",
    "contracts/../packets/node-a.json",
]


@pytest.mark.parametrize("bad_ref", BAD_REFS)
def test_contract_and_packet_refs_must_be_project_relative(env, bad_ref):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, task_contract_ref=bad_ref),)),
        code="TASK_CONTRACT_REF_INVALID",
    )
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, task_packet_ref=bad_ref),)),
        code="TASK_PACKET_REF_INVALID",
    )


BAD_DIGESTS = ["A" * 64, "a" * 63, "z" * 64, ""]


@pytest.mark.parametrize("bad_digest", BAD_DIGESTS)
def test_malformed_digests_fail_before_prepare(env, bad_digest):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(
            app, env, bindings=(_binding(app, env, task_contract_sha256=bad_digest),)
        ),
        code="TASK_CONTRACT_DIGEST_INVALID",
    )
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, task_packet_sha256=bad_digest),)),
        code="TASK_PACKET_DIGEST_INVALID",
    )


def test_missing_contract_file_fails_closed(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(
            app,
            env,
            bindings=(_binding(app, env, task_contract_ref="contracts/node-z.json"),),
        ),
        code="TASK_CONTRACT_UNAVAILABLE",
    )


def test_missing_packet_file_fails_closed(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(
            app,
            env,
            bindings=(_binding(app, env, task_packet_ref="packets/node-z.json"),),
        ),
        code="TASK_PACKET_UNAVAILABLE",
    )


def test_stale_contract_digest_fails_closed(env):
    app = _app()
    env.baseline()
    stale = hashlib.sha256(b"changed-contract").hexdigest()
    _fails(
        env,
        _intent(
            app, env, bindings=(_binding(app, env, task_contract_sha256=stale),)
        ),
        code="TASK_CONTRACT_DIGEST_MISMATCH",
    )


def test_stale_packet_digest_fails_closed(env):
    app = _app()
    env.baseline()
    stale = hashlib.sha256(b"changed-packet").hexdigest()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, task_packet_sha256=stale),)),
        code="TASK_PACKET_DIGEST_MISMATCH",
    )


@pytest.mark.parametrize("bad_kind", ["claude-code", "SERENA", "serena-local", "zcode"])
def test_runtime_kind_other_than_exact_serena_fails_closed(env, bad_kind):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, runtime_kind=bad_kind),)),
        code="RUNTIME_KIND_AUTHORITY_UNAVAILABLE",
    )


@pytest.mark.parametrize("blank", ["", "   "])
def test_missing_explicit_route_fields_fail_closed(env, blank):
    app = _app()
    env.baseline()
    for field in ("provider_id", "model_id", "effort_level"):
        _fails(
            env,
            _intent(app, env, bindings=(_binding(app, env, **{field: blank}),)),
            code="ROUTE_SELECTION_REQUIRED",
        )


def test_unknown_provider_fails_route_authorization(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(
            app, env, bindings=(_binding(app, env, provider_id="provider-none"),)
        ),
        code="ROUTE_SELECTION_UNAUTHORIZED",
    )


def test_unknown_model_fails_route_authorization(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, model_id="glm-9.9"),)),
        code="ROUTE_SELECTION_UNAUTHORIZED",
    )


def test_unsupported_effort_fails_route_authorization(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(app, env, bindings=(_binding(app, env, effort_level="ULTRA"),)),
        code="ROUTE_SELECTION_UNAUTHORIZED",
    )


def test_disabled_provider_fails_route_authorization(env):
    app = _app()
    env.baseline()
    _fails(
        env,
        _intent(
            app, env, bindings=(_binding(app, env, provider_id=PROVIDER_DISABLED),)
        ),
        code="ROUTE_SELECTION_UNAUTHORIZED",
    )


def test_valid_intent_prepares_exactly_once_with_identical_ref(env):
    app = _app()
    env.baseline()
    result, _, graph_port, _, provider_auth = _full_prepare(env, _intent(app, env))
    assert len(graph_port.prepare_calls) == 1
    call = graph_port.prepare_calls[0]
    assert call["graph_id"] == GRAPH_ID
    assert call["project_id"] == PROJECT_ID
    assert call["preparation_ref"] == REF_A
    (spec,) = call["bindings"]
    assert isinstance(spec, GraphRunBindingSpec)
    assert spec.node_id == "a"
    assert spec.runtime_kind == "serena"
    assert spec.task_contract_ref == "contracts/node-a.json"
    assert spec.task_contract_sha256 == env.contract_sha["a"]
    assert spec.task_packet_ref == "packets/node-a.json"
    assert spec.task_packet_sha256 == env.packet_sha["a"]
    assert spec.provider_id == PROVIDER_ID
    assert spec.model_id == MODEL_ID
    assert spec.effort_level == EFFORT
    assert result.run.preparation_ref == REF_A
    assert result.run.run_id.startswith("graph-run-v1:")
    assert provider_auth.calls == [PROVIDER_ID]


def test_same_ref_replay_returns_same_run_id(env):
    app = _app()
    env.baseline()
    intent = _intent(app, env)
    application, _, graph_port, _, _ = env.build_app()
    first = application.prepare(intent)
    replay = application.prepare(intent)
    assert replay.run.run_id == first.run.run_id
    assert len(graph_port.prepare_calls) == 2


def test_same_ref_changed_intent_surfaces_graphstore_identity_mismatch(env):
    app = _app()
    env.baseline()
    application, _, graph_port, _, _ = env.build_app()
    application.prepare(_intent(app, env))
    mod = _app()
    with pytest.raises(mod.PreparationApplicationError) as excinfo:
        application.prepare(
            _intent(app, env, bindings=(_binding(app, env, model_id=MODEL_ALT),))
        )
    assert excinfo.value.code == "GRAPH_RUN_PREPARATION_IDENTITY_MISMATCH"
    assert len(graph_port.prepare_calls) == 2
    assert env.graph_row_counts() == (1, 1)


def test_intentional_rerun_new_driving_job_new_ref_mints_new_run(env):
    app = _app()
    env.baseline()
    env.make_job(JOB_BETA)
    env.checkpoint(JOB_BETA, _canonical_evidence(REF_B))
    first, _, _ = _prepare(env, _intent(app, env))
    second, _, _ = _prepare(env, _intent(app, env, ref=REF_B, job_id=JOB_BETA))
    assert second.run.run_id != first.run.run_id
    assert env.graph_row_counts() == (2, 2)
    durable_first = env.graph_store.load_graph_run(first.run.run_id)
    assert durable_first.preparation_ref == REF_A


def test_v1_binding_authority_unavailable_surfaces_typed_no_auto_upgrade(env):
    app = _app()
    env.baseline()
    mod = _app()
    graph_port = _V1BindingGraphPort(env.graph_store)
    application = mod.PreparationApplication(
        job_store=_ReadonlyJobPort(env.job_store),
        graph_store=graph_port,
        project_registry=env.registry(),
        provider_authority=env.provider_authority(),
    )
    with pytest.raises(mod.PreparationApplicationError) as excinfo:
        application.prepare(_intent(app, env))
    assert excinfo.value.code == "GRAPH_RUN_BINDING_AUTHORITY_UNAVAILABLE"
    assert len(graph_port.prepare_calls) == 1
    assert env.graph_row_counts() == (1, 1)


def test_activation_request_reconstruction_is_field_explicit(env):
    app = _app()
    env.baseline()
    result, _, _, _, _ = _full_prepare(env, _intent(app, env))
    (request,) = result.activation_requests
    assert isinstance(request, RuntimeActivationRequest)
    assert request.graph_id == GRAPH_ID
    assert request.graph_run_id == result.run.run_id
    assert request.node_id == "a"
    assert request.runtime_kind == "serena"
    assert request.project_root == str(env.root)
    assert request.task_contract_ref == "contracts/node-a.json"
    assert (
        Path(request.task_packet_path).resolve() == (env.root / "packets/node-a.json").resolve()
    )
    assert request.provider_id == PROVIDER_ID
    assert request.model_id == MODEL_ID
    assert request.effort_level == EFFORT
    assert request.effort_level != "MAX"


def test_reconstruction_covers_every_binding_node(env):
    app = _app()
    env.baseline()
    intent = _intent(app, env, bindings=(_binding(app, env, "a"), _binding(app, env, "b")))
    result, _, _, _, _ = _full_prepare(env, intent)
    assert {item.node_id for item in result.activation_requests} == {"a", "b"}
    for item in result.activation_requests:
        assert item.provider_id == PROVIDER_ID
        assert item.effort_level == EFFORT


def test_zero_jobstore_writes_on_success(env):
    app = _app()
    env.baseline()
    before = env.job_row_counts()
    _full_prepare(env, _intent(app, env))
    assert env.job_row_counts() == before
    assert env.graph_row_counts() == (1, 1)


def test_zero_jobstore_writes_and_zero_prepare_on_failure_family(env):
    app = _app()
    env.baseline()
    before = env.job_row_counts()
    failures = [
        (_intent(app, env, ref=REF_B), "PREPARATION_PROVENANCE_MISMATCH"),
        (
            _intent(app, env, bindings=(_binding(app, env, runtime_kind="zcode"),)),
            "RUNTIME_KIND_AUTHORITY_UNAVAILABLE",
        ),
        (
            _intent(app, env, bindings=(_binding(app, env, provider_id="provider-none"),)),
            "ROUTE_SELECTION_UNAUTHORIZED",
        ),
        (
            _intent(
                app,
                env,
                bindings=(_binding(app, env, task_contract_sha256="a" * 64),),
            ),
            "TASK_CONTRACT_DIGEST_MISMATCH",
        ),
        (_intent(app, env, graph_id="graph-missing"), "GRAPH_UNAVAILABLE"),
        (
            _intent(app, env, bindings=(_binding(app, env, node_id="zz"),)),
            "BINDING_NODE_INVALID",
        ),
    ]
    mod = _app()
    application, job_port, graph_port, _, _ = env.build_app()
    for intent, code in failures:
        with pytest.raises(mod.PreparationApplicationError) as excinfo:
            application.prepare(intent)
        assert excinfo.value.code == code
    assert graph_port.prepare_calls == []
    assert env.job_row_counts() == before
    assert env.graph_row_counts() == (0, 0)


def test_application_exposes_no_selection_or_activation_surface(env):
    app = _app()
    env.baseline()
    result, _, _, _, _ = _full_prepare(env, _intent(app, env))
    assert [field.name for field in dataclasses.fields(result)] == [
        "run",
        "activation_requests",
    ]
    application, _, _, _, _ = env.build_app()
    for name in (
        "select_provider",
        "rank_providers",
        "next_ready",
        "activate",
        "dispatch",
        "create_job",
        "checkpoint",
    ):
        assert not hasattr(application, name)


def _full_prepare(env: _Env, intent):
    app, job_port, graph_port, registry, provider = env.build_app()
    return (
        app.prepare(intent),
        job_port,
        graph_port,
        registry,
        provider,
    )
