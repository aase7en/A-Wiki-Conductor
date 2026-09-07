"""WO-P1-158 — child.identity.json recovery-consumer matrix (restart tests)."""

from __future__ import annotations

import json

import pytest

from a_conductor.zcode_child_recovery import (
    ZCodeChildRecoveryKind,
    read_child_identity_from_run_dir,
    reconcile_zcode_child,
)
from a_conductor.zcode_supervised_helper import ZCodeChildIdentity

IDENTITY = ZCodeChildIdentity(
    child_pid=4242,
    child_created_epoch_ms=1788490277831,
    executable=r"C:\ZCode\ZCode.exe",
    parent_pid=100,
    target_argv_sha256="a" * 64,
    execution_id="exec-0123456789abcdef",
)

DOCUMENT = json.loads(
    json.dumps(
        {
            "schema": "zcode-child-identity/1",
            "execution_id": IDENTITY.execution_id,
            "child_pid": IDENTITY.child_pid,
            "child_created_epoch_ms": IDENTITY.child_created_epoch_ms,
            "executable": IDENTITY.executable,
            "parent_pid": IDENTITY.parent_pid,
            "target_argv_sha256": IDENTITY.target_argv_sha256,
        },
        sort_keys=True,
    )
)


class Observer:
    def __init__(self, live=None):
        self.live = live

    def observe_child(self, pid):
        return self.live


LIVE_EXACT = {
    "pid": 4242,
    "created_epoch_ms": 1788490277831,
    "executable": r"C:\ZCode\ZCode.exe",
    "parent_pid": 100,
}


# 1. restart + exact identity => attach
def test_restart_exact_identity_attaches():
    decision = reconcile_zcode_child(DOCUMENT, observer=Observer(LIVE_EXACT))
    assert decision.attach and decision.execution_id == "exec-0123456789abcdef"


# 2. PID reused + different creation time => reject
def test_pid_reuse_rejected():
    reused = {**LIVE_EXACT, "created_epoch_ms": 9999999999999}
    decision = reconcile_zcode_child(DOCUMENT, observer=Observer(reused))
    assert decision.kind is ZCodeChildRecoveryKind.RECOVERY_REQUIRED
    assert decision.reason_code == "CHILD_PID_REUSED"


# 3. executable mismatch => reject
def test_executable_mismatch_rejected():
    decision = reconcile_zcode_child(
        DOCUMENT, observer=Observer({**LIVE_EXACT, "executable": "C:/evil.exe"})
    )
    assert decision.reason_code == "CHILD_EXECUTABLE_MISMATCH"


# 4. parent/helper mismatch => reject
def test_parent_mismatch_rejected():
    decision = reconcile_zcode_child(
        DOCUMENT, observer=Observer({**LIVE_EXACT, "parent_pid": 999})
    )
    assert decision.reason_code == "CHILD_PARENT_MISMATCH"


# 5. malformed identity => recovery
def test_malformed_identity_recovery():
    decision = reconcile_zcode_child({"bogus": True}, observer=Observer(LIVE_EXACT))
    assert decision.kind is ZCodeChildRecoveryKind.RECOVERY_REQUIRED
    assert decision.reason_code.startswith("IDENTITY_MALFORMED")


# 6. missing identity with ambiguous execution => recovery
def test_missing_child_pid_gone_recovery():
    decision = reconcile_zcode_child(DOCUMENT, observer=Observer(None))
    assert decision.kind is ZCodeChildRecoveryKind.RECOVERY_REQUIRED
    assert decision.reason_code == "CHILD_PID_GONE"


# 7. helper crash before result => no replay authority exists in this consumer
def test_recovery_consumer_has_no_replay_or_kill_surface():
    import inspect
    from a_conductor import zcode_child_recovery as module
    source = inspect.getsource(module)
    for forbidden in ("taskkill", ".terminate()", ".kill(", "run_task", "dispatch", "Popen"):
        assert forbidden not in source, forbidden


# 8. report present/result absent + live exact child => attach/reconcile
def test_report_present_result_absent_live_child_attaches(tmp_path):
    run_dir = tmp_path / "runs" / "exec-0123456789abcdef"
    run_dir.mkdir(parents=True)
    (run_dir / "child.identity.json").write_text(json.dumps(DOCUMENT), encoding="utf-8")
    (run_dir / "report.json").write_text("{}", encoding="utf-8")  # no result.json
    document = read_child_identity_from_run_dir(run_dir)
    decision = reconcile_zcode_child(document, observer=Observer(LIVE_EXACT))
    assert decision.attach  # reconcile the live child; no fabrication


# 9. UNKNOWN/unreaped => result.json stays absent (consumer never creates it)
def test_consumer_never_fabricates_result(tmp_path):
    run_dir = tmp_path / "runs" / "x"
    run_dir.mkdir(parents=True)
    (run_dir / "child.identity.json").write_text(json.dumps(DOCUMENT), encoding="utf-8")
    reconcile_zcode_child(
        read_child_identity_from_run_dir(run_dir), observer=Observer(None)
    )
    assert not (run_dir / "result.json").exists()


# 10. two recovery invocations idempotent
def test_two_invocations_idempotent():
    first = reconcile_zcode_child(DOCUMENT, observer=Observer(LIVE_EXACT))
    second = reconcile_zcode_child(DOCUMENT, observer=Observer(LIVE_EXACT))
    assert first == second


def test_unreadable_identity_document_recovery(tmp_path):
    run_dir = tmp_path / "runs" / "empty"
    run_dir.mkdir(parents=True)
    document = read_child_identity_from_run_dir(run_dir)  # missing file
    decision = reconcile_zcode_child(document, observer=Observer(LIVE_EXACT))
    assert decision.kind is ZCodeChildRecoveryKind.RECOVERY_REQUIRED
