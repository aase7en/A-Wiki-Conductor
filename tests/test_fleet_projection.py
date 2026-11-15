"""Fleet/work identity read projection tests (WO-P1-763 / SFU26 card 03).

Pins the pure composer contract over injected records:

- per-source-class typed record groups with exact field sets (exclusion law:
  claim worktree/scope raw values, instance project_path/health_address/
  instance_root, tunnel ids, pids and naive stamps never project);
- app-session labels never promote to fleet-ready; remote devices stay a
  single typed UNKNOWN constant; claim expiry stays EXPIRY_UNKNOWN;
- cross-source joins are provable-only; divergences become typed
  IDENTITY_CONFLICT records with the divergent fields named;
- dedup is per-class first-wins with duplicate_count; malformed injected
  records become per-record typed rejections whose neighbors survive; all
  duck-typed attribute access is wrapped (raising attrs never escape);
- every emitted dataclass is frozen+slots with a pinned init=False
  non_authoritative=True flag; the module stays pure (no clock/env/network/
  provider imports) and deterministic.
"""

from __future__ import annotations

import dataclasses
import re
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

from a_conductor.cockpit_projection import CockpitLeaseObservation
from a_conductor.fleet_projection import (
    FleetAppSessionRecord,
    FleetClaimRecord,
    FleetIdentityConflict,
    FleetIdentityLink,
    FleetIdentitySummary,
    FleetLeaseRecord,
    FleetLocalInstanceRecord,
    FleetRecordGroup,
    FleetRecordRejection,
    FleetRemoteDeviceRecord,
    FleetView,
    project_fleet_view,
)

MODULE_SOURCE = (
    Path(__file__).resolve().parents[1] / "src" / "a_conductor" / "fleet_projection.py"
).read_text(encoding="utf-8")

SHA_A = "a" * 40
SHA_B = "b" * 40
FORBIDDEN_WORKTREE = "/Users/operator/repo/.worktrees/wt-secret-1"
FORBIDDEN_SCOPE_ENTRY = "src/a_conductor/secret_internal_module.py"
FORBIDDEN_PROJECT_PATH = "C:\\Apps\\A-Conductor"
FORBIDDEN_HEALTH_ADDRESS = "127.0.0.1:18011"
FORBIDDEN_INSTANCE_ROOT = "C:\\Apps\\A-Conductor\\instances\\worker-1"
FORBIDDEN_TUNNEL_ID = "tunnel_" + "f" * 32
FORBIDDEN_PID = 424242
NAIVE_STAMP = "2026-11-15T10:00:00"
AWARE_STAMP = "2026-11-15T10:00:00+00:00"
NOW = datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)

EMITTED_RECORD_CLASSES = (
    FleetClaimRecord,
    FleetLeaseRecord,
    FleetAppSessionRecord,
    FleetLocalInstanceRecord,
    FleetRemoteDeviceRecord,
    FleetIdentityLink,
    FleetIdentityConflict,
)


class _Binding:
    """Duck-typed stand-in for awiki ClaimTaskBinding (raw path values inside)."""

    def __init__(
        self,
        *,
        task_id: str = "task-1",
        claim_id: str = "awiki-claim-" + "a" * 20,
        generation: int = 3,
        repository: str = "aase7en/A-Wiki",
        worktree: str = FORBIDDEN_WORKTREE,
        branch: str = "feat/wo763-fleet-identity",
        head_sha: str = SHA_A,
        agent: str = "a-worker-01",
        scope: tuple[str, ...] = (FORBIDDEN_SCOPE_ENTRY,),
    ) -> None:
        self.task_id = task_id
        self.claim_id = claim_id
        self.generation = generation
        self.repository = repository
        self.worktree = worktree
        self.branch = branch
        self.head_sha = head_sha
        self.agent = agent
        self.scope = scope


class _Session:
    """Duck-typed web session record ({id, display_name/name, created_at})."""

    def __init__(
        self,
        *,
        session_id: str,
        label: str,
        created_at: str = AWARE_STAMP,
        id_field: str = "id",
    ) -> None:
        self.session_id = session_id
        self.label = label
        self.created_at = created_at
        self.id_field = id_field


class _Worker(_Session):
    pid = FORBIDDEN_PID


class _Connector(_Session):
    name = "connector-name"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = "STOPPED"


class _Instance:
    """Duck-typed local instance plus separately observed health."""

    pid = FORBIDDEN_PID

    def __init__(
        self,
        *,
        name: str = "sunday-worker-1",
        project_path: str = FORBIDDEN_PROJECT_PATH,
        health_address: str = FORBIDDEN_HEALTH_ADDRESS,
        instance_root: str = FORBIDDEN_INSTANCE_ROOT,
        tunnel_configured: bool = True,
        tunnel_suffix: str = "abcd",
        health: object = "READY",
    ) -> None:
        self.name = name
        self.project_path = project_path
        self.health_address = health_address
        self.instance_root = instance_root
        self.tunnel_configured = tunnel_configured
        self.tunnel_suffix = tunnel_suffix
        self.health = health


