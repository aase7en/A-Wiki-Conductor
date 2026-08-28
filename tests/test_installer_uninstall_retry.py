from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main_uninstall_retry",
        REPO_ROOT / "scripts" / "installer_main.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_transient_permission_error_retries_then_succeeds(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    attempts: list[Path] = []
    sleeps: list[float] = []
    def remove(path: Path) -> None:
        attempts.append(path)
        if len(attempts) < 3:
            raise PermissionError("fresh PE is temporarily locked")

    monkeypatch.setattr(module.shutil, "rmtree", remove)
    module._rmtree_with_permission_retry(
        target,
        retry_delays=(0.1, 0.2, 0.4),
        sleep=sleeps.append,
    )

    assert attempts == [target, target, target]
    assert sleeps == [0.1, 0.2]


def test_persistent_permission_error_exhausts_finite_budget(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    attempts: list[Path] = []
    sleeps: list[float] = []

    def remove(path: Path) -> None:
        attempts.append(path)
        raise PermissionError("still locked")
    monkeypatch.setattr(module.shutil, "rmtree", remove)
    with pytest.raises(PermissionError, match="still locked"):
        module._rmtree_with_permission_retry(
            target,
            retry_delays=(0.1, 0.2),
            sleep=sleeps.append,
        )

    assert attempts == [target, target, target]
    assert sleeps == [0.1, 0.2]


def test_unrelated_oserror_fails_fast_without_retry(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    attempts: list[Path] = []
    sleeps: list[float] = []

    def remove(path: Path) -> None:
        attempts.append(path)
        raise OSError("disk failure")

    monkeypatch.setattr(module.shutil, "rmtree", remove)
    with pytest.raises(OSError, match="disk failure"):
        module._rmtree_with_permission_retry(target, retry_delays=(0.1,), sleep=sleeps.append)

    assert attempts == [target]
    assert sleeps == []


def test_do_uninstall_uses_bounded_tree_removal(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    start_link = tmp_path / "start.lnk"
    desktop_link = tmp_path / "desktop.lnk"
    removed: list[Path] = []

    monkeypatch.setattr(module, "shortcut_paths", lambda: (start_link, desktop_link))
    monkeypatch.setattr(module, "remove_registry", lambda: None)
    monkeypatch.setattr(module, "_rmtree_with_permission_retry", removed.append, raising=False)

    assert module.do_uninstall(target) == 0
    assert removed == [target]
