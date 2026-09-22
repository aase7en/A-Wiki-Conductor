"""WO-P1-483 — A-Faster invocation-equivalence contract regression tests.

Semantic assertions over the A-Faster skill contract. These tests fail if a
future edit removes:
- the canonical short-form equivalence ("use A-Faster" /
  "ใช้ A-Faster" / "ใช้ A-Faster ทำงานต่อ ตาม Roadmap" all route the same
  full acceleration profile, and the verbose form adds emphasis only);
- the auto-fill requirement for independent safe READY slots;
- the GPT-5.6 Sol fleet-integrator role (and its review limitation);
- the GLM-5.3 MAX / GLM-5.3-Flash task-class distinction;
- the PRE-DISPATCH DEDUPE GATE and its recovery dispositions;
- the SHORT_BURST reference and its frozen bounded-loop rules.

Deliberately not a full-file snapshot: wording may evolve as long as the
semantic markers stay. WO-P1-483 attempt-0002.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "a-faster" / "SKILL.md"
SHORT_BURST = ROOT / ".agents" / "skills" / "a-faster" / "references" / "short-burst.md"
WO = ROOT / "docs" / "work-orders" / "WO-P1-483-a-faster-short-burst-hardening.md"

_HEADING_RE = re.compile(r"^(?P<depth>#{2,4})\s+(?P<title>.+?)\s*$", re.MULTILINE)

ROADMAP_SHORTHAND = "ใช้ A-Faster ทำงานต่อ ตาม Roadmap"


def _read_strict(path: Path) -> str:
    # Strict UTF-8 decode is itself part of the WO483 verification matrix.
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


def test_skill_stays_overlay_on_a_fasttask_without_new_authority() -> None:
    text = _read_strict(SKILL)
    assert "not a second control plane" in text
    assert "../a-fasttask/SKILL.md" in text
    assert "A_FASTTASK_BASE_MISSING_OR_CONFLICT" in text
    # Router/binder boundary preserved: A-Faster ends after routing/binding.
    assert "ends where A-FastTask ends" in text


def test_canonical_short_forms_all_route_the_full_profile() -> None:
    text = _read_strict(SKILL)
    section = _section(text, "Invocation contract")
    for clause in ('"use A-Faster"', '"ใช้ A-Faster"', f'"{ROADMAP_SHORTHAND}"'):
        assert clause in section, f"canonical clause missing: {clause}"


def test_short_and_verbose_forms_are_semantically_equivalent() -> None:
    section = _norm(_section(_read_strict(SKILL), "Invocation contract"))
    # Emphasis-only: verbose form must not grant extra authority/WIP/collision
    # tolerance over the short form.
    assert "emphasis only" in section
    assert "never grants more WIP, authority, quota, or collision tolerance" in section
    # The work order freezes the same equivalence statement.
    wo = _norm(_read_strict(WO))
    assert "semantically equivalent" in wo


def test_invocation_contract_lists_the_full_default_profile() -> None:
    section = _norm(_section(_read_strict(SKILL), "Invocation contract"))
    markers = {
        "recovery/harvest": "delegated-run recovery/harvest",
        "one global WIP budget": "3 mutable + 1 independent review",
        "auto-fill READY slots": "AUTO-FILL",
        "GLM-first labor": "GLM-first",
        "MAX class": "GLM-5.3 MAX",
        "Flash class": "GLM-5.3-Flash",
        "Sol integrator fan-in": "fan-in",
        "Sol acceptance role": "acceptance",
        "autonomous continuation": "autonomous continuation",
        "no-overlap": "one mutation owner",
    }
    for label, marker in markers.items():
        assert marker in section, f"invocation contract lost: {label}"


def test_model_roles_keep_max_flash_distinction() -> None:
    text = _read_strict(SKILL)
    routing = _norm(_section(text, "Model routing"))
    assert "GLM-5.3 MAX" in routing
    assert "R2/R3" in routing
    assert "GLM-5.3-Flash" in routing
    assert "read-only" in routing
    assert "never satisfies" in routing
    delegation = _norm(_section(text, "GLM multilane delegation"))
    # Flash never silently satisfies a required MAX/qualified review and
    # never holds mutation authority.
    assert "never satisfy a required independent R3 MAX/qualified review" in delegation
    assert "never hold mutation authority" in delegation


def test_sol_remains_fleet_integrator_with_review_limit() -> None:
    text = _read_strict(SKILL)
    assert "fleet integrator" in _norm(text)
    delegation = _norm(_section(text, "GLM multilane delegation"))
    # Sol may directly execute eligible safe work when GLM routes are blocked…
    assert "directly continues the eligible safe task" in delegation
    # …but an authoring Sol lane never satisfies a still-required review.
    assert "authoring Sol" in delegation
    assert "cannot satisfy an independent-review requirement" in delegation


def test_pre_dispatch_dedupe_gate_exists_with_recovery_dispositions() -> None:
    text = _read_strict(SKILL)
    gate = _norm(_section(text, "PRE-DISPATCH DEDUPE GATE"))
    # Reconciliation dimensions before every material GLM launch.
    for dimension in (
        "task/claim",
        "repo / worktree / branch / HEAD",
        "scope / hotspot",
        "pointer",
        "result/exit",
        "process identity",
    ):
        assert dimension in gate, f"dedupe gate lost reconciliation of: {dimension}"
    # Dispositions.
    assert re.search(r"`RUNNING`.*do not dispatch", gate)
    assert re.search(r"`TERMINAL_UNHARVESTED`.*harvest", gate)
    assert re.search(r"`STALLED`.*reconcile.*replay safety", gate)
    # Non-authority events never grant redispatch.
    for event in ("timeout", "UI card", "chat/session loss", "Active Project drift"):
        assert event in gate, f"dedupe gate lost never-authority event: {event}"
    assert "never grants redispatch authority" in gate
    # One mutable hotspot stays one mutation owner (also stated globally).
    assert "1 MUTABLE HOTSPOT = 1 MUTATION OWNER" in text


def test_short_burst_reference_exists_and_is_linked() -> None:
    assert SHORT_BURST.is_file(), "references/short-burst.md must exist"
    skill_text = _read_strict(SKILL)
    assert "references/short-burst.md" in skill_text, (
        "SKILL.md must link the SHORT_BURST reference"
    )


def test_short_burst_reference_freezes_the_bounded_loop() -> None:
    text = _norm(_read_strict(SHORT_BURST))
    # Frozen loop chain.
    assert "RECOVER EXACT EVIDENCE" in text
    assert "ONE BOUNDED ACTION/DISPATCH" in text
    assert "USER CHECKPOINT" in text
    assert "NEXT BURST" in text
    # Exact-path first; broad scans only as one bounded staged escalation.
    assert "exact-path" in text
    assert re.search(r"broad recursive scans", text, re.IGNORECASE)
    assert "one escalation" in text
    # Frozen WO483 budget defaults.
    assert "200 lines" in text
    assert "8 KiB" in text
    assert "400 lines" in text
    assert "120 s" in text
    # Foreground >120s => background-first with PID/log/exit destinations.
    assert "background-first" in text
    assert "exit" in text
    # Wrapper timeout => UNKNOWN/RECOVER, never FAILURE.
    assert "UNKNOWN/RECOVER" in text
    assert "never automatic FAILURE" in text
    # Checkpoint cadence independent of tool-card UI.
    assert "tool card" in text


def test_mandatory_hook_checkpoint_sequence_is_frozen() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Mandatory enforcement-hook checkpoints"))
    sequence = (
        "ENTRY -> RECOVERY -> PRE_DISPATCH -> PRE_MUTATION -> PRE_FREEZE "
        "-> PRE_REVIEW -> PRE_MERGE -> POST_MAIN"
    )
    assert sequence in section
    assert "POLICY_ONLY" in section
    assert "GUARD_ENFORCED" in section
    assert "OBSERVE_ONLY" in section
    assert "MUST NOT claim that runtime enforcement prevented bypass" in section
    assert "do not report `GUARD_ENFORCED`" in section
    assert "guarded execution/Command Gateway" in section

    ref = _norm(_read_strict(SHORT_BURST))
    assert sequence in ref
    for checkpoint in (
        "ENTRY",
        "RECOVERY",
        "PRE_DISPATCH",
        "PRE_MUTATION",
        "PRE_FREEZE",
        "PRE_REVIEW",
        "PRE_MERGE",
        "POST_MAIN",
    ):
        assert f"`{checkpoint}`" in ref
    assert "SAFE_TO_MUTATE=YES" in ref
    assert "fail closed" in ref
    assert "never satisfies a GUARD requirement" in ref
    assert "second control plane" in ref


def test_wo_keeps_duplicate_dispatch_gate_and_equivalence() -> None:
    wo = _read_strict(WO)
    assert "Canonical invocation equivalence" in wo
    assert "Duplicate-dispatch acceptance gate" in wo
    assert ROADMAP_SHORTHAND in wo
