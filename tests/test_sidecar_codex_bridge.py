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

Repair round (independent review exec-muo0bmr3-cic312cp) adds:

20. all-``None`` :class:`LiveBindingFacts` fails closed
    (``CONTEXT_DRIFT``) — zero live facts never bypass revalidation;
21. lane-scoped checkpoint recovery — a requested lane cannot recover
    another lane's checkpoint and a scope without a match fails closed;
22. untrusted-transport error taxonomy normalization — errors raised
    by the transport seam (forged ``BridgeFailureError`` included) are
    bridge-owned seam failures, never caller-selected taxonomy;
23. writer/steerable blocker precedence over unsafe thread-id text;
24. no silent evidence-ref truncation; padded/overlong/duplicate refs
    fail closed bridge-side (carrier-equivalent strictness);
25. ``DELIVERY_UNKNOWN`` preserves the already-observed thread id;
26. expanded structural forbidden-call set (eval/exec/compile/
    ``__import__``/popen and other command/network/storage forms).

P2 repair round (integrator CHANGES_REQUIRED exec-muo0bmr3 follow-up)
adds:

27. untrusted returned-VALUE taxonomy — user-defined mapping/``str``
    subclass code in transport-returned objects (overridden ``get`` /
    ``__eq__`` / ``__iter__``, hostile keys included) never executes
    after the trusted transport-call wrapper and never mints bridge
    codes: hostile observe returns are ``BRIDGE_SURFACE_OFFLINE``
    (unsafe plain identity text stays ``BRIDGE_AMBIGUOUS_TARGET``),
    hostile submit returns are ``DELIVERY_UNKNOWN``.

WO-P1-575 generation-2 hardening round adds:

28. carrier-parity synthetic evidence-ref rejection — secret-token-
    shaped, PEM-marker, and Cc/Cf/Co/Cs unsafe-Unicode refs fail closed
    ``BRIDGE_POINTER_INVALID`` before any observe/submit/append, and
    the composed ``relay-event:`` receipt ref gets the same bridge-side
    gate before any carrier append;
29. typed fail-closed synthetic CREATED_AT validation — non-string,
    invalid-ISO, naive, padded, unsafe, and overlong values fail with
    the stable carrier code in checkpoint chronology, steer selection,
    and the full projection path (transport call count stays zero),
    while aware offset-instant ordering stays deterministic.
