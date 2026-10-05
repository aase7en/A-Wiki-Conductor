"""Pinned local DesktopCommanderMCP compatibility adapter.

This adapter intentionally targets only the MIT local stdio package. It does not
implement, select, or authenticate to the proprietary hosted Remote Desktop
Commander service.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PACKAGE_NAME = "@wonderwhy-er/desktop-commander"
PINNED_VERSION = "0.2.50"
PACKAGE_SPEC = f"{PACKAGE_NAME}@{PINNED_VERSION}"


class DesktopCommanderAdapterError(RuntimeError):
    """Fail-closed local adapter error carrying a stable classification code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class DesktopCommanderPackage:
    package_root: Path
    name: str
    version: str
    license: str
    entrypoint: Path


class DesktopCommanderLocalAdapter:
    """Validate and launch only the pinned local MIT stdio package."""

    def __init__(
        self,
        package_root: str | Path,
        *,
        node_executable: str = "node",
    ) -> None:
        self._package_root = Path(package_root).expanduser().resolve(strict=False)
        if not isinstance(node_executable, str) or not node_executable.strip() or "\x00" in node_executable:
            raise DesktopCommanderAdapterError("NODE_EXECUTABLE_INVALID")
        self._node_executable = node_executable.strip()

    @property
    def package_spec(self) -> str:
        return PACKAGE_SPEC

    def inspect(self) -> DesktopCommanderPackage:
        package_json = self._package_root / "package.json"
        try:
            raw = package_json.read_text(encoding="utf-8")
            metadata = json.loads(raw)
        except FileNotFoundError as exc:
            raise DesktopCommanderAdapterError("PACKAGE_NOT_FOUND") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DesktopCommanderAdapterError("PACKAGE_METADATA_INVALID") from exc

        if not isinstance(metadata, dict):
            raise DesktopCommanderAdapterError("PACKAGE_METADATA_INVALID")
        if metadata.get("name") != PACKAGE_NAME:
            raise DesktopCommanderAdapterError("PACKAGE_IDENTITY_MISMATCH")
        if metadata.get("version") != PINNED_VERSION:
            raise DesktopCommanderAdapterError("PACKAGE_VERSION_MISMATCH")
        if metadata.get("license") != "MIT":
            raise DesktopCommanderAdapterError("PACKAGE_LICENSE_MISMATCH")

        entrypoint = (self._package_root / "dist" / "index.js").resolve(strict=False)
        if not entrypoint.is_file():
            raise DesktopCommanderAdapterError("PACKAGE_ENTRYPOINT_MISSING")

        return DesktopCommanderPackage(
            package_root=self._package_root,
            name=PACKAGE_NAME,
            version=PINNED_VERSION,
            license="MIT",
            entrypoint=entrypoint,
        )

    def local_stdio_argv(self) -> tuple[str, str]:
        package = self.inspect()
        argv = (self._node_executable, str(package.entrypoint))
        if any(argument.casefold() == "remote" for argument in argv):
            raise DesktopCommanderAdapterError("HOSTED_REMOTE_MODE_FORBIDDEN")
        return argv
