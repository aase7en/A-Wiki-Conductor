"""Guarded connector-instance deletion with a zip backup (WO-P1-060 PR-C)."""

from __future__ import annotations

import zipfile
from pathlib import Path


class InstanceManageError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def zip_directory(source: Path, dest_zip: Path) -> Path:
    """Zip the whole instance tree (relative paths preserved, dirs included)."""
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(source.rglob("*")):
            if item.is_file():
                archive.write(item, item.relative_to(source).as_posix())
            elif item.is_dir():
                archive.writestr(item.relative_to(source).as_posix() + "/", "")
    return dest_zip
