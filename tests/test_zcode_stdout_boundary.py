"""WO193: actual helper main, synthetic completed turn, real text wrappers."""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from a_conductor import zcode_protocol, zcode_supervised_helper as helper
from tests.test_zcode_helper_execution import _runtime_metadata_env


def _invoke(monkeypatch, tmp_path, response, output):
    packet = tmp_path / "task.md"
    packet.write_bytes(b"Synthetic task only")
    env = _runtime_metadata_env()
    env.update({
        "ZCODE_TASK_PACKET_PATH": str(packet),
        "ZCODE_TASK_PACKET_TRUSTED_ROOT": str(tmp_path),
        "ZCODE_TASK_PACKET_SHA256": hashlib.sha256(packet.read_bytes()).hexdigest(),
    })
    calls = []
    child = SimpleNamespace(pid=1234, stdin=io.StringIO(), stdout=io.StringIO(),
                            stderr=io.StringIO(), wait=lambda **kw: 0, poll=lambda: 0)
    def spawn(*args, **kwargs):
        calls.append("spawn")
        return child
    def run_turn(*args, **kwargs):
        calls.append("turn")
        return SimpleNamespace(response_text=response,
            bytes_received=len(response.encode("utf-8")), session_id="synthetic-session")
    with monkeypatch.context() as m:
        for key, value in env.items():
            m.setenv(key, value)
        m.setattr(subprocess, "Popen", spawn)
        m.setattr(helper, "_build_child_environment", lambda metadata: {})
        m.setattr(helper, "observe_child_process", lambda pid: {
            "parent_pid": os.getpid(), "created_epoch_ms": 1000, "executable": "synthetic"})
        m.setattr(zcode_protocol.ZCodeProtocolDriver, "run_turn", run_turn)
        m.setattr(sys, "stdout", output)
        rc = helper.main(["--execution-id", "exec-0123456789abcdef",
            "--pid-path", str(tmp_path / "child.pid"),
            "--result-path", str(tmp_path / "result.json"),
            "--report-path", str(tmp_path / "report.json"),
            "--cwd", str(tmp_path), "--", "synthetic", "fake.py",
            "app-server", "--stdio", "--surface", "desktop"])
    report = json.loads((tmp_path / "report.json").read_bytes())
    result = json.loads((tmp_path / "result.json").read_bytes())
    assert calls == ["spawn", "turn"]
    assert result["exit_code"] == 0  # child truth; helper delivery is separate
    return rc, report


@pytest.mark.parametrize("encoding,newline,response", [
    ("cp874", None, "ไทย 漢字 😀"),
    ("utf-8", "\r\n", "first\nsecond\r\nthird\r"),
])
def test_main_stdout_matches_report_under_host_text_translation(
        monkeypatch, tmp_path, encoding, newline, response):
    raw = io.BytesIO()
    output = io.TextIOWrapper(raw, encoding=encoding, newline=newline)
    try:
        rc, report = _invoke(monkeypatch, tmp_path, response, output)
        captured = raw.getvalue()
        assert rc == 0
        assert captured == response.encode("utf-8")
        assert len(captured) == report["response_bytes"]
        assert hashlib.sha256(captured).hexdigest() == report["response_sha256"]
    finally:
        output.close()
