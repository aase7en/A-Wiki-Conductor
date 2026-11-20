"""WO-P1-459 RED-first acceptance tests for the bounded A-Wiki secret writer.

Every fixture is a synthetic temporary directory. No live Drive root, real
credential material, provider store, database, network, or child process is
touched. Raw secret values are represented by a unique synthetic canary and
must never appear in results, representations, or exception surfaces.

The accepted reader contract lives in ``awiki_environment_resolver`` and is
never changed to make writer tests pass.
"""

from __future__ import annotations

import hashlib
import os
import re
import socket
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

import a_conductor.awiki_secret_writer as awiki_secret_writer
from a_conductor.awiki_secret_writer import (
    AWikiSecretWriteAuthority,
    AWikiSecretWriteError,
    AWikiSecretWriter,
)
from a_conductor.awiki_environment_resolver import (
    AWikiDriveEnvironmentSource,
    AWikiEnvironmentReferenceResolver,
    AWikiEnvironmentResolutionError,
    _parse_env_file,
)

CANARY = "CANARY-WO459-SYNTHETIC-4b1c0de5-VALUE"
TEMP_PREFIX = ".awiki-secret-writer-"
CODE_SHAPE = re.compile(r"^[A-Z][A-Z0-9_]*$")


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


def make_drive(tmp_path: Path, env_text: str | bytes = "OTHER=other-value\n") -> Path:
    root = tmp_path / "A-Wiki-Data"
    (root / "secrets").mkdir(parents=True)
    target = root / "secrets" / "global.env"
    if isinstance(env_text, str):
        target.write_text(env_text, encoding="utf-8", newline="")
    else:
        target.write_bytes(env_text)
    return root


def make_writer(root: Path, keys=("TARGET_KEY", "OTHER_KEY", "NEW_KEY")) -> AWikiSecretWriter:
    return AWikiSecretWriter(root, allowed_keys=AWikiSecretWriteAuthority(keys))


def target_of(writer: AWikiSecretWriter) -> Path:
    return writer.target_path


def only_global_env(root: Path) -> None:
    secrets = root / "secrets"
    assert sorted(path.name for path in secrets.iterdir()) == ["global.env"]


def tree_state(base: Path) -> dict[str, str]:
    state: dict[str, str] = {}
    for path in sorted(base.rglob("*")):
        rel = path.relative_to(base).as_posix()
        if path.is_file():
            state[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            state[rel + "/"] = "dir"
    return state


def concurrent_edit_then_temp(monkeypatch, drifted_bytes: bytes) -> None:
    """Inject a real unrelated concurrent edit mid-operation, before replace."""
    real = awiki_secret_writer._write_owned_temp

    def fake(directory: Path, data: bytes, mode: int) -> Path:
        target_of_writer_dir = directory / "global.env"
        target_of_writer_dir.write_bytes(drifted_bytes)
        return real(directory, data, mode)

    monkeypatch.setattr(awiki_secret_writer, "_write_owned_temp", fake)


def read_source(root: Path) -> AWikiDriveEnvironmentSource:
    return AWikiDriveEnvironmentSource(root)


# ---------------------------------------------------------------------------
# authority contract (integrator trust-boundary requirements)
# ---------------------------------------------------------------------------


def test_authority_rejects_empty_malformed_and_duplicate_keys() -> None:
    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriteAuthority([])
    assert exc.value.code == "ALLOWED_KEYS_INVALID"

    bad_members = ["9BAD", "A-B", "A/B", "", "A B", "A\nB", "A/B/X", 5, None, b"KEY"]
    for member in bad_members:
        with pytest.raises(AWikiSecretWriteError) as exc:
            AWikiSecretWriteAuthority(["GOOD_KEY", member])
        assert exc.value.code == "ALLOWED_KEYS_INVALID"

    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriteAuthority(("DUP_KEY", "DUP_KEY"))
    assert exc.value.code == "ALLOWED_KEYS_INVALID"

    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriteAuthority("TARGET_KEY")
    assert exc.value.code == "ALLOWED_KEYS_INVALID"


def test_authority_bounds_cardinality_and_retains_no_values() -> None:
    authority = AWikiSecretWriteAuthority([f"K{i:02d}" for i in range(64)])
    assert len(authority) == 64
    assert "K01" in authority

    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriteAuthority([f"K{i:02d}" for i in range(65)])
    assert exc.value.code == "ALLOWED_KEYS_INVALID"

    named = AWikiSecretWriteAuthority(("TARGET_KEY",))
    assert named.is_allowed("TARGET_KEY") is True
    assert named.is_allowed("OTHER") is False
    assert "TARGET_KEY" not in repr(named)
    assert not any(
        isinstance(getattr(authority, name, None), str)
        for name in vars(authority)
    )


def test_writer_requires_authority_object_and_canonical_directory_root(tmp_path: Path) -> None:
    root = make_drive(tmp_path)
    with pytest.raises(TypeError):
        AWikiSecretWriter(root, allowed_keys=["TARGET_KEY"])
    with pytest.raises(TypeError):
        AWikiSecretWriter(root, allowed_keys=None)

    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriter(tmp_path / "missing-root", allowed_keys=AWikiSecretWriteAuthority(("K",)))
    assert exc.value.code == "DRIVE_ROOT_INVALID"

    plain_file = tmp_path / "plain.txt"
    plain_file.write_text("x", encoding="utf-8")
    with pytest.raises(AWikiSecretWriteError) as exc:
        AWikiSecretWriter(plain_file, allowed_keys=AWikiSecretWriteAuthority(("K",)))
    assert exc.value.code == "DRIVE_ROOT_INVALID"


# ---------------------------------------------------------------------------
# matrix 1/86/94 — key validation before any disk access
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_key",
    [5, None, "", "   ", "9KEY", "KEY-BAD", "KEY/BAD", "../ETC", "KEY BAD",
     "KEY\tBAD", "KEY\nBAD", "KEY\rBAD", "KEY\x00BAD", "KEY=", "=KEY", "KEY;X"],
)
def test_invalid_keys_rejected_before_mutation(tmp_path: Path, bad_key) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    original = target_of(writer).read_bytes()
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert(bad_key, CANARY)
    assert exc.value.code == "KEY_INVALID"
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate(bad_key, CANARY)
    assert exc.value.code == "KEY_INVALID"
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.delete(bad_key)
    assert exc.value.code == "KEY_INVALID"
    assert target_of(writer).read_bytes() == original
    only_global_env(root)


