import json
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
        minimal_event(),
        event_type="advisory.simplify",
        hook_class="ADVISORY",
        domain="advisory",
        action="simplify",
        **OPTIONAL_GROUPS["adapter"],
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
