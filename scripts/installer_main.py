"""A-Sunday Conductor per-user installer / uninstaller (no admin required).

Bundled payload (via PyInstaller --add-data):
    payload/A-Sunday Conductor.exe  the portable app
    payload/docs/USER-GUIDE.md  the user guide
    payload/THIRD-PARTY-NOTICES.md  Serena (MIT) attribution
    payload/assets/a-conductor.ico

Install (default):
    A-Sunday-Conductor-Setup.exe [--target DIR]
Uninstall:
    A-Sunday-Conductor-Setup.exe --uninstall [--target DIR]

Writes only inside the per-user profile: target dir (default
%LOCALAPPDATA%\\Programs\\A-Sunday Conductor), Start Menu shortcut, Desktop
shortcut, and an HKCU Add/Remove-Programs entry. No admin, no system paths.
"""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BRANDING_PAYLOAD_NAME = "installer-branding.json"


def _load_branding() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle is None:
            raise SystemExit("INSTALLER_BRANDING_MISSING")
        metadata_path = Path(bundle) / "payload" / BRANDING_PAYLOAD_NAME
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            app_name = metadata["app_name"]
            app_version = metadata["app_version"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SystemExit(f"INSTALLER_BRANDING_INVALID: {exc}") from exc
    else:
        branding_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "a_conductor"
            / "branding.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_a_conductor_installer_branding", branding_path
        )
        if spec is None or spec.loader is None:
            raise SystemExit("INSTALLER_BRANDING_MISSING")
        branding = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(branding)
        app_name = branding.APP_NAME
        app_version = branding.APP_VERSION

    if not isinstance(app_name, str) or not app_name.strip():
        raise SystemExit("INSTALLER_BRANDING_INVALID: app_name")
    if not isinstance(app_version, str) or not app_version.strip():
        raise SystemExit("INSTALLER_BRANDING_INVALID: app_version")
    return app_name, app_version


APP_NAME, APP_VERSION = _load_branding()

REG_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
CREDIT = "Uses the Serena engine (https://github.com/oraios/serena) internally."
INSTALL_MARKER_NAME = ".a-sunday-conductor-install.json"
INSTALL_MARKER_FORMAT = 1
UNINSTALL_REMOVE_RETRY_DELAYS = (0.25, 0.5, 1.0, 2.0, 4.0)


def _install_marker_path(target: Path) -> Path:
    return target / INSTALL_MARKER_NAME


def _write_install_marker(target: Path) -> None:
    payload = {"app_name": APP_NAME, "format": INSTALL_MARKER_FORMAT}
    _install_marker_path(target).write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _has_valid_install_marker(target: Path) -> bool:
    try:
        payload = json.loads(_install_marker_path(target).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return payload == {"app_name": APP_NAME, "format": INSTALL_MARKER_FORMAT}



def default_target() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / APP_NAME
    return Path.home() / ".local" / "bin" / APP_NAME


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.abspath(left)) == os.path.normcase(os.path.abspath(right))


def _windows_registry_install_location() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            value, _kind = winreg.QueryValueEx(key, "InstallLocation")
    except (OSError, ImportError):
        return None
    return Path(value) if isinstance(value, str) and value.strip() else None


def _registry_install_location_matches(target: Path) -> bool:
    location = _windows_registry_install_location()
    return location is not None and _same_path(location, target)


def _legacy_install_identity_exists(target: Path) -> bool:
    app = target / f"{APP_NAME}.exe"
    uninstall_exe = target / f"Uninstall-{APP_NAME}.exe"
    uninstall_cmd = target / f"Uninstall-{APP_NAME}.cmd"
    return app.is_file() and (uninstall_exe.is_file() or uninstall_cmd.is_file())


def _target_is_empty(target: Path) -> bool:
    if not target.exists():
        return True
    if not target.is_dir():
        return False
    try:
        next(target.iterdir())
    except StopIteration:
        return True
    return False

def _install_target_is_managed_or_safe(target: Path) -> bool:
    if _target_is_empty(target):
        return True
    if _has_valid_install_marker(target):
        return True
    return (
        os.name == "nt"
        and _registry_install_location_matches(target)
        and _legacy_install_identity_exists(target)
    )


def _uninstall_target_is_managed_or_safe(target: Path) -> bool:
    if os.name == "nt":
        return _registry_install_location_matches(target) and (
            _has_valid_install_marker(target) or _legacy_install_identity_exists(target)
        )
    return _has_valid_install_marker(target)


