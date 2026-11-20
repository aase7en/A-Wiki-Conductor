"""Q29+Q30 composition/truth-audit proofs: recovery consumer is production-
called, the assembly executes every declared gate, and no dead authority
paths remain."""

from __future__ import annotations

import json

from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.supervised_run_coordinator import SupervisedRunIdentity
from a_conductor.zcode_runner import (
    ZCODE_BACKEND_ID,
    ZCodeBackendAdapter,
    SupervisedZCodeRunner,
    ZCodeTaskPacketIdentity,
)
from tests.test_zcode_runner import (
    BASE_URL, BINDING, EXEC, BUNDLE, FS, Selection, Secrets, TransportFactory,
    _packet_file, _script,
)
from a_conductor.zcode_child_recovery import ZCodeChildRecoveryKind


class LiveObserver:
    def __init__(self, live):
        self.live = live

    def observe_child(self, pid):
        return self.live


def _runner_with_observer(tmp_path, *, observer, store):
    packet_identity = ZCodeTaskPacketIdentity.from_task_packet_file(
        _packet_file(tmp_path), trusted_root=str(tmp_path)
    )
    adapter = ZCodeBackendAdapter(
        transport_factory=TransportFactory(_script()),
        filesystem=FS(tmp_path),
        execution_store=store,
        selection_source=Selection(),
        expected_binding=BINDING,
        expected_base_url=BASE_URL,
        secret_resolver=Secrets(),
        secret_reference="secret-ref:zcode-credential",
        packet=packet_identity,
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
        child_observer=observer,
    )
    return SupervisedZCodeRunner(
        task_packet=packet_identity,
        execution_store=store,
        identity=SupervisedRunIdentity(
            job_id="j", work_order_ref="WO-P1-158", project_id="p", worker_id="w",
            backend_id=ZCODE_BACKEND_ID, branch="main", head_before="h" * 40,
            runtime_profile_ref="rt", repo_root=str(tmp_path)),
        adapter=adapter, executable=EXEC, bundle_js=BUNDLE, poll_interval_seconds=0.01,
    )


def _exec_id(store):
    import sqlite3
    con = sqlite3.connect(store.database_path)
    row = con.execute("SELECT execution_id FROM execution_records LIMIT 1").fetchone()
    con.close()
    return row[0]


def test_recovery_consumer_is_production_composed_attach(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "comp.sqlite")
    live = {"pid": 4242, "created_epoch_ms": 1788490277831,
            "executable": EXEC, "parent_pid": 100}
    runner = _runner_with_observer(tmp_path, observer=LiveObserver(live), store=store)
    result = runner.run(operation_ref=None)
    assert result.exit_code == 0
    kind = runner._adapter.recover(_exec_id(store))
    assert kind is ZCodeChildRecoveryKind.ATTACH  # durable evidence + live child


def test_recovery_consumer_production_composed_pid_reuse(tmp_path):
    store = SQLiteExecutionStore(tmp_path / "comp2.sqlite")
    reused = {"pid": 4242, "created_epoch_ms": 9999999999999,
              "executable": EXEC, "parent_pid": 100}
    runner = _runner_with_observer(tmp_path, observer=LiveObserver(reused), store=store)
    runner.run(operation_ref=None)
    assert runner._adapter.recover(_exec_id(store)) is ZCodeChildRecoveryKind.RECOVERY_REQUIRED


def test_assembly_executes_every_declared_gate():
    """Truth audit: the assembly call graph runs each gate (source proof).

    WO-P1-226: both entrypoints (mutation + READ_ONLY review) delegate to
    the shared ``_assemble_zcode_execution_impl`` which executes every
    declared gate; neither entrypoint may bypass it."""
    import inspect
    from a_conductor import zcode_production_assembly as module
    source = inspect.getsource(module._assemble_zcode_execution_impl)
    module_source = inspect.getsource(module)
    for entry in (module.assemble_zcode_execution, module.assemble_zcode_review_execution):
        entry_source = inspect.getsource(entry)
        assert "_assemble_zcode_execution_impl(" in entry_source, entry.__name__
    for gate, where in (
        ("verify_execution_context(", source),        # git/worktree gate executed
        ("ZCODE_PROVIDER_GENERATION_DRIFT", source),  # generation CAS gate
        ("ZCODE_STRATEGY_MISMATCH", source),          # strategy gate
        ("ZCODE_RUNTIME_BINDING_MISSING", module_source),  # binding gate (helper)
        ("ZCODE_LEASE_ADMISSION_MISSING", source),   # lease evidence consume
        ("ZCODE_PROVIDER_ADMISSION_MISSING", source), # admission evidence consume
        ("from_task_packet_file(", source),           # verified packet intake
    ):
        assert gate in where, gate


def test_no_dead_helper_builders_or_bypass_paths():
    import inspect
    from a_conductor import supervised_execution as se
    from a_conductor import zcode_runner as zr
    launch_source = inspect.getsource(se.SupervisedExecutionService.launch)
    assert "_build_zcode_helper_spec" in launch_source  # dispatch is LIVE
    assert "_build_owned_spec" in launch_source          # generic unchanged
    runner_source = inspect.getsource(zr)
    assert "reconcile_zcode_child" in runner_source     # recovery consumed
    assert "open_transport" in runner_source             # transport only via factory
    # adapter never spawns outside the factory seam
    adapter_source = inspect.getsource(zr.ZCodeBackendAdapter)
    for banned in ("Popen(", "subprocess.run", "taskkill", ".kill(", ".terminate()"):
        assert banned not in adapter_source, banned
