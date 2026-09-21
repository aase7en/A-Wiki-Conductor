"""Deterministic offline conformance for the BWA-0 browser chat resume
adapter contract (WO-P1-449 / Issue #449).

Covers the mandatory adversarial floor from the work order: schema
closedness and Draft 2020-12; minimal valid examples for every message
type; typed version rejection with a pinned v1 compatibility rule;
string/array/envelope bounds; missing adapter/provider/version/
capability rejection; fail-closed conversation binding reconciliation;
single-effect wake dedupe; duplicate browser response drop; consumed
replay rejection; no blind retry on ambiguous delivery; TEST_ONLY fake
ingress isolation from production DEX-3a; forbidden secret/process/
Git fields; shared fake-secret corpus exclusion; Play/Pause as wake
arm/disarm only; pointer-only payloads without task-state authority;
pinned authority boundaries (#215, WO433, Hook family, WO369, WO374,
DEX-2b, local-only DEX-2a, unavailable production DEX-3a); no new
scheduler/task/claim/lease/retry/review/completion/memory/model-policy
authority; and BWA-1 offline usability.

No network, no MCP, no live browser, and no production modules are
used: only the machine schema, the contract text, and small pure
reference helpers defined inside this file.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "browser-chat-resume-adapter-v1.md"
SCHEMA_PATH = ROOT / "docs" / "contracts" / "browser-chat-resume-adapter-v1.schema.json"

MESSAGE_ID = "bwa-0123456789abcdef0123456789abcdef"
OTHER_MESSAGE_ID = "bwa-fedcba9876543210fedcba9876543210"
WAKE_EVENT_ID = "bwk-0123456789abcdef0123456789abcdef"
OTHER_WAKE_EVENT_ID = "bwk-fedcba9876543210fedcba9876543210"
RESPONSE_CAPTURE_ID = "bwr-0123456789abcdef0123456789abcdef"
OTHER_RESPONSE_CAPTURE_ID = "bwr-fedcba9876543210fedcba9876543210"

OCCURRED_AT = "2026-09-21T02:00:00Z"

MESSAGE_TYPES = (
    "adapter_capability",
    "conversation_binding",
    "wake_request",
    "browser_response",
    "wake_delivery_status",
    "wake_arm_control",
    "test_only_fake_ingress",
)

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
    "credential",
    "credential_value",
    "cookie",
    "session_token",
    "share_url",
    "session_url",
    "argv",
    "command_line",
    "shell_command",
    "git_operation",
    "pid",
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

SHOULD_ENVELOPE_BYTES = 16384
MAX_ENVELOPE_BYTES = 32768

AUTHORITY_FIELD_NAMES = (
    "scheduler",
    "task_router",
    "claim_store",
    "lease",
    "retry_policy",
    "review_state",
    "completion_authority",
    "memory_store",
    "model_policy",
    "successor_selection",
    "same_tick_continue",
)

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


def capability_message() -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "adapter_capability",
        "occurred_at": OCCURRED_AT,
        "adapter_id": "bwa-chatgpt-web-adapter",
        "adapter_version": "0.1.0",
        "provider_id": "chatgpt-web",
        "provider_surface": "web_chat",
        "contract_version": "1.0.0",
        "capabilities": ["wake_delivery", "response_capture"],
        "capability_version": "1.0.0",
    }


def binding_message() -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "conversation_binding",
        "occurred_at": OCCURRED_AT,
        "adapter_id": "bwa-chatgpt-web-adapter",
        "provider_id": "chatgpt-web",
        "project_locator": "proj-7f3a",
        "conversation_locator": "conv-91c",
        "binding_generation": 3,
        "binding_version": 12,
        "observed_evidence": ["runs/WO-P1-449/author/binding-observation.txt"],
    }


def wake_request_message() -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "wake_request",
        "occurred_at": OCCURRED_AT,
        "adapter_id": "bwa-chatgpt-web-adapter",
        "provider_id": "chatgpt-web",
        "conversation_locator": "conv-91c",
        "binding_generation": 3,
        "wake_event_id": WAKE_EVENT_ID,
        "work_order_ref": "WO-P1-449",
        "task_ref": "Issue-449-BWA0-contract",
        "reason": "delegated execution reached a reviewable checkpoint",
        "requested_next_decision": "PROPOSE_CONTINUATION",
        "evidence_refs": ["runs/WO-P1-449/author/attempt-0001/result.md"],
    }


def browser_response_message() -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "browser_response",
        "occurred_at": OCCURRED_AT,
        "adapter_id": "bwa-chatgpt-web-adapter",
        "provider_id": "chatgpt-web",
        "conversation_locator": "conv-91c",
        "binding_generation": 3,
        "wake_event_id": WAKE_EVENT_ID,
        "response_capture_id": RESPONSE_CAPTURE_ID,
        "observed_completion_state": "RESPONSE_OBSERVED",
        "trust_state": "UNTRUSTED",
        "proposal_refs": ["runs/WO-P1-449/author/proposals/0001.md"],
    }


def delivery_status_message(state: str = "WAKE_DELIVERY_CONFIRMED") -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "wake_delivery_status",
        "occurred_at": OCCURRED_AT,
        "wake_event_id": WAKE_EVENT_ID,
        "delivery_state": state,
        "delivery_attempt": 1,
    }


def arm_control_message(command: str = "PLAY") -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "wake_arm_control",
        "occurred_at": OCCURRED_AT,
        "adapter_id": "bwa-chatgpt-web-adapter",
        "provider_id": "chatgpt-web",
        "conversation_locator": "conv-91c",
        "binding_generation": 3,
        "arm_command": command,
    }


def fake_ingress_message() -> dict:
    return {
        "schema_version": "1.0.0",
        "message_id": MESSAGE_ID,
        "message_type": "test_only_fake_ingress",
        "occurred_at": OCCURRED_AT,
        "test_only": True,
        "fake_source_kind": "FAKE_INGRESS",
        "fake_provider_id": "fake-chatgpt-web",
        "fake_conversation_locator": "conv-91c",
        "fake_binding_generation": 3,
        "fake_trigger_kind": "FAKE_COMPLETION_EVENT",
    }


MINIMAL_EXAMPLES = {
    "adapter_capability": capability_message,
    "conversation_binding": binding_message,
    "wake_request": wake_request_message,
    "browser_response": browser_response_message,
    "wake_delivery_status": delivery_status_message,
    "wake_arm_control": arm_control_message,
    "test_only_fake_ingress": fake_ingress_message,
}


def envelope_bytes(payload: dict) -> int:
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def contract_section(title: str) -> str:
    text = CONTRACT.read_text(encoding="utf-8")
    match = re.search(
        rf"^#{{2,3}}\s*{re.escape(title)}\s*$(.*?)(?=^#{{2,3}}\s|\Z)",
        text,
        re.M | re.S,
    )
    assert match is not None, title
    return " ".join(match.group(1).split())


# ---------------------------------------------------------------------------
# Pure reference algorithms (test-only; no production module is imported).
# ---------------------------------------------------------------------------


def classify_schema_version(version) -> str:
    if not isinstance(version, str):
        return "BWA_EVENT_INVALID"
    if re.fullmatch(r"1\.\d+\.\d+", version):
        return "SUPPORTED_V1"
    if re.fullmatch(r"\d+\.\d+\.\d+", version):
        return "BWA_VERSION_UNSUPPORTED"
    return "BWA_EVENT_INVALID"


class WakeEffectGate:
    """Reference single-effect gate: one wake_event_id authorizes at most
    one browser/model effect; anything after consumption is a rejected
    replay, not a second effect."""

    def __init__(self) -> None:
        self._consumed: set[str] = set()

    def deliver(self, wake_request: dict) -> str:
        wake_event_id = wake_request["wake_event_id"]
        if wake_event_id in self._consumed:
            return "WAKE_EVENT_ALREADY_CONSUMED"
        self._consumed.add(wake_event_id)
        return "EFFECT_AUTHORIZED"


class ResponseEffectDedupe:
    """Reference response dedupe: a duplicate capture cannot cause a second
    downstream effect."""

    def __init__(self) -> None:
        self._applied: set[str] = set()
        self.effects: list[str] = []

    def apply(self, response: dict) -> str:
        capture_id = response["response_capture_id"]
        if capture_id in self._applied:
            return "DUPLICATE_RESPONSE_DROPPED"
        self._applied.add(capture_id)
        self.effects.append(capture_id)
        return "RESPONSE_ACCEPTED_FOR_REVIEW"


def delivery_followup(delivery_state: str) -> str:
    if delivery_state == "WAKE_DELIVERY_CONFIRMED":
        return "AWAIT_BROWSER_RESPONSE"
    if delivery_state == "WAKE_DELIVERY_FAILED":
        return "RESCHEDULE_AFTER_BINDING_RECONCILE"
    if delivery_state == "WAKE_DELIVERY_UNKNOWN":
        return "HOLD_RECONCILE_NO_RESEND"
    raise ValueError(f"unknown delivery state: {delivery_state}")


def reconcile_binding(durable: dict | None, observed: dict | None) -> str:
    if durable is None or observed is None:
        return "BINDING_UNKNOWN"
    for field in ("adapter_id", "provider_id", "conversation_locator"):
        if durable.get(field) is None or observed.get(field) is None:
            return "BINDING_UNKNOWN"
        if durable[field] != observed[field]:
            return "BINDING_MISMATCH"
    durable_generation = durable.get("binding_generation")
    observed_generation = observed.get("binding_generation")
    if durable_generation is None or observed_generation is None:
        return "BINDING_UNKNOWN"
    if observed_generation == durable_generation:
        return "BINDING_MATCH"
    if observed_generation < durable_generation:
        return "BINDING_STALE"
    return "BINDING_MISMATCH"


def restart_reconcile(
    durable_receipts: set[str], binding_outcome: str, pending_wake: dict
) -> str:
    if binding_outcome != "BINDING_MATCH":
        return "BINDING_RECONCILE_REQUIRED"
    if pending_wake["wake_event_id"] in durable_receipts:
        return "WAKE_EVENT_ALREADY_CONSUMED"
    return "RESEND_AUTHORIZED"


def durable_binding() -> dict:
    return {
        "adapter_id": "bwa-chatgpt-web-adapter",
        "provider_id": "chatgpt-web",
        "conversation_locator": "conv-91c",
        "binding_generation": 4,
    }


# ---------------------------------------------------------------------------
# 1. Schema is Draft 2020-12 and closed.
# ---------------------------------------------------------------------------


def test_schema_is_draft_2020_12_and_closed(schema) -> None:
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == "urn:a-conductor:schema:browser-chat-resume-adapter:1.0.0"
    assert schema["additionalProperties"] is False

    def assert_closed(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False, node
            for value in node.values():
                assert_closed(value)
        elif isinstance(node, list):
            for value in node:
                assert_closed(value)

    assert_closed(schema)
    assert CONTRACT.exists()


# ---------------------------------------------------------------------------
# 2. Minimal valid examples for every message type.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("message_type", MESSAGE_TYPES)
def test_minimal_examples_validate(validator, message_type) -> None:
    payload = MINIMAL_EXAMPLES[message_type]()
    assert validator.is_valid(payload), message_type


def test_capability_example_carries_exact_identity(validator) -> None:
    payload = capability_message()
    assert validator.is_valid(payload)
    for field in (
        "adapter_id",
        "adapter_version",
        "provider_id",
        "provider_surface",
        "contract_version",
        "capabilities",
        "capability_version",
    ):
        assert field in payload


@pytest.mark.parametrize(
    "field",
    ["schema_version", "message_id", "message_type", "occurred_at"],
)
def test_missing_core_rejected_everywhere(validator, field) -> None:
    for builder in MINIMAL_EXAMPLES.values():
        assert not validator.is_valid(mutated(builder(), **{field: REMOVE})), field


@pytest.mark.parametrize(
    "case",
    [
        {"message_id": ""},
        {"message_id": "hk-0123456789abcdef0123456789abcdef"},
        {"message_id": "bwa-0123456789ABCDEF0123456789ABCDEF"},
        {"message_id": "bwa-0123456789abcdef"},
        {"message_id": 12345},
        {"message_type": "browser_event_bus"},
        {"message_type": REMOVE},
        {"occurred_at": "2026-09-21T02:00:00+00:00"},
        {"occurred_at": "2026-09-21 02:00:00Z"},
    ],
)
def test_core_identity_formats_enforced(validator, case) -> None:
    assert not validator.is_valid(mutated(capability_message(), **case))


def test_wake_and_capture_identity_formats_enforced(validator) -> None:
    for case in ({"wake_event_id": "wake-1"}, {"wake_event_id": "bwk-XYZ"}):
        assert not validator.is_valid(mutated(wake_request_message(), **case))
    assert not validator.is_valid(
        mutated(browser_response_message(), response_capture_id="cap-1")
    )
    correlated = mutated(
        wake_request_message(),
        source_event_ref="runs/WO-P1-449/dex2b/receipt-0001.json",
    )
    assert validator.is_valid(correlated)


def test_provider_surface_is_browser_chat_only(validator) -> None:
    assert validator.is_valid(capability_message())
    assert not validator.is_valid(
        mutated(capability_message(), provider_surface="native_messaging_host")
    )
    assert not validator.is_valid(mutated(capability_message(), provider_surface="cli"))


def test_type_exclusivity_enforced(validator) -> None:
    assert not validator.is_valid(mutated(wake_request_message(), binding_version=5))
    assert not validator.is_valid(
        mutated(wake_request_message(), capabilities=["wake_delivery"])
    )
    assert not validator.is_valid(mutated(browser_response_message(), arm_command="PLAY"))
    assert not validator.is_valid(
        mutated(arm_control_message(), wake_event_id=WAKE_EVENT_ID)
    )
    assert not validator.is_valid(
        mutated(delivery_status_message(), adapter_id="bwa-chatgpt-web-adapter")
    )
    assert not validator.is_valid(
        mutated(capability_message(), conversation_locator="conv-91c")
    )


# ---------------------------------------------------------------------------
# 3. Unknown major / unparseable versions rejected; v1 rule pinned.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "version,expected",
    [
        ("1.0.0", "SUPPORTED_V1"),
        ("1.9.7", "SUPPORTED_V1"),
        ("2.0.0", "BWA_VERSION_UNSUPPORTED"),
        ("0.9.0", "BWA_VERSION_UNSUPPORTED"),
        ("1.0", "BWA_EVENT_INVALID"),
        ("1.0.0.0", "BWA_EVENT_INVALID"),
        ("v1.0.0", "BWA_EVENT_INVALID"),
        (None, "BWA_EVENT_INVALID"),
        (17, "BWA_EVENT_INVALID"),
    ],
)
def test_version_classification_typed(version, expected) -> None:
    assert classify_schema_version(version) == expected


@pytest.mark.parametrize("version", ["2.0.0", "0.9.0", "1.0", "1.0.0.0", "v1.0.0"])
def test_non_v1_schema_versions_rejected(validator, version) -> None:
    assert not validator.is_valid(mutated(capability_message(), schema_version=version))


def test_v1_compatibility_rule_pinned_in_contract() -> None:
    section = contract_section("12. Versioning and compatibility")
    assert "BWA_VERSION_UNSUPPORTED" in section
    assert "no silent fallback" in section
    assert "1.x" in section


# ---------------------------------------------------------------------------
# 4. Oversize strings/arrays/envelope rejected.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case",
    [
        {"reason": "x" * 257},
        {"capabilities": [f"cap_{i:02d}" for i in range(17)]},
        {"evidence_refs": [f"ref-{i:02d}" for i in range(9)]},
        {"evidence_refs": ["same-ref", "same-ref"]},
        {"conversation_locator": "c" * 129},
        {"adapter_id": "a" * 65},
    ],
)
def test_oversize_and_malformed_values_rejected(validator, case) -> None:
    assert not validator.is_valid(mutated(wake_request_message(), **case))
    assert not validator.is_valid(mutated(capability_message(), **case))


def test_whole_envelope_size_rule(validator) -> None:
    section = contract_section("3. Message envelope")
    assert "16384" in section
    assert "32768" in section
    oversized = mutated(wake_request_message(), reason="x" * 33000)
    assert envelope_bytes(oversized) > MAX_ENVELOPE_BYTES
    assert not validator.is_valid(oversized)
    for builder in MINIMAL_EXAMPLES.values():
        assert envelope_bytes(builder()) <= SHOULD_ENVELOPE_BYTES


# ---------------------------------------------------------------------------
# 5. Missing adapter/provider/version/capability rejected.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "adapter_id",
        "adapter_version",
        "provider_id",
        "provider_surface",
        "contract_version",
        "capabilities",
        "capability_version",
    ],
)
def test_missing_adapter_provider_capability_rejected(validator, field) -> None:
    assert not validator.is_valid(mutated(capability_message(), **{field: REMOVE}))


def test_readiness_is_separate_from_capability(validator) -> None:
    section = contract_section("4. Adapter capability")
    for token in ("CAPABLE", "READY", "AUTHORIZED", "ADMITTED"):
        assert token in section, token
    assert "MUST NOT infer" in section
    assert not validator.is_valid(mutated(capability_message(), readiness="AUTHORIZED"))
    assert not validator.is_valid(mutated(capability_message(), admitted=True))


# ---------------------------------------------------------------------------
# 6. Conversation mismatch/stale/unknown are typed fail-closed states.
# ---------------------------------------------------------------------------


def test_binding_reconciliation_is_typed_and_fail_closed() -> None:
    assert reconcile_binding(durable_binding(), durable_binding()) == "BINDING_MATCH"
    assert (
        reconcile_binding(
            durable_binding(), {**durable_binding(), "conversation_locator": "conv-other"}
        )
        == "BINDING_MISMATCH"
    )
    assert (
        reconcile_binding(
            durable_binding(), {**durable_binding(), "binding_generation": 3}
        )
        == "BINDING_STALE"
    )
    # A newer observed generation is drift, never guessed or absorbed.
    assert (
        reconcile_binding(
            durable_binding(), {**durable_binding(), "binding_generation": 5}
        )
        == "BINDING_MISMATCH"
    )
    assert reconcile_binding(durable_binding(), None) == "BINDING_UNKNOWN"
    assert reconcile_binding(None, durable_binding()) == "BINDING_UNKNOWN"
    partial = {
        k: v for k, v in durable_binding().items() if k != "binding_generation"
    }
    assert reconcile_binding(durable_binding(), partial) == "BINDING_UNKNOWN"


def test_binding_fail_closed_vocabulary_pinned() -> None:
    section = contract_section("5. Conversation binding")
    for token in (
        "BINDING_MATCH",
        "BINDING_MISMATCH",
        "BINDING_STALE",
        "BINDING_UNKNOWN",
    ):
        assert token in section, token
    assert "fail" in section.lower()
    assert "never guessed" in section


def test_binding_locators_cannot_be_urls_or_cookie_values(validator) -> None:
    assert not validator.is_valid(
        mutated(
            binding_message(),
            conversation_locator="https://chat.example/FAKE/share/0000",
        )
    )
    assert not validator.is_valid(
        mutated(
            binding_message(),
            project_locator="FAKESESSIONCOOKIE=0000000000000000",
        )
    )


# ---------------------------------------------------------------------------
# 7. Duplicate wake_event_id authorizes at most one effect.
# ---------------------------------------------------------------------------


def test_duplicate_wake_event_id_authorizes_single_effect(validator) -> None:
    first = wake_request_message()
    redelivery = mutated(wake_request_message(), message_id=OTHER_MESSAGE_ID)
    assert redelivery["wake_event_id"] == first["wake_event_id"]
    assert validator.is_valid(first)
    assert validator.is_valid(redelivery)

    gate = WakeEffectGate()
    assert gate.deliver(first) == "EFFECT_AUTHORIZED"
    assert gate.deliver(redelivery) == "WAKE_EVENT_ALREADY_CONSUMED"

    distinct = mutated(wake_request_message(), wake_event_id=OTHER_WAKE_EVENT_ID)
    assert gate.deliver(distinct) == "EFFECT_AUTHORIZED"


def test_wake_request_requires_at_least_one_durable_pointer(validator) -> None:
    bare = wake_request_message()
    for field in ("goal_ref", "task_ref", "work_order_ref"):
        bare.pop(field, None)
    assert not validator.is_valid(bare)
    assert validator.is_valid(mutated(bare, goal_ref="goal-42"))


def test_transport_counter_is_not_retry_authority() -> None:
    section = contract_section("6. Wake request")
    assert "delivery_attempt" in section
    assert "transport metadata only" in section
    assert "retry authority" in section


# ---------------------------------------------------------------------------
# 8. Duplicate browser response cannot create a second effect.
# ---------------------------------------------------------------------------


def test_duplicate_browser_response_cannot_create_second_effect(validator) -> None:
    first = browser_response_message()
    duplicate = mutated(browser_response_message(), message_id=OTHER_MESSAGE_ID)
    assert duplicate["response_capture_id"] == first["response_capture_id"]
    assert validator.is_valid(first)
    assert validator.is_valid(duplicate)

    dedupe = ResponseEffectDedupe()
    assert dedupe.apply(first) == "RESPONSE_ACCEPTED_FOR_REVIEW"
    assert dedupe.apply(duplicate) == "DUPLICATE_RESPONSE_DROPPED"
    assert dedupe.effects == [RESPONSE_CAPTURE_ID]

    other_capture = mutated(
        browser_response_message(), response_capture_id=OTHER_RESPONSE_CAPTURE_ID
    )
    assert dedupe.apply(other_capture) == "RESPONSE_ACCEPTED_FOR_REVIEW"
    assert dedupe.effects == [RESPONSE_CAPTURE_ID, OTHER_RESPONSE_CAPTURE_ID]


# ---------------------------------------------------------------------------
# 9. Consumed event replay rejected (including across restart).
# ---------------------------------------------------------------------------


def test_consumed_replay_rejected_across_restart() -> None:
    wake = wake_request_message()
    gate = WakeEffectGate()
    gate.deliver(wake)
    replay = mutated(wake, message_id=OTHER_MESSAGE_ID)
    assert gate.deliver(replay) == "WAKE_EVENT_ALREADY_CONSUMED"

    # Restart/reconnect reconciles durable receipts and binding before resend.
    assert (
        restart_reconcile({WAKE_EVENT_ID}, "BINDING_MATCH", wake)
        == "WAKE_EVENT_ALREADY_CONSUMED"
    )
    assert (
        restart_reconcile(set(), "BINDING_MISMATCH", wake)
        == "BINDING_RECONCILE_REQUIRED"
    )
    assert (
        restart_reconcile(set(), "BINDING_UNKNOWN", wake)
        == "BINDING_RECONCILE_REQUIRED"
    )
    assert restart_reconcile(set(), "BINDING_MATCH", wake) == "RESEND_AUTHORIZED"


# ---------------------------------------------------------------------------
# 10. Ambiguous delivery maps to UNKNOWN and never blind-retries.
# ---------------------------------------------------------------------------


def test_ambiguous_delivery_never_blind_retries(validator) -> None:
    assert validator.is_valid(delivery_status_message("WAKE_DELIVERY_UNKNOWN"))
    assert validator.is_valid(delivery_status_message("WAKE_DELIVERY_FAILED"))
    assert validator.is_valid(delivery_status_message("WAKE_DELIVERY_CONFIRMED"))
    assert not validator.is_valid(delivery_status_message("WAKE_DELIVERY_RETRY_NOW"))

    assert delivery_followup("WAKE_DELIVERY_UNKNOWN") == "HOLD_RECONCILE_NO_RESEND"
    assert (
        delivery_followup("WAKE_DELIVERY_FAILED")
        == "RESCHEDULE_AFTER_BINDING_RECONCILE"
    )
    assert delivery_followup("WAKE_DELIVERY_CONFIRMED") == "AWAIT_BROWSER_RESPONSE"
    for state in ("WAKE_DELIVERY_CONFIRMED", "WAKE_DELIVERY_FAILED", "WAKE_DELIVERY_UNKNOWN"):
        followup = delivery_followup(state)
        assert "RESEND_NOW" not in followup
        assert not followup.startswith("BLIND")

    section = contract_section("9. Delivery states and failure vocabulary")
    assert "WAKE_DELIVERY_UNKNOWN" in section
    assert "MUST NOT blind" in section
    assert "HOLD_RECONCILE_NO_RESEND" in section
    assert "not a new durable task/retry state" in section


# ---------------------------------------------------------------------------
# 11. Fake ingress is TEST_ONLY-only and cannot validate as production DEX-3a.
# ---------------------------------------------------------------------------


def test_fake_ingress_is_test_only_and_cannot_impersonate_production(
    validator,
) -> None:
    fake = fake_ingress_message()
    assert validator.is_valid(fake)
    assert fake["test_only"] is True
    assert fake["fake_source_kind"] == "FAKE_INGRESS"
    assert fake["fake_provider_id"].startswith("fake-")

    # Fake ingress cannot carry production correlation or wake authority.
    assert not validator.is_valid(
        mutated(fake, source_event_ref="runs/dex/2b/receipt-0001.json")
    )
    assert not validator.is_valid(mutated(fake, wake_event_id=WAKE_EVENT_ID))
    assert not validator.is_valid(mutated(fake, test_only=False))
    assert not validator.is_valid(mutated(fake, fake_source_kind="DEX_3A_PRODUCTION"))
    assert not validator.is_valid(mutated(fake, fake_provider_id="chatgpt-web"))

    # Production-typed messages cannot carry TEST_ONLY vocabulary.
    assert not validator.is_valid(mutated(wake_request_message(), test_only=True))
    assert not validator.is_valid(
        mutated(wake_request_message(), fake_trigger_kind="FAKE_COMPLETION_EVENT")
    )

    # Production DEX-3a-flavored unknown fields are closed-schema-invalid.
    for base in (
        wake_request_message(),
        browser_response_message(),
        fake_ingress_message(),
    ):
        assert not validator.is_valid(mutated(base, dex3a_event_id="dex3a-1"))
        assert not validator.is_valid(mutated(base, production_source="dex-3a"))

    section = contract_section("10. DEX boundary and TEST_ONLY fake ingress")
    assert "UNAVAILABLE" in section
    assert "production DEX-3a" in section
    assert "TEST_ONLY" in section


# ---------------------------------------------------------------------------
# 12. Forbidden secret/process/Git fields rejected.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_name", FORBIDDEN_FIELDS)
def test_forbidden_fields_rejected(validator, schema, field_name) -> None:
    assert field_name not in schema["properties"]
    for base in (
        wake_request_message(),
        browser_response_message(),
        capability_message(),
        fake_ingress_message(),
    ):
        assert not validator.is_valid(mutated(base, **{field_name: "value"})), (
            field_name
        )


def test_native_messaging_deferred_to_bwa1() -> None:
    section = contract_section("13. Security")
    assert "Native Messaging" in section
    assert "BWA-1" in section


# ---------------------------------------------------------------------------
# 13. Shared fake-secret corpus does not appear in valid serialized examples.
# ---------------------------------------------------------------------------


def test_fake_secret_corpus_pinned_and_excluded(schema) -> None:
    contract_text = CONTRACT.read_text(encoding="utf-8")
    assert "fake-secret-corpus/1" in contract_text
    for item in FAKE_SECRET_CORPUS:
        assert item in contract_text, item
        assert item not in SCHEMA_PATH.read_text(encoding="utf-8")
    for builder in MINIMAL_EXAMPLES.values():
        serialized = json.dumps(builder(), ensure_ascii=False)
        for item in FAKE_SECRET_CORPUS:
            assert item not in serialized, item


# ---------------------------------------------------------------------------
# 14. Play/Pause accepted only as wake-arm state.
# ---------------------------------------------------------------------------


def test_play_pause_are_wake_arm_only(validator) -> None:
    assert validator.is_valid(arm_control_message("PLAY"))
    assert validator.is_valid(arm_control_message("PAUSE"))

    for illegal in (
        "PAUSE_EXECUTION",
        "CANCEL_TASK",
        "RETRY",
        "SUSPEND",
        "KILL",
        "pause",
        "play",
    ):
        assert not validator.is_valid(arm_control_message(illegal)), illegal

    for field in (
        "execution_pause",
        "cancel",
        "retry_task",
        "kill",
        "suspend",
        "task_control",
    ):
        assert not validator.is_valid(mutated(arm_control_message(), **{field: True}))
        assert not validator.is_valid(mutated(wake_request_message(), **{field: True}))

    section = contract_section("11. Play and Pause")
    assert "arm" in section
    assert "disarm" in section
    assert "MUST NOT" in section
    for token in ("suspend", "kill", "cancel"):
        assert token in section, token


# ---------------------------------------------------------------------------
# 15. Requests/results carry pointers, not task-state mutation authority.
# ---------------------------------------------------------------------------


def test_requests_and_results_carry_pointers_not_task_authority(validator) -> None:
    for field, value in (
        ("task_state", "COMPLETED"),
        ("next_ready", True),
        ("acceptance", "ACCEPTED"),
        ("completed", True),
        ("retry_policy", "always"),
        ("claim_ref_state", "mine"),
    ):
        assert not validator.is_valid(mutated(wake_request_message(), **{field: value}))
        assert not validator.is_valid(
            mutated(browser_response_message(), **{field: value})
        ), field

    response = browser_response_message()
    assert response["trust_state"] == "UNTRUSTED"
    assert not validator.is_valid(mutated(response, trust_state="TRUSTED"))
    schema = load_schema()
    assert schema["properties"]["trust_state"] == {"const": "UNTRUSTED"}

    section = contract_section("7. Browser proposal and result")
    assert "UNTRUSTED" in section
    assert "cannot declare task acceptance" in section


# ---------------------------------------------------------------------------
# 16. Contract text pins the authority boundaries.
# ---------------------------------------------------------------------------


def test_contract_pins_authority_boundaries() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for token in (
        "#215",
        "WO433",
        "Hook",
        "WO369",
        "WO374",
        "DEX-2b",
        "DEX-2a",
        "DEX-3a",
    ):
        assert token in text, token
    section = contract_section("1. Purpose and authority")
    assert "UNAVAILABLE" in section
    assert "NEXT_READY" in section
    assert "Command Gateway" in section


# ---------------------------------------------------------------------------
# 17. No new scheduler/task/claim/lease/retry/review/completion/memory/
#     model-policy authority.
# ---------------------------------------------------------------------------


def test_no_new_authority_in_schema_or_contract(schema) -> None:
    for field in AUTHORITY_FIELD_NAMES:
        assert field not in schema["properties"], field
    section = contract_section("14. Authority fence")
    lowered = section.lower()
    for token in (
        "scheduler",
        "claim",
        "lease",
        "retry",
        "review",
        "completion",
        "memory",
        "model-policy",
    ):
        assert token in lowered, token
    assert "no new" in lowered


# ---------------------------------------------------------------------------
# 18. Whole contract usable by BWA-1 fake-provider tests offline.
# ---------------------------------------------------------------------------


def test_offline_bwa1_cycle_without_browser_or_network(validator) -> None:
    section = contract_section("15. BWA-1 offline usability")
    assert "no live browser" in section
    assert "no network" in section.lower()
    assert "deterministic" in section.lower()

    fake = fake_ingress_message()
    wake = wake_request_message()
    response = browser_response_message()
    status = delivery_status_message("WAKE_DELIVERY_UNKNOWN")
    for message in (fake, wake, response, status):
        assert validator.is_valid(message)

    gate = WakeEffectGate()
    assert gate.deliver(wake) == "EFFECT_AUTHORIZED"
    assert (
        gate.deliver(mutated(wake, message_id=OTHER_MESSAGE_ID))
        == "WAKE_EVENT_ALREADY_CONSUMED"
    )
    dedupe = ResponseEffectDedupe()
    assert dedupe.apply(response) == "RESPONSE_ACCEPTED_FOR_REVIEW"
    assert (
        dedupe.apply(mutated(response, message_id=OTHER_MESSAGE_ID))
        == "DUPLICATE_RESPONSE_DROPPED"
    )
    assert delivery_followup(status["delivery_state"]) == "HOLD_RECONCILE_NO_RESEND"


def test_unknown_field_rejected_future_minor_still_v1(validator) -> None:
    assert not validator.is_valid(mutated(wake_request_message(), mystery_field="v"))
    future_minor = mutated(capability_message(), schema_version="1.9.7")
    assert validator.is_valid(future_minor)
    assert not validator.is_valid(mutated(future_minor, mystery_field="v"))
