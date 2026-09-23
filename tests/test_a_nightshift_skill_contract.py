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
  ephemeral copy.

Deliberately not a full-file snapshot: wording may evolve as long as the
semantic markers stay. WO-P1-520 attempt-0001; A-Faster utilization-marker
pins added at attempt-0002.
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
