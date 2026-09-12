"""WO208 repair bundle — canonical seed probe rehydration (R5/F1).

The ORIGINAL seed fence content (from docs/reviews/WO-P1-208-closeout-crash-
evidence.md) is republished VERBATIM below with its canonical SHA-256:

    bf1136e729cbe8676676031120a586610adeeb3dccca20addda6c1301a579aac

F1 RETRACTION: the original lab claimed this recorded hash had a one-char
typo. That claim was FALSE — it was this lane's own misreading of the
recorded digest; recorded and computed hashes agree exactly. The seed fence
must never be edited. This wrapper extracts the fence from the CURRENT seed
document in the pinned checkout, verifies the digest, and only then runs the
seed's four observations (imported from the recovered frozen artifact, byte
identical to the original submission).

Usage: python seed_probe.py --repo-root R --output-root D
Exit 0 only when the fence hash verifies AND all four seed observations hold.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_common as lab  # noqa: E402

CANONICAL_SEED_SHA256 = ("bf1136e729cbe8676676031120a586610adeeb3dccca2"
                         "0addda6c1301a579aac")


def extract_fence(repo_root: Path) -> str:
    doc = (repo_root / "docs" / "reviews" / "WO-P1-208-closeout-crash-evidence.md").read_text(
        encoding="utf-8")
    match = re.search(r"```python\n(.*?)```\n", doc, re.DOTALL)
    lab.require(match is not None, "seed python fence not found")
    return match.group(1)


def run_original_seed(seed_path: Path, repo_root: Path, out_dir: Path) -> dict:
    spec = importlib.util.spec_from_file_location("wo208_original_seed", seed_path)
    module = importlib.util.module_from_spec(spec)
    import os
    old_cwd = os.getcwd()
    os.chdir(repo_root)  # the seed resolves ROOT from cwd
    try:
        spec.loader.exec_module(module)
        result = module.run()
    finally:
        os.chdir(old_cwd)
    (out_dir / "seed-observations.json").write_text(
        json.dumps(result, indent=1), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--skip-manifest-preflight", action="store_true",
                        help="research-only: skip the bundle/source preflight gate")
    args = parser.parse_args()
    repo = lab.resolve_repo_root(args.repo_root)
    out_dir = Path(args.output_root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    # S1 preflight: every bundle hash + pinned source blob verified against
    # the SELECTED checkout before any experiment. Trust root is the pinned
    # candidate SHA recorded in the packet; the manifest is a lab-consistency
    # gate, not an authentication claim over attacker checkouts.
    preflight = {"skipped": args.skip_manifest_preflight, "expected": True}
    if not args.skip_manifest_preflight:
        try:
            manifest = lab.verify_manifest(repo)
            preflight["verified_files"] = len(manifest["files"])
            preflight["verified_source_blobs"] = len(manifest["source_blobs"])
            preflight["pinned_candidate_sha"] = lab.PINNED_CANDIDATE_SHA
        except lab.LabFailed as exc:
            preflight.update(expected=False, reason=str(exc)[:300])
            print(f"manifest_preflight_ok=False: {exc}")
            results = {
                "fence_sha256": None, "canonical_sha256": CANONICAL_SEED_SHA256,
                "manifest_preflight": preflight,
                "four_observations": {"expected": False, "data": None},
                "seed_artifact": {"path": None, "rejected_before_import": True},
                "elapsed_s": round(time.monotonic() - started, 2),
                "exit_code": 1,
            }
            summary = out_dir / "seed-summary.json"
            summary.write_text(json.dumps(results, indent=1), encoding="utf-8")
            print(f"summary -> {summary}")
            return 1
    results_preflight = preflight

    fence = extract_fence(repo)
    fence_sha = hashlib.sha256(fence.encode("utf-8")).hexdigest()
    fence_ok = fence_sha == CANONICAL_SEED_SHA256

    recovered = (repo / "docs" / "reviews" / "wo208-closeout-lab" / "_recovered")
    seed_copy = None
    # Prefer the frozen original from ignored repair storage if present;
    # otherwise re-materialize the exact fence bytes into the output dir.
    candidates = [
        repo / "runs" / "WO-P1-208" / "glm-repair" / "original" / "seed_probe.py",
        out_dir / "seed_fence_materialized.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            seed_copy = candidate
            break
    if seed_copy is None:
        seed_copy = candidates[-1]
        seed_copy.write_text(fence, encoding="utf-8")
    raw_sha = hashlib.sha256(seed_copy.read_bytes()).hexdigest()
    # frozen original was written with CRLF on this host; canonical fence is LF
    normalized = seed_copy.read_bytes().replace(b"\r\n", b"\n")
    norm_sha = hashlib.sha256(normalized).hexdigest()

    # S1 (N1): the executable bytes must be bound to the verified canonical
    # fence BEFORE import. Raw CRLF copies normalize to LF for comparison;
    # anything else is rejected without executing. A fake run() returning
    # the five expected numbers can therefore never substitute for the seed.
    executable_ok = raw_sha == CANONICAL_SEED_SHA256 or norm_sha == CANONICAL_SEED_SHA256
    rejection_reason = None
    if not executable_ok:
        rejection_reason = (
            f"executable bytes do not match the canonical fence "
            f"(raw={raw_sha[:12]}… lf={norm_sha[:12]}… canonical="
            f"{CANONICAL_SEED_SHA256[:12]}…); refused BEFORE import")

    observations = {}
    obs_ok = False
    executed_sentinel = False
    if fence_ok and executable_ok:
        lab.bootstrap_paths(repo)
        try:
            # harmless sentinel: proves accepted bytes ran (and, in the N1
            # repro, that rejected mismatched code was never executed)
            (out_dir / "seed-executed.sentinel").write_text(
                f"{raw_sha}\n", encoding="utf-8")
            executed_sentinel = True
            observations = run_original_seed(seed_copy, repo, out_dir)
            obs_ok = (
                observations.get("concurrent", {}).get("effects") == 2
                and observations.get("stale", {}).get("effects") == 1
                and observations.get("unknown_reentry", {}).get("effects") == 2
                and observations.get("positive", {}).get("effects") == 1
                and observations.get("positive", {}).get("state") == "COMPLETE"
            )
        except Exception as exc:  # noqa: BLE001 — lab evidence, not control flow
            observations = {"error": f"{type(exc).__name__}: {exc}"}

    results = {
        "fence_sha256": fence_sha,
        "canonical_sha256": CANONICAL_SEED_SHA256,
        "manifest_preflight": results_preflight,
        "f1_retraction": {
            "expected": fence_ok,
            "statement": ("recorded digest in seed doc == computed digest of its own "
                          "fence; the original '6a vs 6c typo' claim was the lab's "
                          "misreading and is RETRACTED (F1)")},
        "seed_artifact": {"path": str(seed_copy), "raw_sha256": raw_sha,
                           "lf_normalized_sha256": norm_sha,
                           "executable_bound_to_canonical": executable_ok,
                           "rejected_before_import": not executable_ok,
                           "rejection_reason": rejection_reason,
                           "execution_sentinel_written": executed_sentinel},
        "four_observations": {"expected": obs_ok, "data": observations},
        "elapsed_s": round(time.monotonic() - started, 2),
    }
    summary = out_dir / "seed-summary.json"
    exit_code = 0 if (fence_ok and executable_ok and obs_ok) else 1
    results["exit_code"] = exit_code
    summary.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"fence_hash_ok={fence_ok} executable_bound={executable_ok} "
          f"four_observations_ok={obs_ok} exit={exit_code}")
    print(f"summary -> {summary}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
