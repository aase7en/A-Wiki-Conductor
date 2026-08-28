import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "provider-harness.md"
PROFILE_SCHEMA = ROOT / "schemas" / "provider-profile.schema.json"
OBS_SCHEMA = ROOT / "schemas" / "provider-observation.schema.json"
DISPATCH_SCHEMA = ROOT / "schemas" / "harness-dispatch.schema.json"
PROFILE_EXAMPLE = ROOT / "schemas" / "examples" / "provider-profile.example.json"
OBS_EXAMPLE = ROOT / "schemas" / "examples" / "provider-observation.example.json"
DISPATCH_EXAMPLE = ROOT / "schemas" / "examples" / "harness-dispatch.example.json"

ALL_FILES = (
    CONTRACT,
    PROFILE_SCHEMA,
    OBS_SCHEMA,
    DISPATCH_SCHEMA,
    PROFILE_EXAMPLE,
    OBS_EXAMPLE,
    DISPATCH_EXAMPLE,
)

FORBIDDEN_SECRET_FIELDS = {
    "api_key",
    "apikey",
    "token",
    "auth_token",
    "access_token",
    "secret",
    "secret_value",
    "credential_value",
    "password",
}
FORBIDDEN_DISPATCH_FIELDS = {
    "prompt",
    "transcript",
    "command",
    "argv",
    "shell",
    "executable",
    "env",
    "environment",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def property_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(properties)
        for value in node.values():
            names.update(property_names(value))
    elif isinstance(node, list):
        for value in node:
            names.update(property_names(value))
    return names


def string_values(node: object) -> list[str]:
    values: list[str] = []
    if isinstance(node, dict):
        for value in node.values():
            values.extend(string_values(value))
    elif isinstance(node, list):
        for value in node:
            values.extend(string_values(value))
    elif isinstance(node, str):
        values.append(node)
    return values


def test_contract_artifacts_exist() -> None:
    assert all(path.is_file() for path in ALL_FILES)


def test_provider_profile_is_closed_and_secret_reference_only() -> None:
    schema = load_json(PROFILE_SCHEMA)
    assert schema["additionalProperties"] is False
    assert {
        "schema_version",
        "provider_id",
        "display_name",
        "protocol_family",
        "endpoint_ref",
        "credential_ref",
        "trust_class",
        "egress_boundary",
        "harness_strategies",
        "models",
        "enabled",
    } <= set(schema["required"])
    names = property_names(schema)
    assert "credential_ref" in names
    assert "metadata" not in names
    assert not (names & FORBIDDEN_SECRET_FIELDS)


def test_provider_profile_protocol_harness_and_actor_capability_are_explicit() -> None:
    schema = load_json(PROFILE_SCHEMA)
    props = schema["properties"]
    assert {"ANTHROPIC_MESSAGES", "OPENAI_COMPATIBLE", "LOCAL"} <= set(
        props["protocol_family"]["enum"]
    )
    harness_enum = props["harness_strategies"]["items"]["enum"]
    assert {"CLAUDE_CODE_CLI", "DIRECT_API", "LOCAL_CLI"} <= set(harness_enum)
    model_props = props["models"]["items"]["properties"]
    assert "actor_capabilities" in model_props
    capability_props = model_props["actor_capabilities"]["items"]["properties"]
    assert {"capability", "evidence_level", "source"} <= set(capability_props)
    assert "execution_supply" not in model_props
    assert set(props["egress_boundary"]["enum"]) == {
        "EXTERNAL_THIRD_PARTY",
        "EXTERNAL_FIRST_PARTY",
        "LOCAL_MACHINE",
        "NO_EGRESS",
        "UNKNOWN",
    }


def test_provider_observation_is_fresh_typed_evidence_with_optional_quota() -> None:
    schema = load_json(OBS_SCHEMA)
    assert schema["additionalProperties"] is False
    assert {"schema_version", "provider_id", "health", "observed_at", "provenance"} <= set(
        schema["required"]
    )
    assert "details" not in property_names(schema)
    health = set(schema["properties"]["health"]["enum"])
    assert {
        "UNKNOWN",
        "AVAILABLE",
        "DEGRADED",
        "UNAVAILABLE",
        "AUTH_FAILED",
        "RATE_LIMITED",
        "QUOTA_EXHAUSTED",
    } <= health
    quota = schema["properties"]["quota"]
    quota_props = quota["anyOf"][0]["properties"]
    assert {"window_type", "limit", "used", "remaining", "reset_at", "reset_in_seconds"} <= set(
        quota_props
    )


def test_harness_dispatch_is_bounded_and_has_no_free_form_execution_authority() -> None:
    schema = load_json(DISPATCH_SCHEMA)
    assert schema["additionalProperties"] is False
    assert {
        "schema_version",
        "execution_id",
        "task_contract_ref",
        "project_id",
        "worktree_path",
        "expected_head",
        "provider_id",
        "model_id",
        "harness_strategy",
        "mutation_intent",
        "timeout_seconds",
        "max_output_bytes",
    } <= set(schema["required"])
    names = property_names(schema)
    assert "metadata" not in names
    assert not (names & FORBIDDEN_DISPATCH_FIELDS)
    assert set(schema["properties"]["harness_strategy"]["enum"]) == {
        "CLAUDE_CODE_CLI",
        "DIRECT_API",
        "LOCAL_CLI",
    }
    assert set(schema["properties"]["mutation_intent"]["enum"]) == {
        "READ_ONLY",
        "PROJECT_MUTATION",
    }
    assert schema["properties"]["timeout_seconds"]["maximum"] <= 14400
    assert schema["properties"]["max_output_bytes"]["maximum"] <= 8_388_608


def test_examples_are_non_secret_and_reference_based() -> None:
    profile = load_json(PROFILE_EXAMPLE)
    observation = load_json(OBS_EXAMPLE)
    dispatch = load_json(DISPATCH_EXAMPLE)
    assert profile["credential_ref"].startswith("secret-ref:")
    assert profile["models"][0]["model_id"] == "glm-5.3"
    assert dispatch["harness_strategy"] == "CLAUDE_CODE_CLI"
    assert observation["provider_id"] == profile["provider_id"] == dispatch["provider_id"]
    suspicious = re.compile(r"(?:glm-share-|sk-[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,})")
    for path in (PROFILE_EXAMPLE, OBS_EXAMPLE, DISPATCH_EXAMPLE):
        assert not any(suspicious.search(value) for value in string_values(load_json(path)))



def test_schemas_are_valid_draft_2020_12_and_examples_validate() -> None:
    pairs = (
        (PROFILE_SCHEMA, PROFILE_EXAMPLE),
        (OBS_SCHEMA, OBS_EXAMPLE),
        (DISPATCH_SCHEMA, DISPATCH_EXAMPLE),
    )
    for schema_path, example_path in pairs:
        schema = load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
            load_json(example_path)
        )

def test_contract_pins_authority_and_reliability_invariants() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    for phrase in (
        "CAPABLE != AUTHORIZED",
        "CONFIGURED != READY",
        "TRANSPORT FAILURE != EXECUTION FAILURE",
        "provider reporting DONE is evidence, not completion authority",
        "No raw prompt or transcript",
        "No second scheduler",
        "credential_ref",
        "Claude Code CLI",
        "GLM-5.3 is the first provider configuration, not an architectural dependency",
    ):
        assert phrase in text
