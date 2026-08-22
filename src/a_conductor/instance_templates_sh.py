"""POSIX (.sh) instance templates for cross-platform connector creation (B-2).

Mirrors the Windows .ps1/.cmd layout: instance.sh (config), start.sh, stop.sh.
Used by instance_create when the app runs on macOS/Linux.
"""

from __future__ import annotations

from pathlib import Path

INSTANCE_SH = """\
#!/bin/sh
# {instance_name} instance configuration
INSTANCE_NAME="{instance_name}"
PROJECT_PATH="{project}"
SERENA_HOME="{serena_home}"
HEALTH_LISTEN_ADDRESS="127.0.0.1:{port}"
TUNNEL_PROFILE_NAME="{profile}"
TUNNEL_CLIENT_PATH="{tunnel_client}"
API_KEY_FILE="{api_key_file}"
"""

START_SH = """\
#!/bin/sh
# {instance_name} start script
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/instance.sh"

RUN_DIR="$SCRIPT_DIR/run"
LOGS_DIR="$SCRIPT_DIR/logs"
PROFILE_FILE="$RUN_DIR/{profile}.yaml"
PID_FILE="$RUN_DIR/tunnel-client.pid"
mkdir -p "$RUN_DIR" "$LOGS_DIR" "$SERENA_HOME"

if [ -f "$PID_FILE" ]; then
    EXISTING_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
        echo "ALREADY_RUNNING pid=$EXISTING_PID"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

sed "s/__TUNNEL_ID__/$(cat "$SCRIPT_DIR/config/tunnel-id.txt" 2>/dev/null || echo '')/g" \\
    "$SCRIPT_DIR/profiles/{profile}.yaml.template" > "$PROFILE_FILE"

"$TUNNEL_CLIENT_PATH" run \\
    --profile-file "$PROFILE_FILE" \\
    --pid.file "$PID_FILE" \\
    > "$LOGS_DIR/{slug}-runtime.stdout.log" 2>&1 &

RUNTIME_PID=$!
echo "$RUNTIME_PID" > "$PID_FILE"

READY=0
for i in $(seq 1 40); do
    sleep 0.25
    if ! kill -0 "$RUNTIME_PID" 2>/dev/null; then
        echo "TUNNEL_START_FAILED: process exited"
        exit 1
    fi
    if curl -sf "http://$HEALTH_LISTEN_ADDRESS/readyz" > /dev/null 2>&1; then
        READY=1
        break
    fi
done

if [ "$READY" -ne 1 ]; then
    echo "NOT_READY: timeout"
    kill "$RUNTIME_PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 1
fi

echo "READY: $INSTANCE_NAME health=$HEALTH_LISTEN_ADDRESS project=$PROJECT_PATH"
wait "$RUNTIME_PID"
"""

STOP_SH = """\
#!/bin/sh
# {instance_name} stop script
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/instance.sh"

PID_FILE="$SCRIPT_DIR/run/tunnel-client.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "NOT_RUNNING: no pid file"
    exit 0
fi

PID=$(cat "$PID_FILE" 2>/dev/null || true)
if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
    echo "STALE_PID: cleaning"
    rm -f "$PID_FILE"
    exit 0
fi

if kill "$PID" 2>/dev/null; then
    for i in $(seq 1 20); do
        sleep 0.5
        if ! kill -0 "$PID" 2>/dev/null; then
            rm -f "$PID_FILE"
            echo "STOPPED"
            exit 0
        fi
    done
    kill -9 "$PID" 2>/dev/null || true
    rm -f "$PID_FILE"
    echo "STOPPED (force)"
    exit 0
fi

echo "STOP_FAILED"
exit 1
"""


def render_sh_scripts(
    *,
    instance_name: str,
    project: str,
    serena_home: str,
    port: int,
    profile: str,
    slug: str,
    tunnel_client: str,
    api_key_file: str,
) -> dict[str, str]:
    """Render all POSIX instance scripts; caller writes them with mode 0755."""
    context = {
        "instance_name": instance_name,
        "project": project,
        "serena_home": serena_home,
        "port": port,
        "profile": profile,
        "slug": slug,
        "tunnel_client": tunnel_client,
        "api_key_file": api_key_file,
    }
    return {
        "instance.sh": INSTANCE_SH.format(**context),
        "start.sh": START_SH.format(**context),
        "stop.sh": STOP_SH.format(**context),
    }
