"""Sign the built executables via SignPath (Foundation OSS program).

Usage (after SIGNPATH_API_TOKEN is configured):

    python scripts/sign.py dist/A-Sunday-Conductor-Setup.exe

Env:
    SIGNPATH_API_TOKEN   API token from the SignPath portal (required)
    SIGNPATH_ORG         organization id (default: aase7en)
    SIGNPATH_PROJECT     project name (default: a-wiki-conductor)

No-op (exit 0) when the token is absent, so CI/release pipelines can run
unsigned until the Foundation application is approved.
"""

from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

API = "https://app.signpath.io/API/v1"


def _request(url: str, token: str, data: bytes | None = None, method: str = "GET"):
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.read()


def sign(path: Path, token: str, org: str, project: str) -> str:
    import base64

    content = base64.b64encode(path.read_bytes()).decode()
    body = (
        '{"artifact": {"fileName": "%s", "content": "%s"}}' % (path.name, content)
    ).encode()
    status, body = _request(
        f"{API}/{org}/SigningRequests/{project}-auto?ArtifactType=Initial",
        token,
        data=body,
        method="POST",
    )
    print(f"submitted ({status})")
    return "submitted"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    token = os.environ.get("SIGNPATH_API_TOKEN", "").strip()
    if not token:
        print("SIGNPATH_API_TOKEN not set - skipping signing (unsigned build)")
        return 0
    if not argv:
        print("usage: python scripts/sign.py <file-to-sign>")
        return 2
    org = os.environ.get("SIGNPATH_ORG", "aase7en")
    project = os.environ.get("SIGNPATH_PROJECT", "a-wiki-conductor")
    for target in argv:
        path = Path(target)
        if not path.is_file():
            print(f"missing: {path}")
            return 2
        sign(path, token, org, project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
