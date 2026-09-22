from __future__ import annotations

import ast
import hmac as hmac_stdlib
import importlib
import inspect
import re
from hashlib import sha256
from pathlib import Path

import pytest

from a_conductor.origin_provenance import (
    ORIGIN_REF_DOMAIN,
    ORIGIN_SURFACES,
    OriginProvenanceError,
    derive_origin_chat_session_ref,
    parse_origin_chat_session_ref,
    validate_origin_chat_session_ref,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE = ROOT / "src" / "a_conductor" / "origin_provenance.py"

FAKE_KEY = bytes(range(32))
FAKE_KEY_ALT = bytes(range(32, 64))
RAW_REF = "fake-raw-chat-session-77"
FAKE_SHARE_URL = "https://chat.example/" + "FAKE/share/0000"
FAKE_BEARER = "Bearer " + "FAKE" + "0" * 27
FAKE_SK = "sk-" + "FAKE" + "0" * 36

KAT_KEY = b"msp1-kat-fake-key-00000000000000"
KAT_KEY_VERSION = "kv1"
KAT_SURFACE = "srm"
KAT_RAW_REF = "kat-frozen-raw-session-ref-482"
# Frozen 2026-09-22 from an independently computed HMAC-SHA256 over the
# documented construction "a-conductor/msp1/origin-chat-session-v1" \0 "kv1"
# \0 "srm" \0 "kat-frozen-raw-session-ref-482" (UTF-8, NUL-separated) keyed
# by KAT_KEY. The literal freezes the exact byte construction; it must never
# be recomputed from production logic inside this file.
KAT_REF = (
    "origin-chat-v1:kv1:"
    "865ceea78246446f2f68a7f64850100e1b2e49143fbc7a345a38f6b7f5a70383"
)

REF_GRAMMAR = re.compile(
    r"origin-chat-v1:[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?:[0-9a-f]{64}"
)
SESSION_REF_CODE = "ORIGIN_PROVENANCE_SESSION_REF_INVALID"
SURFACE_CODE = "ORIGIN_PROVENANCE_SURFACE_UNSUPPORTED"


def derive(
    key: bytes = FAKE_KEY,
    *,
    key_version: str = "v1",
    origin_surface: str = "kilo",
    raw_session_ref: str = RAW_REF,
) -> str:
    return derive_origin_chat_session_ref(
        key,
        key_version=key_version,
        origin_surface=origin_surface,
        raw_session_ref=raw_session_ref,
    )


def test_derive_is_deterministic_and_exact_grammar() -> None:
    first = derive()
    second = derive()
    assert first == second
    assert REF_GRAMMAR.fullmatch(first) is not None
    prefix, key_version, digest = first.split(":")
    assert prefix == "origin-chat-v1"
    assert key_version == "v1"
    assert len(digest) == 64
    assert digest == digest.lower()
    assert set(digest) <= set("0123456789abcdef")


def test_known_answer_freezes_exact_derivation_construction() -> None:
    ref = derive(
        KAT_KEY,
        key_version=KAT_KEY_VERSION,
        origin_surface=KAT_SURFACE,
        raw_session_ref=KAT_RAW_REF,
    )
    assert ref == KAT_REF


def test_kat_literal_anchors_every_component_and_grammar() -> None:
    assert validate_origin_chat_session_ref(KAT_REF) is True
    assert parse_origin_chat_session_ref(KAT_REF) == (
        KAT_KEY_VERSION,
        KAT_REF.split(":")[2],
    )
    base = {
        "key": KAT_KEY,
        "key_version": KAT_KEY_VERSION,
        "origin_surface": KAT_SURFACE,
        "raw_session_ref": KAT_RAW_REF,
    }
    for field, value in (
        ("key", FAKE_KEY),
        ("key_version", "v1"),
        ("origin_surface", "kilo"),
        ("raw_session_ref", KAT_RAW_REF + "-x"),
    ):
        perturbed = dict(base)
        perturbed[field] = value
        assert derive(**perturbed) != KAT_REF


@pytest.mark.parametrize(
    "other_kwargs",
    [
        {"key": FAKE_KEY_ALT},
        {"key_version": "v2"},
        {"origin_surface": "rdc"},
    ],
)
def test_key_version_or_surface_change_changes_ref(other_kwargs: dict) -> None:
    base = derive()
    kwargs: dict = {
        "key": FAKE_KEY,
        "key_version": "v1",
        "origin_surface": "kilo",
    }
    kwargs.update(other_kwargs)
    assert derive(**kwargs) != base


def test_domain_separation_differs_from_undomained_hmac() -> None:
    ref = derive()
    undomained = hmac_stdlib.new(
        FAKE_KEY, RAW_REF.encode("utf-8"), sha256
    ).hexdigest()
    assert undomained not in ref
    assert ORIGIN_REF_DOMAIN == "a-conductor/msp1/origin-chat-session-v1"


def test_nfc_equivalent_raw_inputs_derive_same_ref() -> None:
    decomposed = "fake-chat-cafe\u0301-01"
    composed = "fake-chat-caf\u00e9-01"
    assert derive(raw_session_ref=decomposed) == derive(raw_session_ref=composed)


def test_nfc_shortening_within_length_cap_is_accepted() -> None:
    padded = "e\u0301" * 128
    assert len(padded) == 256
    assert REF_GRAMMAR.fullmatch(derive(raw_session_ref=padded)) is not None


@pytest.mark.parametrize(
    "bad_raw",
    [
        "",
        " ",
        "\t",
        "\n",
        "  fake-session-1  ",
        "fake-session-1 ",
        " fake-session-1",
        "\u00a0fake-session-1",
        "fake-session-1\u00a0",
        "fake-session-1\ntrailing",
        "fake\x00session",
        "fake\x7fsession",
        "fake-session\u200bzero-width",
        "fake\u2028session",
        "fake\u2029session",
        "fake\ue000private-use",
        "fake\u0378unassigned",
        "fake\ud800surrogate",
        "fake\udffflow-surrogate",
        "x" * 257,
        None,
        42,
        b"fake-session-1",
    ],
)
def test_invalid_raw_session_ref_fails_typed_without_echo(bad_raw: object) -> None:
    with pytest.raises(OriginProvenanceError) as exc_info:
        derive(raw_session_ref=bad_raw)  # type: ignore[arg-type]
    assert exc_info.value.code == SESSION_REF_CODE
    assert str(exc_info.value) == SESSION_REF_CODE


def test_raw_input_at_length_cap_boundary_accepted() -> None:
    assert REF_GRAMMAR.fullmatch(derive(raw_session_ref="x" * 256)) is not None


@pytest.mark.parametrize(
    "bad_key",
    [
        b"",
        b"short",
        b"x" * 31,
        "fake-key-not-bytes",
        bytearray(b"x" * 32),
        42,
        None,
    ],
)
def test_weak_or_wrong_type_key_fails_typed(bad_key: object) -> None:
    with pytest.raises(OriginProvenanceError) as exc_info:
        derive(key=bad_key)  # type: ignore[arg-type]
    assert exc_info.value.code == "ORIGIN_PROVENANCE_KEY_INVALID"


def test_minimum_strength_key_bytes_accepted() -> None:
    assert REF_GRAMMAR.fullmatch(derive(key=b"f" * 32)) is not None


@pytest.mark.parametrize(
    "bad_version",
    [
        "",
        "V1",
        "-v1",
        "v1-",
        "v1_0",
        "v.1",
        "v 1",
        "chatgpt/v1",
        "a" * 33,
        42,
        None,
    ],
)
def test_malformed_key_version_fails_typed(bad_version: object) -> None:
    with pytest.raises(OriginProvenanceError) as exc_info:
        derive(key_version=bad_version)  # type: ignore[arg-type]
    assert exc_info.value.code == "ORIGIN_PROVENANCE_KEY_VERSION_INVALID"


@pytest.mark.parametrize("version", ["v1", "k1", "2026-09", "a" * 32])
def test_accepted_key_version_grammar_derives(version: str) -> None:
    ref = derive(key_version=version)
    assert REF_GRAMMAR.fullmatch(ref) is not None
    assert ref.split(":")[1] == version


@pytest.mark.parametrize(
    "bad_surface",
    ["chatgpt", "slack", "ChatGPT", "", "claude code", "chatgpt/", 42, None],
)
def test_unknown_origin_surface_fails_typed(bad_surface: object) -> None:
    with pytest.raises(OriginProvenanceError) as exc_info:
        derive(origin_surface=bad_surface)  # type: ignore[arg-type]
    assert exc_info.value.code == SURFACE_CODE


@pytest.mark.parametrize("surface", sorted(ORIGIN_SURFACES))
def test_accepted_origin_surfaces_derive(surface: str) -> None:
    assert REF_GRAMMAR.fullmatch(derive(origin_surface=surface)) is not None


def test_raw_identifier_never_appears_in_output_or_error_text() -> None:
    raw = "RAWFAKESESSIONXYZ9999"
    ref = derive(raw_session_ref=raw)
    assert raw not in ref
    for bad in (" " + raw, raw + "\n", "x" * 257 + raw, raw + "\x00"):
        with pytest.raises(OriginProvenanceError) as exc_info:
            derive(raw_session_ref=bad)
        assert raw not in str(exc_info.value)
        assert raw not in repr(exc_info.value)
        assert raw not in exc_info.value.code


def test_rotation_refs_differ_and_old_refs_validate_without_key() -> None:
    old_ref = derive(key=FAKE_KEY, key_version="v1")
    new_ref = derive(key=FAKE_KEY_ALT, key_version="v2")
    assert old_ref != new_ref
    assert validate_origin_chat_session_ref(old_ref) is True
    assert validate_origin_chat_session_ref(new_ref) is True


@pytest.mark.parametrize(
    "bad_value",
    [
        "",
        "session-abc-123",
        FAKE_SHARE_URL,
        FAKE_BEARER,
        FAKE_SK,
        "hk-0123456789abcdef0123456789abcdef",
        "origin-chat-v1:v1:0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF0123456789ABCDEF",
        "origin-chat-v1:v1:" + "0" * 63,
        "origin-chat-v1:v1:" + "0" * 65,
        "origin-chat-v2:v1:" + "0" * 64,
        "origin-chat-v1:V1:" + "0" * 64,
        "origin-chat-v1:v1:" + "g" * 64,
        " origin-chat-v1:v1:" + "0" * 64,
        "origin-chat-v1:v1:" + "0" * 64 + "\n",
        "origin-chat-v1:v1",
        42,
        None,
        b"origin-chat-v1:v1:" + b"0" * 64,
    ],
)
def test_validator_accepts_only_exact_derived_grammar(bad_value: object) -> None:
    assert validate_origin_chat_session_ref(bad_value) is False  # type: ignore[arg-type]


def test_validator_accepts_freshly_derived_ref() -> None:
    assert validate_origin_chat_session_ref(derive()) is True


def test_error_is_typed_with_code_only() -> None:
    error = OriginProvenanceError("ORIGIN_PROVENANCE_TEST")
    assert isinstance(error, ValueError)
    assert error.code == "ORIGIN_PROVENANCE_TEST"
    assert str(error) == "ORIGIN_PROVENANCE_TEST"


def test_module_public_surface_is_exactly_documented_api() -> None:
    import types

    module = importlib.import_module("a_conductor.origin_provenance")
    public_non_module = {
        name
        for name in dir(module)
        if not name.startswith("_")
        and not isinstance(getattr(module, name), types.ModuleType)
        and name != "annotations"
    }
    assert public_non_module == set(module.__all__)
    assert set(module.__all__) == {
        "ORIGIN_REF_DOMAIN",
        "ORIGIN_REF_PREFIX",
        "ORIGIN_REF_PATTERN",
        "ORIGIN_SURFACES",
        "OriginProvenanceError",
        "derive_origin_chat_session_ref",
        "parse_origin_chat_session_ref",
        "validate_origin_chat_session_ref",
    }


def test_parse_exposes_only_grammar_components_and_takes_no_key() -> None:
    ref = derive()
    parsed = parse_origin_chat_session_ref(ref)
    assert parsed == ("v1", ref.split(":")[2])
    assert parse_origin_chat_session_ref("not-a-derived-ref") is None
    parameters = inspect.signature(parse_origin_chat_session_ref).parameters
    assert "key" not in parameters
    assert "raw" not in parameters


def test_no_reverse_or_authority_api_names_exist() -> None:
    import types

    module = importlib.import_module("a_conductor.origin_provenance")
    forbidden = re.compile(
        r"reverse|lookup|identify|reidentif|resolve|decode|recover|migrat"
        r"|grant|lease|claim|admit|dispatch|schedule|retry|review|complet"
        r"|writer|mutat|authoriz|rotate_",
        re.IGNORECASE,
    )
    for name in dir(module):
        if name.startswith("_"):
            continue
        if isinstance(getattr(module, name), types.ModuleType):
            continue
        assert forbidden.search(name) is None, name


def test_import_surface_is_pure_stdlib_subset() -> None:
    source = MODULE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"__future__", "hmac", "hashlib", "re", "unicodedata"}


def test_source_has_no_store_process_network_or_authority_tokens() -> None:
    source = MODULE_SOURCE.read_text(encoding="utf-8")
    for token in (
        "sqlite",
        "subprocess",
        "socket",
        "threading",
        "asyncio",
        "multiprocessing",
        "concurrent",
        "pathlib",
        "tempfile",
        "shutil",
        "pickle",
        "marshal",
        "ctypes",
        "winreg",
        "os.",
        "sys.",
        "open(",
        "exec(",
        "eval(",
        "__import__",
        "WorkerLease",
        "ClaimStore",
        "LeaseStore",
        "Scheduler",
        "scheduler",
        "registry",
    ):
        assert token not in source, token
