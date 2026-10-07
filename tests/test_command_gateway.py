"""WO-P1-603: ACT-1 Command Gateway admission authority — R3 failure floor.

Pure admission: same inputs produce the same ADMIT/DENY with a bound
evidence digest, zero side effects, no authority the caller did not already
hold. Every row maps to a WO-P1-603 frozen failure-floor item.
"""
from __future__ import annotations

import pytest

from a_conductor.command_gateway import (
    DuplicateDecision, FenceStatus, GatewayAdmission,
    GatewayAuthorities, GatewayCommandRequest, GatewayDecision,
    LeaseEvidence, MutationIntent, admit_command,
)
from a_conductor.operator_protocol import (
    OperatorAction, OperatorRequest, OPERATOR_PROTOCOL_VERSION,
)

IDENTITY = {"repo_root": "A:/repo", "worktree": "A:/repo", "branch": "main",
            "head_sha": "a" * 40}


def make_request(action=OperatorAction.JOB_EXECUTE, **overrides):
    base = dict(
        request=OperatorRequest(
            protocol_version=OPERATOR_PROTOCOL_VERSION, action=action),
        mutation_intent=MutationIntent.MUTATE,
        task_ref="WO-P1-603", claim_ref="claim-1", fence_ref="fence-1",
        requested_scope=("src/a_conductor/foo.py",),
        **IDENTITY,
    )
    base.update(overrides)
    return GatewayCommandRequest(**base)


class Recorder:
    """Authority bundle that records every call (side-effect observatory)."""

    _UNSET = object()

    def __init__(self, *, lease=_UNSET, identity=None, dedupe=None, fence=_UNSET,
                 lease_exc=None, identity_exc=None, dedupe_exc=None,
                 fence_exc=None):
        self.calls = []
        self._lease = LeaseEvidence(
            task_ref="WO-P1-603", claim_ref="claim-1",
            scope=("src/a_conductor/**",), active=True) if lease is Recorder._UNSET else lease
        self._identity = identity if identity is not None else dict(IDENTITY)
        self._dedupe = dedupe if dedupe is not None else DuplicateDecision.SAFE_TO_LAUNCH
        self._fence = (FenceStatus.FENCE_HELD_HERE if fence is Recorder._UNSET
                       else fence)
        self._lease_exc = lease_exc
        self._identity_exc = identity_exc
        self._dedupe_exc = dedupe_exc
        self._fence_exc = fence_exc

    def bundle(self) -> GatewayAuthorities:
        return GatewayAuthorities(
            validate_lease=self._validate_lease,
            dedupe_decision=self._dedupe_decision,
            observe_worktree=self._observe_worktree,
            fence_status=self._fence_status,
        )

    def _validate_lease(self, claim_ref, task_ref, scope):
        self.calls.append("lease")
        if self._lease_exc:
            raise self._lease_exc
        return self._lease

    def _observe_worktree(self, repo_root):
        self.calls.append("identity")
        if self._identity_exc:
            raise self._identity_exc
        return self._identity

    def _dedupe_decision(self, fingerprint):
        self.calls.append("dedupe")
        if self._dedupe_exc:
            raise self._dedupe_exc
        return self._dedupe

    def _fence_status(self, fence_ref):
        self.calls.append("fence")
        if self._fence_exc:
            raise self._fence_exc
        return self._fence


# --- 4a: malformed/unknown request -> zero authority calls -----------------