class _RaisingAttr:
    """Injected record whose every attribute read raises (card-08/09 P2)."""

    @property
    def session_id(self) -> str:
        raise RuntimeError("boom")

    @property
    def label(self) -> str:
        raise RuntimeError("boom")

    @property
    def created_at(self) -> str:
        raise RuntimeError("boom")

    @property
    def state(self) -> str:
        raise RuntimeError("boom")

    @property
    def claim_id(self) -> str:
        raise RuntimeError("boom")

    @property
    def task_id(self) -> str:
        raise RuntimeError("boom")

    @property
    def generation(self) -> int:
        raise RuntimeError("boom")

    @property
    def repository(self) -> str:
        raise RuntimeError("boom")

    @property
    def branch(self) -> str:
        raise RuntimeError("boom")

    @property
    def head_sha(self) -> str:
        raise RuntimeError("boom")

    @property
    def agent(self) -> str:
        raise RuntimeError("boom")

    @property
    def scope(self) -> tuple[str, ...]:
        raise RuntimeError("boom")


class _LiarTzinfo(tzinfo):
    """Timezone carrier whose utcoffset read raises (liar time evidence)."""

    def utcoffset(self, dt):  # type: ignore[override]
        raise RuntimeError("liar utcoffset")

    def dst(self, dt):  # type: ignore[override]
        raise RuntimeError("liar dst")

    def tzname(self, dt):  # type: ignore[override]
        raise RuntimeError("liar tzname")


class _FlipFlopTzinfo(tzinfo):
    """Two-faced tzinfo: aware-looking on early calls, raising on a later one."""

    def __init__(self, raise_on: int) -> None:
        self.calls = 0
        self.raise_on = raise_on

    def utcoffset(self, dt):  # type: ignore[override]
        self.calls += 1
        if self.calls >= self.raise_on:
            raise RuntimeError("flip-flop utcoffset")
        return timedelta(0)

    def dst(self, dt):  # type: ignore[override]
        return timedelta(0)

    def tzname(self, dt):  # type: ignore[override]
        return "UTC"


class _RaisingStr(str):
    """Two-faced str subclass whose __iter__/__len__ raise on read."""

    def __iter__(self):  # type: ignore[override]
        raise RuntimeError("liar __iter__")

    def __len__(self):  # type: ignore[override]
        raise RuntimeError("liar __len__")


class _LiarEnumText:
    """Enum-like health carrier whose ``value`` read raises."""

    @property
    def value(self) -> str:
        raise RuntimeError("liar enum value")


# ---------------------------------------------------------------------------
# Purity, structure, and type-level law
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    [
        "import time",
        "time.monotonic",
        "time.time",
        "datetime.now",
        "utcnow",
        "environ",
        "getenv",
        "socket",
        "urllib",
        "requests",
        "httpx",
        "subprocess",
        "pathlib",
        "Path(",
        "open(",
        "__import__",
        "eval(",
        "exec(",
        "from .web_api",
        "from .local_instances",
        "from .awiki_claim_reader",
        "import web_api",
        "import local_instances",
        "import awiki_claim_reader",
    ],
)
def test_module_source_has_no_clock_env_network_provider_imports(forbidden: str) -> None:
    assert forbidden not in MODULE_SOURCE


def test_module_imports_cockpit_lease_observation_only() -> None:
    assert "from .cockpit_projection import CockpitLeaseObservation" in MODULE_SOURCE


@pytest.mark.parametrize("record_class", EMITTED_RECORD_CLASSES)
def test_emitted_records_are_frozen_slots_with_pinned_non_authoritative(
    record_class: type,
) -> None:
    assert record_class.__slots__ or dataclasses.fields(record_class)
    fields = {field.name: field for field in dataclasses.fields(record_class)}
    assert "non_authoritative" in fields
    flag = fields["non_authoritative"]
    assert flag.init is False
    assert flag.default is True
    with pytest.raises(TypeError):
        record_class(non_authoritative=False)  # type: ignore[misc]


@pytest.mark.parametrize("record_class", EMITTED_RECORD_CLASSES)
def test_emitted_records_are_frozen(record_class: type) -> None:
    assert record_class.__dataclass_params__.frozen is True


def test_emitted_record_field_names_carry_no_forbidden_surfaces() -> None:
    # "scope" is excluded as a name only for claim records; app-session
    # records carry the WO-mandated "scope" label pinned to "app-session".
    forbidden_names = {
        "worktree",
        "project_path",
        "health_address",
        "instance_root",
        "tunnel_id",
        "pid",
    }
    for record_class in EMITTED_RECORD_CLASSES:
        names = {field.name for field in dataclasses.fields(record_class)}
        overlap = names & forbidden_names
        assert not overlap, (record_class.__name__, overlap)
    claim_names = {field.name for field in dataclasses.fields(FleetClaimRecord)}
    assert "scope" not in claim_names


# ---------------------------------------------------------------------------
# Claim records: safe handles only, EXPIRY_UNKNOWN, scope as count
# ---------------------------------------------------------------------------


