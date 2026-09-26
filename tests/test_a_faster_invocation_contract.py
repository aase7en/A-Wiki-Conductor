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


# --- WO-P1-517 — utilization enforcement contract ------------------------

UTILIZATION_GUARD = ROOT / "src" / "a_conductor" / "a_faster_utilization_guard.py"
ROADMAP = (
    ROOT
    / "docs"
    / "plans"
    / "2026-09-19-a-faster-hook-stm-observability-roadmap.md"
)
DEFECT_LESSONS = ROOT / "DEFECT_LESSONS.md"


def test_utilization_enforcement_section_pins_classifier_contract() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Utilization enforcement"))
    assert "WO-P1-517" in section
    assert "a_faster_utilization_guard.py" in section
    for output in (
        "FANOUT_TARGET",
        "UNUSED_SAFE_CAPACITY",
        "A_FASTER_UNDERUTILIZED",
        "AUTO_REFILL_REQUIRED",
    ):
        assert output in section, f"utilization enforcement lost: {output}"
    # Classifier stays projection-only; the executable refill bridge reuses
    # the accepted parallel-ready/PRE_DISPATCH path without a second authority.
    assert "no scheduler" in section
    assert "POLICY_ONLY" in section
    assert "WO-P1-498" in section
    assert "a_faster_auto_refill.py" in section
    assert "ParallelReadyExecutor" in section
    assert "scheduler-owned" in section
    assert "second authority" in section


def test_activation_receipt_tasking_vs_explanation_boundary() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Activation receipt"))
    assert "A_FASTER_ACTIVE" in section
    assert "EXPLANATION_ONLY" in section or "explanation" in section.lower()
    assert "never an activation receipt" in section
    # An explanation never grants enforcement or authority either.
    assert "never triggers utilization enforcement" in section
    assert "authority" in section


def test_sol_direct_labor_blocker_and_glm_first_roles_preserved() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Sol direct long labor"))
    assert "SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE" in section
    assert "fallback" in section
    assert "GLM-first" in section or "GLM labor" in section
    # Fleet-integrator role wording remains intact elsewhere in the skill.
    assert "fleet integrator" in _norm(text)


def test_no_manufactured_work_and_no_quota_burning() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "No manufactured work"))
    assert "NO_INDEPENDENT_READY_WORK" in section
    assert "manufacture work" in section or "manufactured work" in section
    assert "burn" in section and "quota" in section


def test_delegated_launch_discipline_preserves_bootstrap_lessons() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Delegated-run launch discipline"))
    # Lesson 1: structured admission evidence only; serialized command
    # text and SECRET_SOURCE_UNAVAILABLE are never admission.
    assert "structured" in section.lower()
    assert "serialized command text" in section
    assert "SECRET_SOURCE_UNAVAILABLE" in section
    # Lesson 2: explicit --dir bound to the claimed worktree plus
    # in-session identity proof before mutation.
    assert "--dir" in section
    assert "worktree" in section
    assert "repo/worktree/branch/HEAD" in section
    # Lesson 3: per-run share=disabled override unless separately
    # authorized.
    assert "share=disabled" in section
    assert "separately authorized" in section


def test_utilization_guard_module_exists_with_projection_boundary() -> None:
    source = _read_strict(UTILIZATION_GUARD)
    assert "FANOUT_TARGET" in source
    assert "UNUSED_SAFE_CAPACITY" in source
    assert "A_FASTER_UNDERUTILIZED" in source
    assert "AUTO_REFILL_REQUIRED" in source
    # No scheduler/dispatch/claim/lease/provider/merge authority.
    assert "no scheduler" in source
    assert "no dispatcher" in source or "launches nothing" in source


def test_roadmap_pins_policy_only_utilization_seam() -> None:
    roadmap = _norm(_read_strict(ROADMAP))
    assert "WO-P1-517" in roadmap
    assert "a_faster_utilization_guard.py" in roadmap
    assert "SOL_DIRECT_LONG_LABOR_WHILE_GLM_CAPACITY_IDLE" in roadmap
    assert "WO-P1-498" in roadmap


