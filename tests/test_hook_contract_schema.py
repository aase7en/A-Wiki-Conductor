import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "hook-contract-v1.md"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "hook-contract-v1.schema.json"

EVENT_ID = "hk-0123456789abcdef0123456789abcdef"
OTHER_EVENT_ID = "hk-fedcba9876543210fedcba9876543210"

FORBIDDEN_FIELDS = (
    "prompt",
    "messages",
    "transcript",
    "token",
    "api_key",
    "apikey",
    "secret",
    "secret_value",
    "password",
    "credential_value",
    "cookie",
    "share_url",
    "session_url",
    "argv",
    "command_line",
    "shell_command",
)

FAKE_SECRET_CORPUS = (
    "sk-FAKE0000000000000000000000000000000000",
    "ghp_FAKE0000000000000000000000000000000",
    "xoxb-FAKE-000000000000000000000000",
    "AKIAFAKE0000000000",
    "FAKESESSIONCOOKIE=0000000000000000",
    "-----BEGIN FAKE PRIVATE KEY-----",
    "https://chat.example/FAKE/share/0000",
    "Bearer FAKE000000000000000000000000000",
)

MAX_ENVELOPE_BYTES = 65536

REMOVE = object()


def load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_schema()


@pytest.fixture(scope="module")
def validator(schema) -> Draft202012Validator:
    return Draft202012Validator(schema)


def mutated(base: dict, **changes) -> dict:
    payload = deepcopy(base)
    for key, value in changes.items():
        if value is REMOVE:
            payload.pop(key, None)
        else:
            payload[key] = value
    return payload


def minimal_event() -> dict:
    return {
        "schema_version": "1.0.0",
        "event_id": EVENT_ID,
        "event_type": "process.spawned",
        "hook_class": "OBSERVE",
        "phase": "within",
        "domain": "process",
        "action": "spawned",
        "occurred_at": "2026-09-19T07:48:08Z",
        "source": "srm",
        "source_version": "1.2.3",
        "device_id": "device-01",
        "host_os": "windows",
        "privacy_class": "INTERNAL",
    }


def guard_event(**guard_fields) -> dict:
    guard = {
        "failure_policy": "FAIL_CLOSED",
        "security_scope": False,
        "authority_scope": False,
    }
    guard.update(guard_fields)
    return mutated(
        minimal_event(),
        event_type="security.gate",
        hook_class="GUARD",
        phase="before",
        domain="security",
        action="gate",
        guard=guard,
    )


def command_event(**request_fields) -> dict:
    request = {"request_id": "cmd-0001", "command": "pause"}
    request.update(request_fields)
    return mutated(
        minimal_event(),
        event_type="control.request",
        hook_class="COMMAND",
        phase="before",
        domain="control",
        action="request",
        command_request=request,
    )


