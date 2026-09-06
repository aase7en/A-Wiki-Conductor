"""WO-P1-158 FINAL TARGETED REPAIR — RED (binding GPT1 review 5560480061).

P1-1 complete runtime execution identity; P1-2 admission bound to the
actual dispatch context; P1-3 lease/project/mutation-scope binding;
P2-2 truthful finished_at boundary; P2-3 argv-evidence truth; P2-4
endpoint assertion API truth. (P2-1 bounded reader is proven by the
real flooding-child E2E in test_zcode_real_helper_e2e.py.)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from a_conductor.zcode_production_assembly import (
    ZCodeAssemblyError,
    ZCodeExecutionAuthorities,
    assemble_zcode_execution,
    derive_zcode_runtime_identity,
)
from tests.test_zcode_authority_bound_assembly import (
    ENDPOINT, EXEC, BUNDLE, Snapshot, _Controller, _Obs, _Secrets, _Store,
    _admission, _lease, _packet, _profile,
)
from tests.test_zcode_real_helper_e2e import _packet as _e2e_packet
from tests.test_zcode_real_helper_e2e import BASE_URL as _E2E_BASE_URL


# ---------------- P1-1: complete runtime execution identity ----------------

def _runtime_kwargs():
    return dict(
        provider_id="zcode-glm",
        model_id="glm-5.3",
        endpoint_base_url=ENDPOINT.base_url,
        runtime_provider_ref="zcode-runtime/glm-main",
        runtime_model_ref="zcode-runtime/glm-5.3",
        generation=1,
    )


def test_runtime_identity_is_domain_separated_full_sha256():
    ref = derive_zcode_runtime_identity(**_runtime_kwargs())
    prefix = "zcode-runtime-v1:"
    assert ref.startswith(prefix)
    digest = ref[len(prefix):]
    assert len(digest) == 64  # NO truncation
    expected = hashlib.sha256(
        b"zcode-runtime-v1"
        + b"zcode-glm" + b"\x00"
        + b"glm-5.3" + b"\x00"
        + ENDPOINT.base_url.encode("utf-8") + b"\x00"
        + b"zcode-runtime/glm-main" + b"\x00"
        + b"zcode-runtime/glm-5.3" + b"\x00"
        + b"1"
    ).hexdigest()
    assert digest == expected  # exact canonical byte encoding pinned


def test_runtime_identity_stable_across_reconstruction():
    a = derive_zcode_runtime_identity(**_runtime_kwargs())
    b = derive_zcode_runtime_identity(**_runtime_kwargs())  # restart-equivalent
    assert a == b


def test_runtime_identity_separates_every_trusted_fact():
    base = derive_zcode_runtime_identity(**_runtime_kwargs())
    variants = {
        "model_id": {**_runtime_kwargs(), "model_id": "glm-4.7"},
        "runtime_model_ref": {**_runtime_kwargs(), "runtime_model_ref": "zcode-runtime/glm-4.7"},
        "endpoint": {**_runtime_kwargs(), "endpoint_base_url": "http://127.0.0.2:2"},
        "runtime_provider_ref": {**_runtime_kwargs(), "runtime_provider_ref": "zcode-runtime/other"},
        "generation": {**_runtime_kwargs(), "generation": 2},
        "provider": {**_runtime_kwargs(), "provider_id": "other-provider"},
    }
    for name, kwargs in variants.items():
        assert derive_zcode_runtime_identity(**kwargs) != base, name


def test_assembly_uses_derived_runtime_identity_not_caller_string(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full

    runner = _assemble_full(tmp_path)
    expected = derive_zcode_runtime_identity(**_runtime_kwargs())
    assert runner._identity.runtime_profile_ref == expected
    # the historical provider:<id>@<generation> form is gone as identity
    assert runner._identity.runtime_profile_ref != "provider:zcode-glm@1"


def test_assembly_has_no_caller_runtime_identity_parameter(tmp_path):
    import inspect

    from a_conductor.zcode_production_assembly import assemble_zcode_execution as fn
    params = inspect.signature(fn).parameters
    assert "runtime_profile_ref" not in params  # caller can never choose it


# ---------------- P1-2: admission bound to the actual dispatch ----------------

def test_missing_dispatch_context_fails_closed(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(tmp_path, dispatch_batch_id="")
    assert e.value.code == "ZCODE_DISPATCH_CONTEXT_MISSING"


def test_wrong_batch_admission_rejected(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(tmp_path, dispatch_batch_id="batch-OTHER")
    assert e.value.code == "ZCODE_ADMISSION_BATCH_MISMATCH"


def test_wrong_execution_admission_rejected(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(tmp_path, dispatch_execution_id="exec-different")
    assert e.value.code == "ZCODE_ADMISSION_EXECUTION_MISMATCH"


def test_correct_dispatch_bound_admission_succeeds(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    runner = _assemble_full(
        tmp_path,
        dispatch_batch_id="batch-0001",
        dispatch_execution_id="exec-bound-0001",
    )
    assert runner is not None


# ---------------- P1-3: lease / project / mutation-scope binding ----------------

def test_wrong_project_rejected(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(tmp_path, project_id="proj-OTHER")
    assert e.value.code == "ZCODE_PROJECT_MISMATCH"


def test_project_identity_comes_from_lease_not_hardcoded(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    runner = _assemble_full(tmp_path)  # lease project_id == "zcode" (fixture)
    assert runner._identity.project_id == "zcode"
    # with a DIFFERENT lease project, the durable identity follows the lease
    runner2 = _assemble_full(tmp_path, lease_overrides={"project_id": "proj-real"})
    assert runner2._identity.project_id == "proj-real"
    assert runner2._identity.project_id != "zcode"  # no synthetic hard-code


def test_read_only_lease_cannot_authorize_mutation_execution(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    from a_conductor.worker_lease import LeaseMutationIntent
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(
            tmp_path,
            lease_overrides={"mutation_intent": LeaseMutationIntent.READ_ONLY},
        )
    assert e.value.code == "ZCODE_LEASE_MUTATION_INTENT_INSUFFICIENT"


def test_mutable_scope_outside_allowed_scope_rejected(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(
            tmp_path,
            requested_mutable_scope=("src/outside/path.py",),
        )
    assert e.value.code == "ZCODE_SCOPE_NOT_AUTHORIZED"


def test_mutable_scope_overlapping_forbidden_scope_rejected(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    with pytest.raises(ZCodeAssemblyError) as e:
        _assemble_full(
            tmp_path,
            lease_overrides={
                # allowed covers it broadly (fnmatch pattern) ...
                "allowed_scope": ("src/*", "secrets/*"),
                # ... but the lease explicitly forbids this subtree
                "forbidden_scope": ("secrets/tokens.py",),
            },
            requested_mutable_scope=("secrets/tokens.py",),
        )
    assert e.value.code == "ZCODE_SCOPE_FORBIDDEN"


def test_exact_mutation_lease_with_authorized_scope_succeeds(tmp_path):
    from tests.test_zcode_authority_bound_assembly import _assemble_full
    runner = _assemble_full(
        tmp_path,
        lease_overrides={"allowed_scope": ("src/a_conductor/*",)},
        requested_mutable_scope=("src/a_conductor/zcode_runner.py",),
    )
    assert runner is not None


# ---------------- P2-2: truthful finished_at (order contract) ----------------

def test_helper_captures_finished_at_after_terminal_exit_in_source_order():
    """Source-order contract: finished_at is captured AFTER the natural
    shutdown that yields the real terminal exit code (E2E proves it live
    with a delayed-exit child in test_zcode_real_helper_e2e.py)."""
    source = (Path(__file__).parent.parent / "src" / "a_conductor"
              / "zcode_supervised_helper.py").read_text(encoding="utf-8")
    body = source[source.index("def main("):]
    shutdown_idx = body.index("_natural_shutdown()")
    # the terminal-exit shutdown call must precede the finished capture
    finished_idx = body.index('finished = _datetime.now')
    assert shutdown_idx < finished_idx, "finished_at must follow terminal exit"
    # and the EXIT_PENDING path must NOT write a canonical result
    pending_idx = body.index('"EXIT_PENDING"')
    assert body.index("_write_atomic(result_path") > pending_idx


# ---------------- P2-3: argv evidence truth ----------------

def test_target_argv_sha_is_launch_evidence_not_live_verified():
    """Option B (truthful contract): live restart identity authority uses
    ONLY the facts the OS observer can actually corroborate — PID, creation
    time, executable, parent. The persisted argv sha is durable LAUNCH
    evidence and is NOT described as live-verified."""
    from a_conductor.zcode_child_recovery import (
        ZCodeChildRecoveryKind,
        read_child_identity_from_run_dir,
        reconcile_zcode_child,
    )
    from a_conductor.zcode_supervised_helper import ZCodeChildIdentity, target_argv_sha256

    argv_a = ("C:\\ZCode\\ZCode.exe", "C:\\b.js", "app-server", "--stdio", "--surface", "desktop")
    identity = ZCodeChildIdentity(
        child_pid=4242, child_created_epoch_ms=1788490277831,
        executable=EXEC, parent_pid=100,
        target_argv_sha256=target_argv_sha256(argv_a),
        execution_id="exec-aaaa0000bbbb1111",
    )
    run_dir = Path(__file__).parent / "_tmp_argv_truth"
    run_dir.mkdir(exist_ok=True)
    try:
        (run_dir / "child.identity.json").write_text(
            __import__("json").dumps(identity.as_dict(), sort_keys=True), encoding="utf-8"
        )
        document = read_child_identity_from_run_dir(run_dir)
        # live observer corroborates pid/creation/executable/parent ONLY —
        # it has no argv fact; reconciliation still attaches. If argv were
        # (falsely) treated as live-verified this would be RECOVERY.
        live = {"pid": 4242, "created_epoch_ms": 1788490277831,
                "executable": EXEC, "parent_pid": 100}

        class _Obs:
            def observe_child(self, pid):
                return live

        decision = reconcile_zcode_child(document, observer=_Obs())
        assert decision.kind is ZCodeChildRecoveryKind.ATTACH
    finally:
        import shutil
        shutil.rmtree(run_dir, ignore_errors=True)


def test_recovery_module_claims_only_observable_facts():
    source = (Path(__file__).parent.parent / "src" / "a_conductor"
              / "zcode_child_recovery.py").read_text(encoding="utf-8")
    assert "argv" in source and "launch evidence" in source
    # the reconcile logic itself must not consult any argv fact
    reconcile_src = source[source.index("def reconcile_zcode_child"):]
    for banned in ("target_argv", "argv_sha"):
        assert banned not in reconcile_src, banned


# ---------------- P2-4: endpoint assertion API truth ----------------

def test_endpoint_parameter_is_named_as_assertion_not_authority():
    import inspect

    from a_conductor.zcode_production_assembly import assemble_zcode_execution as fn
    params = inspect.signature(fn).parameters
    assert "expected_base_url" in params
    assert "authorized_base_url" not in params  # authority-suggesting name gone
    doc = fn.__doc__ or ""
    assert "snapshot" in doc and "authority" in doc
