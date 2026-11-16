"""WO-P1-767 / SFU26 card 05: safe logs + effective settings read models.

Pins the deny-by-default per-surface ALLOW/DENY law for
``a_conductor.settings_activity_projection``:

- field-set introspection: every ALLOW field projects, every DENY field
  (and every forbidden value class embedded in the fixtures) never appears
  anywhere in the emitted view;
- derived booleans replace denied refs (``credential_configured``,
  ``tunnel_binding_configured``); counts replace entries;
- drift typing: generation fields carried where the source carries them,
  typed ``NOT_CARRIED`` where it does not;
- path-shaped / secret-shaped / URL-shaped values smuggled into ALLOW
  fields are typed per-record rejections, never projected;
- malformed and raising duck records are typed rejections with zero
  exception escapes; valid neighbors survive;
- 256-row bounds with drop accounting; empty inputs typed; determinism;
- frozen + slots dataclasses with a pinned ``non_authoritative`` flag;
- module purity: stdlib + pure-type imports only;
- validator parity: the local ``_REF``/``_CODE``/deny-prefix semantics are
  decision-equal to ``a_conductor.web_api`` (both imported here).
"""

from __future__ import annotations

import ast
import dataclasses
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

import a_conductor.settings_activity_projection as sap
from a_conductor.settings_activity_projection import (
    SettingsActivityView,
    SettingsAdmissionRecord,
    SettingsControlActivityRecord,
    SettingsExecutionActivityRecord,
    SettingsHookActivityRecord,
    SettingsLocalReferenceRecord,
    SettingsMutationAuditRecord,
    SettingsNetworkPolicyRecord,
    SettingsProjectBindingRecord,
    SettingsProviderRecord,
    SettingsRecordRejection,
    SettingsRegistryRecord,
    SettingsSurfaceGroup,
    SettingsWorkerBrainRecord,
    SettingsWorkerRuntimeRecord,
    project_settings_activity_view,
)
from a_conductor.provider_operator_view import ProviderOperatorRow
from a_conductor.web_api import _CODE as WEB_CODE
from a_conductor.web_api import _REF as WEB_REF
from a_conductor.web_api import _text as web_text

NOW = datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)

SURFACES = (
    "providers",
    "hook_activity",
    "control_activity",
    "execution_activity",
    "mutation_audit",
    "worker_brain",
    "worker_runtime",
    "project_bindings",
    "local_references",
    "registry",
    "network_policy",
)

# Distinctive forbidden values embedded in fixtures; none may ever surface.
FORBIDDEN_BASE_URL = "https://internal.example:8443/v1"
FORBIDDEN_CREDENTIAL = "cred:sk-live-9f2c1e"
FORBIDDEN_SUMMARY = "operator free-text log line with secrets"
FORBIDDEN_REPO = "/srv/repos/private-app"
FORBIDDEN_WORKTREE = "/srv/worktrees/private-app-main"
FORBIDDEN_BRANCH = "feature/private-app-main"
FORBIDDEN_HOST_ENTRY = "internal-db.example.internal:5432"
FORBIDDEN_ROOT_PATH = "/srv/roots/private-app"
FORBIDDEN_WORKTREE_KEY = "wtkey-9f2c1e-secret"
FORBIDDEN_TUNNEL_REF = "tunnel:cf-9f2c1e-private"
FORBIDDEN_EVIDENCE_REF = "/srv/evidence/private-app/9f2c1e.json"
FORBIDDEN_GUARD_POLICY_REF = "policy:claim/secret-9f2c1e"
FORBIDDEN_PROJECT_PATH = "/Users/operator/private-app"
FORBIDDEN_FILE_PATH = "/Users/operator/private-app/NOTES.md"
FORBIDDEN_ALLOWED_ROOT = "/Users/operator"

ALL_FORBIDDEN = (
    FORBIDDEN_BASE_URL,
    FORBIDDEN_CREDENTIAL,
    FORBIDDEN_SUMMARY,
    FORBIDDEN_REPO,
    FORBIDDEN_WORKTREE,
    FORBIDDEN_BRANCH,
    FORBIDDEN_HOST_ENTRY,
    FORBIDDEN_ROOT_PATH,
    FORBIDDEN_WORKTREE_KEY,
    FORBIDDEN_TUNNEL_REF,
    FORBIDDEN_EVIDENCE_REF,
    FORBIDDEN_GUARD_POLICY_REF,
    FORBIDDEN_PROJECT_PATH,
    FORBIDDEN_FILE_PATH,
    FORBIDDEN_ALLOWED_ROOT,
)

SHA = "b" * 40


def _project_strings(node: object) -> set[str]:
    """Every string carried anywhere inside an emitted structure."""
    out: set[str] = set()
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        for field in fields(node):
            out |= _project_strings(getattr(node, field.name))
    elif isinstance(node, dict):
        for key, value in node.items():
            out |= _project_strings(key)
            out |= _project_strings(value)
    elif isinstance(node, (list, tuple, frozenset, set)):
        for item in node:
            out |= _project_strings(item)
    elif isinstance(node, str):
        out.add(node)
    return out


def assert_forbidden_absent(node: object) -> None:
    seen = _project_strings(node)
    for forbidden in ALL_FORBIDDEN:
        for projected in seen:
            assert forbidden not in projected, (
                f"forbidden value {forbidden!r} leaked inside {projected!r}"
            )


def rejection_codes(group: SettingsSurfaceGroup) -> list[str]:
    return [rejection.code for rejection in group.rejections]


# ---------------------------------------------------------------------------
# Fixture records (duck-typed injected inputs)
# ---------------------------------------------------------------------------


def make_provider_row(**overrides) -> ProviderOperatorRow:
    values = dict(
        provider_id="provider-primary",
        display_name="Primary Provider",
        provider_type="openai-compatible",
        enabled=True,
        configured=True,
        runtime_ready=True,
        readiness_reason="READY",
        task_authorization="NOT_EVALUATED",
        models=(),
        harness_strategies=(),
        trust_class="FIRST_PARTY",
        egress_boundary="LOCAL_MACHINE",
        max_concurrency=4,
        configuration_generation=7,
        health="AVAILABLE",
        observed_at=NOW,
        observation_age_seconds=1.5,
        provenance="PROBE",
        latency_ms=120,
        quota=None,
    )
    values.update(overrides)
    return ProviderOperatorRow(**values)