def envelope_bytes(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def test_schema_parses_and_is_draft_2020_12(schema) -> None:
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:a-conductor:schema:hook-contract:1.0.0"
    assert schema["additionalProperties"] is False
    assert CONTRACT.exists()
    contract_text = CONTRACT.read_text(encoding="utf-8")
    assert "fake-secret-corpus/1" in contract_text
    for item in FAKE_SECRET_CORPUS:
        assert item in contract_text


def test_minimal_observe_event_is_valid(validator) -> None:
    event = minimal_event()
    assert validator.is_valid(event)
    assert set(event) == {
        "schema_version",
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
    }


OPTIONAL_GROUPS = {
    "lane_task": {
        "lane_id": "lane-a1",
        "task_id": "WO-P1-258",
        "work_order": "WO-P1-258",
        "task_topology": "CONTROL_PLANE_ONLY",
        "authority_repo": "A:/GitHub/A-Wiki-Conductor",
        "execution_repo": "A:/GitHub/SunDayRemoteMCP",
    },
    "repository": {
        "repo": "A-Wiki-Conductor",
        "worktree": "A:/GitHub/_worktrees/A-Wiki-Conductor-hook-0",
        "branch": "feat/wo-p1-258-hook-contract-v1",
        "head_sha": "fe1edad5dcce8b399fac1923a2c49e4f75c1b646",
        "claim_ref": "claims/wo-p1-258",
    },
    "execution": {
        "execution_id": "exec-0001",
        "harness_id": "claude-code-1",
        "model_id": "glm-5.3",
        "effort": "max",
        "state": "RUNNING",
        "duration_ms": 1500,
        "blocker_code": "CONTEXT_DRIFT",
    },
    "ordering": {
        "sequence": 42,
        "dedupe_key": "srm:device-01:42",
    },
    "correlation": {
        "correlation_id": "corr-0001",
        "causation_id": OTHER_EVENT_ID,
    },
    "evidence": {
        "evidence_refs": ["runs/WO-P1-258/author/task.md"],
        "evidence_digest": "0123456789abcdef",
    },
    "presentation": {
        "summary": "process spawned for delegated run",
    },
    "redaction": {
        "command_digest": "0123456789abcdef0123456789abcdef",
        "command_ref": "cmdref-0001",
    },
    "adapter": {
        "event_type": "transport.adapter_capabilities",
        "domain": "transport",
        "action": "adapter_capabilities",
        "adapter": {
            "adapter_id": "kilo-plugin-adapter",
            "adapter_version": "0.1.0",
            "contract_version": "1.0.0",
            "emits": ["transport.adapter_capabilities", "tool.execute.before"],
            "redaction_policy": "fake-secret-corpus/1",
            "supports_sequence": True,
        }
    },
}


@pytest.mark.parametrize("group_name", sorted(OPTIONAL_GROUPS))
def test_optional_groups_are_valid(validator, group_name) -> None:
    payload = mutated(minimal_event(), **OPTIONAL_GROUPS[group_name])
    assert validator.is_valid(payload)


def test_all_optional_groups_together_are_valid(validator) -> None:
    merged: dict = {}
    for group in OPTIONAL_GROUPS.values():
        merged.update(group)
    payload = mutated(minimal_event(), **merged)
    assert validator.is_valid(payload)


@pytest.mark.parametrize(
    "case",
    [
        {"event_id": REMOVE},
        {"event_id": ""},
        {"event_id": "event-0123456789abcdef0123456789abcdef"},
        {"event_id": "hk-0123456789ABCDEF0123456789ABCDEF"},
        {"event_id": "hk-0123456789abcdef"},
        {"event_id": 12345},
    ],
)
def test_invalid_event_identity_rejected(validator, case) -> None:
    assert not validator.is_valid(mutated(minimal_event(), **case))


@pytest.mark.parametrize(
    "case",
    [
        {"hook_class": "MONITOR"},
        {"hook_class": "observe"},
        {"hook_class": REMOVE},
        {"phase": "pre"},
        {"phase": REMOVE},
        {"domain": "runtime"},
        {"domain": REMOVE},
        {"action": "Spawned"},
        {"action": "spawned!"},
        {"action": REMOVE},
        {"event_type": "process"},
        {"event_type": "a.b.c.d"},
        {"event_type": "Process.Spawned"},
        {"event_type": REMOVE},
    ],
)
def test_invalid_class_phase_domain_action_rejected(validator, case) -> None:
    assert not validator.is_valid(mutated(minimal_event(), **case))


@pytest.mark.parametrize(
    "version,expected_valid",
    [
        ("1.0.0", True),
        ("1.1.0", True),
        ("1.12.3", True),
        ("0.9.0", False),
        ("2.0.0", False),
        ("1.0", False),
        ("1.0.0.0", False),
        ("v1.0.0", False),
    ],
)
def test_schema_version_bounds(validator, version, expected_valid) -> None:
    payload = mutated(minimal_event(), schema_version=version)
    assert validator.is_valid(payload) is expected_valid


@pytest.mark.parametrize(
    "case",
    [
        {"sequence": -1},
        {"sequence": "42"},
        {"sequence": 1.5},
        {"sequence": 9007199254740992},
        {"dedupe_key": "has space"},
        {"dedupe_key": ""},
    ],
)
def test_sequence_and_dedupe_constraints(validator, case) -> None:
    assert not validator.is_valid(mutated(minimal_event(), **case))


def test_sequence_zero_and_high_bound_are_valid(validator) -> None:
    assert validator.is_valid(mutated(minimal_event(), sequence=0))
    assert validator.is_valid(
        mutated(minimal_event(), sequence=9007199254740991, dedupe_key="srm:42")
    )


def contract_section(title: str) -> str:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        rf"^#{{2,3}}\s*{re.escape(title)}\s*$(.*?)(?=^#{{2,3}}\s|\Z)",
        text,
        re.M | re.S,
    )
    assert match is not None
    return match.group(1)


