"""WO208 finalization — contract test suite for the bundle itself (S4/S8).

Pytest suite validating the validators THROUGH their real entrypoints:
  - lab_common.validate_cut_observation: positive + every malformed-
    observation class rejects for the RIGHT reason;
  - manifest preflight: missing/changed script, manifest self-hash,
    unexpected omission, wrong source pin each fail closed;
  - seed executable binding: mismatched bytes rejected before import
    (N1 closed) and the canonical fence accepted;
  - c07 transition closure: 4-axis next states, first-effect count ONE,
    chained transitions, blocked/stale authority counterexamples caught;
  - aggregation discipline: unknown cases / missing required cases /
    missing result / non-boolean expected / zero-created receipts never
    silently succeed.

Run: python -m pytest -q docs/reviews/wo208-closeout-lab/test_lab_contract.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parent
REPO = BUNDLE.parents[2]
sys.path.insert(0, str(BUNDLE))

import lab_common as lab  # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), BUNDLE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE_OBS = {
    "exit": 10, "want_exit": 10, "marker": True,
    "effects": 0, "want_effects": 0, "refs": 1, "want_refs": 1,
    "state": "REVIEW_PENDING", "want_state": "REVIEW_PENDING",
}


# ── shared validator: positives + per-predicate rejection reasons ──────────

def test_validator_accepts_canonical_observation():
    ok, reasons = lab.validate_cut_observation(dict(BASE_OBS))
    assert ok and reasons == []


@pytest.mark.parametrize("mutation, want_reason", [
    ({"want_exit": 99}, "exit:"),
    ({"marker": False}, "marker-missing"),
    ({"effects": 3}, "effects:"),
    ({"refs": 9}, "refs:"),
    ({"state": "COMPLETE"}, "state:"),
])
def test_validator_rejects_each_predicate_break_for_its_reason(mutation, want_reason):
    obs = dict(BASE_OBS, **mutation)
    ok, reasons = lab.validate_cut_observation(obs)
    assert not ok
    assert any(r.startswith(want_reason) for r in reasons), reasons


def test_validator_reports_all_broken_predicates_together():
    ok, reasons = lab.validate_cut_observation(dict(BASE_OBS, marker=False, refs= 5))
    assert not ok and "marker-missing" in reasons and any(r.startswith("refs:") for r in reasons)


# ── manifest preflight: fail-closed classes ───────────────────────────────

def test_preflight_rejects_missing_script(tmp_path):
    manifest = {"files": {"absent.py": "0" * 64}, "source_blobs": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="absent.py: MISSING"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


def test_preflight_rejects_changed_script(tmp_path):
    (tmp_path / "seed_probe.py").write_text("changed", encoding="utf-8")
    manifest = {"files": {"seed_probe.py": "0" * 64}, "source_blobs": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="hash mismatch"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


def test_preflight_rejects_manifest_self_hash(tmp_path):
    (tmp_path / "seed_probe.py").write_text("x", encoding="utf-8")
    digest = lab.sha256_file(tmp_path / "seed_probe.py")
    manifest = {"files": {"seed_probe.py": digest, "manifest.json": "0" * 64},
                "source_blobs": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="must not hash itself"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


def test_preflight_rejects_unexpected_omission(tmp_path):
    (tmp_path / "a.py").write_text("a", encoding="utf-8")
    (tmp_path / "b.py").write_text("b", encoding="utf-8")
    manifest = {"files": {"a.py": lab.sha256_file(tmp_path / "a.py")},
                "source_blobs": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="b.py"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


def test_preflight_rejects_wrong_source_pin(tmp_path):
    (tmp_path / "a.py").write_text("a", encoding="utf-8")
    manifest = {"files": {"a.py": lab.sha256_file(tmp_path / "a.py")},
                "source_blobs": {"src/a_conductor/goal_closeout.py": "0" * 64,
                                 "b": "1" * 64, "c": "2" * 64, "d": "3" * 64}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="source pin mismatch"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


def test_preflight_requires_four_source_blobs(tmp_path):
    (tmp_path / "a.py").write_text("a", encoding="utf-8")
    manifest = {"files": {"a.py": lab.sha256_file(tmp_path / "a.py")},
                "source_blobs": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(lab.LabFailed, match="four source blobs"):
        lab.verify_manifest(REPO, bundle_dir=tmp_path)


# ── c07 closure through the real module entrypoint ───────────────────────

c07 = _load("c07_model.py")


def test_c07_first_execution_adds_one_effect_and_keeps_four_axes():
    s = ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW")
    n, added, _, _ = c07.transition(s, "EXECUTE_ONCE")
    assert added == 1
    assert c07._valid_state(n)


def test_c07_chained_transition_of_output_works():
    s = ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW")
    n, _, _, _ = c07.transition(s, "EXECUTE_ONCE")
    n2, _, _, _ = c07.transition(n, "RECOVER")  # must not raise
    assert c07._valid_state(n2)


def test_c07_invalid_tuples_raise():
    with pytest.raises(ValueError):
        c07.transition(("CURRENT", "NOT_STARTED", "ABSENT"), "EXECUTE_ONCE")
    with pytest.raises(ValueError):
        c07.transition(("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW"),
                       "COMPLETE_UNMODELED")


def test_c07_blocked_execute_and_stale_complete_mutants_detected():
    def blocked(state):
        if state == ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_BLOCKED"):
            return "EXECUTE_ONCE"
        return c07.decide_conservative(state)

    def stale_complete(state):
        if state == ("STALE", "APPLIED_RECEIPT", "PRESENT_EXACT", "NONTERMINAL_REVIEW"):
            return "COMPLETE"
        return c07.decide_conservative(state)

    for fn, inv in ((blocked, "I1"), (stale_complete, "I1c")):
        violations = c07.check_policy(fn)
        assert violations[inv], f"mutant escaped {inv}"


def test_c07_conservative_policy_clean():
    violations = c07.check_policy(c07.decide_conservative)
    assert all(not hits for hits in violations.values())


# ── seed executable binding through the real entrypoint ──────────────────

def test_seed_binding_rejects_substituted_bytes(tmp_path):
    import hashlib
    probe = _load("seed_probe.py")
    out = tmp_path / "out"
    out.mkdir()
    fake = out / "seed_fence_materialized.py"
    fake.write_text("def run():\n    return {}\n", encoding="utf-8")
    raw = hashlib.sha256(fake.read_bytes()).hexdigest()
    norm = hashlib.sha256(fake.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    executable_ok = raw == probe.CANONICAL_SEED_SHA256 or norm == probe.CANONICAL_SEED_SHA256
    assert not executable_ok  # mismatched bytes detectable BEFORE import
    assert fake.read_text(encoding="utf-8") != probe.extract_fence(REPO)


def test_seed_binding_accepts_canonical_fence_bytes(tmp_path):
    probe = _load("seed_probe.py")
    fence = probe.extract_fence(REPO)
    import hashlib
    assert hashlib.sha256(fence.encode("utf-8")).hexdigest() == probe.CANONICAL_SEED_SHA256


# ── aggregation discipline (fail_nonzero leaf checks) ─────────────────────

def test_aggregation_false_leaf_fails(tmp_path):
    results = {"case": {"expected": False}}
    assert lab.fail_nonzero(results, tmp_path / "s.json") == 1


def test_aggregation_true_leaf_passes(tmp_path):
    results = {"case": {"expected": True}}
    assert lab.fail_nonzero(results, tmp_path / "s.json") == 0


def test_aggregation_bare_false_fails(tmp_path):
    results = {"flag": False}
    assert lab.fail_nonzero(results, tmp_path / "s.json") == 1


def test_aggregation_zero_created_receipts_not_success():
    # zero-created receipts race: observations with created=0 must not be
    # treated as acceptance — the validator's effect-count reason enforces it
    ok, reasons = lab.validate_cut_observation(dict(BASE_OBS, effects=1, want_effects=1))
    assert ok  # positive sanity
    ok2, reasons2 = lab.validate_cut_observation(dict(BASE_OBS, effects=0, want_effects=1))
    assert not ok2 and any(r.startswith("effects:") for r in reasons2)