def test_non_allowlisted_key_rejected_with_unchanged_bytes_and_mtime(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    before = target.stat()
    for call in (
        lambda: writer.insert("FORBIDDEN_KEY", CANARY),
        lambda: writer.rotate("FORBIDDEN_KEY", CANARY),
        lambda: writer.delete("FORBIDDEN_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "KEY_NOT_ALLOWED"
    after = target.stat()
    assert target.read_bytes() == b"OTHER=1\n"
    assert after.st_mtime_ns == before.st_mtime_ns
    only_global_env(root)


# ---------------------------------------------------------------------------
# matrix 2/30/93 — value validation and exact reader round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_value",
    [5, None, "", "   ", "\tlead", "trail ", " lead", "'quoted'", '"quoted"',
     "''", '""', "line\nbreak", "carriage\rreturn", "nul\x00byte", "vert\x0btab",
     "form\x0cfeed", "sep\x1cz", "sep\x1dz", "sep\x1ez", "nel\x85char",
     "line\u2028sep", "para\u2029sep"],
)
def test_invalid_values_rejected_before_mutation(tmp_path: Path, bad_value) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    original = target_of(writer).read_bytes()
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("NEW_KEY", bad_value)
    assert exc.value.code == "VALUE_INVALID"
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", bad_value)
    assert exc.value.code == "VALUE_INVALID"
    assert target_of(writer).read_bytes() == original
    only_global_env(root)


def test_whitespace_and_quote_inputs_prove_reader_divergence(tmp_path: Path) -> None:
    probe = tmp_path / "probe.env"
    probe.write_text("K='v'\nJ=  padded  \n", encoding="utf-8", newline="")
    assert _parse_env_file(probe) == {"K": "v", "J": "padded"}


def test_adversarial_values_round_trip_exactly_through_accepted_reader(tmp_path: Path) -> None:
    adversarial = [
        "a=b",
        "a#b",
        "#lead",
        "a\\b\\",
        'a"b',
        "a'b",
        "quote'in'middle",
        "sp  ace",
        "tab\tinside",
        "unicode-ไทย-ครับ",
        "!@#$%^&*()",
        "semi;colon",
        "trailing.hash#",
    ]
    root = make_drive(tmp_path, "OTHER=1\n")
    allowed = AWikiSecretWriteAuthority([f"ADV_KEY_{i}" for i in range(len(adversarial))])
    writer = AWikiSecretWriter(root, allowed_keys=allowed)
    source = read_source(root)
    for index, value in enumerate(adversarial):
        key = f"ADV_KEY_{index}"
        writer.insert(key, value)
        assert source.resolve_key(key) == value
    assert source.resolve_key("OTHER") == "1"


# ---------------------------------------------------------------------------
# matrix 3/35 — explicit authorized root and exact target surface
# ---------------------------------------------------------------------------


def test_target_is_exactly_secrets_global_env_and_ignores_environment(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path)
    elsewhere = make_drive(tmp_path / "elsewhere")
    monkeypatch.setenv("A_WIKI_DRIVE_PATH", str(elsewhere))
    writer = make_writer(root)
    assert writer.authorized_drive_root == root.resolve()
    assert writer.target_path == root.resolve() / "secrets" / "global.env"
    result = writer.insert("NEW_KEY", CANARY)
    assert result.target == writer.target_path
    assert result.operation == "insert"
    assert result.key == "NEW_KEY"
    assert (elsewhere / "secrets" / "global.env").read_text(encoding="utf-8") == "OTHER=other-value\n"


def test_symlinked_target_components_fail_closed(tmp_path: Path) -> None:
    if not hasattr(os, "symlink"):
        pytest.skip("os.symlink unavailable")
    outside = tmp_path / "outside"
    (outside / "secrets").mkdir(parents=True)
    outside_target = outside / "secrets" / "global.env"
    outside_target.write_text("X=1\n", encoding="utf-8", newline="")

    root = tmp_path / "root"
    (root / "secrets").mkdir(parents=True)
    try:
        (root / "secrets" / "global.env").symlink_to(outside_target)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    writer = make_writer(root)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "TARGET_ESCAPE"
    assert outside_target.read_bytes() == b"X=1\n"

    root2 = tmp_path / "root2"
    root2.mkdir()
    try:
        (root2 / "secrets").symlink_to(outside / "secrets")
    except OSError:
        pytest.skip("symlink privilege unavailable")
    writer2 = make_writer(root2)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer2.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "TARGET_ESCAPE"


def test_missing_secrets_directory_and_missing_target_fail_typed(tmp_path: Path) -> None:
    root = tmp_path / "bare-root"
    root.mkdir()
    writer = make_writer(root)
    for call in (
        lambda: writer.insert("TARGET_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_DIRECTORY_MISSING"
    assert not (root / "secrets").exists()

    (root / "secrets").mkdir()
    for call in (
        lambda: writer.insert("TARGET_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_MISSING"
    assert sorted(path.name for path in (root / "secrets").iterdir()) == []


# ---------------------------------------------------------------------------
# matrix 9/22/91 — malformed and duplicate target content
# ---------------------------------------------------------------------------


def test_malformed_utf8_target_fails_typed_unchanged(tmp_path: Path) -> None:
    raw = b"\xff\xfe# bad\nTARGET_KEY=x\nOTHER=1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    for call in (
        lambda: writer.insert("NEW_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_PARSE_FAILED"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


def test_existing_nul_value_fails_typed_unchanged(tmp_path: Path) -> None:
    raw = b"TARGET_KEY=a\x00b\nOTHER=1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    for call in (
        lambda: writer.insert("NEW_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_PARSE_FAILED"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


def test_duplicate_assignments_fail_closed_despite_last_wins_reader(tmp_path: Path) -> None:
    raw = b"TARGET_KEY=x\nTARGET_KEY=y\nOTHER=1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    assert _parse_env_file(target_of(writer)) == {
        "TARGET_KEY": "y",
        "OTHER": "1",
    }
    for call in (
        lambda: writer.insert("TARGET_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "DUPLICATE_KEY_ASSIGNMENT"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


# ---------------------------------------------------------------------------
# repair cycle 2 (P3) — bare-CR structure must fail closed before mutation
# ---------------------------------------------------------------------------


def test_bare_cr_is_a_line_boundary_to_the_accepted_reader(tmp_path: Path) -> None:
    probe = tmp_path / "probe.env"
    probe.write_bytes(b"TARGET_KEY=old\rSHADOW_KEY=shadow-value\n")
    assert _parse_env_file(probe) == {"TARGET_KEY": "old", "SHADOW_KEY": "shadow-value"}


@pytest.mark.parametrize(
    "raw",
    [
        b"TARGET_KEY=old\rSHADOW_KEY=shadow-value\nOTHER=1\n",
        b"OTHER=1\r",
        b"OTHER=1\r\r\nTARGET_KEY=old\n",
    ],
    ids=["embedded", "trailing", "doubled-before-crlf"],
)
def test_bare_cr_target_structure_fails_closed_before_mutation_preserving_bytes(
    tmp_path: Path, raw: bytes
) -> None:
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    for call in (
        lambda: writer.insert("NEW_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_LINE_BOUNDARY_UNSUPPORTED"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


# ---------------------------------------------------------------------------
# matrix 10/11/92 — comments and export syntax
# ---------------------------------------------------------------------------


def test_comment_lines_containing_assignment_text_are_not_authority(tmp_path: Path) -> None:
    comments = (
        "# TARGET_KEY=old\n"
        "; export TARGET_KEY=x\n"
        "#export TARGET_KEY=y\n"
        "OTHER=1\n"
    )
    root = make_drive(tmp_path, comments)
    writer = make_writer(root)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "KEY_NOT_FOUND"
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.delete("TARGET_KEY")
    assert exc.value.code == "KEY_NOT_FOUND"

    root2 = make_drive(tmp_path / "insert", comments)
    writer2 = make_writer(root2)
    writer2.insert("TARGET_KEY", CANARY)
    assert target_of(writer2).read_bytes() == comments.encode("utf-8") + b"TARGET_KEY=" + CANARY.encode() + b"\n"
    assert read_source(root2).resolve_key("TARGET_KEY") == CANARY
    only_global_env(root2)


def test_export_assignment_surface_is_explicitly_rejected(tmp_path: Path) -> None:
    raw = b"export TARGET_KEY=v\nOTHER=1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    assert _parse_env_file(target_of(writer)) == {"TARGET_KEY": "v", "OTHER": "1"}
    for call in (
        lambda: writer.insert("TARGET_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "EXPORT_SYNTAX_UNSUPPORTED"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


def test_unrelated_export_lines_preserved_verbatim(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "export OTHER=exported\nTARGET_KEY=old\n")
    writer = make_writer(root)
    writer.rotate("TARGET_KEY", CANARY)
    expected = f"export OTHER=exported\nTARGET_KEY={CANARY}\n".encode("utf-8")
    assert target_of(writer).read_bytes() == expected
    assert read_source(root).resolve_key("OTHER") == "exported"


# ---------------------------------------------------------------------------
# matrix 5/6/7/8/88 — byte-exact preservation of unrelated content
# ---------------------------------------------------------------------------


def test_insert_preserves_unrelated_bytes_comments_order_and_newlines(tmp_path: Path) -> None:
    original = (
        "# service secrets\n"
        "\n"
        "OTHER = other-value\r\n"
        "; legacy note TARGET_KEY=old\r\n"
        "export EXPORTED=exported-value\n"
        "9BAD=ignored\n"
        "SPACED = current  \n"
        "\n"
        "no assignment line\n"
        "TRAILING=no-final-newline"
    )
    expected = (
        "# service secrets\n"
        "\n"
        "OTHER = other-value\r\n"
        "; legacy note TARGET_KEY=old\r\n"
        "export EXPORTED=exported-value\n"
        "9BAD=ignored\n"
        "SPACED = current  \n"
        "\n"
        "no assignment line\n"
        "TRAILING=no-final-newline\n"
        f"NEW_KEY={CANARY}\n"
    )
    root = make_drive(tmp_path, original)
    writer = make_writer(root)
    writer.insert("NEW_KEY", CANARY)
    assert target_of(writer).read_bytes() == expected.encode("utf-8")
    source = read_source(root)
    assert source.resolve_key("OTHER") == "other-value"
    assert source.resolve_key("EXPORTED") == "exported-value"
    assert source.resolve_key("SPACED") == "current"
    assert source.resolve_key("TRAILING") == "no-final-newline"
    assert source.resolve_key("NEW_KEY") == CANARY


def test_insert_into_empty_unterminated_and_bom_only_files(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "")
    make_writer(root).insert("NEW_KEY", CANARY)
    assert (root / "secrets" / "global.env").read_bytes() == f"NEW_KEY={CANARY}\n".encode()

    root2 = make_drive(tmp_path / "unterminated", "A=1")
    make_writer(root2).insert("NEW_KEY", CANARY)
    assert (root2 / "secrets" / "global.env").read_bytes() == f"A=1\nNEW_KEY={CANARY}\n".encode()

    root3 = make_drive(tmp_path / "bom-only", b"\xef\xbb\xbf")
    make_writer(root3).insert("NEW_KEY", CANARY)
    assert (root3 / "secrets" / "global.env").read_bytes() == (
        b"\xef\xbb\xbf" + f"NEW_KEY={CANARY}\n".encode()
    )

    root4 = make_drive(tmp_path / "crlf-unterminated", "OTHER=1\r\nTRAIL")
    make_writer(root4).insert("NEW_KEY", CANARY)
    assert (root4 / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\r\nTRAIL\r\nNEW_KEY={CANARY}\r\n".encode()
    )


def test_insert_existing_key_fails_typed_without_rotation(tmp_path: Path) -> None:
    raw = f"TARGET_KEY=current\nOTHER=1\n".encode()
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "KEY_ALREADY_EXISTS"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


def test_rotate_replaces_exactly_one_assignment_line(tmp_path: Path) -> None:
    original = "# header\nSPACED = old-value  \nTAIL=1\n"
    expected = f"# header\nSPACED={CANARY}\nTAIL=1\n"
    root = make_drive(tmp_path, original)
    writer = AWikiSecretWriter(
        root, allowed_keys=AWikiSecretWriteAuthority(("TARGET_KEY", "SPACED", "OTHER_KEY"))
    )
    writer.rotate("SPACED", CANARY)
    assert target_of(writer).read_bytes() == expected.encode("utf-8")
    assert read_source(root).resolve_key("SPACED") == CANARY
    assert read_source(root).resolve_key("TAIL") == "1"

    root_u = make_drive(tmp_path / "unterminated", "OTHER=1\nTARGET_KEY=old")
    AWikiSecretWriter(
        root_u, allowed_keys=AWikiSecretWriteAuthority(("TARGET_KEY",))
    ).rotate("TARGET_KEY", CANARY)
    assert (root_u / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\nTARGET_KEY={CANARY}".encode()
    )


def test_delete_removes_exactly_one_assignment_line(tmp_path: Path) -> None:
    original = "# header\nTARGET_KEY=old\nTAIL=1\n"
    expected = "# header\nTAIL=1\n"
    root = make_drive(tmp_path, original)
    writer = make_writer(root)
    writer.delete("TARGET_KEY")
    assert target_of(writer).read_bytes() == expected.encode("utf-8")

    root_solo = make_drive(tmp_path / "solo", "TARGET_KEY=old\n")
    make_writer(root_solo).delete("TARGET_KEY")
    assert (root_solo / "secrets" / "global.env").read_bytes() == b""

    root_tail = make_drive(tmp_path / "tail", "OTHER=1\nTARGET_KEY=old")
    make_writer(root_tail).delete("TARGET_KEY")
    assert (root_tail / "secrets" / "global.env").read_bytes() == b"OTHER=1\n"


# ---------------------------------------------------------------------------
# matrix 21 — UTF-8 / UTF-8-SIG / newline determinism
# ---------------------------------------------------------------------------


def test_utf8_bom_preserved_across_operations(tmp_path: Path) -> None:
    prefix = b"\xef\xbb\xbf"
    body = "TARGET_KEY=old\nOTHER=1\n"

    root_r = make_drive(tmp_path / "rotate", prefix + body.encode())
    make_writer(root_r).rotate("TARGET_KEY", CANARY)
    target_r = root_r / "secrets" / "global.env"
    assert target_r.read_bytes() == prefix + f"TARGET_KEY={CANARY}\nOTHER=1\n".encode()

    root_i = make_drive(tmp_path / "insert", prefix + body.encode())
    make_writer(root_i).insert("NEW_KEY", CANARY)
    assert (root_i / "secrets" / "global.env").read_bytes() == (
        prefix + f"{body}NEW_KEY={CANARY}\n".encode()
    )

    root_d = make_drive(tmp_path / "delete", prefix + body.encode())
    make_writer(root_d).delete("TARGET_KEY")
    assert (root_d / "secrets" / "global.env").read_bytes() == prefix + b"OTHER=1\n"
    assert read_source(root_r).resolve_key("OTHER") == "1"


def test_crlf_convention_preserved(tmp_path: Path) -> None:
    crlf = "OTHER=1\r\nTARGET_KEY=old\r\n"

    root_r = make_drive(tmp_path / "rotate", crlf)
    make_writer(root_r).rotate("TARGET_KEY", CANARY)
    assert (root_r / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\r\nTARGET_KEY={CANARY}\r\n".encode()
    )

    root_i = make_drive(tmp_path / "insert", crlf)
    make_writer(root_i).insert("NEW_KEY", CANARY)
    assert (root_i / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\r\nTARGET_KEY=old\r\nNEW_KEY={CANARY}\r\n".encode()
    )

    root_d = make_drive(tmp_path / "delete", crlf)
    make_writer(root_d).delete("TARGET_KEY")
    assert (root_d / "secrets" / "global.env").read_bytes() == b"OTHER=1\r\n"


def test_mixed_newlines_use_lf_for_new_lines_deterministically(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "A=1\r\nB=2\n")
    make_writer(root).insert("NEW_KEY", CANARY)
    assert (root / "secrets" / "global.env").read_bytes() == (
        f"A=1\r\nB=2\nNEW_KEY={CANARY}\n".encode()
    )


# ---------------------------------------------------------------------------
# matrix 12/13/14/89/101/102 — atomicity, rollback, orphans, classification
# ---------------------------------------------------------------------------


def test_atomic_write_uses_same_directory_temp_with_fsync_before_replace(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    events: list[str] = []
    real_replace = os.replace
    real_fsync = os.fsync

    def spy_fsync(fd: int) -> None:
        events.append("fsync")
        return real_fsync(fd)

    def spy_replace(src, dst) -> None:
        src_path = Path(src)
        dst_path = Path(dst)
        assert src_path.parent == target.parent
        assert src_path.name.startswith(TEMP_PREFIX)
        assert src_path.name.endswith(".tmp")
        assert src_path != dst_path
        assert CANARY not in src_path.name
        assert "TARGET_KEY" not in src_path.name
        assert CANARY.encode("utf-8") in src_path.read_bytes()
        events.append("replace")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "fsync", spy_fsync)
    monkeypatch.setattr(os, "replace", spy_replace)
    writer.insert("TARGET_KEY", CANARY)
    assert events.index("fsync") < events.index("replace")
    only_global_env(root)


def test_replace_failure_before_effect_leaves_target_intact(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)

    def broken_replace(src, dst) -> None:
        raise OSError("simulated replace failure before effect")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "REPLACE_FAILED"
    assert target_of(writer).read_bytes() == b"OTHER=1\n"
    only_global_env(root)


def test_replace_side_effect_then_raises_rolls_back_verified(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    original = target_of(writer).read_bytes()
    real_replace = os.replace
    calls = {"count": 0}

    def side_effect_then_raise(src, dst) -> None:
        calls["count"] += 1
        real_replace(src, dst)
        if calls["count"] == 1:
            raise OSError("simulated ambiguous mutation")

    monkeypatch.setattr(os, "replace", side_effect_then_raise)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "WRITE_ROLLED_BACK"
    assert target_of(writer).read_bytes() == original
    assert read_source(root).resolve_key("TARGET_KEY") == "old"
    only_global_env(root)


def test_readback_mismatch_after_replacement_restores_original(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    original = target_of(writer).read_bytes()

    def broken_verify(operation: str, key: str, value: str | None) -> None:
        raise RuntimeError("simulated read-back mismatch")

    monkeypatch.setattr(writer, "_verify_after_write", broken_verify)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "WRITE_ROLLED_BACK"
    assert target_of(writer).read_bytes() == original
    assert read_source(root).resolve_key("TARGET_KEY") == "old"
    only_global_env(root)


def test_replace_failure_with_unknown_third_state_requires_recovery(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)

    def chaotic_replace(src, dst) -> None:
        Path(dst).write_bytes(b"THIRD=state\n")
        raise OSError("simulated unknown mutation outcome")

    monkeypatch.setattr(os, "replace", chaotic_replace)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert target_of(writer).read_bytes() == b"THIRD=state\n"
    only_global_env(root)


def test_replace_observation_failure_with_empty_original_requires_recovery(
    monkeypatch, tmp_path: Path
) -> None:
    root = make_drive(tmp_path, "")
    writer = make_writer(root)
    real_read = awiki_secret_writer._read_file_bytes
    reads = {"count": 0}

    def fail_observation(path: Path) -> bytes:
        reads["count"] += 1
        if reads["count"] == 3:
            raise OSError("simulated unreadable ambiguous target")
        return real_read(path)

    def broken_replace(src, dst) -> None:
        raise OSError("simulated replace failure before effect")

    monkeypatch.setattr(awiki_secret_writer, "_read_file_bytes", fail_observation)
    monkeypatch.setattr(os, "replace", broken_replace)

    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)

    assert exc.value.code == "RECOVERY_REQUIRED"
    assert reads["count"] == 3
    only_global_env(root)


def test_replace_observation_failure_with_empty_desired_requires_recovery(
    monkeypatch, tmp_path: Path
) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old")
    writer = make_writer(root)
    real_read = awiki_secret_writer._read_file_bytes
    real_replace = os.replace
    reads = {"count": 0}
    replaces = {"count": 0}

    def fail_observation(path: Path) -> bytes:
        reads["count"] += 1
        if reads["count"] == 3:
            raise OSError("simulated unreadable ambiguous target")
        return real_read(path)

    def side_effect_then_raise(src, dst) -> None:
        replaces["count"] += 1
        real_replace(src, dst)
        if replaces["count"] == 1:
            raise OSError("simulated ambiguous delete replacement")

    monkeypatch.setattr(awiki_secret_writer, "_read_file_bytes", fail_observation)
    monkeypatch.setattr(os, "replace", side_effect_then_raise)

    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.delete("TARGET_KEY")

    assert exc.value.code == "RECOVERY_REQUIRED"
    assert reads["count"] == 3
    assert replaces["count"] == 1
    only_global_env(root)


def test_rollback_failure_requires_recovery(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\n")
    writer = make_writer(root)
    calls = {"count": 0}
    real_replace = os.replace

    def flaky_replace(src, dst) -> None:
        calls["count"] += 1
        if calls["count"] == 1:
            real_replace(src, dst)
            raise OSError("side effect then raise")
        raise OSError("rollback replace failed")

    monkeypatch.setattr(os, "replace", flaky_replace)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "RECOVERY_REQUIRED"
    only_global_env(root)


def chmod_failing_for_rollback_temp(real_chmod):
    def fake_chmod(path, mode) -> None:
        if Path(path).name.startswith(awiki_secret_writer._ROLLBACK_PREFIX):
            raise OSError("simulated rollback mode restoration failure")
        return real_chmod(path, mode)

    return fake_chmod


def test_rollback_mode_restoration_failure_restores_bytes_then_requires_recovery(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    original = target.read_bytes()

    def broken_verify(operation: str, key: str, value: str | None) -> None:
        raise RuntimeError("simulated read-back mismatch")

    monkeypatch.setattr(writer, "_verify_after_write", broken_verify)
    monkeypatch.setattr(os, "chmod", chmod_failing_for_rollback_temp(os.chmod))
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert target.read_bytes() == original
    assert read_source(root).resolve_key("TARGET_KEY") == "old"
    only_global_env(root)


def test_ambiguous_replace_rollback_mode_restoration_failure_requires_recovery(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    original = target.read_bytes()
    real_replace = os.replace
    calls = {"count": 0}

    def side_effect_then_raise(src, dst) -> None:
        calls["count"] += 1
        real_replace(src, dst)
        if calls["count"] == 1:
            raise OSError("simulated ambiguous mutation")

    monkeypatch.setattr(os, "replace", side_effect_then_raise)
    monkeypatch.setattr(os, "chmod", chmod_failing_for_rollback_temp(os.chmod))
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert target.read_bytes() == original
    assert read_source(root).resolve_key("TARGET_KEY") == "old"
    only_global_env(root)


def test_no_orphan_writer_temp_or_backup_artifacts_after_failure_battery(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    outcomes = []

    def snapshot_names() -> list[str]:
        return sorted(path.name for path in (root / "secrets").iterdir())

    with pytest.raises(AWikiSecretWriteError):
        writer.rotate("TARGET_KEY", "pad-not-allowed ")
    outcomes.append(snapshot_names())
    with pytest.raises(AWikiSecretWriteError):
        writer.delete("OTHER_KEY")
    outcomes.append(snapshot_names())
    with pytest.raises(AWikiSecretWriteError):
        writer.insert("TARGET_KEY", CANARY)
    outcomes.append(snapshot_names())

    real_replace = os.replace

    def broken_replace(src, dst) -> None:
        raise OSError("simulated replace failure before effect")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "REPLACE_FAILED"
    outcomes.append(snapshot_names())
    monkeypatch.setattr(os, "replace", real_replace)

    def broken_verify(operation: str, key: str, value: str | None) -> None:
        raise RuntimeError("simulated read-back mismatch")

    monkeypatch.setattr(writer, "_verify_after_write", broken_verify)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "WRITE_ROLLED_BACK"
    outcomes.append(snapshot_names())

    for names in outcomes:
        assert names == ["global.env"]


# ---------------------------------------------------------------------------
# repair cycle 2 (P2) — owned secret-bearing temp removal on replace failure
# ---------------------------------------------------------------------------


def scan_secrets_for_canary(root: Path) -> None:
    for path in (root / "secrets").iterdir():
        assert CANARY.encode() not in path.read_bytes()


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only replace semantics")
def test_readonly_target_replace_failure_still_removes_owned_readonly_temp(tmp_path: Path) -> None:
    raw = b"TARGET_KEY=old\nOTHER=fixture-secret-1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    target = target_of(writer)
    os.chmod(target, stat.S_IREAD)
    try:
        with pytest.raises(AWikiSecretWriteError) as exc:
            writer.rotate("TARGET_KEY", CANARY)
        assert exc.value.code == "REPLACE_FAILED"
        assert target.read_bytes() == raw
        only_global_env(root)
        scan_secrets_for_canary(root)
    finally:
        os.chmod(target, stat.S_IWRITE)


def test_owned_readonly_temp_cleanup_never_touches_unrelated_files(monkeypatch, tmp_path: Path) -> None:
    raw = b"TARGET_KEY=old\nOTHER=fixture-secret-1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    target = target_of(writer)
    unrelated = root / "secrets" / "unrelated-readonly.txt"
    unrelated.write_bytes(b"unrelated-bytes")
    os.chmod(unrelated, stat.S_IREAD)
    os.chmod(target, stat.S_IREAD)
    try:
        def broken_replace(src, dst) -> None:
            raise OSError("simulated replace failure before effect")

        monkeypatch.setattr(os, "replace", broken_replace)
        with pytest.raises(AWikiSecretWriteError) as exc:
            writer.rotate("TARGET_KEY", CANARY)
        assert exc.value.code == "REPLACE_FAILED"
        assert target.read_bytes() == raw
        assert sorted(path.name for path in (root / "secrets").iterdir()) == [
            "global.env",
            "unrelated-readonly.txt",
        ]
        assert unrelated.read_bytes() == b"unrelated-bytes"
        assert (os.stat(unrelated).st_mode & stat.S_IWRITE) == 0
        scan_secrets_for_canary(root)
    finally:
        os.chmod(unrelated, stat.S_IWRITE)
        os.chmod(target, stat.S_IWRITE)


def test_unremovable_owned_temp_fails_typed_after_bounded_attempts(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\n")
    writer = make_writer(root)
    real_unlink = Path.unlink
    unlink_calls = {"count": 0}

    def locked_owned_temp_unlink(self, missing_ok: bool = False) -> None:
        if self.name.startswith(TEMP_PREFIX) and self.name.endswith(".tmp"):
            unlink_calls["count"] += 1
            raise PermissionError("simulated locked owned temp")
        return real_unlink(self, missing_ok=missing_ok)

    def broken_replace(src, dst) -> None:
        raise OSError("simulated replace failure before effect")

    monkeypatch.setattr(Path, "unlink", locked_owned_temp_unlink)
    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("TARGET_KEY", CANARY)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert unlink_calls["count"] == 2
    names = sorted(path.name for path in (root / "secrets").iterdir())
    assert len(names) == 2
    assert "global.env" in names
    owned_temps = [name for name in names if name != "global.env"]
    assert len(owned_temps) == 1
    assert owned_temps[0].startswith(TEMP_PREFIX) and owned_temps[0].endswith(".tmp")
    monkeypatch.undo()
    (root / "secrets" / owned_temps[0]).unlink()


# ---------------------------------------------------------------------------
# matrix 98/99/101 — concurrency and ambiguous-mutation safety
# ---------------------------------------------------------------------------


def test_source_drift_before_replace_refuses_and_preserves_concurrent_edit(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    drifted = b"OTHER=1\n# concurrent unrelated edit\n"
    concurrent_edit_then_temp(monkeypatch, drifted)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "TARGET_DRIFTED"
    assert target_of(writer).read_bytes() == drifted
    only_global_env(root)


def test_same_bytes_replacement_before_replace_is_identity_drift(
    monkeypatch, tmp_path: Path
) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    original = target.read_bytes()
    real_write_temp = awiki_secret_writer._write_owned_temp
    real_replace = os.replace

    def replace_target_with_identical_file(
        directory: Path, data: bytes, mode: int
    ) -> Path:
        concurrent = directory / ".concurrent-identical-replacement.tmp"
        concurrent.write_bytes(original)
        os.chmod(concurrent, stat.S_IMODE(mode))
        real_replace(concurrent, target)
        return real_write_temp(directory, data, mode)

    monkeypatch.setattr(
        awiki_secret_writer, "_write_owned_temp", replace_target_with_identical_file
    )

    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)

    assert exc.value.code == "TARGET_DRIFTED"
    assert target.read_bytes() == original
    only_global_env(root)


def test_drift_fence_applies_to_rotate_and_delete(monkeypatch, tmp_path: Path) -> None:
    original = b"TARGET_KEY=old\n"
    drifted = b"TARGET_KEY=old\n# concurrent\n"
    for operation, invoke in (
        ("rotate", lambda w: w.rotate("TARGET_KEY", CANARY)),
        ("delete", lambda w: w.delete("TARGET_KEY")),
    ):
        root = make_drive(tmp_path / operation, original)
        writer = make_writer(root)
        concurrent_edit_then_temp(monkeypatch, drifted)
        with pytest.raises(AWikiSecretWriteError) as exc:
            invoke(writer)
        assert exc.value.code == "TARGET_DRIFTED"
        assert target_of(writer).read_bytes() == drifted
        only_global_env(root)


# ---------------------------------------------------------------------------
# matrix 15/16/27 — verified read-back through the accepted source
# ---------------------------------------------------------------------------


def test_insert_and_rotate_verify_through_accepted_source(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    source = read_source(root)
    writer.insert("NEW_KEY", CANARY)
    assert source.resolve_key("NEW_KEY") == CANARY
    assert source.resolve_key("TARGET_KEY") == "old"
    writer.rotate("TARGET_KEY", "rotated-value")
    assert source.resolve_key("TARGET_KEY") == "rotated-value"
    assert source.resolve_key("OTHER") == "1"


def test_delete_readback_proves_key_absence(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=old\nOTHER=1\n")
    writer = make_writer(root)
    writer.delete("TARGET_KEY")
    source = read_source(root)
    with pytest.raises(AWikiEnvironmentResolutionError) as exc:
        source.resolve_key("TARGET_KEY")
    assert exc.value.code == "SECRET_REFERENCE_NOT_FOUND"
    assert source.resolve_key("OTHER") == "1"


def test_written_secret_resolves_through_opaque_awiki_env_reference(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    make_writer(root).insert("TARGET_KEY", CANARY)

    class EmptyEndpointReader:
        def get_endpoint(self, reference: str):
            return None

    resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=EmptyEndpointReader(),
        secret_source=AWikiDriveEnvironmentSource(root),
    )
    assert resolver.resolve("secret-ref:awiki-env/TARGET_KEY") == CANARY


# ---------------------------------------------------------------------------
# matrix 17/26 — redacted surfaces and stable codes
# ---------------------------------------------------------------------------


def test_error_and_result_surfaces_never_contain_raw_value(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "TARGET_KEY=current\nOTHER=1\n")
    writer = make_writer(root)
    surfaces: list[str] = []

    result = writer.rotate("TARGET_KEY", CANARY)
    surfaces.extend([str(result), repr(result), result.operation, result.key])

    failure_cases = [
        lambda: writer.insert("TARGET_KEY", CANARY),
        lambda: writer.rotate("OTHER_KEY", CANARY),
        lambda: writer.insert("NEW_KEY", " padded-canary "),
        lambda: writer.insert("NEW_KEY", f"'{CANARY}'"),
        lambda: writer.delete("OTHER_KEY"),
    ]
    for case in failure_cases:
        with pytest.raises(AWikiSecretWriteError) as exc:
            case()
        surfaces.extend([str(exc.value), repr(exc.value), exc.value.code, str(exc.value.args)])
        assert CODE_SHAPE.fullmatch(exc.value.code) is not None

    assert not hasattr(awiki_secret_writer, "logging")
    for surface in surfaces:
        assert CANARY not in surface
        assert "padded-canary" not in surface


# ---------------------------------------------------------------------------
# matrix 18/19/20 — no child process, network, provider store, or DB coupling
# ---------------------------------------------------------------------------


def test_no_subprocess_shell_or_network_calls(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)

    def explode(*args, **kwargs):
        raise AssertionError("forbidden surface called")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    monkeypatch.setattr(subprocess, "check_call", explode)
    monkeypatch.setattr(subprocess, "check_output", explode)
    monkeypatch.setattr(os, "system", explode)
    monkeypatch.setattr(os, "popen", explode)
    monkeypatch.setattr(socket, "socket", explode)
    monkeypatch.setattr(socket, "create_connection", explode)
    writer.insert("TARGET_KEY", CANARY)
    writer.rotate("TARGET_KEY", "rotated")
    writer.delete("TARGET_KEY")


def test_no_writes_outside_target_and_no_new_files(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    before = tree_state(tmp_path)
    writer.insert("NEW_KEY", "v1")
    writer.rotate("NEW_KEY", "v2")
    middle = tree_state(tmp_path)
    changed = {key for key in set(before) | set(middle) if before.get(key) != middle.get(key)}
    assert changed == {"A-Wiki-Data/secrets/global.env"}
    writer.delete("NEW_KEY")
    assert tree_state(tmp_path) == before


def test_module_avoids_provider_db_subprocess_and_logging_imports() -> None:
    source = Path(awiki_secret_writer.__file__).read_text(encoding="utf-8")
    allowed = {
        "__future__",
        "os",
        "re",
        "stat",
        "tempfile",
        "dataclasses",
        "pathlib",
        "typing",
        ".awiki_environment_resolver",
    }
    for line in source.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("import ") or stripped.startswith("from ")):
            continue
        module = stripped.split()[1]
        assert module in allowed, stripped


# ---------------------------------------------------------------------------
# matrix 24/90 — permissions / inspection fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits")
def test_existing_target_mode_preserved(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)
    os.chmod(target, 0o640)
    writer.insert("TARGET_KEY", CANARY)
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o640


def test_security_inspection_failure_fails_closed(monkeypatch, tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)

    def broken_mode(path: Path) -> int:
        raise OSError("inspection unavailable")

    monkeypatch.setattr(awiki_secret_writer, "_target_mode", broken_mode)
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("TARGET_KEY", CANARY)
    assert exc.value.code == "TARGET_INSPECTION_FAILED"
    assert target_of(writer).read_bytes() == b"OTHER=1\n"
    only_global_env(root)


# ---------------------------------------------------------------------------
# matrix 25 — deterministic repeated semantics, no hidden upsert
# ---------------------------------------------------------------------------


def test_repeated_operation_semantics_are_explicit_without_hidden_upsert(tmp_path: Path) -> None:
    root = make_drive(tmp_path, "OTHER=1\n")
    writer = make_writer(root)
    target = target_of(writer)

    writer.insert("NEW_KEY", "v1")
    assert b"NEW_KEY=v1\n" in target.read_bytes()
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.insert("NEW_KEY", "v2")
    assert exc.value.code == "KEY_ALREADY_EXISTS"
    assert b"NEW_KEY=v1\n" in target.read_bytes()

    writer.rotate("NEW_KEY", "v2")
    assert read_source(root).resolve_key("NEW_KEY") == "v2"
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.rotate("OTHER_KEY", "v3")
    assert exc.value.code == "KEY_NOT_FOUND"

    writer.delete("NEW_KEY")
    with pytest.raises(AWikiSecretWriteError) as exc:
        writer.delete("NEW_KEY")
    assert exc.value.code == "KEY_NOT_FOUND"
    writer.insert("NEW_KEY", "v3")
    assert read_source(root).resolve_key("NEW_KEY") == "v3"


# ---------------------------------------------------------------------------
# mirror proof — writer line classification equals accepted reader semantics
# ---------------------------------------------------------------------------


def test_line_classification_matches_accepted_reader_line_semantics(tmp_path: Path) -> None:
    corpus = [
        "K=v",
        "K = v",
        "  K=v  ",
        "#K=v",
        "; K=v",
        "# K=v",
        "export K=v",
        "export  K=v",
        "export\tK=v",
        "exportK=v",
        "9K=v",
        "K-v=x",
        "K=",
        "K==v",
        "=v",
        "K v=x",
        "Kv",
        " K = 'q' ",
        "\tK=v",
        "export =v",
        "K=v#w",
        "OTHER_K=1",
        "K='quoted'",
        'K="dq"',
    ]
    for index, line in enumerate(corpus):
        probe = tmp_path / f"probe-{index}.env"
        probe.write_bytes((line + "\n").encode("utf-8"))
        projected = _parse_env_file(probe)
        owner, _is_export = awiki_secret_writer._classify_line(line)
        if owner is None:
            assert projected == {}, (line, projected)
        else:
            assert list(projected) == [owner], (line, projected)
        probe.unlink()


# ---------------------------------------------------------------------------
# repair cycle 2 — Windows read-only orphan + reader-only line boundaries
# ---------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only attribute semantics")
def test_windows_readonly_target_replace_fails_typed_without_orphan(tmp_path: Path) -> None:
    """Real Windows reproducer: a 0444/read-only target must yield the typed
    REPLACE_FAILED with original bytes intact and NO orphaned secret-bearing
    temp in secrets/ (owned-temp cleanup must clear the read-only bit on the
    exact owned temp and delete it)."""
    raw = b"TARGET_KEY=old\nOTHER=1\n"
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    target = target_of(writer)
    os.chmod(target, 0o444)
    try:
        for invoke, code in (
            (lambda: writer.insert("NEW_KEY", CANARY), "REPLACE_FAILED"),
            (lambda: writer.rotate("TARGET_KEY", CANARY), "REPLACE_FAILED"),
            (lambda: writer.delete("TARGET_KEY"), "REPLACE_FAILED"),
        ):
            with pytest.raises(AWikiSecretWriteError) as exc:
                invoke()
            assert exc.value.code == code
            assert target.read_bytes() == raw
            only_global_env(root)
    finally:
        os.chmod(target, 0o644)


@pytest.mark.skipif(os.name != "nt", reason="Windows read-only attribute semantics")
def test_windows_owned_readonly_temp_cleanup_clears_bit_and_unlinks(tmp_path: Path) -> None:
    fd, name = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix=".tmp", dir=str(tmp_path))
    os.close(fd)
    owned = Path(name)
    owned.write_bytes(b"synthetic-secret-bearing-bytes")
    os.chmod(owned, 0o444)
    awiki_secret_writer._cleanup_owned_temp(owned)
    assert not owned.exists()


def test_unprovable_owned_temp_cleanup_requires_recovery(monkeypatch, tmp_path: Path) -> None:
    fd, name = tempfile.mkstemp(prefix=TEMP_PREFIX, suffix=".tmp", dir=str(tmp_path))
    os.close(fd)
    owned = Path(name)
    owned.write_bytes(b"synthetic-secret-bearing-bytes")

    def unlink_denied(self, missing_ok: bool = False) -> None:
        raise PermissionError("simulated unlink denial")

    def chmod_denied(path, mode) -> None:
        raise PermissionError("simulated chmod denial")

    monkeypatch.setattr(Path, "unlink", unlink_denied)
    monkeypatch.setattr(os, "chmod", chmod_denied)
    with pytest.raises(AWikiSecretWriteError) as exc:
        awiki_secret_writer._cleanup_owned_temp(owned)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert owned.read_bytes() == b"synthetic-secret-bearing-bytes"

    monkeypatch.setattr(os, "chmod", lambda path, mode: None)
    with pytest.raises(AWikiSecretWriteError) as exc:
        awiki_secret_writer._cleanup_owned_temp(owned)
    assert exc.value.code == "RECOVERY_REQUIRED"

    monkeypatch.undo()
    owned.unlink()

    unrelated = tmp_path / "unrelated-file.txt"
    unrelated.write_bytes(b"keep-me")
    chmod_calls: list[str] = []

    def recording_chmod(path, mode) -> None:
        chmod_calls.append(str(path))
        return None

    monkeypatch.setattr(os, "chmod", recording_chmod)
    with pytest.raises(AWikiSecretWriteError) as exc:
        awiki_secret_writer._cleanup_owned_temp(unrelated)
    assert exc.value.code == "RECOVERY_REQUIRED"
    assert chmod_calls == []
    assert unrelated.read_bytes() == b"keep-me"


@pytest.mark.parametrize(
    "raw",
    [
        b"OTHER=1\nTARGET_KEY=old\rplain trailing bytes\n",
        b"OTHER=1\nTARGET_KEY=old\r",
        b"OTHER=1\nTARGET_KEY=old\x0btrailing junk\n",
        "OTHER=1\nTARGET_KEY=old\x85trailing junk\n".encode("utf-8"),
        "OTHER=1\nTARGET_KEY=old\u2028trailing junk\n".encode("utf-8"),
        b"OTHER=1\x0bnon-assignment tail\nTARGET_KEY=old\n",
    ],
)
def test_reader_only_line_boundaries_rejected_fail_closed_before_mutation(
    tmp_path: Path, raw: bytes
) -> None:
    """The accepted reader splits lines on bare CR and other str.splitlines
    boundaries the writer's unit model does not represent; rotating/deleting
    such a unit would silently drop unrelated bytes. All operations must
    reject the target typed before mutation instead of rewriting ambiguous
    bytes."""
    root = make_drive(tmp_path, raw)
    writer = make_writer(root)
    for call in (
        lambda: writer.insert("NEW_KEY", CANARY),
        lambda: writer.rotate("TARGET_KEY", CANARY),
        lambda: writer.delete("TARGET_KEY"),
    ):
        with pytest.raises(AWikiSecretWriteError) as exc:
            call()
        assert exc.value.code == "TARGET_LINE_BOUNDARY_UNSUPPORTED"
    assert target_of(writer).read_bytes() == raw
    only_global_env(root)


def test_crlf_and_lf_line_boundaries_remain_accepted(tmp_path: Path) -> None:
    crlf_root = make_drive(tmp_path / "crlf", "OTHER=1\r\nTARGET_KEY=old\r\n")
    make_writer(crlf_root).rotate("TARGET_KEY", CANARY)
    assert (crlf_root / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\r\nTARGET_KEY={CANARY}\r\n".encode()
    )
    lf_root = make_drive(tmp_path / "lf", "OTHER=1\nTARGET_KEY=old\n")
    make_writer(lf_root).rotate("TARGET_KEY", CANARY)
    assert (lf_root / "secrets" / "global.env").read_bytes() == (
        f"OTHER=1\nTARGET_KEY={CANARY}\n".encode()
    )
