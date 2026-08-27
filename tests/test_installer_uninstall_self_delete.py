from __future__ import annotations

import base64
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main_self_delete",
        REPO_ROOT / "scripts" / "installer_main.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _decode_registered_command(command: str) -> str:
    encoded = command.split("-EncodedCommand", 1)[1].strip().strip('"')
    return base64.b64decode(encoded).decode("utf-16le")


def test_registered_uninstall_command_wraps_frozen_exe_synchronously() -> None:
    module = _load_installer_main()
    target = Path("C:/Users/Test O'Hare/App/A-Sunday Conductor")
    uninstaller = target / "Uninstall-A-Sunday Conductor.exe"
    command = module._registered_uninstall_command(target, uninstaller)

    assert str(target) not in command
    assert str(uninstaller) not in command
    assert "-EncodedCommand" in command
    script = _decode_registered_command(command)
    assert "Copy-Item -LiteralPath $source -Destination $temp -Force" in script
    assert "& $temp --uninstall --target $target" in script
    assert "$rc = $LASTEXITCODE" in script
    assert "Remove-Item -LiteralPath $temp" in script
    assert "for ($i = 0; $i -lt 100; $i++)" in script
    assert "Start-Process" not in script
    assert "O''Hare" in script


def test_registry_uses_registered_wrapper_instead_of_direct_uninstaller(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    uninstaller = target / "Uninstall-A-Sunday Conductor.exe"
    scripts: list[str] = []
    monkeypatch.setattr(module, "_run_ps", scripts.append)
    monkeypatch.setattr(
        module,
        "_registered_uninstall_command",
        lambda _target, _uninstaller: "SAFE_REGISTERED_UNINSTALL",
    )

    module.write_registry(target, uninstaller)

    assert len(scripts) == 1
    assert "SAFE_REGISTERED_UNINSTALL" in scripts[0]
    assert f'"{uninstaller}" --uninstall --target' not in scripts[0]


def test_frozen_in_target_uninstall_fails_before_destructive_cleanup(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    executable = target / "Uninstall-A-Sunday Conductor.exe"
    executable.write_bytes(b"EXE")
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(executable))
    called: list[str] = []
    monkeypatch.setattr(module, "do_uninstall", lambda _target: called.append("cleanup") or 0)

    code = module.main(["--uninstall", "--target", str(target)])

    assert code == 4
    assert called == []
    assert "UNINSTALL_REQUIRES_REGISTERED_COMMAND" in capsys.readouterr().out


def test_frozen_temp_copy_outside_target_can_run_uninstall(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    temp_copy = tmp_path / "temp" / "uninstall.exe"
    temp_copy.parent.mkdir()
    temp_copy.write_bytes(b"EXE")
    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(temp_copy))
    called: list[Path] = []
    monkeypatch.setattr(module, "do_uninstall", lambda value: called.append(value) or 0)

    code = module.main(["--uninstall", "--target", str(target)])

    assert code == 0
    assert called == [target]


def test_source_mode_uninstall_remains_synchronous(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    monkeypatch.setattr(module.sys, "frozen", False, raising=False)
    called: list[Path] = []
    monkeypatch.setattr(module, "do_uninstall", lambda value: called.append(value) or 0)

    assert module.main(["--uninstall", "--target", str(target)]) == 0
    assert called == [target]
