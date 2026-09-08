from pathlib import Path

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
    "claim_policy",
    "runtime_lease",
    "verification_policy",
    "model_policy",
    "runtime_model_selection",
    "review_lifecycle",
    "execution_verification",
    "scheduler_ready_set",
    "retry_recovery",
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
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] in {"Capability key", "---"}:
            continue
        if set(cells[0]) <= {"-", ":"}:
            continue
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
    assert rows["runtime_lease"] == ("CONSUMER", "OWNER")
    assert rows["runtime_model_selection"] == ("CONSUMER", "OWNER")
    assert rows["scheduler_ready_set"] == ("CONSUMER", "OWNER")
    assert rows["retry_recovery"] == ("CONSUMER", "OWNER")


def test_contract_requires_fallback_sunset_and_blocks_owner_owner() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert "OWNER/OWNER is forbidden" in text
    assert "COMPATIBILITY_FALLBACK requires an explicit sunset condition" in text
    assert "P0-B5/P0-B6/ZRA mutation stays gated" in text
