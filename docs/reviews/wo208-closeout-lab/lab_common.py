"""WO208 closeout lab repair — shared helpers (tracked bundle).

Everything here is a RESEARCH artifact for the review bundle, not production
code. ``lab_common`` provides: repository-root resolution from explicit
arguments, bounded owned-temp helpers, strict exit discipline for lab drivers
(any unmet expectation must produce a nonzero exit), and shared fixture
builders used by the bundle scripts.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


class LabFailed(AssertionError):
    """Raised when a lab expectation is not met; drivers exit nonzero."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise LabFailed(message)


def resolve_repo_root(explicit: str | None) -> Path:
    """Repository root comes ONLY from --repo-root or this file's location
    inside the checkout (docs/reviews/wo208-closeout-lab/lab_common.py)."""
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = Path(__file__).resolve().parents[3]
    require((root / "src" / "a_conductor" / "goal_closeout.py").is_file(),
            f"repository root not resolvable: {root}")
    return root


def bootstrap_paths(repo_root: Path) -> None:
    src = str(repo_root / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def owned_temp(prefix: str = "wo208-repair-") -> Path:
    require(prefix.startswith("wo208-"), "temp prefix must be wo208-")
    return Path(tempfile.mkdtemp(prefix=prefix))


def load_result(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def journal_refs(store, job_id: str) -> list:
    return [e.checkpoint_ref for e in store.list_events(job_id) if e.checkpoint_ref]


def fail_nonzero(results: dict, summary_path: Path) -> int:
    """Write summary and return a process exit code that is nonzero when any
    leaf expectation failed (R2: a successful exit must certify the experiment)."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, indent=1, default=str),
                            encoding="utf-8")
    failed = []

    def scan(node, prefix=""):
        if isinstance(node, dict):
            if "expected" in node and isinstance(node["expected"], bool):
                if node["expected"] is not True:
                    failed.append(prefix)
                return
            for key, value in node.items():
                scan(value, f"{prefix}.{key}" if prefix else str(key))
        elif isinstance(node, list):
            for i, value in enumerate(node):
                scan(value, f"{prefix}[{i}]")
        elif node is False:
            failed.append(prefix)

    scan(results)
    results["_failed_checks"] = failed
    summary_path.write_text(json.dumps(results, indent=1, default=str),
                            encoding="utf-8")
    return 1 if failed else 0
