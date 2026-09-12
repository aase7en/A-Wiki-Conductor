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


# ── S1: manifest preflight gate (lab-only trust discipline) ────────────────

BUNDLE_DIR = Path(__file__).resolve().parent

# Trust root: the independently pinned candidate SHA recorded in the exact
# repair packet. A self-authored manifest can never authenticate an
# attacker-controlled checkout; this gate only proves the SELECTED checkout
# still carries the bytes this bundle was authored against.
PINNED_CANDIDATE_SHA = "2482998e19ee439e04adf321cd5d74c1feb94243"

SOURCE_BLOB_PINS = {
    "src/a_conductor/goal_closeout.py": None,  # filled by manifest
}


def sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(repo_root: Path, bundle_dir: Path | None = None) -> dict:
    """Fail-closed preflight BEFORE any experiment (S1).

    Checks every manifest-listed bundle file hash and the pinned source blobs
    against the selected checkout. The manifest itself is excluded from its
    own hashes (a file cannot contain its own digest). Any missing/changed
    script, unexpected manifest omission, or wrong source pin raises
    LabFailed. Returns the verified manifest for callers to record."""
    bundle = bundle_dir or BUNDLE_DIR
    manifest_path = bundle / "manifest.json"
    require(manifest_path.is_file(), "manifest missing from bundle")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files", {})
    require(isinstance(entries, dict) and entries, "manifest has no file entries")
    require("manifest.json" not in entries,
            "manifest must not hash itself (self-reference)")
    # unexpected omission: every tracked bundle .py/.md must be listed
    tracked = sorted(p.name for p in bundle.iterdir()
                     if p.suffix in (".py",) and p.name != "__init__.py")
    listed = sorted(entries)
    missing_from_manifest = [n for n in tracked if n not in entries]
    require(not missing_from_manifest,
            f"bundle scripts absent from manifest: {missing_from_manifest}")
    mismatches = []
    for name, expected in entries.items():
        target = bundle / name
        if not target.is_file():
            mismatches.append(f"{name}: MISSING")
            continue
        actual = sha256_file(target)
        if actual != expected:
            mismatches.append(f"{name}: expected {expected} actual {actual}")
    require(not mismatches, "manifest hash mismatches: " + "; ".join(mismatches))
    # source blob pins (four production seams this lab reasons about)
    blobs = manifest.get("source_blobs", {})
    require(len(blobs) == 4, "manifest must pin exactly four source blobs")
    blob_mismatch = []
    for rel, expected in blobs.items():
        target = repo_root / rel
        if not target.is_file():
            blob_mismatch.append(f"{rel}: MISSING")
            continue
        actual = sha256_file(target)
        if actual != expected:
            blob_mismatch.append(f"{rel}: expected {expected[:12]}… actual {actual[:12]}…")
    require(not blob_mismatch, "source pin mismatches: " + "; ".join(blob_mismatch))
    return manifest


# ── S4: the ONE shared cut-observation validator ────────────────────────────

def validate_cut_observation(observed: dict) -> tuple[bool, list]:
    """The single validation path for C02 cut observations (S4).

    BOTH positive cases and negative controls MUST route their observations
    through this function. Returns (ok, reasons). A deliberately-broken
    observation fed here must produce ok=False for the REASON that was
    broken — exit code, marker, effect count, journal refs, job state."""
    reasons = []
    if observed.get("exit") != observed.get("want_exit"):
        reasons.append(f"exit:{observed.get('exit')}!={observed.get('want_exit')}")
    if not observed.get("marker"):
        reasons.append("marker-missing")
    if observed.get("effects") != observed.get("want_effects"):
        reasons.append(f"effects:{observed.get('effects')}!={observed.get('want_effects')}")
    if observed.get("refs") != observed.get("want_refs"):
        reasons.append(f"refs:{observed.get('refs')}!={observed.get('want_refs')}")
    if observed.get("state") != observed.get("want_state"):
        reasons.append(f"state:{observed.get('state')}!={observed.get('want_state')}")
    return (not reasons), reasons