def test_defect_lessons_record_w517_bootstrap_defects() -> None:
    lessons = _norm(_read_strict(DEFECT_LESSONS))
    assert "#55" in lessons
    assert "WO-P1-517" in lessons
    assert "SECRET_SOURCE_UNAVAILABLE" in lessons
    assert "--dir" in lessons
    assert "share=disabled" in lessons


# --- WO-P1-530 hierarchical child-goal routing pins ---

def test_wo530_child_goal_is_bounded_execution_shape_not_authority() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    assert "CHILD_GOAL" in section
    assert "PARENT_GOAL -> KILO_GLM_CHILD -> OPTIONAL_JEV_ADVISORY" in section
    assert "Deeper recursive spawning is forbidden" in section
    for forbidden_authority in (
        "scheduler",
        "roadmap owner",
        "task database",
        "claim/lease system",
        "review authority",
        "merge authority",
        "completion authority",
    ):
        assert forbidden_authority in section


def test_wo530_child_goal_keeps_global_wip_and_lane_binding() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    assert "max 3 mutable plus 1 independent read-only review" in section
    assert "one mutable hotspot has exactly one owner" in section
    for token in ("task/work order", "claim/owner", "worktree", "exact HEAD", "evidence destination"):
        assert token in section


def test_wo537_global_wip_pins_borrowed_claim_limits() -> None:
    section = _norm(_section(_read_strict(SKILL), "Global WIP and no-collision rule"))
    assert "max 2 additional **borrowed mutable claims**" in section
    assert "total mutable claims may reach 5" in section
    assert "active mutation compute remains `<= 3`" in section
    assert "never increases active mutation above 3" in section


def test_wo530_kilo_goal_is_capability_gated_with_truthful_headless_fallback() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    for token in (
        "KILO_GOAL_CAPABILITY=VERIFIED",
        "KILO_GOAL_CAPABILITY=UNVERIFIED_HEADLESS",
        "POINTER_FALLBACK",
        "KILO_HEADLESS_PROBE=STALLED_NO_OUTPUT",
        "CHILD_ENTRY=POINTER_FALLBACK",
    ):
        assert token in section
    assert "forbids inventing slash-goal semantics" in section


def test_wo530_every_material_child_uses_durable_private_transport_and_fresh_quota() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    # P2 repair (R3 CHANGES_REQUIRED): the exact `sunday_dispatch` tool name
    # is the only valid child transport; generic durable dispatch, alternate
    # durable transports, and direct Kilo invocations are rejected.
    assert "`sunday_dispatch`" in section
    assert "Sunday durable dispatch" not in section
    assert "alternate durable transport" in section
    assert "direct Kilo invocation is not valid child transport" in section
    assert "non-`sunday_dispatch` transport" in section
    assert "explicit --dir" in section
    assert 'KILO_CONFIG_CONTENT={"share":"disabled"}' in section
    assert "CLI --no-share" in section
    assert "fresh CoinTH quota preflight immediately before dispatch" in section
    assert "INVALID_CHILD_EVIDENCE" in section


def test_wo530_glm_child_admission_requires_quota_and_upstream_readiness() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    # P3 repair: fresh proxy quota alone is never upstream readiness; both
    # structured facts plus the existing gates are required per dispatch.
    assert "proxy quota alone is never upstream readiness" in section
    assert (
        "PROXY_QUOTA_STATE=AVAILABLE AND UPSTREAM_PROVIDER_READINESS=READY" in section
    )
    assert "neither fact alone admits a dispatch" in section
    assert "never cached or hard-coded" in section
    assert re.search(
        r"UPSTREAM_PROVIDER_READINESS=THROTTLED.*wait until the declared reset/cooldown",
        section,
    )
    assert "PROXY_QUOTA_STATE=THROTTLED" not in section
    assert "do not repeated-probe" in section
    assert re.search(
        r"UPSTREAM_PROVIDER_READINESS=UNKNOWN.*fail closed for GLM", section
    )
    assert "GPT/Codex work may continue" in section


def test_wo530_child_terminal_harvest_refills_without_chat_turn_dependency() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    assert "RECOVER -> RECONCILE -> HARVEST -> recompute accepted READY frontier -> REFILL" in section
    assert "does not wait for a ChatGPT user turn" in section
    assert "Never manufacture work merely to consume quota" in section


