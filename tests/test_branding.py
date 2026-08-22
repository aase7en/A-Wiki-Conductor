"""Brand-name consistency: one display name across UI, installer, and build."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from a_conductor.branding import APP_NAME

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_display_name_is_a_sunday_conductor() -> None:
    assert APP_NAME == "A-Sunday Conductor"


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main", REPO_ROOT / "scripts" / "installer_main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_uses_same_display_name() -> None:
    installer = _load_installer_main()
    assert installer.APP_NAME == APP_NAME
    assert APP_NAME in installer.REG_KEY
    # The install layout must carry the display name (target dir + shortcut).
    start_link, desktop_link = installer.shortcut_paths()
    assert start_link.name == f"{APP_NAME}.lnk"
    assert desktop_link.name == f"{APP_NAME}.lnk"


def test_build_script_names_the_exe_after_the_display_name() -> None:
    source = (REPO_ROOT / "scripts" / "build_portable.py").read_text(encoding="utf-8")
    assert f'"{APP_NAME}"' in source


def test_data_directory_keeps_legacy_name_for_upgrade_continuity() -> None:
    # The on-disk data directory intentionally keeps its pre-rename name so an
    # in-place upgrade from A-Conductor installs preserves the user database.
    from a_conductor.desktop_app import default_database_path

    path = default_database_path({"LOCALAPPDATA": str(REPO_ROOT)})
    assert path.name == "control-center.sqlite"
    assert path.parent.name == "A-Conductor"