def payload_dir() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle is None:
        raise SystemExit("INSTALLER_PAYLOAD_MISSING")
    return Path(bundle) / "payload"


def _run_ps(script: str) -> None:
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "no diagnostic output").strip()
        raise RuntimeError(
            f"POWERSHELL_COMMAND_FAILED (exit {completed.returncode}): {detail}"
        )


def create_shortcut(link_path: Path, target: Path, icon: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    ps = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{link_path}'); "
        f"$s.TargetPath = '{target}'; "
        f"$s.IconLocation = '{icon}'; "
        f"$s.WorkingDirectory = '{target.parent}'; "
        f"$s.Save()"
    )
    _run_ps(ps)


def shortcut_paths() -> tuple[Path, Path]:
    programs = os.environ.get("APPDATA")
    start_menu = (
        Path(programs) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        if programs
        else Path.home() / ".local" / "share" / "applications"
    )
    start_link = start_menu / APP_NAME / f"{APP_NAME}.lnk"
    desktop = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
    return start_link, desktop


def _registered_uninstall_command(target: Path, uninstaller: Path) -> str:
    """Return a synchronous external wrapper for frozen Windows uninstall."""
    target_q = str(target).replace("'", "''")
    source_q = str(uninstaller).replace("'", "''")
    script = (
        "$ErrorActionPreference = 'Stop'; "
        f"$target = '{target_q}'; $source = '{source_q}'; "
        "$temp = Join-Path ([IO.Path]::GetTempPath()) "
        "('A-Sunday-Conductor-Uninstall-' + [guid]::NewGuid().ToString('N') + '.exe'); "
        "$rc = 1; try { "
        "Copy-Item -LiteralPath $source -Destination $temp -Force; "
        "& $temp --uninstall --target $target; $rc = $LASTEXITCODE "
        "} catch { $rc = 1 } finally { "
        "$removed = $false; for ($i = 0; $i -lt 100; $i++) { "
        "try { Remove-Item -LiteralPath $temp -Force -ErrorAction Stop; $removed = $true; break } "
        "catch { Start-Sleep -Milliseconds 100 } }; "
        "if (-not $removed -and (Test-Path -LiteralPath $temp)) { $rc = 1 } }; exit $rc"
    )
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.list2cmdline(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded]
    )


def write_registry(target: Path, uninstaller: Path) -> None:
    uninstall_command = _registered_uninstall_command(target, uninstaller)
    size_kb = 0
    for file in target.rglob("*"):
        if file.is_file():
            size_kb += file.stat().st_size // 1024
    ps = (
        f"New-Item -Path 'HKCU:\\{REG_KEY}' -Force | Out-Null; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name DisplayName -Value '{APP_NAME}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name DisplayVersion -Value '{APP_VERSION}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name DisplayIcon -Value '{target / 'assets' / 'a-conductor.ico'}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name UninstallString -Value '{uninstall_command}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name InstallLocation -Value '{target}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name NoModify -Value 1; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name NoRepair -Value 1; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name EstimatedSize -Value {size_kb}"
    )
    _run_ps(ps)


def remove_registry() -> None:
    registry_path = f"HKCU:\\{REG_KEY}"
    _run_ps(
        f"if (Test-Path -LiteralPath '{registry_path}') {{ "
        f"Remove-Item -LiteralPath '{registry_path}' -Force -ErrorAction Stop }}"
    )


def _path_is_within(path: Path, root: Path) -> bool:
    path_text = os.path.normcase(os.path.abspath(path))
    root_text = os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _frozen_uninstaller_runs_inside_target(target: Path) -> bool:
    return (
        os.name == "nt"
        and getattr(sys, "frozen", False)
        and _path_is_within(Path(sys.executable), target)
    )


NOTICES_NAME = "THIRD-PARTY-NOTICES.md"