def test_claim_record_projects_safe_handles_and_scope_count_only() -> None:
    view = project_fleet_view(claim_bindings=(_Binding(),))
    group = view.claims
    assert group.available is True
    assert group.provenance == "AWIKI_CLAIM_BINDING"
    assert group.reason is None
    assert group.rejections == ()
    assert group.duplicate_count == 0
    assert group.truncated is False
    assert len(group.records) == 1
    record = group.records[0]
    assert isinstance(record, FleetClaimRecord)
    assert record.claim_id == "awiki-claim-" + "a" * 20
    assert record.task_id == "task-1"
    assert record.agent == "a-worker-01"
    assert record.generation == 3
    assert record.branch == "feat/wo763-fleet-identity"
    assert record.head_sha == SHA_A
    assert record.repository == "aase7en/A-Wiki"
    assert record.scope_count == 1
    assert record.expiry == "EXPIRY_UNKNOWN"
    assert record.provenance == "AWIKI_CLAIM_BINDING"
    assert record.non_authoritative is True


def test_claim_record_never_carries_worktree_scope_paths_or_naive_stamps() -> None:
    binding = _Binding()
    view = project_fleet_view(claim_bindings=(binding,), now=NOW)
    record = view.claims.records[0]
    flattened = repr(record)
    assert FORBIDDEN_WORKTREE not in flattened
    assert FORBIDDEN_SCOPE_ENTRY not in flattened
    assert NAIVE_STAMP not in flattened
    assert binding.worktree == FORBIDDEN_WORKTREE
    assert binding.scope == (FORBIDDEN_SCOPE_ENTRY,)
    assert record.scope_count == 1


def test_claim_expiry_stays_expiry_unknown_even_with_now() -> None:
    view = project_fleet_view(claim_bindings=(_Binding(),), now=NOW)
    assert view.claims.records[0].expiry == "EXPIRY_UNKNOWN"
    assert not any(
        value == "STALE" for record in view.claims.records for value in (record.expiry,)
    )


def test_claim_generation_must_be_non_negative_int() -> None:
    bad = _Binding(generation=-1)
    view = project_fleet_view(claim_bindings=(bad,))
    assert view.claims.records == ()
    assert [rejection.code for rejection in view.claims.rejections] == [
        "GENERATION_INVALID"
    ]
    assert view.claims.rejections[0].field == "generation"


def test_claim_scope_must_be_a_sequence_not_a_string() -> None:
    bad = _Binding(scope="src/a_conductor/one.py")
    view = project_fleet_view(claim_bindings=(bad,))
    assert view.claims.records == ()
    assert [rejection.code for rejection in view.claims.rejections] == [
        "SCOPE_SEQUENCE_INVALID"
    ]


# ---------------------------------------------------------------------------
# Lease records: pass-through of CockpitLeaseObservation
# ---------------------------------------------------------------------------


def _lease(
    *,
    lease_id: str = "lease-1",
    worker_id: str = "a-worker-01",
    branch: str | None = "feat/wo763-fleet-identity",
    expected_head: str | None = SHA_A,
    health: str | None = "ACTIVE",
    available: bool = True,
    reason: str | None = None,
) -> CockpitLeaseObservation:
    return CockpitLeaseObservation(
        available=available,
        provenance="DURABLE_EXECUTION_RECORD" if available else None,
        reason=reason,
        lease_id=lease_id,
        worker_id=worker_id,
        worktree_key=FORBIDDEN_WORKTREE,
        branch=branch,
        expected_head=expected_head,
        health=health,
        acquired_at=AWARE_STAMP,
        heartbeat_at=AWARE_STAMP,
        expires_at="2026-11-15T18:00:00+00:00",
    )


def test_lease_record_is_pass_through_of_injected_observation() -> None:
    observation = _lease()
    view = project_fleet_view(lease_observations=(observation,))
    group = view.leases
    assert group.available is True
    assert group.provenance == "COCKPIT_LEASE_OBSERVATION"
    assert group.reason is None
    assert len(group.records) == 1
    record = group.records[0]
    assert isinstance(record, FleetLeaseRecord)
    assert record.observation is observation
    assert record.available is True
    assert record.provenance == "DURABLE_EXECUTION_RECORD"
    assert record.reason is None
    assert record.duplicate_count == 0


def test_lease_observation_fields_are_not_duplicated_onto_record() -> None:
    names = {field.name for field in dataclasses.fields(FleetLeaseRecord)}
    assert "worktree_key" not in names
    assert "expected_head" not in names
    assert "expires_at" not in names


def test_unavailable_lease_observation_still_projects_with_reason() -> None:
    observation = CockpitLeaseObservation.unavailable("LEASE_SOURCE_UNAVAILABLE")
    view = project_fleet_view(lease_observations=(observation,))
    record = view.leases.records[0]
    assert record.available is False
    assert record.reason == "LEASE_SOURCE_UNAVAILABLE"
    assert record.observation is observation


def test_lease_with_blank_lease_id_is_typed_rejection() -> None:
    view = project_fleet_view(lease_observations=(_lease(lease_id="   "),))
    assert view.leases.records == ()
    assert [rejection.code for rejection in view.leases.rejections] == [
        "IDENTIFIER_BLANK"
    ]
    assert view.leases.rejections[0].field == "lease_id"


# ---------------------------------------------------------------------------
# App sessions: app-session scope, never fleet-ready
# ---------------------------------------------------------------------------


