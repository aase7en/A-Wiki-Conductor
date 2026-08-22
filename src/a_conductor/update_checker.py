"""GitHub Releases update checker — read-only, stdlib-only."""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass

API_URL = "https://api.github.com/repos/aase7en/A-Wiki-Conductor/releases/latest"
TIMEOUT_SECONDS = 8


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str | None
    download_url: str | None
    release_notes: str | None
    is_newer: bool
    error: str | None = None


def _parse_version(version: str) -> tuple[int, ...]:
    clean = version.strip().lstrip("v").lstrip("V")
    parts = re.findall(r"\d+", clean)
    return tuple(int(p) for p in parts[:3]) if parts else (0,)


def fetch_latest_release(url: str = API_URL) -> dict | None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "A-Sunday-Conductor-UpdateChecker",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def check_for_update(
    current_version: str,
    *,
    fetcher=None,
) -> UpdateCheckResult:
    """Check GitHub for a newer release. Never raises; returns error field."""
    active_fetcher = fetcher or fetch_latest_release
    try:
        data = active_fetcher()
    except Exception as exc:
        return UpdateCheckResult(
            current_version=current_version,
            latest_version=None,
            download_url=None,
            release_notes=None,
            is_newer=False,
            error=str(exc)[:120],
        )

    latest_tag = (data or {}).get("tag_name") or ""
    latest = latest_tag.lstrip("v").lstrip("V")
    download_url = (data or {}).get("html_url") or ""
    notes = (data or {}).get("body") or ""

    is_newer = _parse_version(latest) > _parse_version(current_version)
    return UpdateCheckResult(
        current_version=current_version,
        latest_version=latest or None,
        download_url=download_url or None,
        release_notes=notes or None,
        is_newer=is_newer,
    )
