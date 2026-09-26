from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from a_conductor.sunday_remote_bridge import (
    SunDayRemoteBridge,
    SunDayRemoteBridgeError,
    build_http_server,
)
from a_conductor.sunday_remote_protocol import sign_request
from a_conductor.sunday_runtime import RuntimeLaneBinding, SunDayRuntime


SECRET = b"r" * 32
NOW = 1_789_617_600_000


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        shell=False,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _runtime(tmp_path: Path, *, mutation_allowed: bool = False) -> SunDayRuntime:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "bridge-test@example.invalid")
    _git(repo, "config", "user.name", "Bridge Test")
    (repo / "seed.txt").write_text("bridge-needle\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-m", "seed")
    worktree = tmp_path / "lane"
    _git(repo, "worktree", "add", "-b", "bridge-lane", str(worktree))
    head = _git(worktree, "rev-parse", "HEAD")
    return SunDayRuntime(
        RuntimeLaneBinding(
            repo_root=repo,
            worktree_root=worktree,
            branch="bridge-lane",
            head=head,
            claim_id="issue:333",
        ),
        mutation_allowed=mutation_allowed,
    )


def _signed(operation: str, payload: dict[str, object], *, request_id: str, nonce: str) -> bytes:
    return sign_request(
        secret=SECRET,
        operation=operation,
        payload=payload,
        request_id=request_id,
        nonce=nonce,
        issued_at_ms=NOW,
    ).to_json_bytes()


def _decoded(body: bytes) -> dict[str, object]:
    return json.loads(body.decode("utf-8"))


def test_bridge_dispatches_typed_read(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)

    response = bridge.handle(
        _signed("fs.read", {"path": "seed.txt"}, request_id="read-1", nonce="read-nonce-1")
    )

    payload = _decoded(response.body)
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["request_id"] == "read-1"
    assert payload["result"]["content"].splitlines() == ["bridge-needle"]


def test_bridge_rejects_unknown_operation(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)

    response = bridge.handle(
        _signed("shell.raw", {"command": "whoami"}, request_id="raw-1", nonce="raw-nonce-1")
    )

    assert response.status_code == 403
    assert _decoded(response.body) == {"error": "OPERATION_NOT_ALLOWED", "ok": False}


def test_bridge_does_not_mint_mutation_authority(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path, mutation_allowed=False), shared_secret=SECRET, clock_ms=lambda: NOW)

    response = bridge.handle(
        _signed(
            "fs.create",
            {"path": "created.txt", "content": "nope"},
            request_id="create-1",
            nonce="create-nonce-1",
        )
    )

    assert response.status_code == 409
    assert _decoded(response.body) == {"error": "MUTATION_FORBIDDEN", "ok": False}


def test_bridge_rejects_replayed_request(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)
    body = _signed("context.verify", {}, request_id="ctx-1", nonce="ctx-nonce-1")

    first = bridge.handle(body)
    second = bridge.handle(body)

    assert first.status_code == 200
    assert second.status_code == 409
    assert _decoded(second.body) == {"error": "REPLAY_DETECTED", "ok": False}


def test_bridge_rejects_bad_signature(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)
    decoded = json.loads(
        _signed("context.verify", {}, request_id="ctx-2", nonce="ctx-nonce-2").decode("utf-8")
    )
    decoded["signature"] = "0" * 64

    response = bridge.handle(json.dumps(decoded).encode("utf-8"))

    assert response.status_code == 401
    assert _decoded(response.body) == {"error": "AUTH_INVALID", "ok": False}


def test_http_server_defaults_to_loopback_and_serves_signed_calls(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)
    server = build_http_server(bridge, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        with urllib.request.urlopen(f"http://{host}:{port}/healthz", timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))
        assert health["ok"] is True
        assert len(health["context_sha256"]) == 64

        request = urllib.request.Request(
            f"http://{host}:{port}/v1/call",
            method="POST",
            data=_signed("fs.list", {"path": "."}, request_id="list-1", nonce="list-nonce-1"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        assert "seed.txt" in {entry["name"] for entry in payload["result"]}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_http_server_refuses_non_loopback_without_explicit_opt_in(tmp_path: Path) -> None:
    bridge = SunDayRemoteBridge(_runtime(tmp_path), shared_secret=SECRET, clock_ms=lambda: NOW)

    with pytest.raises(
        SunDayRemoteBridgeError,
        match="NON_LOOPBACK_BIND_REQUIRES_EXPLICIT_OPT_IN",
    ):
        build_http_server(bridge, host="0.0.0.0", port=0)


def test_bridge_rejects_integer_secret_instead_of_coercing_zero_bytes(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="shared_secret"):
        SunDayRemoteBridge(_runtime(tmp_path), shared_secret=32)  # type: ignore[arg-type]


def test_bridge_serializes_remote_mutations(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, mutation_allowed=True)
    guard = threading.Lock()
    state = {"active": 0, "max_active": 0}

    def fake_write(path, content, *, expected_sha256=None):
        with guard:
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
        time.sleep(0.05)
        with guard:
            state["active"] -= 1
        return {"path": str(path), "content": content, "expected": expected_sha256}

    runtime.write_text = fake_write  # type: ignore[method-assign]
    bridge = SunDayRemoteBridge(runtime, shared_secret=SECRET, clock_ms=lambda: NOW)
    bodies = [
        _signed("fs.write", {"path": "seed.txt", "content": f"value-{index}"}, request_id=f"write-{index}", nonce=f"write-nonce-{index}")
        for index in range(2)
    ]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(bridge.handle, bodies))

    assert [response.status_code for response in responses] == [200, 200]
    assert state["max_active"] == 1