def source_queue(events: list) -> list:
    if all("sequence" in event for event in events):
        return sorted(events, key=lambda event: event["sequence"])
    if not any("sequence" in event for event in events):
        return list(events)
    queue = [None] * len(events)
    sequenced = sorted(
        (event for event in events if "sequence" in event),
        key=lambda event: event["sequence"],
    )
    free_slots = [i for i, event in enumerate(events) if "sequence" in event]
    for slot, event in zip(free_slots, sequenced):
        queue[slot] = event
    for i, event in enumerate(events):
        if "sequence" not in event:
            queue[i] = event
    return queue


def merge_projection(queues: list) -> list:
    pending = [list(queue) for queue in queues]
    merged = []
    while any(pending):
        head, idx = min(
            ((queue[0], i) for i, queue in enumerate(pending) if queue),
            key=lambda pair: (
                pair[0]["occurred_at"],
                pair[0]["source"],
                pair[0]["event_id"],
            ),
        )
        merged.append(head)
        pending[idx].pop(0)
    return merged


def stream_key(event: dict, session_ref: str) -> tuple:
    return (event["source"], event["device_id"], session_ref)


def dedupe_identity(event: dict) -> str:
    return event["dedupe_key"] if "dedupe_key" in event else event["event_id"]


class BoundedReplayDedupe:
    def __init__(self, window_s: int = 1800) -> None:
        self.window_s = min(86400, max(300, window_s))
        self._seen: dict = {}

    def observe(self, event: dict, now_s: int) -> bool:
        identity = dedupe_identity(event)
        first_seen = self._seen.get(identity)
        duplicate = first_seen is not None and (now_s - first_seen) < self.window_s
        if not duplicate:
            self._seen[identity] = now_s
        return duplicate


class StreamProjection:
    def __init__(self, source: str, device_id: str, session_ref: str) -> None:
        self.stream = (source, device_id, session_ref)
        self.pending = []
        self.emitted = []
        self.last_emitted_sequence = None
        self.metadata = []

    def append(self, event: dict) -> None:
        sequence = event.get("sequence")
        if (
            sequence is not None
            and self.last_emitted_sequence is not None
            and sequence <= self.last_emitted_sequence
        ):
            self.metadata.append(
                ("sequence_inversion", event["event_id"], sequence, self.last_emitted_sequence)
            )
        self.pending.append(event)

    def emit(self) -> None:
        ordered = source_queue(self.pending)
        previous = self.last_emitted_sequence
        for event in ordered:
            sequence = event.get("sequence")
            if sequence is not None:
                if previous is not None and sequence > previous + 1:
                    self.metadata.append(
                        ("sequence_gap", event["event_id"], previous, sequence)
                    )
                previous = sequence
        self.last_emitted_sequence = previous
        self.emitted.extend(ordered)
        self.pending = []

    @property
    def history(self) -> list:
        return list(self.emitted)


def event_type_semantic_mismatch(event: dict) -> bool:
    prefix = f"{event.get('domain')}.{event.get('action')}"
    event_type = event.get("event_type", "")
    return not (event_type == prefix or event_type.startswith(prefix + "."))


def test_ordering_section_forbids_timestamp_first_global_sort() -> None:
    section = contract_section("5. Ordering")
    assert "k-way merge" in section
    assert "MUST NOT reorder" in section
    assert "observed interleaving, not causal" in section
    assert "(occurred_at, source, sequence" not in section
    assert "sorts by" not in section


def test_kway_merge_preserves_source_local_sequence_under_clock_inversion(
    validator,
) -> None:
    srm_10 = mutated(
        minimal_event(),
        event_id="hk-" + "10" * 16,
        sequence=10,
        occurred_at="2026-09-19T07:00:20Z",
    )
    srm_11 = mutated(
        minimal_event(),
        event_id="hk-" + "11" * 16,
        sequence=11,
        occurred_at="2026-09-19T07:00:05Z",
    )
    kilo_0 = mutated(
        minimal_event(),
        event_id="hk-" + "0c" * 16,
        source="kilo",
        occurred_at="2026-09-19T07:00:12Z",
    )
    for event in (srm_10, srm_11, kilo_0):
        assert validator.is_valid(event)

    merged = merge_projection(
        [source_queue([srm_10, srm_11]), source_queue([kilo_0])]
    )
    assert [event["event_id"] for event in merged] == [
        kilo_0["event_id"],
        srm_10["event_id"],
        srm_11["event_id"],
    ]

    legacy_global_sort = sorted(
        (srm_10, srm_11, kilo_0),
        key=lambda event: (
            event["occurred_at"],
            event["source"],
            event.get("sequence", -1),
            event["event_id"],
        ),
    )
    assert legacy_global_sort.index(srm_11) < legacy_global_sort.index(srm_10)


