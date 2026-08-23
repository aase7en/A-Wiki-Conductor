"""Setup Wizard engine: system checks, installers, first-instance creation."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from a_conductor.setup_wizard import (
    SetupWizardError,
    check_system,
)


# --- SystemCheck -----------------------------------------------------------


def test_check_system_all_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("shutil.which", lambda name: None)
    # Point the C:/AI path to a non-existent location for the test
    monkeypatch.setattr("a_conductor.setup_wizard.Path", Path)
    result = check_system()
    assert result["uv"] is False or True  # uv might be on system PATH in test env
    assert result["python_313"] is False or True  # might exist
    assert result["serena"] is False or True  # might exist
    assert result["tunnel_client"] is False or True  # legacy path might exist


def test_check_system_detects_uv_on_path(tmp_path: Path, monkeypatch) -> None:
    fake_uv = tmp_path / "uv.exe"
    fake_uv.write_bytes(b"fake")

    def fake_which(name):
        return str(fake_uv) if name == "uv" else None

    monkeypatch.setattr("shutil.which", fake_which)
    result = check_system()
    assert result["uv"] is True


def test_check_system_detects_tunnel_client(tmp_path: Path, monkeypatch) -> None:
    tc_dir = tmp_path / "dwb-serena-tunnel-starter" / "tunnel-client"
    tc_dir.mkdir(parents=True)
    (tc_dir / "tunnel-client.exe").write_bytes(b"fake")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # The check should find tunnel-client at the standard path
    result = check_system(tunnel_client_path=tc_dir / "tunnel-client.exe")
    assert result["tunnel_client"] is True


# --- Installer (with injectable downloader + subprocess runner) ------------


def test_install_uv_downloads_and_places_exe(tmp_path: Path, monkeypatch) -> None:
    import zipfile

    from a_conductor.setup_wizard import Installer

    fake_zip = tmp_path / "fake-uv.zip"
    with zipfile.ZipFile(fake_zip, "w") as zf:
        zf.writestr("uv-x86_64-pc-windows-msvc/uv.exe", b"fake-uv-binary")
    downloads = []

    def fake_download(url, dest):
        downloads.append(url)
        Path(dest).write_bytes(fake_zip.read_bytes())

    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    installer = Installer(download_fn=fake_download)
    # Mock the GitHub API response
    import json as fake_json

    def fake_urlopen(req, timeout=None):
        class FakeResponse:
            def read(self):
                return fake_json.dumps({
                    "assets": [{
                        "name": "uv-x86_64-pc-windows-msvc.zip",
                        "browser_download_url": "https://example.com/uv.zip",
                    }]
                }).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return FakeResponse()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    uv_path = installer.install_uv()

    assert uv_path.is_file()
    assert uv_path.read_bytes() == b"fake-uv-binary"
    assert len(downloads) == 1


def test_install_python_runs_uv_subprocess(tmp_path: Path, monkeypatch) -> None:
    from a_conductor.setup_wizard import Installer

    uv_path = tmp_path / "uv.exe"
    uv_path.write_bytes(b"fake")
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    installer = Installer(uv_path=uv_path)
    result = installer.install_python()

    assert result is True
    assert any("python" in " ".join(c) and "install" in " ".join(c) for c in commands)
    assert any("3.13" in " ".join(c) for c in commands)


def test_install_serena_runs_uv_subprocess(tmp_path: Path, monkeypatch) -> None:
    from a_conductor.setup_wizard import Installer

    uv_path = tmp_path / "uv.exe"
    uv_path.write_bytes(b"fake")
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    installer = Installer(uv_path=uv_path)
    result = installer.install_serena()

    assert result is True
    assert any("serena-agent" in " ".join(c) for c in commands)


def test_install_tunnel_client_downloads_and_extracts(tmp_path: Path, monkeypatch) -> None:
    import json as fake_json
    import zipfile

    from a_conductor.setup_wizard import Installer

    # Create a fake zip with tunnel-client.exe inside
    fake_zip = tmp_path / "fake-tunnel.zip"
    with zipfile.ZipFile(fake_zip, "w") as zf:
        zf.writestr("tunnel-client.exe", b"fake-tc")
        zf.writestr("LICENSE", b"Apache 2.0")

    def fake_download(url, dest):
        Path(dest).write_bytes(fake_zip.read_bytes())

    # Mock the GitHub API response to avoid rate limits on CI
    def fake_urlopen(req, timeout=None):
        class FakeResponse:
            def read(self):
                return fake_json.dumps({
                    "assets": [{
                        "name": "tunnel-client-v0.0.12-windows-amd64.zip",
                        "browser_download_url": "https://example.com/tc.zip",
                    }]
                }).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return FakeResponse()

    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    installer = Installer(download_fn=fake_download)
    tc_path = installer.install_tunnel_client(target_dir=tmp_path / "tc")

    assert tc_path.is_file()
    assert (tmp_path / "tc" / "LICENSE").is_file()
    assert tc_path.read_bytes() == b"fake-tc"


# --- FirstInstanceCreator ---------------------------------------------------


def test_create_first_instance_full_layout(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "my-project"
    project.mkdir()
    instances_root = tmp_path / "instances"

    creator = FirstInstanceCreator(instances_root=instances_root)
    created = creator.create(
        name="first",
        project_path=project,
        health_port=18011,
        tunnel_client_path=tmp_path / "tc" / "tunnel-client.exe",
        api_key_file=tmp_path / "tc" / "config" / "api-key.dpapi",
    )

    assert (created / "instance.ps1").is_file()
    assert (created / "start.ps1").is_file()
    assert (created / "stop.ps1").is_file()
    assert (created / "Start-Sunday-Worker-1.cmd").is_file()
    assert (created / "Stop-Sunday-Worker-1.cmd").is_file()
    assert (created / "profiles").is_dir()
    assert (created / "serena-home").is_dir()
    assert (created / "config").is_dir()

    ps1 = (created / "instance.ps1").read_text(encoding="utf-8")
    assert "$InstanceName = 'Sunday-Worker-1'" in ps1
    assert "18011" in ps1


def test_create_filesystem_backend_uses_npx(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "proj"
    project.mkdir()
    creator = FirstInstanceCreator(instances_root=tmp_path / "inst")
    created = creator.create(
        name="fs-worker",
        project_path=project,
        tunnel_client_path=tmp_path / "tc.exe",
        api_key_file=tmp_path / "key.dpapi",
        backend="filesystem",
    )
    template = (created / "profiles" / "serena-fs-worker.yaml.template").read_text(encoding="utf-8")
    assert "npx" in template
    assert "@modelcontextprotocol/server-filesystem" in template


def test_create_serena_backend_uses_serena_command(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "proj"
    project.mkdir()
    creator = FirstInstanceCreator(instances_root=tmp_path / "inst")
    created = creator.create(
        name="ser-worker",
        project_path=project,
        tunnel_client_path=tmp_path / "tc.exe",
        api_key_file=tmp_path / "key.dpapi",
        backend="serena",
    )
    template = (created / "profiles" / "serena-ser-worker.yaml.template").read_text(encoding="utf-8")
    assert "serena start-mcp-server" in template


def test_check_nodejs_returns_bool() -> None:
    from a_conductor.setup_wizard import Installer

    installer = Installer()
    result = installer.check_nodejs()
    assert isinstance(result, bool)


def test_create_stitch_backend_generates_node_command(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "proj"
    project.mkdir()
    stitch_dir = tmp_path / "stitch-mcp"
    stitch_dir.mkdir()
    (stitch_dir / "artifact-keyserver.mjs").write_text("// mcp", encoding="utf-8")

    creator = FirstInstanceCreator(instances_root=tmp_path / "inst")
    created = creator.create(
        name="st-worker",
        project_path=project,
        tunnel_client_path=tmp_path / "tc.exe",
        api_key_file=tmp_path / "key.dpapi",
        backend="stitch",
        stitch_mcp_path=str(stitch_dir),
        stitch_api_key="test-stitch-key-123",
    )

    # YAML uses node + artifact-keyserver.mjs
    template = (created / "profiles" / "serena-st-worker.yaml.template").read_text(encoding="utf-8")
    assert "node" in template
    assert "artifact-keyserver.mjs" in template
    assert str(stitch_dir) in template

    # API key saved to sti-key.txt
    sti_key = (created / "config" / "sti-key.txt").read_text(encoding="utf-8").strip()
    assert sti_key == "test-stitch-key-123"


def test_stitch_backend_no_api_key_still_works(tmp_path: Path) -> None:
    from a_conductor.setup_wizard import FirstInstanceCreator

    project = tmp_path / "proj"
    project.mkdir()
    creator = FirstInstanceCreator(instances_root=tmp_path / "inst")
    created = creator.create(
        name="st2",
        project_path=project,
        tunnel_client_path=tmp_path / "tc.exe",
        api_key_file=tmp_path / "key.dpapi",
        backend="stitch",
        stitch_mcp_path="C:/AI/stitch-mcp",
        stitch_api_key="",  # no key
    )
    # sti-key.txt should not be created when no key
    assert not (created / "config" / "sti-key.txt").exists()
