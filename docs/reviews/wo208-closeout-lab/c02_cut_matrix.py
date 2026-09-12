"""WO208 closeout lab repair — C02 cut-matrix driver (R2 repair).

Every expectation is ENFORCED (LabFailed => nonzero exit). Each cut requires:
  - exact child exit code;
  - a cut-marker file written AT the boundary (name matches the mode) — this
    is what proves the fault hook was actually entered rather than a fallback
    exiting with the same code;
  - exact effect count, journal ref count, reopened job state.

Negative controls (run deliberately-broken variants and require the driver to
FAIL) prove the oracle is non-vacuous:
  - wrong expected exit code must fail;
  - missing cut-marker must fail;
  - a zero-exit 'returned-past-hook' child must be reported as such.

Usage: python c02_cut_matrix.py --repo-root R --output-root D
Exit 0 only when every case and every negative control behaves as required.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_common as lab  # noqa: E402

CHILD = Path(__file__).resolve().parent / "wo208_child.py"

CUTS = [
    ("cut0-before-effect", "before-effect", 10, 0, 1, "REVIEW_PENDING"),
    ("cut2-fold-response", "fold-response", 12, 1, 1, "REVIEW_PENDING"),
    ("cut1-effect-commit", "effect-commit", 11, 1, 1, "REVIEW_PENDING"),
    ("cut3-checkpoint-commit", "checkpoint-commit", 13, 1, 2, "REVIEW_PENDING"),
    ("cut4-complete-commit", "complete-commit", 14, 1, 2, "COMPLETE"),
]


def run_child(repo: Path, mode: str, folder: Path, timeout: float = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            [sys.executable, str(CHILD), "--repo-root", str(repo),
             "--mode", mode, "--dir", str(folder)],
            capture_output=True, text=True, timeout=timeout, cwd=str(repo))
        return proc.returncode, (proc.stderr or "")[-200:]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"


def observe(folder: Path, repo: Path) -> dict:
    sys.path.insert(0, str(repo / "src"))
    sys.path.insert(0, str(repo))
    from a_conductor.job_store import SQLiteJobStore
    from tests.test_goal_closeout import JOB
    store = SQLiteJobStore(folder / "jobs.sqlite")
    job = store.get_job(JOB)
    refs = lab.journal_refs(store, JOB)
    effects = sorted(folder.glob("effect-*.txt"))
    return {"state": job.state.value, "version": job.version,
            "refs": len(refs), "effects": len(effects)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    repo = lab.resolve_repo_root(args.repo_root)
    out_root = Path(args.output_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    results: dict = {"cases": {}, "negative_controls": {}, "lab": str(out_root)}

    for name, mode, want_exit, want_effects, want_refs, want_state in CUTS:
        folder = out_root / name
        folder.mkdir(parents=True, exist_ok=True)
        code, err = run_child(repo, mode, folder)
        marker_ok = (folder / f"cut-marker-{mode}.txt").is_file()
        obs = observe(folder, repo)
        # S4: positive observations route through the SAME shared validator
        # the negative controls use — one validation path, no side channel.
        ok, reasons = lab.validate_cut_observation({
            "exit": code, "want_exit": want_exit, "marker": marker_ok,
            "effects": obs["effects"], "want_effects": want_effects,
            "refs": obs["refs"], "want_refs": want_refs,
            "state": obs["state"], "want_state": want_state,
        })
        results["cases"][name] = {
            "expected": ok, "exit": code, "want_exit": want_exit,
            "marker_at_boundary": marker_ok, "obs": obs,
            "want": {"effects": want_effects, "refs": want_refs, "state": want_state},
            "validator_reasons": reasons,
            "stderr_tail": err if not ok else "",
        }
        print(("PASS " if ok else "FAIL ") + name)

    # restart-safe from the checkpoint-commit DB
    src = out_root / "cut3-checkpoint-commit"
    folder = out_root / "restart-safe"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(src, folder)
    code, err = run_child(repo, "safe-restart", folder)
    payload = lab.load_result(folder / "safe-result.json") if (folder / "safe-result.json").exists() else {}
    obs = observe(folder, repo)
    ok = (code == 16 and (folder / "cut-marker-safe-restart.txt").is_file()
          and payload.get("final_state") == "COMPLETE"
          and obs["effects"] == 1 and obs["state"] == "COMPLETE")
    results["cases"]["restart-safe"] = {"expected": ok, "exit": code, "payload": payload,
                                        "obs": obs, "stderr_tail": err if not ok else ""}
    print(("PASS " if ok else "FAIL ") + "restart-safe")

    # restart-unsafe from the fold-response DB (duplicate after REAL crash)
    src = out_root / "cut2-fold-response"
    folder = out_root / "restart-unsafe"
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(src, folder)
    code, err = run_child(repo, "unsafe-restart", folder)
    payload = lab.load_result(folder / "unsafe-result.json") if (folder / "unsafe-result.json").exists() else {}
    obs = observe(folder, repo)
    ok = (code == 15 and (folder / "cut-marker-unsafe-restart.txt").is_file()
          and obs["effects"] == 2)
    results["cases"]["restart-unsafe"] = {
        "expected": ok, "exit": code, "obs": obs, "payload": payload,
        "classification": "BASELINE_SEAM_COUNTEREXAMPLE (duplicate effect after real crash)"
        if ok else "UNEXPECTED"}
    print(("PASS " if ok else "FAIL ") + "restart-unsafe")

    # stale-gated
    folder = out_root / "stale-gated"
    folder.mkdir(parents=True, exist_ok=True)
    code, err = run_child(repo, "stale-gated", folder)
    payload = lab.load_result(folder / "stale-gated.json") if (folder / "stale-gated.json").exists() else {}
    ok = (code == 0 and payload.get("effect_count") == 0 and payload.get("gate_refused"))
    results["cases"]["stale-gated"] = {"expected": ok, "payload": payload}
    print(("PASS " if ok else "FAIL ") + "stale-gated")

    # concurrent two-process baseline (real processes, barrier-driven)
    folder = out_root / "concurrent-processes"
    folder.mkdir(parents=True, exist_ok=True)
    run_child(repo, "seed-only", folder)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_child, repo, "concurrent-baseline", folder) for _ in range(2)]
        outs = [f.result(timeout=90) for f in futures]
    obs = observe(folder, repo)
    per_child = [lab.load_result(p) for p in sorted(folder.glob("concurrent-*.json"))]
    ok = (outs[0][0] == 17 and outs[1][0] == 17
          and len(per_child) == 2
          and sum(c.get("effects_this_run", 0) for c in per_child) == 2
          and obs["effects"] == 2 and obs["refs"] == 2
          and sorted(c["decision"] for c in per_child)
          == ["FOLD_REQUIRED", "RECOVERY_REQUIRED"])
    results["cases"]["concurrent-2proc"] = {
        "expected": ok, "exits": [o[0] for o in outs], "obs": obs, "per_child": per_child,
        "classification": "BASELINE_SEAM_COUNTEREXAMPLE (two effects, one checkpoint)"
        if ok else "UNEXPECTED"}
    print(("PASS " if ok else "FAIL ") + "concurrent-2proc")

    # ── negative controls (driver MUST fail on each) ─────────────────────
    # S4 repair (N3): every control FEEDS its deliberately-broken observation
    # through the SAME validate_cut_observation used by the positive cases
    # and asserts the rejection — proving the experiment itself would fail,
    # not merely that the broken bytes exist.
    def control(name: str, ok: bool, detail: dict) -> None:
        results["negative_controls"][name] = {"expected": ok, **detail}
        print(("PASS " if ok else "FAIL ") + "control:" + name)

    # take one REAL observation as the base, then mutate it per control
    base_folder = out_root / "cut0-before-effect"
    base_code, _ = run_child(repo, "before-effect", base_folder)
    base_marker = (base_folder / "cut-marker-before-effect.txt").is_file()
    base_obs = observe(base_folder, repo)
    base = {
        "exit": base_code, "want_exit": 10, "marker": base_marker,
        "effects": base_obs["effects"], "want_effects": 0,
        "refs": base_obs["refs"], "want_refs": 1,
        "state": base_obs["state"], "want_state": "REVIEW_PENDING",
    }

    # 1. wrong expected exit: mutated want fed to the shared validator
    wrong_exit = dict(base, want_exit=99)
    ok_w, reasons_w = lab.validate_cut_observation(wrong_exit)
    control("wrong-exit-code-detected", not ok_w and any("exit:" in r for r in reasons_w),
            {"validator_reasons": reasons_w, "note": "same validator rejects exit!=want"})

    # 2. missing marker
    no_marker = dict(base, marker=False)
    ok_m, reasons_m = lab.validate_cut_observation(no_marker)
    control("missing-marker-detected", not ok_m and "marker-missing" in reasons_m,
            {"validator_reasons": reasons_m})

    # 3. fallback exit without marker (renamed marker on a REAL run)
    folder = out_root / "neg-fallback-path"
    folder.mkdir(parents=True, exist_ok=True)
    code, _ = run_child(repo, "fold-response", folder)
    m = folder / "cut-marker-fold-response.txt"
    if m.exists():
        m.rename(folder / "renamed-marker.txt")
    fallback_obs = observe(folder, repo)
    ok_f, reasons_f = lab.validate_cut_observation({
        "exit": code, "want_exit": 12, "marker": m.exists(),
        "effects": fallback_obs["effects"], "want_effects": 1,
        "refs": fallback_obs["refs"], "want_refs": 1,
        "state": fallback_obs["state"], "want_state": "REVIEW_PENDING",
    })
    control("fallback-exit-without-marker-rejected",
            not ok_f and "marker-missing" in reasons_f,
            {"validator_reasons": reasons_f})

    # 4. wrong effect count through the shared validator
    bad_effects = dict(base, effects=base["effects"] + 1)
    ok_e, reasons_e = lab.validate_cut_observation(bad_effects)
    control("wrong-effect-count-detected",
            not ok_e and any("effects:" in r for r in reasons_e),
            {"validator_reasons": reasons_e})

    # 5. wrong journal refs
    bad_refs = dict(base, refs=base["refs"] + 2)
    ok_r, reasons_r = lab.validate_cut_observation(bad_refs)
    control("wrong-refs-detected", not ok_r and any("refs:" in r for r in reasons_r),
            {"validator_reasons": reasons_r})

    # 6. wrong reopened job state
    bad_state = dict(base, state="COMPLETE")
    ok_s, reasons_s = lab.validate_cut_observation(bad_state)
    control("wrong-job-state-detected",
            not ok_s and any("state:" in r for r in reasons_s),
            {"validator_reasons": reasons_s})

    # 7. unknown mode argument rejection (separate argparse control — NOT a
    # timeout proof; the real timeout proof is control 8)
    folder = out_root / "neg-unknown-mode"
    folder.mkdir(parents=True, exist_ok=True)
    code, err = run_child(repo, "not-a-mode", folder)
    control("unknown-mode-distinct-exit", code == 2,
            {"exit": code, "stderr": err[-80:]})

    # 8. S5 REAL bounded helper timeout: a finite owned helper that stays
    # alive past a short test timeout; the driver kills it and the exit is
    # nonzero (timeout sentinel), plus a bounded sibling reaped on exit.
    folder = out_root / "neg-real-timeout"
    folder.mkdir(parents=True, exist_ok=True)
    import subprocess as _sp
    hang = _sp.Popen(
        [sys.executable, str(CHILD), "--repo-root", str(repo),
         "--mode", "hang-past-timeout", "--dir", str(folder)],
        stdout=_sp.PIPE, stderr=_sp.PIPE, cwd=str(repo))
    sibling = _sp.Popen(
        [sys.executable, str(CHILD), "--repo-root", str(repo),
         "--mode", "bounded-sibling", "--dir", str(folder)],
        stdout=_sp.PIPE, stderr=_sp.PIPE, cwd=str(repo))
    timed_out = False
    try:
        hang.communicate(timeout=6)
    except _sp.TimeoutExpired:
        timed_out = True
        hang.kill()
        hang.communicate()
    hang_reaped = hang.poll() is not None
    try:
        sibling.communicate(timeout=15)
    except _sp.TimeoutExpired:
        sibling.kill()
        sibling.communicate()
    sibling_reaped = sibling.poll() is not None
    sibling_marker = (folder / "bounded-sibling-started.txt").is_file()
    control("real-helper-timeout-killed-and-reaped",
            timed_out and hang_reaped and sibling_reaped,
            {"timeout_sentinel": timed_out, "helper_reaped": hang_reaped,
             "sibling_reaped": sibling_reaped, "sibling_started": sibling_marker,
             "note": ("owned finite helpers only; direct-child cleanup does not "
                      "imply arbitrary process-tree containment")})

    # 9. S5 early first-child failure + missing-output cases
    folder = out_root / "neg-early-fail"
    folder.mkdir(parents=True, exist_ok=True)
    code, err = run_child(repo, "early-first-child-fail", folder)
    control("early-first-child-failure-nonzero", code not in (0,),
            {"exit": code, "stderr": err[-80:]})
    folder = out_root / "neg-no-output"
    folder.mkdir(parents=True, exist_ok=True)
    code, err = run_child(repo, "no-output-mode", folder)
    control("missing-output-nonzero", code not in (0,),
            {"exit": code, "stderr": err[-80:]})

    results["elapsed_s"] = round(time.monotonic() - started, 2)
    summary = out_root / "c02-summary.json"
    exit_code = lab.fail_nonzero(results, summary)
    print(f"summary -> {summary} exit={exit_code}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
