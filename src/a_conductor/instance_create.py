"""Materialize a new connector instance from a validated reference (WO-P1-060 PR-B).

Copies the validated per-instance layout (instance.ps1, start/stop scripts,
cmd wrappers, profile template, serena-home seed) from a reference instance,
re-rendering name/port/project/profile literals. Shared machine paths
($TunnelClientPath / $LegacySecretPath) are parsed from the reference so the
new instance always follows the same validated source of truth.
"""

from __future__ import annotations

import re
import sys
from enum import Enum
from pathlib import Path

from .instance_rebind import _PROJECTS_LINE_RE
from .instance_runtime import _ps_quote
from .local_instances import LocalInstance, _TUNNEL_ID_RE

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHARED_PATH_RES = (
    re.compile(r"^\$TunnelClientPath\s*=\s*'([^']*)'", re.MULTILINE),
    re.compile(r"^\$LegacySecretPath\s*=\s*'([^']*)'", re.MULTILINE),
)
_LISTEN_RE = re.compile(r"(?m)^(\s*listen_addr:\s*127\.0\.0\.1:)\d+")
_TEMPLATE_PROJECT_RE = re.compile(r"(--project\s+)(?:\"[^\"]*\"|\S+)")


class InstanceCreateError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def next_health_port(instances: tuple[LocalInstance, ...]) -> int:
    ports = []
    for instance in instances:
        tail = instance.health_address.rsplit(":", 1)[-1]
        if tail.isdigit():
            ports.append(int(tail))
    return max(ports, default=18010) + 1


def _reference_root(
    instances_root: Path, reference_root: Path | None
) -> Path:
    if reference_root is not None:
        return reference_root
    for candidate in sorted(instances_root.iterdir()):
        if (candidate / "instance.ps1").is_file():
            return candidate
    raise InstanceCreateError("REFERENCE_MISSING")


def _shared_paths(reference: Path) -> tuple[str, str]:
    text = (reference / "instance.ps1").read_text(encoding="utf-8")
    matches = [pattern.search(text) for pattern in _SHARED_PATH_RES]
    if not all(matches):
        raise InstanceCreateError("REFERENCE_PS1_INVALID")
    return matches[0].group(1), matches[1].group(1)


def _default_work_number(instances_root: Path, reference: Path) -> int:
    count = 0
    if instances_root.is_dir():
        for candidate in instances_root.iterdir():
            if (candidate / "instance.ps1").is_file():
                count += 1
    return max(count, 0) + 1


def _retitle_cmd_text(text: str, title: str) -> str:
    updated, count = re.subn(
        r"(?m)^title .*$", lambda _m: "title " + title, text, count=1
    )
    if count == 0:
        updated = text.replace("@echo off", f"@echo off\ntitle {title}", 1)
    return updated


class _RuntimeForensicsHardeningState(Enum):
    TRANSFORMED = "TRANSFORMED"
    ALREADY_HARDENED = "ALREADY_HARDENED"
    PASSTHROUGH_UNRECOGNIZED = "PASSTHROUGH_UNRECOGNIZED"
    REFUSED_AMBIGUOUS = "REFUSED_AMBIGUOUS"


def _is_runtime_forensics_hardened(text: str) -> bool:
    """Recognize the complete generated forensics shape, not marker presence alone."""
    archive_assignment = "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"
    move_archive = "Move-Item -LiteralPath $RuntimeLog -Destination $Archived -Force"
    wait = "$RuntimeProcess.WaitForExit()"
    refresh = "$RuntimeProcess.Refresh()"
    capture = "$RuntimeExitCode = $RuntimeProcess.ExitCode"
    success_log = 'Write-Log "STOPPED: tunnel-client exit_code=0"'
    failure_log = "exit_code={0}"
    exit_command = "exit $RuntimeExitCode"

    required_once = (
        archive_assignment,
        move_archive,
        wait,
        refresh,
        capture,
        success_log,
        failure_log,
        exit_command,
    )
    if any(text.count(marker) != 1 for marker in required_once):
        return False
    if "Wait-Process -Id $RuntimeProcess.Id" in text:
        return False
    if "if ($RuntimeProcess.ExitCode -ne 0)" in text:
        return False

    start = text.find('Write-Log "STARTING:')
    positions = (
        text.find(archive_assignment),
        text.find(move_archive),
        start,
        text.find(wait),
        text.find(refresh),
        text.find(capture),
        text.find(success_log),
        text.find(failure_log),
        text.find(exit_command),
    )
    return all(position >= 0 for position in positions) and list(positions) == sorted(positions)


