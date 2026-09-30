"""WO-P1-573 — focused RED-first tests for the A-Sidecar Codex bridge.

Covers the work-order §12 fault matrix against
``src/a_conductor/sidecar_codex_bridge.py`` (pure projection/receipt
module over the Phase 1 carrier ``src/a_conductor/sidecar_relay.py``):

1.  checkpoint/event recovery + dedupe by EVENT_ID through the carrier;
2.  deterministic candidate selection; at most one projection target;
3.  stale/unbound candidate revalidation fails closed;
4.  missing surface descriptor -> ``BRIDGE_SURFACE_UNAVAILABLE``;
5.  version not allowlisted -> ``BRIDGE_SURFACE_VERSION_UNVERIFIED``;
6.  connector unreachable -> ``BRIDGE_SURFACE_OFFLINE``;
7.  active writer -> ``BRIDGE_ACTIVE_WRITER``, no projection;
8.  repeat projection of same EVENT_ID -> ``BRIDGE_DUPLICATE_PROJECTION``;
9.  ambiguous thread identity -> ``BRIDGE_AMBIGUOUS_TARGET``;
10. non-steerable target -> ``BRIDGE_NOT_STEERABLE``;
11. context pressure -> ``BRIDGE_CONTEXT_PRESSURE`` + ``CONTEXT_PRESSURE_HIGH``
    event helper;
12. quota constrained -> ``BRIDGE_QUOTA_LIMITED`` + ``GPT_WORK_LIMITED``
    event helper;
13. steer without durable pointers -> ``BRIDGE_POINTER_INVALID``;
14. ACK receipt references original EVENT_ID via EVIDENCE_REFS entry;
15. projection payload is pointer-only (no free-form/executable body);
16. no socket/HTTP/subprocess/native IPC and no raw storage access
    (AST/structural test);
17. no authority-named API surface (AST/structural test);
18. strict UTF-8/LF artifacts and opaque cross-device path handling;
19. related suites (``test_sidecar_relay.py`` etc.) stay green — run
    separately by the work order.
"""

from __future__ import annotations

import ast
import dataclasses
import itertools
from pathlib import Path

import pytest

from a_conductor import sidecar_relay as sr

MODULE_SOURCE_PATH = Path(
    __import__("a_conductor.sidecar_codex_bridge", fromlist=["_"]).__file__
)

VALID_HEAD = "b" * 40
TASK_ID = "WO-P1-573"
CLAIM_ID = "WO-P1-573-SIDECAR-BRIDGE-MAC-001"
REPO = "aase7en/A-Wiki-Conductor"
WORKTREE = "/Users/dev/GitHub/_worktrees/wo573-demo"
WO_REF = "docs/work-orders/WO-P1-573-a-sidecar-phase2-codex-bridge.md"
PROVEN_VERSION = "0.158.0-alpha.2.1"
ACCEPTED_VERSIONS = frozenset({PROVEN_VERSION})

WO_BRIDGE_FAILURE_CODES = frozenset(
    {
        "BRIDGE_SURFACE_UNAVAILABLE",
        "BRIDGE_SURFACE_VERSION_UNVERIFIED",
        "BRIDGE_SURFACE_OFFLINE",
        "BRIDGE_ACTIVE_WRITER",
        "BRIDGE_DUPLICATE_PROJECTION",
        "BRIDGE_AMBIGUOUS_TARGET",
        "BRIDGE_NOT_STEERABLE",
        "BRIDGE_CONTEXT_PRESSURE",
        "BRIDGE_QUOTA_LIMITED",
        "BRIDGE_POINTER_INVALID",
    }
)


