"""Materialize a new connector instance from a validated reference (WO-P1-060 PR-B).

Copies the validated per-instance layout (instance.ps1, start/stop scripts,
cmd wrappers, profile template, serena-home seed) from a reference instance,
re-rendering name/port/project/profile literals. Shared machine paths
($TunnelClientPath / $LegacySecretPath) are parsed from the reference so the
new instance always follows the same validated source of truth.
"""

from __future__ import annotations

import re
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
_TEMPLATE_PROJECT_RE = re.compile(r"(--project\s+)[^\s'\"]+")


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
    (target / "instance.ps1").write_text(instance_ps1 + "\n", encoding="utf-8", newline="\r\n")

    for script, action in (("start.ps1", "Start"), ("stop.ps1", "Stop")):
        source = reference / script
        if not source.is_file():
            raise InstanceCreateError("REFERENCE_SCRIPT_MISSING")
        text = source.read_text(encoding="utf-8")
        text = text.replace(f"serena-{reference_slug}.yaml.template", f"{profile}.yaml.template")
        text = text.replace(f"serena-{reference_slug}.yaml", f"{profile}.yaml")
        text = text.replace(f"'{reference_slug}-'", f"'{slug}-'")
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
        lambda m: m.group(1) + project.as_posix(), template_text, count=1
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

    if tunnel_id is not None:
        (target / "config" / "tunnel-id.txt").write_text(
            clean_tunnel + "\n", encoding="utf-8", newline="\r\n"
        )

    return target
