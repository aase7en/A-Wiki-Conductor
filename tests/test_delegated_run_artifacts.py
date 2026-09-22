"""WO-P1-480 (MSP-0) RED-first tests — collision-proof delegated-run
artifact identity.

Pins the frozen physical attempt-directory grammar derived from the
accepted DELEGATED_RUN_ID grammar (``run:<TASK_ID>:<role>:<ordinal>:a<attempt>:<random-id>``,
``references/durable-lanes.md``): new attempt directories are
``attempt-NNNN-<random-id>``; legacy ``attempt-NNNN`` directories stay
readable/recoverable and are never rewritten; enumeration is
deterministic; mismatched, malformed, traversal/separator inputs fail
closed; one delegated run maps to exactly one immutable physical path.

Also pins the WO-P1-480 P1 repair seam: the five proven real-world
pre-grammar pointer aliases recover pointer-only (entire original
string preserved as immutable recovery identity; only trailing
``a<attempt>`` + accepted-hex suffix bound) while canonical minting and
physical path generation stay strictly canonical.

Also pins the WO-P1-480 P2 repair seam: three further proven real
pointer values widen ONLY the bounded legacy recovery classes —
lowercase-hex recovery tails of length 7 through 12 and a bounded
opaque numeric legacy tag in the ordinal position (never reinterpreted
as ordinal). Canonical parser, minting, and directory-name grammar stay
strictly canonical; 6-hex and 13-hex tails stay outside the window.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from a_conductor.delegated_run_artifacts import (
    DelegatedRunArtifactError,
    DelegatedRunIdentity,
    LegacyPointerRunIdentity,
    attempt_dir_name,
    attempt_dir_path,
    enumerate_attempt_dirs,
    parse_attempt_dir_name,
    parse_delegated_run_id,
    recover_attempt_run,
    read_pointer_run_id,
)

RUN_A = "run:WO-P1-480:author:1:a1:352051cd"
RUN_B = "run:WO-P1-480:author:1:a1:9e8f7a6b"
RUN_A2 = "run:WO-P1-480:author:1:a2:11111111"
RUN_12 = "run:WO-P1-480:author:1:a1:a096ec5b8e23"

VALID_RUN_IDS = [
    RUN_A,
    RUN_B,
    RUN_A2,
    RUN_12,
    "run:WO-P1-374:review:3:a12:00000000",
    "run:WO-P1-475:implementation:2:a100:abcdef01",
    "run:WO-P1-480:verify:1:a1:ffffffff",
]


def pointer_md(run_id: str, attempt: int = 1) -> str:
    return (
        "lane_ref: lane:WO-P1-480:author:1\n"
        f"delegated_run_id: {run_id}\n"
        f"attempt: {attempt}\n"
        "status: RUNNING\n"
    )


# ── run-id grammar ──────────────────────────────────────────────────────────


def test_valid_run_ids_parse_and_round_trip() -> None:
    for run_id in VALID_RUN_IDS:
        identity = parse_delegated_run_id(run_id)
        assert identity.run_id == run_id


def test_parse_extracts_components() -> None:
    identity = parse_delegated_run_id(RUN_A2)
    assert identity == DelegatedRunIdentity(
        task_id="WO-P1-480",
        role="author",
        ordinal=1,
        attempt=2,
        random_id="11111111",
    )
    assert identity.suffix == "11111111"


@pytest.mark.parametrize(
    "run_id",
    [
        None,
        123,
        "",
        "lane:WO-P1-480:author:1",
        "run:WO-P1-480:author:1",
        "run:WO-P1-480:author:1:a1",
        "run:WO-P1-480:author:1:a1:352051cd:extra",
        "run:WO-P1-480:author:1:a1:352051CD",
        "run:WO-P1-480:author:1:a1:352051c",
        "run:WO-P1-480:author:1:a1:352051cdef",
        "run:WO-P1-480:author:0:a1:352051cd",
        "run:WO-P1-480:author:01:a1:352051cd",
        "run:WO-P1-480:author:1:a01:352051cd",
        "run:WO-P1-480:author:1:a0:352051cd",
        "run:WO-P1-480:author:1:b1:352051cd",
        "run:WO-P1-480:Author:1:a1:352051cd",
        "run:WO-P1-480::1:a1:352051cd",
        "run::author:1:a1:352051cd",
        "run:..:author:1:a1:352051cd",
        "run:.:author:1:a1:352051cd",
        "run:WO/../x:author:1:a1:352051cd",
        "run:WO\\x:author:1:a1:352051cd",
        "run:WO-P1-480:au/thor:1:a1:352051cd",
        "run:WO-P1-480:author:1:a1:35/2051cd",
        "run:WO-P1-480:author:1:a1:352051cd ",
        " run:WO-P1-480:author:1:a1:352051cd",
        "run:WO-P1-480:author:1:a1:352051cd\n",
        "run:WO-P1-480:author:1:a1:352051cd\x00",
        "run:" + "x" * 300 + ":author:1:a1:352051cd",
    ],
)
def test_malformed_run_ids_fail_closed(run_id: object) -> None:
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_delegated_run_id(run_id)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


# ── physical name grammar ───────────────────────────────────────────────────


def test_attempt_dir_name_uses_run_suffix_and_readable_ordinal() -> None:
    assert attempt_dir_name(RUN_A) == "attempt-0001-352051cd"
    assert attempt_dir_name(RUN_A2) == "attempt-0002-11111111"
    assert attempt_dir_name("run:WO-P1-374:review:3:a12:00000000") == (
        "attempt-0012-00000000"
    )
    assert attempt_dir_name("run:WO-P1-475:implementation:2:a10000:abcdef01") == (
        "attempt-10000-abcdef01"
    )


def test_same_ordinal_distinct_run_ids_diverge() -> None:
    assert attempt_dir_name(RUN_A) != attempt_dir_name(RUN_B)


def test_same_run_id_deterministic_same_path() -> None:
    lane = Path("runs/WO-P1-480/author")
    first = attempt_dir_path(lane, RUN_A)
    for _ in range(3):
        assert attempt_dir_path(lane, RUN_A) == first
    assert first.name == attempt_dir_name(RUN_A)


def test_one_run_one_path_injective_within_lane() -> None:
    lane = Path("runs/WO-P1-480/author")
    names = {attempt_dir_name(r) for r in VALID_RUN_IDS}
    paths = {attempt_dir_path(lane, r) for r in VALID_RUN_IDS}
    assert len(names) == len(VALID_RUN_IDS)
    assert len(paths) == len(VALID_RUN_IDS)
    for name in names:
        assert "/" not in name
        assert "\\" not in name
        assert ".." not in name


@pytest.mark.parametrize(
    "name",
    [
        "attempt-0001",
        "attempt-0001-352051cd",
        "attempt-10000-abcdef01",
        "attempt-0001-a096ec5b8e23",
    ],
)
def test_recognized_attempt_dir_names(name: str) -> None:
    parsed = parse_attempt_dir_name(name)
    assert parsed.dir_name == name


@pytest.mark.parametrize(
    "name",
    [
        None,
        7,
        "",
        "attempt-",
        "attempt-01",
        "attempt-0000",
        "attempt-1-352051cd",
        "attempt-00001",
        "attempt-0001-352051c",
        "attempt-0001-352051CDA",
        "attempt-0001-352051cd-extra",
        "attempt-0001-352051cd/..",
        "../attempt-0001",
        "Attempt-0001",
        "attempt-0001-352051cd\\x",
        "attempt-" + "9" * 12,
    ],
)
def test_unrecognized_attempt_dir_names_fail_closed(name: object) -> None:
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_attempt_dir_name(name)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_INVALID"


def test_parse_attempt_dir_name_forms() -> None:
    legacy = parse_attempt_dir_name("attempt-0007")
    assert legacy.attempt == 7
    assert legacy.suffix is None
    assert legacy.form == "legacy"
    assert legacy.canonical is False
    new = parse_attempt_dir_name("attempt-0007-352051cd")
    assert new.attempt == 7
    assert new.suffix == "352051cd"
    assert new.form == "suffixed"
    assert new.canonical is True
    current = parse_attempt_dir_name("attempt-0007-a096ec5b8e23")
    assert current.form == "suffixed"
    assert current.canonical is True


# ── deterministic enumeration over mixed legacy/new ─────────────────────────


def test_mixed_enumeration_is_deterministic(tmp_path: Path) -> None:
    lane = tmp_path / "author"
    entries = [
        "attempt-0004-a096ec5b8e23",
        "attempt-0003",
        "garbage-dir",
        "attempt-0002-abcdef99",
        "attempt-0001",
        "attempt-0002-11111111",
    ]
    lane.mkdir()
    for name in entries:
        (lane / name).mkdir()
    (lane / "notes.txt").write_text("not a dir", encoding="utf-8")
    (lane / "attempt-01").mkdir()
    (lane / "attempt-0009").write_text("file not dir", encoding="utf-8")

    records = enumerate_attempt_dirs(lane)
    assert [r.dir_name for r in records] == [
        "attempt-0001",
        "attempt-0002-11111111",
        "attempt-0002-abcdef99",
        "attempt-0003",
        "attempt-0004-a096ec5b8e23",
    ]
    assert [r.attempt for r in records] == [1, 2, 2, 3, 4]
    assert [r.form for r in records] == [
        "legacy",
        "suffixed",
        "suffixed",
        "legacy",
        "suffixed",
    ]
    assert [r.canonical for r in records] == [False, True, True, False, True]
    again = enumerate_attempt_dirs(lane)
    assert [r.dir_name for r in again] == [r.dir_name for r in records]


def test_enumeration_missing_lane_dir_is_empty(tmp_path: Path) -> None:
    assert enumerate_attempt_dirs(tmp_path / "absent") == ()


def test_enumeration_same_ordinal_distinct_runs_coexist(tmp_path: Path) -> None:
    lane = tmp_path / "author"
    lane.mkdir()
    for run_id in (RUN_A, RUN_B):
        (lane / attempt_dir_name(run_id)).mkdir()
    records = enumerate_attempt_dirs(lane)
    assert [r.dir_name for r in records] == [
        "attempt-0001-352051cd",
        "attempt-0001-9e8f7a6b",
    ]


# ── pointer recovery ────────────────────────────────────────────────────────


def test_legacy_pointer_recovery_preserved_and_not_rewritten(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    original = pointer_md(RUN_A)
    (attempt_dir / "pointer.md").write_text(original, encoding="utf-8")

    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == RUN_A
    assert identity.attempt == 1
    assert (attempt_dir / "pointer.md").read_text(encoding="utf-8") == original


def test_new_pointer_recovery_round_trip(tmp_path: Path) -> None:
    for run_id in (RUN_A, RUN_B, RUN_12):
        attempt_dir = tmp_path / attempt_dir_name(run_id)
        attempt_dir.mkdir()
        (attempt_dir / "pointer.md").write_text(pointer_md(run_id), encoding="utf-8")
    identities = [
        recover_attempt_run(tmp_path / attempt_dir_name(r)).run_id
        for r in (RUN_A, RUN_B, RUN_12)
    ]
    assert identities == [RUN_A, RUN_B, RUN_12]


def test_current_execution_pointer_json_recovery(tmp_path: Path) -> None:
    attempt_dir = tmp_path / attempt_dir_name(RUN_12)
    attempt_dir.mkdir()
    (attempt_dir / "execution-pointer.json").write_text(
        '{"delegated_run_id":"' + RUN_12 + '","status":"TERMINAL"}',
        encoding="utf-8",
    )
    assert recover_attempt_run(attempt_dir).run_id == RUN_12


def test_pointer_sources_must_agree(tmp_path: Path) -> None:
    attempt_dir = tmp_path / attempt_dir_name(RUN_A)
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(RUN_A), encoding="utf-8")
    (attempt_dir / "execution-pointer.json").write_text(
        '{"delegated_run_id":"' + RUN_B + '"}', encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_AMBIGUOUS"


def test_malformed_execution_pointer_json_fails_closed(tmp_path: Path) -> None:
    attempt_dir = tmp_path / attempt_dir_name(RUN_A)
    attempt_dir.mkdir()
    (attempt_dir / "execution-pointer.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_READ_FAILED"


def test_pointer_field_style_variants_parse(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001-352051cd"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        "# pointer\n\n- delegated_run_id: " + RUN_A + "\n- attempt: 1\n",
        encoding="utf-8",
    )
    assert read_pointer_run_id(attempt_dir).run_id == RUN_A


def test_pointer_crlf_lines_parse(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_bytes(
        ("delegated_run_id: " + RUN_A + "\r\nattempt: 1\r\n").encode("utf-8")
    )
    assert recover_attempt_run(attempt_dir).run_id == RUN_A


def test_new_pointer_run_suffix_mismatch_rejected(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0005-abcd1234"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md("run:WO-P1-480:author:1:a5:ffffffff", attempt=5),
        encoding="utf-8",
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_new_pointer_attempt_ordinal_mismatch_rejected(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0005-abcd1234"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md("run:WO-P1-480:author:1:a4:abcd1234", attempt=4),
        encoding="utf-8",
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_legacy_pointer_attempt_ordinal_mismatch_rejected(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt-0003"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md("run:WO-P1-480:author:1:a1:352051cd", attempt=1),
        encoding="utf-8",
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_current_12_hex_suffix_binds_exact_pointer(tmp_path: Path) -> None:
    attempt_dir = tmp_path / attempt_dir_name(RUN_12)
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(RUN_12), encoding="utf-8")
    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == RUN_12


def test_noncanonical_suffix_dir_recovers_pointer_only(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001-a096ec5b8e23ffff"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(RUN_A), encoding="utf-8")
    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == RUN_A


def test_pointer_run_id_field_missing(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text("lane_ref: lane:WO:author:1\n")
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_MISSING"


def test_pointer_run_id_ambiguous(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        f"delegated_run_id: {RUN_A}\ndelegated_run_id: {RUN_B}\n",
        encoding="utf-8",
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_AMBIGUOUS"


def test_pointer_identical_duplicates_are_unambiguous(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        f"delegated_run_id: {RUN_A}\ndelegated_run_id: {RUN_A}\n",
        encoding="utf-8",
    )
    assert read_pointer_run_id(attempt_dir).run_id == RUN_A


def test_pointer_absent_fails_closed(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_READ_FAILED"


def test_pointer_undecodable_bytes_fail_closed(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_READ_FAILED"


def test_pointer_traversal_value_fails_closed(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        "delegated_run_id: ../../evil\n", encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "RUN_ID_INVALID"


def test_recover_rejects_unrecognized_directory_name(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "not-an-attempt"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(RUN_A), encoding="utf-8")
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_INVALID"


# ── recovery-only legacy pointer aliases (WO-P1-480 P1 repair) ──────────────

# Five proven real-world pre-grammar delegated_run_id values observed
# in actual durable pointers (WO-P1-480 P1 repair packet). Structural
# shapes: missing ordinal segment, or a non-decimal token in the
# ordinal position. Recovery-only; canonical minting/path generation
# must keep rejecting them.
LEGACY_ALIAS_NO_ORDINAL = "run:WO-P1-478:r3-review:a1:2933deb345c2"
LEGACY_ALIAS_LONG_ROLE = "run:WO-P1-478:phase-a-implementation:a2:b1a96741c8d5"
LEGACY_ALIAS_HEX_IN_ROLE = "run:WO-P1-475:msp2-shaping-e6f96e7:a1:8ed239b4d54f"
LEGACY_ALIAS_HEX_MIDDLE_A2 = "run:WO-P1-475:r3-max-review:acfa39d:a2:923935febee8"
LEGACY_ALIAS_HEX_MIDDLE_A1 = "run:WO-P1-475:flash-architecture:acfa39d:a1:16b32a2f6ea9"

PROVEN_LEGACY_ALIASES = [
    (LEGACY_ALIAS_NO_ORDINAL, 1, "2933deb345c2"),
    (LEGACY_ALIAS_LONG_ROLE, 2, "b1a96741c8d5"),
    (LEGACY_ALIAS_HEX_IN_ROLE, 1, "8ed239b4d54f"),
    (LEGACY_ALIAS_HEX_MIDDLE_A2, 2, "923935febee8"),
    (LEGACY_ALIAS_HEX_MIDDLE_A1, 1, "16b32a2f6ea9"),
]

LEGACY_NEAR_MISSES = [
    "run:WO-P1-478:r3-review:2933deb345c2",  # attempt segment missing (never infer)
    "run:WO-P1-478:r3-review:a1",  # random suffix missing (never infer)
    "run:WO-P1-478:r3-review:a1:",  # trailing blank segment
    "run:WO-P1-478:r3-review:a01:2933deb345c2",  # leading-zero attempt
    "run:WO-P1-478:r3-review:a0:2933deb345c2",  # zero attempt
    "run:WO-P1-478:r3-review:b1:2933deb345c2",  # non-attempt marker
    "run:WO-P1-478:r3-review:a1:2933DEB345C2",  # uppercase hex suffix
    # 11-hex tail near-miss from the P1 list was superseded by the P2
    # repair: 7..12-hex is now the bounded legacy recovery window, so
    # the in-window lengths are pinned as positives in the P2 section
    # below instead of as near-misses here.
    "run:WO-P1-478:r3-review:a1:2933deb345c2:extra",  # unobserved extra segment
    "run:WO-P1-478:r3-review:01:a1:2933deb345c2",  # leading-zero decimal middle
    "run:WO-P1-478:r3-review:0:a1:2933deb345c2",  # zero decimal middle
    "run:A:B:C:D:a1:2933deb345c2",  # six legacy segments (unobserved)
    "run:WO-P1-478:R3-Review:a1:2933deb345c2",  # uppercase role
    "run:WO-P1-478::a1:2933deb345c2",  # blank role segment
    "run::r3-review:a1:2933deb345c2",  # blank task-id segment
    "run:..:r3-review:a1:2933deb345c2",  # traversal task id
    "run:.:r3-review:a1:2933deb345c2",  # dot task id
    "run:WO/../x:r3-review:a1:2933deb345c2",  # separator/traversal task id
    "run:WO-P1-478:au/thor:a1:2933deb345c2",  # separator in role
    "run:WO-P1-478:r3-review:a1:../evil",  # traversal suffix
    "run:WO-P1-478:r3-review:a1:2933deb345c2 ",  # trailing whitespace
    " run:WO-P1-478:r3-review:a1:2933deb345c2",  # leading whitespace
    "run:WO-P1-478:r3-review:a1:2933deb345c2\x00",  # control byte
    "run:" + "x" * 300 + ":r3-review:a1:2933deb345c2",  # oversized task id
]


def _write_execution_pointer(attempt_dir: Path, run_id: str) -> None:
    (attempt_dir / "execution-pointer.json").write_text(
        json.dumps({"delegated_run_id": run_id}), encoding="utf-8"
    )


@pytest.mark.parametrize(
    "alias,attempt,suffix", PROVEN_LEGACY_ALIASES
)
def test_proven_legacy_aliases_recover_from_legacy_attempt_dirs(
    tmp_path: Path, alias: str, attempt: int, suffix: str
) -> None:
    attempt_dir = tmp_path / f"attempt-{attempt:04d}"
    attempt_dir.mkdir()
    original = pointer_md(alias, attempt=attempt)
    (attempt_dir / "pointer.md").write_text(original, encoding="utf-8")

    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == alias  # entire original string preserved
    assert identity.attempt == attempt
    assert identity.suffix == suffix
    assert not isinstance(identity, DelegatedRunIdentity)  # nothing inferred
    assert (attempt_dir / "pointer.md").read_text(encoding="utf-8") == original


def test_end_to_end_legacy_alias_recovery_reproduces_pre_repair_failure(
    tmp_path: Path,
) -> None:
    # Pre-repair (exact head f3d2b41) this exact real-world layout failed
    # recovery with RUN_ID_INVALID on the attempt-0001 directory because
    # the strict canonical parser rejected the structurally non-canonical
    # legacy pointer value.
    attempt_dir = tmp_path / "runs" / "WO-P1-478" / "r3-review" / "attempt-0001"
    attempt_dir.mkdir(parents=True)
    original = (
        "lane_ref: lane:WO-P1-478:r3-review:1\n"
        "delegated_run_id: run:WO-P1-478:r3-review:a1:2933deb345c2\n"
        "attempt: 1\n"
        "status: TERMINAL_UNHARVESTED\n"
    )
    (attempt_dir / "pointer.md").write_text(original, encoding="utf-8")

    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == LEGACY_ALIAS_NO_ORDINAL
    assert identity.attempt == 1
    assert identity.suffix == "2933deb345c2"
    assert not isinstance(identity, DelegatedRunIdentity)
    assert (attempt_dir / "pointer.md").read_text(encoding="utf-8") == original


def test_proven_legacy_alias_via_execution_pointer_json(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt-0002"
    attempt_dir.mkdir()
    _write_execution_pointer(attempt_dir, LEGACY_ALIAS_HEX_MIDDLE_A2)
    identity = recover_attempt_run(attempt_dir)
    assert identity.run_id == LEGACY_ALIAS_HEX_MIDDLE_A2
    assert identity.attempt == 2
    assert identity.suffix == "923935febee8"


def test_legacy_alias_identity_surface(tmp_path: Path) -> None:
    from a_conductor.delegated_run_artifacts import LegacyPointerRunIdentity

    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, LegacyPointerRunIdentity)
    assert identity.run_id == LEGACY_ALIAS_NO_ORDINAL
    assert identity.attempt == 1
    assert identity.random_id == "2933deb345c2"
    assert identity.suffix == "2933deb345c2"


def test_legacy_alias_on_suffixed_dir_binds_only_with_exact_suffix(
    tmp_path: Path,
) -> None:
    bound = tmp_path / "attempt-0001-2933deb345c2"
    bound.mkdir()
    (bound / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    identity = recover_attempt_run(bound)
    assert identity.run_id == LEGACY_ALIAS_NO_ORDINAL

    wrong_suffix = tmp_path / "attempt-0001-9e8f7a6b1111"
    wrong_suffix.mkdir()
    (wrong_suffix / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(wrong_suffix)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"

    wrong_attempt = tmp_path / "attempt-0002-2933deb345c2"
    wrong_attempt.mkdir()
    (wrong_attempt / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(wrong_attempt)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_legacy_alias_on_noncanonical_suffix_dir_fails_closed(
    tmp_path: Path,
) -> None:
    # A legacy alias cannot prove physical suffix agreement on a
    # non-8/12-hex suffixed directory, so recovery fails closed instead
    # of binding pointer-only.
    attempt_dir = tmp_path / "attempt-0001-a096ec5b8e23ffff"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_legacy_alias_attempt_mismatch_on_legacy_dir_rejected(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt-0003"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_dual_pointer_sources_must_agree_on_exact_legacy_string(
    tmp_path: Path,
) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()

    (attempt_dir / "pointer.md").write_text(
        pointer_md(LEGACY_ALIAS_NO_ORDINAL), encoding="utf-8"
    )
    _write_execution_pointer(attempt_dir, LEGACY_ALIAS_NO_ORDINAL)
    assert read_pointer_run_id(attempt_dir).run_id == LEGACY_ALIAS_NO_ORDINAL

    _write_execution_pointer(attempt_dir, LEGACY_ALIAS_HEX_IN_ROLE)
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_AMBIGUOUS"

    # Same attempt + same trailing suffix but a different full string
    # (canonical vs legacy alias) is still an exact-string disagreement.
    (attempt_dir / "pointer.md").write_text(
        pointer_md("run:WO-P1-478:r3-review:1:a1:2933deb345c2"),
        encoding="utf-8",
    )
    _write_execution_pointer(attempt_dir, LEGACY_ALIAS_NO_ORDINAL)
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_AMBIGUOUS"


def test_decimal_ordinal_still_uses_canonical_parser(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    canonical = "run:WO-P1-478:r3-review:2:a1:2933deb345c2"
    (attempt_dir / "pointer.md").write_text(pointer_md(canonical), encoding="utf-8")
    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, DelegatedRunIdentity)
    assert identity.ordinal == 2
    assert identity.run_id == canonical


@pytest.mark.parametrize("run_id", LEGACY_NEAR_MISSES)
def test_legacy_near_misses_fail_closed(tmp_path: Path, run_id: str) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    _write_execution_pointer(attempt_dir, run_id)
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


def test_legacy_near_miss_via_pointer_md_fails_closed(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md("run:WO-P1-478:r3-review:01:a1:2933deb345c2"),
        encoding="utf-8",
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "RUN_ID_INVALID"


# ── canonical minting strictness (repair guard) ─────────────────────────────


@pytest.mark.parametrize("alias,attempt,suffix", PROVEN_LEGACY_ALIASES)
def test_legacy_aliases_rejected_by_canonical_parser(
    alias: str, attempt: int, suffix: str
) -> None:
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_delegated_run_id(alias)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


@pytest.mark.parametrize("alias,attempt,suffix", PROVEN_LEGACY_ALIASES)
def test_legacy_aliases_never_mint_physical_paths(
    alias: str, attempt: int, suffix: str
) -> None:
    for factory in (attempt_dir_name, lambda r: str(attempt_dir_path("lane", r))):
        with pytest.raises(DelegatedRunArtifactError) as excinfo:
            factory(alias)
        assert excinfo.value.code == "RUN_ID_INVALID"


# ── recovery-only widened bounded classes (WO-P1-480 P2 repair) ──────────────

# Three further proven real-world pointer values (WO-P1-480 P2 repair
# packet; independent full durable-pointer census at exact head
# ef61fe14c55452979265137eb39e9cf5245be545). The canonical parser
# correctly rejects each one; the recovery-only legacy seam must accept
# them pointer-only, preserving the entire original string verbatim.
#   1. 10-hex legacy recovery tail (decimal middle, non-8/12 tail);
#      note: the packet annotates this value as "9-hex" but the exact
#      string is authoritative and its tail is 10 lowercase-hex chars —
#      both lengths sit inside the declared 7..12 recovery window;
#   2. 7-hex legacy recovery tail (decimal middle, non-8/12 tail);
#   3. numeric legacy tag 20260922 in the ordinal-position slot
#      (canonical decimal ordinal range rejects it as out-of-range).
P2_TEN_HEX_TAIL = "run:WO-P1-449:r3-review:1:a1:1516601fcc"
P2_SEVEN_HEX_TAIL = "run:WO-P1-449:r3-rereview-cycle2:1:a1:d2cc2c4"
P2_NUMERIC_TAG = "run:WO-P1-453:cutover-flash-advisory:20260922:a2:dfe48eaa88fe"
P2_REAL_VALUES = [P2_TEN_HEX_TAIL, P2_SEVEN_HEX_TAIL, P2_NUMERIC_TAG]


def test_p2_ten_hex_tail_recovers_end_to_end(tmp_path: Path) -> None:
    # Real directory shape: suffixed with the run's exact 10-hex tail
    # (directory grammar accepts 8..64-hex suffixes; 10-hex is
    # non-canonical census-visible, and exact suffix agreement binds).
    attempt_dir = (
        tmp_path / "runs" / "WO-P1-449" / "r3-review" / "attempt-0001-1516601fcc"
    )
    attempt_dir.mkdir(parents=True)
    original = (
        "lane_ref: lane:WO-P1-449:r3-review:1\n"
        "delegated_run_id: run:WO-P1-449:r3-review:1:a1:1516601fcc\n"
        "attempt: 1\n"
        "status: TERMINAL\n"
    )
    (attempt_dir / "pointer.md").write_text(original, encoding="utf-8")

    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, LegacyPointerRunIdentity)
    assert identity.run_id == P2_TEN_HEX_TAIL  # verbatim, never rewritten
    assert identity.attempt == 1
    assert identity.suffix == "1516601fcc"
    assert not isinstance(identity, DelegatedRunIdentity)
    assert (attempt_dir / "pointer.md").read_text(encoding="utf-8") == original


def test_p2_seven_hex_tail_recovers_on_legacy_dir(tmp_path: Path) -> None:
    # Real directory shape: unsuffixed legacy attempt directory — a
    # 7-hex tail can never form a recognizable suffixed directory name
    # (directory grammar requires >=8 hex), so recovery is
    # attempt-bound with the full pointer string preserved.
    attempt_dir = (
        tmp_path / "runs" / "WO-P1-449" / "r3-rereview-cycle2" / "attempt-0001"
    )
    attempt_dir.mkdir(parents=True)
    original = (
        "lane_ref: lane:WO-P1-449:r3-rereview-cycle2:1\n"
        "delegated_run_id: run:WO-P1-449:r3-rereview-cycle2:1:a1:d2cc2c4\n"
        "attempt: 1\n"
        "status: TERMINAL\n"
    )
    (attempt_dir / "pointer.md").write_text(original, encoding="utf-8")

    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, LegacyPointerRunIdentity)
    assert identity.run_id == P2_SEVEN_HEX_TAIL
    assert identity.attempt == 1
    assert identity.suffix == "d2cc2c4"
    assert (attempt_dir / "pointer.md").read_text(encoding="utf-8") == original


def test_p2_numeric_tag_recovers_as_legacy_evidence(tmp_path: Path) -> None:
    # Real directory shape: suffixed with the run's exact 12-hex tail.
    # The numeric legacy tag 20260922 recovers ONLY as legacy evidence
    # and is never normalized/reinterpreted as an ordinal.
    attempt_dir = (
        tmp_path / "runs" / "WO-P1-453" / "cutover-flash-advisory"
        / "attempt-0002-dfe48eaa88fe"
    )
    attempt_dir.mkdir(parents=True)
    _write_execution_pointer(attempt_dir, P2_NUMERIC_TAG)

    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, LegacyPointerRunIdentity)
    assert identity.run_id == P2_NUMERIC_TAG
    assert identity.attempt == 2
    assert identity.suffix == "dfe48eaa88fe"
    assert not isinstance(identity, DelegatedRunIdentity)  # no ordinal binding


def test_p2_ten_hex_tail_via_pointer_md_and_json_agree(tmp_path: Path) -> None:
    attempt_dir = tmp_path / "attempt-0001-1516601fcc"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(P2_TEN_HEX_TAIL), encoding="utf-8")
    _write_execution_pointer(attempt_dir, P2_TEN_HEX_TAIL)
    identity = read_pointer_run_id(attempt_dir)
    assert identity.run_id == P2_TEN_HEX_TAIL

    # Dual sources must agree on the exact full string even when both
    # values are individually inside the widened recovery classes.
    _write_execution_pointer(
        attempt_dir, "run:WO-P1-449:r3-review:1:a1:1516601fc"  # 9-hex variant
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "POINTER_RUN_ID_AMBIGUOUS"


def test_p2_ten_hex_tail_wrong_attempt_or_suffix_rejected(
    tmp_path: Path,
) -> None:
    wrong_attempt = tmp_path / "attempt-0002-1516601fcc"
    wrong_attempt.mkdir()
    (wrong_attempt / "pointer.md").write_text(
        pointer_md(P2_TEN_HEX_TAIL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(wrong_attempt)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"

    wrong_suffix = tmp_path / "attempt-0001-9e8f7a6b"
    wrong_suffix.mkdir()
    (wrong_suffix / "pointer.md").write_text(
        pointer_md(P2_TEN_HEX_TAIL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(wrong_suffix)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


def test_p2_seven_hex_pointer_on_suffixed_dir_fails_closed(
    tmp_path: Path,
) -> None:
    # A 7-hex alias tail can never equal an 8..64-hex directory suffix,
    # so a suffixed directory always fails closed instead of binding
    # pointer-only.
    attempt_dir = tmp_path / "attempt-0001-d2cc2c4a"  # 8-hex directory suffix
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(
        pointer_md(P2_SEVEN_HEX_TAIL), encoding="utf-8"
    )
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        recover_attempt_run(attempt_dir)
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_RUN_MISMATCH"


@pytest.mark.parametrize(
    "tail",
    [
        "d2cc2c4",  # 7 (real P2 evidence tail)
        "352051cd",  # 8 (historical canonical length)
        "1516601fc",  # 9 (synthetic; 9-char prefix of the real 10-hex tail)
        "1516601fcc",  # 10 (real P2 evidence tail)
        "2933deb345c",  # 11 (former P1 near-miss, now in-window)
        "dfe48eaa88fe",  # 12 (current canonical length; real P2 evidence tail)
    ],
)
def test_p2_recovery_tail_window_seven_through_twelve(
    tmp_path: Path, tail: str
) -> None:
    # The whole declared 7..12-hex window recovers on a legacy
    # directory (synthetic in-class tails beyond the three real
    # values; no directory suffix agreement is involved).
    run_id = f"run:WO-P1-449:r3-window:a1:{tail}"
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    _write_execution_pointer(attempt_dir, run_id)
    identity = read_pointer_run_id(attempt_dir)
    assert isinstance(identity, LegacyPointerRunIdentity)
    assert identity.run_id == run_id
    assert identity.attempt == 1
    assert identity.suffix == tail


@pytest.mark.parametrize(
    "run_id",
    [
        "run:WO-P1-449:r3-review:1:a1:d2cc2c",  # 6-hex tail: below window
        "run:WO-P1-449:r3-review:1:a1:1516601fcc0dd",  # 13-hex: above window
        "run:WO-P1-449:r3-window:a1:d2cc2c",  # 6-hex on 4-part shape
        "run:WO-P1-449:r3-window:a1:1516601fcc0dd",  # 13-hex on 4-part shape
        "run:WO-P1-449:r3-review:1:a1:1516601FCC",  # uppercase stays closed
    ],
)
def test_p2_recovery_tails_outside_window_fail_closed(
    tmp_path: Path, run_id: str
) -> None:
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    _write_execution_pointer(attempt_dir, run_id)
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


P2_NUMERIC_TAG_NEAR_MISSES = [
    "run:WO-P1-453:cutover-flash-advisory:0:a2:dfe48eaa88fe",  # zero tag
    "run:WO-P1-453:cutover-flash-advisory:01:a2:dfe48eaa88fe",  # leading zero
    "run:WO-P1-453:cutover-flash-advisory:0123:a2:dfe48eaa88fe",  # leading zero
    "run:WO-P1-453:cutover-flash-advisory:123456789:a2:dfe48eaa88fe",  # 9 digits
    "run:WO-P1-453:cutover-flash-advisory:+1:a2:dfe48eaa88fe",  # plus sign
    "run:WO-P1-453:cutover-flash-advisory:1.5:a2:dfe48eaa88fe",  # decimal point
    "run:WO-P1-453:cutover-flash-advisory:..:a2:dfe48eaa88fe",  # traversal
    "run:WO-P1-453:cutover-flash-advisory:2026/22:a2:dfe48eaa88fe",  # separator
    "run:WO-P1-453:cutover-flash-advisory:20260922:x:a2:dfe48eaa88fe",  # 6 segments
    "run:WO-P1-453:cutover-flash-advisory:20260922:a02:dfe48eaa88fe",  # lz attempt
]


@pytest.mark.parametrize("run_id", P2_NUMERIC_TAG_NEAR_MISSES)
def test_p2_numeric_tag_near_misses_fail_closed(
    tmp_path: Path, run_id: str
) -> None:
    attempt_dir = tmp_path / "attempt-0002"
    attempt_dir.mkdir()
    _write_execution_pointer(attempt_dir, run_id)
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        read_pointer_run_id(attempt_dir)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


def test_p2_valid_canonical_decimal_ordinal_stays_canonical(
    tmp_path: Path,
) -> None:
    # Real canonical durable pointer for the same lane as the 7-hex
    # evidence (runs/WO-P1-449/review-terminal-harvest-notice.md): a
    # valid canonical decimal ordinal plus a 12-hex tail must keep
    # parsing canonically, never as a legacy alias.
    canonical = "run:WO-P1-449:r3-rereview-cycle2:1:a1:e7c88021eadd"
    attempt_dir = tmp_path / "attempt-0001"
    attempt_dir.mkdir()
    (attempt_dir / "pointer.md").write_text(pointer_md(canonical), encoding="utf-8")
    identity = recover_attempt_run(attempt_dir)
    assert isinstance(identity, DelegatedRunIdentity)
    assert identity.ordinal == 1
    assert identity.attempt == 1
    assert identity.random_id == "e7c88021eadd"
    assert identity.run_id == canonical


def test_p2_directory_name_grammar_not_widened() -> None:
    # Directory-name recognition is untouched by the P2 repair: 7-hex
    # suffixes and uppercase stay unrecognized, 9-hex stays the
    # non-canonical census-visible suffixed form it already was.
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_attempt_dir_name("attempt-0001-d2cc2c4")
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_INVALID"
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_attempt_dir_name("attempt-0001-1516601FCC")
    assert excinfo.value.code == "ATTEMPT_DIR_NAME_INVALID"
    nine = parse_attempt_dir_name("attempt-0001-1516601fcc")
    assert nine.attempt == 1
    assert nine.suffix == "1516601fcc"
    assert nine.form == "suffixed"
    assert nine.canonical is False


@pytest.mark.parametrize("run_id", P2_REAL_VALUES)
def test_p2_real_values_rejected_by_canonical_parser(run_id: str) -> None:
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_delegated_run_id(run_id)
    assert excinfo.value.code == "RUN_ID_INVALID"
    assert str(excinfo.value) == "RUN_ID_INVALID"


@pytest.mark.parametrize("run_id", P2_REAL_VALUES)
def test_p2_real_values_never_mint_physical_paths(run_id: str) -> None:
    # 20260922 (and every other P2 value) can never mint a new attempt
    # directory: minting stays strictly canonical.
    for factory in (attempt_dir_name, lambda r: str(attempt_dir_path("lane", r))):
        with pytest.raises(DelegatedRunArtifactError) as excinfo:
            factory(run_id)
        assert excinfo.value.code == "RUN_ID_INVALID"


@pytest.mark.parametrize(
    "run_id",
    [
        "run:WO-P1-480:author:1:a1:352051c",  # 7-hex tail canonical reject
        "run:WO-P1-480:author:1:a1:352051cdef",  # 10-hex tail canonical reject
        "run:WO-P1-453:cutover-flash-advisory:20260922:a2:dfe48eaa88fe",
    ],
)
def test_p2_canonical_parser_still_rejects_non_8_12_tails(run_id: str) -> None:
    # The canonical parser was NOT broadened by the recovery-window
    # widening: only 8/12-hex tails mint and parse canonically.
    with pytest.raises(DelegatedRunArtifactError) as excinfo:
        parse_delegated_run_id(run_id)
    assert excinfo.value.code == "RUN_ID_INVALID"





def test_module_declares_no_authority_surfaces() -> None:
    import a_conductor.delegated_run_artifacts as module

    for forbidden in (
        "sqlite3",
        "threading",
        "multiprocessing",
        "subprocess",
        "asyncio",
        "sched",
        "socket",
    ):
        assert not hasattr(module, forbidden)
    assert not hasattr(module, "acquire")
    assert not hasattr(module, "release")
