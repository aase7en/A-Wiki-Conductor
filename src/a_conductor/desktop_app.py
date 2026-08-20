"""A-Conductor desktop bootstrap and CLI entrypoint."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Mapping, Sequence

import tkinter as tk

from .control_center import ControlCenterError
from .desktop_control import DesktopControlService
from .desktop_ui import AConductorDesktopApp


def default_database_path(environment: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environment is None else environment
    local_app_data = env.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "A-Conductor" / "control-center.sqlite"
    return Path.home() / ".a-conductor" / "control-center.sqlite"


def _open_service(database_path: str | Path) -> DesktopControlService:
    return DesktopControlService.open(Path(database_path))


def run_smoke(database_path: str | Path) -> tuple[int, str]:
    service = _open_service(database_path)
    root = tk.Tk()
    root.withdraw()
    try:
        app = AConductorDesktopApp(root, service=service, error_handler=lambda _code: None)
        app.refresh()
        root.update_idletasks()
        snapshot = service.snapshot()
        return (
            0,
            f"A-CONDUCTOR_SMOKE_OK projects={len(snapshot.projects)} workers={len(snapshot.workers)}",
        )
    finally:
        root.destroy()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="a-conductor")
    parser.add_argument(
        "--database",
        type=Path,
        default=default_database_path(),
        help="Path to the local Control Center SQLite database.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Construct, refresh, and destroy the UI without entering mainloop.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.smoke:
        try:
            code, summary = run_smoke(args.database)
        except ControlCenterError as exc:
            print(f"A-CONDUCTOR_SMOKE_FAILED {exc.code}")
            return 2
        print(summary)
        return code

    try:
        service = _open_service(args.database)
    except ControlCenterError as exc:
        print(f"A-CONDUCTOR_START_FAILED {exc.code}")
        return 2

    root = tk.Tk()
    AConductorDesktopApp(root, service=service)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