def test_mixed_sequence_queue_keeps_arrival_slots() -> None:
    seq_5 = mutated(minimal_event(), event_id="hk-" + "aa" * 16, sequence=5)
    no_seq = mutated(minimal_event(), event_id="hk-" + "bb" * 16)
    seq_1 = mutated(minimal_event(), event_id="hk-" + "cc" * 16, sequence=1)
    queue = source_queue([seq_5, no_seq, seq_1])
    assert [event["event_id"] for event in queue] == [
        seq_1["event_id"],
        no_seq["event_id"],
        seq_5["event_id"],
    ]
    assert "sequence" not in no_seq


def test_guard_requires_explicit_failure_policy(validator) -> None:
    missing_guard = mutated(
        minimal_event(),
        event_type="security.gate",
        hook_class="GUARD",
        domain="security",
        action="gate",
    )
    assert not validator.is_valid(missing_guard)

    guard_without_policy = guard_event()
    guard_without_policy["guard"].pop("failure_policy")
    assert validator.is_valid(guard_event())
    assert not validator.is_valid(guard_without_policy)
    assert validator.is_valid(
        guard_event(failure_policy="FAIL_OPEN", policy_ref="docs/contracts/hook-contract-v1.md")
    )


def test_guard_requires_explicit_scope_declarations(validator) -> None:
    ambiguous = guard_event()
    ambiguous["guard"].pop("security_scope")
    assert not validator.is_valid(ambiguous)

    ambiguous_authority = guard_event()
    ambiguous_authority["guard"].pop("authority_scope")
    assert not validator.is_valid(ambiguous_authority)

    null_scopes = guard_event(security_scope=None, authority_scope=None)
    assert not validator.is_valid(null_scopes)


def test_security_or_authority_guard_fail_open_rejected(validator) -> None:
    assert not validator.is_valid(
        guard_event(failure_policy="FAIL_OPEN", security_scope=True)
    )
    assert not validator.is_valid(
        guard_event(failure_policy="FAIL_OPEN", authority_scope=True)
    )
    assert validator.is_valid(
        guard_event(failure_policy="FAIL_CLOSED", security_scope=True, authority_scope=True)
    )


def test_ambiguous_guard_cannot_fail_open(validator) -> None:
    undeclared = guard_event(failure_policy="FAIL_OPEN")
    undeclared["guard"].pop("security_scope")
    undeclared["guard"].pop("authority_scope")
    assert not validator.is_valid(undeclared)

    non_guard_with_guard = mutated(
        minimal_event(), guard={"failure_policy": "FAIL_OPEN", "security_scope": True, "authority_scope": True}
    )
    assert not validator.is_valid(non_guard_with_guard)


@pytest.mark.parametrize("field_name", FORBIDDEN_FIELDS)
def test_secret_and_raw_prompt_fields_excluded(validator, schema, field_name) -> None:
    assert field_name not in schema["properties"]
    for corpus_item in FAKE_SECRET_CORPUS:
        assert corpus_item not in SCHEMA_PATH.read_text(encoding="utf-8")
    payload = mutated(minimal_event(), **{field_name: "value"})
    assert not validator.is_valid(payload)


@pytest.mark.parametrize(
    "case",
    [
        {"summary": "x" * 513},
        {"worktree": "w" * 257},
        {"branch": "b" * 257},
        {"event_type": "t" * 97},
        {"evidence_refs": [f"ref-{i:02d}" for i in range(17)]},
        {"evidence_refs": ["same-ref", "same-ref"]},
        {"state": "RUNNING" * 10},
    ],
)
def test_oversized_strings_and_arrays_rejected(validator, case) -> None:
    payload = mutated(minimal_event(), **case)
    assert not validator.is_valid(payload)

    oversized = mutated(minimal_event(), worktree="w" * (MAX_ENVELOPE_BYTES + 1))
    assert not validator.is_valid(oversized)
    assert envelope_bytes(oversized) > MAX_ENVELOPE_BYTES


