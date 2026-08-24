"""Build the portable A-Sunday Conductor.exe (single file, icon + docs).

Usage (from the repository root, any Python 3.11+ with PyInstaller installed):

    python scripts/build_portable.py [--distpath DIR]

Windows security software can temporarily hold freshly built executables during
PE post-processing. This wrapper retries only that transient PermissionError
with a finite delay budget; persistent locks and unrelated failures still fail
the build with their original error.

Product display contract: "A-Sunday Conductor". The executable name is read
from ``a_conductor.branding.APP_NAME`` rather than duplicated here.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from functools import wraps
from pathlib import Path
from typing import TypeVar

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from a_conductor.branding import APP_NAME  # noqa: E402

T = TypeVar("T")
PE_RETRY_DELAYS = (0.25, 0.5, 1.0, 2.0, 4.0)
_PERMISSION_RETRY_MARKER = "_a_conductor_permission_retry"


def run_with_permission_retry(
    operation: Callable[[], T],
    *,
    retry_delays: Sequence[float] = PE_RETRY_DELAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Run a PE write, retrying transient file locks within a finite budget."""
    for delay in retry_delays:
        try:
            return operation()
        except PermissionError:
            sleep(delay)
    return operation()


def with_permission_retry(operation: Callable[..., T]) -> Callable[..., T]:
    """Wrap a PE operation once, even when hardening is initialized repeatedly."""
    if getattr(operation, _PERMISSION_RETRY_MARKER, False):
        return operation

    @wraps(operation)
    def wrapper(*args, **kwargs):
        return run_with_permission_retry(lambda: operation(*args, **kwargs))

    setattr(wrapper, _PERMISSION_RETRY_MARKER, True)
    return wrapper


def _harden_cosmetic_pe_steps() -> None:
    try:
        from PyInstaller.utils.win32 import winmanifest, winutils
    except Exception:
        return

    winutils.set_exe_build_timestamp = with_permission_retry(
        winutils.set_exe_build_timestamp
    )
    winmanifest.write_manifest_to_executable = with_permission_retry(
        winmanifest.write_manifest_to_executable
    )
    if hasattr(winutils, "update_exe_pe_checksum"):
        winutils.update_exe_pe_checksum = with_permission_retry(
            winutils.update_exe_pe_checksum
        )


def pyinstaller_args(root: Path, dist_dir: Path | str) -> list[str]:
    """Return the deterministic portable build contract."""
    return [
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onefile",
        "--name",
        APP_NAME,
        "--paths",
        str(root / "src"),
        "--icon",
        str(root / "assets" / "a-conductor.ico"),
        "--add-data",
        f"{root / 'docs' / 'USER-GUIDE.md'};docs",
        "--add-data",
        f"{root / 'docs' / 'USER-GUIDE-EN.md'};docs",
        "--add-data",
        f"{root / 'assets'};assets",
        "--distpath",
        str(dist_dir),
        str(root / "entry.py"),
    ]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    distpath = "dist"
    if "--distpath" in argv:
        index = argv.index("--distpath")
        distpath = argv[index + 1]
        del argv[index : index + 2]

    root = REPO_ROOT
    _harden_cosmetic_pe_steps()

    from PyInstaller.__main__ import run as pyinstaller_run

    pyinstaller_run(pyinstaller_args(root=root, dist_dir=distpath))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