def test_worker_session_projects_app_session_label_and_unknown_state() -> None:
    worker = _Worker(session_id="a-worker-01", label="Alpha Worker")
    view = project_fleet_view(worker_sessions=(worker,), now=NOW)
    group = view.worker_sessions
    assert group.available is True
    assert group.provenance == "APP_SESSION_RECORD"
    assert len(group.records) == 1
    record = group.records[0]
    assert isinstance(record, FleetAppSessionRecord)
    assert record.kind == "worker"
    assert record.session_id == "a-worker-01"
    assert record.label == "Alpha Worker"
    assert record.scope == "app-session"
    assert record.state == "UNKNOWN"
    assert record.created_at == AWARE_STAMP
    assert record.age_seconds == 7200.0
    assert record.staleness == "AVAILABLE"


def test_connector_session_projects_recorded_stopped_state() -> None:
    connector = _Connector(session_id="conn-abcd1234", label="Sunday Connector")
    view = project_fleet_view(connector_sessions=(connector,))
    record = view.connector_sessions.records[0]
    assert record.kind == "connector"
    assert record.session_id == "conn-abcd1234"
    assert record.label == "Sunday Connector"
    assert record.scope == "app-session"
    assert record.state == "STOPPED"
    assert record.age_seconds is None
    assert record.staleness is None


@pytest.mark.parametrize("vocabulary", ["READY", "FLEET_READY", "fleet-ready"])
def test_session_records_never_carry_fleet_ready_vocabulary(vocabulary: str) -> None:
    view = project_fleet_view(
        worker_sessions=(_Worker(session_id="a-worker-01", label="Alpha"),),
        connector_sessions=(_Connector(session_id="conn-abcd1234", label="Sunday"),),
        now=NOW,
    )
    for group in (view.worker_sessions, view.connector_sessions):
        for record in group.records:
            assert vocabulary not in repr(record)
            assert record.scope == "app-session"
    assert not any(
        field.name in {"available", "fleet_ready", "ready"}
        for field in dataclasses.fields(FleetAppSessionRecord)
    )


def test_worker_session_negative_age_is_unknown_staleness() -> None:
    worker = _Worker(
        session_id="a-worker-01",
        label="Alpha",
        created_at="2026-11-15T13:00:00+00:00",
    )
    view = project_fleet_view(worker_sessions=(worker,), now=NOW)
    record = view.worker_sessions.records[0]
    assert record.age_seconds == -3600.0
    assert record.staleness == "UNKNOWN"


def test_naive_session_timestamp_is_typed_rejection_neighbors_survive() -> None:
    good = _Worker(session_id="a-worker-02", label="Beta")
    bad = _Worker(session_id="a-worker-01", label="Alpha", created_at=NAIVE_STAMP)
    view = project_fleet_view(worker_sessions=(bad, good), now=NOW)
    assert [record.session_id for record in view.worker_sessions.records] == [
        "a-worker-02"
    ]
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "TIMESTAMP_NAIVE"
    ]
    assert view.worker_sessions.rejections[0].field == "created_at"
    assert view.worker_sessions.rejections[0].source_index == 0


def test_session_with_missing_created_at_is_typed_rejection() -> None:
    class _Bare:
        session_id = "a-worker-01"
        label = "Alpha"

    view = project_fleet_view(worker_sessions=(_Bare(),))
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "RECORD_FIELD_MISSING"
    ]
    assert view.worker_sessions.rejections[0].field == "created_at"


def test_connector_state_outside_vocabulary_is_typed_rejection() -> None:
    connector = _Connector(session_id="conn-abcd1234", label="Sunday")
    connector.state = "RUNNING"
    view = project_fleet_view(connector_sessions=(connector,))
    assert view.connector_sessions.records == ()
    assert [rejection.code for rejection in view.connector_sessions.rejections] == [
        "SESSION_STATE_INVALID"
    ]


# ---------------------------------------------------------------------------
# Local instances: safe fields only, age NOT_CARRIED
# ---------------------------------------------------------------------------


def test_local_instance_projects_safe_fields_and_not_carried_age() -> None:
    view = project_fleet_view(local_instances=(_Instance(),), now=NOW)
    group = view.local_instances
    assert group.available is True
    assert group.provenance == "LOCAL_INSTANCE_RECORD"
    assert len(group.records) == 1
    record = group.records[0]
    assert isinstance(record, FleetLocalInstanceRecord)
    assert record.name == "sunday-worker-1"
    assert record.tunnel_configured is True
    assert record.tunnel_suffix == "abcd"
    assert record.health == "READY"
    assert record.staleness == "NOT_CARRIED"
    flattened = repr(record)
    assert FORBIDDEN_PROJECT_PATH not in flattened
    assert FORBIDDEN_HEALTH_ADDRESS not in flattened
    assert FORBIDDEN_INSTANCE_ROOT not in flattened
    assert FORBIDDEN_TUNNEL_ID not in flattened


def test_local_instance_without_health_attr_projects_unknown_health() -> None:
    class _BareInstance:
        name = "sunday-worker-2"
        tunnel_configured = False
        tunnel_suffix = ""

    view = project_fleet_view(local_instances=(_BareInstance(),))
    record = view.local_instances.records[0]
    assert record.health == "UNKNOWN"
    assert record.staleness == "NOT_CARRIED"


