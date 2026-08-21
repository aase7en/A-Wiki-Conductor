"""Read-only upstream engine update check (WO-P1-059 PR-E).

Fetches the latest release and latest default-branch commit of the engine's
public GitHub repository via the unauthenticated REST API. This is the app's
first network egress: public, read-only, no credentials, bounded timeout.
Results are for display only — no DB writes, no auto-update.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable
from urllib.request import urlopen

UPSTREAM_REPO = "oraios/serena"
_TIMEOUT_SECONDS = 8


@dataclass(frozen=True, slots=True)
class UpstreamStatus:
    latest_release_tag: str | None
    latest_release_url: str | None
    latest_commit_sha: str | None
    latest_commit_date: str | None
    repo_url: str
    error_code: str | None = None


Fetcher = Callable[[str], str]


def _default_fetch(url: str) -> str:
    with urlopen(url, timeout=_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_upstream_status(
    repo: str = UPSTREAM_REPO, fetcher: Fetcher | None = None
) -> UpstreamStatus:
    fetch = fetcher or _default_fetch
    repo_url = f"https://github.com/{repo}"
    base = f"https://api.github.com/repos/{repo}"

    latest_tag: str | None = None
    latest_url: str | None = None
    latest_sha: str | None = None
    latest_date: str | None = None

    try:
        payload = json.loads(fetch(f"{base}/releases/latest"))
        latest_tag = payload.get("tag_name")
        latest_url = payload.get("html_url")
    except Exception:
        return UpstreamStatus(None, None, None, None, repo_url, "UPSTREAM_RELEASE_FETCH_FAILED")

    try:
        payload = json.loads(fetch(f"{base}/commits/main"))
        sha = payload.get("sha")
        latest_sha = sha[:12] if isinstance(sha, str) and len(sha) >= 12 else sha
        commit = payload.get("commit") or {}
        latest_date = (commit.get("committer") or {}).get("date")
    except Exception:
        if latest_tag is None:
            return UpstreamStatus(None, None, None, None, repo_url, "UPSTREAM_FETCH_FAILED")
        # release info alone is still useful — keep partial result
        return UpstreamStatus(latest_tag, latest_url, None, None, repo_url, None)

    return UpstreamStatus(latest_tag, latest_url, latest_sha, latest_date, repo_url)
