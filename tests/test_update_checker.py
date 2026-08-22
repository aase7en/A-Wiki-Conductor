"""Update checker + legal files + MIT license (public release prep)."""

from __future__ import annotations

import pytest

from a_conductor.update_checker import (
    UpdateCheckResult,
    _parse_version,
    check_for_update,
)


def test_parse_version_extracts_numeric_parts() -> None:
    assert _parse_version("0.3.1") == (0, 3, 1)
    assert _parse_version("v1.2.3") == (1, 2, 3)
    assert _parse_version("2.0.0-beta") == (2, 0, 0)
    assert _parse_version("") == (0,)


def test_check_newer_version_detected() -> None:
    def fake_fetch():
        return {"tag_name": "v1.0.0", "html_url": "https://github.com/rel", "body": "notes"}

    result = check_for_update("0.3.1", fetcher=fake_fetch)
    assert result.is_newer is True
    assert result.latest_version == "1.0.0"
    assert result.download_url == "https://github.com/rel"
    assert result.release_notes == "notes"
    assert result.error is None


def test_check_same_version_not_newer() -> None:
    def fake_fetch():
        return {"tag_name": "v0.3.1", "html_url": "https://github.com/rel", "body": ""}

    result = check_for_update("0.3.1", fetcher=fake_fetch)
    assert result.is_newer is False


def test_check_older_github_version_not_newer() -> None:
    def fake_fetch():
        return {"tag_name": "v0.2.0", "html_url": "https://github.com/rel", "body": ""}

    result = check_for_update("0.3.1", fetcher=fake_fetch)
    assert result.is_newer is False


def test_network_error_returns_error_not_crash() -> None:
    def broken_fetch():
        raise ConnectionError("no internet")

    result = check_for_update("0.3.1", fetcher=broken_fetch)
    assert result.is_newer is False
    assert result.error is not None
    assert "no internet" in result.error or "Connection" in result.error


def test_mit_license_file_exists() -> None:
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    license_text = (repo / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "WITHOUT WARRANTY OF ANY KIND" in license_text


def test_funding_yml_exists() -> None:
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    funding = repo / ".github" / "FUNDING.yml"
    assert funding.is_file()
    assert "github" in funding.read_text(encoding="utf-8")


def test_privacy_and_security_docs_exist() -> None:
    from pathlib import Path

    repo = Path(__file__).resolve().parents[1]
    assert (repo / "PRIVACY.md").is_file()
    assert (repo / "SECURITY.md").is_file()