def test_local_instance_with_invalid_health_is_typed_rejection() -> None:
    view = project_fleet_view(local_instances=(_Instance(health="FRESH",),))
    assert view.local_instances.records == ()
    assert [rejection.code for rejection in view.local_instances.rejections] == [
        "LOCAL_HEALTH_INVALID"
    ]


def test_local_instance_with_oversized_tunnel_suffix_is_rejected() -> None:
    view = project_fleet_view(local_instances=(_Instance(tunnel_suffix="abcde",),))
    assert [rejection.code for rejection in view.local_instances.rejections] == [
        "TUNNEL_SUFFIX_INVALID"
    ]


# ---------------------------------------------------------------------------
# Remote devices: single typed UNKNOWN constant
# ---------------------------------------------------------------------------


def test_remote_devices_are_single_constant_unknown_record() -> None:
    view = project_fleet_view(
        claim_bindings=(_Binding(),),
        worker_sessions=(_Worker(session_id="a-worker-01", label="Alpha"),),
    )
    group = view.remote_devices
    assert group.available is False
    assert group.provenance == "AWC_TOPOLOGY_CONSTANT"
    assert group.reason == "REMOTE_DEVICE_OBSERVATION_UNAVAILABLE"
    assert len(group.records) == 1
    record = group.records[0]
    assert isinstance(record, FleetRemoteDeviceRecord)
    assert record.state == "UNKNOWN"
    assert record.reason == "REMOTE_DEVICE_OBSERVATION_UNAVAILABLE"


def test_remote_constant_is_identical_regardless_of_inputs() -> None:
    empty = project_fleet_view()
    loaded = project_fleet_view(local_instances=(_Instance(),))
    assert empty.remote_devices.records[0] == loaded.remote_devices.records[0]


# ---------------------------------------------------------------------------
# Cross-source joins, conflicts, and dedup
# ---------------------------------------------------------------------------


def test_matching_branch_and_head_join_into_identity_link() -> None:
    view = project_fleet_view(
        claim_bindings=(_Binding(branch="feat/x", head_sha=SHA_A),),
        lease_observations=(
            _lease(lease_id="lease-1", branch="feat/x", expected_head=SHA_A),
        ),
    )
    assert len(view.identity.links) == 1
    link = view.identity.links[0]
    assert isinstance(link, FleetIdentityLink)
    assert link.claim_id == "awiki-claim-" + "a" * 20
    assert link.lease_id == "lease-1"
    assert link.branch == "feat/x"
    assert link.head_sha == SHA_A
    assert view.identity.conflicts == ()


def test_same_branch_different_head_is_identity_conflict_not_merge() -> None:
    view = project_fleet_view(
        claim_bindings=(_Binding(branch="feat/x", head_sha=SHA_A),),
        lease_observations=(
            _lease(lease_id="lease-1", branch="feat/x", expected_head=SHA_B),
        ),
    )
    assert view.identity.links == ()
    assert len(view.identity.conflicts) == 1
    conflict = view.identity.conflicts[0]
    assert isinstance(conflict, FleetIdentityConflict)
    assert conflict.code == "IDENTITY_CONFLICT"
    assert conflict.divergent_fields == ("head_sha",)
    assert conflict.claim_ids == ("awiki-claim-" + "a" * 20,)
    assert conflict.lease_ids == ("lease-1",)
    assert conflict.branch == "feat/x"


def test_same_task_id_with_different_claim_id_is_identity_conflict() -> None:
    view = project_fleet_view(
        claim_bindings=(
            _Binding(
                task_id="task-1",
                claim_id="awiki-claim-" + "a" * 20,
            ),
            _Binding(
                task_id="task-1",
                claim_id="awiki-claim-" + "b" * 20,
            ),
        )
    )
    assert len(view.identity.conflicts) == 1
    conflict = view.identity.conflicts[0]
    assert conflict.code == "IDENTITY_CONFLICT"
    assert conflict.divergent_fields == ("claim_id",)
    assert conflict.task_id == "task-1"
    assert conflict.claim_ids == ("awiki-claim-" + "a" * 20, "awiki-claim-" + "b" * 20)


def test_same_id_across_different_classes_stays_distinct() -> None:
    view = project_fleet_view(
        claim_bindings=(_Binding(claim_id="shared-id"),),
        worker_sessions=(_Worker(session_id="shared-id", label="Alpha"),),
    )
    assert view.claims.records[0].claim_id == "shared-id"
    assert view.worker_sessions.records[0].session_id == "shared-id"
    assert view.claims.records[0].duplicate_count == 0
    assert view.worker_sessions.records[0].duplicate_count == 0
    assert view.identity.conflicts == ()
    assert view.identity.links == ()


