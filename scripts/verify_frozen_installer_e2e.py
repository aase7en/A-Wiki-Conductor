"""Clean-host Windows E2E for the frozen A-Sunday Conductor installer."""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import uuid
import winreg
from pathlib import Path

APP_NAME = "A-Sunday Conductor"
REG_SUBKEY = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
TEMP_UNINSTALLER_GLOB = "A-Sunday-Conductor-Uninstall-*.exe"


def fail(code: str) -> None:
    raise RuntimeError(code)


def ensure(condition: bool, code: str) -> None:
    if not condition:
        fail(code)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def registry_values() -> dict[str, object] | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY) as key:
            values: dict[str, object] = {}
            index = 0
            while True:
                try:
                    name, value, _kind = winreg.EnumValue(key, index)
                except OSError:
                    break
                values[name] = value
                index += 1
            return values
    except FileNotFoundError:
        return None


def shortcut_paths() -> tuple[Path, Path]:
    appdata = Path(os.environ["APPDATA"])
    start = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / APP_NAME / f"{APP_NAME}.lnk"
    desktop = Path.home() / "Desktop" / f"{APP_NAME}.lnk"
    return start, desktop


def run_native(exe: Path, args: list[str], expected: set[int]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run([str(exe), *args], text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="")
    ensure(completed.returncode in expected, f"NATIVE_EXIT_UNEXPECTED:{exe}:{completed.returncode}")
    return completed


def verify(portable: Path, setup: Path, expected_version: str) -> None:
    portable = portable.resolve(strict=True)
    setup = setup.resolve(strict=True)
    start_link, desktop_link = shortcut_paths()

    ensure(registry_values() is None, "HOST_REGISTRY_NOT_CLEAN")
    ensure(not start_link.exists(), "HOST_START_LINK_NOT_CLEAN")
    ensure(not desktop_link.exists(), "HOST_DESKTOP_LINK_NOT_CLEAN")
    ensure(not list(Path(tempfile.gettempdir()).glob(TEMP_UNINSTALLER_GLOB)), "HOST_TEMP_UNINSTALLER_NOT_CLEAN")

    root = Path(os.environ.get("RUNNER_TEMP", tempfile.gettempdir())) / f"a-sunday-installer-e2e-{uuid.uuid4().hex}"
    unknown = root / "unknown-nonempty"
    target = root / "managed-target"
    smoke_db = root / "installed-smoke.sqlite"
    unknown.mkdir(parents=True)
    target.mkdir(parents=True)
    sentinel = unknown / "sentinel.txt"
    sentinel.write_text("keep-me", encoding="utf-8")
    sentinel_before = sha256(sentinel)

    try:
        ensure(run_native(setup, ["--target", str(unknown)], {5}).returncode == 5, "UNKNOWN_TARGET_NOT_REJECTED")
        ensure(sha256(sentinel) == sentinel_before, "UNKNOWN_TARGET_SENTINEL_CHANGED")
        ensure(not (unknown / ".a-sunday-conductor-install.json").exists(), "UNKNOWN_TARGET_MARKER_CREATED")

        ensure(run_native(setup, ["--target", str(target)], {0}).returncode == 0, "SETUP_INSTALL_FAILED")
        marker = target / ".a-sunday-conductor-install.json"
        installed = target / f"{APP_NAME}.exe"
        uninstaller = target / f"Uninstall-{APP_NAME}.exe"
        ensure(marker.is_file(), "INSTALL_MARKER_MISSING")
        ensure(installed.is_file(), "INSTALLED_PORTABLE_MISSING")
        ensure(uninstaller.is_file(), "FROZEN_UNINSTALLER_MISSING")
        ensure(sha256(installed) == sha256(portable), "INSTALLED_PORTABLE_HASH_MISMATCH")
        ensure(start_link.is_file(), "START_LINK_MISSING")
        ensure(desktop_link.is_file(), "DESKTOP_LINK_MISSING")

        reg = registry_values()
        ensure(reg is not None, "UNINSTALL_REGISTRY_MISSING")
        ensure(reg.get("DisplayVersion") == expected_version, "REGISTRY_VERSION_MISMATCH")
        ensure(Path(str(reg.get("InstallLocation"))).resolve() == target.resolve(), "REGISTRY_TARGET_MISMATCH")
        uninstall_string = str(reg.get("UninstallString") or "")
        ensure(bool(uninstall_string.strip()), "UNINSTALL_STRING_MISSING")

        ensure(run_native(installed, ["--smoke", "--database", str(smoke_db)], {0}).returncode == 0, "INSTALLED_SMOKE_FAILED")
        ensure(smoke_db.is_file(), "INSTALLED_SMOKE_DATABASE_MISSING")

        ensure(run_native(uninstaller, ["--uninstall", "--target", str(target)], {4}).returncode == 4, "DIRECT_UNINSTALL_DID_NOT_FAIL_CLOSED")
        ensure(target.is_dir(), "DIRECT_UNINSTALL_REMOVED_TARGET")
        ensure(registry_values() is not None, "DIRECT_UNINSTALL_REMOVED_REGISTRY")

        completed = subprocess.run(uninstall_string, shell=True, text=True, capture_output=True)
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="")
        ensure(completed.returncode == 0, "REGISTERED_UNINSTALL_FAILED")
        ensure(not target.exists(), "UNINSTALL_TARGET_RESIDUE")
        ensure(not start_link.exists(), "UNINSTALL_START_LINK_RESIDUE")
        ensure(not desktop_link.exists(), "UNINSTALL_DESKTOP_LINK_RESIDUE")
        ensure(registry_values() is None, "UNINSTALL_REGISTRY_RESIDUE")
        ensure(not list(Path(tempfile.gettempdir()).glob(TEMP_UNINSTALLER_GLOB)), "UNINSTALL_TEMP_RESIDUE")
        print(f"FROZEN_INSTALLER_E2E_OK version={expected_version}")
    finally:
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--portable", type=Path, required=True)
    parser.add_argument("--setup", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()
    verify(args.portable, args.setup, args.expected_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