def test_command_cannot_carry_process_or_git_authority(validator) -> None:
    assert validator.is_valid(command_event())

    missing_request = mutated(
        minimal_event(),
        event_type="control.request",
        hook_class="COMMAND",
        domain="control",
        action="request",
    )
    assert not validator.is_valid(missing_request)

    for forbidden in (
        {"argv": ["git", "push"]},
        {"executable": "python.exe"},
        {"shell": "powershell"},
        {"env": {"PATH": "x"}},
        {"git_operation": "force-push"},
        {"pid": 4242},
        {"kill": True},
    ):
        assert not validator.is_valid(command_event(**forbidden)), forbidden

    assert not validator.is_valid(command_event(command="kill_process"))
    assert not validator.is_valid(command_event(command="force_push"))

    observe_with_request = mutated(minimal_event(), command_request={"request_id": "cmd-0001", "command": "pause"})
    assert not validator.is_valid(observe_with_request)


def test_correlation_and_causation_are_identifier_only(validator) -> None:
    valid = mutated(
        minimal_event(), correlation_id="corr-0001", causation_id=OTHER_EVENT_ID
    )
    assert validator.is_valid(valid)

    schema = load_schema()
    assert schema["properties"]["correlation_id"]["type"] == "string"
    assert schema["properties"]["causation_id"]["type"] == "string"

    for case in (
        {"correlation_id": {"event_id": EVENT_ID}},
        {"causation_id": {"event_id": EVENT_ID}},
        {"causation_id": "not-an-event-id"},
        {"causation_id": EVENT_ID.upper().replace("HK-", "hk-")},
        {"correlation_id": "has space"},
        {"correlation_id": [EVENT_ID]},
    ):
        assert not validator.is_valid(mutated(minimal_event(), **case)), case


def test_unknown_optional_field_policy(validator) -> None:
    unknown_field = mutated(minimal_event(), mystery_field="value")
    assert not validator.is_valid(unknown_field)

    future_minor = mutated(minimal_event(), schema_version="1.9.7")
    assert validator.is_valid(future_minor)
    assert not validator.is_valid(mutated(future_minor, mystery_field="value"))


def test_adapter_only_on_observe_events(validator) -> None:
    assert validator.is_valid(mutated(minimal_event(), **OPTIONAL_GROUPS["adapter"]))

    advisory_with_adapter = mutated(
        mutated(
            minimal_event(),
            event_type="advisory.simplify",
            hook_class="ADVISORY",
            domain="advisory",
            action="simplify",
        ),
        adapter=OPTIONAL_GROUPS["adapter"]["adapter"],
    )
    assert not validator.is_valid(advisory_with_adapter)


def test_event_type_matches_domain_and_action_in_fixtures() -> None:
    for payload in (
        minimal_event(),
        guard_event(),
        command_event(),
        mutated(minimal_event(), **OPTIONAL_GROUPS["ordering"]),
    ):
        prefix = f"{payload['domain']}.{payload['action']}"
        assert payload["event_type"] == prefix or payload["event_type"].startswith(prefix + ".")


def test_optional_group_cross_references_point_at_real_sections() -> None:
    section = contract_section("3.2 Optional context groups")
    assert "§9.2" not in section
    assert "§7.2" in section
    assert "`sequence` (§5)" in section
    assert "`dedupe_key` (§4)" in section


def test_dedupe_identity_is_dedupe_key_else_event_id_never_source_sequence() -> None:
    section = contract_section("4. Event identity")
    assert "`source` + `sequence` MUST NOT be used as a fallback duplicate identity" in section
    assert "Distinct `event_id`s MUST NOT be dropped" in section


def test_dedupe_identity_ladder() -> None:
    with_key = mutated(minimal_event(), dedupe_key="upload:batch-9")
    assert dedupe_identity(with_key) == "upload:batch-9"
    assert dedupe_identity(minimal_event()) == EVENT_ID


def test_dedupe_replay_window_defaults_and_clamps() -> None:
    assert BoundedReplayDedupe().window_s == 1800
    assert BoundedReplayDedupe(window_s=1).window_s == 300
    assert BoundedReplayDedupe(window_s=10**9).window_s == 86400