def test_join_requires_both_sides_valid_mixed_invalid_does_not_half_join() -> None:
    good_claim = _Binding(branch="feat/x", head_sha=SHA_A)
    bad_claim = _Binding(branch="feat/x", head_sha="nothex")
    good_lease = _lease(lease_id="lease-1", branch="feat/x", expected_head=SHA_A)
    bad_lease = _lease(
        lease_id="   ", branch="feat/x", expected_head=SHA_B
    )
    view = project_fleet_view(
        claim_bindings=(good_claim, bad_claim),
        lease_observations=(bad_lease, good_lease),
    )
    assert [link.claim_id for link in view.identity.links] == [
        "awiki-claim-" + "a" * 20
    ]
    assert [link.lease_id for link in view.identity.links] == ["lease-1"]
    assert len(view.claims.rejections) == 1
    assert view.claims.rejections[0].code == "HEAD_SHA_INVALID"
    assert len(view.leases.rejections) == 1
    assert view.leases.rejections[0].code == "IDENTIFIER_BLANK"


def test_duplicate_ids_within_one_class_dedup_first_wins_with_count() -> None:
    first = _Binding(claim_id="awiki-claim-" + "a" * 20, agent="a-worker-01")
    second = _Binding(claim_id="awiki-claim-" + "a" * 20, agent="a-worker-02")
    view = project_fleet_view(claim_bindings=(first, second))
    assert len(view.claims.records) == 1
    assert view.claims.records[0].agent == "a-worker-01"
    assert view.claims.records[0].duplicate_count == 1
    assert view.claims.duplicate_count == 1


def test_duplicate_lease_and_session_ids_dedup_per_class() -> None:
    view = project_fleet_view(
        lease_observations=(
            _lease(lease_id="lease-1", worker_id="a-worker-01"),
            _lease(lease_id="lease-1", worker_id="a-worker-02"),
        ),
        worker_sessions=(
            _Worker(session_id="a-worker-01", label="Alpha"),
            _Worker(session_id="a-worker-01", label="Alpha Two"),
        ),
    )
    assert len(view.leases.records) == 1
    assert view.leases.records[0].duplicate_count == 1
    assert len(view.worker_sessions.records) == 1
    assert view.worker_sessions.records[0].label == "Alpha"
    assert view.worker_sessions.records[0].duplicate_count == 1


# ---------------------------------------------------------------------------
# Malformed records: per-record typed rejection, neighbors survive
# ---------------------------------------------------------------------------


def test_bad_sha_shape_is_typed_rejection_and_neighbor_survives() -> None:
    good_first = _Binding(claim_id="awiki-claim-" + "a" * 20)
    bad = _Binding(claim_id="awiki-claim-" + "b" * 20, head_sha="ZZZ-not-a-sha")
    good_second = _Binding(claim_id="awiki-claim-" + "c" * 20)
    view = project_fleet_view(claim_bindings=(good_first, bad, good_second))
    assert [record.claim_id for record in view.claims.records] == [
        "awiki-claim-" + "a" * 20,
        "awiki-claim-" + "c" * 20,
    ]
    assert [rejection.code for rejection in view.claims.rejections] == [
        "HEAD_SHA_INVALID"
    ]
    assert view.claims.rejections[0].source_index == 1


def test_blank_identifier_is_typed_rejection() -> None:
    view = project_fleet_view(claim_bindings=(_Binding(task_id="   "),))
    assert [rejection.code for rejection in view.claims.rejections] == [
        "IDENTIFIER_BLANK"
    ]


def test_path_shaped_value_in_safe_field_is_typed_rejection() -> None:
    bad_branch = _Binding(branch="/Users/operator/repo")
    bad_repository = _Binding(repository="C:\\Repos\\Secret")
    view = project_fleet_view(claim_bindings=(bad_branch, bad_repository))
    assert [rejection.code for rejection in view.claims.rejections] == [
        "SAFE_FIELD_PATH_SHAPED",
        "SAFE_FIELD_PATH_SHAPED",
    ]
    assert view.claims.rejections[0].field == "branch"
    assert view.claims.rejections[1].field == "repository"


def test_rejections_carry_no_diagnostic_value_echo() -> None:
    names = {field.name for field in dataclasses.fields(FleetRecordRejection)}
    assert names == {"source_class", "code", "field", "source_index", "non_authoritative"}
    leaky = _Binding(branch="/Users/operator/repo")
    view = project_fleet_view(claim_bindings=(leaky,))
    rejection = view.claims.rejections[0]
    assert "/Users/operator/repo" not in repr(rejection)
    assert rejection.source_class == "claims"
    assert rejection.code == "SAFE_FIELD_PATH_SHAPED"
    assert rejection.field == "branch"
    assert rejection.source_index == 0


@pytest.mark.parametrize(
    ("source_class", "record"),
    [
        ("claim_bindings", _RaisingAttr()),
        ("worker_sessions", _RaisingAttr()),
    ],
)
def test_raising_attribute_becomes_typed_record_never_exception_escape(
    source_class: str, record: object
) -> None:
    view = project_fleet_view(**{source_class: (record,)})
    group_name = {"claim_bindings": "claims"}.get(source_class, source_class)
    group = getattr(view, group_name)
    assert group.records == ()
    assert [rejection.code for rejection in group.rejections] == [
        "RECORD_ATTRIBUTE_UNREADABLE"
    ]


def test_lease_with_raising_attribute_is_typed_rejection() -> None:
    class _RaisingLease:
        @property
        def available(self) -> bool:
            raise RuntimeError("boom")

    view = project_fleet_view(lease_observations=(_RaisingLease(),))
    assert view.leases.records == ()
    assert [rejection.code for rejection in view.leases.rejections] == [
        "RECORD_ATTRIBUTE_UNREADABLE"
    ]


