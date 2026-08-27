from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main_target_ownership",
        REPO_ROOT / "scripts" / "installer_main.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_nonempty_unknown_install_target_fails_before_install(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    target = tmp_path / "existing"
    target.mkdir()
    sentinel = target / "user-file.txt"
    sentinel.write_text("keep-me", encoding="utf-8")
    called: list[Path] = []
    monkeypatch.setattr(module, "do_install", lambda value: called.append(value) or 0)

    code = module.main(["--target", str(target)])

    assert code == 5
    assert called == []
    assert sentinel.read_text(encoding="utf-8") == "keep-me"
    assert "INSTALL_TARGET_NOT_MANAGED" in capsys.readouterr().out


def test_empty_install_target_is_allowed(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "empty"
    target.mkdir()
    called: list[Path] = []
    monkeypatch.setattr(module, "do_install", lambda value: called.append(value) or 0)

    assert module.main(["--target", str(target)]) == 0
    assert called == [target]


def test_valid_marker_allows_reinstall(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "managed"
    target.mkdir()
    (target / "existing.txt").write_text("old", encoding="utf-8")
    module._write_install_marker(target)
    called: list[Path] = []
    monkeypatch.setattr(module, "do_install", lambda value: called.append(value) or 0)

    assert module.main(["--target", str(target)]) == 0
    assert called == [target]


def test_corrupt_marker_does_not_authorize_nonempty_install_target(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "corrupt"
    target.mkdir()
    (target / module.INSTALL_MARKER_NAME).write_text("not-json", encoding="utf-8")
    (target / "user.txt").write_text("keep", encoding="utf-8")
    called: list[Path] = []
    monkeypatch.setattr(module, "do_install", lambda value: called.append(value) or 0)

    assert module.main(["--target", str(target)]) == 5
    assert called == []


def test_unmanaged_nonempty_uninstall_fails_before_cleanup(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    target = tmp_path / "foreign"
    target.mkdir()
    sentinel = target / "user.txt"
    sentinel.write_text("keep", encoding="utf-8")
    monkeypatch.setattr(module.sys, "frozen", False, raising=False)
    called: list[Path] = []
    monkeypatch.setattr(module, "do_uninstall", lambda value: called.append(value) or 0)

    code = module.main(["--uninstall", "--target", str(target)])

    assert code == 5
    assert called == []
    assert sentinel.exists()
    assert "UNINSTALL_TARGET_NOT_MANAGED" in capsys.readouterr().out


def test_windows_frozen_marker_requires_matching_registry_target(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "managed"
    target.mkdir()
    module._write_install_marker(target)
    (target / "payload.txt").write_text("owned", encoding="utf-8")
    temp_exe = tmp_path / "temp-uninstaller.exe"
    temp_exe.write_bytes(b"EXE")
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(temp_exe))
    monkeypatch.setattr(module, "_windows_registry_install_location", lambda: tmp_path / "other")
    called: list[Path] = []
    monkeypatch.setattr(module, "do_uninstall", lambda value: called.append(value) or 0)

    assert module.main(["--uninstall", "--target", str(target)]) == 5
    assert called == []


def test_windows_frozen_marker_and_matching_registry_allow_uninstall(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "managed"
    target.mkdir()
    module._write_install_marker(target)
    temp_exe = tmp_path / "temp-uninstaller.exe"
    temp_exe.write_bytes(b"EXE")
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(temp_exe))
    monkeypatch.setattr(module, "_windows_registry_install_location", lambda: target)
    called: list[Path] = []
    monkeypatch.setattr(module, "do_uninstall", lambda value: called.append(value) or 0)

    assert module.main(["--uninstall", "--target", str(target)]) == 0
    assert called == [target]


def test_legacy_registry_and_expected_files_allow_upgrade_without_marker(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "legacy"
    target.mkdir()
    (target / f"{module.APP_NAME}.exe").write_bytes(b"APP")
    (target / f"Uninstall-{module.APP_NAME}.exe").write_bytes(b"UNINSTALL")
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module, "_windows_registry_install_location", lambda: target)
    called: list[Path] = []
    monkeypatch.setattr(module, "do_install", lambda value: called.append(value) or 0)

    assert module.main(["--target", str(target)]) == 0
    assert called == [target]


def test_marker_payload_has_bounded_identity_fields(tmp_path: Path) -> None:
    module = _load_installer_main()
    target = tmp_path / "managed"
    target.mkdir()

    module._write_install_marker(target)
    payload = json.loads((target / module.INSTALL_MARKER_NAME).read_text(encoding="utf-8"))

    assert payload == {
        "app_name": module.APP_NAME,
        "format": 1,
    }
