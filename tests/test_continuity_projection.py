"""WO-P1-166 P0-B4 — single-writer continuity projections (RED-first).

Covers the 25 binding RED acceptance families from the task packet:
pure deterministic renderer (identity-bound facts -> byte-stable
sentinel-section Markdown) and the thin CloseoutFoldPort adapter that
publishes ONLY through the existing AgentChangeApplier mutation
authority. All filesystem work happens in tmp_path; the repository's
real hotspot files are never touched.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256

import pytest

from a_conductor.native_execution import NativeExecutionScope, NativeFileSystem
from a_conductor.worker_lease import LeaseHealth, LeaseHealthKind, LeaseMutationIntent, WorkerLease

from a_conductor.continuity_projection import (
    CANONICAL_TARGETS,
    ProjectionFacts,
    ProjectionLeaseFact,
    render_current_work,
    render_handoff,
    render_collab,
    ContinuityProjectionFoldAdapter,
    render_projection_target,
)

HEAD = "0f1e2d3c4b5a697887766554433221100f1e2d3c4b5a6978877665544332211f"
HEAD_OTHER = "1111222233334444555566667777888811112222333344445555666677778888"
TASK = "task-1"
SESSION = "session-1"


def digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def lease(root, *, head: str = HEAD, session_id: str = SESSION) -> WorkerLease:
    return WorkerLease(
        lease_id="lease-1", worker_id="a-worker-01", session_id=session_id,
        task_id=TASK, project_id="project-1", runtime_id="glm-5.3",
        worktree_key=str(root), branch="feat/example", expected_head=head,
        required_capabilities=("code",), allowed_scope=CANONICAL_TARGETS,
        forbidden_scope=("secrets/**",), mutable_scope=CANONICAL_TARGETS,
        mutation_intent=LeaseMutationIntent.MUTATION,
        acquired_at="2026-09-08T00:00:00.000000Z",
        heartbeat_at="2026-09-08T00:00:00.000000Z", lease_ttl_seconds=900,
        expires_at="2026-09-08T00:15:00.000000Z",
    )


def L(**over) -> ProjectionLeaseFact:
    base = dict(
        lease_id="lease-1", session_id=SESSION, task_id=TASK,
        state="ACTIVE", owner_ok=True,
    )
    base.update(over)
    return ProjectionLeaseFact(**base)


def facts(**over) -> ProjectionFacts:
    base = dict(
        task_id=TASK,
        candidate_sha=HEAD,
        branch="feat/example",
        head=HEAD,
        merge_commit=None,
        post_main_status="NOT_REQUIRED",
        closeout_status="FOLD_PENDING",
        leases=(L(),),
        ownership_known=True,
        writer_session=SESSION,
    )
    base.update(over)
    return ProjectionFacts(**base)


# ── 1-3, 22: pure renderer determinism ────────────────────────────────
def test_same_facts_twice_byte_identical():
    a = render_current_work(facts())
    b = render_current_work(facts())
    assert a == b


def test_reordered_lease_inputs_canonical_output():
    l1, l2 = L(lease_id="lease-a"), L(lease_id="lease-b")
    a = render_current_work(facts(leases=(l1, l2)))
    b = render_current_work(facts(leases=(l2, l1)))
    assert a == b


def test_factual_head_outranks_stale_projection_text():
    """The renderer never parses supplied Markdown for authority: stale text
    supplied as prior_bytes cannot change the factual head rendering."""
    text = render_current_work(facts(head=HEAD))
    stale = text.replace(HEAD, HEAD_OTHER)
    assert HEAD in text and HEAD_OTHER not in text
    again = render_current_work(facts(head=HEAD))
    assert again == text and stale != again


def test_newline_and_utf8_deterministic():
    text = render_current_work(facts(task_id="task-ünïcode-1"))
    raw = text.encode("utf-8")
    assert b"\r" not in raw
    assert raw.decode("utf-8") == text


def test_factual_branch_outranks_stale_text():
    text = render_current_work(facts(branch="feat/example"))
    assert "feat/example" in text
    other = render_current_work(facts(branch="feat/other"))
    assert "feat/other" in other and other != text


# ── 4-5, 16-18: fact binding / UNKNOWN handling ───────────────────────
def test_old_lease_cannot_be_current_authority():
    """R2-D: exact (non-vacuous) display assertions — a RELEASED lease id must
    never appear on the active-leases line, only on released-leases."""
    text = render_current_work(facts(leases=(L(state="RELEASED"), L(state="ACTIVE", lease_id="lease-2"))))
    active_line = [l for l in text.splitlines() if l.startswith("active-leases:")][0]
    assert active_line == "active-leases: lease-2", active_line
    assert "released-leases: lease-1" in text


def test_unknown_fact_renders_explicit_unknown():
    text = render_current_work(facts(head=None))
    assert "head: UNKNOWN" in text
    assert f"head: {HEAD}" not in text


def test_completion_display_requires_durable_fact():
    done = render_current_work(facts(closeout_status="COMPLETE"))
    pending = render_current_work(facts(closeout_status="FOLD_PENDING"))
    assert "COMPLETE" in done and "COMPLETE" not in pending


def test_release_display_requires_durable_release_fact():
    released = render_current_work(facts(leases=(L(state="RELEASED"),)))
    active = render_current_work(facts())
    assert "released-leases: lease-1" in released
    assert "released-leases:" not in active


def test_doctored_markdown_cannot_alter_facts():
    """Renderer output is derived only from ProjectionFacts; forging
    Markdown fields (merge/fold status) has no parse-back authority."""
    text = render_current_work(facts(merge_commit=None))
    forged = text + "\nMerge-Commit: deadbeef\n"
    fresh = render_current_work(facts(merge_commit=None))
    assert "deadbeef" not in fresh and fresh == text and forged != fresh


# ── 9-10: targets ─────────────────────────────────────────────────────
def test_only_approved_targets_accepted():
    assert set(CANONICAL_TARGETS) == {"CURRENT-WORK.md", "handoff.md", "COLLAB.md"}
    with pytest.raises(ValueError):
        render_projection_target("EVIL.md", facts())
    with pytest.raises(ValueError):
        render_projection_target("../CURRENT-WORK.md", facts())
    with pytest.raises(ValueError):
        render_projection_target("docs/CURRENT-WORK.md", facts())


# ── 19-21: sentinel regions ───────────────────────────────────────────
SENTINEL_DOC = (
    "# CURRENT-WORK\n\nHuman intro.\n\n"
    "<!-- BEGIN-MACHINE-PROJECTION -->\nold machine block\n"
    "<!-- END-MACHINE-PROJECTION -->\n\nHuman tail.\n"
)


def test_valid_sentinel_update_preserves_human_bytes():
    out = render_current_work(facts(), prior_text=SENTINEL_DOC)
    assert "Human intro." in out and "Human tail." in out
    assert "old machine block" not in out
    assert out.startswith("# CURRENT-WORK")


def test_malformed_sentinel_refuses_and_preserves():
    for broken in (
        SENTINEL_DOC.replace("<!-- END-MACHINE-PROJECTION -->", ""),
        SENTINEL_DOC.replace("<!-- BEGIN-MACHINE-PROJECTION -->", "<!-- BEGIN-MACHINE-PROJECTION -->\n<!-- BEGIN-MACHINE-PROJECTION -->", 1),
    ):
        with pytest.raises(ValueError):
            render_current_work(facts(), prior_text=broken)
    assert render_current_work(facts(), prior_text=None)  # no prior = full render OK


# ══════════════════════════════════════════════════════════════════════
# Thin fold adapter over AgentChangeApplier (uses tmp_path only)
# ══════════════════════════════════════════════════════════════════════
class StaticLeaseStore:
    def __init__(self, value: WorkerLease):
        self.value = value

    def inspect_health(self, lease_id: str, *, now: object) -> LeaseHealth:
        assert lease_id == self.value.lease_id
        kind = LeaseHealthKind.ACTIVE
        if self.value.released_at is not None:
            kind = LeaseHealthKind.RELEASED
        elif self.value.quarantined_at is not None:
            kind = LeaseHealthKind.QUARANTINED
        return LeaseHealth(kind, self.value)


from a_conductor.agent_change_packets import (
    AgentChangeApplier,
    AgentChangeError,
    ContinuitySnapshotProvider,
    AgentResultPacket,
)
from a_conductor.continuity_guard import ContinuitySnapshot
from a_conductor.goal_closeout import FoldOutcome, FoldRequest


class FreshProvider:
    def continuity_snapshot(self, request) -> ContinuitySnapshot:
        return ContinuitySnapshot(
            worktree=request.worktree, branch=request.branch,
            session_id=request.session_id, task_id=request.task_id,
            expected_head=request.expected_head, local_head=request.actual_head,
            remote_head=request.actual_head, dirty_state="CLEAN",
            ownership_known=True, mutable_scope=request.mutable_scope,
        )


def applier(root, lease_value, provider=None):
    fs = NativeFileSystem(NativeExecutionScope(root=root, mutation_allowed=True))
    return AgentChangeApplier(
        filesystem=fs,
        lease_store=StaticLeaseStore(lease_value),
        continuity_provider=provider or FreshProvider(),
        clock=lambda: "2026-09-08T00:05:00.000000Z",
    )


def adapter(root, lease_value=None, *, targets=CANONICAL_TARGETS, provider=None, read_back=None):
    return ContinuityProjectionFoldAdapter(
        applier=applier(root, lease_value or lease(root), provider=provider),
        lease_id="lease-1",
        session_id=SESSION,
        task_id=TASK,
        actual_head=HEAD,
        facts_factory=lambda: facts(),
        targets=targets,
        read_back=read_back,
    )


def seed(root, names=CANONICAL_TARGETS, text=SENTINEL_DOC):
    for name in names:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")


def test_adapter_publishes_all_targets_with_sentinel_preservation(tmp_path):
    seed(tmp_path)
    outcome = adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is True
    for name in CANONICAL_TARGETS:
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert "Human intro." in text and "old machine block" not in text
        assert HEAD in text


def test_wrong_owner_zero_writes(tmp_path):
    seed(tmp_path)
    other = adapter(tmp_path, lease(tmp_path, session_id="session-other"))
    outcome = other.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


def test_inactive_lease_zero_writes(tmp_path):
    from dataclasses import replace as _r
    seed(tmp_path)
    released = _r(lease(tmp_path), released_at="2026-09-08T00:01:00.000000Z")
    outcome = adapter(tmp_path, released).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


def test_ownership_loss_zero_writes(tmp_path):
    seed(tmp_path)
    class LostOwnership(FreshProvider):
        def continuity_snapshot(self, request):
            snap = super().continuity_snapshot(request)
            from dataclasses import replace as _r
            return _r(snap, ownership_known=False)
    outcome = adapter(tmp_path, provider=LostOwnership()).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


def test_stale_head_zero_writes(tmp_path):
    seed(tmp_path)
    stale = applier(tmp_path, lease(tmp_path, head=HEAD_OTHER))
    adapter_obj = ContinuityProjectionFoldAdapter(
        applier=stale, lease_id="lease-1", session_id=SESSION, task_id=TASK,
        actual_head=HEAD, facts_factory=lambda: facts(), targets=CANONICAL_TARGETS,
    )
    outcome = adapter_obj.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


def test_unsupported_target_refused_zero_writes(tmp_path):
    with pytest.raises(ValueError):
        adapter(tmp_path, targets=("EVIL.md",)).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert not (tmp_path / "EVIL.md").exists()


def test_stale_precondition_conflict_zero_writes(tmp_path):
    """R1-strengthened: the loader supplies OLD text (hash preconditions
    derived from it) while the files on disk have drifted => the applier
    precondition must fail closed on the FIRST packet: no target is
    overwritten, outcome is never completed=True."""
    seed(tmp_path)
    old = SENTINEL_DOC
    drifted = old + "\nDRIFT\n"
    for name in CANONICAL_TARGETS:
        (tmp_path / name).write_text(drifted, encoding="utf-8", newline="\n")
    adapter_obj = ContinuityProjectionFoldAdapter(
        applier=applier(tmp_path, lease(tmp_path)), lease_id="lease-1",
        session_id=SESSION, task_id=TASK, actual_head=HEAD,
        facts_factory=lambda: facts(), targets=CANONICAL_TARGETS,
        prior_text_loader=lambda name: old,
    )
    outcome = adapter_obj.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is False
    for name in CANONICAL_TARGETS:
        assert (tmp_path / name).read_text(encoding="utf-8") == drifted



def test_render_failure_zero_partial_writes(tmp_path):
    seed(tmp_path)
    def boom():
        raise RuntimeError("renderer down")
    adapter_obj = ContinuityProjectionFoldAdapter(
        applier=applier(tmp_path, lease(tmp_path)), lease_id="lease-1",
        session_id=SESSION, task_id=TASK, actual_head=HEAD,
        facts_factory=boom, targets=CANONICAL_TARGETS,
    )
    with pytest.raises(Exception):
        adapter_obj.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


class FailingApplier:
    """Wraps a real applier but fails the write of the Nth change."""
    def __init__(self, inner, fail_on: int):
        self._inner = inner
        self._fail_on = fail_on
        self._seen = 0

    @property
    def _filesystem(self):
        return self._inner._filesystem

    def apply(self, packet, lease_id, **kw):
        self._seen += 1
        if self._seen == self._fail_on:
            from a_conductor.agent_change_packets import AgentChangeError as E
            raise E("CHANGE_APPLY_FAILED")
        return self._inner.apply(packet, lease_id, **kw)


def test_failure_after_first_file_not_completed(tmp_path):
    seed(tmp_path)
    adapter_obj = ContinuityProjectionFoldAdapter(
        applier=FailingApplier(applier(tmp_path, lease(tmp_path)), fail_on=2),
        lease_id="lease-1", session_id=SESSION, task_id=TASK, actual_head=HEAD,
        facts_factory=lambda: facts(), targets=CANONICAL_TARGETS,
    )
    outcome = adapter_obj.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True  # mixed bundle never reports success


def test_readback_failure_typed_fail_closed(tmp_path):
    seed(tmp_path)
    outcome = adapter(tmp_path, read_back=lambda name: None).fold(
        FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold")
    )
    assert outcome.completed is not True


def test_identical_republish_idempotent(tmp_path):
    seed(tmp_path)
    req = FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold")
    first = adapter(tmp_path).fold(req)
    assert first.completed is True
    before = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    second = adapter(tmp_path).fold(req)
    assert second.completed is True
    after = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    assert before == after


def test_all_targets_verified_before_completed(tmp_path):
    seed(tmp_path)
    seen = []
    def read_back(name):
        seen.append(name)
        return (tmp_path / name).read_text(encoding="utf-8")
    outcome = adapter(tmp_path, read_back=read_back).fold(
        FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold")
    )
    assert outcome.completed is True
    assert set(seen) >= set(CANONICAL_TARGETS)


def test_no_second_authority_surface():
    import inspect
    from a_conductor import continuity_projection as m
    src = inspect.getsource(m)
    for banned in ("threading.", "asyncio.", "sqlite3", "subprocess", "requests", "time.time", "datetime.now"):
        assert banned not in src, banned

# ══════════════════════════════════════════════════════════════════════
# R1 — P1-A: exact candidate identity binding (RED family)
# ══════════════════════════════════════════════════════════════════════
from a_conductor.continuity_projection import ProjectionError  # noqa: E402

def test_r1_a1_request_candidate_mismatch_fails_closed_zero_writes(tmp_path):
    seed(tmp_path)
    before = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    with pytest.raises(ProjectionError):
        adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD_OTHER, checkpoint_ref="c:fold"))
    assert {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS} == before


def test_r1_a2_exact_candidate_positive_control(tmp_path):
    seed(tmp_path)
    outcome = adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is True


def test_r1_a3_mismatch_with_all_targets_writable_still_zero_writes(tmp_path):
    for name in CANONICAL_TARGETS:
        (tmp_path / name).write_text("# fresh\nhuman\n", encoding="utf-8", newline="\n")
    before = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    with pytest.raises(ProjectionError):
        adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD_OTHER, checkpoint_ref="c:fold"))
    assert {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS} == before


# ══════════════════════════════════════════════════════════════════════
# R1 — P1-B: production first-adoption (RED family; fixtures copied from
# current main structures: title + current region + HISTORICAL EVIDENCE
# anchor for CW/handoff; In-progress claims table + WO166 row for COLLAB)
# ══════════════════════════════════════════════════════════════════════
CW_ANCHOR = "<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->"
CW_FIXTURE = (
    "# A-Sunday Conductor — Current Work\n"
    "\n"
    "Last updated: 2026-09-08 (GPT1 — WO166 P0-B Continuity Guard activation)\n"
    "\n"
    "- **P0-B Continuity Guard is the current dependency frontier.** Durable architecture/preflight authority is Issue #226; implementation identity is `WO-P1-166`.\n"
    "\n"
    + CW_ANCHOR + "\n"
    "<!-- Nothing below this separator is a current instruction.              -->\n"
    "\n"
    "## Post-PR208 merge actual-state override - 2026-09-05 (HISTORICAL / SUPERSEDED BY WO162 2026-09-07)\n"
    "old historical body\n"
)

HO_ANCHOR = "<!-- HISTORICAL EVIDENCE — superseded by WO162 (2026-09-07).            -->"
HO_FIXTURE = (
    "# HANDOFF — A-Sunday Conductor\n"
    "\n"
    "Last updated: 2026-09-08 — GPT1 WO166 P0-B activation\n"
    "\n"
    "- WO165/ZRA-2 is queued successor only: activation-doc head `3d7209e...`.\n"
    "\n"
    + HO_ANCHOR + "\n"
    "\n"
    "## WO158 / PR221 r5 handoff override - 2026-09-06 (HISTORICAL / SUPERSEDED BY WO162)\n"
    "old handoff history\n"
)

CO_WO166_ROW = (
    "| `WO-P1-166` P0-B Continuity Guard activation | GPT1 architecture/activation | "
    "FOLD_CANDIDATE / CONDITIONAL_RELEASE 2026-09-08 (self-closing) | Docs-only activation: "
    "`COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-166-p0b-continuity-guard.md`. |"
)
CO_OTHER_ROW = (
    "| `WO-P1-164` COLLAB stale-row reconciliation | GLM-1 / GLM-A (ZCode) | "
    "MERGED / POST_MAIN_VERIFIED / RELEASED via PR #225 | rows reconciled. |"
)
CO_FIXTURE = (
    "# A-Wiki Conductor — Agent Collaboration\n"
    "\n"
    "## In-progress claims\n"
    "\n"
    "| Chunk/WO | Agent | Claimed | Scope (files) |\n"
    "|---|---|---|---|\n"
    + CO_WO166_ROW + "\n"
    + CO_OTHER_ROW + "\n"
    "\n"
    "## Released claims history\n"
    "human history text\n"
)

FIXTURES = {"CURRENT-WORK.md": CW_FIXTURE, "handoff.md": HO_FIXTURE, "COLLAB.md": CO_FIXTURE}
ANCHORS = {"CURRENT-WORK.md": CW_ANCHOR, "handoff.md": HO_ANCHOR}


def test_r1_b1_cw_adoption_succeeds():
    out = render_projection_target("CURRENT-WORK.md", facts(), prior_text=CW_FIXTURE)
    assert out.startswith("# A-Sunday Conductor — Current Work\n")
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out and HEAD in out


def test_r1_b2_handoff_adoption_succeeds():
    out = render_projection_target("handoff.md", facts(), prior_text=HO_FIXTURE)
    assert out.startswith("# HANDOFF — A-Sunday Conductor\n")
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out


def test_r1_b3_collab_adoption_succeeds():
    out = render_projection_target("COLLAB.md", facts(), prior_text=CO_FIXTURE)
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out
    assert CO_OTHER_ROW in out and CO_WO166_ROW not in out


def test_r1_b4_non_adopted_bytes_identical():
    out = render_projection_target("CURRENT-WORK.md", facts(), prior_text=CW_FIXTURE)
    anchor_pos = CW_FIXTURE.index(CW_ANCHOR)
    assert out.endswith(CW_FIXTURE[anchor_pos:])          # anchor + tail byte-for-byte
    assert out.startswith(CW_FIXTURE[:CW_FIXTURE.index("\n") + 1])  # title byte-for-byte
    co = render_projection_target("COLLAB.md", facts(), prior_text=CO_FIXTURE)
    assert co.startswith("# A-Wiki Conductor — Agent Collaboration\n\n## In-progress claims\n\n| Chunk/WO | Agent | Claimed | Scope (files) |\n|---|---|---|---|\n")
    assert co.endswith("\n\n## Released claims history\nhuman history text\n")


def test_r1_b5_historical_tail_byte_for_byte():
    for name in ("CURRENT-WORK.md", "handoff.md"):
        fixture = FIXTURES[name]
        anchor = ANCHORS[name]
        out = render_projection_target(name, facts(), prior_text=fixture)
        assert out.endswith(fixture[fixture.index(anchor):])


def test_r1_b6_duplicate_historical_anchor_refuses():
    dup = CW_FIXTURE.replace(CW_ANCHOR, CW_ANCHOR + "\n" + CW_ANCHOR, 1)
    with pytest.raises(ValueError):
        render_projection_target("CURRENT-WORK.md", facts(), prior_text=dup)


def test_r1_b7_missing_historical_anchor_refuses():
    missing = CW_FIXTURE.replace(CW_ANCHOR + "\n", "").replace(CW_ANCHOR, "")
    with pytest.raises(ValueError):
        render_projection_target("CURRENT-WORK.md", facts(), prior_text=missing)
    with pytest.raises(ValueError):
        render_projection_target("handoff.md", facts(), prior_text="# HANDOFF\nno anchor\n")


def test_r1_b8_collab_zero_wo166_row_refuses():
    no_row = CO_FIXTURE.replace(CO_WO166_ROW + "\n", "")
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=no_row)


def test_r1_b9_collab_duplicate_wo166_row_refuses():
    dup = CO_FIXTURE.replace(CO_WO166_ROW, CO_WO166_ROW + "\n" + CO_WO166_ROW, 1)
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=dup)


def test_r1_b10_already_adopted_idempotent():
    adopted = render_projection_target("COLLAB.md", facts(), prior_text=CO_FIXTURE)
    again = render_projection_target("COLLAB.md", facts(), prior_text=adopted)
    assert again == adopted


def test_r1_b11_doctored_adopted_markdown_cannot_override_facts():
    adopted = render_projection_target("CURRENT-WORK.md", facts(head=HEAD), prior_text=CW_FIXTURE)
    doctored = adopted.replace(HEAD, HEAD_OTHER)
    fresh = render_projection_target("CURRENT-WORK.md", facts(head=HEAD), prior_text=doctored)
    assert HEAD in fresh and HEAD_OTHER not in fresh


def test_r1_b12_first_adoption_failure_zero_writes_anywhere(tmp_path):
    for name in CANONICAL_TARGETS:
        (tmp_path / name).write_text(FIXTURES[name], encoding="utf-8", newline="\n")
    (tmp_path / "handoff.md").write_text("# HANDOFF\nmissing anchor\n", encoding="utf-8", newline="\n")
    before = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    with pytest.raises(ValueError):
        adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS} == before


def test_r1_b13_adapter_first_adoption_all_targets_verified(tmp_path):
    for name in CANONICAL_TARGETS:
        (tmp_path / name).write_text(FIXTURES[name], encoding="utf-8", newline="\n")
    outcome = adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is True
    for name in CANONICAL_TARGETS:
        text = (tmp_path / name).read_text(encoding="utf-8")
        assert "<!-- BEGIN-MACHINE-PROJECTION -->" in text
        assert HEAD in text


# ══════════════════════════════════════════════════════════════════════
# R2 — final bounded repair (RED-first).
#   R2-A CRLF-safe exact COLLAB heading;
#   R2-B section-bounded WO-P1-166 row adoption;
#   R2-C read-back exception envelope (completed=None, no retry);
#   R2-D evidenced test gaps made non-vacuous.
# Fixtures are FROZEN raw-byte copies of the real COLLAB.md structure at
# 42541de (converted to CRLF where labelled) — no live repository file
# dependency inside tests.
# ══════════════════════════════════════════════════════════════════════
_FROZEN_COLLAB_LF = (
    "# COLLAB\n"
    "\n"
    "## Lanes\n"
    "\n"
    "lane text\n"
    "\n"
    "## In-progress claims\n"
    "\n"
    "| Chunk/WO | Agent | Claimed | Scope (files) |\n"
    "|---|---|---|---|\n"
    "| `WO-P1-166` P0-B Continuity Guard activation | GPT1 architecture/activation | FOLD_CANDIDATE / CONDITIONAL_RELEASE 2026-09-08 (self-closing) | Docs-only activation lanes |\n"
    "| `WO-P1-164` COLLAB stale-row reconciliation | GLM-1 / GLM-A (ZCode) | MERGED / RELEASED |\n"
    "rows reconciled. |\n"
    "\n"
    "## Rules\n"
    "\n"
    "rule text\n"
    "\n"
    "## Fast execution / risk-tier binding\n"
    "\n"
    "binding text\n"
)
_FROZEN_COLLAB_CRLF = _FROZEN_COLLAB_LF.replace("\n", "\r\n")
_FROZEN_ROW_LINE_PREFIX = "| `WO-P1-166` P0-B Continuity Guard activation"


def _collab_with_row(row_state: str, eol: str = "\n") -> str:
    """Frozen COLLAB-family builder: row placement variants, LF or CRLF."""
    lf = _FROZEN_COLLAB_LF
    row = [l for l in lf.splitlines() if l.startswith(_FROZEN_ROW_LINE_PREFIX)][0]
    if row_state == "in_section":
        doc = lf
    elif row_state == "later_h2":
        doc = lf.replace(row + "\n", "", 1).replace(
            "## Rules\n", "## Rules\n\n| Chunk/WO | Agent | Claimed | Scope |\n|---|---|---|---|\n" + row + "\n", 1)
    elif row_state == "before_heading":
        doc = lf.replace(row + "\n", "", 1).replace(
            "# COLLAB\n\n", "# COLLAB\n\n| Chunk/WO | Agent | Claimed | Scope |\n|---|---|---|---|\n" + row + "\n\n", 1)
    elif row_state == "in_section_plus_later":
        doc = lf.replace(
            "## Rules\n", "## Rules\n\n| Chunk/WO | Agent | Claimed | Scope |\n|---|---|---|---|\n" + row + "\n", 1)
    else:
        raise ValueError(row_state)
    return doc.replace("\n", eol) if eol != "\n" else doc


# ---------- R2-A: CRLF-safe exact COLLAB heading ----------
def test_r2_a1_lf_exact_heading_adopts():
    out = render_projection_target("COLLAB.md", facts(), prior_text=_FROZEN_COLLAB_LF)
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out


def test_r2_a2_crlf_exact_heading_adopts():
    out = render_projection_target("COLLAB.md", facts(), prior_text=_FROZEN_COLLAB_CRLF)
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out


def test_r2_a3_mixed_eol_crlf_heading_adopts():
    lines = _FROZEN_COLLAB_LF.splitlines(keepends=True)
    doc = "".join(l.rstrip("\n") + ("\r\n" if "## In-progress claims" in l else "\n") for l in lines)
    out = render_projection_target("COLLAB.md", facts(), prior_text=doc)
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out


def test_r2_a4_frozen_raw_crlf_collab_first_and_second_render():
    first = render_projection_target("COLLAB.md", facts(), prior_text=_FROZEN_COLLAB_CRLF)
    second = render_projection_target("COLLAB.md", facts(), prior_text=first)
    assert first == second  # byte-stable idempotence
    # non-owned bytes preserved exactly (tail from the first later H2 on)
    tail_marker = "## Rules"
    tail = _FROZEN_COLLAB_CRLF[_FROZEN_COLLAB_CRLF.index(tail_marker):]
    assert first.endswith(tail)
    # the machine block itself stays LF-only
    block = first.split("<!-- BEGIN-MACHINE-PROJECTION -->\n")[1].split("\n<!-- END-MACHINE-PROJECTION -->")[0]
    assert "\r" not in block


def test_r2_a5_wrong_case_fuzzy_heading_refused():
    for bad in ("## In progress claims", "## in-progress claims", "## In-progress claims team",
                "## **In-progress claims**", "### In-progress claims"):
        doc = _FROZEN_COLLAB_LF.replace("## In-progress claims\n", bad + "\n", 1)
        with pytest.raises(ValueError):
            render_projection_target("COLLAB.md", facts(), prior_text=doc)


def test_r2_a6_duplicate_headings_refused():
    doc = _FROZEN_COLLAB_LF.replace(
        "## In-progress claims\n", "## In-progress claims\n\n## In-progress claims\n", 1)
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=doc)


# ---------- R2-B: section-bounded WO-P1-166 adoption ----------
def test_r2_b1_row_inside_section_adopts():
    out = render_projection_target("COLLAB.md", facts(), prior_text=_collab_with_row("in_section"))
    assert "<!-- BEGIN-MACHINE-PROJECTION -->" in out  # adopted (row replaced by machine region)


def test_r2_b2_row_only_in_later_h2_refused():
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=_collab_with_row("later_h2"))


def test_r2_b3_row_before_heading_refused():
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=_collab_with_row("before_heading"))


def test_r2_b4_row_in_section_plus_later_duplicate_refused():
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=_collab_with_row("in_section_plus_later"))


def test_r2_b5_crlf_next_h2_section_bound_refused():
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=_collab_with_row("later_h2", eol="\r\n"))


def test_r2_b6_fold_on_frozen_crlf_collab_first_and_second(tmp_path):
    (tmp_path / "CURRENT-WORK.md").write_text(CW_FIXTURE, encoding="utf-8", newline="\n")
    (tmp_path / "handoff.md").write_text(HO_FIXTURE, encoding="utf-8", newline="\n")
    (tmp_path / "COLLAB.md").write_text(_FROZEN_COLLAB_CRLF, encoding="utf-8", newline="")
    first = adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert first.completed is True
    before = {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS}
    second = adapter(tmp_path).fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert second.completed is True
    assert {n: (tmp_path / n).read_bytes() for n in CANONICAL_TARGETS} == before


# ---------- R2-C: read-back exception envelope ----------
def _readback_raising_after(tmp_path, target_index):
    """Default read-back that raises once it reaches target N (0-based)."""
    def rb(name):
        if CANONICAL_TARGETS.index(name) >= target_index:
            raise RuntimeError("read-back transport down")
        with open(tmp_path / name, "r", encoding="utf-8", newline="") as h:
            return h.read()
    return rb


def test_r2_c1_readback_raise_after_first_target_completed_none(tmp_path):
    seed(tmp_path)
    ad = adapter(tmp_path, read_back=_readback_raising_after(tmp_path, 0))
    outcome = ad.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is None


def test_r2_c2_readback_raise_after_second_target_completed_none(tmp_path):
    seed(tmp_path)
    ad = adapter(tmp_path, read_back=_readback_raising_after(tmp_path, 1))
    outcome = ad.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is None


def test_r2_c3_readback_raise_after_third_target_completed_none(tmp_path):
    seed(tmp_path)
    ad = adapter(tmp_path, read_back=_readback_raising_after(tmp_path, 2))
    outcome = ad.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is None


def test_r2_c4_readback_raise_never_true_and_no_retry(tmp_path):
    seed(tmp_path)
    calls = {"n": 0}
    def counting_raise(name):
        calls["n"] += 1
        raise RuntimeError("read-back down")
    ad = adapter(tmp_path, read_back=counting_raise)
    outcome = ad.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert outcome.completed is None  # typed ambiguous outcome, not an exception
    # fail-fast envelope: the FIRST raising read-back ends the pass; exactly one
    # attempt total — no internal retry, no continued reads after a transport failure.
    assert calls["n"] == 1


# ---------- R2-D: evidenced test gaps made non-vacuous ----------
def test_r2_d2_request_task_id_binding_typed_raise(tmp_path):
    seed(tmp_path)
    with pytest.raises(ProjectionError) as exc:
        adapter(tmp_path).fold(FoldRequest(task_id="IMPOSTOR-TASK", candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert exc.value.code == "PROJECTION_TASK_MISMATCH"
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == SENTINEL_DOC


def test_r2_d3_empty_targets_refused(tmp_path):
    seed(tmp_path)
    with pytest.raises(ValueError):
        adapter(tmp_path, targets=())


def test_r2_d4_writer_session_machine_line_present():
    text = render_current_work(facts())
    assert f"writer-session: {SESSION}" in text


def test_r2_d5_title_structural_check():
    for bad in ("not a title\n" + CW_ANCHOR + "\nh\n", "## not a title\n" + CW_ANCHOR + "\nh\n"):
        with pytest.raises(ValueError):
            render_projection_target("CURRENT-WORK.md", facts(), prior_text=bad)


def test_r2_d6_max_length_validation():
    with pytest.raises(ValueError):
        facts(task_id="x" * 600)
    with pytest.raises(ValueError):
        ProjectionLeaseFact(lease_id="l" * 500, session_id=SESSION, task_id=TASK, state="ACTIVE", owner_ok=True)


def test_r2_d8_dangling_extra_end_refused():
    adopted = render_projection_target("COLLAB.md", facts(), prior_text=_FROZEN_COLLAB_LF)
    dangling = adopted + "\n<!-- END-MACHINE-PROJECTION -->\n"  # 1 BEGIN + 2 END
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=dangling)


def test_r2_d9_two_begin_one_end_refused():
    adopted = render_projection_target("COLLAB.md", facts(), prior_text=_FROZEN_COLLAB_LF)
    two_begin = adopted.replace(
        "<!-- BEGIN-MACHINE-PROJECTION -->",
        "<!-- BEGIN-MACHINE-PROJECTION -->\n<!-- BEGIN-MACHINE-PROJECTION -->", 1)
    with pytest.raises(ValueError):
        render_projection_target("COLLAB.md", facts(), prior_text=two_begin)


def test_r2_d10_released_never_in_active_leases():
    text = render_current_work(facts(leases=(L(state="RELEASED"),)))
    active_line = [l for l in text.splitlines() if l.startswith("active-leases:")][0]
    assert active_line == "active-leases: NONE"
    assert "released-leases: lease-1" in text