def make_provider_input(**overrides) -> SimpleNamespace:
    values = dict(
        row=make_provider_row(),
        protocol_family="https",
        schema_version="provider-config/v1",
        endpoint_ref="endpoint:primary",
        admission=SimpleNamespace(
            admission_id="adm-1",
            status="ACTIVE",
            acquired_at="2026-11-16T10:00:00+00:00",
            expires_at="2026-11-16T15:00:00+00:00",
            released_at=None,
            reconciled_at=None,
            configuration_generation=7,
        ),
        credential_ref=FORBIDDEN_CREDENTIAL,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_hook_envelope(**overrides) -> SimpleNamespace:
    values = dict(
        event_id="hk-" + "a" * 32,
        event_type="HOOK_COMPLETED",
        hook_class="PreToolUse",
        phase="pre",
        domain="tool",
        action="execute",
        occurred_at="2026-11-16T11:59:00+00:00",
        source="serena",
        source_version="1.2.3",
        device_id="dev-1",
        host_os="darwin",
        privacy_class="PUBLIC",
        lane_id="lane-1",
        task_id="task-1",
        work_order="WO-P1-767",
        task_topology="CONTROL_PLANE_ONLY",
        head_sha=SHA,
        claim_ref="claim-1",
        execution_id="exec-1",
        harness_id="harness-1",
        model_id="model-1",
        effort="high",
        state="SUCCEEDED",
        duration_ms=25,
        blocker_code=None,
        sequence=3,
        dedupe_key="hk-dedupe-1",
        correlation_id="corr-1",
        causation_id="hk-" + "b" * 32,
        evidence_refs=("ev-1",),
        evidence_digest="c" * 64,
        command_digest="d" * 64,
        command_ref="cmd-1",
        markers=("SAFE",),
        # DENY-carrying fields that must never project:
        summary=FORBIDDEN_SUMMARY,
        justification=FORBIDDEN_SUMMARY,
        repo=FORBIDDEN_REPO,
        worktree=FORBIDDEN_WORKTREE,
        branch=FORBIDDEN_BRANCH,
        authority_repo=FORBIDDEN_REPO,
        execution_repo=FORBIDDEN_REPO,
        adapter=SimpleNamespace(
            adapter_id="adapter-1",
            adapter_version="1.0.0",
            contract_version="hook-envelope/v1",
            redaction_policy="DENY_BY_DEFAULT",
            supports_sequence=True,
        ),
        guard=SimpleNamespace(
            failure_policy="FAIL_CLOSED",
            security_scope="TOOL",
            authority_scope="OPERATOR",
            policy_ref=FORBIDDEN_GUARD_POLICY_REF,
        ),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_control_event(**overrides) -> SimpleNamespace:
    values = dict(
        event_id="event-1",
        event_type="WORKER_STARTED",
        worker_id="a-worker-01",
        project_id="proj-1",
        recorded_at="2026-11-16T10:00:00+00:00",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_execution_event(**overrides) -> SimpleNamespace:
    values = dict(
        event_id="eev-1",
        execution_id="exec-1",
        sequence_no=1,
        event_type="CREATED",
        transport_state="STOPPED",
        execution_state="RUNNING",
        pid=4321,
        exit_code=0,
        started_at="2026-11-16T10:00:00+00:00",
        finished_at="2026-11-16T10:00:05+00:00",
        recorded_at="2026-11-16T10:00:06+00:00",
        evidence_ref=FORBIDDEN_EVIDENCE_REF,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_mutation_record(**overrides) -> SimpleNamespace:
    values = dict(
        worker_id="a-worker-01",
        action="UPDATE_SETTINGS",
        at="2026-11-16T10:00:00+00:00",
        target="/srv/private/target",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_brain_settings(**overrides) -> SimpleNamespace:
    values = dict(
        worker_id="a-worker-01",
        language_backend="LSP",
        tool_timeout=240,
        excluded_tools=("web",),
        included_optional_tools=("git",),
        fixed_tools=("read",),
        base_modes=("builtin",),
        enabled_languages=("python",),
        brain_folders=(FORBIDDEN_PROJECT_PATH, "/Users/operator/brain-b"),
        brain_entry_files=("INDEX.md",),
        # value-bearing fields that must never project:
        project_path=FORBIDDEN_PROJECT_PATH,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_runtime_config(**overrides) -> SimpleNamespace:
    values = dict(
        worker_id="a-worker-01",
        runtime_id="serena-1",
        instance_root="/srv/instances/w1",
        serena_home="/srv/serena",
        health_host="127.0.0.1",
        health_port=8123,
        tunnel_binding_ref=FORBIDDEN_TUNNEL_REF,
        credential_ref=None,
        runtime_executable_ref="/srv/bin/serena",
        profile_template_ref="/srv/tmpl/serena",
        run_dir="/srv/run/w1",
        log_dir="/srv/log/w1",
        startup_timeout_seconds=30,
        stop_timeout_seconds=10,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_project_binding(**overrides) -> SimpleNamespace:
    values = dict(
        project_id="proj-1",
        worktree_path=FORBIDDEN_WORKTREE,
        identity_policy="READ_ONLY_DISCOVERY",
        expected_branch="main",
        expected_head=SHA,
        mutation_allowed=False,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_reference_group(**overrides) -> SimpleNamespace:
    values = dict(
        reference_id="ref-1",
        paths=[FORBIDDEN_FILE_PATH] * 5,
        roots=[FORBIDDEN_ALLOWED_ROOT] * 2,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_registry_entry(**overrides) -> SimpleNamespace:
    values = dict(
        project_id="proj-1",
        display_name="Project One",
        worker_id="a-worker-01",
        worker_display_name="Worker One",
        runtime_id="serena-1",
        state="READY",
        assignment_id="asg-1",
        mutation_allowed=True,
        root_path=FORBIDDEN_ROOT_PATH,
        worktree_key=FORBIDDEN_WORKTREE_KEY,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_network_policy(**overrides) -> SimpleNamespace:
    values = dict(
        privacy_class="PUBLIC",
        network_policy="ALLOWLISTED",
        secret_access=False,
        network_allowlist=(FORBIDDEN_HOST_ENTRY, "fallback.example:443"),
        reason_code="POLICY_ALLOWLISTED",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class LyingStr(str):
    """Two-faced str subclass whose iteration raises."""

    def __iter__(self):
        raise RuntimeError("lying iteration")

    def __len__(self):
        return 3


class Raising:
    """Attribute read that always raises."""

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "_name", name)

    def __getattr__(self, name: str):
        raise RuntimeError(f"raising probe: {name}")


# ---------------------------------------------------------------------------
# Module existence, purity, structure
# ---------------------------------------------------------------------------


class TestModuleLaw:
    def test_module_source_purity(self) -> None:
        source = Path(sap.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        allowed_stdlib = {
            "__future__",
            "re",
            "dataclasses",
            "datetime",
            "typing",
        }
        allowed_relative = {"provider_operator_view"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    assert root in allowed_stdlib, f"non-pure import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:
                    root = (node.module or "").split(".")[0]
                    assert root in allowed_stdlib, f"non-pure import: {node.module}"
                else:
                    assert (node.module or "") in allowed_relative, (
                        f"unexpected relative import: {node.module}"
                    )

    @pytest.mark.parametrize(
        "record_type",
        [
            SettingsActivityView,
            SettingsSurfaceGroup,
            SettingsRecordRejection,
            SettingsProviderRecord,
            SettingsAdmissionRecord,
            SettingsHookActivityRecord,
            SettingsControlActivityRecord,
            SettingsExecutionActivityRecord,
            SettingsMutationAuditRecord,
            SettingsWorkerBrainRecord,
            SettingsWorkerRuntimeRecord,
            SettingsProjectBindingRecord,
            SettingsLocalReferenceRecord,
            SettingsRegistryRecord,
            SettingsNetworkPolicyRecord,
        ],
    )
    def test_records_frozen_slots_non_authoritative(self, record_type) -> None:
        assert record_type.__dataclass_params__.frozen is True
        assert hasattr(record_type, "__slots__")
        non_auth = [
            field for field in fields(record_type) if field.name == "non_authoritative"
        ]
        assert len(non_auth) == 1
        assert non_auth[0].init is False

    def test_view_is_non_authoritative_and_has_eleven_groups(self) -> None:
        view = project_settings_activity_view()
        assert view.non_authoritative is True
        for name in SURFACES:
            group = getattr(view, name)
            assert isinstance(group, SettingsSurfaceGroup)
            assert group.non_authoritative is True
            assert group.state == "OK"
            assert group.records == ()
            assert group.rejections == ()

    def test_now_must_be_tz_aware_when_given(self) -> None:
        with pytest.raises(ValueError):
            project_settings_activity_view(
                control_events=(make_control_event(),),
                now=datetime(2026, 11, 16, 12, 0, 0),
            )

    def test_empty_inputs_are_typed_not_degraded(self) -> None:
        view = project_settings_activity_view(now=NOW)
        for name in SURFACES:
            group = getattr(view, name)
            assert group.state == "OK"
            assert group.records == ()
            assert group.dropped_count == 0
            assert group.truncated is False

    def test_non_sequence_input_degrades_group(self) -> None:
        view = project_settings_activity_view(control_events=None)
        group = view.control_activity
        assert group.state == "DEGRADED"
        assert group.reason == "SURFACE_INPUT_INVALID"
        assert group.records == ()

    def test_determinism(self) -> None:
        kwargs = dict(
            providers=(make_provider_input(),),
            hook_records=(make_hook_envelope(),),
            control_events=(make_control_event(),),
            execution_events=(make_execution_event(),),
            mutation_audits=(make_mutation_record(),),
            worker_brain_settings=(make_brain_settings(),),
            worker_runtime_configs=(make_runtime_config(),),
            project_bindings=(make_project_binding(),),
            local_reference_groups=(make_reference_group(),),
            registry_entries=(make_registry_entry(),),
            network_policies=(make_network_policy(),),
            now=NOW,
        )
        assert project_settings_activity_view(**kwargs) == project_settings_activity_view(
            **kwargs
        )


# ---------------------------------------------------------------------------
# Provider surface
# ---------------------------------------------------------------------------


class TestProviderSurface:
    def test_allow_fields_project_and_row_is_reused(self) -> None:
        view = project_settings_activity_view(providers=(make_provider_input(),))
        group = view.providers
        assert group.state == "OK"
        (record,) = group.records
        assert isinstance(record, SettingsProviderRecord)
        assert isinstance(record.row, ProviderOperatorRow)
        assert record.row.provider_id == "provider-primary"
        assert record.row.display_name == "Primary Provider"
        assert record.row.provider_type == "openai-compatible"
        assert record.row.enabled is True
        assert record.row.configured is True
        assert record.row.runtime_ready is True
        assert record.row.readiness_reason == "READY"
        assert record.row.task_authorization == "NOT_EVALUATED"
        assert record.row.harness_strategies == ()
        assert record.row.trust_class == "FIRST_PARTY"
        assert record.row.egress_boundary == "LOCAL_MACHINE"
        assert record.row.max_concurrency == 4
        assert record.row.configuration_generation == 7
        assert record.row.health == "AVAILABLE"
        assert record.row.observed_at == NOW
        assert record.row.observation_age_seconds == 1.5
        assert record.row.provenance == "PROBE"
        assert record.row.latency_ms == 120
        assert record.protocol_family == "https"
        assert record.schema_version == "provider-config/v1"
        assert record.endpoint_ref == "endpoint:primary"
        assert_forbidden_absent(group)

    def test_admission_metadata_projects_with_generation(self) -> None:
        (record,) = project_settings_activity_view(
            providers=(make_provider_input(),)
        ).providers.records
        admission = record.admission
        assert isinstance(admission, SettingsAdmissionRecord)
        assert admission.admission_id == "adm-1"
        assert admission.status == "ACTIVE"
        assert admission.acquired_at == "2026-11-16T10:00:00+00:00"
        assert admission.expires_at == "2026-11-16T15:00:00+00:00"
        assert admission.released_at is None
        assert admission.reconciled_at is None
        assert admission.configuration_generation == 7

    def test_credential_ref_derived_boolean_only(self) -> None:
        (record,) = project_settings_activity_view(
            providers=(make_provider_input(),)
        ).providers.records
        assert record.credential_configured is True
        assert not any(
            field.name == "credential_ref" for field in fields(SettingsProviderRecord)
        )
        assert FORBIDDEN_CREDENTIAL not in _project_strings(record)

    def test_credential_absent_means_not_configured(self) -> None:
        input_record = make_provider_input()
        del input_record.credential_ref
        (record,) = project_settings_activity_view(providers=(input_record,)).providers.records
        assert record.credential_configured is False

    def test_blank_credential_ref_means_not_configured(self) -> None:
        (record,) = project_settings_activity_view(
            providers=(make_provider_input(credential_ref="   "),)
        ).providers.records
        assert record.credential_configured is False

    def test_row_type_mismatch_is_typed_rejection(self) -> None:
        group = project_settings_activity_view(
            providers=(make_provider_input(row=object()),)
        ).providers
        assert group.records == ()
        assert rejection_codes(group) == ["RECORD_TYPE_UNSUPPORTED"]

    def test_path_shaped_endpoint_ref_is_typed_rejection(self) -> None:
        group = project_settings_activity_view(
            providers=(make_provider_input(endpoint_ref="/srv/endpoints/primary"),)
        ).providers
        assert group.records == ()
        (rejection,) = group.rejections
        assert rejection.code == "SAFE_FIELD_PATH_SHAPED"
        assert rejection.field == "endpoint_ref"

    def test_secret_shaped_endpoint_ref_is_typed_rejection(self) -> None:
        group = project_settings_activity_view(
            providers=(make_provider_input(endpoint_ref="sk-live-abcdef"),)
        ).providers
        assert rejection_codes(group) == ["SAFE_FIELD_SECRET_SHAPED"]

    def test_url_shaped_schema_version_is_typed_rejection(self) -> None:
        group = project_settings_activity_view(
            providers=(make_provider_input(schema_version=FORBIDDEN_BASE_URL),)
        ).providers
        assert rejection_codes(group) == ["SAFE_FIELD_URL_SHAPED"]

    def test_raising_row_attribute_is_contained(self) -> None:
        group = project_settings_activity_view(
            providers=(make_provider_input(admission=Raising("admission_id")),)
        ).providers
        assert rejection_codes(group) == ["RECORD_ATTRIBUTE_UNREADABLE"]


# ---------------------------------------------------------------------------
# Hook activity surface
# ---------------------------------------------------------------------------


class TestHookActivitySurface:
    def test_allow_fields_project_and_deny_fields_never(self) -> None:
        (record,) = project_settings_activity_view(
            hook_records=(make_hook_envelope(),)
        ).hook_activity.records
        assert isinstance(record, SettingsHookActivityRecord)
        allowed_names = {field.name for field in fields(SettingsHookActivityRecord)}
        for name in (
            "event_id",
            "event_type",
            "hook_class",
            "phase",
            "domain",
            "action",
            "occurred_at",
            "source",
            "source_version",
            "device_id",
            "host_os",
            "privacy_class",
            "lane_id",
            "task_id",
            "work_order",
            "task_topology",
            "head_sha",
            "claim_ref",
            "execution_id",
            "harness_id",
            "model_id",
            "effort",
            "state",
            "duration_ms",
            "blocker_code",
            "sequence",
            "dedupe_key",
            "correlation_id",
            "causation_id",
            "evidence_refs",
            "evidence_digest",
            "command_digest",
            "command_ref",
            "markers",
            "adapter",
            "guard",
        ):
            assert name in allowed_names, f"ALLOW field missing: {name}"
        assert record.event_id == "hk-" + "a" * 32
        assert record.head_sha == SHA
        assert record.duration_ms == 25
        assert record.sequence == 3
        assert record.evidence_refs == ("ev-1",)
        assert record.markers == ("SAFE",)
        for denied in (
            "summary",
            "justification",
            "repo",
            "worktree",
            "branch",
            "authority_repo",
            "execution_repo",
            "policy_ref",
        ):
            assert denied not in allowed_names, f"DENY field present: {denied}"
        assert record.guard.failure_policy == "FAIL_CLOSED"
        assert record.guard.security_scope == "TOOL"
        assert record.guard.authority_scope == "OPERATOR"
        assert record.adapter.adapter_id == "adapter-1"
        assert record.adapter.supports_sequence is True
        assert_forbidden_absent(record)

    def test_denied_fields_are_never_read(self) -> None:
        envelope = make_hook_envelope(
            summary=property(lambda self: (_ for _ in ()).throw(RuntimeError("boom"))),
            guard=SimpleNamespace(
                failure_policy="FAIL_CLOSED",
                security_scope="TOOL",
                authority_scope="OPERATOR",
                policy_ref=property(
                    lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
                ),
            ),
        )
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.guard.failure_policy == "FAIL_CLOSED"

    def test_path_shaped_allow_field_is_rejected(self) -> None:
        envelope = make_hook_envelope(task_id=FORBIDDEN_WORKTREE)
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert group.records == ()
        (rejection,) = group.rejections
        assert rejection.code == "SAFE_FIELD_PATH_SHAPED"
        assert rejection.field == "task_id"

    def test_windows_drive_path_shaped_is_rejected(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(command_ref=r"C:\ops\cmd-1"),)
        ).hook_activity
        assert rejection_codes(group) == ["SAFE_FIELD_PATH_SHAPED"]

    def test_dotdot_relative_path_shaped_is_rejected(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(source="safe/../../escape"),)
        ).hook_activity
        assert rejection_codes(group) == ["SAFE_FIELD_PATH_SHAPED"]

    def test_secret_shaped_allow_field_is_rejected(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(model_id="sk-proj-abcdef"),)
        ).hook_activity
        assert rejection_codes(group) == ["SAFE_FIELD_SECRET_SHAPED"]

    def test_url_shaped_allow_field_is_rejected(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(claim_ref=FORBIDDEN_BASE_URL),)
        ).hook_activity
        assert rejection_codes(group) == ["SAFE_FIELD_URL_SHAPED"]

    def test_naive_occurred_at_is_rejected(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(occurred_at="2026-11-16T11:59:00"),)
        ).hook_activity
        assert rejection_codes(group) == ["TIMESTAMP_NAIVE"]

    def test_head_sha_shape_is_enforced(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(head_sha="nothex"),)
        ).hook_activity
        assert rejection_codes(group) == ["HEAD_SHA_INVALID"]

    def test_evidence_digest_shape_is_enforced(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(evidence_digest="not-a-digest!"),)
        ).hook_activity
        assert rejection_codes(group) == ["DIGEST_INVALID"]

    def test_malformed_adapter_is_per_record_rejection(self) -> None:
        envelope = make_hook_envelope(adapter=Raising("adapter_id"))
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert group.records == ()
        assert rejection_codes(group) == ["RECORD_ATTRIBUTE_UNREADABLE"]

    def test_guard_with_raising_policy_ref_still_projects(self) -> None:
        envelope = make_hook_envelope(
            guard=SimpleNamespace(
                failure_policy="FAIL_CLOSED",
                security_scope="TOOL",
                authority_scope="OPERATOR",
            )
        )
        envelope.guard.__dict__["policy_ref"] = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("boom"))
        )
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert group.state == "OK"

    def test_invalid_adapter_nested_field_is_rejected(self) -> None:
        envelope = make_hook_envelope(
            adapter=SimpleNamespace(
                adapter_id="/abs/adapter",
                adapter_version="1.0.0",
                contract_version="hook-envelope/v1",
                redaction_policy="DENY_BY_DEFAULT",
                supports_sequence=True,
            )
        )
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert rejection_codes(group) == ["SAFE_FIELD_PATH_SHAPED"]

    def test_neighbor_survives_sibling_rejection(self) -> None:
        good = make_hook_envelope()
        bad = make_hook_envelope(event_id="/absolute/path", event_id_extra=None)
        group = project_settings_activity_view(hook_records=(bad, good)).hook_activity
        assert len(group.records) == 1
        assert len(group.rejections) == 1

    def test_missing_required_field_is_rejected(self) -> None:
        envelope = make_hook_envelope()
        del envelope.event_id
        group = project_settings_activity_view(hook_records=(envelope,)).hook_activity
        assert rejection_codes(group) == ["RECORD_FIELD_MISSING"]

    def test_two_faced_string_is_rejected_not_escaped(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(task_id=LyingStr("tk-1")),)
        ).hook_activity
        assert rejection_codes(group) == ["IDENTIFIER_INVALID"]


# ---------------------------------------------------------------------------
# Control / execution / mutation audit surfaces
# ---------------------------------------------------------------------------


class TestControlSurface:
    def test_five_payload_free_fields_only(self) -> None:
        (record,) = project_settings_activity_view(
            control_events=(make_control_event(),)
        ).control_activity.records
        assert isinstance(record, SettingsControlActivityRecord)
        names = {field.name for field in fields(SettingsControlActivityRecord)}
        assert names == {
            "event_id",
            "event_type",
            "worker_id",
            "project_id",
            "recorded_at",
            "non_authoritative",
        }
        assert record.event_id == "event-1"
        assert record.recorded_at == "2026-11-16T10:00:00+00:00"

    def test_payload_key_is_ignored_not_projected(self) -> None:
        envelope = make_control_event(payload={"secret": FORBIDDEN_CREDENTIAL})
        view = project_settings_activity_view(control_events=(envelope,))
        assert view.control_activity.state == "OK"
        assert FORBIDDEN_CREDENTIAL not in _project_strings(view)


class TestExecutionSurface:
    def test_allow_fields_project_evidence_ref_never(self) -> None:
        (record,) = project_settings_activity_view(
            execution_events=(make_execution_event(),)
        ).execution_activity.records
        assert isinstance(record, SettingsExecutionActivityRecord)
        names = {field.name for field in fields(record)}
        assert {
            "event_id",
            "execution_id",
            "sequence_no",
            "event_type",
            "transport_state",
            "execution_state",
            "pid",
            "exit_code",
            "started_at",
            "finished_at",
            "recorded_at",
        } <= names
        assert "evidence_ref" not in names
        assert record.sequence_no == 1
        assert record.pid == 4321
        assert record.exit_code == 0
        assert FORBIDDEN_EVIDENCE_REF not in _project_strings(record)

    def test_raising_evidence_ref_is_never_read(self) -> None:
        event = make_execution_event(
            evidence_ref=property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
        )
        group = project_settings_activity_view(execution_events=(event,)).execution_activity
        assert group.state == "OK"
        assert len(group.records) == 1

    def test_invalid_pid_is_rejected(self) -> None:
        group = project_settings_activity_view(
            execution_events=(make_execution_event(pid=True),)
        ).execution_activity
        assert rejection_codes(group) == ["FIELD_TYPE_INVALID"]


class TestMutationAuditSurface:
    def test_worker_identity_action_at_only(self) -> None:
        (record,) = project_settings_activity_view(
            mutation_audits=(make_mutation_record(),)
        ).mutation_audit.records
        assert isinstance(record, SettingsMutationAuditRecord)
        assert record.actor_id == "a-worker-01"
        assert record.actor_kind == "worker"
        assert record.action == "UPDATE_SETTINGS"
        assert record.at == "2026-11-16T10:00:00+00:00"
        assert FORBIDDEN_REPO not in _project_strings(record)

    def test_connector_identity_supported(self) -> None:
        record_input = SimpleNamespace(
            connector_id="connector-1", action="RENAME", at="2026-11-16T10:00:00+00:00"
        )
        (record,) = project_settings_activity_view(
            mutation_audits=(record_input,)
        ).mutation_audit.records
        assert record.actor_id == "connector-1"
        assert record.actor_kind == "connector"

    def test_neither_identity_is_missing_rejection(self) -> None:
        group = project_settings_activity_view(
            mutation_audits=(SimpleNamespace(action="X", at="2026-11-16T10:00:00+00:00"),)
        ).mutation_audit
        assert rejection_codes(group) == ["RECORD_FIELD_MISSING"]

    def test_identity_value_is_not_a_path(self) -> None:
        group = project_settings_activity_view(
            mutation_audits=(make_mutation_record(target=FORBIDDEN_FILE_PATH),)
        ).mutation_audit
        assert group.state == "OK"
        assert FORBIDDEN_FILE_PATH not in _project_strings(group)


# ---------------------------------------------------------------------------
# Effective settings surfaces
# ---------------------------------------------------------------------------


class TestWorkerBrainSurface:
    def test_allow_fields_and_counts_replace_entries(self) -> None:
        (record,) = project_settings_activity_view(
            worker_brain_settings=(make_brain_settings(),)
        ).worker_brain.records
        assert isinstance(record, SettingsWorkerBrainRecord)
        names = {field.name for field in fields(record)}
        assert {
            "worker_id",
            "language_backend",
            "tool_timeout",
            "excluded_tools",
            "included_optional_tools",
            "fixed_tools",
            "base_modes",
            "enabled_languages",
            "brain_folder_count",
            "brain_entry_count",
            "settings_version",
        } <= names
        assert record.brain_folder_count == 2
        assert record.brain_entry_count == 1
        assert "brain_folders" not in names
        assert "brain_entry_files" not in names
        assert "project_path" not in names
        assert record.settings_version == "NOT_CARRIED"
        assert FORBIDDEN_PROJECT_PATH not in _project_strings(record)

    def test_brain_entry_values_are_counts_only(self) -> None:
        view = project_settings_activity_view(
            worker_brain_settings=(
                make_brain_settings(brain_entry_files=(FORBIDDEN_FILE_PATH, "B.md")),
            )
        )
        (record,) = view.worker_brain.records
        assert record.brain_entry_count == 2
        assert FORBIDDEN_FILE_PATH not in _project_strings(view)

    def test_non_sequence_brain_folders_is_count_invalid(self) -> None:
        group = project_settings_activity_view(
            worker_brain_settings=(make_brain_settings(brain_folders="not-a-tuple"),)
        ).worker_brain
        assert rejection_codes(group) == ["COUNT_SEQUENCE_INVALID"]

    def test_drift_typing_not_carried_has_no_generation(self) -> None:
        (record,) = project_settings_activity_view(
            worker_brain_settings=(make_brain_settings(),)
        ).worker_brain.records
        names = {field.name for field in fields(record)}
        assert "generation" not in names
        assert "configuration_generation" not in names
        assert record.settings_version == "NOT_CARRIED"


class TestWorkerRuntimeSurface:
    def test_allow_fields_and_derived_tunnel_boolean(self) -> None:
        (record,) = project_settings_activity_view(
            worker_runtime_configs=(make_runtime_config(),)
        ).worker_runtime.records
        assert isinstance(record, SettingsWorkerRuntimeRecord)
        names = {field.name for field in fields(record)}
        assert {
            "worker_id",
            "runtime_id",
            "health_port",
            "startup_timeout_seconds",
            "stop_timeout_seconds",
            "tunnel_binding_configured",
        } <= names
        assert record.health_port == 8123
        assert record.startup_timeout_seconds == 30
        assert record.stop_timeout_seconds == 10
        assert record.tunnel_binding_configured is True
        for denied in (
            "instance_root",
            "serena_home",
            "run_dir",
            "log_dir",
            "health_host",
            "runtime_executable_ref",
            "profile_template_ref",
            "tunnel_binding_ref",
            "credential_ref",
        ):
            assert denied not in names, f"DENY field present: {denied}"
        assert FORBIDDEN_TUNNEL_REF not in _project_strings(record)

    def test_tunnel_ref_absent_means_not_configured(self) -> None:
        input_record = make_runtime_config()
        del input_record.tunnel_binding_ref
        (record,) = project_settings_activity_view(
            worker_runtime_configs=(input_record,)
        ).worker_runtime.records
        assert record.tunnel_binding_configured is False

    def test_invalid_health_port_is_rejected(self) -> None:
        group = project_settings_activity_view(
            worker_runtime_configs=(make_runtime_config(health_port=99999),)
        ).worker_runtime
        assert rejection_codes(group) == ["FIELD_TYPE_INVALID"]


class TestProjectBindingSurface:
    def test_allow_fields_project_worktree_path_never(self) -> None:
        (record,) = project_settings_activity_view(
            project_bindings=(make_project_binding(),)
        ).project_bindings.records
        assert isinstance(record, SettingsProjectBindingRecord)
        names = {field.name for field in fields(record)}
        assert {
            "project_id",
            "identity_policy",
            "expected_branch",
            "expected_head",
            "mutation_allowed",
        } <= names
        assert "worktree_path" not in names
        assert record.expected_branch == "main"
        assert record.expected_head == SHA
        assert record.mutation_allowed is False
        assert FORBIDDEN_WORKTREE not in _project_strings(record)

    def test_expected_head_shape_is_enforced(self) -> None:
        group = project_settings_activity_view(
            project_bindings=(make_project_binding(expected_head="HEAD"),)
        ).project_bindings
        assert rejection_codes(group) == ["HEAD_SHA_INVALID"]


class TestLocalReferenceSurface:
    def test_reference_id_and_counts_only(self) -> None:
        (record,) = project_settings_activity_view(
            local_reference_groups=(make_reference_group(),)
        ).local_references.records
        assert isinstance(record, SettingsLocalReferenceRecord)
        names = {field.name for field in fields(record)}
        assert names == {"reference_id", "reference_count", "root_count", "non_authoritative"}
        assert record.reference_id == "ref-1"
        assert record.reference_count == 5
        assert record.root_count == 2
        assert FORBIDDEN_FILE_PATH not in _project_strings(record)
        assert FORBIDDEN_ALLOWED_ROOT not in _project_strings(record)

    def test_non_sequence_paths_is_rejected(self) -> None:
        group = project_settings_activity_view(
            local_reference_groups=(make_reference_group(paths=7),)
        ).local_references
        assert rejection_codes(group) == ["COUNT_SEQUENCE_INVALID"]

    def test_raising_paths_is_unreadable(self) -> None:
        class RaisingPathsRecord:
            reference_id = "ref-1"
            roots: tuple = ()

            @property
            def paths(self):
                raise RuntimeError("raising paths probe")

        group = project_settings_activity_view(
            local_reference_groups=(RaisingPathsRecord(),)
        ).local_references
        assert rejection_codes(group) == ["RECORD_ATTRIBUTE_UNREADABLE"]


class TestRegistrySurface:
    def test_allow_fields_project_denied_identifiers_never(self) -> None:
        (record,) = project_settings_activity_view(
            registry_entries=(make_registry_entry(),)
        ).registry.records
        assert isinstance(record, SettingsRegistryRecord)
        names = {field.name for field in fields(record)}
        assert {
            "project_id",
            "display_name",
            "worker_id",
            "worker_display_name",
            "runtime_id",
            "state",
            "assignment_id",
            "mutation_allowed",
        } <= names
        assert "root_path" not in names
        assert "worktree_key" not in names
        assert record.worker_display_name == "Worker One"
        assert record.mutation_allowed is True
        assert FORBIDDEN_ROOT_PATH not in _project_strings(record)
        assert FORBIDDEN_WORKTREE_KEY not in _project_strings(record)

    def test_path_shaped_display_name_is_rejected(self) -> None:
        group = project_settings_activity_view(
            registry_entries=(make_registry_entry(display_name=FORBIDDEN_ROOT_PATH),)
        ).registry
        assert rejection_codes(group) == ["SAFE_FIELD_PATH_SHAPED"]


class TestNetworkPolicySurface:
    def test_metadata_and_count_only(self) -> None:
        (record,) = project_settings_activity_view(
            network_policies=(make_network_policy(),)
        ).network_policy.records
        assert isinstance(record, SettingsNetworkPolicyRecord)
        names = {field.name for field in fields(record)}
        assert {
            "privacy_class",
            "network_policy",
            "secret_access",
            "network_allowlist_count",
            "reason_code",
        } <= names
        assert record.network_allowlist_count == 2
        assert record.reason_code == "POLICY_ALLOWLISTED"
        assert record.secret_access is False
        assert FORBIDDEN_HOST_ENTRY not in _project_strings(record)

    def test_reason_code_is_closed_vocabulary(self) -> None:
        group = project_settings_activity_view(
            network_policies=(make_network_policy(reason_code="MADE_UP_CODE"),)
        ).network_policy
        assert rejection_codes(group) == ["REASON_CODE_INVALID"]


# ---------------------------------------------------------------------------
# Bounds, escape containment, parity
# ---------------------------------------------------------------------------


class TestBoundsAndContainment:
    def test_row_bound_256_with_drop_accounting(self) -> None:
        records = tuple(
            make_hook_envelope(event_id=f"hk-{index:06d}") for index in range(300)
        )
        group = project_settings_activity_view(hook_records=records).hook_activity
        assert group.state == "OK"
        assert len(group.records) == 256
        assert group.dropped_count == 44
        assert group.truncated is True
        assert group.reason == "FRAME_ROW_LIMIT_EXCEEDED"

    def test_rejection_bound_with_drop_accounting(self) -> None:
        records = tuple(
            make_hook_envelope(event_id="/abs/path", event_id_seq=i) for i in range(300)
        )
        group = project_settings_activity_view(hook_records=records).hook_activity
        assert len(group.rejections) == 256
        assert group.truncated is True

    def test_no_exception_escapes_from_raising_records(self) -> None:
        records = (
            Raising("anything"),
            make_hook_envelope(event_id=LyingStr("hk-x")),
            make_hook_envelope(guard=None),
            None,
            42,
            "plain-string-record",
        )
        group = project_settings_activity_view(hook_records=records).hook_activity
        assert group.state == "OK"
        assert len(group.records) == 1
        assert group.records[0].guard is None
        assert len(group.rejections) == 5


class TestValidatorParity:
    def test_regex_shapes_equal_web_api(self) -> None:
        assert sap._CODE_RE.pattern == WEB_CODE.pattern
        assert sap._REF_RE.pattern == WEB_REF.pattern

    def test_deny_prefixes_equal_web_api_semantics(self) -> None:
        expected = ("sk-", "bearer", "token", "password", "secret")
        assert tuple(sap._DENY_PREFIXES) == expected
        corpus = [
            "sk-abc123",
            "Bearer token",
            "TOKEN-VALUE",
            "password:hunter2",
            "secret/ref",
            "clean-ref-1",
            "another_clean_ref",
            "PASSWORDS",  # prefix "password" + suffix: web_api rejects too
        ]
        for value in corpus:
            web_rejects = False
            try:
                web_text(value)
            except Exception:
                web_rejects = True
            local_rejects = sap._deny_prefixed(value)
            assert web_rejects == local_rejects, f"parity drift for {value!r}"

    def test_ref_shape_decisions_equal_web_api(self) -> None:
        # The local ref law = web_api's charset/length/deny-prefix law plus
        # the strictly stronger fleet path-shape law, so every web_api
        # rejection is a local rejection; path-shaped values web accepts
        # (e.g. drive-shaped "a:b") are local-only rejections, pinned below.
        corpus = [
            "abc",
            "a:b",
            "A_1",
            "abc.def",
            "has space",
            "a/../b",
            "/abs",
            "~/home",
            "C:\\x",
            "x" * 200,
            "",
            ".hidden",
            "-lead",
            "ümlaut",
            "hk-" + "a" * 32,
        ]
        for value in corpus:
            web_rejects = False
            try:
                web_text(value)
            except Exception:
                web_rejects = True
            local_rejects = sap._check_ref(value) is not None
            if web_rejects:
                assert local_rejects, f"local law weaker than web_api for {value!r}"

    def test_local_path_law_stricter_than_web_api(self) -> None:
        # Fleet path-shape law additions over web_api's charset law.
        for value in ("~/home", "a/../b", r"C:\x", "/abs", "a:b"):
            web_accepts = True
            try:
                web_text(value)
            except Exception:
                web_accepts = False
            assert sap._check_ref(value) is not None, value
            assert sap._path_shaped(value) is True, value
            if web_accepts:
                continue


# ---------------------------------------------------------------------------
# Security repair round 1 (independent review F1-F5, WO-P1-767)
# ---------------------------------------------------------------------------


LEAK_ATTACK = "/srv/private/leak-path"
EVIL_REPR = "<EVIL-REPR-LAUNDRY-999999>"


class TwoFacedStr(str):
    """Benign ``__iter__`` view; attacker-controlled ``__str__``.

    The probed iteration view is the truth the projection must emit;
    ``str(value)`` on the original object returns the attack text.
    """

    def __new__(cls, benign: str, attack: str = LEAK_ATTACK):
        self = super().__new__(cls, benign)
        self.attack = attack
        return self

    def __str__(self) -> str:
        return self.attack


class EvilInt(int):
    """Hostile int subclass laundering attacker text through ``__repr__``."""

    def __repr__(self) -> str:
        return EVIL_REPR


class MidIterHostileList(list):
    """A real ``list`` whose ``__iter__`` raises mid-iteration."""

    def __init__(self, items, raise_after: int) -> None:
        super().__init__(items)
        self.raise_after = raise_after

    def __iter__(self):
        def generate():
            for count, item in enumerate(list.__iter__(self)):
                if count == self.raise_after:
                    raise RuntimeError("hostile mid-iteration raise")
                yield item

        return generate()


class TestTwoFacedEmissionLaw:
    """F1: emission must carry the probed iteration view, never str(duck)."""

    def test_two_faced_task_id_emits_iteration_view(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(task_id=TwoFacedStr("tk-1")),)
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.task_id == "tk-1"
        assert type(record.task_id) is str
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)

    def test_two_faced_markers_emits_iteration_view(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(markers=(TwoFacedStr("SAFE"),)),)
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.markers == ("SAFE",)
        assert all(type(entry) is str for entry in record.markers)
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)

    def test_two_faced_evidence_digest_emits_iteration_view(self) -> None:
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(evidence_digest=TwoFacedStr("c" * 64)),)
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.evidence_digest == "c" * 64
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)

    def test_two_faced_endpoint_ref_emits_iteration_view(self) -> None:
        group = project_settings_activity_view(
            providers=(
                make_provider_input(endpoint_ref=TwoFacedStr("endpoint:primary")),
            )
        ).providers
        assert group.state == "OK"
        (record,) = group.records
        assert record.endpoint_ref == "endpoint:primary"
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)

    def test_two_faced_display_name_emits_iteration_view(self) -> None:
        group = project_settings_activity_view(
            registry_entries=(
                make_registry_entry(display_name=TwoFacedStr("Project One")),
            )
        ).registry
        assert group.state == "OK"
        (record,) = group.records
        assert record.display_name == "Project One"
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)


