"""R1 x AF2 cross-product on real stores; no network or production mutation."""
import json
import pytest
from tests import test_zero_relay_review_execution as f


@pytest.mark.parametrize('state', [f.ExecutionProcessState.FAILED,
    f.ExecutionProcessState.PARTIAL, f.ExecutionProcessState.CANCELLED])
@pytest.mark.parametrize('identity', ['exact', 'generation_unknown', 'wrong_batch'])
def test_terminal_cleanup_preserves_r1_identity(tmp_path, state, identity):
    generation = None if identity == 'generation_unknown' else 1
    plan, a, route, task, admission = f._replay_setup(tmp_path,
        expected_generation=generation,
        batch_id='WRONG-BATCH' if identity == 'wrong_batch' else None)
    # Canonical durable transition, same exact execution identity.
    a.execution_store.set_execution_state('exec-pre-done', state, expected_version=1)
    runner = f.FakeRunnerFactory()
    counts_before = (len(f._all_admissions(a)), len(f._all_leases(a)))
    result = f._af_dispatch(a, route, task, runner)
    after = f._af_resources(a)
    print(json.dumps({'state': state.value, 'identity': identity,
        'expected_generation': a.snapshot.generation,
        'persisted_generation': admission.configuration_generation,
        'reason': result.reason_code, 'resources': after}))
    assert result.outcome == 'RECOVERY_REQUIRED' and result.handoff is None
    assert runner.model_effects == 0
    assert counts_before == (len(f._all_admissions(a)), len(f._all_leases(a)))
    if identity == 'exact':
        assert after == {'admissions': ['RELEASED'], 'leases_released': [True]}
    else:
        assert after == {'admissions': ['ACTIVE'], 'leases_released': [False]}, \
            'terminal cleanup bypassed preserved R1 admission identity gate'
