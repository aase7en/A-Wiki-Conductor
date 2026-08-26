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


def test_activation_is_found_when_recent_runtime_noise_exceeds_one_tail_chunk(tmp_path: Path) -> None:
    _write_runtime_log(
        tmp_path,
        "INFO  2026-08-26 13:54:08,456 [Task-18:ActivateProjectTool] "
        "serena.agent:_activate_project:1219 - Activating pharmacy at "
        "L:\\\\My Drive\\\\A-Wiki-Data\\\\personal-business\\\\pharmacy\n"
        + ("noise-line\n" * 60_000),
    )

    observed = observe_serena_activity(tmp_path)

    assert observed.active_project_name == "pharmacy"
    assert observed.active_project_path is not None


def test_legacy_runtime_log_filename_is_observed(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "phase6-runtime.stderr.log").write_text(
        "INFO  2026-08-26 14:05:01,100 [Task-3:ActivateProjectTool] "
        "serena.agent:_activate_project:1219 - Activating pharmacy at "
        "L:\\\\My Drive\\\\A-Wiki-Data\\\\personal-business\\\\pharmacy\n",
        encoding="utf-8",
    )

    observed = observe_serena_activity(tmp_path)

    assert observed.active_project_name == "pharmacy"


def test_tool_output_mentioning_activation_is_not_runtime_truth(tmp_path: Path) -> None:
    _write_runtime_log(
        tmp_path,
        "INFO  2026-08-26 14:01:00,001 [Task-2:ActivateProjectTool] "
        "serena.agent:_activate_project:1219 - Activating real-project at A:\\\\GitHub\\\\real-project\n"
        "INFO  2026-08-26 14:02:00,002 [Task-9:ExecuteShellCommandTool] "
        "serena.tools.tools_base:task:410 - Result: quoted text - Activating fake-project at A:\\\\GitHub\\\\fake-project\n",
    )

    observed = observe_serena_activity(tmp_path)

    assert observed.active_project_name == "real-project"
