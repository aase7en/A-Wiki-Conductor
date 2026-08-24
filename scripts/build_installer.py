"""Assemble the installer payload and build the Setup exe.

Usage (from the repository root, after scripts/build_portable.py succeeded):

    python scripts/build_installer.py [--distpath DIR]

Steps:
1. Copy the portable exe (dist/<APP_NAME>.exe), docs/USER-GUIDE.md,
   THIRD-PARTY-NOTICES.md, and assets/a-conductor.ico into build/payload/.
2. Run PyInstaller on scripts/installer_main.py with the payload bundled
   via --add-data, producing dist/<APP_NAME hyphenated>-Setup.exe.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from a_conductor.branding import APP_NAME, APP_VERSION  # noqa: E402
from build_portable import _harden_cosmetic_pe_steps  # noqa: E402


def setup_exe_name() -> str:
    return APP_NAME.replace(" ", "-") + "-Setup"


def assemble_payload(root: Path, dist_dir: Path, payload_dir: Path) -> Path:
    app_exe = dist_dir / f"{APP_NAME}.exe"
    guide = root / "docs" / "USER-GUIDE.md"
    guide_en = root / "docs" / "USER-GUIDE-EN.md"
    notices = root / "THIRD-PARTY-NOTICES.md"
    icon = root / "assets" / "a-conductor.ico"
    missing = [str(p) for p in (app_exe, guide, guide_en, notices, icon) if not p.is_file()]
    if missing:
        print("INSTALLER_INPUT_MISSING:")
        for item in missing:
            print(f"  {item}")
        if not app_exe.is_file():
            print("  -> run scripts/build_portable.py first")
        raise SystemExit(1)

    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)
    (payload_dir / "docs").mkdir(exist_ok=True)
    (payload_dir / "assets").mkdir(exist_ok=True)
    shutil.copy2(app_exe, payload_dir / f"{APP_NAME}.exe")
    shutil.copy2(guide, payload_dir / "docs" / "USER-GUIDE.md")
    shutil.copy2(guide_en, payload_dir / "docs" / "USER-GUIDE-EN.md")
    shutil.copy2(notices, payload_dir / "THIRD-PARTY-NOTICES.md")
    shutil.copy2(icon, payload_dir / "assets" / "a-conductor.ico")
    (payload_dir / "installer-branding.json").write_text(
        json.dumps(
            {"app_name": APP_NAME, "app_version": APP_VERSION},
            ensure_ascii=True,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return payload_dir


def pyinstaller_args(root: Path, payload_dir: Path, dist_dir: Path) -> list[str]:
    return [
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        setup_exe_name(),
        "--paths",
        str(root / "src"),
        "--icon",
        str(root / "assets" / "a-conductor.ico"),
        "--add-data",
        f"{payload_dir};payload",
        "--distpath",
        str(dist_dir),
        str(root / "scripts" / "installer_main.py"),
    ]


def main(
    argv: list[str] | None = None,
    *,
    pyinstaller_run=None,
    harden: "callable | None" = None,
    dist_dir: Path | None = None,
    payload_dir: Path | None = None,
) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    distpath = "dist"
    if "--distpath" in argv:
        index = argv.index("--distpath")
        distpath = argv[index + 1]
        del argv[index : index + 2]

    root = REPO_ROOT
    dist_dir = dist_dir or root / distpath
    payload_dir = payload_dir or root / "build" / "payload"

    assemble_payload(root=root, dist_dir=dist_dir, payload_dir=payload_dir)

    if harden is None:
        harden = _harden_cosmetic_pe_steps
    harden()

    if pyinstaller_run is None:
        from PyInstaller.__main__ import run as pyinstaller_run

    pyinstaller_run(pyinstaller_args(root=root, payload_dir=payload_dir, dist_dir=dist_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
