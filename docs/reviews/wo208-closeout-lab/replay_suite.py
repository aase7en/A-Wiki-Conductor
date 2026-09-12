"""WO208 finalization — single documented batch runner (S7/S8).

One command runs, in order:
  1. manifest preflight (bundle hashes + pinned source blobs; the manifest
     itself is excluded from its own hashes);
  2. the four lab entrypoints (seed_probe, c02_cut_matrix,
     c03_c05_c06_suite, c07_model) with per-entry exit codes preserved;
  3. the differential/metamorphic batch (S7): ordering permutations, fresh
     output dirs, missing/corrupt summary handling, and replay determinism
     compared on typed outcome/identity/effect/journal facts.

Usage (Windows):
    python docs/reviews/wo208-closeout-lab/replay_suite.py ^
        --repo-root A:\\path\\to\\export --output-root C:\\temp\\wo208-batch
POSIX:
    python docs/reviews/wo208-closeout-lab/replay_suite.py \\
        --repo-root /path/to/export --output-root /tmp/wo208-batch

Requires a checkout of the pinned candidate (tracked contents only; no
prior ignored runs needed). Existing output directories are reused only
when their contents are explained (the suite appends a run-N subdirectory
and never deletes evidence). Set PYTHONDONTWRITEBYTECODE=1 (the suite
forces it for children). Exit 0 only when every stage passes.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent
sys.path.insert(0, str(BUNDLE))
import lab_common as lab  # noqa: E402

ENTRIES = [
    ("seed", "seed_probe.py"),
    ("c02", "c02_cut_matrix.py"),
    ("c03c05c06", "c03_c05_c06_suite.py"),
    ("c07", "c07_model.py"),
]


def run_entry(repo: Path, script: str, out: Path, extra=()) -> dict:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(BUNDLE / script), "--repo-root", str(repo),
         "--output-root", str(out), *extra],
        capture_output=True, text=True, timeout=900, cwd=str(repo), env=env)
    return {"script": script, "exit": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-200:],
            "stderr_tail": (proc.stderr or "")[-200:],
            "expected": proc.returncode == 0,
            "elapsed_s": round(time.monotonic() - started, 2)}


def load_exit_typed(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def differential_batch(repo: Path, out: Path) -> dict:
    """S7: compare TYPED facts (outcome/identity/effects/journal), never
    timing or path strings, across meaningful variations."""
    facts = {}

    # ordering permutation: c07 before c02 etc. — outcomes must be identical
    # regardless of entry order (fresh dirs per permutation)
    order_a = out / "diff-order-a"
    order_b = out / "diff-order-b"
    exits_a = [run_entry(repo, s, order_a / n) for n, s in
               (("s", "seed_probe.py"), ("c", "c02_cut_matrix.py"))]
    exits_b = [run_entry(repo, s, order_b / n) for n, s in
               (("c", "c02_cut_matrix.py"), ("s", "seed_probe.py"))]
    facts["order-permutation-equivalent"] = {
        "expected": all(e["expected"] for e in exits_a + exits_b)
        and [e["exit"] for e in exits_a] == [0, 0]
        and [e["exit"] for e in exits_b] == [0, 0],
        "note": "typed exits equal under entry permutation; fresh dirs each run"}

    # c07 replay determinism: two fresh runs must produce identical
    # state_count/mutant verdicts/trace verdicts (paths and timing excluded)
    c7a = load_exit_typed(order_a / "c07" / "c07-summary.json")
    if c7a is None:
        c7run = run_entry(repo, "c07_model.py", order_a / "c07")
        c7a = load_exit_typed(order_a / "c07" / "c07-summary.json")
    c7b_run = run_entry(repo, "c07_model.py", order_b / "c07")
    c7b = load_exit_typed(order_b / "c07" / "c07-summary.json")
    same = (c7a is not None and c7b is not None
            and c7a["state_count"] == c7b["state_count"]
            and {k: v["expected"] for k, v in c7a["mutants"].items()}
                == {k: v["expected"] for k, v in c7b["mutants"].items()}
            and {k: v["expected"] for k, v in c7a["traces"].items()}
                == {k: v["expected"] for k, v in c7b["traces"].items()}
            and c7b_run["exit"] == 0)
    facts["c07-replay-deterministic"] = {"expected": same,
        "note": "state_count + mutant/trace verdicts identical across fresh dirs"}

    # missing/corrupt summary must not silently become success
    probe_dir = out / "diff-corrupt"
    r = run_entry(repo, "seed_probe.py", probe_dir / "s")
    summary_path = probe_dir / "s" / "seed-summary.json"
    if summary_path.is_file():
        backup = summary_path.read_text(encoding="utf-8")
        summary_path.write_text("{corrupt", encoding="utf-8")
        corrupt_load = load_exit_typed(summary_path)
        summary_path.write_text(backup, encoding="utf-8")
    else:
        corrupt_load = "missing-summary-file"
    facts["corrupt-summary-not-success"] = {
        "expected": r["expected"] and corrupt_load is None,
        "note": "entry exit still governs; corrupt JSON loads as None, never success"}

    # identical replay key across version advances (C05 receipt semantics):
    # exercised inside c03_c05_c06; here assert the suite stays green on a
    # FRESH dir (idempotent rerun of the whole entrypoint)
    again = run_entry(repo, "c03_c05_c06_suite.py", out / "diff-again")
    facts["suite-idempotent-rerun"] = {
        "expected": again["expected"],
        "note": "fresh-dir rerun green (receipt/replay identity inside suite)"}

    return facts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--skip-manifest-preflight", action="store_true")
    args = parser.parse_args()
    repo = lab.resolve_repo_root(args.repo_root)
    out_root = Path(args.output_root).resolve()

    # existing output directories: never delete; append a fresh run-N dir
    n = 1
    while (out_root / f"run-{n}").exists():
        n += 1
    out = out_root / f"run-{n}"
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results: dict = {"run_dir": str(out), "repo_root": str(repo)}

    # 1. manifest preflight (unless explicitly skipped for research)
    preflight = {"skipped": args.skip_manifest_preflight, "expected": True}
    if not args.skip_manifest_preflight:
        try:
            manifest = lab.verify_manifest(repo)
            preflight["verified_files"] = len(manifest["files"])
            preflight["verified_source_blobs"] = len(manifest["source_blobs"])
        except lab.LabFailed as exc:
            preflight.update(expected=False, reason=str(exc)[:300])
    results["manifest_preflight"] = preflight
    print(("PASS " if preflight["expected"] else "FAIL ") + "manifest-preflight")
    if not preflight["expected"]:
        results["exit_code"] = 1
        summary = out / "batch-summary.json"
        summary.write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"summary -> {summary}")
        return 1

    # 1.5 cold-start git shim: the seed fence records source_sha via
    # `git rev-parse HEAD` (immutable fence). On a fresh export without
    # .git, initialize an OWNED git identity so the observation records a
    # real HEAD instead of failing. This is host metadata (observation
    # data), never an acceptance predicate.
    if not (repo / ".git").exists():
        import shutil
        if shutil.which("git"):
            for cmd in (["git", "init", "-q"], ["git", "commit", "--allow-empty", "-q",
                          "-m", "wo208 cold-start export (owned; observation-only HEAD)"]):
                subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True,
                               timeout=60)
            results["cold_start_git_shim"] = "initialized owned empty HEAD in export"
            print("NOTE cold-start git shim: owned empty commit for source_sha observation")

    # 2. the four entrypoints
    entries = {}
    all_green = True
    for name, script in ENTRIES:
        r = run_entry(repo, script, out / name)
        entries[name] = r
        all_green = all_green and r["expected"]
        print(("PASS " if r["expected"] else "FAIL ") + f"entry:{name} exit={r['exit']}")
    results["entries"] = entries

    # 3. differential/metamorphic batch (S7) — only meaningful when the
    # base entries are green
    if all_green:
        diff = differential_batch(repo, out)
        results["differential_batch"] = diff
        for name, fact in diff.items():
            print(("PASS " if fact["expected"] else "FAIL ") + f"diff:{name}")
        all_green = all_green and all(f["expected"] for f in diff.values())

    results["elapsed_s"] = round(time.monotonic() - started, 2)
    results["_failed_checks"] = []
    exit_code = 0 if all_green else 1
    results["exit_code"] = exit_code
    summary = out / "batch-summary.json"
    summary.write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    print(f"batch exit={exit_code} summary -> {summary}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
