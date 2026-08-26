"""Worker table must show the user's custom display_name, not the auto id.

User bug: typed a name in Add Worker, but the table showed the auto-generated
`a-worker-NN` instead. The display_name WAS saved — the table just didn't
render it.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def root():
    import tkinter as tk

    try:
        window = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    window.withdraw()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


def make_app(root, tmp_path: Path):
    from test_instance_manage import ImmediateExecutor
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    instances_root = tmp_path / "instances"
    instances_root.mkdir(exist_ok=True)
    service = DesktopControlService.open(
        tmp_path / "ui.sqlite", instances_root=instances_root
    )
    return AConductorDesktopApp(
        root, service=service, background_executor=ImmediateExecutor()
    )


def test_add_worker_with_custom_name_shows_in_table(root, tmp_path: Path) -> None:
    app = make_app(root, tmp_path)

    # Add a worker with a custom name (simulates the dialog submit)
    app.add_worker_slot("My Custom Name")
    root.update()

    # Check the WORKERS table shows the custom name, not "a-worker-04"
    rows = app.worker_tree.get_children()
    assert len(rows) >= 4  # 3 seeded + 1 new
    new_row = rows[-1]  # the last row is the new worker
    values = app.worker_tree.item(new_row, "values")
    assert values[0] == "My Custom Name", (
        f"WORKERS table should show display_name 'My Custom Name', "
        f"got '{values[0]}' (auto id leaked through)"
    )


def test_default_worker_name_still_shows(root, tmp_path: Path) -> None:
    """Workers created without a name show the default 'A-Worker N'."""
    app = make_app(root, tmp_path)
    app.add_worker_slot(None)  # no custom name
    root.update()

    rows = app.worker_tree.get_children()
    new_row = rows[-1]
    values = app.worker_tree.item(new_row, "values")
    assert values[0].startswith("A-Worker"), (
        f"Default-named worker should show 'A-Worker N', got '{values[0]}'"
    )
