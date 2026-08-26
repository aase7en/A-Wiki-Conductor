from __future__ import annotations

from pathlib import Path

from a_conductor.serena_activity import (
    SerenaActivityObservation,
    observe_serena_activity,
)


def _write_runtime_log(root: Path, text: str) -> None:
    log_dir = root / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "conductor-runtime.stderr.log").write_text(text, encoding="utf-8")


def test_missing_runtime_log_is_unknown(tmp_path: Path) -> None:
    assert observe_serena_activity(tmp_path) == SerenaActivityObservation()


def test_latest_activation_event_wins(tmp_path: Path) -> None:
    _write_runtime_log(
        tmp_path,
        "\n".join(
            [
                "INFO  2026-08-26 13:53:56,777 [Task-15:ActivateProjectTool] "
                "serena.agent:_activate_project:1219 - Activating A-Wiki at A:\\GitHub\\A-Wiki",
                "INFO  2026-08-26 13:54:08,456 [Task-18:ActivateProjectTool] "
                "serena.agent:_activate_project:1219 - Activating pharmacy at "
                "L:\\My Drive\\A-Wiki-Data\\personal-business\\pharmacy",
            ]
        ),
    )

    observed = observe_serena_activity(tmp_path)

    assert observed.active_project_name == "pharmacy"
    assert observed.active_project_path == (
        "L:\\My Drive\\A-Wiki-Data\\personal-business\\pharmacy"
    )
    assert observed.switched_at is not None
    assert observed.switched_at.strftime("%H:%M:%S") == "13:54:08"


def test_bounded_tail_still_reads_latest_activation(tmp_path: Path) -> None:
    _write_runtime_log(
        tmp_path,
        ("x" * 20_000)
        + "\nINFO  2026-08-26 14:01:02,003 [Task-22:ActivateProjectTool] "
        "serena.agent:_activate_project:1219 - Activating demo at A:\\GitHub\\demo\n",
    )

    observed = observe_serena_activity(tmp_path, max_bytes=1024)

    assert observed.active_project_name == "demo"
    assert observed.active_project_path == "A:\\GitHub\\demo"


def test_malformed_activation_is_not_reported_as_live_state(tmp_path: Path) -> None:
    _write_runtime_log(
        tmp_path,
        "INFO not-a-time [Task-1:ActivateProjectTool] "
        "serena.agent:_activate_project:1219 - Activating demo at A:\\GitHub\\demo\n",
    )
    assert observe_serena_activity(tmp_path) == SerenaActivityObservation()
