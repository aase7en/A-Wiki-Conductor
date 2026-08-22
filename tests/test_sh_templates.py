"""B-2: POSIX .sh instance templates render correctly."""

from __future__ import annotations

from a_conductor.instance_templates_sh import render_sh_scripts


def test_render_produces_all_three_scripts():
    scripts = render_sh_scripts(
        instance_name="Sunday-Worker-1",
        project="/home/user/proj",
        serena_home="/home/user/AI/serena-instances/sunday-worker-1/serena-home",
        port=18011,
        profile="serena-sunday-worker-1",
        slug="sunday-worker-1",
        tunnel_client="/usr/local/bin/tunnel-client",
        api_key_file="/home/user/.config/tunnel/api-key",
    )
    assert set(scripts) == {"instance.sh", "start.sh", "stop.sh"}


def test_instance_sh_contains_all_config_values():
    scripts = render_sh_scripts(
        instance_name="Sunday-Worker-9",
        project="/opt/my project",
        serena_home="/tmp/inst/serena-home",
        port=48114,
        profile="serena-sunday-worker-9",
        slug="sunday-worker-9",
        tunnel_client="/usr/bin/tunnel-client",
        api_key_file="/etc/tunnel/key",
    )
    text = scripts["instance.sh"]
    assert 'INSTANCE_NAME="Sunday-Worker-9"' in text
    assert 'PROJECT_PATH="/opt/my project"' in text
    assert 'HEALTH_LISTEN_ADDRESS="127.0.0.1:48114"' in text
    assert 'TUNNEL_PROFILE_NAME="serena-sunday-worker-9"' in text


def test_start_sh_references_profile_and_slug():
    scripts = render_sh_scripts(
        instance_name="X",
        project="/p",
        serena_home="/sh",
        port=1234,
        profile="serena-x",
        slug="x",
        tunnel_client="/tc",
        api_key_file="/k",
    )
    start = scripts["start.sh"]
    assert "serena-x.yaml.template" in start
    assert "serena-x.yaml" in start
    assert "x-runtime.stdout.log" in start
    assert "--pid.file" in start


def test_stop_sh_handles_stale_and_missing_pid():
    stop = render_sh_scripts(
        instance_name="X",
        project="/p",
        serena_home="/sh",
        port=1234,
        profile="serena-x",
        slug="x",
        tunnel_client="/tc",
        api_key_file="/k",
    )["stop.sh"]
    assert "NOT_RUNNING" in stop
    assert "STALE_PID" in stop
    assert "kill -9" in stop