def _payload(**overrides: object) -> dict:
    payload: dict = {
        "EVENT_ID": "evt-chatgpt-sidecar-base0000000000001",
        "EVENT_TYPE": "CODEX_STEER_REQUEST",
        "SOURCE_SURFACE": "chatgpt-sidecar",
        "SOURCE_THREAD_ID": "sidecar-thread-1",
        "SOURCE_TURN_ID": "turn-0001",
        "TASK_ID": TASK_ID,
        "CLAIM_ID": CLAIM_ID,
        "REPO": REPO,
        "WORKTREE": WORKTREE,
        "HEAD_SHA": VALID_HEAD,
        "EVIDENCE_REFS": [WO_REF],
        "CREATED_AT": "2026-09-30T10:00:00+00:00",
    }
    for key, value in overrides.items():
        if value is None:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


def _envelope(**overrides: object) -> sr.RelayEnvelope:
    return sr.envelope_from_mapping(_payload(**overrides))


def _checkpoint(event_id: str, created_at: str) -> sr.RelayEnvelope:
    return sr.envelope_from_mapping(
        _payload(
            EVENT_TYPE="SIDECAR_CHECKPOINT",
            EVENT_ID=event_id,
            CREATED_AT=created_at,
        )
    )


def _steer(event_id: str, created_at: str, **overrides: object) -> sr.RelayEnvelope:
    return sr.envelope_from_mapping(
        _payload(EVENT_ID=event_id, CREATED_AT=created_at, **overrides)
    )


def _code(excinfo: pytest.ExceptionInfo) -> str:
    return excinfo.value.code


class FakeTransport:
    def __init__(
        self,
        observe: dict | None = None,
        submit: dict | None = None,
        observe_error: Exception | None = None,
        submit_error: Exception | None = None,
    ) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.observe = observe if observe is not None else {
            "reachable": True,
            "target_resolved": True,
            "active_writer": False,
            "steerable": True,
            "thread_id": "codex-thread-7",
        }
        self.submit = submit if submit is not None else {
            "delivery": "DELIVERED",
            "thread_id": "codex-thread-7",
            "queue_ref": "queue-0001",
        }
        self.observe_error = observe_error
        self.submit_error = submit_error

    def __call__(self, kind: str, payload: dict) -> object:
        self.calls.append((kind, dict(payload)))
        if kind == "observe":
            if self.observe_error is not None:
                raise self.observe_error
            return dict(self.observe)
        if kind == "submit":
            if self.submit_error is not None:
                raise self.submit_error
            return dict(self.submit)
        raise AssertionError("unexpected transport kind")

    @property
    def observe_calls(self) -> int:
        return sum(1 for kind, _ in self.calls if kind == "observe")

    @property
    def submit_calls(self) -> int:
        return sum(1 for kind, _ in self.calls if kind == "submit")


def _facts(**overrides: object) -> object:
    from a_conductor import sidecar_codex_bridge as scb

    fields = {
        "repo": REPO,
        "worktree": WORKTREE,
        "head_sha": VALID_HEAD,
        "task_id": TASK_ID,
        "claim_id": CLAIM_ID,
    }
    fields.update(overrides)
    return scb.LiveBindingFacts(**fields)


def _surface(version: str | None = PROVEN_VERSION) -> object:
    from a_conductor import sidecar_codex_bridge as scb

    return scb.SurfaceDescriptor(
        surface_kind="desktop-app-server", version=version
    )


def _project(
    events,
    *,
    facts=None,
    surface="default",
    transport: FakeTransport | None = None,
    **kwargs: object,
):
    from a_conductor import sidecar_codex_bridge as scb

    return scb.project_steer_candidate(
        events,
        facts=facts if facts is not None else _facts(),
        surface=_surface() if surface == "default" else surface,
        accepted_versions=ACCEPTED_VERSIONS,
        accepted_prefixes=(),
        transport=transport if transport is not None else FakeTransport(),
        **kwargs,
    )


