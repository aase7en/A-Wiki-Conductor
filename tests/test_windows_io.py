import subprocess
from urllib.error import HTTPError, URLError

import pytest

from a_conductor.runtime_safety import PortBindingState, ProcessOwnership, classify_process_ownership
from a_conductor.windows_io import (
    LoopbackReadyzHttpProbe,
    StrictPowerShellInspectionRunner,
)
from a_conductor.windows_observer import (
    HealthProbeObservation,
    HealthProbeState,
    WindowsRuntimeObserver,
)


class NeverHttpProbe:
    def get(self, url: str, timeout_seconds: int) -> HealthProbeObservation:
        raise AssertionError("HTTP probe should not be used in this test")


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_process_inspection_query_executes_with_shell_disabled(monkeypatch) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"ProcessId":1234,"Name":"runtime.exe","ExecutablePath":null,"CommandLine":"runtime.exe worker-01.yaml"}',
            stderr="",
        )

    monkeypatch.setattr("a_conductor.windows_io.subprocess.run", fake_run)
    runner = StrictPowerShellInspectionRunner()
    observer = WindowsRuntimeObserver(runner=runner, http_probe=NeverHttpProbe())

    process = observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )

    assert classify_process_ownership(process) is ProcessOwnership.OWNED
    argv, kwargs = calls[0]
    assert argv[0].lower().endswith("powershell.exe")
    assert kwargs["shell"] is False
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] == 5
    assert kwargs["encoding"] == "utf-8"
    assert "Get-CimInstance Win32_Process" in argv[-1]


def test_port_inspection_query_is_allowlisted(monkeypatch) -> None:
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout='{"LocalAddress":"127.0.0.1","LocalPort":18011,"OwningProcess":1234}',
            stderr="",
        )

    monkeypatch.setattr("a_conductor.windows_io.subprocess.run", fake_run)
    runner = StrictPowerShellInspectionRunner()
    observer = WindowsRuntimeObserver(runner=runner, http_probe=NeverHttpProbe())

    state = observer.observe_port_binding(port=18011, expected_pid=1234)

    assert state is PortBindingState.OWNED
    assert "Get-NetTCPConnection" in calls[0][0][-1]


@pytest.mark.parametrize(
    "script",
    [
        "Stop-Process -Id 1234",
        "Start-Process notepad.exe",
        "Remove-Item C:/important.txt",
        "Get-Process",
        "Write-Output hello",
    ],
)
def test_arbitrary_or_mutating_powershell_is_rejected_before_execution(
    monkeypatch,
    script: str,
) -> None:
    called = False

    def fake_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess must not be reached")

    monkeypatch.setattr("a_conductor.windows_io.subprocess.run", fake_run)
    runner = StrictPowerShellInspectionRunner()

    with pytest.raises(ValueError, match="inspection command is not allowlisted"):
        runner.run(
            (
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ),
            5,
        )

    assert called is False


def test_unexpected_powershell_argv_shape_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        "a_conductor.windows_io.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    runner = StrictPowerShellInspectionRunner()

    with pytest.raises(ValueError, match="PowerShell invocation is not allowlisted"):
        runner.run(("cmd.exe", "/c", "dir"), 5)


def test_runner_timeout_returns_safe_result_without_command_echo(monkeypatch) -> None:
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])

    monkeypatch.setattr("a_conductor.windows_io.subprocess.run", fake_run)
    runner = StrictPowerShellInspectionRunner()
    observer = WindowsRuntimeObserver(runner=runner, http_probe=NeverHttpProbe())

    process = observer.observe_process(
        pid=1234,
        expected_executable_name="runtime.exe",
        expected_profile_marker="worker-01.yaml",
    )

    assert process.process_exists is None


def test_readyz_probe_accepts_only_loopback_http_and_returns_ready(monkeypatch) -> None:
    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse(200)

    monkeypatch.setattr("a_conductor.windows_io.urlopen", fake_urlopen)
    probe = LoopbackReadyzHttpProbe()

    result = probe.get("http://127.0.0.1:18011/readyz", 2)

    assert result.state is HealthProbeState.READY
    assert result.status_code == 200
    assert result.error_code is None
    request, timeout = calls[0]
    assert request.full_url == "http://127.0.0.1:18011/readyz"
    assert timeout == 2


def test_readyz_http_error_is_not_ready_without_body_echo(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise HTTPError(request.full_url, 503, "down", hdrs=None, fp=None)

    monkeypatch.setattr("a_conductor.windows_io.urlopen", fake_urlopen)
    probe = LoopbackReadyzHttpProbe()

    result = probe.get("http://localhost:18011/readyz", 2)

    assert result.state is HealthProbeState.NOT_READY
    assert result.status_code == 503
    assert result.error_code == "HTTP_503"


def test_readyz_transport_error_is_safe_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "a_conductor.windows_io.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(URLError("connection refused secret=abc")),
    )
    probe = LoopbackReadyzHttpProbe()

    result = probe.get("http://127.0.0.1:18011/readyz", 2)

    assert result.state is HealthProbeState.NOT_READY
    assert result.status_code is None
    assert result.error_code == "TRANSPORT_ERROR"
    assert "secret" not in repr(result).lower()


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:18011/readyz",
        "http://example.com:18011/readyz",
        "http://10.0.0.5:18011/readyz",
        "http://user:pass@127.0.0.1:18011/readyz",
        "http://127.0.0.1:18011/other",
        "http://127.0.0.1:18011/readyz?x=1",
        "http://127.0.0.1:18011/readyz#fragment",
    ],
)
def test_readyz_probe_rejects_non_allowlisted_urls_before_network(monkeypatch, url: str) -> None:
    called = False

    def fake_urlopen(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("network must not be reached")

    monkeypatch.setattr("a_conductor.windows_io.urlopen", fake_urlopen)
    probe = LoopbackReadyzHttpProbe()

    with pytest.raises(ValueError, match="readyz URL is not allowlisted"):
        probe.get(url, 2)

    assert called is False


@pytest.mark.parametrize("timeout", [0, -1])
def test_backends_reject_non_positive_timeout_before_io(monkeypatch, timeout: int) -> None:
    monkeypatch.setattr(
        "a_conductor.windows_io.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )
    probe = LoopbackReadyzHttpProbe()

    with pytest.raises(ValueError, match="timeout_seconds must be >= 1"):
        probe.get("http://127.0.0.1:18011/readyz", timeout)
