from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from a_conductor.codex_goal_api_adapter import QueueEntry, TurnEvidence
from a_conductor.codex_queue_submission_guard import queue_submission_task_key
from a_conductor.domain import TaskState
from a_conductor.job_control import DurableJobControlService
from a_conductor.job_store import SQLiteJobStore
from a_conductor.orchestration import OrchestrationError
from a_conductor.orchestration_parent import (
    ParentAdmission, ParentAudit, ParentCredential, ParentIntent,
    ParentRecovery, ParentRequest,
)
from a_conductor.orchestration_receiver import EvidenceBinding, SignalReceiver

NOW = datetime(2026, 11, 6, 17, tzinfo=timezone.utc)
REPO = "aase7en/A-Wiki-Conductor"


def request(**changes):
    return replace(ParentRequest("signal:1", "ENQUEUE", NOW.isoformat(), REPO,
        "project:1", "issue:733/task:one", "intent:one"), **changes)


def credential(**changes):
    return replace(ParentCredential("sunday:issuer", "operator.v1", "device:1",
        REPO, "project:1"), **changes)


def intent(**changes):
    return replace(ParentIntent(REPO, "project:1", "task:one", "wo:733",
        "intent:one", "binding:1", ("issue:733/task:one", "wo:733/task:one"),
        "job:1", 1, "evidence:intent:one", ("docs/task-one",)), **changes)


def recovery(**changes):
    return replace(ParentRecovery("task:one", "intent:one", "binding:1", "thread:1",
        "submission:1", "evidence:recovery:1", "PENDING"), **changes)


def fixture(tmp_path):
    store = SQLiteJobStore(tmp_path / "jobs.sqlite")
    store.create_job(job_id="job:1", project_id="project:1", work_order_ref="wo:733")
    jobs = DurableJobControlService(store=store, coordinator=None)
    calls = []
    state = SimpleNamespace(verified=credential(), resolved=intent(), recovered=recovery(),
        queue_pages=[([], None)], turn_pages=[([], None)], authority=True)
    bound = EvidenceBinding("task:one", "binding:1", "thread:1", "collection:1", NOW)

    class Reader:
        def list_queue_items(self, thread, cursor):
            calls.append("queue")
            items, next_cursor = state.queue_pages[0 if cursor is None else int(cursor)]
            return {"items": list(items), "nextCursor": next_cursor, "binding": bound}

        def list_turns(self, thread, cursor):
            calls.append("turns")
            items, next_cursor = state.turn_pages[0 if cursor is None else int(cursor)]
            return {"items": list(items), "nextCursor": next_cursor, "binding": bound}

    def verify(raw):
        calls.append("verify")
        assert raw == "fixture-only-not-a-real-credential"
        return state.verified

    def resolve(req):
        calls.append("resolve")
        return state.resolved

    def check(task, scope):
        calls.append("authority")
        return state.authority

    def recover(binding, prior, evidence):
        calls.append("recovery")
        return state.recovered

    readers = Reader()
    receiver = SignalReceiver(queue_reader=readers, turn_reader=readers,
        binding_reader=lambda *_: bound, clock=lambda: NOW)
    admission = ParentAdmission(verifier=verify, expected_issuer="sunday:issuer",
        resolve_intent=resolve, receiver=receiver, authority_checker=check,
        audit=ParentAudit(jobs), resolve_recovery=recover)

    def handle(req=None, **kwargs):
        return admission.inspect(req or request(), credential="fixture-only-not-a-real-credential",
            caller_ref=kwargs.get("caller_ref", "operator.v1"),
            device_id=kwargs.get("device_id", "device:1"))

    return SimpleNamespace(store=store, jobs=jobs, calls=calls, state=state,
        admission=admission, handle=handle)


def test_valid_enqueue_is_offline_only_and_never_writes(tmp_path):
    f = fixture(tmp_path)
    before = f.jobs.list_events("job:1")
    result = f.handle()
    assert result.decision == "DENIED"
    assert result.reason_code == "ORCH_QUEUE_SERIALIZATION_UNPROVEN"
    assert result.task_ref == "task:one"
    assert f.calls == ["verify", "resolve", "queue", "turns", "authority", "resolve"]
    assert f.jobs.list_events("job:1") == before


def test_unknown_caller_is_refused_before_any_port(tmp_path):
    f = fixture(tmp_path)
    assert f.handle(caller_ref="supervisor.v1").reason_code == "ORCH_PARENT_CALLER_DENIED"
    assert f.calls == []