class TestCheckpointRecoveryAndDedupe:
    def test_recovers_latest_checkpoint_through_carrier_log(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        log = tmp_path / "events.jsonl"
        sr.append_event(log, _checkpoint("evt-chatgpt-sidecar-ck000000000001", "2026-09-30T09:00:00+00:00"))
        sr.append_event(log, _steer("evt-chatgpt-sidecar-st000000000001", "2026-09-30T09:30:00+00:00"))
        sr.append_event(log, _checkpoint("evt-chatgpt-sidecar-ck000000000002", "2026-09-30T11:00:00+00:00"))
        sr.append_event(log, _checkpoint("evt-chatgpt-sidecar-ck000000000003", "2026-09-30T10:00:00+00:00"))
        events = sr.read_events(log).events
        checkpoint = scb.recover_checkpoint(events)
        assert checkpoint is not None
        assert checkpoint.event_id == "evt-chatgpt-sidecar-ck000000000002"
        assert checkpoint.task_id == TASK_ID
        assert checkpoint.claim_id == CLAIM_ID
        assert checkpoint.repo == REPO
        assert checkpoint.worktree == WORKTREE
        assert checkpoint.head_sha == VALID_HEAD

    def test_no_checkpoint_returns_none(self):
        from a_conductor import sidecar_codex_bridge as scb

        events = (_steer("evt-chatgpt-sidecar-st000000000002", "2026-09-30T10:05:00+00:00"),)
        assert scb.recover_checkpoint(events) is None

    def test_duplicate_event_ids_collapse_first_occurrence_wins(self):
        from a_conductor import sidecar_codex_bridge as scb

        first = _steer("evt-chatgpt-sidecar-dup000000000001", "2026-09-30T10:00:00+00:00")
        duplicate = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-chatgpt-sidecar-dup000000000001",
                CREATED_AT="2026-09-30T12:00:00+00:00",
            )
        )
        deduped = scb.dedupe_events([first, duplicate, first])
        assert deduped == (first,)

    def test_non_envelope_input_fails_with_carrier_code(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(sr.RelayCarrierError) as excinfo:
            scb.dedupe_events([{"EVENT_ID": "evt-codex-not-an-envelope"}])
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"


class TestCandidateSelection:
    def test_selects_single_earliest_candidate_deterministically(self):
        from a_conductor import sidecar_codex_bridge as scb

        early = _steer("evt-chatgpt-sidecar-sel00000000001", "2026-09-30T10:00:00+00:00")
        late = _steer("evt-chatgpt-sidecar-sel00000000002", "2026-09-30T11:00:00+00:00")
        other_producer = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-codex-sel00000000003",
                SOURCE_SURFACE="codex",
                SOURCE_THREAD_ID="codex-lane-1",
                CREATED_AT="2026-09-30T09:00:00+00:00",
            )
        )
        for shuffle in itertools.permutations([late, other_producer, early]):
            selected = scb.select_steer_candidate(shuffle)
            assert selected == early

    def test_selection_is_at_most_one_and_none_when_absent(self):
        from a_conductor import sidecar_codex_bridge as scb

        assert scb.select_steer_candidate(()) is None
        checkpoint = _checkpoint("evt-chatgpt-sidecar-ck100000000001", "2026-09-30T10:00:00+00:00")
        assert scb.select_steer_candidate([checkpoint]) is None

    def test_duplicate_delivery_collapses_to_one_candidate(self):
        from a_conductor import sidecar_codex_bridge as scb

        first = _steer("evt-chatgpt-sidecar-dup000000000002", "2026-09-30T10:00:00+00:00")
        duplicate = sr.envelope_from_mapping(
            _payload(
                EVENT_ID="evt-chatgpt-sidecar-dup000000000002",
                CREATED_AT="2026-09-30T10:30:00+00:00",
            )
        )
        assert scb.select_steer_candidate([first, duplicate]) == first


