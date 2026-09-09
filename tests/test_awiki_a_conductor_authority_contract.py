from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs" / "contracts" / "a-wiki-a-conductor-integration.md"

START = "<!-- operational-authority-map:start -->"
END = "<!-- operational-authority-map:end -->"
ALLOWED_ROLES = {"OWNER", "CONSUMER", "ADAPTER", "COMPATIBILITY_FALLBACK"}
REQUIRED_CAPABILITIES = {
    "knowledge_memory",
    "planning_intelligence",
    "workflow_stage_state",
    "work_order_contract",
    "repo_coordination_claim",
    "runtime_task_instance",
    "status",
    "claim_policy",
    "mutation_gate",
    "runtime_lease",
    "verification_policy",
    "model_policy",
    "runtime_model_selection",
    "review_lifecycle",
    "execution_verification",
    "scheduler_ready_set",
    "retry_recovery",
    "next_ready_continuation",
    "handoff_convention",
    "execution_evidence",
    "defect_learning",
}


def _authority_rows() -> list[tuple[str, str, str, str]]:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text.count(START) == 1
    assert text.count(END) == 1
    block = text.split(START, 1)[1].split(END, 1)[0]
    rows: list[tuple[str, str, str, str]] = []
    for line in block.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        assert stripped.startswith("|"), f"malformed authority-map row: {line!r}"
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        assert len(cells) == 4, f"malformed authority-map row: {line!r}"
        if cells[0] == "Capability key":
            continue
        if set(cells[0]) <= {"-", ":"}:
            continue
        assert cells[0], f"malformed authority-map row: {line!r}"
        if "COMPATIBILITY_FALLBACK" in cells[1:3]:
            assert "SUNSET:" in cells[3], (
                f"{cells[0]} COMPATIBILITY_FALLBACK requires SUNSET: <condition>"
            )
            assert cells[3].split("SUNSET:", 1)[1].strip(), (
                f"{cells[0]} COMPATIBILITY_FALLBACK requires SUNSET: <condition>"
            )
        rows.append((cells[0], cells[1], cells[2], cells[3]))
    return rows


def test_operational_authority_map_has_one_owner_per_capability() -> None:
    rows = _authority_rows()
    keys = {row[0] for row in rows}
    assert REQUIRED_CAPABILITIES <= keys
    assert len(keys) == len(rows), "capability keys must be unique"

    for key, awiki_role, conductor_role, note in rows:
        assert awiki_role in ALLOWED_ROLES, key
        assert conductor_role in ALLOWED_ROLES, key
        assert [awiki_role, conductor_role].count("OWNER") == 1, key
        assert note and note != "-", key


def test_runtime_and_brain_ownership_stays_split() -> None:
    rows = {key: (awiki, conductor) for key, awiki, conductor, _ in _authority_rows()}
    assert rows["planning_intelligence"] == ("OWNER", "ADAPTER")
    assert rows["workflow_stage_state"] == ("OWNER", "CONSUMER")
    assert rows["work_order_contract"] == ("OWNER", "ADAPTER")
    assert rows["repo_coordination_claim"] == ("OWNER", "ADAPTER")
    assert rows["claim_policy"] == ("OWNER", "ADAPTER")
    assert rows["verification_policy"] == ("OWNER", "ADAPTER")
    assert rows["model_policy"] == ("OWNER", "ADAPTER")
    assert rows["review_lifecycle"] == ("OWNER", "ADAPTER")
    assert rows["runtime_task_instance"] == ("CONSUMER", "OWNER")
    assert rows["status"] == ("ADAPTER", "OWNER")
    assert rows["mutation_gate"] == ("ADAPTER", "OWNER")
    assert rows["runtime_lease"] == ("CONSUMER", "OWNER")
    assert rows["runtime_model_selection"] == ("CONSUMER", "OWNER")
    assert rows["scheduler_ready_set"] == ("CONSUMER", "OWNER")
    assert rows["retry_recovery"] == ("CONSUMER", "OWNER")
    assert rows["next_ready_continuation"] == ("CONSUMER", "OWNER")


def test_contract_requires_fallback_sunset_and_blocks_owner_owner() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "OWNER/OWNER is forbidden" in text
    assert "`COMPATIBILITY_FALLBACK` requires an explicit `SUNSET: <condition>`" in text
    assert "P0-B5/P0-B6/ZRA mutation stays gated" in text


def _with_inserted_authority_row(tmp_path: Path, row: str) -> Path:
    text = CONTRACT.read_text(encoding="utf-8")
    mutated = text.replace(END, f"{row}\n{END}")
    path = tmp_path / "integration-contract.md"
    path.write_text(mutated, encoding="utf-8")
    return path


def test_malformed_authority_rows_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _with_inserted_authority_row(
        tmp_path,
        "| hidden_future_claim_store | OWNER | OWNER |",
    )
    monkeypatch.setattr("test_awiki_a_conductor_authority_contract.CONTRACT", path)
    with pytest.raises(AssertionError, match="malformed authority-map row"):
        _authority_rows()


def test_fallback_rows_require_explicit_sunset_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _with_inserted_authority_row(
        tmp_path,
        "| legacy_claim_bridge | COMPATIBILITY_FALLBACK | OWNER | temporary compatibility |",
    )
    monkeypatch.setattr("test_awiki_a_conductor_authority_contract.CONTRACT", path)
    with pytest.raises(AssertionError, match="SUNSET"):
        _authority_rows()
