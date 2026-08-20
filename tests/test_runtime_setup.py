from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from a_conductor.control_center import ControlCenterService
from a_conductor.persistence import SQLiteRegistryStore
from a_conductor.project_identity import GitReadResult
from a_conductor.runtime_setup import (
    RuntimeSetupError,
    RuntimeSetupService,
    SetupReadiness,
    WorkerSetupDraft,
)
from a_conductor.serena_config_store import SQLiteSerenaConfigStore
from a_conductor.serena_runtime import ProjectIdentityPolicy


class FakeGitRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.root = GitReadResult(True, "")
        self.branch_result = GitReadResult(True, "main")
        self.head_result = GitReadResult(True, "abc123")

    def show_toplevel(self, worktree: Path):
        self.calls.append(("root", worktree))
        return self.root

    def branch(self, worktree: Path):
        self.calls.append(("branch", worktree))
        return self.branch_result

    def head(self, worktree: Path):
        self.calls.append(("head", worktree))
        return self.head_result

    def is_ancestor(self, worktree: Path, ancestor: str):
        self.calls.append(("ancestor", ancestor))
        return GitReadResult(True, "")


def open_setup(tmp_path: Path, *, git_runner=None):
    database = tmp_path / "control.sqlite"
    control = ControlCenterService.open(SQLiteRegistryStore(database))
    config = SQLiteSerenaConfigStore(database)
    setup = RuntimeSetupService(
        control_center=control,
        config_store=config,
        git_runner=git_runner or FakeGitRunner(),
        instance_base=tmp_path / "instances",
    )
    return database, control, config, setup


def make_runtime_inputs(tmp_path: Path, draft: WorkerSetupDraft):
    external = tmp_path / "external"
    external.mkdir(exist_ok=True)
    executable = external / "tunnel-client.exe"
    executable.write_bytes(b"dummy")
    template = external / "runtime.yaml.template"
    template.write_text("tunnel: __TUNNEL_ID__\n", encoding="utf-8")
    source = external / "serena_config.yml"
    source.write_text("opaque-config-sentinel: true\n", encoding="utf-8")
    refs = tmp_path / "refs"
    refs.mkdir(exist_ok=True)
    ref_file = refs / "tunnel-id.txt"
    return (
        replace(
            draft,
            runtime_executable_ref=str(executable.resolve()),
            profile_template_ref=str(template.resolve()),
            tunnel_binding_ref="tunnel-ref-a-worker-01",
            reference_file_path=str(ref_file.resolve()),
            reference_allowed_root=str(refs.resolve()),
        ),
        source,
        ref_file,
    )


def assign_project(tmp_path: Path, control: ControlCenterService):
    project_dir = tmp_path / "project"
    project_dir.mkdir(exist_ok=True)
    project = control.register_project(project_dir, display_name="Project")
    control.assign_project("a-worker-01", project.project_id, mutation_allowed=True)
    return project, project_dir


def test_unconfigured_worker_gets_non_persisted_isolated_proposal(tmp_path: Path) -> None:
    _, _, config, setup = open_setup(tmp_path)

    draft = setup.worker_setup("a-worker-01")

    assert draft.configured is False
    assert Path(draft.instance_root) == (tmp_path / "instances" / "a-worker-01").resolve()
    assert draft.health_host == "127.0.0.1"
    assert draft.health_port == 18011
    assert Path(draft.serena_home) == Path(draft.instance_root) / "serena-home"
    assert Path(draft.run_dir) == Path(draft.instance_root) / "run"
    assert Path(draft.log_dir) == Path(draft.instance_root) / "logs"
    assert config.get_worker_config("a-worker-01") is None


def test_worker_two_three_default_ports_are_deterministic(tmp_path: Path) -> None:
    _, _, _, setup = open_setup(tmp_path)
    assert setup.worker_setup("a-worker-02").health_port == 18012
    assert setup.worker_setup("a-worker-03").health_port == 18013


def test_save_worker_setup_copies_opaque_serena_config_and_persists_metadata(tmp_path: Path) -> None:
    database, _, config, setup = open_setup(tmp_path)
    draft, source, _ = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))

    saved = setup.save_worker_setup(draft, serena_config_source=source)

    assert saved.configured is True
    worker = config.get_worker_config("a-worker-01")
    assert worker is not None
    assert worker.health_port == 18011
    target_config = Path(worker.serena_home) / "serena_config.yml"
    assert target_config.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")
    database_bytes = database.read_bytes()
    assert b"opaque-config-sentinel" not in database_bytes
    assert str(source).encode() not in database_bytes


def test_save_worker_setup_requires_existing_executable_template_and_source(tmp_path: Path) -> None:
    _, _, _, setup = open_setup(tmp_path)
    draft = setup.worker_setup("a-worker-01")
    with pytest.raises(RuntimeSetupError) as exc_info:
        setup.save_worker_setup(draft, serena_config_source=tmp_path / "missing.yml")
    assert exc_info.value.code == "RUNTIME_EXECUTABLE_NOT_FOUND"


