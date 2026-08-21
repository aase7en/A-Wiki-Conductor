"""Build the portable A-Conductor.exe (single file, icon + bundled docs).

Usage (from the repository root, any Python 3.11+ with PyInstaller installed):

    python scripts/build_portable.py [--distpath DIR]

Windows Defender occasionally holds freshly built executables during the two
PE post-processing steps (timestamp + manifest rewrite), which can corrupt or
fail the build. Those steps are cosmetic for local use, so this wrapper runs
PyInstaller with those two operations made best-effort (failures ignored).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _harden_cosmetic_pe_steps() -> None:
    try:
        from PyInstaller.utils.win32 import winmanifest, winutils
    except Exception:
        return

    def _soft(fn):
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                return None

        return wrapper

    winutils.set_exe_build_timestamp = _soft(winutils.set_exe_build_timestamp)
    winmanifest.write_manifest_to_executable = _soft(
        winmanifest.write_manifest_to_executable
    )
    if hasattr(winutils, "update_exe_pe_checksum"):
        winutils.update_exe_pe_checksum = _soft(winutils.update_exe_pe_checksum)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    distpath = "dist"
    if "--distpath" in argv:
        index = argv.index("--distpath")
        distpath = argv[index + 1]
        del argv[index : index + 2]

    root = Path(__file__).resolve().parents[1]
    _harden_cosmetic_pe_steps()

    from PyInstaller.__main__ import run as pyinstaller_run

    pyinstaller_run(
        [
            "--noconfirm",
            "--windowed",
            "--onefile",
            "--name",
            "A-Conductor",
            "--paths",
            str(root / "src"),
            "--icon",
            str(root / "assets" / "a-conductor.ico"),
            "--add-data",
            f"{root / 'docs' / 'USER-GUIDE.md'};docs",
            "--add-data",
            f"{root / 'assets'};assets",
            "--distpath",
            distpath,
            str(root / "entry.py"),
        ]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
