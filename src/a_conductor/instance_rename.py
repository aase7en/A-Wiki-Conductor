"""Rename a connector instance's real backend identity (WO follow-up).

Moves the instance folder and rewrites every place the old slug/name appears:
instance.ps1 ($InstanceName, $SerenaHome, $TunnelProfileName), the
start/stop.ps1 profile + log-prefix literals, the profile template filename,
and the Start/Stop cmd wrappers (renamed + retitled). Port, project, tunnel
ID, and serena-home contents are untouched. The instance must be stopped and
the caller is expected to migrate DB rows (flags/aliases) keyed by name.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .instance_runtime import _ps_quote

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_INSTANCE_LINE_RES = {
    "InstanceName": re.compile(r"^(\s*\$InstanceName\s*=\s*')(?P<value>[^']*)(')", re.M),
    "SerenaHome": re.compile(r"^(\s*\$SerenaHome\s*=\s*')(?P<value>[^']*)(')", re.M),
    "TunnelProfileName": re.compile(r"^(\s*\$TunnelProfileName\s*=\s*')(?P<value>[^']*)(')", re.M),
}


class InstanceRenameError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _display_name(slug: str) -> str:
    return "-".join(part.capitalize() for part in slug.split("-"))


def _set_ps1_value(text: str, key: str, value: str) -> str:
    pattern = _INSTANCE_LINE_RES[key]
    if pattern.search(text) is None:
        raise InstanceRenameError(f"PS1_{key.upper()}_LINE_NOT_FOUND")
    return pattern.sub(
        lambda m: m.group(1) + _ps_quote(value) + m.group(3), text, count=1
    )


def rename_instance_backend(
    instances_root: Path | str,
    old_slug: str,
    new_slug: str,
    *,
    work_number: int | None = None,
) -> Path:
    root = Path(instances_root).expanduser().resolve(strict=False)
    old = (root / (old_slug or "").strip()).resolve(strict=False)
    if root not in old.parents or not (old / "instance.ps1").is_file():
        raise InstanceRenameError("INSTANCE_NOT_FOUND")

    clean = (new_slug or "").strip().lower()
    if not _SLUG_RE.match(clean) or set(clean) == {"-"}:
        raise InstanceRenameError("SLUG_INVALID")
    target = root / clean
    if target.exists():
        raise InstanceRenameError("TARGET_EXISTS")

    old_profile = f"serena-{old.name}"
    new_profile = f"serena-{clean}"
    display = _display_name(clean)

    shutil.move(str(old), str(target))

    ps1_path = target / "instance.ps1"
    try:
        ps1 = ps1_path.read_text(encoding="utf-8")
        ps1 = _set_ps1_value(ps1, "InstanceName", display)
        ps1 = _set_ps1_value(ps1, "SerenaHome", str(target / "serena-home"))
        ps1 = _set_ps1_value(ps1, "TunnelProfileName", new_profile)
        ps1_path.write_text(ps1, encoding="utf-8", newline="\r\n")
    except Exception:
        shutil.move(str(target), str(old))
        raise

    for script in ("start.ps1", "stop.ps1"):
        path = target / script
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            text = text.replace(f"{old_profile}.yaml.template", f"{new_profile}.yaml.template")
            text = text.replace(f"{old_profile}.yaml", f"{new_profile}.yaml")
            text = text.replace(f"'{old.name}-'", f"'{clean}-'")
            path.write_text(text, encoding="utf-8", newline="\r\n")

    for template in (target / "profiles").glob(f"{old_profile}.yaml.template"):
        template.rename(target / "profiles" / f"{new_profile}.yaml.template")
    stale_profile = target / "run" / f"{old_profile}.yaml"
    if stale_profile.exists():
        stale_profile.unlink()

    if work_number is not None:
        title = f"Sunday-works {work_number} - {display}"
        for action in ("Start", "Stop"):
            for cmd in sorted(target.glob(f"{action}-*.cmd")):
                text = cmd.read_text(encoding="utf-8")
                text, count = re.subn(
                    r"(?m)^title .*$", lambda _m: "title " + title, text, count=1
                )
                if count == 0:
                    text = text.replace("@echo off", f"@echo off\ntitle {title}", 1)
                cmd.unlink()
                (target / f"{action}-{display}.cmd").write_text(
                    text, encoding="utf-8", newline="\r\n"
                )

    return target
