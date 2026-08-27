"""Mechanical guards for the Desktop Commander bounded transport contract.

WO-P1-080 (North Star N3): the contract must REUSE/WRAP the existing opaque
``operation_ref`` authority, stay a closed bounded definition shape, and
never introduce raw command/argv/shell authority or a second registry.
These tests parse the schema/contract with the stdlib only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "schemas" / "desktop-commander-operation.schema.json"
EXAMPLE_PATH = (
    REPO_ROOT / "schemas" / "examples" / "desktop-commander-operation.example.json"
)
CONTRACT_PATH = (
    REPO_ROOT / "docs" / "contracts" / "desktop-commander-bounded-transport.md"
)

EXPECTED_TOOL_FAMILIES = {
    "PROJECT_FILE_READ",
    "PROJECT_FILE_SEARCH",
    "PROCESS_START",
    "PROCESS_INSPECT",
    "PROCESS_READ_OUTPUT",
    "PROCESS_INTERACT",
    "DOCUMENT_READ",
    "DATA_ANALYZE",
}

EXPECTED_REQUIRED_FIELDS = {
    "operation_ref",
    "tool_family",
    "project_id",
    "mutation_intent",
    "timeout_seconds",
    "max_output_bytes",
}

#: Union of raw-authority fields forbidden by operator.v1, the native
#: operation registry contract, and WO-P1-080 itself.
FORBIDDEN_PROPERTY_NAMES = {
    "command",
    "cmd",
    "argv",
    "args",
    "shell",
    "powershell",
    "bash",
    "executable",
    "env",
    "environment",
    "prompt",
    "goal",
    "transcript",
    "script",
    "sql",
    "cwd",
    "working_dir",
    "stdin",
    "remote_shell",
}

HARD_MAX_OUTPUT_BYTES = 8_388_608  # 8 MiB documented hard maximum
OPAQUE_REF_PATTERN = re.compile(r"^[A-Za-z0-9._\-/:@]+$")


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _load_example() -> dict[str, Any]:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _iter_property_names(node: Any) -> set[str]:
    """Recursively collect every property name in a JSON schema node."""
    names: set[str] = set()
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            names.update(properties.keys())
            for child in properties.values():
                names |= _iter_property_names(child)
        for key in ("items", "additionalProperties", "oneOf", "anyOf", "allOf"):
            if key in node:
                names |= _iter_property_names(node[key])
    elif isinstance(node, list):
        for child in node:
            names |= _iter_property_names(child)
    return names


def test_schema_and_example_parse_as_json() -> None:
    schema = _load_schema()
    example = _load_example()
    assert schema["type"] == "object"
    assert isinstance(example, dict)


def test_schema_is_closed_object_with_exact_required_fields() -> None:
    schema = _load_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == EXPECTED_REQUIRED_FIELDS
    assert set(schema["properties"].keys()) == EXPECTED_REQUIRED_FIELDS | {
        "device_id"
    }
    # device identity is optional: local definitions carry no device target.
    assert "device_id" not in schema["required"]


def test_no_raw_authority_payload_fields_anywhere() -> None:
    schema = _load_schema()
    names = _iter_property_names(schema)
    assert not names & FORBIDDEN_PROPERTY_NAMES, (
        f"raw-authority fields leaked into schema: {sorted(names & FORBIDDEN_PROPERTY_NAMES)}"
    )


def test_tool_family_is_fixed_closed_enum() -> None:
    schema = _load_schema()
    enum = schema["properties"]["tool_family"]["enum"]
    assert set(enum) == EXPECTED_TOOL_FAMILIES
    assert len(enum) == len(EXPECTED_TOOL_FAMILIES)  # no duplicates
    assert "REMOTE_SHELL" not in enum


def test_mutation_intent_is_explicit_two_state_enum() -> None:
    schema = _load_schema()
    assert set(schema["properties"]["mutation_intent"]["enum"]) == {
        "READ_ONLY",
        "PROJECT_MUTATION",
    }


def test_timeout_seconds_bounded_1_to_3600() -> None:
    schema = _load_schema()
    spec = schema["properties"]["timeout_seconds"]
    assert spec["type"] == "integer"
    assert spec["minimum"] == 1
    assert spec["maximum"] == 3600


def test_max_output_bytes_positive_with_documented_hard_maximum() -> None:
    schema = _load_schema()
    spec = schema["properties"]["max_output_bytes"]
    assert spec["type"] == "integer"
    assert spec["minimum"] == 1
    assert spec["maximum"] == HARD_MAX_OUTPUT_BYTES

    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "8,388,608" in contract  # the documented hard maximum


def test_device_identity_is_optional_remote_target_fail_closed() -> None:
    schema = _load_schema()
    spec = schema["properties"]["device_id"]
    assert spec["type"] == "string"
    assert spec.get("minLength") == 1
    description = spec.get("description", "")
    assert "fails closed" in description.lower()


def test_example_conforms_to_schema_shape() -> None:
    schema = _load_schema()
    example = _load_example()
    properties = schema["properties"]

    assert set(example.keys()) <= set(properties.keys())
    assert EXPECTED_REQUIRED_FIELDS <= set(example.keys())

    assert OPAQUE_REF_PATTERN.match(example["operation_ref"])
    assert example["tool_family"] in properties["tool_family"]["enum"]
    assert example["mutation_intent"] in properties["mutation_intent"]["enum"]
    assert (
        properties["timeout_seconds"]["minimum"]
        <= example["timeout_seconds"]
        <= properties["timeout_seconds"]["maximum"]
    )
    assert (
        properties["max_output_bytes"]["minimum"]
        <= example["max_output_bytes"]
        <= properties["max_output_bytes"]["maximum"]
    )


def test_example_is_read_only_remote_inspection_first() -> None:
    """Read-only inspection is the recommended first remote capability."""
    example = _load_example()
    assert example["mutation_intent"] == "READ_ONLY"
    assert example["tool_family"] == "PROJECT_FILE_READ"
    assert "device_id" in example


def test_contract_document_states_reuse_not_second_registry() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "operator.v1" in contract
    assert "job.execute" in contract
    assert "operation_ref" in contract
    assert "does not create a second registry" in contract
    assert "does not create a second `operation_ref` namespace" in contract


def test_contract_document_states_authority_boundaries() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "defense-in-depth" in contract
    assert "not A-Conductor's authorization boundary" in contract
    assert "durable execution ID" in contract
    assert "before any side effect" in contract
    assert "Transport loss is not execution failure" in contract
    assert "ADR-0001" in contract
    assert "no MCP gateway" in contract
    assert "no discovery or polling" in contract


def test_contract_documents_bounds_and_gating() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")
    assert "3600" in contract
    assert "paginated" in contract
    assert "Read-only inspection is the recommended first remote capability" in contract
    assert "remote execution is a target device identity" in contract
