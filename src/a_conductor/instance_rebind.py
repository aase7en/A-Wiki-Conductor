"""Surgical rebind of a connector instance's project (WO-P1-059 PR-C).

Rewrites exactly two lines - `$ProjectPath` in `instance.ps1` and the
`--project <forward-slash>` token in the profile template - plus the
`projects:` pin inside the instance's serena-home config when present.
Backs up both files first (`.bak`). The rendered run profile is regenerated
by `start.ps1` on every start, so only the template needs the edit.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

_PS1_PROJECT_RE = re.compile(
    r"^(\s*\$ProjectPath\s*=\s*')(?P<path>[^']*)(')\s*$", re.MULTILINE
)
_TEMPLATE_PROJECT_RE = re.compile(r"(--project\s+)(?P<path>[^\s']+)")


class InstanceRebindError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _to_forward_slash(path: str) -> str:
    return path.replace(chr(92), "/")


def _backup(path: Path) -> None:
    shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))


def _rewrite_ps1(instance_root: Path, new_project: str) -> None:
    ps1 = instance_root / "instance.ps1"
    text = ps1.read_text(encoding="utf-8")
    match = _PS1_PROJECT_RE.search(text)
    if match is None:
        raise InstanceRebindError("PS1_PROJECT_LINE_NOT_FOUND")
    _backup(ps1)
    ps1.write_text(
        _PS1_PROJECT_RE.sub(
            lambda m: m.group(1) + new_project + m.group(3), text, count=1
        ),
        encoding="utf-8",
        newline="\n",
    )


def _rewrite_template(instance_root: Path, new_project: str) -> None:
    templates = sorted((instance_root / "profiles").glob("*.template"))
    if not templates:
        raise InstanceRebindError("TEMPLATE_MISSING")
    template = templates[0]
    text = template.read_text(encoding="utf-8")
    if _TEMPLATE_PROJECT_RE.search(text) is None:
        raise InstanceRebindError("TEMPLATE_PROJECT_TOKEN_NOT_FOUND")
    _backup(template)
    template.write_text(
        _TEMPLATE_PROJECT_RE.sub(
            lambda m: m.group(1) + _to_forward_slash(new_project), text, count=1
        ),
        encoding="utf-8",
        newline="\n",
    )


_PROJECTS_LINE_RE = re.compile(r"^projects:\n- '[^']*'", re.MULTILINE)


def _rewrite_serena_home(instance_root: Path, new_project: str) -> None:
    config = instance_root / "serena-home" / "serena_config.yml"
    if not config.is_file():
        return
    text = config.read_text(encoding="utf-8")
    updated = _PROJECTS_LINE_RE.sub(
        "projects:\n- '" + new_project + "'", text, count=1
    )
    if updated != text:
        _backup(config)
        config.write_text(updated, encoding="utf-8", newline="\n")


def rebind_instance_project(
    instance, instances_root, new_project_root: str
) -> str:
    """Rebind a connector to a different project root (validated + backed up)."""
    root = Path(instances_root).expanduser().resolve(strict=False)
    instance_root = instance.instance_root.resolve(strict=False)
    if root not in instance_root.parents:
        raise InstanceRebindError("INSTANCE_OUTSIDE_ROOT")

    candidate = (new_project_root or "").strip()
    BS = chr(92)
    if not candidate or chr(0) in candidate or not Path(candidate).is_absolute():
        return "SKIPPED_PATH_INVALID"
    if not Path(candidate).is_dir():
        return "SKIPPED_PATH_NOT_FOUND"
    if Path(instance.project_path).resolve(strict=False) == Path(candidate).resolve(strict=False):
        return "SKIPPED_SAME_PROJECT"

    try:
        _rewrite_ps1(instance_root, candidate)
        _rewrite_template(instance_root, candidate)
        _rewrite_serena_home(instance_root, candidate)
    except InstanceRebindError as exc:
        return exc.code

    return "REBOUND"