def test_malformed_request_denies_with_zero_authority_calls():
    recorder = Recorder()
    request = make_request()
    object.__setattr__(request.request, "action", "not-an-action")
    admission = admit_command(request, authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"
    assert recorder.calls == []  # zero side effects, zero authority reads


def test_wrong_protocol_version_denies_malformed():
    recorder = Recorder()
    request = make_request()
    object.__setattr__(request.request, "protocol_version", "operator.v0")
    admission = admit_command(request, authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"
    assert recorder.calls == []


def test_blank_task_ref_denies_malformed():
    recorder = Recorder()
    admission = admit_command(make_request(task_ref=" "),
                              authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"
    assert recorder.calls == []


# --- 4b: missing/stale task/claim/lease -> fail closed ----------------------

def test_missing_lease_evidence_denies_claim_missing():
    recorder = Recorder(lease=None)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_CLAIM_MISSING"


def test_inactive_lease_denies_claim_stale():
    recorder = Recorder(lease=LeaseEvidence(
        task_ref="WO-P1-603", claim_ref="claim-1",
        scope=("src/a_conductor/**",), active=False))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_CLAIM_STALE"


def test_lease_bound_to_other_task_denies():
    recorder = Recorder(lease=LeaseEvidence(
        task_ref="WO-P1-999", claim_ref="claim-1",
        scope=("src/a_conductor/**",), active=True))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_TASK_MISSING"


# --- 4c: identity drift -> deny (observation is the only truth) -------------

def test_observed_identity_drift_denies():
    drifted = dict(IDENTITY, head_sha="b" * 40)
    recorder = Recorder(identity=drifted)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_IDENTITY_DRIFT"


def test_observed_branch_drift_denies():
    recorder = Recorder(identity=dict(IDENTITY, branch="feature/x"))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_IDENTITY_DRIFT"


# --- 4d: scope drift -> deny --------------------------------------------------

def test_requested_scope_outside_lease_denies():
    recorder = Recorder()
    admission = admit_command(
        make_request(requested_scope=("docs/other/**", "src/x.py")),
        authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_SCOPE_DRIFT"


def test_requested_scope_inside_lease_admits():
    recorder = Recorder()
    admission = admit_command(
        make_request(requested_scope=("src/a_conductor/foo.py",
                                      "src/a_conductor/bar.py")),
        authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.ADMIT


# --- 4e: UNKNOWN dedupe -> never relaunch -------------------------------------

def test_unknown_dedupe_decision_denies():
    recorder = Recorder(dedupe=DuplicateDecision.BLOCKED_UNKNOWN)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_DUPLICATE_UNKNOWN"


def test_attach_and_reuse_decisions_denied_for_new_dispatch():
    for decision in (DuplicateDecision.ATTACH_RUNNING,
                     DuplicateDecision.REUSE_COMPLETED):
        recorder = Recorder(dedupe=decision)
        admission = admit_command(make_request(),
                                  authorities=recorder.bundle())
        assert admission.reason_code == "GATEWAY_DUPLICATE_UNKNOWN"


# --- 4f: MUTATE without lawful fence -> deny -----------------------------------

def test_missing_fence_denies_mutation():
    recorder = Recorder(fence=None)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_FENCE_MISSING"


def test_stale_fence_denies_mutation():
    recorder = Recorder(fence=FenceStatus.FENCE_STALE)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_FENCE_STALE"


# --- 4g: read-only can never become mutation ------------------------------------

def test_readonly_action_with_mutation_intent_denies_escalation():
    recorder = Recorder()
    admission = admit_command(
        make_request(action=OperatorAction.JOB_GET,
                     mutation_intent=MutationIntent.MUTATE),
        authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_INTENT_ESCALATION"


def test_readonly_action_admits_without_lease_or_fence():
    recorder = Recorder(lease=None, fence=None)
    admission = admit_command(
        make_request(action=OperatorAction.STATUS,
                     mutation_intent=MutationIntent.READ_ONLY,
                     claim_ref="", fence_ref="", requested_scope=()),
        authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.ADMIT
    assert "lease" not in recorder.calls
    assert "fence" not in recorder.calls


# --- 4h: authority errors contained ----------------------------------------------

@pytest.mark.parametrize("exc,expected", [
    ("lease_exc", "GATEWAY_CLAIM_MISSING"),
    ("identity_exc", "GATEWAY_IDENTITY_DRIFT"),
    ("dedupe_exc", "GATEWAY_DUPLICATE_UNKNOWN"),
    ("fence_exc", "GATEWAY_FENCE_MISSING"),
])
def test_authority_exception_denies_without_escaping(exc, expected):
    recorder = Recorder(**{exc: RuntimeError("authority exploded")})
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == expected


# --- 4k/5: purity + evidence binding ----------------------------------------------

def test_admission_is_pure_and_binds_exact_evidence():
    recorder_a, recorder_b = Recorder(), Recorder()
    request_a = make_request()
    request_b = make_request()
    first = admit_command(request_a, authorities=recorder_a.bundle())
    second = admit_command(request_b, authorities=recorder_b.bundle())
    assert first.decision is GatewayDecision.ADMIT
    assert first.evidence_digest == second.evidence_digest
    assert first.evidence_digest != "undefined"
    # Mutating the admission is impossible; digest binds the authority set.
    with pytest.raises(Exception):
        first.decision = GatewayDecision.DENY


def test_admission_digest_changes_with_identity():
    recorder = Recorder()
    base = admit_command(make_request(), authorities=recorder.bundle())
    other = admit_command(
        make_request(head_sha="c" * 40, fence_ref="fence-2"),
        authorities=Recorder(fence=FenceStatus.FENCE_HELD_HERE).bundle())
    assert base.evidence_digest != other.evidence_digest


def test_no_secret_fields_anywhere():
    request = make_request()
    admission = admit_command(request, authorities=Recorder().bundle())
    for field in ("api_key", "token", "password", "secret"):
        assert not hasattr(request, field)
        assert not hasattr(admission, field)


def test_imports_are_pure():
    # Namespace check: no I/O or system modules may leak into the module.
    import sys
    import a_conductor.command_gateway as module
    banned = ("subprocess", "socket", "urllib", "sqlite3", "shutil",
              "requests", "http")
    for name, value in vars(module).items():
        if isinstance(value, type(sys)):  # a module object
            assert value.__name__ not in banned