def test_same_source_sequence_two_devices_distinct_event_ids_are_distinct() -> None:
    device_a = mutated(
        minimal_event(), event_id="hk-" + "aa" * 16, device_id="device-01", sequence=7
    )
    device_b = mutated(
        minimal_event(), event_id="hk-" + "bb" * 16, device_id="device-02", sequence=7
    )
    assert (device_a["source"], device_a["sequence"]) == (
        device_b["source"],
        device_b["sequence"],
    )
    assert device_a["event_id"] != device_b["event_id"]

    dedupe = BoundedReplayDedupe()
    assert dedupe.observe(device_a, now_s=0) is False
    assert dedupe.observe(device_b, now_s=1) is False

    assert stream_key(device_a, "session-1") != stream_key(device_b, "session-1")

    merged = merge_projection([source_queue([device_a]), source_queue([device_b])])
    assert [event["event_id"] for event in merged] == [
        device_a["event_id"],
        device_b["event_id"],
    ]


def test_same_stream_sequence_collision_distinct_event_ids_not_dropped() -> None:
    first = mutated(minimal_event(), event_id="hk-" + "c1" * 16, sequence=4)
    second = mutated(minimal_event(), event_id="hk-" + "c2" * 16, sequence=4)
    dedupe = BoundedReplayDedupe()
    assert not dedupe.observe(first, now_s=0)
    assert not dedupe.observe(second, now_s=1)

    projection = StreamProjection("srm", "device-01", "session-9")
    projection.append(first)
    projection.emit()
    projection.append(second)
    assert ("sequence_inversion", second["event_id"], 4, 4) in projection.metadata
    projection.emit()
    assert [event["event_id"] for event in projection.history] == [
        first["event_id"],
        second["event_id"],
    ]


def test_same_event_id_redelivery_is_duplicate() -> None:
    event = mutated(minimal_event(), sequence=3)
    redelivery = mutated(event)
    dedupe = BoundedReplayDedupe()
    assert not dedupe.observe(event, now_s=0)
    assert dedupe.observe(redelivery, now_s=60)
    assert not dedupe.observe(redelivery, now_s=1800)


def test_sequence_restart_with_new_observed_session_is_not_duplicate() -> None:
    session_a = mutated(
        minimal_event(),
        event_id="hk-" + "5e" * 16,
        sequence=5,
        occurred_at="2026-09-19T07:00:01Z",
    )
    session_b = mutated(
        minimal_event(),
        event_id="hk-" + "6f" * 16,
        sequence=5,
        occurred_at="2026-09-19T07:05:01Z",
    )
    dedupe = BoundedReplayDedupe()
    assert not dedupe.observe(session_a, now_s=0)
    assert not dedupe.observe(session_b, now_s=10)

    assert stream_key(session_a, "session-A") != stream_key(session_b, "session-B")

    merged = merge_projection([source_queue([session_a]), source_queue([session_b])])
    assert [event["event_id"] for event in merged] == [
        session_a["event_id"],
        session_b["event_id"],
    ]


def test_explicit_dedupe_key_idempotence_remains_bounded() -> None:
    first = mutated(
        minimal_event(), event_id="hk-" + "d4" * 16, dedupe_key="upload:batch-9"
    )
    retry = mutated(
        minimal_event(), event_id="hk-" + "e5" * 16, dedupe_key="upload:batch-9"
    )
    unrelated = mutated(minimal_event(), event_id="hk-" + "f6" * 16)
    dedupe = BoundedReplayDedupe()
    assert not dedupe.observe(first, now_s=0)
    assert dedupe.observe(retry, now_s=30)
    assert not dedupe.observe(unrelated, now_s=31)
    assert not dedupe.observe(retry, now_s=1800 + 30)


def test_ordering_stream_domain_is_never_bare_source() -> None:
    section = contract_section("5. Ordering")
    assert "(source, device_id," in section
    assert "bare `source`" in section
    assert "restart" in section
    assert "MUST NOT wait" in section
    assert "never retroactively" in section
    assert "arrival position" in section