"""

from __future__ import annotations

import ast
import dataclasses
import itertools
from datetime import datetime, timezone
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


def _checkpoint(
    event_id: str, created_at: str, **overrides: object
) -> sr.RelayEnvelope:
    return sr.envelope_from_mapping(
        _payload(
            EVENT_TYPE="SIDECAR_CHECKPOINT",
            EVENT_ID=event_id,
            CREATED_AT=created_at,
            **overrides,
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


class _RawReturnTransport:
    """Transport seam that returns caller-supplied objects unmodified.

    Unlike :class:`FakeTransport` this performs no ``dict()`` copy, so
    a test can hand the bridge the exact hostile object shape the
    untrusted transport is alleged to return.
    """

    def __init__(self, observe: object = None, submit: object = None) -> None:
        self._observe = observe if observe is not None else dict(_HEALTHY_OBSERVATION)
        self._submit = submit
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, kind: str, payload: dict) -> object:
        self.calls.append((kind, dict(payload)))
        if kind == "observe":
            return self._observe
        if kind == "submit":
            return self._submit
        raise AssertionError("unexpected transport kind")

    @property
    def observe_calls(self) -> int:
        return sum(1 for kind, _ in self.calls if kind == "observe")

    @property
    def submit_calls(self) -> int:
        return sum(1 for kind, _ in self.calls if kind == "submit")


_HEALTHY_OBSERVATION = {
    "reachable": True,
    "target_resolved": True,
    "active_writer": False,
    "steerable": True,
    "thread_id": "codex-thread-7",
}


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


class TestLaneScopedCheckpointRecovery:
    def test_scoped_recovery_cannot_return_foreign_lane_checkpoint(self):
        from a_conductor import sidecar_codex_bridge as scb

        other_claim = "WO-P1-573-SIDECAR-BRIDGE-WIN-002"
        lane_a = _checkpoint(
            "evt-chatgpt-sidecar-ck200000000001",
            "2026-09-30T11:00:00+00:00",
        )
        lane_b = _checkpoint(
            "evt-chatgpt-sidecar-ck200000000002",
            "2026-09-30T10:00:00+00:00",
            CLAIM_ID=other_claim,
        )
        events = [lane_a, lane_b]
        assert scb.recover_checkpoint(events).event_id == lane_a.event_id
        recovered = scb.recover_checkpoint(events, claim_id=other_claim)
        assert recovered is not None
        assert recovered.event_id == lane_b.event_id

    def test_scope_without_match_fails_closed_none(self):
        from a_conductor import sidecar_codex_bridge as scb

        events = [
            _checkpoint("evt-chatgpt-sidecar-ck200000000003", "2026-09-30T10:00:00+00:00")
        ]
        assert scb.recover_checkpoint(events, claim_id="WO-P1-999-NO-SUCH-CLAIM") is None
        assert scb.recover_checkpoint(events, task_id="WO-P1-999") is None
        assert scb.recover_checkpoint(events, source_thread_id="no-such-thread") is None

    def test_multi_producer_thread_scope_selects_requested_lane_only(self):
        from a_conductor import sidecar_codex_bridge as scb

        mac = _checkpoint(
            "evt-chatgpt-sidecar-ck200000000004",
            "2026-09-30T12:00:00+00:00",
            SOURCE_THREAD_ID="sidecar-thread-mac",
        )
        win = sr.envelope_from_mapping(
            _payload(
                EVENT_TYPE="SIDECAR_CHECKPOINT",
                EVENT_ID="evt-codex-ck200000000005",
                SOURCE_SURFACE="codex",
                SOURCE_THREAD_ID="codex-lane-win",
                CLAIM_ID="WO-P1-573-SIDECAR-BRIDGE-WIN-002",
                CREATED_AT="2026-09-30T09:00:00+00:00",
            )
        )
        events = [mac, win]
        recovered = scb.recover_checkpoint(events, source_thread_id="codex-lane-win")
        assert recovered is not None
        assert recovered.event_id == "evt-codex-ck200000000005"
        combined = scb.recover_checkpoint(
            events,
            task_id=TASK_ID,
            claim_id=CLAIM_ID,
            source_thread_id="sidecar-thread-mac",
        )
        assert combined is not None
        assert combined.event_id == "evt-chatgpt-sidecar-ck200000000004"
        assert (
            scb.recover_checkpoint(
                events, claim_id=CLAIM_ID, source_thread_id="codex-lane-win"
            )
            is None
        )

    def test_scoped_recovery_keeps_deterministic_newest_within_lane(self):
        from a_conductor import sidecar_codex_bridge as scb

        older = _checkpoint("evt-chatgpt-sidecar-ck200000000006", "2026-09-30T10:00:00+00:00")
        newer = _checkpoint("evt-chatgpt-sidecar-ck200000000007", "2026-09-30T11:00:00+00:00")
        for shuffle in itertools.permutations([newer, older]):
            recovered = scb.recover_checkpoint(shuffle, claim_id=CLAIM_ID)
            assert recovered is not None
            assert recovered.event_id == "evt-chatgpt-sidecar-ck200000000007"


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

    def test_all_none_facts_fail_closed_context_drift(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.revalidate_candidate(_envelope(), scb.LiveBindingFacts())
        assert _code(excinfo) == "CONTEXT_DRIFT"
        assert _code(excinfo) not in scb.BRIDGE_FAILURE_CODES

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

    def test_writer_blocker_precedence_over_unsafe_thread_text(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": True, "steerable": True, "thread_id": "thread\x1b[31m"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_ACTIVE_WRITER"
        assert transport.submit_calls == 0

    def test_not_steerable_precedence_over_unsafe_thread_text(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": False, "steerable": False, "thread_id": "thread\x1b[31m"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_NOT_STEERABLE"
        assert transport.submit_calls == 0


class TestUntrustedTransportTaxonomy:
    def test_forged_bridge_error_on_observe_is_normalized_offline(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(
            observe_error=scb.BridgeFailureError("BRIDGE_NOT_STEERABLE")
        )
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"

    def test_forged_bridge_error_on_submit_is_delivery_unknown(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(
            submit_error=scb.BridgeFailureError("BRIDGE_NOT_STEERABLE")
        )
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"
        assert transport.submit_calls == 1

    def test_bridge_owned_classification_codes_are_not_masked(self):
        from a_conductor import sidecar_codex_bridge as scb

        transport = FakeTransport(observe={"reachable": True, "target_resolved": True, "active_writer": True, "steerable": True, "thread_id": "codex-thread-7"})
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_ACTIVE_WRITER"
        assert transport.submit_calls == 0


class TestUntrustedReturnValueTaxonomy:
    """Transport-RETURNED values cannot execute code or mint taxonomy.

    The seam wrapper normalizes errors raised DURING the transport
    call, but classification used to invoke methods on the returned
    objects themselves (``get`` on mapping subclasses, ``__eq__`` /
    ``__iter__`` on ``str`` subclasses, key ``__eq__`` during lookups),
    letting untrusted code forge bridge-owned failure codes after the
    trusted wrapper. Every test here asserts both the bridge-owned
    normalized code and that the hostile override never executed.
    """

    def test_mapping_subclass_get_cannot_forge_observe_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        class ForgedGetObservation(dict):
            def get(self, key, default=None):
                self.touched = True
                raise scb.BridgeFailureError("BRIDGE_ACTIVE_WRITER")

        hostile = ForgedGetObservation()
        hostile.touched = False
        transport = _RawReturnTransport(observe=hostile)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"
        assert hostile.touched is False
        assert transport.submit_calls == 0

    def test_mapping_subclass_get_cannot_forge_submit_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        class ForgedGetResponse(dict):
            def get(self, key, default=None):
                if key == "delivery":
                    self.touched = True
                    raise scb.BridgeFailureError("BRIDGE_ACTIVE_WRITER")
                return dict.get(self, key, default)

        hostile = ForgedGetResponse()
        hostile.touched = False
        transport = _RawReturnTransport(submit=hostile)
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"
        assert outcome.observed_thread_id == "codex-thread-7"
        assert transport.submit_calls == 1
        assert hostile.touched is False

    def test_hostile_thread_text_cannot_forge_observe_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        class EvilIterStr(str):
            executed = False

            def __iter__(self):
                type(self).executed = True
                raise scb.BridgeFailureError("BRIDGE_NOT_STEERABLE")

        observation = {
            "reachable": True,
            "target_resolved": True,
            "active_writer": False,
            "steerable": True,
            "thread_id": EvilIterStr("codex-thread-7"),
        }
        transport = _RawReturnTransport(observe=observation)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_AMBIGUOUS_TARGET"
        assert EvilIterStr.executed is False
        assert transport.submit_calls == 0

    def test_hostile_delivery_text_cannot_forge_submit_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        class EvilEqStr(str):
            executed = False

            def __eq__(self, other):
                type(self).executed = True
                raise scb.BridgeFailureError("BRIDGE_ACTIVE_WRITER")

            __hash__ = str.__hash__

        response = {
            "delivery": EvilEqStr("DELIVERED"),
            "thread_id": "codex-thread-7",
            "queue_ref": "queue-0001",
        }
        transport = _RawReturnTransport(submit=response)
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"
        assert EvilEqStr.executed is False
        assert transport.submit_calls == 1

    def test_hostile_mapping_key_cannot_forge_observe_taxonomy(self):
        from a_conductor import sidecar_codex_bridge as scb

        class EvilEqKey(str):
            executed = False

            def __eq__(self, other):
                type(self).executed = True
                raise scb.BridgeFailureError("BRIDGE_NOT_STEERABLE")

            __hash__ = str.__hash__

        observation = {
            EvilEqKey("reachable"): True,
            "target_resolved": True,
            "active_writer": False,
            "steerable": True,
            "thread_id": "codex-thread-7",
        }
        transport = _RawReturnTransport(observe=observation)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_SURFACE_OFFLINE"
        assert EvilEqKey.executed is False
        assert transport.submit_calls == 0

    def test_plain_non_text_thread_id_stays_ambiguous(self):
        from a_conductor import sidecar_codex_bridge as scb

        observation = {
            "reachable": True,
            "target_resolved": True,
            "active_writer": False,
            "steerable": True,
            "thread_id": 7,
        }
        transport = _RawReturnTransport(observe=observation)
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([_envelope()], transport=transport)
        assert _code(excinfo) == "BRIDGE_AMBIGUOUS_TARGET"


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

    def test_over_limit_evidence_refs_fail_instead_of_silent_truncation(self):
        from a_conductor import sidecar_codex_bridge as scb

        refs = tuple(
            f"docs/work-orders/WO-P1-573/ref-{index}"
            for index in range(sr.MAX_EVIDENCE_REFS + 1)
        )
        candidate = dataclasses.replace(_envelope(), evidence_refs=refs)
        assert len(candidate.evidence_refs) > sr.MAX_EVIDENCE_REFS
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_padded_evidence_ref_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(
            _envelope(), evidence_refs=(" docs/work-orders/WO-P1-573/padded ",)
        )
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_overlong_evidence_ref_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(_envelope(), evidence_refs=("x" * 4097,))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_duplicate_evidence_refs_are_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(_envelope(), evidence_refs=(WO_REF, WO_REF))
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
        assert transport.submit_calls == 1

    def test_delivery_unknown_preserves_observed_thread_id(self):
        transport = FakeTransport(submit_error=RuntimeError("connection dropped"))
        outcome = _project([_envelope()], transport=transport)
        assert outcome is not None
        assert outcome.delivery == "DELIVERY_UNKNOWN"
        assert outcome.observed_thread_id == "codex-thread-7"
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

    def test_receipt_padded_result_ref_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                _envelope(),
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
                result_refs=(" runs/WO-P1-573/padded ",),
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_receipt_overlong_result_ref_is_pointer_invalid(self):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                _envelope(),
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
                result_refs=("x" * 4097,),
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_receipt_over_limit_result_refs_fail_closed(self):
        from a_conductor import sidecar_codex_bridge as scb

        result_refs = tuple(
            f"runs/WO-P1-573/r-{index}" for index in range(sr.MAX_EVIDENCE_REFS)
        )
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                _envelope(),
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
                result_refs=result_refs,
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"


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
                is_regex_compile = (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "compile"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "re"
                )
                if is_regex_compile:
                    continue
                assert name not in {
                    "eval",
                    "exec",
                    "compile",
                    "__import__",
                    "import_module",
                    "Popen",
                    "popen",
                    "system",
                    "check_call",
                    "check_output",
                    "spawn",
                    "fork",
                    "execv",
                    "kill",
                    "terminate",
                    "urlopen",
                    "requests",
                    "socket",
                    "connect",
                    "create_connection",
                    "getaddrinfo",
                    "send",
                    "recv",
                    "run",
                    "open",
                    "read_text",
                    "read_bytes",
                    "write",
                    "write_text",
                    "write_bytes",
                    "mkdir",
                    "makedirs",
                    "rmdir",
                    "unlink",
                    "remove",
                    "touch",
                    "chmod",
                    "chown",
                    "rename",
                    "symlink",
                    "truncate",
                    "Cursor",
                    "execute",
                    "executemany",
                    "executescript",
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


_SECRET_SHAPED_REFS = (
    "runs/WO-P1-575/ghp_ABCDEFGHIJKLMNOPQRST",
    "runs/WO-P1-575/gho_ABCDEFGHIJKLMNOPQRST",
    "runs/WO-P1-575/ghs_ABCDEFGHIJKLMNOPQRST",
    "runs/WO-P1-575/github_pat_ABCDEFGHIJKLMNOPQRST",
    "runs/WO-P1-575/sk-ABCDEFGHIJKLMNOPQRST",
    "runs/WO-P1-575/xoxb-1234567890abcdef123456",
    "runs/WO-P1-575/AKIAABCDEFGHIJKLMNOP",
    "runs/WO-P1-575/AIzaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
)

_PEM_MARKER_REFS = (
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "keys/-----begin ec private key-----",
)

_UNSAFE_UNICODE_REFS = (
    "docs/WO-P1-575/ref\x1b[31m",
    "docs/WO-P1-575/ref\u200b",
    "docs/WO-P1-575/ref\ue000",
    "docs/WO-P1-575/ref\U000e0001",
    "docs/WO-P1-575/ref\ud800",
)

_MALFORMED_CREATED_AT_VALUES = (
    1759236000,
    None,
    datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc),
    "not-a-timestamp",
    "2026-09-30T10:00:00",
    "2026-09-30T10:00:00Zulu",
    " 2026-09-30T10:00:00+00:00",
    "2026-09-30T10:00:00+00:00 ",
    "2026-09-30T10:00:00+00:00\u200b",
    "2026-09-30T10:00:00+00:00" + "0" * 64,
    "2026-09-30 10:00:00+00:00",
)


class TestSyntheticEvidenceRefCarrierParity:
    """WO-P1-575 §5.A — carrier-parity rejection for synthetic refs.

    Synthetic envelopes constructed outside the carrier (e.g. via
    ``dataclasses.replace``) must not bypass the carrier's
    sensitive-text rules: secret-token-shaped, PEM-marker, and
    unsafe-Unicode refs fail closed bridge-side before observe,
    submit, or append, without echoing the ref text.
    """

    @pytest.mark.parametrize("ref", _SECRET_SHAPED_REFS)
    def test_secret_token_shaped_ref_is_pointer_invalid(self, ref):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(_envelope(), evidence_refs=(ref,))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    @pytest.mark.parametrize("ref", _PEM_MARKER_REFS)
    def test_pem_marker_ref_is_pointer_invalid(self, ref):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(_envelope(), evidence_refs=(ref,))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    @pytest.mark.parametrize("ref", _UNSAFE_UNICODE_REFS)
    def test_unsafe_unicode_ref_is_pointer_invalid(self, ref):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(_envelope(), evidence_refs=(ref,))
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_steer_projection(candidate)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_unsafe_ref_fails_before_any_transport_call(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(
            _envelope(), evidence_refs=("docs/WO-P1-575/ref\u200b",)
        )
        transport = FakeTransport()
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            _project([candidate], transport=transport)
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"
        assert transport.calls == []
        assert transport.observe_calls == 0
        assert transport.submit_calls == 0

    @pytest.mark.parametrize("ref", _SECRET_SHAPED_REFS[:3] + _PEM_MARKER_REFS[:2])
    def test_receipt_rejects_sensitive_result_refs(self, ref):
        from a_conductor import sidecar_codex_bridge as scb

        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                _envelope(),
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
                result_refs=(ref,),
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"

    def test_receipt_rejects_unsafe_original_event_id_ref(self):
        from a_conductor import sidecar_codex_bridge as scb

        original = dataclasses.replace(
            _envelope(), event_id="evt-chatgpt-sidecar-bad\u200bref0001"
        )
        with pytest.raises(scb.BridgeFailureError) as excinfo:
            scb.build_ack_receipt(
                original,
                source_thread_id="sidecar-thread-1",
                source_turn_id="turn-0002",
                created_at="2026-09-30T10:05:00+00:00",
            )
        assert _code(excinfo) == "BRIDGE_POINTER_INVALID"


class TestSyntheticCreatedAtValidation:
    """WO-P1-575 §5.B — typed fail-closed synthetic CREATED_AT gates.

    Manually constructed envelopes with malformed CREATED_AT must fail
    with the stable carrier code before ordering or transport; no raw
    TypeError/ValueError may escape checkpoint chronology, steer
    selection, or the full projection path. Valid aware ISO-8601
    timestamps with different offsets stay deterministic.
    """

    @pytest.mark.parametrize("created_at", _MALFORMED_CREATED_AT_VALUES)
    def test_checkpoint_malformed_created_at_fails_typed(self, created_at):
        from a_conductor import sidecar_codex_bridge as scb

        checkpoint = dataclasses.replace(
            _checkpoint(
                "evt-chatgpt-sidecar-ck5750000000001",
                "2026-09-30T10:00:00+00:00",
            ),
            created_at=created_at,
        )
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            scb.recover_checkpoint([checkpoint])
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_checkpoint_mixed_aware_naive_chronology_fails_typed(self):
        from a_conductor import sidecar_codex_bridge as scb

        aware = _checkpoint(
            "evt-chatgpt-sidecar-ck5750000000002", "2026-09-30T10:00:00+00:00"
        )
        naive = dataclasses.replace(
            _checkpoint(
                "evt-chatgpt-sidecar-ck5750000000003", "2026-09-30T09:00:00+00:00"
            ),
            created_at="2026-09-30T11:00:00",
        )
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            scb.recover_checkpoint([aware, naive])
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    @pytest.mark.parametrize("created_at", _MALFORMED_CREATED_AT_VALUES)
    def test_steer_malformed_created_at_fails_typed_before_ordering(
        self, created_at
    ):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(
            _steer(
                "evt-chatgpt-sidecar-st5750000000001", "2026-09-30T10:00:00+00:00"
            ),
            created_at=created_at,
        )
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            scb.select_steer_candidate([candidate])
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"

    def test_full_projection_malformed_created_at_never_calls_transport(self):
        from a_conductor import sidecar_codex_bridge as scb

        candidate = dataclasses.replace(
            _steer(
                "evt-chatgpt-sidecar-st5750000000002", "2026-09-30T10:00:00+00:00"
            ),
            created_at="2026-09-30T10:00:00",
        )
        transport = FakeTransport()
        with pytest.raises(sr.RelayCarrierError) as excinfo:
            _project([candidate], transport=transport)
        assert _code(excinfo) == "RELAY_ENVELOPE_INVALID"
        assert transport.calls == []

    def test_aware_offset_instants_order_deterministically_in_selection(self):
        from a_conductor import sidecar_codex_bridge as scb

        later = _steer(
            "evt-chatgpt-sidecar-st5750000000003", "2026-09-30T12:00:00+02:00"
        )
        earlier = _steer(
            "evt-chatgpt-sidecar-st5750000000004", "2026-09-30T09:30:00+00:00"
        )
        for shuffle in itertools.permutations([later, earlier]):
            assert scb.select_steer_candidate(shuffle) == earlier

    def test_aware_offset_instants_order_deterministically_in_recovery(self):
        from a_conductor import sidecar_codex_bridge as scb

        same_instant_a = _checkpoint(
            "evt-chatgpt-sidecar-ck5750000000004", "2026-09-30T12:00:00+02:00"
        )
        same_instant_b = _checkpoint(
            "evt-chatgpt-sidecar-ck5750000000005", "2026-09-30T10:00:00+00:00"
        )
        newest = _checkpoint(
            "evt-chatgpt-sidecar-ck5750000000006", "2026-09-30T10:30:00+00:00"
        )
        for shuffle in itertools.permutations(
            [same_instant_a, same_instant_b, newest]
        ):
            recovered = scb.recover_checkpoint(shuffle)
            assert recovered is not None
            assert recovered.event_id == newest.event_id