def _install_files(source: Path, target: Path) -> Path:
    """Copy payload files into the target dir and create the uninstaller."""
    app_exe = source / f"{APP_NAME}.exe"
    guide = source / "docs" / "USER-GUIDE.md"
    guide_en = source / "docs" / "USER-GUIDE-EN.md"
    notices = source / NOTICES_NAME
    icon = source / "assets" / "a-conductor.ico"
    for required in (app_exe, guide, guide_en, notices, icon):
        if not required.is_file():
            raise FileNotFoundError(f"INSTALL_PAYLOAD_MISSING: {required}")

    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(app_exe, target / f"{APP_NAME}.exe")
    (target / "docs").mkdir(exist_ok=True)
    shutil.copy2(guide, target / "docs" / "USER-GUIDE.md")
    shutil.copy2(guide_en, target / "docs" / "USER-GUIDE-EN.md")
    (target / "assets").mkdir(exist_ok=True)
    shutil.copy2(icon, target / "assets" / "a-conductor.ico")
    shutil.copy2(notices, target / NOTICES_NAME)
    if getattr(sys, "frozen", False):
        uninstaller = target / f"Uninstall-{APP_NAME}.exe"
        shutil.copy2(Path(sys.executable), uninstaller)
    else:
        # Source mode: generate a repo-backed uninstall command for local installs.
        script = Path(__file__).resolve()
        cmd = target / f"Uninstall-{APP_NAME}.cmd"
        cmd.write_text(
            f'@echo off\r\n"{sys.executable}" "{script}" --uninstall --target "{target}"\r\n',
            encoding="utf-8",
        )
        uninstaller = cmd
    return uninstaller


def do_install(target: Path) -> int:
    source = payload_dir()
    print(f"[1/4] Installing to {target}")
    try:
        uninstaller = _install_files(source, target)
        _write_install_marker(target)
    except (FileNotFoundError, OSError) as exc:
        print(exc)
        return 2

    print("[2/4] Creating Start Menu shortcut")
    installed_icon = target / "assets" / "a-conductor.ico"
    start_link, desktop_link = shortcut_paths()
    try:
        create_shortcut(start_link, target / f"{APP_NAME}.exe", installed_icon)

        print("[3/4] Creating Desktop shortcut")
        create_shortcut(desktop_link, target / f"{APP_NAME}.exe", installed_icon)

        print("[4/4] Registering uninstall entry")
        write_registry(target, uninstaller)
    except RuntimeError as exc:
        print(f"INSTALLER_INTEGRATION_FAILED: {exc}")
        return 3

    print("DONE")
    print(f"  Start Menu : {start_link}")
    print(f"  Installed  : {target / (APP_NAME + '.exe')}")
    print(f"  Uninstall  : {uninstaller}")
    print(f"  {CREDIT}")
    return 0


def _rmtree_with_permission_retry(
    target: Path,
    *,
    retry_delays: tuple[float, ...] = UNINSTALL_REMOVE_RETRY_DELAYS,
    sleep=time.sleep,
) -> None:
    """Remove an install tree, retrying only transient Windows-style PE locks."""
    for delay in retry_delays:
        try:
            shutil.rmtree(target)
            return
        except PermissionError:
            sleep(delay)
    shutil.rmtree(target)


def do_uninstall(target: Path) -> int:
    print(f"[1/3] Removing shortcuts")
    start_link, desktop_link = shortcut_paths()
    partial = False
    for link in (start_link, desktop_link):
        try:
            link.unlink(missing_ok=True)
            if link == start_link and link.parent.name == APP_NAME:
                link.parent.rmdir()
        except OSError as exc:
            partial = True
            print(f"UNINSTALL_SHORTCUT_FAILED: {link}: {exc}")
    print("[2/3] Removing registry entry")
    try:
        remove_registry()
    except RuntimeError as exc:
        partial = True
        print(f"UNINSTALL_REGISTRY_FAILED: {exc}")
    print(f"[3/3] Removing files: {target}")
    try:
        _rmtree_with_permission_retry(target)
    except OSError as exc:
        partial = True
        print(f"UNINSTALL_FILES_FAILED: {exc}")
    if partial:
        print("UNINSTALL_PARTIAL")
        return 1
    print("DONE")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"{APP_NAME}-Setup")
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--uninstall", action="store_true")
    args = parser.parse_args(argv)

    target = args.target or default_target()
    if args.uninstall:
        if _frozen_uninstaller_runs_inside_target(target):
            print("UNINSTALL_REQUIRES_REGISTERED_COMMAND")
            return 4
        if not _uninstall_target_is_managed_or_safe(target):
            print(f"UNINSTALL_TARGET_NOT_MANAGED: {target}")
            return 5
        return do_uninstall(target)
    if not _install_target_is_managed_or_safe(target):
        print(f"INSTALL_TARGET_NOT_MANAGED: {target}")
        return 5
    return do_install(target)


if __name__ == "__main__":
    raise SystemExit(main())