def test_wo537_wait_aware_backfill_is_part_of_a_faster_skill() -> None:
    section = _norm(_section(_read_strict(SKILL), "Wait-aware auto-backfill"))
    assert "WAIT_AWARE_AUTO_BACKFILL" in section
    for state in (
        "WAITING_APPROVAL",
        "WAITING_CI",
        "WAITING_GLM",
        "WAITING_JEV",
        "WAITING_EXTERNAL",
        "COOLDOWN",
    ):
        assert state in section
    assert "A-NightShift" in section
    assert "SAFE_READY" in section
    assert "PARKED_CAPACITY" in section
    assert "at most 2 borrowed mutable claims" in section
    assert "never more than 3 simultaneous active mutations" in section


def test_wo537_wait_label_never_frees_active_mutation_child_slot() -> None:
    section = _norm(_section(_read_strict(SKILL), "Wait-aware auto-backfill"))
    assert "wait label alone never frees a mutable slot" in section
    assert "active delegated mutation child" in section
    assert "actual active-mutation evidence" in section
    assert "simultaneous active mutation stays `<= 3`" in section
    assert "1 MUTABLE HOTSPOT = 1 MUTATION OWNER" in _read_strict(SKILL)


def test_wo537_canonical_activation_removes_repeated_long_prompt_requirement() -> None:
    section = _norm(_section(_read_strict(SKILL), "Wait-aware auto-backfill"))
    assert "does not need to repeat" in section
    assert "continue" in section
    assert "A_FASTER_ACTIVE" in section
    assert "real goal/stop gate" in section
    assert "explicit deactivation" in section


def test_wo537_wait_resolution_harvests_then_contracts_without_destructive_preemption() -> None:
    section = _norm(_section(_read_strict(SKILL), "Wait-aware auto-backfill"))
    assert "RECOVER -> RECONCILE -> HARVEST" in section
    assert "bounded micro-step" in section
    assert "checkpoint" in section
    assert "PARKED_CAPACITY" in section
    assert (
        "contraction must never kill an owned task, reset git, stash unknown work"
        in section.lower()
    )


def test_wo530_model_roles_preserve_max_flash_and_jev_boundaries() -> None:
    section = _norm(_section(_read_strict(SKILL), "Hierarchical child-goal routing"))
    assert "GLM-5.3 MAX" in section
    assert "GLM-5.3 Flash" in section
    assert "TypeSafe-Jev" in section
    assert "authoritative_for_action=false" in section


# Issue #545 — Codex executor fallback while the GLM route is blocked.
def test_codex_executor_fallback_is_bounded_and_never_bypasses_glm_first() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Codex executor fallback"))
    for token in (
        "GLM_ROUTE_BLOCKED",
        "GPT-6 Luna",
        "effort max",
        "GPT-5.6 Sol",
        "GPT-6 Astra",
        "model identity grants no authority",
        "Codex supervisor",
        "never the primary engineer",
        "CODEX_EXECUTION_CAPACITY_EXHAUSTED",
    ):
        assert token in section
    assert "GLM-5.3 MAX remains the preferred heavy executor" in section
    assert "GLM_ROUTE_READY=TRUE" in section
    assert "fallback is forbidden" in section



def test_wo545_jev_system_one_fast_path_is_advisory_only() -> None:
    section = _norm(_section(_read_strict(SKILL), "JEV System-One advisory fast path"))
    for token in (
        "System-One advisory",
        "condition checks",
        "evidence relevance scoring",
        "route suggestions",
        "guardrail checks",
        "confidence",
        "accepted JEV authority",
        "advisory evidence only",
        "NEXT_READY authority",
    ):
        assert token in section
    assert "Never manufacture JEV calls" in section


def test_wo545_device_capacity_discovers_workers_and_mac_without_multiplying_wip() -> None:
    text = _read_strict(SKILL)
    section = _norm(_section(text, "Device resource capacity projection"))
    assert "SunDay-Worker 1..5" in section
    assert "SundayMCP Mac" in section
    assert "ONLINE/READY" in section
    assert "capacity evidence, not as extra authority" in section
    assert "never multiplies the global WIP budget" in section
    assert "3 simultaneously active mutable lanes" in section
    assert "Issue #340" in section
    routes = _norm(_section(text, "Default device execution routes"))
    assert "SundayMCP Mac" in routes
    assert "RDC secondarily" in routes
