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
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_NAME = "A-Sunday Conductor"
REG_KEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
CREDIT = "Uses the Serena engine (https://github.com/oraios/serena) internally."


def default_target() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "Programs" / APP_NAME
    return Path.home() / ".local" / "bin" / APP_NAME


def payload_dir() -> Path:
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle is None:
        raise SystemExit("INSTALLER_PAYLOAD_MISSING")
    return Path(bundle) / "payload"


def _run_ps(script: str) -> None:
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=False,
        capture_output=True,
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


def write_registry(target: Path, uninstaller: Path) -> None:
    size_kb = 0
    for file in target.rglob("*"):
        if file.is_file():
            size_kb += file.stat().st_size // 1024
    ps = (
        f"New-Item -Path 'HKCU:\\{REG_KEY}' -Force | Out-Null; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name DisplayName -Value '{APP_NAME}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name DisplayIcon -Value '{target / 'assets' / 'a-conductor.ico'}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name UninstallString -Value '\"{uninstaller}\" --uninstall --target \"{target}\"'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name InstallLocation -Value '{target}'; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name NoModify -Value 1; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name NoRepair -Value 1; "
        f"Set-ItemProperty -Path 'HKCU:\\{REG_KEY}' -Name EstimatedSize -Value {size_kb}"
    )
    _run_ps(ps)


def remove_registry() -> None:
    _run_ps(f"Remove-Item -Path 'HKCU:\\{REG_KEY}' -Force -ErrorAction SilentlyContinue")


NOTICES_NAME = "THIRD-PARTY-NOTICES.md"


def _install_files(source: Path, target: Path) -> Path:
    """Copy payload files into the target dir and create the uninstaller."""
    app_exe = source / f"{APP_NAME}.exe"
    guide = source / "docs" / "USER-GUIDE.md"
    notices = source / NOTICES_NAME
    icon = source / "assets" / "a-conductor.ico"
    for required in (app_exe, guide, notices, icon):
        if not required.is_file():
            raise FileNotFoundError(f"INSTALL_PAYLOAD_MISSING: {required}")

    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(app_exe, target / f"{APP_NAME}.exe")
    (target / "docs").mkdir(exist_ok=True)
    shutil.copy2(guide, target / "docs" / "USER-GUIDE.md")
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
    except FileNotFoundError as exc:
        print(exc)
        return 2

    print("[2/4] Creating Start Menu shortcut")
    start_link, desktop_link = shortcut_paths()
    create_shortcut(start_link, target / f"{APP_NAME}.exe", icon)

    print("[3/4] Creating Desktop shortcut")
    create_shortcut(desktop_link, target / f"{APP_NAME}.exe", icon)

    print("[4/4] Registering uninstall entry")
    write_registry(target, uninstaller)

    print("DONE")
    print(f"  Start Menu : {start_link}")
    print(f"  Installed  : {target / (APP_NAME + '.exe')}")
    print(f"  Uninstall  : {uninstaller}")
    print(f"  {CREDIT}")
    return 0


def do_uninstall(target: Path) -> int:
    print(f"[1/3] Removing shortcuts")
    start_link, desktop_link = shortcut_paths()
    for link in (start_link, desktop_link):
        try:
            link.unlink(missing_ok=True)
            if link.parent.name == APP_NAME and link.parent != shortcut_paths()[0].parent:
                link.parent.rmdir()
        except OSError:
            pass
    print("[2/3] Removing registry entry")
    remove_registry()
    print(f"[3/3] Removing files: {target}")
    try:
        shutil.rmtree(target)
    except OSError as exc:
        print(f"UNINSTALL_PARTIAL: {exc}")
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
        return do_uninstall(target)
    return do_install(target)


if __name__ == "__main__":
    raise SystemExit(main())