@pytest.mark.parametrize("value", [None, True, {}, "verified",
    credential(issuer_ref="desktop-commander"), credential(caller_ref="supervisor"),
    credential(device_id="other"), credential(repository_ref="foreign/repo"),
    credential(project_id="foreign")])
def test_unverified_or_mismatched_credential_never_reads_authority(tmp_path, value):
    f = fixture(tmp_path)
    f.state.verified = value
    assert f.handle().reason_code == "ORCH_PARENT_CREDENTIAL_DENIED"
    assert f.calls == ["verify"]


def test_verifier_absence_and_exception_are_closed_and_sanitized(tmp_path):
    f = fixture(tmp_path)
    for verifier in (None, lambda _: (_ for _ in ()).throw(ValueError("private-value"))):
        f.admission._verifier = verifier
        result = f.handle()
        assert result.reason_code == "ORCH_PARENT_CREDENTIAL_DENIED"
        assert "private-value" not in repr(result)
    assert f.calls == []


@pytest.mark.parametrize("alias", ["issue:733/task:one", "wo:733/task:one", "task:one"])
def test_owner_aliases_use_identical_canonical_task_and_key(tmp_path, alias):
    f = fixture(tmp_path)
    result = f.handle(request(task_alias=alias))
    assert result.task_ref == "task:one"
    assert queue_submission_task_key(result.task_ref) == queue_submission_task_key("task:one")


@pytest.mark.parametrize("value", [None, True, {}, intent(repository_ref="foreign/repo"),
    intent(project_id="foreign"), intent(intent_ref="other"), intent(aliases=()),
    intent(aliases=("issue:733/task:one", "issue:733/task:one")),
    intent(task_ref="x" * 129), intent(scope=()), intent(evidence_ref="")])
def test_owner_missing_ambiguous_or_foreign_identity_is_not_guessed(tmp_path, value):
    f = fixture(tmp_path)
    f.state.resolved = value
    result = f.handle()
    assert result.reason_code == "ORCH_PARENT_IDENTITY_UNRESOLVED"
    assert f.calls == ["verify", "resolve"]


def test_unknown_alias_and_different_tasks_within_one_wo_do_not_collapse(tmp_path):
    f = fixture(tmp_path)
    assert f.handle(request(task_alias="issue:733/task:two")).reason_code == "ORCH_PARENT_IDENTITY_UNRESOLVED"
    assert f.handle(request(task_alias="legacy:random")).reason_code == "ORCH_PARENT_IDENTITY_UNRESOLVED"


def test_late_owner_drift_refuses_even_after_preflight(tmp_path):
    f = fixture(tmp_path)
    values = iter((intent(), intent(parent_binding_ref="binding:2")))
    f.admission._resolve_intent = lambda _: next(values)
    assert f.handle().reason_code == "ORCH_PARENT_BINDING_DRIFT"
    assert len(f.jobs.list_events("job:1")) == 1


def test_duplicate_on_later_page_preserves_precedence_and_id(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([], "1"), ([QueueEntry("submission:1", queue_submission_task_key("task:one"))], None)]
    f.state.turn_pages = [([TurnEvidence("turn:1", "interrupted")], None)]
    result = f.handle()
    assert result.reason_code == "QUEUE_GUARD_DUPLICATE_PENDING"
    assert result.submission_ids == ("submission:1",)
    assert "authority" not in f.calls


@pytest.mark.parametrize("status, reason", [("interrupted", "QUEUE_GUARD_TURN_INTERRUPTED"),
    ("inProgress", "ORCH_PARENT_TURN_ACTIVE")])
@pytest.mark.parametrize("kind", ["ENQUEUE", "REPLAY"])
def test_later_page_interrupted_or_active_turn_never_replays(tmp_path, status, reason, kind):
    f = fixture(tmp_path)
    f.state.turn_pages = [([], "1"), ([TurnEvidence("turn:1", status)], None)]
    req = request(kind=kind, prior_submission_ref="submission:1" if kind == "REPLAY" else None,
        recovery_evidence_ref="evidence:recovery:1" if kind == "REPLAY" else None)
    assert f.handle(req).reason_code == reason
    assert "recovery" not in f.calls


def test_incomplete_listing_is_never_absence_proof(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([], "1")]
    assert f.handle().decision == "RECONCILIATION_REQUIRED"
    assert "authority" not in f.calls