class TestIterableContainmentLaw:
    """F2: a hostile list subclass raising mid-``__iter__`` is contained."""

    @pytest.mark.parametrize("raise_after, kept_records", [(0, 0), (1, 1)])
    def test_hostile_iteration_degrades_group_without_escape(
        self, raise_after: int, kept_records: int
    ) -> None:
        hostile = MidIterHostileList(
            [make_control_event(event_id=f"event-{i}") for i in range(3)],
            raise_after,
        )
        group = project_settings_activity_view(
            control_events=hostile
        ).control_activity
        assert group.state == "DEGRADED"
        assert group.reason == "SURFACE_INPUT_INVALID"
        assert len(group.records) == kept_records
        assert group.truncated is False


class TestIntCoercionLaw:
    """F3: hostile int-subclass ``__repr__`` cannot launder via reprs."""

    def test_evil_int_pid_emits_plain_int(self) -> None:
        group = project_settings_activity_view(
            execution_events=(make_execution_event(pid=EvilInt(4321)),)
        ).execution_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.pid == 4321
        assert type(record.pid) is int
        assert EVIL_REPR not in repr(record)
        assert EVIL_REPR not in repr(group)

    def test_evil_int_duration_and_sequence_emit_plain_ints(self) -> None:
        group = project_settings_activity_view(
            hook_records=(
                make_hook_envelope(duration_ms=EvilInt(25), sequence=EvilInt(3)),
            )
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.duration_ms == 25
        assert type(record.duration_ms) is int
        assert record.sequence == 3
        assert type(record.sequence) is int
        assert EVIL_REPR not in repr(record)

    def test_evil_int_sequence_no_emits_plain_int(self) -> None:
        group = project_settings_activity_view(
            execution_events=(make_execution_event(sequence_no=EvilInt(1)),)
        ).execution_activity
        (record,) = group.records
        assert record.sequence_no == 1
        assert type(record.sequence_no) is int
        assert EVIL_REPR not in repr(record)

    def test_evil_int_generation_and_port_emit_plain_ints(self) -> None:
        admission = SimpleNamespace(
            admission_id="adm-1",
            status="ACTIVE",
            acquired_at="2026-11-16T10:00:00+00:00",
            expires_at="2026-11-16T15:00:00+00:00",
            released_at=None,
            reconciled_at=None,
            configuration_generation=EvilInt(7),
        )
        (provider,) = project_settings_activity_view(
            providers=(make_provider_input(admission=admission),)
        ).providers.records
        assert provider.admission.configuration_generation == 7
        assert type(provider.admission.configuration_generation) is int
        (runtime,) = project_settings_activity_view(
            worker_runtime_configs=(make_runtime_config(health_port=EvilInt(8123)),)
        ).worker_runtime.records
        assert runtime.health_port == 8123
        assert type(runtime.health_port) is int
        assert EVIL_REPR not in repr(provider)
        assert EVIL_REPR not in repr(runtime)


def _raising_property(name: str) -> property:
    def raise_attr(self) -> None:
        raise RuntimeError(f"raising deny probe: {name}")

    return property(raise_attr)


class TestDenyNonAccessRound1:
    """F5: the six remaining DENY fields are never read (raising fixture)."""

    @pytest.mark.parametrize(
        "deny_name",
        [
            "repo",
            "worktree",
            "branch",
            "authority_repo",
            "execution_repo",
            "justification",
        ],
    )
    def test_deny_field_raising_never_read(self, deny_name: str) -> None:
        envelope = make_hook_envelope()
        values = dict(envelope.__dict__)
        values[deny_name] = _raising_property(deny_name)
        record_cls = type("HookDenyRaisingEnvelope", (), values)
        group = project_settings_activity_view(
            hook_records=(record_cls(),)
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        assert record.task_id == "task-1"
        assert group.rejections == ()


class TestWholeViewRenderPin:
    """F5: repr()/str() of the whole view leak nothing forbidden."""

    def test_whole_view_repr_and_str_contain_no_forbidden_values(self) -> None:
        view = project_settings_activity_view(
            providers=(
                make_provider_input(endpoint_ref=TwoFacedStr("endpoint:primary")),
            ),
            hook_records=(
                make_hook_envelope(
                    task_id=TwoFacedStr("tk-1"),
                    markers=(TwoFacedStr("SAFE"),),
                    evidence_digest=TwoFacedStr("c" * 64),
                    duration_ms=EvilInt(25),
                ),
            ),
            control_events=(make_control_event(),),
            execution_events=(
                make_execution_event(pid=EvilInt(4321), sequence_no=EvilInt(1)),
            ),
            mutation_audits=(make_mutation_record(),),
            worker_brain_settings=(make_brain_settings(),),
            worker_runtime_configs=(make_runtime_config(),),
            project_bindings=(make_project_binding(),),
            local_reference_groups=(make_reference_group(),),
            registry_entries=(
                make_registry_entry(display_name=TwoFacedStr("Project One")),
            ),
            network_policies=(make_network_policy(),),
            now=NOW,
        )
        for rendered in (repr(view), str(view)):
            for forbidden in (*ALL_FORBIDDEN, LEAK_ATTACK, EVIL_REPR):
                assert forbidden not in rendered, forbidden
        assert_forbidden_absent(view)


# ---------------------------------------------------------------------------
# Security repair round 2 (adjudication ADJ-1, WO-P1-767): a datetime
# subclass with benign tzinfo/utcoffset but an attacker-controlled
# ``isoformat()`` must never launder its text into emitted stamps.
# ---------------------------------------------------------------------------


class LyingStamp(datetime):
    """Benign tz-aware datetime view; attacker-controlled ``isoformat()``."""

    def isoformat(self, sep: str = "T", timespec: str = "auto") -> str:
        return LEAK_ATTACK


class RaisingComponentStamp(datetime):
    """Two-faced stamp whose ``year`` attribute read raises."""

    @property
    def year(self):
        raise RuntimeError("raising year probe")


class TestStampIsoformatLaundering:
    def test_lying_isoformat_occurred_at_emits_real_iso_string(self) -> None:
        lying = LyingStamp(2026, 11, 16, 11, 59, 0, tzinfo=timezone.utc)
        assert lying.isoformat() == LEAK_ATTACK
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(occurred_at=lying),)
        ).hook_activity
        assert group.state == "OK"
        (record,) = group.records
        expected = datetime(
            2026, 11, 16, 11, 59, 0, tzinfo=timezone.utc
        ).isoformat()
        assert record.occurred_at == expected
        assert record.occurred_at != LEAK_ATTACK
        assert LEAK_ATTACK not in _project_strings(record)
        assert LEAK_ATTACK not in repr(group)

    def test_lying_isoformat_admission_stamp_emits_real_iso_string(self) -> None:
        lying = LyingStamp(2026, 11, 16, 10, 0, 0, tzinfo=timezone.utc)
        input_record = make_provider_input(
            admission=SimpleNamespace(
                admission_id="adm-1",
                status="ACTIVE",
                acquired_at=lying,
                expires_at="2026-11-16T15:00:00+00:00",
                released_at=None,
                reconciled_at=None,
                configuration_generation=7,
            )
        )
        group = project_settings_activity_view(providers=(input_record,)).providers
        assert group.state == "OK"
        (record,) = group.records
        assert record.admission is not None
        expected = datetime(
            2026, 11, 16, 10, 0, 0, tzinfo=timezone.utc
        ).isoformat()
        assert record.admission.acquired_at == expected
        assert record.admission.acquired_at != LEAK_ATTACK
        assert LEAK_ATTACK not in _project_strings(record)

    def test_raising_stamp_component_is_typed_rejection(self) -> None:
        lying = RaisingComponentStamp(2026, 11, 16, tzinfo=timezone.utc)
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(occurred_at=lying),)
        ).hook_activity
        assert group.records == ()
        (rejection,) = group.rejections
        assert rejection.code == "TIMESTAMP_INVALID"
        assert rejection.field == "occurred_at"

    def test_lying_component_values_never_project(self) -> None:
        lying = RaisingComponentStamp(2026, 11, 16, tzinfo=timezone.utc)
        group = project_settings_activity_view(
            hook_records=(make_hook_envelope(occurred_at=lying),)
        ).hook_activity
        assert LEAK_ATTACK not in _project_strings(group)
