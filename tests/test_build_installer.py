"""Installer build: payload assembly, setup naming, notices, version sync."""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

from a_conductor.branding import APP_NAME, APP_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_build_installer():
    spec = importlib.util.spec_from_file_location(
        "build_installer", REPO_ROOT / "scripts" / "build_installer.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def build_installer():
    return _load_build_installer()


def test_pyproject_version_matches_branding() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == APP_VERSION


def test_third_party_notices_exists_and_credits_serena() -> None:
    notices = REPO_ROOT / "THIRD-PARTY-NOTICES.md"
    assert notices.is_file()
    content = notices.read_text(encoding="utf-8")
    assert "Serena" in content
    assert "oraios/serena" in content
    assert "MIT License" in content
    assert "Permission is hereby granted" in content  # full MIT text, not a link


def test_setup_exe_name_derives_from_display_name(build_installer) -> None:
    assert build_installer.setup_exe_name() == "A-Sunday-Conductor-Setup"


def test_assemble_payload_copies_everything(build_installer, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"{APP_NAME}.exe").write_bytes(b"FAKE-EXE")
    payload = tmp_path / "payload"

    build_installer.assemble_payload(root=REPO_ROOT, dist_dir=dist, payload_dir=payload)

    assert (payload / f"{APP_NAME}.exe").read_bytes() == b"FAKE-EXE"
    assert (payload / "docs" / "USER-GUIDE.md").is_file()
    assert (payload / "THIRD-PARTY-NOTICES.md").is_file()
    assert (payload / "assets" / "a-conductor.ico").is_file()


def test_assemble_payload_fails_clearly_without_portable_exe(
    build_installer, tmp_path: Path, capsys
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_installer.assemble_payload(
            root=REPO_ROOT, dist_dir=tmp_path, payload_dir=tmp_path / "payload"
        )
    assert "build_portable" in str(excinfo.value) or "build_portable" in capsys.readouterr().out


def test_pyinstaller_args_carry_setup_name_and_payload(build_installer, tmp_path: Path) -> None:
    args = build_installer.pyinstaller_args(
        root=REPO_ROOT, payload_dir=tmp_path / "payload", dist_dir=tmp_path / "dist"
    )
    name_index = args.index("--name")
    assert args[name_index + 1] == "A-Sunday-Conductor-Setup"
    data_index = next(i for i, a in enumerate(args) if str(a).startswith("payload;") or str(a).endswith(";payload"))
    assert str(args[data_index]).startswith(str(tmp_path / "payload"))
    assert args[-1].endswith("installer_main.py")


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main", REPO_ROOT / "scripts" / "installer_main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_main_hardens_pe_steps_before_running_pyinstaller(build_installer, tmp_path: Path) -> None:
    events: list[str] = []

    def fake_harden() -> None:
        events.append("harden")

    def fake_run(args) -> None:
        events.append("run")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"{APP_NAME}.exe").write_bytes(b"FAKE-EXE")

    code = build_installer.main(
        [],
        pyinstaller_run=fake_run,
        harden=fake_harden,
        dist_dir=dist,
        payload_dir=tmp_path / "payload",
    )

    assert code == 0
    assert events == ["harden", "run"]


def test_installer_install_files_copies_notices(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()

    source = tmp_path / "payload"
    source.mkdir()
    (source / f"{APP_NAME}.exe").write_bytes(b"EXE")
    (source / "docs").mkdir()
    (source / "docs" / "USER-GUIDE.md").write_text("guide", encoding="utf-8")
    (source / "assets").mkdir()
    (source / "assets" / "a-conductor.ico").write_bytes(b"ICO")
    (source / "THIRD-PARTY-NOTICES.md").write_text("notices", encoding="utf-8")
    monkeypatch.setattr(module, "payload_dir", lambda: source)

    target = tmp_path / "target"
    target.mkdir()
    uninstaller = module._install_files(source, target)

    assert (target / f"{APP_NAME}.exe").is_file()
    assert (target / "docs" / "USER-GUIDE.md").is_file()
    assert (target / "assets" / "a-conductor.ico").is_file()
    assert (target / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8") == "notices"
    assert uninstaller.is_file()
