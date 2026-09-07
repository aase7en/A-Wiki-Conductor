"""WO-P1-158 — AC-RES-002 closed helper-kind + report_ref confinement (RED).

SupervisedExecutionService must gain a CLOSED helper-kind contract:
GENERIC_NATIVE (existing supervised_child.py behavior, byte-identical) and
ZCODE_APP_SERVER_V1 (repository-owned specialized helper), with no arbitrary
helper path injectable, unknown kinds rejected, and report_ref — when
configured — resolved through the existing runtime-root confinement and
required to live inside run_dir (traversal/outside => fail closed before
spawn). The generic path with report_ref=None must remain unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.execution_record import (
    ExecutionProcessState,
    TransportState,
    new_execution_record,
)
from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.owned_process import WindowsOwnedProcessController
from a_conductor.supervised_execution import (
    SupervisedExecutionError,
    SupervisedExecutionService,
    SupervisedLaunchPlan,
)
from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from a_conductor.windows_observer import WindowsRuntimeObserver


def _record(tmp_path: Path, *, report_ref=None, run_rel="runs/exec-0123456789abcdef"):
    return new_execution_record(
        execution_id="exec-0123456789abcdef",
        job_id="job-1",
        work_order_ref="WO-P1-158",
        project_id="p1",
        worker_id="w1",
        backend_id="zcode-app-server",
        agent_ref="agent:zcode-app-server",
        repo_root=str(tmp_path),
        branch="main",
        head_before="h" * 40,
        operation_ref="zcode:test",
        command_fingerprint="f" * 64,
        command_summary="zcode",
        runtime_profile_ref="rt:zcode",
        run_dir_ref=run_rel,
        stdout_ref=f"{run_rel}/stdout.log",
        stderr_ref=f"{run_rel}/stderr.log",
        result_ref=f"{run_rel}/result.json",
        report_ref=report_ref,
        transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.QUEUED,
    )


def _plan(tmp_path: Path, record):
    return SupervisedLaunchPlan(
        record=record,
        runtime_root=tmp_path,
        target_argv=("ZCode.exe", "zcode.cjs", "app-server", "--stdio",
                     "--surface", "desktop"),
        target_executable_name="ZCode.exe",
    )


def _kinds(values):
    from a_conductor.supervised_execution import SupervisedHelperKind
    return {SupervisedHelperKind(v) for v in values}


def _service(tmp_path: Path, *, helper_kinds=None):
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(),
        http_probe=LoopbackReadyzHttpProbe(),
    )
    controller = WindowsOwnedProcessController(observer=observer)
    allowed = ("ZCode.exe",)
    if helper_kinds is not None:
        return SupervisedExecutionService(
            store=SQLiteExecutionStore(tmp_path / "control.sqlite"),
            controller=controller,
            observer=observer,
            allowed_target_executables=allowed,
            helper_kinds=_kinds(helper_kinds),
        )
    return SupervisedExecutionService(
        store=SQLiteExecutionStore(tmp_path / "control.sqlite"),
        controller=controller,
        observer=observer,
        allowed_target_executables=allowed,
    )


def _validate(tmp_path: Path, *, report_ref=None, helper_kinds=None):
    service = _service(tmp_path, helper_kinds=helper_kinds)
    record = _record(tmp_path, report_ref=report_ref)
    return service._validate_plan_with_report(_plan(tmp_path, record))


# 1. generic helper selection reproduces existing behavior exactly
def test_generic_helper_kind_keeps_existing_validate_paths(tmp_path):
    run_dir, stdout, stderr, result, report, sup_pid, child_pid = _validate(tmp_path)
    assert run_dir.name == "exec-0123456789abcdef"
    assert stdout.name == "stdout.log" and stderr.name == "stderr.log"
    assert result.name == "result.json"
    assert report is None  # generic record has no report_ref
    assert sup_pid.name == "supervisor.pid" and child_pid.name == "child.pid"


# 2. ZCODE kind selects only the repository-owned specialized helper
def test_zcode_helper_kind_maps_to_fixed_repository_helper(tmp_path):
    service = _service(tmp_path, helper_kinds={"ZCODE_APP_SERVER_V1"})
    helper = service.helper_path_for("ZCODE_APP_SERVER_V1")
    assert helper.name == "zcode_supervised_helper.py"
    from a_conductor import supervised_execution as module
    assert helper.parent == Path(module.__file__).parent  # repository-owned
    import inspect
    source = inspect.getsource(module)
    assert "zcode_supervised_helper.py" in source  # fixed mapping in-module


# 3. arbitrary helper path cannot be injected
def test_arbitrary_helper_path_cannot_be_injected(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(ValueError):
        service.helper_path_for("GENERIC_NATIVE", helper_path="C:/evil/evil.py")
    with pytest.raises(ValueError):
        # caller-shaped kinds do not exist in the closed enum
        service.helper_path_for("ATTACKER_KIND")


# 4. unknown helper kind rejected
def test_unknown_helper_kind_rejected(tmp_path):
    service = _service(tmp_path)
    with pytest.raises(ValueError):
        service.helper_path_for("NOT_A_KIND")


# 5. report_ref inside run_dir accepted
def test_report_ref_inside_run_dir_accepted(tmp_path):
    run_dir, _, _, _, report, _, _ = _validate(
        tmp_path, report_ref="runs/exec-0123456789abcdef/report.json"
    )
    assert report is not None
    assert report.name == "report.json"
    assert report.parent == run_dir


# 6. report_ref traversal rejected
def test_report_ref_traversal_rejected(tmp_path):
    with pytest.raises(SupervisedExecutionError):
        _validate(
            tmp_path,
            report_ref="runs/exec-0123456789abcdef/../../outside/report.json",
        )


# 7. absolute outside ref rejected
def test_report_ref_absolute_outside_rejected(tmp_path):
    with pytest.raises(SupervisedExecutionError):
        _validate(tmp_path, report_ref="C:/Windows/evil-report.json")


# 8. ZCode prompt absent from supervisor argv (helper builds command)
def test_zcode_prompt_never_in_supervisor_argv(tmp_path):
    service = _service(tmp_path, helper_kinds={"ZCODE_APP_SERVER_V1"})
    record = _record(tmp_path)
    plan = _plan(tmp_path, record)
    spec = service._build_zcode_helper_spec(plan, "ZCODE_APP_SERVER_V1")
    dump = repr(spec) + str(getattr(spec, "__dict__", {}))
    assert "ZRA1-OK" not in dump  # prompt content never rides the command


# 9. generic fingerprints/results unchanged (validate is the generic seam)
def test_generic_validate_unchanged_for_generic_records(tmp_path):
    # a generic record (report_ref=None) validates identically with and
    # without helper-kind configuration
    a = _validate(tmp_path)
    b = _validate(tmp_path, helper_kinds={"ZCODE_APP_SERVER_V1"})
    assert a == b


# 10. specialized launch still routes through the canonical lifecycle
def test_helper_kind_does_not_bypass_canonical_launch(tmp_path):
    # the kind only selects WHICH repository-owned helper builds the owned
    # process spec; launch/inspect/collect/version-CAS remain the single
    # authority in this service.
    from a_conductor import supervised_execution as module
    import inspect
    source = inspect.getsource(module.SupervisedExecutionService.launch)
    assert "self._store.create" in source
    assert "self._controller.start" in source
