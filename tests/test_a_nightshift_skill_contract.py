"""WO-P1-520 — A-NightShift skill contract regression tests.

Semantic assertions over the A-NightShift overlay and its canonical
overnight-supervisor template. These tests fail if a future edit removes:
- invocation-vs-explanation activation ("use A-NightShift" /
  "ใช้ A-NightShift" / "A-NightShift ตาม Roadmap" route the full overnight
  profile; explanatory mentions never activate work);
- the fail-closed overlay on accepted A-FastTask + A-Faster (no second
  control plane, no new authority);
- the RECOVER -> RECONCILE -> HARVEST ordering before any new dispatch;
- the inherited global WIP budget (3 mutable + 1 independent review,
  one mutable hotspot = one mutation owner);
- model-role separation (GLM-5.3 MAX heavy R2/R3, Flash read-only assist,
  TypeSafe-JEV advisory only, nesting Codex -> GLM -> JEV);
- the low-cost Codex traffic-controller/supervisor role with no permanent
  product-model pin, LOW default effort, bounded escalation classes, and
  fail-closed mid-goal model/effort changes;
- quiet/event-driven waiting with only bounded infrequent polling;
- dispatch-first/harvest-later refill that never manufactures work or burns
  quota for its own sake;
- the #517 successor alignment: active NightShift implies
  A_FASTER_ACTIVE=YES after base activation succeeds, and the five
  A-Faster utilization receipt markers (A_FASTER_ACTIVE, FANOUT_TARGET,
  UNUSED_SAFE_CAPACITY, A_FASTER_UNDERUTILIZED, AUTO_REFILL_REQUIRED)
  are consumed/preserved verbatim from accepted A-Faster semantics with
  no second utilization authority and no parallel refill state machine;
- quota refresh before every material GLM dispatch and QUOTA_UNKNOWN !=
  RATE_LIMITED;
- no blind redispatch of RUNNING/UNKNOWN/INTERRUPTED/TERMINAL_UNHARVESTED;
- the collision-safe per-run ephemeral supervisor contract outside Git under
  the OS temp dir, recorded in an A_NIGHTSHIFT receipt via a compact /goal
  pointer;
- exact-path-only cleanup at terminal state (no wildcard/glob deletion);
- the frozen stop gates;
- the canonical tracked template that never instructs committing the
  ephemeral copy;
- the attempt-0003 premature-terminal regression repair (issue #520):
  STALLED and WAITING_EXTERNAL recheckable external dependencies are
  waiting states, never terminal Goal states or stop gates;
  RECHECK_ACTION_EXISTS forbids NO_SAFE_NEXT_ACTION;
  NO_MUTATION_AVAILABLE is not NO_SAFE_NEXT_ACTION; terminal
  NO_SAFE_NEXT_ACTION requires the exhaustive TRUE_NO_SAFE_NEXT_ACTION
  absence proof; the WAITING_EXTERNAL lifecycle keeps the Goal alive with
  ownership/context and exact dependency/job identity; cleanup is
  forbidden for recheckable non-terminal states and a "blocked" label
  alone is never cleanup authority; ambiguous terminal conversion must
  escalate or fail closed as WAITING_EXTERNAL; the 2026-09-23 CI incident
  outcome vector is pinned verbatim; and no new scheduler, timer, or
  state store is created;
- the attempt-0004 no-model-spin waiting regression repair (issue #520):
  WAITING_EXTERNAL with unchanged authoritative state never completes a
  model turn merely to report still waiting and never emits a
  user-visible repeated WAITING_EXTERNAL reply solely because a /goal
  continuation fired; the wait itself happens inside ONE foreground
  read-only blocking call bound to the exact dependency identity
  (gh run watch preferred, silent unchanged-wait output,
  WAIT_TOOL_TIMEOUT_RECHECK timeout fallback, no detached watcher or new
  scheduler/task store/state store); and the pinned 2026-09-23/24
  reply-spin incident vector with its state_changed=YES transition;
- the WO-P1-522 integrator-handoff / stale-terminal-pointer repair
  (issue #522): INTEGRATOR_ACTION_REQUIRED is not itself a stop gate and
  requires integrator-route classification (AVAILABLE / UNKNOWN /
  PROVEN_UNAVAILABLE) first; AVAILABLE => WAITING_INTEGRATOR,
  non-terminal, no cleanup, no human gate; UNKNOWN => recover/probe,
  never an invented human gate; PROVEN_UNAVAILABLE may derive
  HUMAN_ACTION_REQUIRED only when human invocation is actually
  necessary; terminal cleanup requires folding a compact final run
  record into an existing durable task authority first, and the
  ephemeral receipt alone is explicitly insufficient durable closeout; a
  CONTRACT_ABSENT entry recovers durable closeout by exact run id before
  classification — exact terminal+cleanup proof => STALE_TERMINAL_POINTER
  / GOAL_ALREADY_TERMINAL with SAFETY_BLOCK=FALSE,
  REMATERIALIZE=FORBIDDEN, REDISPATCH=FORBIDDEN,
  USER_VISIBLE_REPEAT_REPLY=FORBIDDEN; unproven absence stays
  fail-closed CONTRACT_ABSENT_UNKNOWN / SAFETY_BLOCK; and the existing
  WAITING_EXTERNAL / WAIT_TOOL_TIMEOUT_RECHECK / no-model-spin
  semantics remain unchanged;
- the WO-P1-522 attempt-0002 two-phase durable-closeout repair (Sol
  CHANGES_REQUIRED on issue #522): PRE_CLEANUP_FOLDED precedes the
  exact-path deletion and POST_CLEANUP_CONFIRMED follows successful
  deletion in the SAME existing durable authority, recording run id,
  exact deleted path, terminal classification, and cleanup result with
  no secrets and no log dumps; STALE_TERMINAL_POINTER /
  GOAL_ALREADY_TERMINAL requires POST_CLEANUP_CONFIRMED — cleanup
  intent alone is insufficient; delete failure or missing
  post-confirmation stays fail-closed/recoverable and never fabricates
  success; and all attempt-0001 F1/F2/F3 + WAITING_EXTERNAL /
  no-model-spin semantics remain unchanged.

Deliberately not a full-file snapshot: wording may evolve as long as the
semantic markers stay. WO-P1-520 attempt-0001; A-Faster utilization-marker
pins added at attempt-0002; premature-terminal regression pins (issue
#520 incident) added at attempt-0003; no-model-spin blocking-wait pins
(issue #520 reply-spin incident) added at attempt-0004; integrator-handoff
and stale-terminal-pointer pins (issue #522) added at WO-P1-522
attempt-0001; two-phase durable-closeout pins (issue #522 Sol finding)
added at WO-P1-522 attempt-0002.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "a-nightshift" / "SKILL.md"
REFERENCE = (
    ROOT / ".agents" / "skills" / "a-nightshift" / "references" / "overnight-supervisor.md"
)
WO = ROOT / "docs" / "work-orders" / "WO-P1-520-a-nightshift-skill.md"

_HEADING_RE = re.compile(r"^(?P<depth>#{2,4})\s+(?P<title>.+?)\s*$", re.MULTILINE)


def _read_strict(path: Path) -> str:
    # Strict UTF-8 decode is itself part of the WO520 verification matrix.
    return path.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    """Collapse whitespace so phrase assertions survive hard line wraps."""
    return re.sub(r"\s+", " ", text)


def _section(text: str, title_needle: str) -> str:
    """Return the body of the first section whose title contains the needle.

    The section extends to the next heading of the same or shallower depth,
    so ``###`` subsections below a ``##`` heading stay inside its body.
    """
    for match in _HEADING_RE.finditer(text):
        if title_needle.lower() in match.group("title").lower():
            depth = len(match.group("depth"))
            for later in _HEADING_RE.finditer(text, match.end()):
                if len(later.group("depth")) <= depth:
                    return text[match.end() : later.start()]
            return text[match.end() :]
    raise AssertionError(f"missing section containing {title_needle!r}")


def test_artifacts_exist_and_decode_strict_utf8() -> None:
    for path in (SKILL, REFERENCE, WO):
        assert path.is_file(), f"missing artifact: {path}"
        _read_strict(path)


def test_canonical_invocation_clauses_activate_full_profile() -> None:
    section = _section(_read_strict(SKILL), "Invocation contract")
    for clause in (
        '"use A-NightShift"',
        '"ใช้ A-NightShift"',
        '"A-NightShift ตาม Roadmap"',
    ):
        assert clause in section, f"canonical clause missing: {clause}"
    assert "overnight/operator-away continuation intent" in _norm(section)


def test_explanatory_mentions_do_not_activate() -> None:
    section = _norm(_section(_read_strict(SKILL), "Invocation contract"))
    assert "Explanatory mentions" in section
    assert "do not activate" in section


def test_overlay_on_accepted_bases_fails_closed() -> None:
    text = _read_strict(SKILL)
    assert "not a second control plane" in text
    assert "../a-faster/SKILL.md" in text
    assert "a-fasttask" in text
    assert "A_NIGHTSHIFT_BASE_MISSING_OR_CONFLICT" in text
    # Router/overlay boundary preserved: no new authority of its own.
    assert (
        "grants no task, claim, cleanup, provider, review, merge, "
        "or acceptance authority" in _norm(text)
    )


def test_recover_reconcile_harvest_precedes_new_dispatch() -> None:
    section = _norm(_section(_read_strict(SKILL), "Overnight loop"))
    assert "RECOVER -> RECONCILE -> HARVEST" in section
    assert "before any new dispatch" in section


def test_global_wip_budget_and_hotspot_ownership() -> None:
    text = _read_strict(SKILL)
    wip = _norm(_section(text, "Global WIP"))
    assert "3 mutable + 1 independent review" in wip
    assert "1 MUTABLE HOTSPOT = 1 MUTATION OWNER" in wip
    assert "never multiplied" in wip


def test_model_roles_and_max_normal_nesting() -> None:
    roles = _norm(_section(_read_strict(SKILL), "Model roles"))
    assert "GLM-5.3 MAX" in roles
    assert "R2/R3" in roles
    assert "GLM-5.3-Flash" in roles
    assert "read-only" in roles
    # TypeSafe-JEV stays advisory evidence, never authority.
    assert "advisory only" in roles
    assert "never" in roles and "authority" in roles
    # Maximum normal nesting is Codex -> GLM -> JEV.
    assert "Codex -> GLM -> JEV" in roles


def test_codex_is_low_cost_supervisor_not_primary_engineer() -> None:
    text = _read_strict(SKILL)
    codex = _norm(_section(text, "Codex supervisor"))
    combined = _norm(_section(text, "Model roles")) + " " + codex
    # Traffic controller / supervisor, never the engineer.
    assert "traffic controller" in combined or "traffic-controller" in combined
    assert "never the primary engineer" in codex
    # Selection policy: cheapest capable, LOW effort default.
    assert "smallest/cheapest currently available capable supervisor" in codex
    assert "LOW effort" in codex
    # Escalation is bounded to genuinely ambiguous classes.
    for escalation_class in ("ambiguous recovery", "collision", "authority", "acceptance"):
        assert escalation_class in codex, f"lost escalation class: {escalation_class}"
    # No permanent product-model pin; mid-goal changes fail closed.
    assert "Do not permanently pin a Codex product model name" in codex
    assert "cannot change mid-goal" in codex
    assert "fail closed" in codex
    assert "rather than" in codex and "inventing" in codex


def test_quiet_waiting_with_bounded_polling_fallback() -> None:
    section = _norm(_section(_read_strict(SKILL), "Quiet waiting"))
    assert "event-driven" in section
    assert "compact receipts" in section
    assert "bounded infrequent polling" in section


def test_fanout_refill_never_manufactures_work() -> None:
    section = _norm(_section(_read_strict(SKILL), "Fanout and refill"))
    assert "dispatch-first / harvest-later" in section
    assert "refill" in section
    assert "never manufacture work" in section
    assert "never burn quota for its own sake" in section


def test_afaster_utilization_markers_pinned_and_passed_through() -> None:
    skill = _read_strict(SKILL)
    ref = _read_strict(REFERENCE)
    markers = (
        "A_FASTER_ACTIVE",
        "FANOUT_TARGET",
        "UNUSED_SAFE_CAPACITY",
        "A_FASTER_UNDERUTILIZED",
        "AUTO_REFILL_REQUIRED",
    )
    # All five literal markers appear in the overlay and the template.
    for marker in markers:
        assert marker in skill, f"marker lost from SKILL.md: {marker}"
        assert marker in ref, f"marker lost from template: {marker}"
    # Semantics: consume/preserve verbatim, never recompute authority.
    fanout = _norm(_section(skill, "Fanout and refill"))
    assert "consumed, never recomputed" in fanout
    assert "verbatim" in fanout
    assert "no second utilization authority" in fanout
    assert "no parallel refill state machine" in fanout
    # Routing/receipt output carries the markers compactly.
    routing = _norm(_section(skill, "Routing output additions"))
    receipt = _norm(_section(ref, "Receipt (A_NIGHTSHIFT)"))
    for marker in markers:
        assert marker in routing, f"routing receipt lost marker: {marker}"
        assert marker in receipt, f"template receipt lost marker: {marker}"
    # The supervisor template carries the fields as pass-through
    # placeholders, resolved per the UNKNOWN-not-invented rules.
    assert "A_FASTER_ACTIVE={{A_FASTER_ACTIVE}}" in ref
    assert "FANOUT_TARGET={{FANOUT_TARGET}}" in ref
    assert "UNUSED_SAFE_CAPACITY={{UNUSED_SAFE_CAPACITY}}" in ref
    assert "A_FASTER_UNDERUTILIZED={{A_FASTER_UNDERUTILIZED}}" in ref
    assert "AUTO_REFILL_REQUIRED={{AUTO_REFILL_REQUIRED}}" in ref


def test_active_nightshift_implies_a_faster_active_yes() -> None:
    text = _norm(_read_strict(SKILL))
    assert "A_FASTER_ACTIVE=YES" in text
    assert "after base activation succeeds" in text
    # The overlay never fabricates or overrides the base marker itself.
    assert "never sets, clears, or fabricates" in text


def test_quota_refresh_before_each_material_glm_dispatch() -> None:
    section = _norm(_section(_read_strict(SKILL), "Quota gates"))
    assert "before every material GLM dispatch" in section
    assert "QUOTA_UNKNOWN" in section
    assert "not `RATE_LIMITED`" in section
    assert "never treated as unlimited" in section


def test_no_blind_redispatch_of_ambiguous_states() -> None:
    section = _norm(_section(_read_strict(SKILL), "No blind redispatch"))
    for state in ("RUNNING", "UNKNOWN", "INTERRUPTED", "TERMINAL_UNHARVESTED"):
        assert state in section, f"lost never-redispatch state: {state}"
    assert re.search(r"Never blindly redispatch", section)


def test_ephemeral_contract_outside_git_collision_safe() -> None:
    section = _norm(_section(_read_strict(SKILL), "Ephemeral per-run supervisor contract"))
    assert "outside Git" in section
    assert "OS temp" in section
    assert "collision-safe" in section
    # Compact /goal pointer points Codex at the exact ephemeral contract.
    assert "compact" in section
    assert "/goal" in section
    assert "ephemeral contract" in section
    # The exact ephemeral path is recorded in an A_NIGHTSHIFT receipt.
    assert "A_NIGHTSHIFT receipt" in section
    assert "exact ephemeral path" in section


def test_cross_platform_temp_roots_no_hardcoded_operator_machine() -> None:
    ref = _norm(_read_strict(REFERENCE))
    for surface in ("TMPDIR", "%TEMP%"):
        assert surface in ref, f"temp-root semantics lost: {surface}"
    skill = _norm(_read_strict(SKILL))
    assert (
        "never hard-code one operator machine" in skill
        or "never hard-code one operator machine" in ref
    )


def test_cleanup_exact_path_only_at_terminal_state() -> None:
    skill = _norm(_section(_read_strict(SKILL), "cleanup"))
    ref = _norm(_read_strict(REFERENCE))
    combined = skill + " " + ref
    assert "terminal state" in combined
    assert "harvested or durably checkpointed" in combined
    assert "exact path" in combined or "exact-path" in combined
    assert "wildcard" in combined
    assert "glob" in combined
    assert "Never" in combined and "glob" in combined


def test_stop_gates_are_frozen() -> None:
    skill = _norm(_section(_read_strict(SKILL), "Stop gates"))
    ref = _norm(_read_strict(REFERENCE))
    combined = skill + " " + ref
    for gate in (
        "HUMAN_ACTION_REQUIRED",
        "HUMAN_DECISION_REQUIRED",
        "AUTHORIZATION_REQUIRED",
        "SAFETY_BLOCK",
        "NO_SAFE_NEXT_ACTION",
    ):
        assert gate in combined, f"stop gate lost: {gate}"
    assert "Stop only on" in skill


def test_reference_is_canonical_tracked_template() -> None:
    skill = _norm(_read_strict(SKILL))
    ref = _read_strict(REFERENCE)
    # SKILL.md links the reference and defines materialization semantics.
    assert "references/overnight-supervisor.md" in skill
    assert "canonical tracked source" in skill
    assert "ephemeral per-run copy" in skill
    assert "exact recovered run facts/paths" in skill
    assert "Never commit the ephemeral copy" in skill
    # Template uses placeholders; unavailable facts are UNKNOWN, never invented.
    assert "{{" in ref and "}}" in ref
    assert "UNKNOWN" in ref
    assert re.search(r"never invent", ref, re.IGNORECASE)
    # The ephemeral copy must never be committed.
    assert "never committed" in _norm(ref)


def test_work_order_pins_scope_tests_and_verification() -> None:
    wo = _norm(_read_strict(WO))
    assert "WO-P1-520" in wo
    for path in (
        ".agents/skills/a-nightshift/SKILL.md",
        ".agents/skills/a-nightshift/references/overnight-supervisor.md",
        "tests/test_a_nightshift_skill_contract.py",
        "docs/work-orders/WO-P1-520-a-nightshift-skill.md",
    ):
        assert path in wo, f"WO lost frozen path: {path}"
    assert "RED" in wo
    assert "84696b2360197c981d6f9fa2f33fb065b7b8ef07" in wo
    assert "CONTROL_PLANE_ONLY" in wo
    assert "R3" in wo


# --- attempt-0003: premature-terminal regression repair (issue #520) ---
# The first real overnight run stopped prematurely: a derived-STALLED
# external CI job (authoritative state IN_PROGRESS, recheck available)
# collapsed into terminal NO_SAFE_NEXT_ACTION and early cleanup. These
# tests pin the corrected terminal-classification semantics.


_INCIDENT_520_SCENARIO = {
    "external_kind": "CI",
    "authoritative_state": "IN_PROGRESS",
    "derived_liveness": "STALLED",
    "last_progress_age": "above the declared stall bound",
    "can_repoll": "YES",
    "mutable_ready": 0,
}

_INCIDENT_520_EXPECTED = {
    "NIGHTSHIFT_STATE": "WAITING_EXTERNAL",
    "GOAL_TERMINAL": "NO",
    "CLEANUP_ALLOWED": "NO",
    "NO_SAFE_NEXT_ACTION": "FALSE",
    "NEXT_SAFE_ACTION": "bounded re-poll/reconcile",
}


def _liveness_section() -> str:
    return _norm(_section(_read_strict(SKILL), "External liveness"))


def test_stalled_external_dependency_is_waiting_external_not_terminal() -> None:
    # Invariant 1: a recheckable RUNNING/WAITING/STALLED external
    # dependency is WAITING_EXTERNAL, never a terminal Goal state.
    section = _liveness_section()
    combined = section + " " + _norm(_read_strict(REFERENCE))
    assert "WAITING_EXTERNAL" in section
    for kind in ("CI", "provider", "review", "device"):
        assert kind in combined, f"lost external-dependency kind: {kind}"
    assert "never a terminal" in section or "not a terminal" in section
    # STALLED is a reconciliation warning, never replay/termination.
    assert "STALLED" in section and "reconciliation" in section
    assert "never automatic replay" in combined


def test_recheck_action_forbids_no_safe_next_action() -> None:
    # Invariant 2: RECHECK_ACTION_EXISTS => NO_SAFE_NEXT_ACTION = FALSE.
    section = _liveness_section()
    assert "RECHECK_ACTION_EXISTS" in section
    assert (
        "NO_SAFE_NEXT_ACTION = FALSE" in section
        or "NO_SAFE_NEXT_ACTION=FALSE" in section
    )
    assert "bounded" in section and "re-poll" in section
    # A checkpoint's own declared exact next safe action counts as recheck.
    assert "already-declared exact next safe action" in section


def test_no_mutation_available_is_not_terminal_stop() -> None:
    # Invariant 3: NO_MUTATION_AVAILABLE != NO_SAFE_NEXT_ACTION.
    section = _liveness_section()
    assert "NO_MUTATION_AVAILABLE" in section
    assert "is not `NO_SAFE_NEXT_ACTION`" in section
    for remains in (
        "read-only recovery/reconciliation",
        "independent review",
        "bounded monitoring work",
    ):
        assert remains in section, f"lost remaining-work class: {remains}"


def test_terminal_gate_requires_exhaustive_absence_proof() -> None:
    # Invariant 4: terminal NO_SAFE_NEXT_ACTION requires proving ALL
    # seven action classes absent (TRUE_NO_SAFE_NEXT_ACTION).
    section = _liveness_section()
    combined = section + " " + _norm(_read_strict(REFERENCE))
    assert "TRUE_NO_SAFE_NEXT_ACTION" in combined
    for absent in (
        "mutable READY work",
        "read-only recovery/reconciliation",
        "`TERMINAL_UNHARVESTED` harvest",
        "independent review action",
        "authorized external observation/recheck",
        "bounded monitoring action",
        "already-declared exact next safe action",
    ):
        assert absent in combined, f"lost required-absent proof: {absent}"
    assert "If any exists" in combined
    assert "prove ALL" in section


def test_waiting_external_lifecycle_keeps_goal_alive() -> None:
    # Invariant 5: WAITING_EXTERNAL lifecycle semantics.
    section = _liveness_section()
    assert "Goal remains alive" in section
    assert "ownership" in section and "dependency/job identity" in section
    assert "event-driven wake" in section
    assert "Unchanged polls are not progress" in section
    assert "busy polling" in section
    assert "recompute the DAG" in section
    assert "continue/refill" in section


def test_cleanup_forbidden_for_recheckable_non_terminal_states() -> None:
    # Invariant 6: cleanup hardening — non-terminal/recheckable states
    # and a bare "blocked" label are never cleanup authority.
    skill = _norm(_section(_read_strict(SKILL), "cleanup"))
    ref = _norm(_read_strict(REFERENCE))
    combined = skill + " " + ref
    for state in (
        "RUNNING",
        "WAITING",
        "WAITING_EXTERNAL",
        "STALLED",
        "INTERRUPTED-recoverable",
        "UNKNOWN-recoverable",
    ):
        assert state in combined, f"cleanup hardening lost state: {state}"
    assert "valid recheck" in combined
    for eligible in (
        "GOAL_COMPLETE",
        "TRUE terminal human/safety/authorization gate",
        "TRUE_NO_SAFE_NEXT_ACTION",
    ):
        assert eligible in combined, f"lost cleanup eligibility proof: {eligible}"
    assert '"blocked" label alone is never cleanup authority' in combined


def test_escalation_guard_before_terminal_conversion() -> None:
    # Invariant 7: ambiguous STALLED/WAITING_EXTERNAL terminal conversion
    # must escalate or fail closed, never terminate on model uncertainty.
    section = _liveness_section()
    combined = section + " " + _norm(_read_strict(REFERENCE))
    assert "Escalation guard" in section
    assert (
        "escalate the classification to the configured stronger/integrator path"
        in combined
    )
    assert "fail closed as `WAITING_EXTERNAL`" in combined
    assert (
        "Never terminate merely because the low-cost model is uncertain" in combined
    )
    codex = _norm(_section(_read_strict(SKILL), "Codex supervisor"))
    assert "terminal-classification" in codex


def test_incident_520_regression_pinned() -> None:
    # Invariant 8: the actual incident scenario and its required outcome
    # vector are pinned as regression semantics.
    assert _INCIDENT_520_SCENARIO["external_kind"] == "CI"
    assert _INCIDENT_520_SCENARIO["authoritative_state"] == "IN_PROGRESS"
    assert _INCIDENT_520_SCENARIO["derived_liveness"] == "STALLED"
    assert _INCIDENT_520_SCENARIO["can_repoll"] == "YES"
    assert _INCIDENT_520_SCENARIO["mutable_ready"] == 0
    assert _INCIDENT_520_EXPECTED["NIGHTSHIFT_STATE"] == "WAITING_EXTERNAL"
    assert _INCIDENT_520_EXPECTED["GOAL_TERMINAL"] == "NO"
    assert _INCIDENT_520_EXPECTED["CLEANUP_ALLOWED"] == "NO"
    assert _INCIDENT_520_EXPECTED["NO_SAFE_NEXT_ACTION"] == "FALSE"
    assert _INCIDENT_520_EXPECTED["NEXT_SAFE_ACTION"] == "bounded re-poll/reconcile"
    # The contract carries the same machine-visible outcomes verbatim.
    ref = _norm(_read_strict(REFERENCE))
    for needle in (
        "external_kind=CI",
        "IN_PROGRESS",
        "STALLED",
        "can_repoll=YES",
        "mutable_ready=0",
        "NIGHTSHIFT_STATE=WAITING_EXTERNAL",
        "GOAL_TERMINAL=NO",
        "CLEANUP_ALLOWED=NO",
        "NO_SAFE_NEXT_ACTION=FALSE",
        "NEXT_SAFE_ACTION=bounded re-poll/reconcile",
        "running, recheckable CI dependency is not terminal",
    ):
        assert needle in ref, f"incident regression marker lost: {needle}"


def test_no_new_scheduler_timer_or_state_store() -> None:
    # Invariant 10: policy/contract hardening only — the overlay still
    # creates no scheduler, timer, or state store of its own.
    text = _norm(_read_strict(SKILL))
    assert "never becomes a scheduler, task store, claim/lease system" in text
    assert "WAITING_EXTERNAL" in _liveness_section()


# --- attempt-0005: no-model-spin blocking-wait repair (issue #520) ---
# Resumed from the cooperatively cancelled attempt-0004, preserving its
# partial docstring mutation. The 2026-09-23/24 reply-spin incident: on a
# live /goal, an unchanged WAITING_EXTERNAL CI dependency caused
# seconds-scale model turns — poll -> visible still-waiting reply ->
# model turn completes -> /goal auto-continues -> poll again — burning
# Codex/model usage. A prose polling interval is not a timer. These tests
# pin the blocking-wait contract (WO-P1-520 Phase 1: RED proof required
# before any SKILL.md/reference/WO implementation edit).

_REPLY_SPIN_520_SCENARIO = {
    "external_kind": "CI",
    "authoritative_state": "IN_PROGRESS",
    "state_changed": "NO",
    "blocking_wait_capable": "YES",
    "independent_ready_work": "NO",
}

_REPLY_SPIN_520_EXPECTED = {
    "USE_BLOCKING_WAIT": "YES",
    "MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT": "YES",
    "USER_VISIBLE_REPEAT_REPLY": "FORBIDDEN",
    "AUTO_CONTINUATION_REPOLL": "FORBIDDEN",
    "UNCHANGED_WAIT_OUTPUT": "SILENT",
    "GOAL_TERMINAL": "NO",
    "CLEANUP_ALLOWED": "NO",
}


def _wait_contract_sections() -> str:
    # External-liveness bodies of the overlay and the canonical template,
    # where the blocking-wait semantics live.
    skill = _read_strict(SKILL)
    ref = _read_strict(REFERENCE)
    return _norm(_section(skill, "External liveness")) + " " + _norm(
        _section(ref, "External liveness")
    )


def _combined_contract_text() -> str:
    return _norm(_read_strict(SKILL)) + " " + _norm(_read_strict(REFERENCE))


def test_no_model_spin_markers_pinned_in_skill_and_template() -> None:
    # The six machine-visible markers of the no-model-spin contract must
    # appear verbatim in both the overlay and the canonical template.
    skill = _norm(_read_strict(SKILL))
    ref = _norm(_read_strict(REFERENCE))
    for marker in (
        "USE_BLOCKING_WAIT=YES",
        "MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT=YES",
        "USER_VISIBLE_REPEAT_REPLY=FORBIDDEN",
        "AUTO_CONTINUATION_REPOLL=FORBIDDEN",
        "UNCHANGED_WAIT_OUTPUT=SILENT",
        "WAIT_TOOL_TIMEOUT_RECHECK",
    ):
        assert marker in skill, f"no-model-spin marker lost from SKILL.md: {marker}"
        assert marker in ref, f"no-model-spin marker lost from template: {marker}"


def test_unchanged_external_wait_is_one_foreground_blocking_wait() -> None:
    # Invariant 1: WAITING_EXTERNAL + unchanged authoritative state +
    # blocking wait capable + no independent READY work resolves to ONE
    # foreground read-only blocking wait bound to the exact dependency
    # identity.
    corpus = _wait_contract_sections()
    assert "foreground" in corpus
    assert "read-only" in corpus
    assert "blocking wait" in corpus
    assert "bound to the exact dependency" in corpus
    assert "unchanged authoritative state" in corpus
    assert (
        "no independent READY work" in corpus
        or "no independent SAFE READY work" in corpus
    )


def test_waiting_never_completes_model_turn_to_report_unchanged_state() -> None:
    # Invariant 2: waiting does not complete the model turn solely to
    # report unchanged state.
    corpus = _wait_contract_sections()
    assert (
        "never completes the model turn" in corpus
        or "does not complete the model turn" in corpus
        or "must not complete the model turn" in corpus
    )
    assert "solely to report" in corpus
    assert "unchanged" in corpus


def test_no_repeated_user_visible_reply_on_goal_auto_continuation() -> None:
    # Invariant 3: no repeated user-visible WAITING_EXTERNAL reply solely
    # because /goal auto-continued.
    corpus = _combined_contract_text()
    assert "/goal" in corpus
    assert "auto-continu" in corpus
    assert "user-visible" in corpus
    assert "solely because" in corpus


def test_gh_run_watch_is_the_preferred_ci_blocking_primitive() -> None:
    # Invariant 4: the GitHub Actions preferred primitive references the
    # exact foreground blocking watch command (or an equivalent one).
    ref = _norm(_read_strict(REFERENCE))
    assert "gh run watch" in ref
    for fragment in (
        "<RUN_ID>",
        "<OWNER/REPO>",
        "--compact",
        "--exit-status",
        "--interval 60",
    ):
        assert fragment in ref, f"gh run watch primitive lost fragment: {fragment}"
    assert "foreground" in _combined_contract_text()


def test_unchanged_watcher_output_suppressed_from_model_context() -> None:
    # Invariant 5: repetitive unchanged watcher output is suppressed or
    # redirected out of model context.
    corpus = _combined_contract_text()
    assert (
        "suppress" in corpus
        or "suppressed" in corpus
        or "redirect" in corpus
        or "redirected" in corpus
    )
    assert "model context" in corpus


def test_generic_fallback_is_one_silent_in_tool_loop() -> None:
    # Invariant 6: the generic fallback is one foreground bounded silent
    # loop inside a tool call; sleep/poll internally; return output only
    # on transition, terminal state, real error, or bounded tool timeout.
    corpus = _combined_contract_text()
    assert "inside a tool call" in corpus
    assert "sleep" in corpus
    assert "silent" in corpus
    assert "only on transition" in corpus
    assert "real error" in corpus
    assert "bounded tool timeout" in corpus


def test_no_detached_watcher_or_new_state_store() -> None:
    # Invariant 7: the wait mechanics create no detached/unowned
    # watcher/timer, scheduler, task store, or new state store.
    corpus = _combined_contract_text()
    assert "no detached" in corpus or "never detached" in corpus
    assert "unowned" in corpus
    assert "watcher" in corpus and "timer" in corpus
    assert "new state store" in corpus or "no state store" in corpus


def test_wait_tool_timeout_recheck_not_progress_gate_or_cleanup() -> None:
    # Invariant 8: WAIT_TOOL_TIMEOUT_RECHECK is not progress, not a stop
    # gate, not cleanup authority; fresh-read then re-enter the blocking
    # wait while still recheckable with no READY work.
    corpus = _combined_contract_text()
    assert "WAIT_TOOL_TIMEOUT_RECHECK" in corpus
    assert "not progress" in corpus
    assert "not a stop gate" in corpus or "never a stop gate" in corpus
    assert "not cleanup authority" in corpus or "never cleanup authority" in corpus
    assert "fresh-read" in corpus or "fresh read" in corpus
    assert "re-enter" in corpus


def test_seconds_scale_goal_response_loops_forbidden() -> None:
    # Invariant 9: seconds-scale goal response loops are explicitly
    # forbidden.
    corpus = _combined_contract_text()
    assert "seconds-scale" in corpus
    assert re.search(
        r"seconds-scale.{0,120}forbidden|forbidden.{0,120}seconds-scale", corpus
    )


def test_safe_ready_work_dispatched_before_blocking() -> None:
    # Invariant 10: before blocking, dispatch/harvest independent SAFE
    # READY work first.
    corpus = _combined_contract_text()
    assert (
        "Before blocking" in corpus
        or "before entering the blocking wait" in corpus
        or "before any blocking wait" in corpus
    )
    assert "dispatch" in corpus and "harvest" in corpus
    assert "independent SAFE READY" in corpus or "independent safe READY" in corpus


def test_state_changed_yes_returns_to_recover_reconcile_harvest() -> None:
    # Invariant 11: state_changed=YES causes the watcher to return, then
    # RECOVER -> RECONCILE -> HARVEST as needed -> recompute the DAG ->
    # continue/refill.
    sections = _wait_contract_sections()
    corpus = _combined_contract_text()
    assert "state_changed=YES" in sections
    assert "RECOVER -> RECONCILE -> HARVEST" in sections
    assert "recompute the DAG" in sections
    assert "continue/refill" in sections
    assert "watcher return" in corpus


def test_unchanged_polls_do_not_append_repeated_receipts() -> None:
    # Invariant 12: unchanged internal polls are not progress and do not
    # append repeated receipts; record watcher start plus transition or
    # timeout summary at most.
    corpus = _combined_contract_text()
    assert "Unchanged polls are not progress" in corpus
    assert "watcher start" in corpus
    assert (
        "transition/timeout summary" in corpus
        or "transition or timeout summary" in corpus
    )
    assert "at most" in corpus
    assert "do not append" in corpus or "never append" in corpus
    assert "repeated receipts" in corpus


def test_reply_spin_incident_vector_pinned() -> None:
    # Regression vector: the 2026-09-23/24 reply-spin incident scenario
    # and its required outcome vector (including the state_changed=YES
    # transition) are pinned as machine-visible markers in the template.
    assert _REPLY_SPIN_520_SCENARIO["external_kind"] == "CI"
    assert _REPLY_SPIN_520_SCENARIO["authoritative_state"] == "IN_PROGRESS"
    assert _REPLY_SPIN_520_SCENARIO["state_changed"] == "NO"
    assert _REPLY_SPIN_520_SCENARIO["blocking_wait_capable"] == "YES"
    assert _REPLY_SPIN_520_SCENARIO["independent_ready_work"] == "NO"
    assert _REPLY_SPIN_520_EXPECTED["USE_BLOCKING_WAIT"] == "YES"
    assert (
        _REPLY_SPIN_520_EXPECTED["MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT"]
        == "YES"
    )
    assert _REPLY_SPIN_520_EXPECTED["USER_VISIBLE_REPEAT_REPLY"] == "FORBIDDEN"
    assert _REPLY_SPIN_520_EXPECTED["AUTO_CONTINUATION_REPOLL"] == "FORBIDDEN"
    assert _REPLY_SPIN_520_EXPECTED["UNCHANGED_WAIT_OUTPUT"] == "SILENT"
    assert _REPLY_SPIN_520_EXPECTED["GOAL_TERMINAL"] == "NO"
    assert _REPLY_SPIN_520_EXPECTED["CLEANUP_ALLOWED"] == "NO"
    ref = _norm(_read_strict(REFERENCE))
    for needle in (
        "external_kind=CI",
        "authoritative_state=IN_PROGRESS",
        "state_changed=NO",
        "blocking_wait_capable=YES",
        "independent_ready_work=NO",
        "USE_BLOCKING_WAIT=YES",
        "MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT=YES",
        "USER_VISIBLE_REPEAT_REPLY=FORBIDDEN",
        "AUTO_CONTINUATION_REPOLL=FORBIDDEN",
        "UNCHANGED_WAIT_OUTPUT=SILENT",
        "GOAL_TERMINAL=NO",
        "CLEANUP_ALLOWED=NO",
        "state_changed=YES",
    ):
        assert needle in ref, f"reply-spin regression marker lost: {needle}"


# --- WO-P1-522 attempt-0001: integrator handoff + stale terminal pointer ---
# Post-#520 production sequence (issue #522): NightShift recovered #517
# and PR #519 correctly, then an integrator (Sol) acceptance boundary was
# collapsed directly into HUMAN_ACTION_REQUIRED, the run directory was
# cleaned up by exact path, the same /goal auto-continuation later
# re-entered using the deleted contract, and CONTRACT_ABSENT was
# repeatedly reported as SAFETY_BLOCK. These tests pin the corrected
# F1/F2/F3 semantics before any SKILL.md/reference repair (RED-first).

_INCIDENT_522_SCENARIO = {
    "recovered": "#517 and PR #519",
    "collapsed_boundary": "integrator acceptance -> HUMAN_ACTION_REQUIRED",
    "cleanup": "exact-path run-directory deletion",
    "reentry": "/goal auto-continuation using the deleted contract",
    "misclassification": "CONTRACT_ABSENT reported as SAFETY_BLOCK",
}

_INCIDENT_522_AVAILABLE_VECTOR = {
    "INTEGRATOR_ROUTE": "AVAILABLE",
    "NIGHTSHIFT_STATE": "WAITING_INTEGRATOR",
    "GOAL_TERMINAL": "NO",
    "CLEANUP_ALLOWED": "NO",
    "HUMAN_ACTION_REQUIRED": "FALSE",
}

_INCIDENT_522_STALE_POINTER_VECTOR = {
    "CLASSIFICATION": "STALE_TERMINAL_POINTER",
    "GOAL_STATE": "GOAL_ALREADY_TERMINAL",
    "SAFETY_BLOCK": "FALSE",
    "REMATERIALIZE": "FORBIDDEN",
    "REDISPATCH": "FORBIDDEN",
    "USER_VISIBLE_REPEAT_REPLY": "FORBIDDEN",
}


def _integrator_handoff_sections() -> str:
    skill = _read_strict(SKILL)
    ref = _read_strict(REFERENCE)
    return _norm(_section(skill, "Integrator handoff")) + " " + _norm(
        _section(ref, "Integrator handoff")
    )


def _stale_pointer_sections() -> str:
    skill = _read_strict(SKILL)
    ref = _read_strict(REFERENCE)
    return _norm(_section(skill, "Stale terminal-pointer")) + " " + _norm(
        _section(ref, "Stale terminal-pointer")
    )


def _cleanup_rules_corpus() -> str:
    skill = _read_strict(SKILL)
    ref = _read_strict(REFERENCE)
    return _norm(_section(skill, "Cleanup of the ephemeral run")) + " " + _norm(
        _section(ref, "Cleanup rules")
    )


def test_integrator_action_required_requires_route_classification_first() -> None:
    # F1 pin 1: INTEGRATOR_ACTION_REQUIRED is not itself a stop gate; the
    # integrator route must be classified before any stop classification,
    # and an available-or-unknown route is not automatically terminal.
    corpus = _integrator_handoff_sections()
    assert "INTEGRATOR_ACTION_REQUIRED" in corpus
    assert "not itself a stop gate" in corpus
    for route in ("AVAILABLE", "UNKNOWN", "PROVEN_UNAVAILABLE"):
        assert route in corpus, f"lost integrator route class: {route}"
    assert "classify" in corpus
    assert "not automatically terminal" in corpus


def test_integrator_route_available_is_waiting_integrator_not_human_gate() -> None:
    # F1 pin 2: AVAILABLE routes through the existing accepted authority
    # as WAITING_INTEGRATOR — non-terminal, no cleanup, no human gate.
    corpus = _integrator_handoff_sections()
    assert "WAITING_INTEGRATOR" in corpus
    assert "GOAL_TERMINAL=NO" in corpus
    assert "CLEANUP_ALLOWED=NO" in corpus
    assert "HUMAN_ACTION_REQUIRED=FALSE" in corpus


def test_integrator_route_unknown_recovers_never_invents_human_gate() -> None:
    # F1 pin 3: UNKNOWN recovers/probes the route; it never invents
    # HUMAN_ACTION_REQUIRED while the route is merely unproven.
    corpus = _integrator_handoff_sections()
    assert "UNKNOWN" in corpus
    assert "recover" in corpus and "probe" in corpus
    assert "do not invent" in corpus or "never invent" in corpus
    assert "HUMAN_ACTION_REQUIRED" in corpus


def test_integrator_route_proven_unavailable_bounded_human_gate() -> None:
    # F1 pin 4: PROVEN_UNAVAILABLE may derive HUMAN_ACTION_REQUIRED only
    # when a human must actually invoke the integrator.
    corpus = _integrator_handoff_sections()
    assert "PROVEN_UNAVAILABLE" in corpus
    assert "only when" in corpus or "only after" in corpus
    assert "actually" in corpus


def test_no_model_name_grants_integrator_authority() -> None:
    # F1 pin 5: model/provider names are routing preferences only; the
    # accepted integrator/acceptance authority is not replaced.
    corpus = _combined_contract_text()
    assert "No model/provider name grants authority" in corpus
    assert "GPT-5.6 Sol" in corpus
    assert "integrator/acceptance authority" in corpus


def test_terminal_cleanup_requires_durable_fold_into_existing_authority() -> None:
    # F2 pin 1: before any terminal cleanup, fold a compact final run
    # record into an existing durable task authority — continuity
    # folding, never a new status store.
    corpus = _cleanup_rules_corpus()
    assert "Before any terminal cleanup" in corpus
    assert "existing durable task authority" in corpus
    for authority in ("Issue", "accepted WO checkpoint", "existing durable checkpoint"):
        assert authority in corpus, f"lost durable fold target: {authority}"
    for field in (
        "run id",
        "terminal classification",
        "evidence pointer",
        "exact next safe action",
        "cleanup intent",
    ):
        assert field in corpus, f"lost final-run-record field: {field}"
    assert "not a new status store" in corpus or "never a new status store" in corpus


def test_ephemeral_receipt_alone_is_insufficient_durable_closeout() -> None:
    # F2 pin 2: the ephemeral receipt may be deleted with its run
    # directory and is explicitly insufficient durable closeout on its
    # own.
    corpus = _cleanup_rules_corpus()
    assert "ephemeral receipt" in corpus
    assert "insufficient durable closeout" in corpus
    assert "deleted with its run directory" in corpus


def test_contract_absent_recovers_durable_closeout_by_run_id() -> None:
    # F3 pin 1: a CONTRACT_ABSENT entry performs run-id durable recovery
    # before any classification.
    corpus = _stale_pointer_sections()
    assert "CONTRACT_ABSENT" in corpus
    assert "durable closeout" in corpus
    assert "exact run id" in corpus
    assert "before any classification" in corpus or "before classification" in corpus


def test_proven_terminal_cleanup_is_stale_pointer_not_safety_block() -> None:
    # F3 pin 2: exact durable terminal+cleanup proof classifies as
    # STALE_TERMINAL_POINTER / GOAL_ALREADY_TERMINAL with the full
    # no-incident, no-new-authority outcome vector.
    corpus = _stale_pointer_sections()
    assert "STALE_TERMINAL_POINTER" in corpus
    assert "GOAL_ALREADY_TERMINAL" in corpus
    assert "SAFETY_BLOCK=FALSE" in corpus
    assert "REMATERIALIZE=FORBIDDEN" in corpus
    assert "REDISPATCH=FORBIDDEN" in corpus
    assert "USER_VISIBLE_REPEAT_REPLY=FORBIDDEN" in corpus
    assert "no new authority" in corpus


def test_unproven_contract_absent_fails_closed() -> None:
    # F3 pin 3: without matching durable terminal proof, contract absence
    # stays CONTRACT_ABSENT_UNKNOWN and may fail closed as SAFETY_BLOCK.
    corpus = _stale_pointer_sections()
    assert "CONTRACT_ABSENT_UNKNOWN" in corpus
    assert "SAFETY_BLOCK" in corpus
    assert "fail" in corpus and "closed" in corpus


def test_incident_522_regression_vector_pinned() -> None:
    # The post-#520 production sequence and its required outcome vectors
    # are pinned as regression semantics, with machine-visible markers in
    # the canonical template.
    assert _INCIDENT_522_SCENARIO["recovered"] == "#517 and PR #519"
    assert (
        _INCIDENT_522_SCENARIO["collapsed_boundary"]
        == "integrator acceptance -> HUMAN_ACTION_REQUIRED"
    )
    assert _INCIDENT_522_SCENARIO["cleanup"] == "exact-path run-directory deletion"
    assert (
        _INCIDENT_522_SCENARIO["reentry"]
        == "/goal auto-continuation using the deleted contract"
    )
    assert (
        _INCIDENT_522_SCENARIO["misclassification"]
        == "CONTRACT_ABSENT reported as SAFETY_BLOCK"
    )
    assert _INCIDENT_522_AVAILABLE_VECTOR["INTEGRATOR_ROUTE"] == "AVAILABLE"
    assert (
        _INCIDENT_522_AVAILABLE_VECTOR["NIGHTSHIFT_STATE"] == "WAITING_INTEGRATOR"
    )
    assert _INCIDENT_522_AVAILABLE_VECTOR["GOAL_TERMINAL"] == "NO"
    assert _INCIDENT_522_AVAILABLE_VECTOR["CLEANUP_ALLOWED"] == "NO"
    assert _INCIDENT_522_AVAILABLE_VECTOR["HUMAN_ACTION_REQUIRED"] == "FALSE"
    assert (
        _INCIDENT_522_STALE_POINTER_VECTOR["CLASSIFICATION"] == "STALE_TERMINAL_POINTER"
    )
    assert _INCIDENT_522_STALE_POINTER_VECTOR["GOAL_STATE"] == "GOAL_ALREADY_TERMINAL"
    assert _INCIDENT_522_STALE_POINTER_VECTOR["SAFETY_BLOCK"] == "FALSE"
    assert _INCIDENT_522_STALE_POINTER_VECTOR["REMATERIALIZE"] == "FORBIDDEN"
    assert _INCIDENT_522_STALE_POINTER_VECTOR["REDISPATCH"] == "FORBIDDEN"
    assert (
        _INCIDENT_522_STALE_POINTER_VECTOR["USER_VISIBLE_REPEAT_REPLY"] == "FORBIDDEN"
    )
    ref = _norm(_read_strict(REFERENCE))
    for needle in (
        "INTEGRATOR_ROUTE=AVAILABLE",
        "NIGHTSHIFT_STATE=WAITING_INTEGRATOR",
        "HUMAN_ACTION_REQUIRED=FALSE",
        "STALE_TERMINAL_POINTER",
        "GOAL_ALREADY_TERMINAL",
        "SAFETY_BLOCK=FALSE",
        "REMATERIALIZE=FORBIDDEN",
        "REDISPATCH=FORBIDDEN",
        "USER_VISIBLE_REPEAT_REPLY=FORBIDDEN",
        "CONTRACT_ABSENT_UNKNOWN",
    ):
        assert needle in ref, f"incident-522 regression marker lost: {needle}"
    skill = _norm(_read_strict(SKILL))
    assert "STALE_TERMINAL_POINTER" in skill
    assert "WAITING_INTEGRATOR" in skill


def test_wait_semantics_unchanged_by_handoff_repair() -> None:
    # Control pin (WO-P1-522 regression 10): the handoff/closeout repair
    # leaves the WAITING_EXTERNAL / WAIT_TOOL_TIMEOUT_RECHECK /
    # no-model-spin contract markers intact in both artifacts.
    skill = _norm(_read_strict(SKILL))
    ref = _norm(_read_strict(REFERENCE))
    for marker in (
        "WAITING_EXTERNAL",
        "WAIT_TOOL_TIMEOUT_RECHECK",
        "USE_BLOCKING_WAIT=YES",
        "MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT=YES",
        "AUTO_CONTINUATION_REPOLL=FORBIDDEN",
        "UNCHANGED_WAIT_OUTPUT=SILENT",
    ):
        assert marker in skill, f"wait marker lost from SKILL.md: {marker}"
        assert marker in ref, f"wait marker lost from template: {marker}"


# --- WO-P1-522 attempt-0002: two-phase durable closeout (Sol finding) ---
# Sol integrator CHANGES_REQUIRED (issue #522, 2026-09-24): attempt-0001
# required a durable PRE-cleanup fold carrying cleanup intent, but no
# POST-delete durable confirmation. If exact-path deletion succeeds and
# the ephemeral receipt disappears with the run directory, a durable
# authority holding only the PRE fold proves intent, not completed
# cleanup — a later CONTRACT_ABSENT cannot deterministically distinguish
# expected completed cleanup from unexpected loss. These tests pin the
# two-phase closeout repair before any further SKILL.md/reference edit
# (RED-first).

_TWO_PHASE_522_SCENARIO = {
    "finding": "PRE fold proves cleanup intent, not completed cleanup",
    "phase_1": "PRE_CLEANUP_FOLDED before exact-path deletion",
    "phase_2": "exact-path deletion of the one run directory",
    "phase_3": "POST_CLEANUP_CONFIRMED in the SAME existing durable authority",
}

_TWO_PHASE_522_EXPECTED = {
    "POST_FIELDS": "run id, exact deleted path, terminal classification, cleanup result",
    "STALE_POINTER_PROOF": "PRE_CLEANUP_FOLDED + POST_CLEANUP_CONFIRMED",
    "INTENT_ALONE": "INSUFFICIENT",
    "DELETE_FAILURE": "FAIL_CLOSED_RECOVERABLE",
    "MISSING_POST_CONFIRM": "NEVER_FABRICATED_SUCCESS",
}


def test_two_phase_closeout_pre_delete_post_ordering() -> None:
    # Repair pin 1: terminal closeout is two-phase in the same existing
    # durable authority — PRE_CLEANUP_FOLDED precedes the exact-path
    # deletion; POST_CLEANUP_CONFIRMED follows successful deletion.
    corpora = (
        _norm(_section(_read_strict(SKILL), "Cleanup of the ephemeral run")),
        _norm(_section(_read_strict(REFERENCE), "Cleanup rules")),
    )
    for corpus in corpora:
        assert "PRE_CLEANUP_FOLDED" in corpus
        assert "POST_CLEANUP_CONFIRMED" in corpus
        pre = corpus.find("PRE_CLEANUP_FOLDED")
        post = corpus.find("POST_CLEANUP_CONFIRMED")
        assert pre != -1 and post != -1 and pre < post
        # The deletion step sits between the two durable phases.
        assert re.search(r"delet", corpus[pre:post])


def test_post_cleanup_confirmed_minimum_fields_no_secrets() -> None:
    # Repair pin 2: POST_CLEANUP_CONFIRMED records at minimum run id,
    # exact deleted path, terminal classification, and cleanup result —
    # with no secrets and no log dumps.
    corpora = (
        _norm(_section(_read_strict(SKILL), "Cleanup of the ephemeral run")),
        _norm(_section(_read_strict(REFERENCE), "Cleanup rules")),
    )
    for body in corpora:
        post = body.find("POST_CLEANUP_CONFIRMED")
        assert post != -1
        window = body[post : post + 600]
        for field in (
            "run id",
            "exact deleted path",
            "terminal classification",
            "cleanup result",
        ):
            assert field in window, f"POST_CLEANUP_CONFIRMED lost field: {field}"
        assert "no secrets" in window
        assert "no log dumps" in window


def test_stale_pointer_requires_post_cleanup_confirmed() -> None:
    # Repair pin 3: STALE_TERMINAL_POINTER / GOAL_ALREADY_TERMINAL
    # requires POST_CLEANUP_CONFIRMED; cleanup intent alone is
    # insufficient.
    corpus = _stale_pointer_sections()
    assert "STALE_TERMINAL_POINTER" in corpus
    assert "GOAL_ALREADY_TERMINAL" in corpus
    assert "POST_CLEANUP_CONFIRMED" in corpus
    assert "PRE_CLEANUP_FOLDED" in corpus
    assert re.search(r"intent alone", corpus)
    assert "insufficient" in corpus


def test_delete_failure_or_missing_post_confirmation_fails_closed() -> None:
    # Repair pin 4: delete failure or a missing post-confirmation stays
    # fail-closed and recoverable and never fabricates success.
    corpus = _cleanup_rules_corpus() + " " + _stale_pointer_sections()
    assert "deletion fails" in corpus or "failed deletion" in corpus
    assert "cannot be recorded" in corpus or "missing post-confirmation" in corpus
    assert "fail-closed" in corpus or "fail closed" in corpus
    assert "recoverable" in corpus
    assert "never fabricate" in corpus


def test_two_phase_reuses_same_existing_durable_authority() -> None:
    # Repair pin 5: both phases fold into the SAME existing durable
    # authority — no new store, no new authority.
    corpus = _cleanup_rules_corpus()
    assert "SAME existing durable authority" in corpus
    for authority in ("Issue", "accepted WO checkpoint", "existing durable checkpoint"):
        assert authority in corpus, f"lost durable fold target: {authority}"
    assert "not a new status store" in corpus or "never a new status store" in corpus


def test_two_phase_incident_vector_pinned() -> None:
    # The Sol-finding scenario and the required two-phase outcome are
    # pinned as machine-visible markers in both artifacts.
    assert (
        _TWO_PHASE_522_SCENARIO["phase_1"]
        == "PRE_CLEANUP_FOLDED before exact-path deletion"
    )
    assert _TWO_PHASE_522_SCENARIO["phase_3"].endswith("SAME existing durable authority")
    assert _TWO_PHASE_522_EXPECTED["INTENT_ALONE"] == "INSUFFICIENT"
    assert _TWO_PHASE_522_EXPECTED["DELETE_FAILURE"] == "FAIL_CLOSED_RECOVERABLE"
    assert _TWO_PHASE_522_EXPECTED["MISSING_POST_CONFIRM"] == "NEVER_FABRICATED_SUCCESS"
    skill = _norm(_read_strict(SKILL))
    ref = _norm(_read_strict(REFERENCE))
    for needle in (
        "PRE_CLEANUP_FOLDED",
        "POST_CLEANUP_CONFIRMED",
        "SAME existing durable authority",
        "exact deleted path",
        "cleanup result",
    ):
        assert needle in skill, f"two-phase marker lost from SKILL.md: {needle}"
        assert needle in ref, f"two-phase marker lost from template: {needle}"
    assert "intent alone is insufficient" in ref


def test_attempt0002_preserves_f1_f2_f3_and_wait_semantics() -> None:
    # Repair pin 6 (control): the two-phase repair preserves the
    # attempt-0001 F1/F2/F3 repair and the WAITING_EXTERNAL /
    # no-model-spin semantics in both artifacts.
    skill = _norm(_read_strict(SKILL))
    ref = _norm(_read_strict(REFERENCE))
    for marker in (
        "WAITING_INTEGRATOR",
        "PROVEN_UNAVAILABLE",
        "HUMAN_ACTION_REQUIRED=FALSE",
        "CONTRACT_ABSENT_UNKNOWN",
        "STALE_TERMINAL_POINTER",
        "GOAL_ALREADY_TERMINAL",
        "WAITING_EXTERNAL",
        "WAIT_TOOL_TIMEOUT_RECHECK",
        "USE_BLOCKING_WAIT=YES",
        "MODEL_TURN_MUST_NOT_COMPLETE_ON_UNCHANGED_WAIT=YES",
        "AUTO_CONTINUATION_REPOLL=FORBIDDEN",
        "UNCHANGED_WAIT_OUTPUT=SILENT",
    ):
        assert marker in skill, f"preserved marker lost from SKILL.md: {marker}"
        assert marker in ref, f"preserved marker lost from template: {marker}"
    # Machine-visible route markers stay canonical in the template.
    for marker in ("INTEGRATOR_ROUTE=AVAILABLE", "NIGHTSHIFT_STATE=WAITING_INTEGRATOR"):
        assert marker in ref, f"canonical route marker lost: {marker}"


# --- WO-P1-522 attempt-0003: R3 mutation-probe hardening ---
# Independent review of 9f54e121 found that the attempt-0002 presence-based
# checks could be decoy-satisfied across duplicated contract copies. These
# validators bind the requirement structure independently in SKILL.md, the
# reference canonical prose, and the fenced supervisor template body.


def _reference_without_supervisor_template_body() -> str:
    text = _read_strict(REFERENCE)
    marker = "## Supervisor contract body (template)"
    marker_at = text.find(marker)
    assert marker_at != -1, "missing supervisor template heading"
    fence = chr(96) * 3
    fence_start = text.find(fence, marker_at + len(marker))
    assert fence_start != -1, "missing supervisor template opening fence"
    fence_end = text.find(fence, fence_start + len(fence))
    assert fence_end != -1, "missing supervisor template closing fence"
    return text[:fence_start] + text[fence_end + len(fence) :]


def _supervisor_template_body() -> str:
    text = _read_strict(REFERENCE)
    marker = "## Supervisor contract body (template)"
    marker_at = text.find(marker)
    assert marker_at != -1, "missing supervisor template heading"
    fence = chr(96) * 3
    fence_start = text.find(fence, marker_at + len(marker))
    assert fence_start != -1, "missing supervisor template opening fence"
    fence_end = text.find(fence, fence_start + len(fence))
    assert fence_end != -1, "missing supervisor template closing fence"
    return text[fence_start + len(fence) : fence_end].lstrip("\n")


def _attempt0003_cleanup_copies() -> dict[str, str]:
    return {
        "skill": _norm(_section(_read_strict(SKILL), "Cleanup of the ephemeral run")),
        "reference-canonical": _norm(
            _section(_reference_without_supervisor_template_body(), "Cleanup rules")
        ),
        "template-body": _norm(_section(_supervisor_template_body(), "Cleanup")),
    }


def _attempt0003_stale_pointer_copies() -> dict[str, str]:
    return {
        "skill": _norm(_section(_read_strict(SKILL), "Stale terminal-pointer")),
        "reference-canonical": _norm(
            _section(
                _reference_without_supervisor_template_body(),
                "Stale terminal-pointer",
            )
        ),
        "template-body": _norm(
            _section(_supervisor_template_body(), "Stale terminal-pointer")
        ),
    }


_DELETE_SUCCESS_RE = re.compile(
    r"(?:exact-path\s+)?deletion"
    r"(?:\s+of\s+the\s+one\s+run\s+directory)?\s+succeeds"
    r"|successful\s+deletion",
    re.IGNORECASE,
)


def _assert_two_phase_cleanup_structure(label: str, body: str) -> None:
    corpus = _norm(body)
    pre = corpus.find("PRE_CLEANUP_FOLDED")
    assert pre != -1, f"{label}: missing PRE_CLEANUP_FOLDED"
    deletion = _DELETE_SUCCESS_RE.search(corpus, pre + len("PRE_CLEANUP_FOLDED"))
    assert deletion is not None, f"{label}: missing successful exact-path deletion step"
    early_post = corpus.find("POST_CLEANUP_CONFIRMED", pre, deletion.start())
    assert early_post == -1, (
        f"{label}: POST_CLEANUP_CONFIRMED appears before successful deletion"
    )
    post = corpus.find("POST_CLEANUP_CONFIRMED", deletion.end())
    assert post != -1, f"{label}: POST_CLEANUP_CONFIRMED must follow successful deletion"
    assert pre < deletion.start() < post
    post_window = corpus[post : post + 650]
    assert "SAME existing durable authority" in post_window, (
        f"{label}: POST confirmation lost same-authority binding"
    )
    for field in (
        "run id",
        "exact deleted path",
        "terminal classification",
        "cleanup result",
    ):
        assert field in post_window, f"{label}: POST confirmation lost field {field!r}"

    assert re.search(r"(?:deletion fails|failed deletion)", corpus, re.IGNORECASE), (
        f"{label}: deletion-failure branch missing"
    )
    assert re.search(
        r"(?:post-confirmation cannot be recorded|missing post-confirmation)",
        corpus,
        re.IGNORECASE,
    ), f"{label}: missing-post-confirmation branch missing"
    assert re.search(r"fail[- ]closed", corpus, re.IGNORECASE), (
        f"{label}: fail-closed outcome missing"
    )
    assert "recoverable" in corpus.lower(), f"{label}: recoverable outcome missing"
    assert re.search(
        r"never\s+fabricate(?:\s+cleanup)?\s+success",
        corpus,
        re.IGNORECASE,
    ), f"{label}: never-fabricate-success outcome missing"


def _assert_stale_pointer_proof_structure(label: str, body: str) -> None:
    corpus = _norm(body)
    proof = re.search(
        r"(?:terminal\+cleanup\s+proof|cleanup\s+proof)"
        r".{0,220}?PRE_CLEANUP_FOLDED"
        r".{0,140}?(?:plus|\+)"
        r".{0,140}?POST_CLEANUP_CONFIRMED",
        corpus,
        re.IGNORECASE,
    )

    assert proof is not None, (
        f"{label}: stale-pointer proof must structurally require PRE plus POST"
    )
    for marker in (
        "STALE_TERMINAL_POINTER",
        "GOAL_ALREADY_TERMINAL",
        "SAFETY_BLOCK=FALSE",
        "REMATERIALIZE=FORBIDDEN",
        "REDISPATCH=FORBIDDEN",
        "USER_VISIBLE_REPEAT_REPLY=FORBIDDEN",
    ):
        assert marker in corpus, f"{label}: stale-pointer outcome lost {marker}"
    assert re.search(
        r"cleanup\s+intent\s+alone.{0,260}?(?:insufficient|not\s+cleanup\s+proof)",
        corpus,
        re.IGNORECASE,
    ), f"{label}: cleanup-intent insufficiency is not bound in this copy"


def _expect_contract_validator_rejects(label: str, check) -> None:
    try:
        check()
    except AssertionError:
        return
    raise AssertionError(f"mutation probe unexpectedly escaped: {label}")


def _move_post_before_successful_delete(body: str) -> str:
    corpus = _norm(body)
    pre = corpus.find("PRE_CLEANUP_FOLDED")

    assert pre != -1
    deletion = _DELETE_SUCCESS_RE.search(corpus, pre + len("PRE_CLEANUP_FOLDED"))
    assert deletion is not None
    token = "POST_CLEANUP_CONFIRMED"
    post = corpus.find(token, deletion.end())
    assert post != -1
    without_original = (
        corpus[:post] + "POST_MOVED_FROM_SUCCESS_SEQUENCE" + corpus[post + len(token) :]
    )
    return (
        without_original[: deletion.start()]
        + token
        + " "
        + without_original[deletion.start() :]
    )


def _remove_post_from_stale_proof(body: str) -> str:
    corpus = _norm(body)
    proof_start_match = re.search(
        r"(?:terminal\+cleanup\s+proof|cleanup\s+proof)",
        corpus,
        re.IGNORECASE,
    )
    assert proof_start_match is not None
    pre = corpus.find("PRE_CLEANUP_FOLDED", proof_start_match.start())
    assert pre != -1
    post = corpus.find("POST_CLEANUP_CONFIRMED", pre)
    assert post != -1

    return (
        corpus[:post]
        + "POST_REMOVED_FROM_PROOF"
        + corpus[post + len("POST_CLEANUP_CONFIRMED") :]
    )


def _remove_delete_failure_clause(body: str) -> str:
    corpus = _norm(body)
    mutated, count = re.subn(
        r"If deletion fails or the post-confirmation cannot be recorded,"
        r".*?never fabricate(?: cleanup)? success\.",
        "DELETE_FAILURE_CLAUSE_REMOVED.",
        corpus,
        count=1,
        flags=re.IGNORECASE,
    )
    assert count == 1, "probe could not isolate delete-failure clause"
    return mutated


def test_attempt0003_two_phase_cleanup_structure_is_pinned_per_copy() -> None:
    for label, body in _attempt0003_cleanup_copies().items():
        _assert_two_phase_cleanup_structure(label, body)


def test_attempt0003_stale_pointer_proof_is_pinned_per_copy() -> None:
    for label, body in _attempt0003_stale_pointer_copies().items():
        _assert_stale_pointer_proof_structure(label, body)


def test_attempt0003_reviewer_escape_vectors_are_rejected_per_copy() -> None:
    for label, body in _attempt0003_cleanup_copies().items():
        inverted = _move_post_before_successful_delete(body)
        _expect_contract_validator_rejects(
            f"{label}: POST before successful delete",
            lambda label=label, inverted=inverted: _assert_two_phase_cleanup_structure(
                label, inverted
            ),
        )
        no_failure = _remove_delete_failure_clause(body)
        _expect_contract_validator_rejects(
            f"{label}: delete-failure clause removed",
            lambda label=label, no_failure=no_failure: _assert_two_phase_cleanup_structure(
                label, no_failure
            ),
        )

    for label, body in _attempt0003_stale_pointer_copies().items():
        pre_only = _remove_post_from_stale_proof(body)
        _expect_contract_validator_rejects(
            f"{label}: PRE-only stale-pointer proof",
            lambda label=label, pre_only=pre_only: _assert_stale_pointer_proof_structure(
                label, pre_only
            ),
        )
