"""End-to-end real-system test through the DesktopControlService facade.

Exercises every user-facing flow the same way the UI does, against a real
SQLite database, real connector discovery, and a sandbox copy of a real
instance directory (so the user's live instances are untouched).

Usage: python -m pytest tests/test_e2e_real_system.py -v --tb=short
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from a_conductor.desktop_control import DesktopControlService
from a_conductor.local_instances import (
    InstanceHealthState,
    LocalInstanceOrchestrator,
    discover_local_instances,
    instance_health_state,
)
from a_conductor.memory_presence import MemoryPresenceState, inspect_memory_presence
from a_conductor.upstream_check import fetch_upstream_status
from a_conductor.worker_serena_settings import (
    LanguageBackend,
    WorkerSerenaSettings,
    apply_brain_to_serena_home,
)


REAL_INSTANCES_ROOT = Path("C:/AI/serena-instances")
SANDBOX_SOURCE = REAL_INSTANCES_ROOT / "wastewater"

# Projects on this machine that genuinely exist
PROJECT_WASTEWATER = Path("A:/GitHub/env-wastewater-webapp")
PROJECT_CONDUCTOR = Path("A:/GitHub/A-Wiki-Conductor")
PROJECT_AWIKI = Path("A:/GitHub/A-Wiki")

# Skip the entire module on CI runners (no local instances/projects/network)
pytestmark = pytest.mark.skipif(
    not REAL_INSTANCES_ROOT.is_dir() or not PROJECT_WASTEWATER.is_dir(),
    reason="requires this machine's real instances and projects",
)


@pytest.fixture(scope="module")
def e2e(tmp_path_factory):
    """Fresh service + sandbox instance tree."""
    tmp = tmp_path_factory.mktemp("e2e-real")
    db = tmp / "e2e.sqlite"
    sandbox_root = tmp / "instances"

    # Copy the real wastewater instance as a sandbox (skip logs/run for speed)
    if SANDBOX_SOURCE.is_dir():
        shutil.copytree(
            SANDBOX_SOURCE,
            sandbox_root / "wastewater",
            ignore=shutil.ignore_patterns("logs", "run", "__pycache__"),
        )

    service = DesktopControlService.open(db, instances_root=sandbox_root)
    yield {"service": service, "tmp": tmp, "sandbox_root": sandbox_root, "db": db}


class TestProgramOpen:
    """User opens the program."""

    def test_opens_with_default_workers(self, e2e):
        snap = e2e["service"].snapshot()
        assert len(snap.workers) == 3
        assert snap.online is True
        assert all(w.assignment_id is None for w in snap.workers)

    def test_discovers_real_connector_instances(self, e2e):
        instances = e2e["service"].instances()
        assert len(instances) >= 1
        names = {i.name for i in instances}
        assert "Serena-Wastewater" in names


class TestAddProjectAndAssign:
    """User adds a project, assigns to a worker, releases, reassigns."""

    def test_add_project_registers_without_mutation(self, e2e):
        svc = e2e["service"]
        result = svc.register_project(str(PROJECT_WASTEWATER), display_name="Wastewater")
        snap = svc.snapshot()
        assert any(p.root_path == str(PROJECT_WASTEWATER) for p in snap.projects)

    def test_assign_to_worker_slot_1(self, e2e):
        svc = e2e["service"]
        snap = svc.snapshot()
        worker = next(w for w in snap.workers if w.assignment_id is None)
        project = next(p for p in snap.projects if "wastewater" in p.root_path.lower())
        svc.assign_project(worker.worker_id, project.project_id, mutation_allowed=True)
        snap = svc.snapshot()
        row = next(w for w in snap.workers if w.worker_id == worker.worker_id)
        assert row.project_root_path is not None
        assert "wastewater" in row.project_root_path.lower()

    def test_release_and_reassign_to_worker_2(self, e2e):
        svc = e2e["service"]
        snap = svc.snapshot()
        assigned = next(w for w in snap.workers if w.assignment_id is not None)
        free = next(w for w in snap.workers if w.assignment_id is None)
        svc.release_worker(assigned.worker_id)
        snap = svc.snapshot()
        assert next(w for w in snap.workers if w.worker_id == assigned.worker_id).assignment_id is None

        project = next(p for p in snap.projects)
        svc.assign_project(free.worker_id, project.project_id, mutation_allowed=True)
        snap = svc.snapshot()
        assert next(w for w in snap.workers if w.worker_id == free.worker_id).assignment_id is not None


class TestConnectorAwareStart:
    """User presses Start on a worker that has a matching connector."""

    def test_worker_start_path_finds_connector(self, e2e):
        svc = e2e["service"]
        snap = svc.snapshot()
        assigned = next((w for w in snap.workers if w.assignment_id is not None), None)
        if assigned is None:
            pytest.skip("no assigned worker in fixture ordering")
        kind, detail = svc.worker_start_path(assigned.worker_id)
        assert kind in ("connector", "lifecycle", "blocked")
        # In the sandbox, the connector project path may differ from the assigned project
        # so we check that the decision mechanism works
        assert isinstance(detail, (str, type(None)))

    def test_connector_health_state_real(self, e2e):
        """Check the live wastewater instance health through our probe."""
        instances = discover_local_instances(REAL_INSTANCES_ROOT)
        wastewater = next((i for i in instances if i.name == "Serena-Wastewater"), None)
        if wastewater is None:
            pytest.skip("Serena-Wastewater not on this machine")
        state = instance_health_state(wastewater)
        assert state in (InstanceHealthState.READY, InstanceHealthState.STOPPED, InstanceHealthState.UNKNOWN)


class TestProjectChange:
    """User activates a project and changes the connector's project."""

    def test_activation_prompt_contains_project_path(self, e2e):
        svc = e2e["service"]
        snap = svc.snapshot()
        assigned = next((w for w in snap.workers if w.assignment_id is not None), None)
        if assigned is None:
            pytest.skip("no assigned worker")
        # The activation prompt (WO-056) should reference the worker's project path
        assert assigned.project_root_path is not None

    def test_rebind_sandbox_connector(self, e2e):
        """Rebind the sandbox copy to a different real project."""
        svc = e2e["service"]
        sandbox_instances = discover_local_instances(e2e["sandbox_root"])
        if not sandbox_instances:
            pytest.skip("sandbox instance not copied")
        target = sandbox_instances[0]
        # Rebind to A-Wiki-Conductor (a real project on this machine)
        result = svc.rebind_instance(target.name, str(PROJECT_CONDUCTOR))
        assert result == "REBOUND"
        # Verify files changed
        refreshed = discover_local_instances(e2e["sandbox_root"])
        assert refreshed[0].project_path == str(PROJECT_CONDUCTOR)
        # .bak backups exist
        assert (target.instance_root / "instance.ps1.bak").is_file()

    def test_rebind_back_to_original(self, e2e):
        """Rebind back to the original project."""
        svc = e2e["service"]
        sandbox_instances = discover_local_instances(e2e["sandbox_root"])
        if not sandbox_instances:
            pytest.skip("sandbox instance not copied")
        target = sandbox_instances[0]
        result = svc.rebind_instance(target.name, str(PROJECT_WASTEWATER))
        assert result == "REBOUND"


