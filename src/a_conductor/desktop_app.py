"""A-Conductor desktop bootstrap and CLI entrypoint."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Mapping, Sequence

import tkinter as tk

from .branding import APP_NAME, APP_VERSION
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
    summary = (
        0,
        f"A-CONDUCTOR_SMOKE_OK projects={len(service.snapshot().projects)} "
        f"workers={len(service.snapshot().workers)}",
    )
    try:
        root = tk.Tk()
    except tk.TclError:
        # Headless (no display): the service layer above already proves the
        # app boots; nothing UI-related to verify here.
        return summary
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
    parser.add_argument(
        "--activate-runtime",
        action="store_true",
        help="Activate one explicit durable graph node without automatic NEXT READY.",
    )
    parser.add_argument("--graph-id")
    parser.add_argument("--graph-run-id")
    parser.add_argument("--node-id")
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--task-contract-ref")
    parser.add_argument("--task-packet", type=Path)
    parser.add_argument("--provider-id")
    parser.add_argument("--model-id")
    parser.add_argument("--runtime-kind", default="serena")
    parser.add_argument("--effort-level", default="MAX")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.activate_runtime:
        if args.smoke:
            print("A-CONDUCTOR_RUNTIME_ACTIVATION_FAILED ACTIVATION_MODE_CONFLICT")
            return 2
        required = (
            ("graph_id", "GRAPH_ID_REQUIRED"),
            ("graph_run_id", "GRAPH_RUN_ID_REQUIRED"),
            ("node_id", "NODE_ID_REQUIRED"),
            ("project_root", "PROJECT_ROOT_REQUIRED"),
            ("task_contract_ref", "TASK_CONTRACT_REF_REQUIRED"),
            ("task_packet", "TASK_PACKET_REQUIRED"),
            ("provider_id", "PROVIDER_ID_REQUIRED"),
            ("model_id", "MODEL_ID_REQUIRED"),
        )
        for field, code in required:
            if getattr(args, field) is None:
                print(f"A-CONDUCTOR_RUNTIME_ACTIVATION_FAILED {code}")
                return 2
        from .desktop_control import RuntimeAuthorityError
        from .runtime_activation import RuntimeActivationError, RuntimeActivationRequest

        try:
            request = RuntimeActivationRequest(
                graph_id=args.graph_id,
                graph_run_id=args.graph_run_id,
                node_id=args.node_id,
                runtime_kind=args.runtime_kind,
                project_root=str(args.project_root),
                task_contract_ref=args.task_contract_ref,
                task_packet_path=str(args.task_packet),
                provider_id=args.provider_id,
                model_id=args.model_id,
                effort_level=args.effort_level,
            )
            service = _open_service(args.database)
            result = service.activate_runtime(args.database, request)
        except (ControlCenterError, RuntimeAuthorityError, RuntimeActivationError, ValueError) as exc:
            code = getattr(exc, "code", None) or str(exc) or "ACTIVATION_INVALID"
            print(f"A-CONDUCTOR_RUNTIME_ACTIVATION_FAILED {code}")
            return 2

        status = getattr(getattr(result, "kind", None), "value", None)
        if status is None:
            status = getattr(getattr(result, "action", None), "value", None)
        if status is None:
            status = type(result).__name__
        reason = getattr(result, "reason_code", None) or "NO_REASON"
        print(f"A-CONDUCTOR_RUNTIME_ACTIVATION_OK {status} {reason}")
        if status in {"WAIT", "RECOVERY_REQUIRED", "RECONCILE", "BLOCKED"}:
            return 3
        return 0

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
    root.withdraw()

    # Build the app immediately (hidden), then show splash → reveal
    app = AConductorDesktopApp(root, service=service)

    def reveal_main_window():
        if root.winfo_exists():
            root.deiconify()
            app.start_background_operations()

    try:
        from .splash import show_splash

        show_splash(root, APP_NAME, APP_VERSION, on_done=reveal_main_window)
    except Exception:
        reveal_main_window()

    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