def _has_runtime_forensics_structural_signal(text: str) -> bool:
    signals = (
        "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'",
        "$RuntimeProcess.Refresh()",
        "$RuntimeExitCode = $RuntimeProcess.ExitCode",
        "exit $RuntimeExitCode",
        "Wait-Process -Id $RuntimeProcess.Id",
        "$RuntimeProcess.WaitForExit()",
    )
    return any(signal in text for signal in signals)


def _harden_start_script_runtime_forensics(text: str) -> str:
    """Upgrade validated legacy start.ps1 text without replacing its credential/preflight logic."""
    archive_assignment_pattern = re.compile(
        r"(?m)^[ \t]*\$RuntimeArchiveDir\s*=\s*Join-Path \$LogsDir 'runtime-archive'[ \t]*$"
    )
    exit_capture_pattern = re.compile(
        r"(?m)^[ \t]*\$RuntimeExitCode\s*=\s*\$RuntimeProcess\.ExitCode[ \t]*$"
    )
    refresh_pattern = re.compile(r"(?m)^[ \t]*\$RuntimeProcess\.Refresh\(\)[ \t]*$")
    exit_command_pattern = re.compile(r"(?m)^[ \t]*exit \$RuntimeExitCode[ \t]*$")

    complete_hardening = (
        archive_assignment_pattern.search(text) is not None
        and exit_capture_pattern.search(text) is not None
        and refresh_pattern.search(text) is not None
        and exit_command_pattern.search(text) is not None
    )
    if complete_hardening:
        return text
    if (
        archive_assignment_pattern.search(text) is not None
        or exit_capture_pattern.search(text) is not None
    ):
        return text

    stdout_pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)\$RuntimeStdout\s*=.*$")
    stderr_pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)\$RuntimeStderr\s*=.*$")
    start_pattern = re.compile(r'(?m)^(?P<indent>[ \t]*)Write-Log "STARTING:')
    wait_process_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)Wait-Process -Id \$RuntimeProcess\.Id[ \t]*$"
    )
    method_wait_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)\$RuntimeProcess\.WaitForExit\(\)[ \t]*\r?\n"
        r"(?P=indent)if \(\$RuntimeProcess\.ExitCode -ne 0\) \{[ \t]*\r?\n"
        r"(?P=indent)[ \t]+Fail 'TUNNEL_START_FAILED' \"Tunnel client exited with code "
        r"\$\(\$RuntimeProcess\.ExitCode\)\.\"[ \t]*\r?\n"
        r"(?P=indent)\}[ \t]*$"
    )

    stdout_matches = tuple(stdout_pattern.finditer(text))
    stderr_matches = tuple(stderr_pattern.finditer(text))
    start_matches = tuple(start_pattern.finditer(text))
    wait_process_matches = tuple(wait_process_pattern.finditer(text))
    method_wait_matches = tuple(method_wait_pattern.finditer(text))
    if (
        len(stdout_matches) != 1
        or len(stderr_matches) != 1
        or len(start_matches) != 1
        or len(wait_process_matches) + len(method_wait_matches) != 1
        or stderr_matches[0].start() >= start_matches[0].start()
    ):
        return text

    archive = """New-Item -ItemType Directory -Force -Path $RuntimeArchiveDir | Out-Null
$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {
    if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {
        $Leaf = [System.IO.Path]::GetFileName($RuntimeLog)
        $Archived = Join-Path $RuntimeArchiveDir ($ArchiveStamp + '-' + $Leaf)
        Move-Item -LiteralPath $RuntimeLog -Destination $Archived -Force
    }
}
"""
    exit_block = """$RuntimeProcess.WaitForExit()
$RuntimeProcess.Refresh()
$RuntimeExitCode = $RuntimeProcess.ExitCode
if ($RuntimeExitCode -eq 0) {
    Write-Log "STOPPED: tunnel-client exit_code=0"
} else {
    Write-Log ("TUNNEL_START_FAILED: Tunnel client exited with code {0}; exit_code={0}" -f $RuntimeExitCode)
}
exit $RuntimeExitCode"""

    def _indent_block(block: str, indent: str) -> str:
        return "\n".join(indent + line if line else "" for line in block.splitlines())

    stderr_match = stderr_matches[0]
    stderr_indent = stderr_match.group("indent")
    hardened = (
        text[: stderr_match.end()]
        + "\n"
        + stderr_indent
        + "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"
        + text[stderr_match.end() :]
    )

    start_match = start_pattern.search(hardened)
    if start_match is None:
        return text
    start_indent = start_match.group("indent")
    archive_block = _indent_block(archive.rstrip("\n"), start_indent) + "\n\n"
    hardened = hardened[: start_match.start()] + archive_block + hardened[start_match.start() :]

    if wait_process_matches:
        wait_match = wait_process_pattern.search(hardened)
        if wait_match is None:
            return text
        replacement = _indent_block(exit_block, wait_match.group("indent"))
        return hardened[: wait_match.start()] + replacement + hardened[wait_match.end() :]

    method_match = method_wait_pattern.search(hardened)
    if method_match is None:
        return text
    replacement = _indent_block(exit_block, method_match.group("indent"))
    return hardened[: method_match.start()] + replacement + hardened[method_match.end() :]


