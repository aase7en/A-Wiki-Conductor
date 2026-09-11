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
    assert calls == ["spawn", "turn"]
    if rc:
        # A collector must not see completion authority for missing/partial bytes.
        assert not (tmp_path / "result.json").exists()
        assert not (tmp_path / "report.json").exists()
        return rc, None
    report = json.loads((tmp_path / "report.json").read_bytes())
    result = json.loads((tmp_path / "result.json").read_bytes())
    assert result["exit_code"] == 0
    return rc, report


@pytest.mark.parametrize("encoding,newline,response", [
    ("cp874", None, "ไทย 漢字 😀"),
    ("ascii", None, ""),
    ("ascii", None, "plain ASCII"),
    ("cp1252", "\r\n", "\ufeffe\u0301\x00\r\nไทย\n😀"),
    ("ascii", "\r\n", "😀" * 16384),
    ("utf-8", "\r\n", "first\nsecond\r\nthird\r"),
], ids=["cp874-unicode", "empty", "ascii", "composition-controls", "byte-budget", "mixed-newlines"])
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


class _FaultyBinary(io.BytesIO):
    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self.writes = 0

    def write(self, payload):
        self.writes += 1
        if self.mode == "broken":
            raise BrokenPipeError("synthetic response must not appear in diagnostics")
        if self.mode == "short":
            super().write(payload[:2])
            return 2
        if self.mode == "none":
            return None
        return super().write(payload)

    def flush(self):
        if self.mode == "flush":
            raise OSError("synthetic response must not appear in diagnostics")
        return super().flush()


@pytest.mark.parametrize("mode", ["broken", "short", "none", "flush", "no-buffer"])
def test_main_delivery_failure_is_typed_without_provider_replay(
        monkeypatch, tmp_path, capsys, mode):
    raw = _FaultyBinary(mode)
    output = io.StringIO() if mode == "no-buffer" else SimpleNamespace(buffer=raw)
    rc, report = _invoke(monkeypatch, tmp_path, "synthetic response", output)
    assert rc == 1
    code = "RESPONSE_OUTPUT_INCOMPLETE" if mode in {"short", "none"} else "RESPONSE_OUTPUT_FAILED"
    assert capsys.readouterr().err == f"ZCODE_HELPER_EXIT code={code}\n"
    assert raw.writes == (0 if mode == "no-buffer" else 1)
    assert report is None
    if mode == "short":
        assert raw.getvalue() == b"sy"


@pytest.mark.parametrize("encoding", ["ascii", "cp874", "utf-8"])
def test_real_helper_process_preserves_raw_stdout(monkeypatch, tmp_path, encoding):
    """Real helper + synthetic child processes; runs on macOS and Windows."""
    from pathlib import Path
    from tests import test_zcode_real_helper_e2e as e2e

    response = "ไทย 漢字 😀\nLF\r\nCRLF\rCR\ufeffe\u0301"
    script_text = e2e.FAKE_APP_SERVER.replace(
        json.dumps(e2e.RESPONSE_TEXT), json.dumps(response))
    assert script_text != e2e.FAKE_APP_SERVER
    monkeypatch.setattr(e2e, "FAKE_APP_SERVER", script_text)
    fake = e2e._write_fake_app_server(tmp_path / "fake", tmp_path / "receipts", "ok")
    packet = e2e._packet(tmp_path)
    env = {k: os.environ[k] for k in ("PATH", "SystemRoot", "SYSTEMROOT", "TEMP", "TMP")
           if k in os.environ}
    env.update(_runtime_metadata_env())
    env.update({"ZCODE_TASK_PACKET_PATH": packet.path,
        "ZCODE_TASK_PACKET_TRUSTED_ROOT": str(tmp_path),
        "ZCODE_TASK_PACKET_SHA256": packet.sha256,
        "PYTHONIOENCODING": encoding})
    executable = getattr(sys, "_base_executable", sys.executable)
    result = subprocess.run([executable, str(Path(helper.__file__).resolve()),
        "--execution-id", "exec-0123456789abcdef", "--pid-path", str(tmp_path / "child.pid"),
        "--result-path", str(tmp_path / "result.json"),
        "--report-path", str(tmp_path / "report.json"),
        "--cwd", str(tmp_path), "--", executable, str(fake),
        "app-server", "--stdio", "--surface", "desktop"],
        env=env, capture_output=True, timeout=45)
    assert result.returncode == 0, result.stderr
    assert result.stdout == response.encode("utf-8")
    report = json.loads((tmp_path / "report.json").read_bytes())
    assert report["response_bytes"] == len(result.stdout)
    assert report["response_sha256"] == hashlib.sha256(result.stdout).hexdigest()
    assert len((tmp_path / "receipts" / "spawn.pid").read_text().splitlines()) == 1


def test_result_publication_waits_for_output_flush(monkeypatch, tmp_path):
    class PublicationProbe(io.BytesIO):
        def write(self, payload):
            assert not (tmp_path / "report.json").exists()
            assert not (tmp_path / "result.json").exists()
            return super().write(payload)

        def flush(self):
            assert not (tmp_path / "report.json").exists()
            assert not (tmp_path / "result.json").exists()
            return super().flush()

    raw = PublicationProbe()
    rc, report = _invoke(monkeypatch, tmp_path, "flushed first", SimpleNamespace(buffer=raw))
    assert rc == 0
    assert report["response_sha256"] == hashlib.sha256(raw.getvalue()).hexdigest()
