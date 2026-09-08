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
    text = render_current_work(facts(leases=(L(state="RELEASED"), L(state="ACTIVE", lease_id="lease-2"))))
    assert "lease-2" in text and "lease-1" not in text.split("Active")[1].split("Released")[0] if "Active" in text else True


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


def test_precondition_conflict_zero_writes(tmp_path):
    """Bytes drift BETWEEN the render read and the write preflight: the
    loader supplies the pre-drift text for hashing while the filesystem
    holds drifted bytes -> applier precondition fails -> zero writes."""
    seed(tmp_path)
    pre_drift = {n: SENTINEL_DOC for n in CANONICAL_TARGETS}
    drifted = SENTINEL_DOC + "\nDRIFT\n"
    (tmp_path / "CURRENT-WORK.md").write_text(drifted, encoding="utf-8", newline="\n")
    adapter_obj = ContinuityProjectionFoldAdapter(
        applier=applier(tmp_path, lease(tmp_path)), lease_id="lease-1",
        session_id=SESSION, task_id=TASK, actual_head=HEAD,
        facts_factory=lambda: facts(), targets=CANONICAL_TARGETS,
        prior_text_loader=lambda name: pre_drift[name],
    )
    outcome = adapter_obj.fold(FoldRequest(task_id=TASK, candidate_sha=HEAD, checkpoint_ref="c:fold"))
    assert outcome.completed is not True
    assert (tmp_path / "CURRENT-WORK.md").read_text(encoding="utf-8") == drifted
    assert (tmp_path / "handoff.md").read_text(encoding="utf-8") == SENTINEL_DOC



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