class TestRevalidationFailsClosed:
    def test_matching_facts_pass(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = _envelope()
        scb.revalidate_candidate(candidate, _facts())

    def test_stale_head_fails_closed_context_drift(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = _envelope()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(candidate, _facts(head_sha="c" * 40))
        assert _code(excinfo) == "CONTEXT_DRIFT"
        assert _code(excinfo) not in scb.BRIDGE_FAILURE_CODES

    @pytest.mark.parametrize(
        "field,value",
        [
            ("repo", "aase7en/Other-Repo"),
            ("worktree", "/Users/dev/GitHub/_worktrees/other"),
            ("task_id", "WO-P1-999"),
        ],
    )
    def test_binding_mismatch_fails_closed_context_drift(self, field, value):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = _envelope()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(candidate, _facts(**{field: value}))
        assert _code(excinfo) == "CONTEXT_DRIFT"

    def test_claim_mismatch_fails_closed_claim_conflict(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = _envelope()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(candidate, _facts(claim_id="WO-P1-999-OTHER-CLAIM"))
        assert _code(excinfo) == "CLAIM_CONFLICT"
        assert _code(excinfo) not in scb.BRIDGE_FAILURE_CODES

    def test_missing_facts_object_fails_closed(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(_envelope(), None)
        assert _code(excinfo) == "CONTEXT_DRIFT"

    def test_partial_facts_only_check_supplied_values(self):
        from a_conductor import sidecar_codex_bridge as scb

        scb.revalidate_candidate(_envelope(), _facts(repo=None, worktree=None, head_sha=None, claim_id=None))

    def test_unbound_candidate_fails_closed(self):
        from a_conductor import sidecar_codex_bridge as scb

        unbound = dataclasses.replace(_envelope(), task_id=None, claim_id=None, repo=None, worktree=None, head_sha=None)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(unbound, _facts())
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"


class TestSurfaceGate:
    def test_missing_descriptor_is_surface_unavailable(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = _envelope()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.project_steer_candidate(
                [candidate],
                facts=_facts(),
                surface=None,
                accepted_versions=ACCEPTED_VERSIONS,
                transport=FakeTransport(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_UNAVAILABLE"

    def test_missing_transport_is_surface_unavailable(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.project_steer_candidate(
                [_envelope()],
                facts=_facts(),
                surface=_surface(),
                accepted_versions=ACCEPTED_VERSIONS,
                transport=None,
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_UNAVAILABLE"

    def test_unsupported_surface_kind_is_surface_unavailable(self):
        from a_conductor import sidecar_codex_bridge as scb

        descriptor = scb.SurfaceDescriptor(surface_kind="raw-sqlite", version=PROVEN_VERSION)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                descriptor, accepted_versions=ACCEPTED_VERSIONS, accepted_prefixes=()
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_UNAVAILABLE"

    def test_version_missing_is_version_unverified(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                _surface(version=None),
                accepted_versions=ACCEPTED_VERSIONS,
                accepted_prefixes=(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_version_not_allowlisted_is_version_unverified(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                _surface(version="0.999.0"),
                accepted_versions=ACCEPTED_VERSIONS,
                accepted_prefixes=(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_empty_allowlist_never_verifies(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                _surface(), accepted_versions=(), accepted_prefixes=()
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_malformed_allowlist_entry_fails_verification(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                _surface(),
                accepted_versions=frozenset({"0.1!; drop"}),
                accepted_prefixes=(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_proven_version_is_evidence_not_implicit_authority(self):
        from a_conductor import sidecar_codex_bridge as scb

        assert scb.INITIAL_PROVEN_SURFACE_VERSION == "0.158.0-alpha.2.1"
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                _surface(version=scb.INITIAL_PROVEN_SURFACE_VERSION),
                accepted_versions=frozenset({"9.9.9"}),
                accepted_prefixes=(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_exact_version_and_prefix_acceptance(self):
        from a_conductor import sidecar_codex_bridge as scb

        scb.validate_surface_version(
            _surface(), accepted_versions=ACCEPTED_VERSIONS, accepted_prefixes=()
        )
        scb.validate_surface_version(
            _surface(),
            accepted_versions=frozenset(),
            accepted_prefixes=("0.158.0",),
        )

    def test_unsafe_version_text_is_version_unverified(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.validate_surface_version(
                scb.SurfaceDescriptor(surface_kind="desktop-app-server", version="0.158.0-alpha\x1b"),
                accepted_versions=frozenset({"0.158.0-alpha\x1b"}),
                accepted_prefixes=(),
            )
        assert _code(excinfo) == "BRIDGE_SURFACE_VERSION_UNVERIFIED"

    def test_supported_surface_kinds_are_desktop_managed_only(self):
        from a_conductor import sidecar_codex_bridge as scb

        assert scb.SUPPORTED_SURFACE_KINDS == frozenset(
            {"desktop-app-server", "codex-native-queue"}
        )


class TestConnectorObservation:
    def test_transport_error_is_surface_offline(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe_error=RuntimeError("unreachable"))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"

    def test_unreachable_observation_is_surface_offline(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": False})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"

    def test_malformed_observation_is_surface_offline(self):
        from a_conductor import sidecar_codex_bridge as scb

        for garbage in ("ok", 7, None, {"reachable": "yes"}):
            transport = FakeTransport()
            transport.observe = garbage
            with pytest.raises(scb.BridgeFailureError) as excinfo:
                _project([_envelope()], transport=transport)
            assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"

    def test_active_writer_refuses_without_submission(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": True, "steerable": True, "thread_id": "codex-thread-7"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_ACTIVE_WRITER"
        assert transport.submit_calls == 0

    def test_unresolved_target_is_ambiguous(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": False, "active_writer": False, "steerable": True, "thread_id": None})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_AMBIGUOUS_TARGET"
        assert transport.submit_calls == 0

    def test_operator_hint_is_context_not_existence_proof(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": False, "active_writer": False, "steerable": True, "thread_id": None})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport, target_hint="codex-thread-999")
        assert _code(excinfo) == "BRIDGE_AMBIGUOUS_TARGET"

    def test_unsafe_thread_identity_text_is_ambiguous(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": False, "steerable": True, "thread_id": "thread\x1b[31m"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_AMBIGUOUS_TARGET"

    def test_not_steerable_target_blocks_projection(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": False, "steerable": False, "thread_id": "codex-thread-7"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_NOT_STEERABLE"
        assert transport.submit_calls == 0


class TestDuplicateProjection:
    def _acked_events(self, tmp_path):
        log = tmp_path / "events.jsonl"
        steer = _steer("evt-chatgpt-sidecar-dup000000000009", "2026-09-30T10:00:00+00:00")
        sr.append_event(log, steer)
        from a_conductor import sidecar_codex_bridge as scb

        receipt = scb.build_ack_receipt(
            steer,
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0002",
            created_at="2026-09-30T10:05:00+00:00",
        )
        scb.emit_receipt(log, receipt)
        return sr.read_events(log).events, steer

    def test_reprojection_of_acked_event_fails_duplicate(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        events, steer = self._acked_events(tmp_path)
        transport = FakeTransport()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project(events, transport=transport)
        assert _code(excinfo) == "BRIDGE_DUPLICATE_PROJECTION"
        assert transport.calls == []
        assert steer.event_id in scb.projected_event_ids(events)

    def test_projected_ids_derive_only_from_relay_event_refs(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        events, steer = self._acked_events(tmp_path)
        assert scb.projected_event_ids(events) == {steer.event_id}


class TestContextPressureAndQuota:
    def test_context_pressure_defers_projection(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport, context_pressure=True)
        assert _code(excinfo) == "BRIDGE_CONTEXT_PRESSURE"
        assert transport.calls == []

    def test_quota_limited_defers_projection(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport, quota_limited=True)
        assert _code(excinfo) == "BRIDGE_QUOTA_LIMITED"
        assert transport.calls == []

    def test_context_pressure_event_helper_round_trips(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        event = scb.build_context_pressure_event(
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0003",
            created_at="2026-09-30T10:06:00+00:00",
        )
        assert event.event_type == "CONTEXT_PRESSURE_HIGH"
        assert event.priority == "HIGH"
        log = tmp_path / "events.jsonl"
        sr.append_event(log, event)
        restored = sr.read_events(log).events[0]
        assert restored == event

    def test_gpt_work_limited_event_helper_round_trips(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        event = scb.build_gpt_work_limited_event(
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0004",
            created_at="2026-09-30T10:07:00+00:00",
        )
        assert event.event_type == "GPT_WORK_LIMITED"
        assert event.priority == "NORMAL"
        log = tmp_path / "events.jsonl"
        sr.append_event(log, event)
        assert sr.read_events(log).events[0] == event


class TestPointerProjection:
    def test_steer_without_evidence_refs_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = sr.envelope_from_mapping(_payload(EVIDENCE_REFS=None))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_url_ref_candidate_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        mapping = _payload()
        candidate = dataclasses.replace(_envelope(), evidence_refs=("https://share.example.com/x",))
        assert candidate.evidence_refs == ("https://share.example.com/x",)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_pointer_invalid_surfaces_in_full_projection(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = sr.envelope_from_mapping(_payload(EVIDENCE_REFS=None))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([candidate])
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_projection_payload_is_pointer_only(self):
        from a_conductor import sidecar_codex_bridge as scb

        projection = scb.build_steer_projection(_envelope())
        mapping = projection.to_pointer_mapping()
        assert set(mapping) == {"EVENT_ID", "TASK_ID", "CLAIM_ID", "EVIDENCE_REFS"}
        assert mapping["EVIDENCE_REFS"] == [WO_REF]
        assert mapping["TASK_ID"] == TASK_ID
        assert mapping["CLAIM_ID"] == CLAIM_ID
        for value in mapping.values():
            assert not isinstance(value, dict)

    def test_projection_is_frozen_and_bounded(self):
        from a_conductor import sidecar_codex_bridge as scb

        projection = scb.build_steer_projection(_envelope())
        with pytest.raises(dataclasses.FrozenInstanceError):
            projection.original_event_id = "changed"
        assert projection.evidence_refs == tuple(projection.evidence_refs)
        assert len(projection.evidence_refs) <= sr.MAX_EVIDENCE_REFS

    def test_submission_carries_only_pointer_payload(self):
        transport = FakeTransport()
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        kind, payload = transport.calls[-1]
        assert kind == "submit"
        assert set(payload) == {"EVENT_ID", "TASK_ID", "CLAIM_ID", "EVIDENCE_REFS"}
        joined = repr(payload)
        for banned in ("prompt", "command", "shell", "argv", "token", "secret"):
            assert banned not in joined.lower()


class TestDeliveryOutcomes:
    def test_full_lifecycle_delivered(self, tmp_path):
        from a_conductor import sidecar_codex_bridge as scb

        log = tmp_path / "events.jsonl"
        steer = _steer("evt-chatgpt-sidecar-life00000000001", "2026-09-30T10:00:00+00:00")
        sr.append_event(log, steer)
        events = sr.read_events(log).events
        transport = FakeTransport()
        outcome = _project(events, transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERED"
        assert outcome.original_event_id == steer.event_id
        assert outcome.observed_thread_id == "codex-thread-7"
        assert outcome.observed_queue_ref == "queue-0001"
        assert transport.observe_calls == 1
        assert transport.submit_calls == 1
        receipt = scb.build_ack_receipt(
            steer,
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0002",
            created_at="2026-09-30T10:05:00+00:00",
            result_refs=("runs/WO-P1-573/steer-1/result.md",),
        )
        scb.emit_receipt(log, receipt)
        restored = sr.read_events(log).events
        assert [event.event_type for event in restored] == [
            "CODEX_STEER_REQUEST",
            "SIDECAR_RESULT_RECEIPT",
        ]
        assert restored[1].evidence_refs == (
            f"relay-event:{steer.event_id}",
            "runs/WO-P1-573/steer-1/result.md",
        )

    def test_no_candidate_returns_none(self):
        assert _project(()) is None

    def test_delivery_unknown_is_preserved_never_retried(self):
        transport = FakeTransport(submit_error=RuntimeError("connection dropped"))
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"
        assert outcome.observed_thread_id is None
        assert transport.submit_calls == 1

    def test_garbage_submit_response_is_delivery_unknown(self):
        transport = FakeTransport()
        transport.submit = {"delivery": "MAYBE"}
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"

    def test_unsafe_submit_text_is_delivery_unknown(self):
        transport = FakeTransport()
        transport.submit = {"delivery": "DELIVERED", "thread_id": "t\x1b"}
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"

    def test_rejected_delivery_is_recorded_without_retry(self):
        transport = FakeTransport(submit={"delivery": "REJECTED"})
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "REJECTED"
        assert transport.submit_calls == 1


class TestAckReceipt:
    def test_receipt_references_original_event_id_in_evidence_refs(self):
        from a_conductor import sidecar_codex_bridge as scb

        original = _envelope()
        receipt = scb.build_ack_receipt(
            original,
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0002",
            created_at="2026-09-30T10:05:00+00:00",
        )
        assert receipt.event_type == "SIDECAR_RESULT_RECEIPT"
        assert f"relay-event:{original.event_id}" in receipt.evidence_refs
        assert receipt.evidence_refs[0] == f"relay-event:{original.event_id}"

    def test_receipt_carries_lane_binding_from_original(self):
        from a_conductor import sidecar_codex_bridge as scb

        original = _envelope()
        receipt = scb.build_ack_receipt(
            original,
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0002",
            created_at="2026-09-30T10:05:00+00:00",
        )
        assert receipt.task_id == original.task_id
        assert receipt.claim_id == original.claim_id
        assert receipt.repo == original.repo
        assert receipt.worktree == original.worktree
        assert receipt.head_sha == original.head_sha

    def test_receipt_is_observed_folded_evidence_only(self):
        from a_conductor import sidecar_codex_bridge as scb

        receipt = scb.build_ack_receipt(
            _envelope(),
            source_thread_id="sidecar-thread-1",
            source_turn_id="turn-0002",
            created_at="2026-09-30T10:05:00+00:00",
        )
        mapping = receipt.to_mapping()
        assert set(mapping) <= {
            "EVENT_ID",
            "EVENT_TYPE",
            "SOURCE_SURFACE",
            "SOURCE_THREAD_ID",
            "SOURCE_TURN_ID",
            "TASK_ID",
            "CLAIM_ID",
            "REPO",
            "WORKTREE",
            "HEAD_SHA",
            "PRIORITY",
            "EVIDENCE_REFS",
            "CREATED_AT",
            "REQUESTED_CAPABILITY",
            "DEVICE_CONTEXT",
        }
        assert "APPROVED" not in mapping
        assert "STATUS" not in mapping

    def test_receipt_requires_bound_original(self):
        from a_conductor import sidecar_codex_bridge as scb

        unbound = dataclasses.replace(_envelope(), task_id=None)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                unbound,
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_receipt_rejects_url_result_refs(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(srb_or_bridge_error()) as excinfo:
            scb.build_ack_receipt(
                _envelope(),
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
                result_refs=("https://share.example.com/leak",),
            )
        assert _code(excinfo) in {"BRIDGE_POINTER_INVALID", "RELAY_ENVELOPE_INVALID"}


def srb_or_bridge_error():
    from a_conductor import sidecar_codex_bridge as scb

    return (scb.BridgeFailureError, sr.RelayCarrierError)


class TestFailureTaxonomy:
    def test_bridge_failure_codes_match_wo_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        assert scb.BRIDGE_FAILURE_CODES == WO_BRIDGE_FAILURE_CODES

    def test_bridge_errors_are_code_only(self):
        from a_conductor import sidecar_codex_bridge as scb

        for code in sorted(scb.BRIDGE_FAILURE_CODES):
            error = scb.BridgeFailureError(code)
            assert str(error) == code
            assert error.code == code


class TestStructuralContract:
    def test_stdlib_only_no_network_subprocess_private_storage(self):
        tree = ast.parse(MODULE_SOURCE_PATH.read_text(encoding="utf-8"))
        allowed = {
            "__future__",
            "dataclasses",
            "datetime",
            "re",
            "typing",
            "unicodedata",
            "a_conductor",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] in allowed
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] in allowed
            elif isinstance(node, ast.Call):
                name = (
                    node.func.id
                    if isinstance(node.func, ast.Name)
                    else node.func.attr
                    if isinstance(node.func, ast.Attribute)
                    else ""
                )
                assert name not in {
                    "Popen",
                    "system",
                    "urlopen",
                    "requests",
                    "socket",
                    "connect",
                    "send",
                    "recv",
                    "run",
                    "open",
                    "write",
                    "write_text",
                    "write_bytes",
                    "mkdir",
                    "unlink",
                    "remove",
                    "chmod",
                    "rename",
                    "Cursor",
                    "execute",
                }

    def test_no_authority_api_names(self):
        tree = ast.parse(MODULE_SOURCE_PATH.read_text(encoding="utf-8"))
        forbidden = (
            "claim",
            "lease",
            "schedul",
            "dispatch",
            "review",
            "merge",
            "complete",
            "approve",
            "cancel",
            "retry",
            "execute",
        )
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lowered = node.name.lower()
                for token in forbidden:
                    assert token not in lowered

    def test_module_source_hygiene(self):
        raw = MODULE_SOURCE_PATH.read_bytes()
        canonical = raw.replace(b"\r\n", b"\n")
        canonical.decode("utf-8", errors="strict")
        assert b"\r" not in canonical
        assert canonical.endswith(b"\n")
        text = canonical.decode("utf-8")
        assert "\ufffd" not in text
        for line in text.splitlines():
            assert line == line.rstrip(), repr(line)


class TestOpaqueCrossDevicePaths:
    def test_windows_worktree_round_trips_opaquely(self):
        from a_conductor import sidecar_codex_bridge as scb

        worktree = r"A:\GitHub\_worktrees\wo573-win"
        candidate = sr.envelope_from_mapping(_payload(WORKTREE=worktree))
        scb.revalidate_candidate(candidate, _facts(worktree=worktree))
        transport = FakeTransport()
        outcome = scb.project_steer_candidate(
            [candidate],
            facts=_facts(worktree=worktree),
            surface=_surface(),
            accepted_versions=ACCEPTED_VERSIONS,
            transport=transport,
        )
        assert outcome is not None
        assert outcome.delivery == "DELIVERED"

    def test_no_path_normalization_across_devices(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = sr.envelope_from_mapping(_payload(WORKTREE=r"A:\GitHub\_worktrees\wo573-win"))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(
                candidate, _facts(worktree="A:/GitHub/_worktrees/wo573-win")
            )
        assert _code(excinfo) == "CONTEXT_DRIFT"

    def test_nonexistent_foreign_path_is_never_resolved(self):
        from a_conductor import sidecar_codex_bridge as scb

        worktree = "/definitely/not/resolved/anywhere"
        candidate = sr.envelope_from_mapping(_payload(WORKTREE=worktree))
        scb.revalidate_candidate(candidate, _facts(worktree=worktree))

    def test_different_device_worktree_is_context_drift(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = sr.envelope_from_mapping(_payload(WORKTREE=r"A:\GitHub\_worktrees\wo573-win"))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(
                candidate, _facts(worktree="/Users/dev/GitHub/_worktrees/wo573-mac")
            )
        assert _code(excinfo) == "CONTEXT_DRIFT"
