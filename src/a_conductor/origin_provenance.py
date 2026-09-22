"""Pure privacy-preserving origin/session provenance references (WO-P1-482).

Derives opaque, versioned, domain-separated HMAC-SHA256 references that stand
in for raw chat/session origin identifiers. Raw origin input never appears in
derived output or in error text. The helper receives key material strictly by
injection, performs no secret retrieval, and adds no persistence, process,
network, or execution authority of any kind.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata

__all__ = [
    "ORIGIN_REF_DOMAIN",
    "ORIGIN_REF_PREFIX",
    "ORIGIN_REF_PATTERN",
    "ORIGIN_SURFACES",
    "OriginProvenanceError",
    "derive_origin_chat_session_ref",
    "parse_origin_chat_session_ref",
    "validate_origin_chat_session_ref",
]

ORIGIN_REF_DOMAIN = "a-conductor/msp1/origin-chat-session-v1"
ORIGIN_REF_PREFIX = "origin-chat-v1"

ORIGIN_SURFACES = frozenset({"a-conductor", "srm", "claude-code", "kilo", "rdc"})

_KEY_VERSION = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?")
ORIGIN_REF_PATTERN = re.compile(
    rf"{ORIGIN_REF_PREFIX}"
    r":[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?:[0-9a-f]{64}"
)

_MIN_KEY_BYTES = 32
_MAX_RAW_CHARS = 256
_MAX_RAW_BYTES = 1024

_KEY_INVALID = "ORIGIN_PROVENANCE_KEY_INVALID"
_KEY_VERSION_INVALID = "ORIGIN_PROVENANCE_KEY_VERSION_INVALID"
_SURFACE_UNSUPPORTED = "ORIGIN_PROVENANCE_SURFACE_UNSUPPORTED"
_SESSION_REF_INVALID = "ORIGIN_PROVENANCE_SESSION_REF_INVALID"


class OriginProvenanceError(ValueError):
    """Code-only failure; the message never contains origin input."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise OriginProvenanceError(code)


def _validate_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) < _MIN_KEY_BYTES:
        _fail(_KEY_INVALID)


def _validate_key_version(key_version: str) -> None:
    if not isinstance(key_version, str) or _KEY_VERSION.fullmatch(key_version) is None:
        _fail(_KEY_VERSION_INVALID)


def _validate_surface(origin_surface: str) -> None:
    if not isinstance(origin_surface, str) or origin_surface not in ORIGIN_SURFACES:
        _fail(_SURFACE_UNSUPPORTED)


def _canonicalize_raw_session_ref(raw_session_ref: str) -> bytes:
    if (
        not isinstance(raw_session_ref, str)
        or raw_session_ref == ""
        or len(raw_session_ref) > _MAX_RAW_CHARS
        or raw_session_ref.strip() == ""
        or raw_session_ref != raw_session_ref.strip()
    ):
        _fail(_SESSION_REF_INVALID)
    for character in raw_session_ref:
        code_point = ord(character)
        if code_point < 0x20 or code_point == 0x7F:
            _fail(_SESSION_REF_INVALID)
        if 0xD800 <= code_point <= 0xDFFF:
            _fail(_SESSION_REF_INVALID)
        category = unicodedata.category(character)
        if (
            category[0] == "C"
            or category in {"Zl", "Zp"}
            or (category == "Zs" and code_point != 0x20)
        ):
            _fail(_SESSION_REF_INVALID)
    canonical = unicodedata.normalize("NFC", raw_session_ref)
    encoded = canonical.encode("utf-8")
    if len(encoded) > _MAX_RAW_BYTES:
        _fail(_SESSION_REF_INVALID)
    return encoded


def derive_origin_chat_session_ref(
    key: bytes,
    *,
    key_version: str,
    origin_surface: str,
    raw_session_ref: str,
) -> str:
    """Derive one opaque durable reference for a raw origin identifier."""
    _validate_key(key)
    _validate_key_version(key_version)
    _validate_surface(origin_surface)
    encoded_ref = _canonicalize_raw_session_ref(raw_session_ref)
    message = b"\x00".join(
        (
            ORIGIN_REF_DOMAIN.encode("utf-8"),
            key_version.encode("utf-8"),
            origin_surface.encode("utf-8"),
            encoded_ref,
        )
    )
    digest = hmac.new(key, message, hashlib.sha256).hexdigest()
    return f"{ORIGIN_REF_PREFIX}:{key_version}:{digest}"


def validate_origin_chat_session_ref(value: str) -> bool:
    """Return True only when value follows the opaque derived grammar."""
    return isinstance(value, str) and ORIGIN_REF_PATTERN.fullmatch(value) is not None


def parse_origin_chat_session_ref(value: str) -> tuple[str, str] | None:
    """Return (key_version, digest) for a derived ref, else None."""
    if not validate_origin_chat_session_ref(value):
        return None
    _, key_version, digest = value.split(":")
    return key_version, digest
