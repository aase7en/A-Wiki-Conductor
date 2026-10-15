"""WO-P1-677: agent context filters must not hide SSoT/verification evidence.

Tests Git-compatible pattern semantics independently of installed editor plugins.
"""
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
DENIED = (
    "node_modules/lib/index.ts",
    "dist/index.js",
    "build/cache.bin",
    "media/scene.glb",
    "assets/logo.png",
    "runs/task/trace.log",
    "private/.env",
    "private/service.pem",
    "private/app-credentials.json",
)
REQUIRED = (
    "00-AGENT-ENTRY.md",
    "AGENTS.md",
    "PROJECT-GRAPH.yaml",
    "CURRENT-WORK.md",
    "handoff.md",
    "docs/work-orders/WO-P1-677-context-economy.md",
    "src/a_conductor/engine.py",
    "tests/test_agent_context_economy_config.py",
    "runs/task/result.json",
    "package-lock.json",
)


@pytest.mark.parametrize("config_name", [".kilocodeignore", ".cursorignore"])
def test_gitignore_style_agent_filters_preserve_authority(tmp_path: Path, config_name: str) -> None:
    config = ROOT / config_name
    assert config.is_file()
    init = subprocess.run(["git", "init", "-q", str(tmp_path)], capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    samples = DENIED + REQUIRED
    proc = subprocess.run(
        ["git", "-C", str(tmp_path), "-c", f"core.excludesFile={config}",
         "check-ignore", "--no-index", "--stdin", "-z"],
        input=b"\0".join(p.encode("utf-8") for p in samples) + b"\0",
        capture_output=True,
    )
    assert proc.returncode in (0, 1), proc.stderr.decode("utf-8", errors="replace")
    ignored = {x.decode("utf-8") for x in proc.stdout.split(b"\0") if x}
    assert set(DENIED) <= ignored, f"{config_name} missed: {set(DENIED) - ignored}"
    assert not (set(REQUIRED) & ignored), f"{config_name} hid authority: {set(REQUIRED) & ignored}"


def test_kilo_cursor_patterns_do_not_drift() -> None:
    assert (ROOT / ".kilocodeignore").read_text(encoding="utf-8") == (
        ROOT / ".cursorignore"
    ).read_text(encoding="utf-8")