def test_unknown_legacy_queue_correlation_requires_owner_reconciliation(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([QueueEntry("old:submission", "legacy-random-uuid")], None)]
    assert f.handle().reason_code == "ORCH_PARENT_IDENTITY_UNRESOLVED"


@pytest.mark.parametrize("value", [False, None, "PASS", True])
def test_task_admission_is_separate_from_credentials(tmp_path, value):
    f = fixture(tmp_path)
    f.state.authority = value
    result = f.handle()
    assert result.reason_code == ("ORCH_QUEUE_SERIALIZATION_UNPROVEN" if value is True else "AUTHORITY_DENIED")


@pytest.mark.parametrize("changes, reason", [({"job_id": None}, "ORCH_PARENT_AUDIT_OWNER_REQUIRED"),
    ({"job_id": "unknown"}, "ORCH_PARENT_AUDIT_OWNER_REQUIRED"),
    ({"job_version": 2}, "JOB_VERSION_CONFLICT")])
def test_pre_job_unknown_or_stale_audit_owner_does_not_create_a_job(tmp_path, changes, reason):
    f = fixture(tmp_path)
    f.state.resolved = intent(**changes)
    assert f.handle().reason_code == reason
    assert len(f.jobs.list_events("job:1")) == 1


@pytest.mark.parametrize("changes", [{"project_id": "foreign"}, {"work_order_ref": "foreign"},
    {"state": TaskState.COMPLETE}, {"worker_id": "worker:1"}])
def test_foreign_terminal_or_worker_job_cannot_be_audit_owner(tmp_path, changes):
    f = fixture(tmp_path)
    job = replace(f.jobs.get_job("job:1"), **changes)
    f.jobs.get_job = lambda _: job
    assert f.handle().reason_code == "ORCH_PARENT_AUDIT_OWNER_REQUIRED"


def test_unresolved_pre_checkpoint_blocks_new_signal_and_process_restart(tmp_path):
    f = fixture(tmp_path)
    audit = ParentAudit(f.jobs)
    prepared = audit.checkpoint_before(intent(), "signal:old")
    f.state.resolved = intent(job_version=prepared.version)
    fresh = ParentAudit(DurableJobControlService(store=SQLiteJobStore(tmp_path / "jobs.sqlite"), coordinator=None))
    f.admission._audit = fresh
    assert f.handle(request(signal_id="signal:new")).reason_code == "ORCH_PARENT_PRIOR_SUBMISSION_UNRESOLVED"
    assert len(f.jobs.list_events("job:1")) == 2


def test_audit_uses_real_versioned_job_checkpoints_and_evidence(tmp_path):
    f = fixture(tmp_path)
    audit = ParentAudit(f.jobs)
    prepared = audit.checkpoint_before(intent(), "signal:1")
    assert prepared.version == 2
    result = audit.record_observed(intent(), "signal:1", expected_version=2,
        submission_ref="submission:1", evidence_ref="evidence:submission:1")
    assert result.decision == "SUBMISSION_OBSERVED"
    events = f.jobs.list_events("job:1")
    assert [(e.checkpoint_ref, e.evidence_ref) for e in events[1:]] == [
        ("orch-parent-pre:signal:1", "evidence:intent:one"),
        ("orch-parent-post:signal:1", "evidence:submission:1")]
    assert all(e.worker_id is None for e in events)


def test_pre_audit_failure_and_post_audit_loss_are_distinct(tmp_path):
    f = fixture(tmp_path)
    audit = ParentAudit(f.jobs)
    f.jobs.checkpoint = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("private"))
    with pytest.raises(OrchestrationError, match="ORCH_AUDIT_UNAVAILABLE"):
        audit.checkpoint_before(intent(), "signal:1")
    result = audit.record_observed(intent(), "signal:1", expected_version=2,
        submission_ref="submission:1", evidence_ref="evidence:submission:1")
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert result.submission_ref == "submission:1"
    assert result.observability_degraded
    assert "private" not in repr(result)


def test_audit_cas_is_not_queue_serialization_and_only_one_prepare_wins(tmp_path):
    f = fixture(tmp_path)

    def prepare(_):
        try:
            ParentAudit(f.jobs).checkpoint_before(intent(), "signal:1")
            return "prepared"
        except OrchestrationError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(prepare, range(2)))
    assert sorted(results) == ["prepared", "refused"]
    assert len(f.jobs.list_events("job:1")) == 2


