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

@pytest.mark.parametrize("exc", [
    "lease_exc", "identity_exc", "dedupe_exc", "fence_exc",
])
def test_authority_exception_denies_without_escaping(exc):
    recorder = Recorder(**{exc: RuntimeError("authority exploded")})
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    # Row h: a RAISING authority is AUTHORITY_ERROR, distinct from absent
    # evidence (CLAIM_MISSING etc.).
    assert admission.reason_code == "GATEWAY_AUTHORITY_ERROR"


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
    # Compare two ADMITs (a DENY digest is empty and proves nothing).
    recorder = Recorder()
    base = admit_command(make_request(), authorities=recorder.bundle())
    assert base.decision is GatewayDecision.ADMIT
    identity_keys = ("head_sha", "worktree", "branch", "repo_root")
    for overrides in ({"head_sha": "c" * 40}, {"fence_ref": "fence-2"},
                      {"task_ref": "WO-P1-604"}, {"worktree": "A:/other"},
                      {"requested_scope": ("src/a_conductor/a.py",
                                           "src/a_conductor/b.py")}):
        observed = dict(IDENTITY)
        for key in identity_keys:
            if key in overrides:
                observed[key] = overrides[key]
        lease = LeaseEvidence(
            task_ref=overrides.get("task_ref", "WO-P1-603"),
            claim_ref="claim-1", scope=("src/a_conductor/**",), active=True)
        other_recorder = Recorder(identity=observed, lease=lease)
        other = admit_command(make_request(**overrides),
                              authorities=other_recorder.bundle())
        assert other.decision is GatewayDecision.ADMIT, overrides
        assert base.evidence_digest != other.evidence_digest, overrides


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

# --- Sol round-1 findings (RED before repair) ----------------------------------

