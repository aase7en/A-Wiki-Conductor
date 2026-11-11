from __future__ import annotations

import json
from pathlib import Path

import pytest

from a_conductor.desktop_commander_adapter import (
    PACKAGE_NAME,
    PACKAGE_SPEC,
    PINNED_VERSION,
    DesktopCommanderAdapterError,
    DesktopCommanderLocalAdapter,
)


def _package(
    tmp_path: Path,
    *,
    name: str = PACKAGE_NAME,
    version: str = PINNED_VERSION,
    license_name: str = "MIT",
    entrypoint: bool = True,
) -> Path:
    root = tmp_path / "desktop-commander"
    (root / "dist").mkdir(parents=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": name,
                "version": version,
                "license": license_name,
            }
        ),
        encoding="utf-8",
    )
    if entrypoint:
        (root / "dist" / "index.js").write_text("// local stdio server\n", encoding="utf-8")
    return root


def test_adapter_pins_exact_mit_package_and_local_stdio_only(tmp_path: Path) -> None:
    root = _package(tmp_path)
    adapter = DesktopCommanderLocalAdapter(root, node_executable="node")

    package = adapter.inspect()
    argv = adapter.local_stdio_argv()

    assert PACKAGE_SPEC == "@wonderwhy-er/desktop-commander@0.2.50"
    assert package.name == PACKAGE_NAME
    assert package.version == PINNED_VERSION
    assert package.license == "MIT"
    assert package.entrypoint == (root / "dist" / "index.js").resolve()
    assert argv == ("node", str(package.entrypoint))
    assert "remote" not in {part.casefold() for part in argv}


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"name": "@other/package"}, "PACKAGE_IDENTITY_MISMATCH"),
        ({"version": "0.2.51"}, "PACKAGE_VERSION_MISMATCH"),
        ({"license_name": "Proprietary"}, "PACKAGE_LICENSE_MISMATCH"),
        ({"entrypoint": False}, "PACKAGE_ENTRYPOINT_MISSING"),
    ],
)
def test_adapter_fails_closed_on_unexpected_package(
    tmp_path: Path,
    changes: dict[str, object],
    code: str,
) -> None:
    root = _package(tmp_path, **changes)
    adapter = DesktopCommanderLocalAdapter(root)

    with pytest.raises(DesktopCommanderAdapterError, match=code) as exc:
        adapter.local_stdio_argv()

    assert exc.value.code == code


def test_adapter_rejects_missing_or_invalid_metadata(tmp_path: Path) -> None:
    missing = DesktopCommanderLocalAdapter(tmp_path / "missing")
    with pytest.raises(DesktopCommanderAdapterError, match="PACKAGE_NOT_FOUND"):
        missing.inspect()

    root = tmp_path / "bad-json"
    root.mkdir()
    (root / "package.json").write_text("{", encoding="utf-8")
    invalid = DesktopCommanderLocalAdapter(root)
    with pytest.raises(DesktopCommanderAdapterError, match="PACKAGE_METADATA_INVALID"):
        invalid.inspect()


@pytest.mark.parametrize("node", ["", "   ", "bad\x00node"])
def test_adapter_rejects_invalid_node_executable(tmp_path: Path, node: str) -> None:
    root = _package(tmp_path)

    with pytest.raises(DesktopCommanderAdapterError, match="NODE_EXECUTABLE_INVALID"):
        DesktopCommanderLocalAdapter(root, node_executable=node)
