"""Installer build: payload assembly, setup naming, notices, version sync."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tomllib
from pathlib import Path

import pytest

from a_conductor.branding import APP_NAME, APP_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_build_portable():
    spec = importlib.util.spec_from_file_location(
        "build_portable", REPO_ROOT / "scripts" / "build_portable.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fresh_pe_permission_lock_is_retried_with_a_finite_budget() -> None:
    module = _load_build_portable()
    attempts = 0
    delays: list[float] = []

    def temporarily_locked() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("fresh executable is temporarily locked")
        return "written"

    result = module.run_with_permission_retry(
        temporarily_locked,
        retry_delays=(0.1, 0.2, 0.4),
        sleep=delays.append,
    )

    assert result == "written"
    assert attempts == 3
    assert delays == [0.1, 0.2]


def test_permission_retry_wrapper_is_idempotent() -> None:
    module = _load_build_portable()

    def write_pe() -> None:
        return None

    wrapped = module.with_permission_retry(write_pe)

    assert module.with_permission_retry(wrapped) is wrapped


def test_persistent_pe_permission_lock_is_raised_after_retry_budget() -> None:
    module = _load_build_portable()
    attempts = 0
    delays: list[float] = []

    def persistently_locked() -> None:
        nonlocal attempts
        attempts += 1
        raise PermissionError("still locked")

    with pytest.raises(PermissionError, match="still locked"):
        module.run_with_permission_retry(
            persistently_locked,
            retry_delays=(0.1, 0.2),
            sleep=delays.append,
        )

    assert attempts == 3
    assert delays == [0.1, 0.2]


def test_portable_build_is_clean_and_bundles_brand_runtime_inputs(tmp_path: Path) -> None:
    module = _load_build_portable()

    args = module.pyinstaller_args(root=REPO_ROOT, dist_dir=tmp_path / "dist")

    assert "--clean" in args
    assert args[args.index("--name") + 1] == APP_NAME
    assert f"{REPO_ROOT / 'assets'};assets" in args
    collected = [args[index + 1] for index, value in enumerate(args[:-1]) if value == "--collect-all"]
    assert collected == ["tkinterweb", "tkinterweb_tkhtml", "tkinterweb_tkhtml_extras"]
    assert args[-1] == str(REPO_ROOT / "entry.py")


def test_build_and_installer_metadata_use_branding_ssot() -> None:
    portable_source = (REPO_ROOT / "scripts" / "build_portable.py").read_text(
        encoding="utf-8"
    )
    build_installer_source = (
        REPO_ROOT / "scripts" / "build_installer.py"
    ).read_text(encoding="utf-8")
    installer_source = (REPO_ROOT / "scripts" / "installer_main.py").read_text(
        encoding="utf-8"
    )

    assert "from a_conductor.branding import APP_NAME" in portable_source
    assert "from a_conductor.branding import APP_NAME, APP_VERSION" in build_installer_source
    assert "installer-branding.json" in installer_source
    assert 'APP_NAME = "A-Sunday Conductor"' not in installer_source
    assert 'APP_VERSION = "0.7.0"' not in installer_source


def _load_build_installer():
    spec = importlib.util.spec_from_file_location(
        "build_installer", REPO_ROOT / "scripts" / "build_installer.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def build_installer():
    return _load_build_installer()


def test_pyproject_version_matches_branding() -> None:
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == APP_VERSION


def test_third_party_notices_exists_and_credits_serena() -> None:
    notices = REPO_ROOT / "THIRD-PARTY-NOTICES.md"
    assert notices.is_file()
    content = notices.read_text(encoding="utf-8")
    assert "Serena" in content
    assert "oraios/serena" in content
    assert "MIT License" in content
    assert "Permission is hereby granted" in content  # full MIT text, not a link
    assert "TkinterWeb" in content
    assert "Andrew Clarke" in content
    assert "Python-Markdown" in content
    assert "BSD 3-Clause License" in content


def test_setup_exe_name_derives_from_display_name(build_installer) -> None:
    assert build_installer.setup_exe_name() == "A-Sunday-Conductor-Setup"


def test_assemble_payload_copies_everything(build_installer, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"{APP_NAME}.exe").write_bytes(b"FAKE-EXE")
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "stale-file.txt").write_text("stale", encoding="utf-8")

    build_installer.assemble_payload(root=REPO_ROOT, dist_dir=dist, payload_dir=payload)

    assert not (payload / "stale-file.txt").exists()
    assert (payload / f"{APP_NAME}.exe").read_bytes() == b"FAKE-EXE"
    assert (payload / "docs" / "USER-GUIDE.md").is_file()
    assert (payload / "THIRD-PARTY-NOTICES.md").is_file()
    assert (payload / "assets" / "a-conductor.ico").is_file()
    assert json.loads((payload / "installer-branding.json").read_text(encoding="utf-8")) == {
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
    }


def test_assemble_payload_fails_clearly_without_portable_exe(
    build_installer, tmp_path: Path, capsys
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        build_installer.assemble_payload(
            root=REPO_ROOT, dist_dir=tmp_path, payload_dir=tmp_path / "payload"
        )
    assert "build_portable" in str(excinfo.value) or "build_portable" in capsys.readouterr().out


def test_pyinstaller_args_carry_setup_name_and_payload(build_installer, tmp_path: Path) -> None:
    args = build_installer.pyinstaller_args(
        root=REPO_ROOT, payload_dir=tmp_path / "payload", dist_dir=tmp_path / "dist"
    )
    name_index = args.index("--name")
    assert "--clean" in args
    assert args[name_index + 1] == "A-Sunday-Conductor-Setup"
    assert args[args.index("--icon") + 1] == str(
        REPO_ROOT / "assets" / "a-conductor.ico"
    )
    data_index = next(
        i
        for i, arg in enumerate(args)
        if str(arg).startswith("payload;") or str(arg).endswith(";payload")
    )
    assert str(args[data_index]).startswith(str(tmp_path / "payload"))
    assert args[-1].endswith("installer_main.py")


def _load_installer_main():
    spec = importlib.util.spec_from_file_location(
        "installer_main", REPO_ROOT / "scripts" / "installer_main.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_installer_payload(root: Path) -> Path:
    source = root / "payload"
    source.mkdir()
    (source / f"{APP_NAME}.exe").write_bytes(b"EXE")
    (source / "docs").mkdir()
    (source / "docs" / "USER-GUIDE.md").write_text("guide", encoding="utf-8")
    (source / "docs" / "USER-GUIDE-EN.md").write_text(
        "guide-en", encoding="utf-8"
    )
    (source / "assets").mkdir()
    (source / "assets" / "a-conductor.ico").write_bytes(b"ICO")
    (source / "THIRD-PARTY-NOTICES.md").write_text(
        "notices", encoding="utf-8"
    )
    return source


def test_powershell_failure_is_reported_instead_of_silently_ignored(
    monkeypatch,
) -> None:
    module = _load_installer_main()

    def failed_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0], returncode=5, stdout="", stderr="access denied"
        )

    monkeypatch.setattr(module.subprocess, "run", failed_run)

    with pytest.raises(RuntimeError, match="POWERSHELL_COMMAND_FAILED.*access denied"):
        module._run_ps("Write-Output test")


def test_registry_entry_records_current_display_version(
    tmp_path: Path, monkeypatch
) -> None:
    module = _load_installer_main()
    target = tmp_path / "installed"
    target.mkdir()
    (target / f"{APP_NAME}.exe").write_bytes(b"EXE")
    scripts: list[str] = []
    monkeypatch.setattr(module, "_run_ps", scripts.append)

    module.write_registry(target, target / f"Uninstall-{APP_NAME}.exe")

    assert module.APP_VERSION == APP_VERSION == "0.7.0"
    assert "-Name DisplayVersion -Value '0.7.0'" in scripts[0]


def test_registry_removal_ignores_absence_but_surfaces_real_errors(monkeypatch) -> None:
    module = _load_installer_main()
    scripts: list[str] = []
    monkeypatch.setattr(module, "_run_ps", scripts.append)

    module.remove_registry()

    assert "Test-Path" in scripts[0]
    assert "-ErrorAction Stop" in scripts[0]
    assert "SilentlyContinue" not in scripts[0]


def test_windows_ci_builds_verifies_smokes_and_archives_portable() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    for required in (
        "python scripts/build_portable.py",
        "pyinstaller==6.22.2",
        "PORTABLE_BUILD_FAILED",
        "SETUP_BUILD_FAILED",
        "pyi-archive_viewer",
        "assets/sunday-family-particle.png",
        "a_conductor.gpu_particle_logo",
        "a_conductor.system_metrics",
        "moderngl/mgl",
        "glcontext/wgl",
        "PIL/_imaging",
        "tcl86t.dll",
        "tk86t.dll",
        "tkinterweb",
        "tkinterweb_tkhtml",
        "tkinterweb_tkhtml_extras",
        "markdown",
        "tests/test_guide_html_ui.py",
        "payload/installer-branding.json",
        "SETUP_ARCHIVE_UNEXPECTED_ENTRY",
        "Start-Process",
        "actions/upload-artifact@v7",
        "scripts/verify_frozen_installer_e2e.ps1",
        "Frozen Setup install/uninstall E2E",
    ):
        assert required in workflow
    # ``pyi-archive_viewer`` emits Windows member names with backslashes.  CI
    # normalises both archives before comparing them with portable '/' paths.
    assert workflow.count("-replace '\\\\', '/'") == 2
    # Hosted Windows runners expose an unstable virtual GL context that can
    # terminate the process before Python's fallback handler runs.  Generic CI
    # exercises the deterministic Canvas path; real WGL is an explicit local E2E.
    assert 'A_CONDUCTOR_GPU_PARTICLES: "0"' in workflow

    verifier = (REPO_ROOT / "scripts" / "verify_frozen_installer_e2e.ps1").read_text(
        encoding="utf-8"
    )
    for required in (
        "FROZEN_INSTALLER_E2E_OK",
        "UNKNOWN_TARGET_SENTINEL_CHANGED",
        "REGISTERED_UNINSTALL_FAILED",
        "UNINSTALL_TEMP_RESIDUE",
    ):
        assert required in verifier

    gui_block = workflow.split("- name: Run GUI test suite", 1)[1].split(
        "- name: Run local-instance lifecycle suite", 1
    )[0]
    assert "tests/test_interactive_logo.py" in gui_block

    remaining_block = workflow.split(
        "- name: Run remaining core suites one file per process", 1
    )[1].split("- name: Smoke test", 1)[0]
    assert '"test_interactive_logo.py"' in remaining_block


def test_install_guide_matches_current_release_and_hkcu_contract() -> None:
    guide = (REPO_ROOT / "INSTALL.md").read_text(encoding="utf-8")

    assert f"v{APP_VERSION}" in guide
    assert "HKCU" in guide
    assert "ไม่แตะ system32 / registry" not in guide


def test_main_hardens_pe_steps_before_running_pyinstaller(
    build_installer, tmp_path: Path
) -> None:
    events: list[str] = []

    def fake_harden() -> None:
        events.append("harden")

    def fake_run(args) -> None:
        events.append("run")

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / f"{APP_NAME}.exe").write_bytes(b"FAKE-EXE")

    code = build_installer.main(
        [],
        pyinstaller_run=fake_run,
        harden=fake_harden,
        dist_dir=dist,
        payload_dir=tmp_path / "payload",
    )

    assert code == 0
    assert events == ["harden", "run"]


def test_installer_install_files_copies_notices(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    source = _make_installer_payload(tmp_path)
    monkeypatch.setattr(module, "payload_dir", lambda: source)

    target = tmp_path / "target"
    target.mkdir()
    uninstaller = module._install_files(source, target)

    assert (target / f"{APP_NAME}.exe").is_file()
    assert (target / "docs" / "USER-GUIDE.md").is_file()
    assert (target / "assets" / "a-conductor.ico").is_file()
    assert (target / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8") == "notices"
    assert uninstaller.is_file()


def test_do_install_uses_installed_icon_for_shortcuts(tmp_path: Path, monkeypatch) -> None:
    module = _load_installer_main()
    source = _make_installer_payload(tmp_path)
    monkeypatch.setattr(module, "payload_dir", lambda: source)

    calls: list[tuple] = []
    monkeypatch.setattr(module, "create_shortcut", lambda *a: calls.append(("shortcut", *a)))
    monkeypatch.setattr(module, "write_registry", lambda *a: calls.append(("registry", *a)))

    target = tmp_path / "install-target"
    code = module.do_install(target)

    assert code == 0
    shortcuts = [c for c in calls if c[0] == "shortcut"]
    assert len(shortcuts) == 2
    expected_icon = target / "assets" / "a-conductor.ico"
    for call in shortcuts:
        assert call[3] == expected_icon
        assert call[2] == target / f"{APP_NAME}.exe"
    assert any(c[0] == "registry" for c in calls)


def test_do_install_returns_failure_when_shortcut_creation_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    source = _make_installer_payload(tmp_path)
    monkeypatch.setattr(module, "payload_dir", lambda: source)

    def fail_shortcut(*args) -> None:
        raise RuntimeError("POWERSHELL_COMMAND_FAILED (exit 5): access denied")

    monkeypatch.setattr(module, "create_shortcut", fail_shortcut)
    registry_calls: list[tuple] = []
    monkeypatch.setattr(module, "write_registry", lambda *args: registry_calls.append(args))

    code = module.do_install(tmp_path / "target")

    assert code == 3
    assert "INSTALLER_INTEGRATION_FAILED" in capsys.readouterr().out
    assert registry_calls == []


def test_do_uninstall_reports_shortcut_removal_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    start_link = tmp_path / "start.lnk"
    desktop_link = tmp_path / "desktop.lnk"
    monkeypatch.setattr(module, "shortcut_paths", lambda: (start_link, desktop_link))

    def denied_unlink(self, *args, **kwargs):
        raise PermissionError("shortcut is locked")

    monkeypatch.setattr(Path, "unlink", denied_unlink)
    monkeypatch.setattr(module, "remove_registry", lambda: None)
    monkeypatch.setattr(module.shutil, "rmtree", lambda target: None)

    code = module.do_uninstall(tmp_path / "target")

    output = capsys.readouterr().out
    assert code == 1
    assert "UNINSTALL_SHORTCUT_FAILED" in output
    assert "shortcut is locked" in output


def test_do_uninstall_continues_file_cleanup_after_registry_failure(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    module = _load_installer_main()
    monkeypatch.setattr(
        module,
        "shortcut_paths",
        lambda: (tmp_path / "start.lnk", tmp_path / "desktop.lnk"),
    )

    def fail_registry() -> None:
        raise RuntimeError("registry denied")

    monkeypatch.setattr(module, "remove_registry", fail_registry)
    removed: list[Path] = []
    monkeypatch.setattr(module.shutil, "rmtree", removed.append)
    target = tmp_path / "target"

    code = module.do_uninstall(target)

    output = capsys.readouterr().out
    assert code == 1
    assert removed == [target]
    assert "UNINSTALL_REGISTRY_FAILED" in output
    assert "registry denied" in output