def test_existing_serena_config_allows_resave_without_source(tmp_path: Path) -> None:
    _, _, _, setup = open_setup(tmp_path)
    draft, source, _ = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))
    setup.save_worker_setup(draft, serena_config_source=source)
    existing = setup.worker_setup("a-worker-01")

    saved = setup.save_worker_setup(existing, serena_config_source=None)

    assert saved.configured is True


def test_tunnel_reference_metadata_is_persisted_without_reading_value(tmp_path: Path) -> None:
    _, _, config, setup = open_setup(tmp_path)
    draft, source, ref_file = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))
    assert not ref_file.exists()

    setup.save_worker_setup(draft, serena_config_source=source)

    reference = config.get_local_reference("tunnel-ref-a-worker-01")
    assert reference is not None
    assert reference.file_path == str(ref_file.resolve())
    assert not ref_file.exists()


def test_capture_exact_project_identity_is_read_only_and_persistent(tmp_path: Path) -> None:
    git = FakeGitRunner()
    _, control, config, setup = open_setup(tmp_path, git_runner=git)
    project, project_dir = assign_project(tmp_path, control)
    git.root = GitReadResult(True, str(project_dir.resolve()))
    sentinel = project_dir / "keep.txt"
    sentinel.write_text("same", encoding="utf-8")

    binding = setup.capture_exact_project_identity("a-worker-01")

    assert binding.project_id == project.project_id
    assert binding.identity_policy is ProjectIdentityPolicy.EXACT
    assert binding.expected_branch == "main"
    assert binding.expected_head == "abc123"
    assert binding.mutation_allowed is True
    assert config.get_project_binding(project.project_id) == binding
    assert sentinel.read_text(encoding="utf-8") == "same"
    assert [name for name, _ in git.calls] == ["root", "branch", "head"]


def test_capture_exact_identity_rejects_root_mismatch(tmp_path: Path) -> None:
    git = FakeGitRunner()
    _, control, _, setup = open_setup(tmp_path, git_runner=git)
    assign_project(tmp_path, control)
    git.root = GitReadResult(True, str((tmp_path / "other").resolve()))

    with pytest.raises(RuntimeSetupError) as exc_info:
        setup.capture_exact_project_identity("a-worker-01")
    assert exc_info.value.code == "PROJECT_ROOT_MISMATCH"


def test_explicit_no_git_binding_is_persisted(tmp_path: Path) -> None:
    _, control, config, setup = open_setup(tmp_path)
    project, _ = assign_project(tmp_path, control)

    binding = setup.save_no_git_project_identity("a-worker-01")

    assert binding.identity_policy is ProjectIdentityPolicy.NO_GIT
    assert binding.expected_branch is None
    assert binding.expected_head is None
    assert config.get_project_binding(project.project_id) == binding


def test_readiness_reports_assignment_missing(tmp_path: Path) -> None:
    _, _, _, setup = open_setup(tmp_path)
    assert setup.lifecycle_readiness("a-worker-01") == SetupReadiness(False, "ASSIGNMENT_MISSING")


def test_readiness_requires_worker_config_then_project_binding(tmp_path: Path) -> None:
    _, control, _, setup = open_setup(tmp_path)
    assign_project(tmp_path, control)
    assert setup.lifecycle_readiness("a-worker-01") == SetupReadiness(False, "WORKER_CONFIG_MISSING")

    draft, source, _ = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))
    setup.save_worker_setup(draft, serena_config_source=source)
    assert setup.lifecycle_readiness("a-worker-01") == SetupReadiness(False, "PROJECT_BINDING_MISSING")


def test_readiness_requires_reference_file_when_tunnel_is_required(tmp_path: Path) -> None:
    _, control, _, setup = open_setup(tmp_path)
    assign_project(tmp_path, control)
    draft, source, ref_file = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))
    setup.save_worker_setup(draft, serena_config_source=source)
    setup.save_no_git_project_identity("a-worker-01")

    assert setup.lifecycle_readiness("a-worker-01") == SetupReadiness(False, "TUNNEL_REFERENCE_FILE_NOT_FOUND")

    ref_file.write_text("opaque-tunnel-id", encoding="utf-8")
    assert setup.lifecycle_readiness("a-worker-01") == SetupReadiness(True, "READY")


def test_worker_setup_view_never_exposes_reference_file_contents(tmp_path: Path) -> None:
    _, _, _, setup = open_setup(tmp_path)
    draft, source, ref_file = make_runtime_inputs(tmp_path, setup.worker_setup("a-worker-01"))
    ref_file.write_text("do-not-show-this-tunnel-id", encoding="utf-8")
    setup.save_worker_setup(draft, serena_config_source=source)

    view = setup.worker_setup("a-worker-01")

    assert "do-not-show-this-tunnel-id" not in repr(view)
    assert view.reference_file_path == str(ref_file.resolve())
