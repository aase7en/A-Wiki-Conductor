"""Resolve provider references through the private A-Wiki Drive contract.

This module owns no secret store or shell loader. It reads the existing A-Wiki
Data env files natively, never evaluates shell syntax, and resolves endpoint
references through the accepted provider configuration store boundary.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Mapping, Protocol

from .provider_configuration import ProviderEndpointConfig

_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_REPO_ENV_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SECRET_PREFIX = "secret-ref:awiki-env/"
_MAX_REFERENCE_LENGTH = 512


class AWikiEnvironmentResolutionError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ProviderEndpointReader(Protocol):
    def get_endpoint(self, endpoint_ref: str) -> ProviderEndpointConfig | None: ...

class SecretEnvironmentSource(Protocol):
    def resolve_key(self, key: str) -> str: ...


def _safe_directory(value: str | Path) -> Path | None:
    try:
        path = Path(value).expanduser().resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        return None
    return path if path.is_dir() else None


def resolve_awiki_drive_root(
    *,
    environment: Mapping[str, str] | None = None,
    awiki_repo_root: str | Path | None = None,
    home: str | Path | None = None,
) -> Path:
    """Resolve the A-Wiki private Drive root without hard-coded machine paths."""
    source = os.environ if environment is None else environment
    override = source.get("A_WIKI_DRIVE_PATH", "").strip()
    if override:
        candidate = _safe_directory(override)
        if candidate is None:
            raise AWikiEnvironmentResolutionError("AWIKI_DRIVE_ROOT_UNAVAILABLE")
        return candidate

    if awiki_repo_root is not None:
        repo = Path(awiki_repo_root).expanduser().resolve(strict=False)
        candidate = _safe_directory(repo / "drive")
        if candidate is not None:
            return candidate
        path_file = repo / ".drive-path"
        if path_file.is_file():
            try:
                raw = path_file.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError):
                raw = ""
            if raw:
                configured = Path(raw).expanduser()
                if not configured.is_absolute():
                    configured = repo / configured
                candidate = _safe_directory(configured)
                if candidate is not None:
                    return candidate

    home_root = Path.home() if home is None else Path(home).expanduser()
    candidate = _safe_directory(home_root / ".a-wiki-data")
    if candidate is not None:
        return candidate
    raise AWikiEnvironmentResolutionError("AWIKI_DRIVE_ROOT_UNAVAILABLE")


def _parse_env_file(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        raise AWikiEnvironmentResolutionError("SECRET_SOURCE_UNAVAILABLE") from exc
    values: dict[str, str] = {}
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if _ENV_KEY_RE.fullmatch(key) is None:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if any(char in value for char in ("\x00", "\r", "\n")):
            raise AWikiEnvironmentResolutionError("SECRET_VALUE_INVALID")
        values[key] = value
    return values


class AWikiDriveEnvironmentSource:
    """Read requested keys on demand from existing A-Wiki Data env files."""

    def __init__(
        self,
        drive_root: str | Path,
        *,
        repo_env_name: str | None = None,
    ) -> None:
        root = _safe_directory(drive_root)
        if root is None:
            raise AWikiEnvironmentResolutionError("AWIKI_DRIVE_ROOT_UNAVAILABLE")
        if repo_env_name is not None and _REPO_ENV_RE.fullmatch(repo_env_name) is None:
            raise ValueError("repo_env_name is invalid")
        self.drive_root = root
        self.repo_env_name = repo_env_name

    def _load(self) -> dict[str, str]:
        global_path = self.drive_root / "secrets" / "global.env"
        if not global_path.is_file():
            raise AWikiEnvironmentResolutionError("SECRET_SOURCE_UNAVAILABLE")
        values = _parse_env_file(global_path)
        if self.repo_env_name is not None:
            repo_path = self.drive_root / "secrets" / f"{self.repo_env_name}.env"
            if repo_path.is_file():
                values.update(_parse_env_file(repo_path))
        return values

    def resolve_key(self, key: str) -> str:
        if not isinstance(key, str) or _ENV_KEY_RE.fullmatch(key) is None:
            raise AWikiEnvironmentResolutionError("SECRET_REFERENCE_INVALID")
        values = self._load()
        if key not in values or not values[key]:
            raise AWikiEnvironmentResolutionError("SECRET_REFERENCE_NOT_FOUND")
        return values[key]


class AWikiEnvironmentReferenceResolver:
    """Resolve endpoint metadata or allowlisted A-Wiki env secret references."""

    def __init__(
        self,
        *,
        endpoint_reader: ProviderEndpointReader,
        secret_source: SecretEnvironmentSource,
    ) -> None:
        if not callable(getattr(endpoint_reader, "get_endpoint", None)):
            raise ValueError("endpoint_reader must provide get_endpoint")
        if not callable(getattr(secret_source, "resolve_key", None)):
            raise ValueError("secret_source must provide resolve_key")
        self._endpoint_reader = endpoint_reader
        self._secret_source = secret_source
    def resolve(self, reference: str) -> str:
        if (
            not isinstance(reference, str)
            or not reference.strip()
            or len(reference) > _MAX_REFERENCE_LENGTH
            or any(char in reference for char in ("\x00", "\r", "\n"))
        ):
            raise AWikiEnvironmentResolutionError("REFERENCE_INVALID")
        reference = reference.strip()
        if reference.startswith("secret-ref:"):
            if not reference.startswith(_SECRET_PREFIX):
                raise AWikiEnvironmentResolutionError("SECRET_REFERENCE_UNSUPPORTED")
            key = reference[len(_SECRET_PREFIX) :]
            if _ENV_KEY_RE.fullmatch(key) is None:
                raise AWikiEnvironmentResolutionError("SECRET_REFERENCE_INVALID")
            return self._secret_source.resolve_key(key)

        try:
            endpoint = self._endpoint_reader.get_endpoint(reference)
        except Exception as exc:
            raise AWikiEnvironmentResolutionError("ENDPOINT_REFERENCE_UNAVAILABLE") from exc
        if endpoint is None:
            raise AWikiEnvironmentResolutionError("ENDPOINT_REFERENCE_NOT_FOUND")
        if not isinstance(endpoint, ProviderEndpointConfig) or endpoint.endpoint_ref != reference:
            raise AWikiEnvironmentResolutionError("ENDPOINT_REFERENCE_INVALID")
        return endpoint.base_url