def test_late_lower_sequence_appends_at_arrival_and_never_rewrites_history() -> None:
    projection = StreamProjection("srm", "device-01", "session-42")
    first = mutated(minimal_event(), event_id="hk-" + "01" * 16, sequence=1)
    second = mutated(minimal_event(), event_id="hk-" + "02" * 16, sequence=2)
    third = mutated(minimal_event(), event_id="hk-" + "03" * 16, sequence=3)
    for event in (first, second, third):
        projection.append(event)
    projection.emit()
    assert [event["event_id"] for event in projection.history] == [
        first["event_id"],
        second["event_id"],
        third["event_id"],
    ]

    late = mutated(minimal_event(), event_id="hk-" + "04" * 16, sequence=2)
    projection.append(late)
    assert ("sequence_inversion", late["event_id"], 2, 3) in projection.metadata
    projection.emit()
    assert [event["event_id"] for event in projection.history] == [
        first["event_id"],
        second["event_id"],
        third["event_id"],
        late["event_id"],
    ]
    assert len(projection.metadata) == 1


def test_projection_does_not_wait_for_unseen_gap_events() -> None:
    projection = StreamProjection("srm", "device-01", "session-43")
    seq_1 = mutated(minimal_event(), event_id="hk-" + "11" * 16, sequence=1)
    seq_2 = mutated(minimal_event(), event_id="hk-" + "12" * 16, sequence=2)
    seq_5 = mutated(minimal_event(), event_id="hk-" + "15" * 16, sequence=5)
    projection.append(seq_1)
    projection.append(seq_2)
    projection.emit()
    projection.append(seq_5)
    projection.emit()
    assert [event["event_id"] for event in projection.history] == [
        seq_1["event_id"],
        seq_2["event_id"],
        seq_5["event_id"],
    ]
    assert ("sequence_gap", seq_5["event_id"], 2, 5) in projection.metadata

    late_fill = mutated(minimal_event(), event_id="hk-" + "13" * 16, sequence=3)
    projection.append(late_fill)
    assert ("sequence_inversion", late_fill["event_id"], 3, 5) in projection.metadata
    projection.emit()
    assert [event["event_id"] for event in projection.history] == [
        seq_1["event_id"],
        seq_2["event_id"],
        seq_5["event_id"],
        late_fill["event_id"],
    ]


def test_guard_fail_closed_enforced_at_invocation_never_stream_delivery() -> None:
    section = contract_section("8.3 GUARD")
    assert "invocation" in section
    assert "eventual stream delivery" in section


def test_adapter_payload_only_on_capability_discovery_event(validator) -> None:
    capability = mutated(minimal_event(), **OPTIONAL_GROUPS["adapter"])
    assert validator.is_valid(capability)

    on_other_observe_event = mutated(
        minimal_event(),
        event_type="tool.execute",
        domain="tool",
        action="execute",
        adapter=OPTIONAL_GROUPS["adapter"]["adapter"],
    )
    assert not validator.is_valid(on_other_observe_event)

    wrong_action = mutated(
        minimal_event(),
        event_type="transport.adapter_capabilities",
        domain="transport",
        action="capabilities",
        adapter=OPTIONAL_GROUPS["adapter"]["adapter"],
    )
    assert not validator.is_valid(wrong_action)


def test_event_type_domain_action_semantic_mismatch_pinned(validator) -> None:
    rule = contract_section("3.1 Required core")
    assert "MUST equal `domain`" in rule

    for event in (
        minimal_event(),
        guard_event(),
        command_event(),
        mutated(minimal_event(), **OPTIONAL_GROUPS["adapter"]),
        mutated(minimal_event(), **OPTIONAL_GROUPS["ordering"]),
    ):
        assert not event_type_semantic_mismatch(event)

    schema_blind_mismatch = mutated(minimal_event(), event_type="execution.started")
    assert validator.is_valid(schema_blind_mismatch)
    assert event_type_semantic_mismatch(schema_blind_mismatch)

    truncated = mutated(minimal_event(), event_type="process.spawn")
    assert validator.is_valid(truncated)
    assert event_type_semantic_mismatch(truncated)

    wrong_domain = mutated(
        minimal_event(), event_type="process.spawned", domain="execution", action="started"
    )
    assert validator.is_valid(wrong_domain)
    assert event_type_semantic_mismatch(wrong_domain)

    phase_qualified = mutated(minimal_event(), event_type="process.spawned.child")
    assert validator.is_valid(phase_qualified)
    assert not event_type_semantic_mismatch(phase_qualified)