def replay_request(**changes):
    return request(kind="REPLAY", prior_submission_ref="submission:1",
        recovery_evidence_ref="evidence:recovery:1", **changes)


@pytest.mark.parametrize("state", ["PENDING", "TERMINAL"])
def test_replay_attaches_owner_proven_result_without_any_write(tmp_path, state):
    f = fixture(tmp_path)
    f.state.recovered = recovery(state=state)
    if state == "PENDING":
        f.state.queue_pages = [([QueueEntry("submission:1", queue_submission_task_key("task:one"))], None)]
    before = f.jobs.list_events("job:1")
    result = f.handle(replay_request())
    assert result.decision == "NO_ACTION"
    assert result.submission_ids == ("submission:1",)
    assert result.evidence_refs == ("evidence:recovery:1",)
    assert f.jobs.list_events("job:1") == before


@pytest.mark.parametrize("value", [None, True, {}, recovery(task_ref="foreign"),
    recovery(intent_ref="other"), recovery(parent_binding_ref="old"),
    recovery(thread_id="foreign"), recovery(submission_id="other"),
    recovery(evidence_ref="other"), recovery(state="completed"), recovery(state="PENDING")])
def test_missing_foreign_or_unobserved_recovery_is_never_replay_permission(tmp_path, value):
    f = fixture(tmp_path)
    f.state.recovered = value
    result = f.handle(replay_request())
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert result.reason_code == "ORCH_PARENT_RECOVERY_UNRESOLVED"


def test_generic_terminal_turn_is_not_this_task_result(tmp_path):
    f = fixture(tmp_path)
    f.state.turn_pages = [([TurnEvidence("turn:unknown", "completed")], None)]
    f.state.recovered = None
    assert f.handle(replay_request()).decision == "RECONCILIATION_REQUIRED"


@pytest.mark.parametrize("changes", [{"prior_submission_ref": None}, {"recovery_evidence_ref": None}])
def test_missing_replay_refs_refused_before_authority(tmp_path, changes):
    f = fixture(tmp_path)
    assert f.handle(replace(replay_request(), **changes)).decision == "DENIED"
    assert "resolve" not in f.calls


def test_many_credentialed_producers_cannot_enable_writer(tmp_path):
    f = fixture(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: f.handle(request(signal_id=f"signal:{i}")), range(8)))
    assert all(r.reason_code == "ORCH_QUEUE_SERIALIZATION_UNPROVEN" for r in results)
    assert len(f.jobs.list_events("job:1")) == 1


def test_unwired_module_does_not_change_operator_actions_or_worker_dispatcher():
    from a_conductor.operator_protocol import OperatorAction
    assert not any("parent" in action.value.lower() for action in OperatorAction)
    assert not hasattr(ParentAdmission, "enqueue")
    assert not hasattr(ParentAdmission, "dispatch")


def test_credential_projection_fields_are_not_truthy_or_equality_receipts(tmp_path):
    f = fixture(tmp_path)

    class EqualToAnything:
        def __eq__(self, other):
            return True

    f.state.verified = credential(issuer_ref=EqualToAnything())
    assert f.handle().reason_code == "ORCH_PARENT_CREDENTIAL_DENIED"
    assert f.calls == ["verify"]


def test_timeout_window_pre_checkpoint_can_only_attach_owner_proven_pending_result(tmp_path):
    f = fixture(tmp_path)
    prepared = ParentAudit(f.jobs).checkpoint_before(intent(), "signal:old")
    f.state.resolved = intent(job_version=prepared.version)
    f.state.queue_pages = [([QueueEntry("submission:1", queue_submission_task_key("task:one"))], None)]
    before = f.jobs.list_events("job:1")
    result = f.handle(replay_request(signal_id="signal:new"))
    assert result.decision == "NO_ACTION"
    assert result.submission_ids == ("submission:1",)
    assert f.jobs.list_events("job:1") == before
    # A missing observation/proof never clears the pre-effect checkpoint.
    f.state.recovered = None
    assert f.handle(replay_request()).decision == "RECONCILIATION_REQUIRED"
    f.state.queue_pages = [([], None)]
    assert f.handle().reason_code == "ORCH_PARENT_PRIOR_SUBMISSION_UNRESOLVED"


def test_duplicate_ids_retained_when_turn_listing_fails(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([QueueEntry("submission:1", queue_submission_task_key("task:one"))], None)]
    f.state.turn_pages = []
    result = f.handle()
    assert result.reason_code == "QUEUE_GUARD_DUPLICATE_PENDING"
    assert result.submission_ids == ("submission:1",)


