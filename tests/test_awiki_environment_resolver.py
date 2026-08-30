from __future__ import annotations

from pathlib import Path

import pytest

from a_conductor.awiki_environment_resolver import (
    AWikiDriveEnvironmentSource,
    AWikiEnvironmentReferenceResolver,
    AWikiEnvironmentResolutionError,
    resolve_awiki_drive_root,
)
from a_conductor.provider_configuration import ProviderEndpointConfig


class EndpointReader:
    def __init__(self, values: dict[str, ProviderEndpointConfig]) -> None:
        self.values = values
        self.calls: list[str] = []

    def get_endpoint(self, reference: str):
        self.calls.append(reference)
        return self.values.get(reference)


def make_drive(tmp_path: Path) -> Path:
    drive = tmp_path / "A-Wiki-Data"
    (drive / "secrets").mkdir(parents=True)
    return drive

def test_drive_root_prefers_explicit_environment(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    result = resolve_awiki_drive_root(
        environment={"A_WIKI_DRIVE_PATH": str(drive)},
        awiki_repo_root=tmp_path / "unused",
        home=tmp_path / "home",
    )
    assert result == drive.resolve()


def test_drive_root_uses_awiki_drive_link_then_path_file(tmp_path: Path) -> None:
    repo = tmp_path / "A-Wiki"
    repo.mkdir()
    linked = repo / "drive"
    (linked / "secrets").mkdir(parents=True)
    assert resolve_awiki_drive_root(
        environment={}, awiki_repo_root=repo, home=tmp_path / "home"
    ) == linked.resolve()

    repo2 = tmp_path / "A-Wiki-2"
    repo2.mkdir()
    configured = make_drive(tmp_path / "configured")
    (repo2 / ".drive-path").write_text(str(configured), encoding="utf-8")
    assert resolve_awiki_drive_root(
        environment={}, awiki_repo_root=repo2, home=tmp_path / "home"
    ) == configured.resolve()

def test_drive_root_falls_back_to_home_and_fails_closed(tmp_path: Path) -> None:
    home = tmp_path / "home"
    fallback = home / ".a-wiki-data"
    (fallback / "secrets").mkdir(parents=True)
    assert resolve_awiki_drive_root(
        environment={}, awiki_repo_root=None, home=home
    ) == fallback.resolve()

    with pytest.raises(AWikiEnvironmentResolutionError) as exc:
        resolve_awiki_drive_root(
            environment={}, awiki_repo_root=None, home=tmp_path / "empty-home"
        )
    assert exc.value.code == "AWIKI_DRIVE_ROOT_UNAVAILABLE"


def test_environment_source_global_then_repo_override_without_shell_eval(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    (drive / "secrets" / "global.env").write_text(
        "TOKEN=global\nLITERAL=$(whoami)\n", encoding="utf-8"
    )
    (drive / "secrets" / "A-Wiki-Conductor.env").write_text(
        "TOKEN=repo\n", encoding="utf-8"
    )
    source = AWikiDriveEnvironmentSource(
        drive, repo_env_name="A-Wiki-Conductor"
    )
    assert source.resolve_key("TOKEN") == "repo"
    assert source.resolve_key("LITERAL") == "$(whoami)"

def test_reference_resolver_uses_endpoint_store_and_awiki_secret_ref(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=top-secret-value\n", encoding="utf-8"
    )
    endpoint_ref = "provider-config:glm/base-url"
    endpoint = ProviderEndpointConfig(endpoint_ref, "https://provider.example/v1")
    reader = EndpointReader({endpoint_ref: endpoint})
    resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=reader,
        secret_source=AWikiDriveEnvironmentSource(drive),
    )

    assert resolver.resolve(endpoint_ref) == endpoint.base_url
    assert resolver.resolve("secret-ref:awiki-env/ANTHROPIC_API_KEY") == "top-secret-value"
    assert reader.calls == [endpoint_ref]


def test_reference_resolver_rejects_unsupported_or_missing_secret_without_leak(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    (drive / "secrets" / "global.env").write_text(
        "ANTHROPIC_API_KEY=top-secret-value\n", encoding="utf-8"
    )
    resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=EndpointReader({}),
        secret_source=AWikiDriveEnvironmentSource(drive),
    )
    with pytest.raises(AWikiEnvironmentResolutionError) as unsupported:
        resolver.resolve("secret-ref:provider/glm/main")
    assert unsupported.value.code == "SECRET_REFERENCE_UNSUPPORTED"

    with pytest.raises(AWikiEnvironmentResolutionError) as missing:
        resolver.resolve("secret-ref:awiki-env/DOES_NOT_EXIST")
    assert missing.value.code == "SECRET_REFERENCE_NOT_FOUND"
    assert "top-secret-value" not in str(missing.value)

    with pytest.raises(AWikiEnvironmentResolutionError) as invalid:
        resolver.resolve("secret-ref:awiki-env/../ANTHROPIC_API_KEY")
    assert invalid.value.code == "SECRET_REFERENCE_INVALID"


def test_missing_endpoint_reference_fails_closed(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    (drive / "secrets" / "global.env").write_text("X=y\n", encoding="utf-8")
    resolver = AWikiEnvironmentReferenceResolver(
        endpoint_reader=EndpointReader({}),
        secret_source=AWikiDriveEnvironmentSource(drive),
    )
    with pytest.raises(AWikiEnvironmentResolutionError) as exc:
        resolver.resolve("provider-config:missing/base-url")
    assert exc.value.code == "ENDPOINT_REFERENCE_NOT_FOUND"

def test_malformed_drive_path_file_falls_through_without_decode_leak(tmp_path: Path) -> None:
    repo = tmp_path / "A-Wiki-bad-config"
    repo.mkdir()
    (repo / ".drive-path").write_bytes(b"\xff\xfe\x00")
    home = tmp_path / "home-bad-config"
    fallback = home / ".a-wiki-data"
    fallback.mkdir(parents=True)

    assert resolve_awiki_drive_root(
        environment={}, awiki_repo_root=repo, home=home
    ) == fallback.resolve()


def test_repo_environment_name_rejects_path_escape(tmp_path: Path) -> None:
    drive = make_drive(tmp_path)
    with pytest.raises(ValueError, match="repo_env_name"):
        AWikiDriveEnvironmentSource(drive, repo_env_name="../outside")


def test_invalid_explicit_drive_override_fails_closed_instead_of_falling_back(tmp_path: Path) -> None:
    repo = tmp_path / "A-Wiki-explicit"
    repo.mkdir()
    (repo / "drive").mkdir()

    with pytest.raises(AWikiEnvironmentResolutionError) as exc:
        resolve_awiki_drive_root(
            environment={"A_WIKI_DRIVE_PATH": str(tmp_path / "missing-explicit")},
            awiki_repo_root=repo,
            home=tmp_path / "home-explicit",
        )

    assert exc.value.code == "AWIKI_DRIVE_ROOT_UNAVAILABLE"
