"""WO208 closeout lab finalization — C07 bounded CLOSED transition model.

S2/S3 finalization (repair of review N2): transitions are CLOSED over the
declared four-axis schema, the first execution counts its effect, duplicate
effects are observable, and the checker validates ``next_state`` instead of
discarding it. Execution AND completion both require the model's CURRENT
authorization and an eligible job state; COMPLETE is a legal vocabulary
action while COMPLETE_UNMODELED is the unsupported-action counterexample.

  state = (ownership, effect, checkpoint, job)   # ALL FOUR AXES ALWAYS
  action in {EXECUTE_ONCE, CONSUME_EVENT, RECOVER, REFUSE, NOOP, COMPLETE}

Invariants (each with a NAMED mutant; every mutant must be DETECTED):

  I1 execution authority: EXECUTE_ONCE with STALE ownership, with a
     BLOCKED job, or when an effect may already have landed is a violation.
  I1c completion authority: COMPLETE with STALE ownership is a violation.
  I2 no fabricated checkpoint/job-completion from intent/error alone.
  I3 contradictory identity never completes (PRESENT_DIVERGENT).
  I4 terminal same-exact-job repeat is a no-op.
  I5 current+unstarted+review can progress (bounded liveness, explicitly
     NOT full-lifecycle: blocked/recover stops are counted availability
     losses; the real-store positive lifecycle proof is C03, not this model).
  I6 unsupported action is rejected (COMPLETE_UNMODELED counterexample).
  I7 transition closure: every supported transition returns a valid
     four-axis state and an exact effect count (first execution adds ONE).

Traces (S3): bounded 2–4 step sequences exercise the live path
(execute → consume → complete), the blocked path, the stale path and the
duplicate-effect hazard; their outcomes are recorded in the summary.

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

AXES = (OWNERSHIP, EFFECT, CHECKPOINT, JOB)


def _valid_state(state) -> bool:
    return (
        isinstance(state, tuple) and len(state) == 4
        and state[0] in OWNERSHIP and state[1] in EFFECT
        and state[2] in CHECKPOINT and state[3] in JOB
    )


def transition(state, action):
    """Return (next_state, effects_added, checkpoint_fabricated, completed).

    CLOSED over the four-axis schema (S2/I7): next_state is always a valid
    4-tuple; feeding one step's output into the next transition works.
    effects_added counts NEW external effects truthfully — the FIRST
    execution adds ONE; executing again when an effect may already have
    landed adds another (duplicates must be observable, not hidden).
    Invalid (state, action) tuples raise ValueError explicitly.
    """
    if not _valid_state(state):
        raise ValueError(f"state must be a 4-axis tuple, got {state!r}")
    if action not in ACTIONS:
        raise ValueError(f"unsupported action {action!r} (vocabulary: {ACTIONS})")
    ownership, effect, checkpoint, job = state
    if job == "TERMINAL_COMPLETE":
        return state, 0, False, False  # nothing changes terminal (I4 no-op)
    if action == "EXECUTE_ONCE":
        # an EXECUTE always lands an effect in this model: the first one
        # (NOT_STARTED -> APPLIED_NO_RECEIPT) counts ONE; a repeat while an
        # effect may already have landed counts another observable duplicate.
        next_effect = "APPLIED_NO_RECEIPT" if effect == "NOT_STARTED" else effect
        return (ownership, next_effect, checkpoint, job), 1, False, False
    if action == "CONSUME_EVENT":
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
        return "REFUSE"  # blocked job: not executable (I1 eligible-state)
    return "RECOVER"  # effect may have landed, checkpoint absent


def check_policy(policy_fn, allow_unsupported=False):
    """Evaluate invariants over the full state space for a policy."""
    violations = {f"I{i}": [] for i in ("1", "1c", "2", "3", "4", "5", "6", "7")}
    states = list(itertools.product(*AXES))
    for state in states:
        ownership, effect, checkpoint, job = state
        action = policy_fn(state)
        if action not in ACTIONS:
            violations["I6"].append({"state": state, "action": action})
            continue
        next_state, effects_added, fabricated, completed = transition(state, action)
        # I7 closure: the returned state must be schema-valid (validated,
        # never discarded) — a malformed transition is itself a violation.
        if not _valid_state(next_state):
            violations["I7"].append({"state": state, "action": action,
                                     "next_state": next_state})
            continue
        if action == "EXECUTE_ONCE" and (
                ownership == "STALE" or job == "NONTERMINAL_BLOCKED"
                or effect in ("ATTEMPTED_UNKNOWN", "APPLIED_RECEIPT", "APPLIED_NO_RECEIPT")):
            violations["I1"].append({"state": state, "action": action})
        if action == "COMPLETE" and ownership == "STALE":
            violations["I1c"].append({"state": state, "action": action})
        if fabricated:
            violations["I2"].append({"state": state, "action": action})
        if completed and checkpoint == "PRESENT_DIVERGENT":
            violations["I3"].append({"state": state, "action": action})
        if job == "TERMINAL_COMPLETE" and action not in ("NOOP",):
            violations["I4"].append({"state": state, "action": action})
    live = [("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW")]
    for state in live:
        if policy_fn(state) not in ("EXECUTE_ONCE",):
            violations["I5"].append({"state": state, "action": policy_fn(state)})
    return violations


# ── named mutants (each violates exactly one invariant by design) ─────────

def mutant_duplicate_unknown_retry(state):
    ownership, effect, checkpoint, job = state
    if (effect == "ATTEMPTED_UNKNOWN" and checkpoint == "ABSENT"
            and job == "NONTERMINAL_REVIEW"):
        return "EXECUTE_ONCE"  # I1: effect may have landed
    return decide_conservative(state)


def mutant_stale_owner_effect(state):
    ownership, effect, checkpoint, job = state
    if (ownership == "STALE" and effect == "NOT_STARTED"
            and checkpoint == "ABSENT" and job == "NONTERMINAL_REVIEW"):
        return "EXECUTE_ONCE"  # I1: stale owner performs effect
    return decide_conservative(state)


def mutant_blocked_job_execute(state):
    # I1 eligible-state: the review's counterexample — execute a BLOCKED job
    if state == ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_BLOCKED"):
        return "EXECUTE_ONCE"
    return decide_conservative(state)


def mutant_stale_owner_complete(state):
    # I1c completion authority: the review's counterexample — stale owner
    # completes with an exact checkpoint and an applied effect
    if state == ("STALE", "APPLIED_RECEIPT", "PRESENT_EXACT", "NONTERMINAL_REVIEW"):
        return "COMPLETE"
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
    # I6: COMPLETE_UNMODELED is outside the vocabulary (COMPLETE itself is
    # a legal action; the UNMODELED variant is the counterexample)
    if state == ("CURRENT", "ATTEMPTED_UNKNOWN", "ABSENT", "NONTERMINAL_REVIEW"):
        return "COMPLETE_UNMODELED"
    return decide_conservative(state)


MUTANTS = {
    "duplicate-unknown-retry": (mutant_duplicate_unknown_retry, "I1"),
    "stale-owner-effect": (mutant_stale_owner_effect, "I1"),
    "blocked-job-execute": (mutant_blocked_job_execute, "I1"),
    "stale-owner-complete": (mutant_stale_owner_complete, "I1c"),
    "fabricated-checkpoint-complete": (mutant_fabricated_checkpoint, "I2"),
    "contradictory-completion": (mutant_contradictory_completion, "I3"),
    "terminal-repeated-effect": (mutant_terminal_repeated_effect, "I4"),
    "unjustified-initial-blocking": (mutant_unjustified_blocking, "I5"),
    "unsupported-action-vocabulary": (mutant_unsupported_action, "I6"),
}


# ── S3: bounded traces over the model ──────────────────────────────────────

def run_trace(start, actions):
    """Execute a bounded trace; return per-step facts + final summary.

    Each step records (action, next_state, effects_added, fabricated,
    completed). The trace ABORTS with an 'aborted' marker when a
    transition raises (e.g. unsupported action fed to the model)."""
    steps = []
    state = start
    total_effects = 0
    for action in actions:
        try:
            nxt, added, fabricated, completed = transition(state, action)
        except ValueError as exc:
            steps.append({"action": action, "aborted": str(exc)})
            break
        steps.append({"action": action, "next_state": list(nxt),
                      "effects_added": added, "fabricated": fabricated,
                      "completed": completed})
        total_effects += added
        state = nxt
    return {"start": list(start), "steps": steps, "total_effects": total_effects,
            "final_state": list(state)}


TRACES = {
    # live bounded happy path: first execute lands ONE effect, then the
    # bounded recovery stop (completion is NOT attempted without a
    # checkpoint — full real-store lifecycle liveness is C03's proof).
    "live-execute-recover": (
        ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW"),
        ["EXECUTE_ONCE", "RECOVER"],
        {"total_effects": 1, "final_job": "NONTERMINAL_REVIEW"}),
    # live completion path: exact checkpoint consumed, legal completion,
    # terminal repeat is a no-op (I4) — three steps, zero new effects.
    "live-consume-complete-noop": (
        ("CURRENT", "APPLIED_RECEIPT", "PRESENT_EXACT", "NONTERMINAL_REVIEW"),
        ["CONSUME_EVENT", "COMPLETE", "NOOP"],
        {"total_effects": 0, "final_job": "TERMINAL_COMPLETE"}),
    # adversarial: completion attempted WITHOUT a checkpoint — the model
    # records the fabrication truthfully instead of granting the terminal
    # state (final job stays nonterminal; total effects stays one).
    "adversarial-unbacked-completion-refused": (
        ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW"),
        ["EXECUTE_ONCE", "CONSUME_EVENT", "COMPLETE"],
        {"total_effects": 1, "final_job": "NONTERMINAL_REVIEW"}),
    # duplicate-effect hazard made observable: two executes add TWO effects
    # (the policy forbids this; the model must not hide the count).
    "duplicate-effect-observable": (
        ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW"),
        ["EXECUTE_ONCE", "EXECUTE_ONCE"],
        {"total_effects": 2, "final_job": "NONTERMINAL_REVIEW"}),
    # blocked job: refuse keeps availability loss bounded; executing anyway
    # aborts nothing but is an I1 violation the checker catches.
    "blocked-refuse": (
        ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_BLOCKED"),
        ["REFUSE"],
        {"total_effects": 0, "final_job": "NONTERMINAL_BLOCKED"}),
    # stale owner: refuse; completing anyway is caught by I1c.
    "stale-refuse": (
        ("STALE", "APPLIED_RECEIPT", "PRESENT_EXACT", "NONTERMINAL_REVIEW"),
        ["REFUSE"],
        {"total_effects": 0, "final_job": "NONTERMINAL_REVIEW"}),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    out_root = Path(args.output_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    states = list(itertools.product(*AXES))
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

    # S2 regression checks (the review's exact counterexamples, now closed)
    s = ("CURRENT", "NOT_STARTED", "ABSENT", "NONTERMINAL_REVIEW")
    n, added, _, _ = transition(s, "EXECUTE_ONCE")
    closure_ok = _valid_state(n) and added == 1
    chained = transition(n, "RECOVER")  # must not raise
    chained_ok = _valid_state(chained[0])
    s2_regression = {
        "expected": closure_ok and chained_ok,
        "first_execute_adds_one_effect": added == 1,
        "next_state_is_four_axis": _valid_state(n),
        "chained_recover_works": chained_ok,
        "chained_next_state": list(chained[0]),
    }
    print(("PASS " if s2_regression["expected"] else "FAIL ") + "s2-closure-regression")

    # S3 bounded traces
    trace_report = {}
    traces_ok = True
    for name, (start, actions, want) in TRACES.items():
        trace = run_trace(start, actions)
        ok = (trace["total_effects"] == want["total_effects"]
              and trace["final_state"][3] == want["final_job"])
        traces_ok = traces_ok and ok
        trace_report[name] = {**trace, "want": want, "expected": ok}
        print(("PASS " if ok else "FAIL ") + f"trace:{name}")

    results = {
        "state_count": len(states),
        "axes": {"ownership": OWNERSHIP, "effect": EFFECT,
                 "checkpoint": CHECKPOINT, "job": JOB},
        "action_vocabulary": ACTIONS,
        "complete_vs_unmodeled": (
            "COMPLETE is a legal vocabulary action (I1c/I2/I3 constrain it); "
            "COMPLETE_UNMODELED is outside the vocabulary and rejected by I6"),
        "conservative_policy_clean": {"expected": conservative_clean,
                                      "violations": {k: len(v) for k, v in conservative.items()}},
        "s2_closure_regression": s2_regression,
        "traces": trace_report,
        "mutants": mutant_report,
        "all_mutants_caught": {"expected": mutants_all_caught},
        "bounded_availability_note": (
            "I5 covers ONLY the initial progress tuple; RECOVER/REFUSE stops "
            "are bounded availability losses. Full real-store lifecycle "
            "liveness is proven by the C03 positive suite, not this model"),
        "ack_axis_note": ("acknowledgment RECEIVED/LOST is NOT modeled as changing durable "
                          "knowledge: the C03 experiments prove the same caller-visible error "
                          "follows committed and uncommitted writes, so counting ack tuples "
                          "would duplicate evidence, not add assurance"),
        "oracle_assumption": ("synthetic oracle: transition() is a MODEL of a generic "
                              "executor contract, not the production GoalCloseoutExecutor; "
                              "actual executor behavior is proven by C02/C03/C05/C06 against "
                              "the real store"),
        "exclusions": ("no power-loss durability, no cross-host coordination, no unbounded "
                       "liveness"),
        "elapsed_s": round(time.monotonic() - started, 2),
    }
    summary = out_root / "c07-summary.json"
    payload = dict(results)
    exit_code = 0 if (conservative_clean and mutants_all_caught
                      and s2_regression["expected"] and traces_ok) else 1
    payload["exit_code"] = exit_code
    summary.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"states={len(states)} conservative_clean={conservative_clean} "
          f"all_mutants_caught={mutants_all_caught} "
          f"s2={s2_regression['expected']} traces={traces_ok} -> exit={exit_code}")
    print(f"summary -> {summary}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
