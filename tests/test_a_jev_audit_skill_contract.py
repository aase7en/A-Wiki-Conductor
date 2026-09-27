from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".agents" / "skills" / "a-jev-audit" / "SKILL.md"
QUOTA_RUNBOOK = ROOT / "docs" / "runbooks" / "cointh-glm-quota.md"


def normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_skill_has_valid_identity_and_only_audit_trigger() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert text.startswith("---\nname: a-jev-audit\n")
    frontmatter = text.split("---\n", 2)[1]
    assert "description:" in frontmatter
    assert "does not call a provider" in frontmatter.lower()
    assert "A-JEV-Audit" in text


def test_audit_has_exactly_four_dispositions_and_non_authority_boundary() -> None:
    text = normalized(SKILL)

    for disposition in (
        "`FIT`",
        "`SHADOW_ONLY`",
        "`NO_FIT`",
        "`INSUFFICIENT_EVIDENCE`",
    ):
        assert disposition in text

    assert "JEV output cannot authorize actions" in text
    assert "does not itself authorize a call" in text
    assert "deterministic policy/integrator" in text
    assert "another provider/router" in text


def test_quota_freshness_and_provider_dimensions_stay_separate() -> None:
    text = normalized(SKILL)
    quota = normalized(QUOTA_RUNBOOK)

    assert "docs/runbooks/cointh-glm-quota.md" in text
    assert "GET https://cointh.com/glm/api/quota" in text
    assert "x-api-key" in text
    for field in (
        "remaining_5h",
        "used_5h",
        "limit_5h",
        "window_reset_at",
        "window_reset_in_sec",
    ):
        # The canonical runbook owns field definitions; the skill points to it.
        assert field in quota
    assert "window_source=stale" in text
    assert "not exhaustion" in text
    assert "CoinTH proxy quota is only GLM account evidence" in text
    assert "TypeSafe-JEV quota or TypeSafe readiness" in text


def test_secret_rotation_and_no_live_call_gate_are_explicit() -> None:
    text = normalized(SKILL)

    assert "previously exposed in chat" in text
    assert "Presence in an approved resolver is not rotation proof" in text
    assert "LIVE_JEV_ALLOWED=NO" in text
    assert "must never read or print the key" in text
    assert "This audit is read-only and makes no provider call" in text


def test_liveness_unknown_does_not_block_independent_authorized_route() -> None:
    text = normalized(SKILL)

    assert "Device availability, execution liveness, JEV readiness, and GLM" in text
    assert "blocks work that requires that surface only" in text
    assert "never grants cancellation, takeover, or duplicate dispatch" in text
    assert "Never wait for an unrelated device" in text