def test_mutate_action_labeled_readonly_denies_escalation():
    """The authority class is derived from the action, never the label."""
    recorder = Recorder(lease=None, fence=None)
    admission = admit_command(
        make_request(action=OperatorAction.JOB_EXECUTE,
                     mutation_intent=MutationIntent.READ_ONLY,
                     claim_ref="", fence_ref="", requested_scope=()),
        authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_INTENT_ESCALATION"
    assert recorder.calls == []


def test_scope_coverage_is_universal_not_existential():
    recorder = Recorder()
    admission = admit_command(
        make_request(requested_scope=("src/a_conductor/foo.py",
                                      "secrets/key")),
        authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_SCOPE_DRIFT"


@pytest.mark.parametrize("evil_item", [
    "src/a_conductor_evil/key",                     # sibling prefix
    "src/a_conductor/../../secrets/key",            # traversal
    "/absolute/path.py",                            # absolute
    "src/a_conductor",                              # bare prefix
])
def test_component_boundary_and_traversal_rejected(evil_item):
    recorder = Recorder()
    admission = admit_command(
        make_request(requested_scope=(evil_item,)),
        authorities=recorder.bundle())
    assert admission.reason_code in ("GATEWAY_REQUEST_MALFORMED",
                                     "GATEWAY_SCOPE_DRIFT")


def test_worktree_identity_drift_denies():
    recorder = Recorder(identity=dict(IDENTITY, worktree="A:/other"))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_IDENTITY_DRIFT"


def test_identity_without_worktree_key_denies():
    partial = {k: v for k, v in IDENTITY.items() if k != "worktree"}
    recorder = Recorder(identity=partial)
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_IDENTITY_DRIFT"


def test_digest_has_no_separator_collision():
    a = admit_command(
        make_request(requested_scope=("src/a_conductor/a;src/a_conductor/b",)),
        authorities=Recorder().bundle())
    b = admit_command(
        make_request(requested_scope=("src/a_conductor/a",
                                      "src/a_conductor/b")),
        authorities=Recorder().bundle())
    for admission in (a, b):
        assert admission.decision is GatewayDecision.ADMIT
    assert a.evidence_digest != b.evidence_digest


def test_digest_binds_operator_request_fields():
    base = admit_command(make_request(), authorities=Recorder().bundle())
    with_job = make_request()
    object.__setattr__(with_job.request, "job_id", "job-77")
    other = admit_command(with_job, authorities=Recorder().bundle())
    assert other.decision is GatewayDecision.ADMIT
    assert base.evidence_digest != other.evidence_digest


def test_digest_binds_readonly_task_claim_antiseparators():
    # Control-character refs cannot reach the digest at all now: they are
    # malformed at validation, so no separator-injection surface exists.
    sep = chr(0x1F)
    for field, value in (("task_ref", "a" + sep + "b"),
                         ("claim_ref", "b" + sep + "c")):
        hostile = make_request(
            action=OperatorAction.STATUS,
            mutation_intent=MutationIntent.READ_ONLY,
            task_ref="", claim_ref="", fence_ref="", requested_scope=())
        object.__setattr__(hostile, field, value)
        admission = admit_command(hostile, authorities=Recorder().bundle())
        assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED", field


def test_non_bool_lease_active_denies_stale():
    recorder = Recorder(lease=LeaseEvidence(
        task_ref="WO-P1-603", claim_ref="claim-1",
        scope=("src/a_conductor/**",), active="False"))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_CLAIM_STALE"


def test_blank_fence_ref_denies_missing():
    recorder = Recorder()
    admission = admit_command(make_request(fence_ref=" "),
                              authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_FENCE_MISSING"


def test_hostile_lease_scope_item_covers_nothing():
    recorder = Recorder(lease=LeaseEvidence(
        task_ref="WO-P1-603", claim_ref="claim-1",
        scope=("",), active=True))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.reason_code == "GATEWAY_SCOPE_DRIFT"


def test_none_outer_request_denies_malformed_without_escaping():
    admission = admit_command(None, authorities=Recorder().bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"


def test_readonly_none_task_ref_denies_malformed():
    admission = admit_command(
        make_request(action=OperatorAction.STATUS,
                     mutation_intent=MutationIntent.READ_ONLY,
                     task_ref=None, claim_ref="", fence_ref="",
                     requested_scope=()),
        authorities=Recorder().bundle())
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"


def test_raising_identity_mapping_denies_contained():
    class RaisingMapping(dict):
        def get(self, *args):
            raise RuntimeError("hostile mapping")

    recorder = Recorder(identity=RaisingMapping(IDENTITY))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    # Hostile evidence that raises during processing is an authority
    # failure, not an observed drift.
    assert admission.reason_code == "GATEWAY_AUTHORITY_ERROR"


# --- Sol round-2 findings (RED before repair) -----------------------------------

def test_digest_binds_worker_version_and_attempts():
    base = admit_command(make_request(), authorities=Recorder().bundle())
    for field, value in (("worker_id", "w-9"), ("expected_version", 7),
                         ("max_attempts", 4)):
        variant = make_request()
        object.__setattr__(variant.request, field, value)
        other = admit_command(variant, authorities=Recorder().bundle())
        assert other.decision is GatewayDecision.ADMIT, field
        assert base.evidence_digest != other.evidence_digest, field


def test_surrogate_scope_items_rejected_not_collided():
    surrogate_pair = "\U0001f600"          # real emoji (astral plane)
    lone_surrogate = chr(0xD83D) + chr(0xDE00)  # surrogate pair spelling
    a = admit_command(
        make_request(requested_scope=("src/a_conductor/" + surrogate_pair,)),
        authorities=Recorder().bundle())
    b = admit_command(
        make_request(requested_scope=("src/a_conductor/" + lone_surrogate,)),
        authorities=Recorder().bundle())
    # The lone-surrogate spelling must be rejected outright (malformed),
    # never admitted and never allowed to collide with the real character.
    assert b.decision is GatewayDecision.DENY
    assert b.reason_code == "GATEWAY_REQUEST_MALFORMED"
    assert a.decision is GatewayDecision.ADMIT


def test_raising_request_property_denies_contained():
    class HostileRequest:
        @property
        def request(self):
            raise RuntimeError("hostile property")

    admission = admit_command(HostileRequest(), authorities=Recorder().bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == "GATEWAY_REQUEST_MALFORMED"


def test_raising_task_ref_property_denies_contained():
    class HostileRequest:
        request = OperatorRequest(
            protocol_version=OPERATOR_PROTOCOL_VERSION,
            action=OperatorAction.JOB_EXECUTE)

        @property
        def task_ref(self):
            raise RuntimeError("hostile property")

    admission = admit_command(HostileRequest(), authorities=Recorder().bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code in ("GATEWAY_REQUEST_MALFORMED",
                                     "GATEWAY_AUTHORITY_ERROR")


def test_hostile_lease_eq_denies_authority_error():
    class PoisonRef(str):
        def __eq__(self, other):
            raise RuntimeError("poison eq")

        def __ne__(self, other):
            raise RuntimeError("poison ne")

    recorder = Recorder(lease=LeaseEvidence(
        task_ref=PoisonRef("WO-P1-603"), claim_ref="claim-1",
        scope=("src/a_conductor/**",), active=True))
    admission = admit_command(make_request(), authorities=recorder.bundle())
    assert admission.decision is GatewayDecision.DENY
    assert admission.reason_code == "GATEWAY_AUTHORITY_ERROR"


# --- Sol round-3 finding (surrogate refs on the read-only path) ------------------

def test_readonly_surrogate_refs_denied_not_collided():
    real = chr(0x1F600)
    lone = chr(0xD83D) + chr(0xDE00)
    for field in ('task_ref', 'claim_ref', 'fence_ref'):
        hostile = make_request(
            action=OperatorAction.STATUS,
            mutation_intent=MutationIntent.READ_ONLY,
            task_ref='', claim_ref='', fence_ref='', requested_scope=())
        object.__setattr__(hostile, field, lone)
        admission = admit_command(hostile, authorities=Recorder().bundle())
        assert admission.reason_code == 'GATEWAY_REQUEST_MALFORMED', field
        legit = make_request(
            action=OperatorAction.STATUS,
            mutation_intent=MutationIntent.READ_ONLY,
            task_ref='', claim_ref='', fence_ref='', requested_scope=())
        object.__setattr__(legit, field, real)
        other = admit_command(legit, authorities=Recorder().bundle())
        assert other.decision is GatewayDecision.ADMIT, field


# --- Sol round-4 finding (nested operator fields) -------------------------------

def test_nested_operator_surrogate_fields_denied_for_every_digest_field():
    lone = chr(0xD83D) + chr(0xDE00)
    for field in ('job_id', 'operation_ref', 'evidence_ref',
                  'checkpoint_ref', 'work_order_ref', 'project_id',
                  'worker_id'):
        hostile = make_request()
        object.__setattr__(hostile.request, field, lone)
        admission = admit_command(hostile, authorities=Recorder().bundle())
        assert admission.reason_code == 'GATEWAY_REQUEST_MALFORMED', field


def test_nested_operator_clean_fields_still_admit():
    hostile = make_request()
    object.__setattr__(hostile.request, 'job_id', 'job-1')
    object.__setattr__(hostile.request, 'worker_id', 'w-1')
    admission = admit_command(hostile, authorities=Recorder().bundle())
    assert admission.decision is GatewayDecision.ADMIT