def _classify_start_script_runtime_forensics(
    text: str,
) -> tuple[str, _RuntimeForensicsHardeningState]:
    """Return a transformed/verified script plus an explicit safety classification."""
    hardened = _harden_start_script_runtime_forensics(text)
    if hardened != text:
        if _is_runtime_forensics_hardened(hardened):
            return hardened, _RuntimeForensicsHardeningState.TRANSFORMED
        return text, _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    if _is_runtime_forensics_hardened(text):
        return text, _RuntimeForensicsHardeningState.ALREADY_HARDENED
    if _has_runtime_forensics_structural_signal(text):
        return text, _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    return text, _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


def create_instance(
    instances_root: Path | str,
    name: str,
    project_path: Path | str,
    *,
    health_port: int,
    tunnel_id: str | None = None,
    reference_root: Path | str | None = None,
    work_number: int | None = None,
) -> Path:
    root = Path(instances_root).expanduser().resolve(strict=False)
    slug = (name or "").strip().lower()
    if not _SLUG_RE.match(slug) or set(slug) == {"-"}:
        raise InstanceCreateError("NAME_INVALID")
    target = root / slug
    if target.exists():
        raise InstanceCreateError("NAME_ALREADY_EXISTS")

    project = Path(project_path)
    if not project.is_absolute() or not project.is_dir():
        raise InstanceCreateError("PROJECT_NOT_FOUND")
    project = project.resolve(strict=False)
    if not 1 <= int(health_port) <= 65535:
        raise InstanceCreateError("PORT_INVALID")

    reference = _reference_root(root, Path(reference_root) if reference_root else None)
    reference = reference.resolve(strict=False)
    tunnel_client, legacy_secret = _shared_paths(reference)
    reference_slug = reference.name

    # Validate every reference artifact BEFORE creating anything, so a bad
    # reference never leaves a half-built skeleton folder behind.
    for script in ("start.ps1", "stop.ps1"):
        if not (reference / script).is_file():
            raise InstanceCreateError("REFERENCE_SCRIPT_MISSING")

    reference_start_text = (reference / "start.ps1").read_text(encoding="utf-8")
    _, reference_start_state = _classify_start_script_runtime_forensics(reference_start_text)
    if reference_start_state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS:
        raise InstanceCreateError("REFERENCE_START_SCRIPT_UNSAFE")

    for pattern, code in (
        ("Start-*.cmd", "REFERENCE_CMD_MISSING"),
        ("Stop-*.cmd", "REFERENCE_CMD_MISSING"),
        ("profiles/*.template", "REFERENCE_TEMPLATE_MISSING"),
    ):
        if not list(reference.glob(pattern)):
            raise InstanceCreateError(code)
    if not (reference / "serena-home" / "serena_config.yml").is_file():
        raise InstanceCreateError("REFERENCE_TEMPLATE_MISSING")

    clean_tunnel = (tunnel_id or "").strip()
    if tunnel_id is not None and not _TUNNEL_ID_RE.match(clean_tunnel):
        raise InstanceCreateError("TUNNEL_ID_INVALID")

    display = slug.title()
    instance_name = f"Serena-{display}"
    profile = f"serena-{slug}"
    number = work_number if work_number is not None else _default_work_number(root, reference)

    for folder in ("profiles", "config", "run", "logs", "serena-home"):
        (target / folder).mkdir(parents=True, exist_ok=True)

    instance_ps1 = "\n".join(
        [
            f"# {instance_name} instance configuration",
            f"$InstanceName = '{_ps_quote(instance_name)}'",
            f"$ProjectPath = '{_ps_quote(str(project))}'",
            f"$SerenaHome = '{_ps_quote(str(target / 'serena-home'))}'",
            f"$HealthListenAddress = '127.0.0.1:{health_port}'",
            f"$TunnelProfileName = '{_ps_quote(profile)}'",
            f"$TunnelClientPath = '{_ps_quote(tunnel_client)}'",
            f"$LegacySecretPath = '{_ps_quote(legacy_secret)}'",
        ]
    )
    (target / "instance.ps1").write_text(instance_ps1 + "\n", encoding="utf-8-sig", newline="\r\n")

    for script, action in (("start.ps1", "Start"), ("stop.ps1", "Stop")):
        source = reference / script
        if not source.is_file():
            raise InstanceCreateError("REFERENCE_SCRIPT_MISSING")
        text = source.read_text(encoding="utf-8")
        text = text.replace(f"serena-{reference_slug}.yaml.template", f"{profile}.yaml.template")
        text = text.replace(f"serena-{reference_slug}.yaml", f"{profile}.yaml")
        text = text.replace(f"'{reference_slug}-'", f"'{slug}-'")
        if action == "Start":
            text, hardening_state = _classify_start_script_runtime_forensics(text)
            if hardening_state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS:
                raise InstanceCreateError("REFERENCE_START_SCRIPT_UNSAFE")
        (target / script).write_text(text, encoding="utf-8", newline="\r\n")

        cmd_source = reference / f"{action}-Serena-{reference_slug.title()}.cmd"
        if not cmd_source.is_file():
            matches = sorted(reference.glob(f"{action}-*.cmd"))
            if len(matches) != 1:
                raise InstanceCreateError("REFERENCE_CMD_MISSING")
            cmd_source = matches[0]
        cmd_text = cmd_source.read_text(encoding="utf-8")
        cmd_text = _retitle_cmd_text(cmd_text, f"Sunday-works {number} - {display}")
        (target / f"{action}-{instance_name}.cmd").write_text(
            cmd_text, encoding="utf-8", newline="\r\n"
        )

    templates = sorted((reference / "profiles").glob("*.template"))
    if not templates:
        raise InstanceCreateError("REFERENCE_TEMPLATE_MISSING")
    template_text = templates[0].read_text(encoding="utf-8")
    template_text = _LISTEN_RE.sub(
        lambda m: m.group(1) + str(health_port), template_text, count=1
    )
    template_text = _TEMPLATE_PROJECT_RE.sub(
        lambda m: m.group(1) + f'"{project.as_posix()}"', template_text, count=1
    )
    (target / "profiles" / f"{profile}.yaml.template").write_text(
        template_text, encoding="utf-8", newline="\n"
    )

    reference_config = reference / "serena-home" / "serena_config.yml"
    if reference_config.is_file():
        config_text = reference_config.read_text(encoding="utf-8")
        replacement = "projects:\n- '" + _ps_quote(str(project)) + "'"
        config_text = _PROJECTS_LINE_RE.sub(
            lambda _m: replacement, config_text, count=1
        )
        (target / "serena-home" / "serena_config.yml").write_text(
            config_text, encoding="utf-8", newline="\n"
        )

    if sys.platform != "win32":
        from .instance_templates_sh import render_sh_scripts

        sh_scripts = render_sh_scripts(
            instance_name=instance_name,
            project=str(project),
            serena_home=str(target / "serena-home"),
            health_port=health_port,
            profile=profile,
            slug=slug,
            tunnel_client=tunnel_client,
            api_key_file="config/api-key",
        )
        for filename, content in sh_scripts.items():
            script = target / filename
            script.write_text(content, encoding="utf-8", newline="\n")
            script.chmod(0o755)

    if tunnel_id is not None:
        (target / "config" / "tunnel-id.txt").write_text(
            clean_tunnel + "\n", encoding="utf-8", newline="\r\n"
        )

    return target
