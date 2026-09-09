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


EXPECTED_HEADER_CELLS = [
    "Capability key",
    "A-Wiki role",
    "A-Conductor role",
    "Boundary / migration note",
]


def _authority_rows() -> list[tuple[str, str, str, str]]:
    text = CONTRACT.read_text(encoding="utf-8")
    assert text.count(START) == 1
    assert text.count(END) == 1
    assert text.index(START) < text.index(END), "authority-map sentinel order invalid"
    block = text.split(START, 1)[1].split(END, 1)[0]
    nonblank = [line.strip() for line in block.splitlines() if line.strip()]
    assert len(nonblank) >= 2, "malformed authority-map row: missing header/separator"

    def _cells(line: str) -> list[str]:
        assert line.startswith("|"), f"malformed authority-map row: {line!r}"
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == 4, f"malformed authority-map row: {line!r}"
        return cells

    # Structural contract: exactly one header then one separator at the top;
    # every later nonblank row is DATA. No first-cell-only skip is allowed —
    # a mid-table row shaped like a header/separator is an injected bypass.
    assert _cells(nonblank[0]) == EXPECTED_HEADER_CELLS, "authority-map header invalid"
    separator_cells = _cells(nonblank[1])
    assert all(cell and set(cell) <= {"-", ":"} for cell in separator_cells), (
        "authority-map separator invalid"
    )

    rows: list[tuple[str, str, str, str]] = []
    seen_keys: set[str] = set()
    for line in nonblank[2:]:
        cells = _cells(line)
        assert cells[0], f"malformed authority-map row: {line!r}"
        assert cells[0] != EXPECTED_HEADER_CELLS[0], (
            "repeated or misplaced authority-map header"
        )
        assert not set(cells[0]) <= {"-", ":"}, (
            "repeated or misplaced authority-map separator"
        )
        if "COMPATIBILITY_FALLBACK" in cells[1:3]:
            assert "SUNSET:" in cells[3], (
                f"{cells[0]} COMPATIBILITY_FALLBACK requires SUNSET: <condition>"
            )
            assert cells[3].split("SUNSET:", 1)[1].strip(), (
                f"{cells[0]} COMPATIBILITY_FALLBACK requires SUNSET: <condition>"
            )
        assert cells[1] in ALLOWED_ROLES, f"{cells[0]} invalid A-Wiki role"
        assert cells[2] in ALLOWED_ROLES, f"{cells[0]} invalid A-Conductor role"
        assert [cells[1], cells[2]].count("OWNER") == 1, (
            f"{cells[0]} must have exactly one OWNER"
        )
        assert cells[3] and cells[3] != "-", f"{cells[0]} requires a migration note"
        assert cells[0] not in seen_keys, f"duplicate capability key: {cells[0]}"
        seen_keys.add(cells[0])
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

# ---------------------------------------------------------------------------
# WO-P1-167-R1 — pseudo-header/separator bypass RED family (Astra P1).
# Deterministic temp fixtures only; the real contract file is never edited.
# ---------------------------------------------------------------------------


def _rows_for(monkeypatch, path):
    import test_awiki_a_conductor_authority_contract as mod
    monkeypatch.setattr(mod, "CONTRACT", path)
    return mod._authority_rows()


def test_pseudo_header_row_with_owner_owner_is_rejected(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| Capability key | OWNER | OWNER | hidden duplicate authority |",
    )
    with pytest.raises(AssertionError, match="repeated or misplaced authority-map header"):
        _rows_for(monkeypatch, path)


def test_pseudo_separator_row_fallback_without_sunset_is_rejected(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| --- | COMPATIBILITY_FALLBACK | OWNER | temporary without sunset |",
    )
    with pytest.raises(AssertionError, match="repeated or misplaced authority-map separator"):
        _rows_for(monkeypatch, path)


def test_repeated_header_mid_table_is_rejected(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| Capability key | A-Wiki role | A-Conductor role | Boundary / migration note |",
    )
    with pytest.raises(AssertionError, match="repeated or misplaced authority-map header"):
        _rows_for(monkeypatch, path)


def test_repeated_separator_mid_table_is_rejected(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(tmp_path, "|---|---|---|---|")
    with pytest.raises(AssertionError, match="repeated or misplaced authority-map separator"):
        _rows_for(monkeypatch, path)


def test_malformed_pseudo_header_shape_is_rejected(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| Capability key | OWNER | OWNER | hidden | extra |",
    )
    with pytest.raises(AssertionError, match="repeated or misplaced authority-map header|malformed authority-map row"):
        _rows_for(monkeypatch, path)


def test_sentinel_order_invalid_is_rejected(tmp_path, monkeypatch):
    text = CONTRACT.read_text(encoding="utf-8")
    body = text.replace(START, "").replace(END, "")
    path = tmp_path / "integration-contract.md"
    path.write_text(END + body + START, encoding="utf-8")
    with pytest.raises(AssertionError, match="sentinel order"):
        _rows_for(monkeypatch, path)


def test_positive_control_valid_new_owner_row_passes(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| future_capability | OWNER | CONSUMER | A-Wiki owns; Conductor consumes. |",
    )
    rows = _rows_for(monkeypatch, path)
    assert ("future_capability", "OWNER", "CONSUMER") == tuple(rows[-1][:3])


def test_positive_control_fallback_row_with_explicit_sunset_passes(tmp_path, monkeypatch):
    path = _with_inserted_authority_row(
        tmp_path,
        "| legacy_bridge | COMPATIBILITY_FALLBACK | OWNER | temporary; SUNSET: removed by 2026-10-01 |",
    )
    rows = _rows_for(monkeypatch, path)
    assert rows[-1][0] == "legacy_bridge"


def test_positive_control_current_contract_still_passes():
    rows = _authority_rows()
    assert rows and len(rows) >= len(REQUIRED_CAPABILITIES)
