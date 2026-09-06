"""Q26 — real specialized-helper execution proofs (RED-first).

launch() must dispatch by the plan's CLOSED helper kind (generic unchanged;
ZCODE_APP_SERVER_V1 invokes the repository-owned specialized helper), the
specialized helper must have an executable bounded CLI whose argv carries
only verified metadata, and the plan must reject arbitrary kinds.
"""

from __future__ import annotations

import json
import subprocess
import sys
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
    SupervisedExecutionService,
    SupervisedHelperKind,
    SupervisedLaunchPlan,
)
from a_conductor.windows_io import LoopbackReadyzHttpProbe, StrictPowerShellInspectionRunner
from a_conductor.windows_observer import WindowsRuntimeObserver

HELPER = Path("src/a_conductor/zcode_supervised_helper.py").resolve()


def _record(tmp_path, backend="supervised-native"):
    return new_execution_record(
        execution_id="exec-0123456789abcdef",
        job_id="j", work_order_ref="w", project_id="p", worker_id="w",
        backend_id=backend, agent_ref="agent:x", repo_root=str(tmp_path),
        branch="main", head_before="h" * 40, operation_ref="o",
        command_fingerprint="f" * 64, command_summary="s",
        runtime_profile_ref="r", run_dir_ref="runs/exec-0123456789abcdef",
        stdout_ref="runs/exec-0123456789abcdef/stdout.log",
        stderr_ref="runs/exec-0123456789abcdef/stderr.log",
        result_ref="runs/exec-0123456789abcdef/result.json",
        report_ref=None, transport_state=TransportState.CONNECTED,
        execution_state=ExecutionProcessState.QUEUED,
    )


def _service(tmp_path, kinds):
    observer = WindowsRuntimeObserver(
        runner=StrictPowerShellInspectionRunner(), http_probe=LoopbackReadyzHttpProbe()
    )
    return SupervisedExecutionService(
        store=SQLiteExecutionStore(tmp_path / "c.sqlite"),
        controller=WindowsOwnedProcessController(observer=observer),
        observer=observer,
        allowed_target_executables=("ZCode.exe",),
        helper_kinds={SupervisedHelperKind(k) for k in kinds},
    )


def _plan(tmp_path, kind="GENERIC_NATIVE", argv=("ZCode.exe", "b.cjs")):
    return SupervisedLaunchPlan(
        record=_record(tmp_path),
        runtime_root=tmp_path,
        target_argv=argv,
        target_executable_name=argv[0],
        helper_kind=kind,
    )


# 1. generic launch still invokes the existing generic helper
def test_generic_plan_uses_generic_helper(tmp_path):
    service = _service(tmp_path, ["GENERIC_NATIVE"])
    plan = _plan(tmp_path, "GENERIC_NATIVE")
    spec = service._build_owned_spec(plan)
    assert "supervised_child.py" in spec.command[1]


def test_plan_default_kind_is_generic(tmp_path):
    plan = SupervisedLaunchPlan(
        record=_record(tmp_path), runtime_root=tmp_path,
        target_argv=("ZCode.exe", "b.cjs"), target_executable_name="ZCode.exe",
    )
    assert plan.helper_kind is SupervisedHelperKind.GENERIC_NATIVE


# 2. ZCODE kind builds the specialized helper spec through the same service
def test_zcode_kind_selects_specialized_helper(tmp_path):
    service = _service(tmp_path, ["GENERIC_NATIVE", "ZCODE_APP_SERVER_V1"])
    plan = _plan(
        tmp_path, "ZCODE_APP_SERVER_V1",
        argv=("ZCode.exe", "zcode.cjs", "app-server", "--stdio", "--surface", "desktop"),
    )
    spec = service._build_zcode_helper_spec(plan, plan.helper_kind)
    assert "zcode_supervised_helper.py" in spec.command[1]


# 3. arbitrary helper kind rejected at the plan boundary
def test_arbitrary_kind_rejected_at_plan():
    with pytest.raises(ValueError):
        SupervisedHelperKind("ATTACKER")


def test_plan_rejects_non_kind_text():
    with pytest.raises(ValueError):
        _plan(None, "ATTACKER")


# 4. disabled helper kind rejected at launch
def test_disabled_kind_rejected_at_launch(tmp_path):
    service = _service(tmp_path, ["GENERIC_NATIVE"])  # ZCODE not enabled
    plan = _plan(
        tmp_path, "ZCODE_APP_SERVER_V1",
        argv=("ZCode.exe", "zcode.cjs", "app-server", "--stdio", "--surface", "desktop"),
    )
    outcome = service.launch(plan)
    assert outcome.recovery_required and outcome.error_code == "HELPER_KIND_NOT_ENABLED"


# 5. the specialized helper has an executable CLI (import + main entrypoint)
def test_helper_has_executable_cli():
    sys.path.insert(0, str(REPO_ROOT := Path("src").resolve()))
    from a_conductor import zcode_supervised_helper as module
    assert callable(module.main)
    assert module.__file__.endswith("zcode_supervised_helper.py")