def test_instance_with_raising_attribute_is_typed_rejection() -> None:
    class _RaisingInstance:
        @property
        def name(self) -> str:
            raise RuntimeError("boom")

    view = project_fleet_view(local_instances=(_RaisingInstance(),))
    assert view.local_instances.records == ()
    assert [rejection.code for rejection in view.local_instances.rejections] == [
        "RECORD_ATTRIBUTE_UNREADABLE"
    ]


def test_non_record_object_is_typed_rejection() -> None:
    view = project_fleet_view(worker_sessions=(None, 7))
    assert view.worker_sessions.records == ()
    assert {rejection.code for rejection in view.worker_sessions.rejections} == {
        "RECORD_TYPE_UNSUPPORTED"
    }


# ---------------------------------------------------------------------------
# Empty classes, frame bound, framing, determinism
# ---------------------------------------------------------------------------


def test_empty_input_classes_are_typed_empty_not_unavailable() -> None:
    view = project_fleet_view()
    for group_name in (
        "claims",
        "leases",
        "worker_sessions",
        "connector_sessions",
        "local_instances",
    ):
        group = getattr(view, group_name)
        assert group.available is True, group_name
        assert group.records == ()
        assert group.rejections == ()
        assert group.reason is None
        assert group.duplicate_count == 0
        assert group.truncated is False
    assert view.identity.links == ()
    assert view.identity.conflicts == ()


def test_record_groups_carry_available_provenance_reason_framing() -> None:
    view = project_fleet_view()
    assert view.claims.provenance == "AWIKI_CLAIM_BINDING"
    assert view.leases.provenance == "COCKPIT_LEASE_OBSERVATION"
    assert view.worker_sessions.provenance == "APP_SESSION_RECORD"
    assert view.connector_sessions.provenance == "APP_SESSION_RECORD"
    assert view.local_instances.provenance == "LOCAL_INSTANCE_RECORD"
    assert view.remote_devices.provenance == "AWC_TOPOLOGY_CONSTANT"
    for group_name in (
        "claims",
        "leases",
        "worker_sessions",
        "connector_sessions",
        "local_instances",
        "remote_devices",
    ):
        group = getattr(view, group_name)
        assert isinstance(group, FleetRecordGroup)
        assert isinstance(group.available, bool)
        assert group.reason is None or re.fullmatch(
            r"[A-Z][A-Z0-9_:\-]{0,127}", group.reason
        )


def test_frame_rows_are_bounded_at_256_per_group() -> None:
    bindings = tuple(
        _Binding(claim_id=f"awiki-claim-{index:020d}") for index in range(300)
    )
    view = project_fleet_view(claim_bindings=bindings)
    assert len(view.claims.records) == 256
    assert view.claims.truncated is True
    assert view.claims.reason == "FRAME_ROW_LIMIT_EXCEEDED"


def test_non_sequence_input_is_typed_group_unavailable() -> None:
    view = project_fleet_view(worker_sessions=42)
    assert view.worker_sessions.available is False
    assert view.worker_sessions.reason == "RECORD_FRAME_INPUT_INVALID"
    assert view.worker_sessions.records == ()


def test_naive_now_argument_fails_closed() -> None:
    with pytest.raises(ValueError):
        project_fleet_view(now=datetime(2026, 11, 15, 12, 0, 0))


def test_same_inputs_produce_equal_views() -> None:
    inputs: dict[str, object] = {
        "claim_bindings": (_Binding(), _Binding(claim_id="awiki-claim-" + "b" * 20)),
        "lease_observations": (_lease(),),
        "worker_sessions": (_Worker(session_id="a-worker-01", label="Alpha"),),
        "connector_sessions": (_Connector(session_id="conn-abcd1234", label="Sunday"),),
        "local_instances": (_Instance(),),
        "now": NOW,
    }
    assert project_fleet_view(**inputs) == project_fleet_view(**inputs)


def test_fleet_view_is_typed_composition_with_identity_summary() -> None:
    view = project_fleet_view()
    assert isinstance(view, FleetView)
    assert isinstance(view.identity, FleetIdentitySummary)
    assert view.non_authoritative is True
    for group_name in (
        "claims",
        "leases",
        "worker_sessions",
        "connector_sessions",
        "local_instances",
        "remote_devices",
    ):
        assert isinstance(getattr(view, group_name), FleetRecordGroup)


# ---------------------------------------------------------------------------
# Repair round 1 (review P1/P2/P3): liar carriers, id path-shape law, now
# contract, forbidden-pid corpus pin
# ---------------------------------------------------------------------------


def test_lease_with_liar_enum_value_health_is_typed_rejection() -> None:
    observation = CockpitLeaseObservation(
        available=True,
        provenance="DURABLE_EXECUTION_RECORD",
        lease_id="lease-1",
        worker_id="a-worker-01",
        branch="feat/x",
        expected_head=SHA_A,
        health=_LiarEnumText(),
    )
    view = project_fleet_view(lease_observations=(observation,))
    assert view.leases.records == ()
    assert [rejection.code for rejection in view.leases.rejections] == [
        "LEASE_HEALTH_INVALID"
    ]
    assert view.leases.rejections[0].field == "health"


