"""WO-P1-158 Prompt-3 RED — authority-bound production assembly.

The assembly must consume REAL typed accepted authority evidence — the
canonical WorkerLease record, the canonical ProviderAdmissionRecord, and the
provider-snapshot endpoint authority — and the worktree gate must compare
OBSERVED context against the LEASE authority, never a caller-supplied
expected pair. Truthy placeholders and None must FAIL CLOSED.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from a_conductor.claude_code_harness import TaskPacketFile
from a_conductor.provider_config_store import ProviderAdmissionRecord
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessRuntimeBinding,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderModelConfiguration,
    ProviderTrustClass,
    ProtocolFamily,
)
from a_conductor.registry import windows_worktree_key
from a_conductor.worker_lease import LeaseMutationIntent, WorkerLease
from a_conductor.zcode_production_assembly import (
    ZCodeAssemblyError,
    ZCodeExecutionAuthorities,
    assemble_zcode_execution,
)

BINDING = HarnessRuntimeBinding(
    harness_strategy=HarnessStrategy.ZCODE_APP_SERVER,
    runtime_provider_ref="zcode-runtime/glm-main",
    runtime_model_ref="zcode-runtime/glm-5.3",
)
ENDPOINT = ProviderEndpointConfig(endpoint_ref="zcode-desktop", base_url="http://127.0.0.1:1")
EXEC = r"C:\ZCode\ZCode.exe"
BUNDLE = r"C:\ZCode\resources\glm\zcode.cjs"


class Snapshot:
    def __init__(self, generation, profile, endpoint=ENDPOINT):
        self.generation = generation
        self.profile = profile
        self.endpoint = endpoint


def _profile():
    return ProviderConfiguration(
        provider_id="zcode-glm",
        display_name="ZCode GLM",
        provider_type="zcode-app-server",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="zcode-desktop",
        credential_ref="secret-ref:zcode-credential",
        trust_class=ProviderTrustClass.FIRST_PARTY,
        egress_boundary=EgressBoundary.LOCAL_MACHINE,
        harness_strategies=(HarnessStrategy.ZCODE_APP_SERVER,),
        max_concurrency=1,
        models=(ProviderModelConfiguration(
            model_id="glm-5.3",
            display_name="GLM 5.3",
            actor_capabilities=(ActorCapabilityEvidence("code", "DECLARED", "wo158"),),
            runtime_binding=BINDING,
        ),),
        enabled=True,
        schema_version="1.1.0",
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _lease(tmp_path: Path, **overrides) -> WorkerLease:
    fields = dict(
        lease_id="lease-0001",
        worker_id="a-worker-01",
        session_id="sess-1",
        task_id="WO-P1-158-ZRA1",
        project_id="zcode",
        runtime_id=None,
        worktree_key=windows_worktree_key(str(tmp_path)),
        branch="feat/wo-p1-158-zcode-zero-relay",
        expected_head="h" * 40,
        required_capabilities=("code",),
        allowed_scope=("src/a_conductor", "src/a_conductor/*"),
        forbidden_scope=("secrets", "secrets/*"),
        mutable_scope=("src/a_conductor/*",),
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at=_now().isoformat(),
        heartbeat_at=_now().isoformat(),
        lease_ttl_seconds=600,
        expires_at=(_now() + timedelta(minutes=10)).isoformat(),
        released_at=None,
        quarantined_at=None,
        quarantine_code=None,
        recovery_classification=None,
        recovery_evidence_ref=None,
        reconciled_at=None,
    )
    fields.update(overrides)
    return WorkerLease(**fields)


def _admission(**overrides) -> ProviderAdmissionRecord:
    fields = dict(
        admission_id="provider-admission-0001",
        provider_id="zcode-glm",
        execution_id="exec-pending",
        batch_id="batch-0001",
        acquired_at=_now(),
        expires_at=_now() + timedelta(minutes=10),
        status="ACTIVE",  # canonical SQLiteProviderConfigStore record state
        released_at=None,
        reconciled_at=None,
        configuration_generation=1,
    )
    fields.update(overrides)
    return ProviderAdmissionRecord(**fields)


def _packet(tmp_path: Path) -> TaskPacketFile:
    path = tmp_path / "task-packet.md"
    path.write_text("authority-bound task", encoding="utf-8")
    return TaskPacketFile(
        task_contract_ref="WO-P1-158-ZRA1",
        path=str(path),
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


class _Secrets:
    def resolve(self, ref):
        return "opaque"


class _Controller:
    def start(self, spec):
        raise AssertionError("no launch may occur in gate tests")


class _Obs:
    def read_pid_metadata(self, pid_path):
        raise AssertionError("no launch may occur in gate tests")

    def observe_process(self, *, pid, expected_executable_name, expected_profile_marker):
        raise AssertionError("no launch may occur in gate tests")


class _Store:
    def create(self, record):
        return record

    def get(self, execution_id):
        raise KeyError(execution_id)

    def find_by_fingerprint(self, fingerprint):
        return ()


_DEFAULT = object()


def _authorities(tmp_path: Path, *, lease=_DEFAULT, admission=_DEFAULT, snapshot=None,
                 repo_root=None, branch=None, head=None, dirty=False) -> ZCodeExecutionAuthorities:
    return ZCodeExecutionAuthorities(
        provider_snapshot=snapshot or Snapshot(1, _profile()),
        secret_resolver=_Secrets(),
        execution_store=_Store(),
        supervised_controller=_Controller(),
        supervised_observer=_Obs(),
        python_executable="python.exe",
        lease_evidence=_lease(tmp_path) if lease is _DEFAULT else lease,
        admission_evidence=_admission() if admission is _DEFAULT else admission,
        dispatch_batch_id="batch-0001",
        dispatch_execution_id="exec-pending",  # matches _admission default
        project_id="zcode",
        requested_mutable_scope=("src/a_conductor/zcode_runner.py",),
        worker_id="a-worker-01",
        repo_root=str(repo_root or tmp_path),
        branch=branch or "feat/wo-p1-158-zcode-zero-relay",
        head=head or "h" * 40,
        dirty=dirty,
    )


def _assemble(
    tmp_path: Path, *, authorities=None, base_url="http://127.0.0.1:1",
    secret_reference="secret-ref:zcode-credential", **kw
):
    return assemble_zcode_execution(
        authorities=authorities or _authorities(tmp_path, **kw),
        packet=_packet(tmp_path),
        model_id="glm-5.3",
        expected_generation=1,
        expected_base_url=base_url,
        secret_reference=secret_reference,
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )


# ---------------- lease authority (fail closed) ----------------

def test_lease_missing_fails_closed(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=None)
    assert e.value.code == "ZCODE_LEASE_ADMISSION_MISSING"


def test_fake_truthy_lease_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=object())  # truthy placeholder
    assert e.value.code == "ZCODE_LEASE_INVALID"


def test_truthy_boolean_lease_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=True)
    assert e.value.code == "ZCODE_LEASE_INVALID"


def test_wrong_worker_lease_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=_lease(tmp_path, worker_id="a-worker-99"))
    assert e.value.code == "ZCODE_LEASE_WORKER_MISMATCH"


def test_wrong_worktree_lease_rejected(tmp_path):
    other = tmp_path / "other-worktree"
    other.mkdir()
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=_lease(tmp_path, worktree_key=windows_worktree_key(str(other))))
    assert e.value.code == "ZCODE_LEASE_WORKTREE_MISMATCH"


def test_expired_lease_rejected(tmp_path):
    expired = (_now() - timedelta(seconds=1)).isoformat()
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=_lease(tmp_path, expires_at=expired))
    assert e.value.code == "ZCODE_LEASE_EXPIRED"


def test_released_lease_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=_lease(tmp_path, released_at=_now().isoformat()))
    assert e.value.code == "ZCODE_LEASE_NOT_ACTIVE"


def test_lease_task_identity_mismatch_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, lease=_lease(tmp_path, task_id="WO-P1-999-OTHER"))
    assert e.value.code == "ZCODE_LEASE_TASK_MISMATCH"


# ---------------- worktree gate: observed vs LEASE authority ----------------

def test_wrong_head_against_lease_authority_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, head="b" * 40)  # observed head drifts from lease
    assert e.value.code == "ZCODE_HEAD_DRIFT"


def test_branch_drift_against_lease_authority_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, branch="other/branch")
    assert e.value.code == "ZCODE_BRANCH_DRIFT"


def test_dirty_worktree_rejected_before_any_authority(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, dirty=True)
    assert e.value.code == "ZCODE_WORKTREE_DIRTY"


# ---------------- provider admission authority (fail closed) ----------------

def test_admission_missing_fails_closed(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=None)
    assert e.value.code == "ZCODE_PROVIDER_ADMISSION_MISSING"


def test_fake_truthy_admission_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=object())
    assert e.value.code == "ZCODE_ADMISSION_INVALID"


def test_wrong_provider_admission_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=_admission(provider_id="other-provider"))
    assert e.value.code == "ZCODE_ADMISSION_PROVIDER_MISMATCH"


def test_admission_not_active_rejected(tmp_path):
    """Canonical record states are ACTIVE/RELEASED/EXPIRED only; a non-ACTIVE
    record (e.g. EXPIRED state with future expiry, or any other value) can
    never authorize production dispatch."""
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=_admission(status="RELEASED"))
    assert e.value.code == "ZCODE_ADMISSION_NOT_ACTIVE"


def test_admission_released_record_rejected(tmp_path):
    from dataclasses import replace

    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=replace(_admission(), released_at=_now()))
    assert e.value.code == "ZCODE_ADMISSION_RELEASED"


def test_admission_generation_drift_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=_admission(configuration_generation=7))
    assert e.value.code == "ZCODE_ADMISSION_GENERATION_DRIFT"


def test_admission_expired_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, admission=_admission(expires_at=_now() - timedelta(seconds=1)))
    assert e.value.code == "ZCODE_ADMISSION_EXPIRED"


def test_wrong_model_rejected(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        assemble_zcode_execution(
            authorities=_authorities(tmp_path),
            packet=_packet(tmp_path),
            model_id="not-a-model",
            expected_generation=1,
            expected_base_url="http://127.0.0.1:1",
            secret_reference="secret-ref:zcode-credential",
            workspace=str(tmp_path), executable=EXEC, bundle_js=BUNDLE,
        )
    assert e.value.code == "ZCODE_RUNTIME_BINDING_MISSING"


# ---------------- endpoint authority ----------------

def test_caller_secret_reference_cannot_override_profile_credential_authority(tmp_path):
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, secret_reference="secret-ref:other-credential")
    assert e.value.code == "ZCODE_CREDENTIAL_REFERENCE_UNAUTHORIZED"


def test_ambiguous_custom_protocol_cannot_be_guessed_into_anthropic_runtime(tmp_path):
    from dataclasses import replace

    profile = replace(_profile(), protocol_family=ProtocolFamily.CUSTOM)
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, snapshot=Snapshot(1, profile))
    assert e.value.code == "ZCODE_RUNTIME_PROTOCOL_UNSUPPORTED"


def test_endpoint_drift_against_snapshot_authority_rejected(tmp_path):
    """The caller-requested route must match the provider-snapshot endpoint
    authority — caller-string-vs-caller-string authorization is gone."""
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, base_url="http://evil:9")
    assert e.value.code == "ZCODE_ENDPOINT_UNAUTHORIZED"


def test_endpoint_authority_missing_fails_closed(tmp_path):
    snapshot = Snapshot(1, _profile(), endpoint=None)
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble(tmp_path, snapshot=snapshot)
    assert e.value.code == "ZCODE_ENDPOINT_AUTHORITY_MISSING"


# ---------------- valid chain ----------------

def test_valid_exact_authority_chain_succeeds(tmp_path):
    runner = _assemble(tmp_path)
    assert runner is not None
    assert runner._task_packet.path


# ---------------- shared full-context assembly helper ----------------

def _assemble_full(tmp_path, *, dispatch_batch_id="batch-0001",
                   dispatch_execution_id="exec-bound-0001", project_id="zcode",
                   requested_mutable_scope=("src/a_conductor/zcode_runner.py",),
                   lease_overrides=None, admission_override=None,
                   base_url="http://127.0.0.1:1"):
    """Assembly with the complete trusted dispatch context bound (used by
    the final targeted repair matrix). The default admission carries the
    canonical ACTIVE state and its OWN execution binding; dispatch
    expectations vary independently in the tests."""
    lease = _lease(tmp_path, **(lease_overrides or {}))
    authorities = ZCodeExecutionAuthorities(
        provider_snapshot=Snapshot(1, _profile()),
        secret_resolver=_Secrets(),
        execution_store=_Store(),
        supervised_controller=_Controller(),
        supervised_observer=_Obs(),
        python_executable="python.exe",
        lease_evidence=lease,
        admission_evidence=admission_override if admission_override is not None
        else _admission(execution_id="exec-bound-0001"),
        dispatch_batch_id=dispatch_batch_id,
        dispatch_execution_id=dispatch_execution_id,
        project_id=project_id,
        requested_mutable_scope=requested_mutable_scope,
        worker_id="a-worker-01",
        repo_root=str(tmp_path),
        branch="feat/wo-p1-158-zcode-zero-relay",
        head="h" * 40,
        dirty=False,
    )
    return assemble_zcode_execution(
        authorities=authorities,
        packet=_packet(tmp_path),  # task ref matches the fixture lease task_id
        model_id="glm-5.3",
        expected_generation=1,
        expected_base_url=base_url,
        secret_reference="secret-ref:zcode-credential",
        workspace=str(tmp_path),
        executable=EXEC,
        bundle_js=BUNDLE,
    )