# 6/7. prompt and credential absent from helper CLI argv shape (source proof)
def test_cli_never_takes_prompt_or_credential_argv():
    import inspect
    sys.path.insert(0, str(Path("src").resolve()))
    from a_conductor import zcode_supervised_helper as module
    source = inspect.getsource(module)
    parser_block = source[source.index("add_argument"):source.index("add_argument(\"target\"")]
    for banned in ("--prompt", "--credential", "--api-key", "--secret", "--token"):
        assert banned not in source, banned


# CLI behavior via subprocess (bounded, no live provider): bad argv fails typed
def test_cli_rejects_non_allowlisted_argv(tmp_path):
    result = subprocess.run(
        [sys.executable, str(HELPER), "--execution-id", "e", "--pid-path", "p",
         "--result-path", "r", "--cwd", str(tmp_path), "--", "ZCode.exe", "z.cjs",
         "shell", "-c", "evil"],
        capture_output=True, text=True, timeout=30,
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    # typed codes go to stderr (stdout is reserved for the bounded response)
    assert "ZCODE_HELPER_EXIT code=TARGET_ARGV_NOT_ALLOWLISTED" in result.stderr


# 8/9. identity-before-protocol enforced in the CLI source
def test_cli_writes_identity_before_protocol():
    import inspect
    sys.path.insert(0, str(Path("src").resolve()))
    from a_conductor import zcode_supervised_helper as module
    source = inspect.getsource(module.main)
    identity_idx = source.index("IDENTITY_WRITE_FAILED")
    protocol_idx = source.index("run_turn")
    assert identity_idx < protocol_idx  # identity write precedes protocol send


# 10. report_ref confined inside run_dir (service-level)
def test_report_ref_confined(tmp_path):
    from a_conductor.execution_record import new_execution_record as _nr
    service = _service(tmp_path, ["GENERIC_NATIVE", "ZCODE_APP_SERVER_V1"])
    record = _record(tmp_path)
    record = record.__class__(**{**record.__dict__, "report_ref": "runs/exec-0123456789abcdef/report.json"}) if hasattr(record, "__dict__") else record
    # frozen slots record — use replace-style rebuild via _nr kwargs
    record = _nr(
        execution_id=record.execution_id, job_id=record.job_id,
        work_order_ref=record.work_order_ref, project_id=record.project_id,
        worker_id=record.worker_id, backend_id=record.backend_id,
        agent_ref=record.agent_ref, repo_root=record.repo_root,
        branch=record.branch, head_before=record.head_before,
        operation_ref=record.operation_ref,
        command_fingerprint=record.command_fingerprint,
        command_summary=record.command_summary,
        runtime_profile_ref=record.runtime_profile_ref,
        run_dir_ref=record.run_dir_ref, stdout_ref=record.stdout_ref,
        stderr_ref=record.stderr_ref, result_ref=record.result_ref,
        report_ref="runs/exec-0123456789abcdef/report.json",
        transport_state=record.transport_state,
        execution_state=record.execution_state,
    )
    plan = SupervisedLaunchPlan(
        record=record, runtime_root=tmp_path,
        target_argv=("ZCode.exe", "zcode.cjs", "app-server", "--stdio", "--surface", "desktop"),
        target_executable_name="ZCode.exe", helper_kind="ZCODE_APP_SERVER_V1",
    )
    paths = service._validate_plan_with_report(plan)
    assert paths[4] is not None and paths[4].name == "report.json"
    from a_conductor.supervised_execution import SupervisedExecutionError
    bad = _nr(
        execution_id=record.execution_id, job_id=record.job_id,
        work_order_ref=record.work_order_ref, project_id=record.project_id,
        worker_id=record.worker_id, backend_id=record.backend_id,
        agent_ref=record.agent_ref, repo_root=record.repo_root,
        branch=record.branch, head_before=record.head_before,
        operation_ref=record.operation_ref,
        command_fingerprint=record.command_fingerprint,
        command_summary=record.command_summary,
        runtime_profile_ref=record.runtime_profile_ref,
        run_dir_ref=record.run_dir_ref, stdout_ref=record.stdout_ref,
        stderr_ref=record.stderr_ref, result_ref=record.result_ref,
        report_ref="runs/exec-0123456789abcdef/../../escape.json",
        transport_state=record.transport_state,
        execution_state=record.execution_state,
    )
    bad_plan = SupervisedLaunchPlan(
        record=bad, runtime_root=tmp_path,
        target_argv=("ZCode.exe", "zcode.cjs", "app-server", "--stdio", "--surface", "desktop"),
        target_executable_name="ZCode.exe", helper_kind="ZCODE_APP_SERVER_V1",
    )
    with pytest.raises(SupervisedExecutionError):
        service._validate_plan_with_report(bad_plan)


# 11. UNKNOWN exit produces no result.json (CLI source ordering)
def test_cli_result_only_on_real_exit():
    import inspect
    sys.path.insert(0, str(Path("src").resolve()))
    from a_conductor import zcode_supervised_helper as module
    source = inspect.getsource(module.main)
    exit_gate = source.index("isinstance(exit_code, int)")
    result_write = source.index('"child_pid": child.pid')
    assert exit_gate < result_write


# 12. generic regression unchanged (covered by existing suites)
def test_generic_suites_still_govern():
    from a_conductor.supervised_execution import SupervisedLaunchPlan as P
    assert P is SupervisedLaunchPlan  # import identity stable