def test_instance_with_liar_enum_value_health_is_typed_rejection() -> None:
    view = project_fleet_view(local_instances=(_Instance(health=_LiarEnumText()),))
    assert view.local_instances.records == ()
    assert [rejection.code for rejection in view.local_instances.rejections] == [
        "LOCAL_HEALTH_INVALID"
    ]
    assert view.local_instances.rejections[0].field == "health"


def test_liar_tzinfo_created_at_is_typed_rejection() -> None:
    worker = _Worker(
        session_id="a-worker-01",
        label="Alpha",
        created_at=datetime(2026, 11, 15, 10, 0, 0, tzinfo=_LiarTzinfo()),
    )
    view = project_fleet_view(worker_sessions=(worker,), now=NOW)
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "TIMESTAMP_NAIVE"
    ]
    assert view.worker_sessions.rejections[0].field == "created_at"


def test_path_shaped_lease_id_is_typed_rejection() -> None:
    view = project_fleet_view(lease_observations=(_lease(lease_id="/etc/passwd"),))
    assert view.leases.records == ()
    assert [rejection.code for rejection in view.leases.rejections] == [
        "SAFE_FIELD_PATH_SHAPED"
    ]
    assert view.leases.rejections[0].field == "lease_id"


def test_path_shaped_lease_worker_id_is_typed_rejection() -> None:
    view = project_fleet_view(
        lease_observations=(_lease(worker_id="C:\\Users\\operator"),)
    )
    assert view.leases.records == ()
    assert [rejection.code for rejection in view.leases.rejections] == [
        "SAFE_FIELD_PATH_SHAPED"
    ]
    assert view.leases.rejections[0].field == "worker_id"


def test_path_shaped_session_id_is_typed_rejection() -> None:
    worker = _Worker(session_id="../../x", label="Alpha")
    view = project_fleet_view(worker_sessions=(worker,))
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "SAFE_FIELD_PATH_SHAPED"
    ]


def test_liar_tzinfo_now_raises_contract_value_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        project_fleet_view(
            now=datetime(2026, 11, 15, 12, 0, 0, tzinfo=_LiarTzinfo())
        )
    assert str(excinfo.value) == "FLEET_NOW_MUST_BE_TZ_AWARE"


def test_forbidden_pid_never_projects_anywhere() -> None:
    view = project_fleet_view(
        claim_bindings=(_Binding(),),
        lease_observations=(_lease(),),
        worker_sessions=(_Worker(session_id="a-worker-01", label="Alpha"),),
        connector_sessions=(_Connector(session_id="conn-abcd1234", label="Sunday"),),
        local_instances=(_Instance(),),
    )
    assert str(FORBIDDEN_PID) not in repr(view)


# ---------------------------------------------------------------------------
# WO-P1-765 card-03: two-faced-subclass residuals (flip-flop stamps, raising
# __iter__/__len__ str subclasses) must become typed rejections, never escapes
# ---------------------------------------------------------------------------


def test_flip_flop_tzinfo_raising_at_isoformat_is_typed_rejection() -> None:
    # aware-looking on the awareness probe (call 1), raising at the second
    # read inside parsed.isoformat() when no ``now`` comparison runs
    worker = _Worker(
        session_id="a-worker-01",
        label="Alpha",
        created_at=datetime(2026, 11, 15, 10, 0, 0, tzinfo=_FlipFlopTzinfo(2)),
    )
    view = project_fleet_view(worker_sessions=(worker,))
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "TIMESTAMP_INVALID"
    ]
    assert view.worker_sessions.rejections[0].field == "created_at"


def test_flip_flop_tzinfo_raising_at_now_subtraction_is_typed_rejection() -> None:
    # survives the awareness probe (call 1) and isoformat (call 2), raising
    # only at the ``now - parsed`` subtraction (call 3)
    worker = _Worker(
        session_id="a-worker-01",
        label="Alpha",
        created_at=datetime(2026, 11, 15, 10, 0, 0, tzinfo=_FlipFlopTzinfo(3)),
    )
    view = project_fleet_view(worker_sessions=(worker,), now=NOW)
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "TIMESTAMP_INVALID"
    ]
    assert view.worker_sessions.rejections[0].field == "created_at"


def test_raising_iter_session_id_is_typed_rejection_not_escape() -> None:
    worker = _Worker(session_id=_RaisingStr("a-worker-01"), label="Alpha")
    view = project_fleet_view(worker_sessions=(worker,))
    assert view.worker_sessions.records == ()
    assert [rejection.code for rejection in view.worker_sessions.rejections] == [
        "IDENTIFIER_INVALID"
    ]
    assert view.worker_sessions.rejections[0].field == "session_id"


def test_raising_len_tunnel_suffix_is_typed_rejection_not_escape() -> None:
    view = project_fleet_view(
        local_instances=(_Instance(tunnel_suffix=_RaisingStr("abcd")),)
    )
    assert view.local_instances.records == ()
    assert [rejection.code for rejection in view.local_instances.rejections] == [
        "TUNNEL_SUFFIX_INVALID"
    ]
    assert view.local_instances.rejections[0].field == "tunnel_suffix"