def test_audit_post_without_matching_pre_never_claims_submission_audited(tmp_path):
    f = fixture(tmp_path)
    result = ParentAudit(f.jobs).record_observed(intent(), "signal:1", expected_version=1,
        submission_ref="submission:1", evidence_ref="evidence:submission:1")
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert result.submission_ref == "submission:1"
    assert len(f.jobs.list_events("job:1")) == 1


def test_refill_cannot_borrow_explicit_or_missing_quota_admission(tmp_path):
    f = fixture(tmp_path)
    assert f.handle(request(trigger="REFILL")).decision == "DENIED"
    assert "authority" not in f.calls


@pytest.mark.parametrize("port", ["_resolve_intent", "_recovery"])
def test_owner_port_failure_is_sanitized_and_never_retried(tmp_path, port):
    f = fixture(tmp_path)
    calls = []

    def fail(*args):
        calls.append("called")
        raise RuntimeError("private-owner-detail")

    setattr(f.admission, port, fail)
    result = f.handle(replay_request())
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert calls == ["called"]
    assert "private-owner-detail" not in repr(result)


def test_recovery_callback_owner_drift_is_rechecked_before_attach(tmp_path):
    f = fixture(tmp_path)

    def recover(*args):
        f.state.resolved = intent(parent_binding_ref="new-parent")
        return recovery(state="TERMINAL")

    f.admission._recovery = recover
    assert f.handle(replay_request()).reason_code == "ORCH_PARENT_BINDING_DRIFT"


def test_more_than_outcome_id_bound_is_typed_not_an_exception(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([QueueEntry(f"submission:{i}", queue_submission_task_key("task:one"))
        for i in range(17)], None)]
    result = f.handle()
    assert result.reason_code == "EVIDENCE_OVERFLOW"
    assert result.decision == "RECONCILIATION_REQUIRED"


def test_multiple_pending_copies_cannot_be_attached_as_one_resolved_result(tmp_path):
    f = fixture(tmp_path)
    f.state.queue_pages = [([QueueEntry(f"submission:{i}", queue_submission_task_key("task:one"))
        for i in (1, 2)], None)]
    assert f.handle(replay_request()).reason_code == "ORCH_PARENT_RECOVERY_UNRESOLVED"


def test_job_version_drift_during_recovery_refuses_attachment(tmp_path):
    f = fixture(tmp_path)

    def recover(*args):
        f.jobs.checkpoint("job:1", expected_version=1, checkpoint_ref="external-change")
        return recovery(state="TERMINAL")

    f.admission._recovery = recover
    assert f.handle(replay_request()).reason_code == "JOB_VERSION_CONFLICT"


def test_malformed_checkpoint_ack_never_certifies_pre_or_post_audit(tmp_path):
    f = fixture(tmp_path)
    audit = ParentAudit(f.jobs)
    checkpoint = f.jobs.checkpoint

    def uncertain(*args, **kwargs):
        checkpoint(*args, **kwargs)
        return None

    f.jobs.checkpoint = uncertain
    with pytest.raises(OrchestrationError, match="ORCH_AUDIT_UNAVAILABLE"):
        audit.checkpoint_before(intent(), "signal:1")
    assert len(f.jobs.list_events("job:1")) == 2
    result = audit.record_observed(intent(), "signal:1", expected_version=2,
        submission_ref="submission:1", evidence_ref="evidence:submission:1")
    assert result.decision == "RECONCILIATION_REQUIRED"
    assert result.submission_ref == "submission:1"


def test_final_identity_read_must_still_be_typed_owner_evidence(tmp_path):
    f = fixture(tmp_path)

    class EqualToAnything:
        def __eq__(self, other):
            return True

    values = iter((intent(), EqualToAnything()))
    f.admission._resolve_intent = lambda _: next(values)
    assert f.handle().reason_code == "ORCH_PARENT_BINDING_DRIFT"


def test_recovery_projection_fields_are_strict_identifiers(tmp_path):
    f = fixture(tmp_path)

    class EqualToAnything:
        def __eq__(self, other):
            return True

    f.state.recovered = recovery(task_ref=EqualToAnything(), state="TERMINAL")
    assert f.handle(replay_request()).reason_code == "ORCH_PARENT_RECOVERY_UNRESOLVED"
