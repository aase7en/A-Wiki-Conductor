"""WO208 closeout lab repair — C07 bounded TRANSITION model (R3 repair).

R3 repair: this is no longer a bare input-tuple table. It is a small
action-validating TRANSITION model:

  state = (ownership, effect, checkpoint, job)
  action in {EXECUTE_ONCE, CONSUME_EVENT, RECOVER, REFUSE, NOOP, COMPLETE}
  transition(state, action) -> state'   (models effect, checkpoint AND job)

Invariants are defined over OBSERVABLE state changes and each has a NAMED
mutant policy that violates it; every mutant must be DETECTED (top-level
exit nonzero if any mutant survives, if an unsupported action is accepted,
or if the conservative policy itself violates anything):

  I1 no effect without current authorization / no second effect
     when one may already have landed (stale-owner + duplicate classes)
     (effect in {ATTEMPTED_UNKNOWN, APPLIED_*} and action EXECUTE_ONCE)
  I2 no fabricated checkpoint/job-completion from intent/error alone
     (action CONSUME/COMPLETE requires a PRESENT_EXACT checkpoint or a
     committed transition marker in the transition itself, never from error)
  I3 contradictory identity never completes (PRESENT_DIVERGENT -> complete)
  I4 terminal same-exact-job repeat is a no-op
  I5 current+unstarted can progress (liveness, bounded)
  I6 unsupported action is rejected (e.g. injected "COMPLETE" outside
     vocabulary — the review's counterexample)

Acknowledgment axis: modeled as NOT affecting durable knowledge (the error
return alone cannot), documented as an equivalence rather than counted twice.

Usage: python c07_model.py --output-root D  (exit 0 = all hold + mutants caught)
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_common as lab  # noqa: E402

OWNERSHIP = ["CURRENT", "STALE"]
EFFECT = ["NOT_STARTED", "ATTEMPTED_UNKNOWN", "APPLIED_RECEIPT", "APPLIED_NO_RECEIPT"]
CHECKPOINT = ["ABSENT", "PRESENT_EXACT", "PRESENT_DIVERGENT"]
JOB = ["NONTERMINAL_REVIEW", "NONTERMINAL_BLOCKED", "TERMINAL_COMPLETE"]

ACTIONS = ["EXECUTE_ONCE", "CONSUME_EVENT", "RECOVER", "REFUSE", "NOOP", "COMPLETE"]


def transition(state, action):
    """Return (next_state, effects_added, checkpoint_fabricated, completed).

    Models the observable consequence of taking `action` in `state` under a
    generic executor contract. effects_added counts NEW external effects.
    checkpoint_fabricated marks a checkpoint/complete claim that was not
    backed by a committed durable write in this action.
    """
    ownership, effect, checkpoint, job = state
    if job == "TERMINAL_COMPLETE":
        return state, 0, False, False  # nothing changes terminal
    if action == "EXECUTE_ONCE":
        next_effect = "APPLIED_NO_RECEIPT" if effect == "NOT_STARTED" else "DUP"
        return (ownership, next_effect if next_effect != "DUP" else effect,
                checkpoint), (0 if effect == "NOT_STARTED" else 1), False, False
    if action == "CONSUME_EVENT":
        # consuming an existing exact event: no new effect, no fabrication
        if checkpoint != "PRESENT_EXACT":
            return state, 0, True, False  # fabricated consume
        return state, 0, False, False
    if action == "COMPLETE":
        if checkpoint == "PRESENT_EXACT" and effect in ("APPLIED_RECEIPT",
                                                        "APPLIED_NO_RECEIPT"):
            return (ownership, effect, checkpoint, "TERMINAL_COMPLETE"), 0, False, True
        return state, 0, True, True  # completion claimed without durable backing
    # RECOVER / REFUSE / NOOP: no state change, no effects
    return state, 0, False, False


def decide_conservative(state):
    ownership, effect, checkpoint, job = state
    if job == "TERMINAL_COMPLETE":
        return "NOOP"
    if checkpoint == "PRESENT_DIVERGENT":
        return "RECOVER"
    if ownership == "STALE":
        return "REFUSE"
    if checkpoint == "PRESENT_EXACT":
        return "CONSUME_EVENT" if effect != "NOT_STARTED" else "RECOVER"
    if effect == "NOT_STARTED":
        if job == "NONTERMINAL_REVIEW":
            return "EXECUTE_ONCE"
        return "REFUSE"  # blocked job: not executable
    return "RECOVER"  # effect may have landed, checkpoint absent


def check_policy(policy_fn, allow_unsupported=False):
    """Evaluate invariants over the full state space for a policy."""
    violations = {f"I{i}": [] for i in range(1, 7)}
    states = list(itertools.product(OWNERSHIP, EFFECT, CHECKPOINT, JOB))
    for state in states:
        ownership, effect, checkpoint, job = state
        action = policy_fn(state)
        if action not in ACTIONS and not allow_unsupported:
            violations["I6"].append({"state": state, "action": action})
            continue
        if action not in ACTIONS:
            # unsupported action accepted by an unchecked caller: model its
            # effect as fabricating authority (worst case for I6)
            violations["I6"].append({"state": state, "action": action})
            continue
        next_state, effects_added, fabricated, completed = transition(state, action)
        if (effects_added > 0 and effect != "NOT_STARTED") or (
                action == "EXECUTE_ONCE" and ownership == "STALE"):
            violations["I1"].append({"state": state, "action": action})
        if fabricated:
            violations["I2"].append({"state": state, "action": action})
        if completed and checkpoint == "PRESENT_DIVERGENT":
            violations["I3"].append({"state": state, "action": action})
        if job == "TERMINAL_COMPLETE" and action not in ("NOOP",):
            violations["I4"].append({"state": state, "action": action})
    live = [("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW")]
    for state in live:
        if policy_fn(state) not in ("EXECUTE_ONCE",):
            violations["I5"].append({"state": state,
                                     "action": policy_fn(state)})
    return violations


# ── named mutants (each violates exactly one invariant by design) ─────────

def mutant_duplicate_unknown_retry(state):
    ownership, effect, checkpoint, job = state
    if (effect == "ATTEMPTED_UNKNOWN" and checkpoint == "ABSENT"
            and job == "NONTERMINAL_REVIEW"):
        return "EXECUTE_ONCE"  # I1 violation: effect may have landed
    return decide_conservative(state)


def mutant_stale_owner_effect(state):
    ownership, effect, checkpoint, job = state
    if (ownership == "STALE" and effect == "NOT_STARTED"
            and checkpoint == "ABSENT" and job == "NONTERMINAL_REVIEW"):
        return "EXECUTE_ONCE"  # I-ownership: stale owner performs effect
    return decide_conservative(state)


def mutant_fabricated_checkpoint(state):
    ownership, effect, checkpoint, job = state
    if (effect == "APPLIED_NO_RECEIPT" and checkpoint == "ABSENT"
            and job == "NONTERMINAL_REVIEW"):
        return "COMPLETE"  # I2: completion without durable checkpoint
    return decide_conservative(state)


def mutant_contradictory_completion(state):
    ownership, effect, checkpoint, job = state
    if checkpoint == "PRESENT_DIVERGENT" and job == "NONTERMINAL_REVIEW":
        return "COMPLETE"  # I3: contradictory identity completes
    return decide_conservative(state)


def mutant_terminal_repeated_effect(state):
    ownership, effect, checkpoint, job = state
    if job == "TERMINAL_COMPLETE":
        return "EXECUTE_ONCE"  # I4: terminal repeat performs effect
    return decide_conservative(state)


def mutant_unjustified_blocking(state):
    # I5 liveness mutant: refuse the canonical progress state
    if state == ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW"):
        return "REFUSE"
    return decide_conservative(state)


def mutant_unsupported_action(state):
    # I6: the review's counterexample — inject COMPLETE outside vocabulary
    if state == ("CURRENT", "ATTEMPTED_UNKNOWN", "ABSENT", "NONTERMINAL_REVIEW"):
        return "COMPLETE_UNMODELED"
    return decide_conservative(state)


MUTANTS = {
    "duplicate-unknown-retry": (mutant_duplicate_unknown_retry, "I1"),
    "stale-owner-effect": (mutant_stale_owner_effect, "I1"),
    "fabricated-checkpoint-complete": (mutant_fabricated_checkpoint, "I2"),
    "contradictory-completion": (mutant_contradictory_completion, "I3"),
    "terminal-repeated-effect": (mutant_terminal_repeated_effect, "I4"),
    "unjustified-initial-blocking": (mutant_unjustified_blocking, "I5"),
    "unsupported-action-vocabulary": (mutant_unsupported_action, "I6"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    out_root = Path(args.output_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    states = list(itertools.product(OWNERSHIP, EFFECT, CHECKPOINT, JOB))
    conservative = check_policy(decide_conservative)
    conservative_clean = all(not v for v in conservative.values())

    mutant_report = {}
    mutants_all_caught = True
    for name, (policy, expected_invariant) in MUTANTS.items():
        violations = check_policy(policy, allow_unsupported=(name == "unsupported-action-vocabulary"))
        caught = [inv for inv, hits in violations.items() if hits]
        ok = expected_invariant in caught
        mutants_all_caught = mutants_all_caught and ok
        mutant_report[name] = {
            "expected_violation": expected_invariant,
            "detected_violations": caught,
            "expected": ok,
            "example": (violations[expected_invariant][0]
                        if violations.get(expected_invariant) else None),
        }
        print(("PASS " if ok else "FAIL ") + f"mutant:{name} -> {caught}")

    results = {
        "state_count": len(states),
        "axes": {"ownership": OWNERSHIP, "effect": EFFECT,
                 "checkpoint": CHECKPOINT, "job": JOB},
        "action_vocabulary": ACTIONS,
        "conservative_policy_clean": {"expected": conservative_clean,
                                      "violations": {k: len(v) for k, v in conservative.items()}},
        "mutants": mutant_report,
        "all_mutants_caught": {"expected": mutants_all_caught},
        "ack_axis_note": ("acknowledgment RECEIVED/LOST is NOT modeled as changing durable "
                          "knowledge: the C03 experiments prove the same caller-visible error "
                          "follows committed and uncommitted writes, so counting ack tuples "
                          "would duplicate evidence, not add assurance"),
        "exclusions": ("no power-loss durability, no cross-host coordination, no unbounded "
                       "liveness: RECOVER/REFUSE stops are counted as bounded availability "
                       "losses, separate from safety"),
        "elapsed_s": round(time.monotonic() - started, 2),
    }
    results["expected"] = None  # marker; leaf checks decide exit
    summary = out_root / "c07-summary.json"
    payload = dict(results)
    payload.pop("expected")
    exit_code = 0 if (conservative_clean and mutants_all_caught) else 1
    payload["exit_code"] = exit_code
    summary.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"states={len(states)} conservative_clean={conservative_clean} "
          f"all_mutants_caught={mutants_all_caught} -> exit={exit_code}")
    print(f"summary -> {summary}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