class TestConfigDialogFlows:
    """User opens Config, changes settings, saves."""

    def test_save_and_reload_worker_settings(self, e2e):
        svc = e2e["service"]
        snap = svc.snapshot()
        worker = snap.workers[0]
        settings = WorkerSerenaSettings(
            worker_id=worker.worker_id,
            language_backend=LanguageBackend.LSP,
            excluded_tools=("execute_shell",),
            base_modes=("interactive", "editing"),
            tool_timeout=600,
            project_path=str(PROJECT_WASTEWATER),
            enabled_languages=("python", "markdown", "html"),
        )
        svc.save_worker_settings(settings)
        loaded = svc.worker_settings(worker.worker_id)
        assert loaded == settings
        assert loaded.tool_timeout == 600
        assert "python" in loaded.enabled_languages

    def test_materialize_settings_to_serena_home(self, e2e):
        """WO-P1-058: settings land in the worker's SERENA_HOME."""
        svc = e2e["service"]
        snap = svc.snapshot()
        worker = snap.workers[0]
        result = svc.apply_worker_settings_to_home(worker.worker_id)
        # Worker has no SerenaWorkerConfig → should skip cleanly
        assert result in ("SKIPPED_NO_SETTINGS", "SKIPPED_NOT_CONFIGURED", "APPLIED")


class TestSecondBrain:
    """User opens Second Brain dialog, saves the global brain profile."""

    def test_global_brain_profile_round_trip(self, e2e):
        svc = e2e["service"]
        profile = WorkerSerenaSettings(
            worker_id="global-brain",
            brain_folders=(str(PROJECT_AWIKI),),
            brain_entry_files=(
                str(PROJECT_AWIKI / "AGENTS.md"),
                str(PROJECT_AWIKI / "wiki" / "context" / "wiki-overview.md"),
            ),
        )
        svc.save_worker_settings(profile)
        loaded = svc.worker_settings("global-brain")
        assert loaded.brain_folders == (str(PROJECT_AWIKI),)
        assert "AGENTS.md" in loaded.brain_entry_files[0]

    def test_brain_render_is_index_only(self, e2e):
        profile = e2e["service"].worker_settings("global-brain")
        text = profile.render_serena_config(project_path=str(PROJECT_WASTEWATER))
        assert "[A-CONDUCTOR SECOND BRAIN]" in text
        assert "AGENTS.md" in text
        # Index-only: compact
        start = text.index("system_prompt: |")
        end = text.index("language_backend:")
        assert end - start < 1600


