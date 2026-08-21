from __future__ import annotations

import json

from a_conductor.upstream_check import fetch_upstream_status


def _fake_github(release: dict | None, commit: dict | None):
    responses = {}
    if release is not None:
        responses["/releases/latest"] = release
    if commit is not None:
        responses["/commits/main"] = commit

    def fetch(url: str) -> str:
        for suffix, payload in responses.items():
            if url.endswith(suffix):
                return json.dumps(payload)
        raise OSError("no fake for " + url)

    return fetch


def test_fetch_upstream_success() -> None:
    fetcher = _fake_github(
        {"tag_name": "v1.2.3", "html_url": "https://github.com/oraios/serena/releases/v1.2.3"},
        {"sha": "abcdef1234567890abcdef", "commit": {"committer": {"date": "2026-08-20T10:00:00Z"}}},
    )

    status = fetch_upstream_status(fetcher=fetcher)

    assert status.error_code is None
    assert status.latest_release_tag == "v1.2.3"
    assert status.latest_release_url is not None and "v1.2.3" in status.latest_release_url
    assert status.latest_commit_sha == "abcdef123456"
    assert status.latest_commit_date == "2026-08-20T10:00:00Z"
    assert status.repo_url == "https://github.com/oraios/serena"


def test_fetch_upstream_release_only_partial() -> None:
    fetcher = _fake_github(
        {"tag_name": "v1.0.0", "html_url": "https://x"},
        None,
    )

    status = fetch_upstream_status(fetcher=fetcher)

    assert status.error_code is None
    assert status.latest_release_tag == "v1.0.0"
    assert status.latest_commit_sha is None


def test_fetch_upstream_network_failure() -> None:
    def broken(_url: str) -> str:
        raise OSError("no network")

    status = fetch_upstream_status(fetcher=broken)

    assert status.error_code == "UPSTREAM_RELEASE_FETCH_FAILED"
    assert status.latest_release_tag is None
    assert status.repo_url  # link still shown so the user can check manually
