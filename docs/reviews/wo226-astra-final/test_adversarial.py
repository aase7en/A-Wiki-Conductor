"""Independent RED expectations for frozen WO226 candidate; no live provider.
Run: python3 -m pytest -q -s docs/reviews/wo226-astra-final/test_adversarial.py
Reuses candidate fixtures only for data/builders; assertions are independent.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from dataclasses import replace
import json

from tests import test_zero_relay_review_execution as f
from a_conductor.zero_relay_review_execution import execute_review_dispatch


def dispatch(a, route, task, factory):
    return execute_review_dispatch(
        route=route, route_task=task, provider_snapshot=a.snapshot,
        provider_store=a.provider_store, lease_broker=a.lease_broker,
        lease_store=a.lease_store, execution_store=a.execution_store,
        job_store=a.job_store, runner_factory=factory,
        secret_resolver=a.secret_resolver, repo_root=a.repo_root,
        executable=f.EXEC, bundle_js=f.BUNDLE, clock=lambda: f.NOW,
    )


def resources(a):
    return {
        'admissions': [x.status for x in f._all_admissions(a)],
        'leases_released': [x.released_at is not None for x in f._all_leases(a)],
    }


def test_loser_does_not_release_paused_winner_resources(tmp_path):
    plan, a, route, task = f._bridge(tmp_path)
    entered, proceed = Event(), Event()
    inner = f.FakeRunnerFactory()

    def paused_factory(**kwargs):
        entered.set()  # winner owns resources, but no runtime record yet
        assert proceed.wait(10), 'probe barrier timed out'
        return inner(**kwargs)

    with ThreadPoolExecutor(max_workers=1) as pool:
        winner = pool.submit(dispatch, a, route, task, paused_factory)
        try:
            assert entered.wait(10)
            before = resources(a)
            loser = dispatch(a, route, task, inner)
            after = resources(a)
        finally:
            proceed.set()
        first = winner.result(timeout=10)
    print(json.dumps({'case': 'paused_winner', 'before': before, 'after_loser': after,
                      'loser': loser.outcome, 'winner': first.outcome,
                      'model_effects': inner.model_effects}))
    assert after == before, 'losing dispatch released still-owned winner resources'


def test_failed_terminal_after_timeout_releases_resources(tmp_path):
    plan, a, route, task = f._bridge(tmp_path)
    factory = f.FakeRunnerFactory(live_timeout=True)
    first = dispatch(a, route, task, factory)
    assert first.handoff is None
    a.execution_store.set_execution_state(factory.execution_ids[0],
        f.ExecutionProcessState.FAILED, expected_version=1)
    replay = dispatch(a, route, task, factory)
    after = resources(a)
    print(json.dumps({'case': 'failed_terminal_reconcile', 'outcome': replay.outcome,
                      'reason': replay.reason_code, 'resources': after}))
    assert replay.handoff is None
    assert after['admissions'] == ['RELEASED'] and after['leases_released'] == [True], \
        'terminal failed child must release capacity without usable handoff'


def test_foreign_worker_terminal_record_cannot_create_handoff(tmp_path):
    plan, a, route, task = f._bridge(tmp_path)
    inner = f.FakeRunnerFactory()

    def foreign_factory(**kwargs):
        original = inner(**kwargs)
        class Runner:
            def execution_fingerprint_spec(self):
                return original.execution_fingerprint_spec()
            def run(self, **run_kwargs):
                # Same fingerprint does not cover worker identity (canonical
                # classifier explicitly rejects this supported record shape).
                a.execution_store.create(f._record_for(
                    kwargs['plan'], 'exec-foreign', worker='a-worker-99'))
                return f.NativeCommandResult(executable='ZCode.exe', argument_count=6,
                    exit_code=0, timed_out=False, stdout='', stderr='',
                    stdout_sha256='0'*64, stderr_sha256='0'*64,
                    stdout_truncated=False, stderr_truncated=False)
        return Runner()
    result = dispatch(a, route, task, foreign_factory)
    print(json.dumps({'case': 'foreign_worker', 'outcome': result.outcome,
                      'handoff_worker': result.handoff.worker_id if result.handoff else None,
                      'record_worker': a.execution_store.get('exec-foreign').worker_id}))
    assert result.handoff is None, 'post-run path bypassed equivalent identity classifier'


def test_task_network_denied_blocks_before_effect(tmp_path):
    from a_conductor.provider_policy import (
        ProviderPolicyTaskSecurity, TaskPrivacyClass, TaskNetworkPolicy,
        evaluate_provider_policy,
    )
    from a_conductor.provider_configuration import EgressBoundary, ProviderEndpointConfig
    plan, a, route, task = f._bridge(tmp_path)
    profile = replace(task.provider_profile, egress_boundary=EgressBoundary.EXTERNAL_FIRST_PARTY)
    a.provider_store.save_provider(profile, expected_generation=1)
    current = a.provider_store.load_provider_snapshot(profile.provider_id)
    a.provider_store.save_endpoint(ProviderEndpointConfig(profile.endpoint_ref,
        'https://provider.example.invalid'), expected_generation=1)
    a.snapshot = a.provider_store.load_provider_snapshot(profile.provider_id)
    security = ProviderPolicyTaskSecurity(privacy_class=TaskPrivacyClass.INTERNAL,
        network_policy=TaskNetworkPolicy.DENIED)
    task = replace(task, provider_profile=a.snapshot.profile,
        provider_endpoint=a.snapshot.endpoint, provider_security=security,
        expected_configuration_generation=a.snapshot.generation)
    policy = evaluate_provider_policy(a.snapshot.profile, a.snapshot.endpoint, security)
    assert not policy.allowed and policy.reason_code == 'TASK_NETWORK_DENIED'
    factory = f.FakeRunnerFactory()
    try:
        result = dispatch(a, route, task, factory)
        outcome = result.outcome
    except f.ZeroRelayReviewExecutionError as exc:
        outcome = exc.code
    print(json.dumps({'case': 'task_policy_denied', 'canonical_policy': policy.reason_code,
                      'bridge_outcome': outcome, 'model_effects': factory.model_effects,
                      'resources': resources(a)}))
    assert factory.model_effects == 0, 'trusted C0 network policy ignored by bridge'
    assert resources(a) == {'admissions': [], 'leases_released': []}