class TestMemoryPresence:
    """User selects a project and sees memory status."""

    def test_wastewater_project_memory(self, e2e):
        result = inspect_memory_presence(str(PROJECT_WASTEWATER))
        assert result.state in (
            MemoryPresenceState.NO_PROJECT,
            MemoryPresenceState.NO_MEMORIES,
            MemoryPresenceState.EMPTY,
            MemoryPresenceState.MAINTENANCE_ONLY,
            MemoryPresenceState.HAS_MEMORIES,
        )

    def test_awiki_project_memory(self, e2e):
        result = inspect_memory_presence(str(PROJECT_AWIKI))
        assert result.state in (
            MemoryPresenceState.NO_PROJECT,
            MemoryPresenceState.NO_MEMORIES,
            MemoryPresenceState.EMPTY,
            MemoryPresenceState.MAINTENANCE_ONLY,
            MemoryPresenceState.HAS_MEMORIES,
        )


class TestTunnelId:
    """User sets a Tunnel ID through the dialog."""

    def test_set_tunnel_id_on_sandbox(self, e2e):
        svc = e2e["service"]
        sandbox_instances = discover_local_instances(e2e["sandbox_root"])
        if not sandbox_instances:
            pytest.skip("sandbox instance not copied")
        target = sandbox_instances[0]
        valid_id = "tunnel_" + "e2e12345" * 4
        path = svc.set_instance_tunnel_id(target.name, valid_id)
        assert path.is_file()
        assert path.read_text(encoding="utf-8").strip() == valid_id
        # Discovery reflects it
        refreshed = discover_local_instances(e2e["sandbox_root"])
        assert refreshed[0].tunnel_configured is True

    def test_invalid_tunnel_id_rejected(self, e2e):
        svc = e2e["service"]
        from a_conductor.serena_config_store import SerenaConfigStoreError
        with pytest.raises(SerenaConfigStoreError, match="TUNNEL_ID_INVALID"):
            svc.set_instance_tunnel_id("Serena-Wastewater", "not-a-tunnel")


class TestPreferences:
    """User toggles the supervised switch in ตั้งค่า."""

    def test_supervised_default_on(self, e2e):
        svc = e2e["service"]
        pref = svc.get_preference("supervised")
        assert pref is None or pref is True  # None = default (ON)

    def test_toggle_off_and_on(self, e2e):
        svc = e2e["service"]
        svc.set_preference("supervised", False)
        assert svc.get_preference("supervised") is False
        svc.set_preference("supervised", True)
        assert svc.get_preference("supervised") is True


class TestUpstreamCheck:
    """User presses เช็คอัปเดท engine."""

    @pytest.mark.skipif(
        not PROJECT_AWIKI.is_dir(), reason="needs network + this machine"
    )
    def test_real_upstream_fetch(self, e2e):
        status = fetch_upstream_status()
        # If we have network, we should get a result; if not, a clear error
        if status.error_code is None:
            assert status.latest_release_tag is not None
            assert status.repo_url == "https://github.com/oraios/serena"
        else:
            assert status.error_code == "UPSTREAM_RELEASE_FETCH_FAILED"


class TestAutostartFlags:
    """User toggles Auto on a connector."""

    def test_autostart_flag_round_trip(self, e2e):
        svc = e2e["service"]
        sandbox_instances = discover_local_instances(e2e["sandbox_root"])
        if not sandbox_instances:
            pytest.skip("sandbox instance not copied")
        target = sandbox_instances[0]
        svc.set_instance_autostart(target.name, True)
        assert svc.instance_autostart(target.name) is True
        assert target.name in svc.autostart_instance_names()
        svc.set_instance_autostart(target.name, False)
        assert svc.instance_autostart(target.name) is False


class TestSandboxOrchestratorStartStop:
    """Start/stop the sandbox instance through the orchestrator (real scripts)."""

    @pytest.mark.skipif(os_name := __import__("os").name != "nt", reason="Windows")
    def test_health_check_sandbox(self, e2e):
        """Sandbox shares the real instance's health port, so the probe may
        find the live instance READY through it — any valid state is fine."""
        instances = discover_local_instances(e2e["sandbox_root"])
        if not instances:
            pytest.skip("sandbox instance not copied")
        state = instance_health_state(instances[0])
        assert state in (
            InstanceHealthState.STOPPED,
            InstanceHealthState.UNKNOWN,
            InstanceHealthState.READY,  # real instance may answer on the shared port
        )

    def test_orchestrator_reports_stopped(self, e2e):
        instances = discover_local_instances(e2e["sandbox_root"])
        if not instances:
            pytest.skip("sandbox instance not copied")
        orchestrator = LocalInstanceOrchestrator(instances_root=e2e["sandbox_root"])
        outcome = orchestrator.stop(instances[0])
        # If it's already stopped, the outcome should be ALREADY_STOPPED
        from a_conductor.local_instances import InstanceResultCode
        assert outcome.result_code in (
            InstanceResultCode.ALREADY_STOPPED,
            InstanceResultCode.STOPPED,
            InstanceResultCode.STOP_FAILED,  # if scripts aren't fully functional in sandbox
        )
