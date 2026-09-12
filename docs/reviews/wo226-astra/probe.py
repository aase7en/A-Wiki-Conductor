"""Pinned-source archaeology. No live process/provider. All DBs/artifacts temporary.
Run: PYTHONPATH=src:. python3 docs/reviews/wo226-astra/probe.py
Assertions characterize CURRENT behavior, including counterexamples, not WO226 acceptance.
"""
import hashlib
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Barrier

# Refuse evidence drift before importing any pinned repository module.
REPO = Path(__file__).resolve().parents[3]
manifest = json.loads(Path(__file__).with_name('source-sha256.json').read_text())
for relative, expected in manifest.items():
    actual_hash = hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
    if actual_hash != expected:
        raise SystemExit('SOURCE_DRIFT: ' + relative)

from a_conductor.execution_store import SQLiteExecutionStore
from a_conductor.execution_record import ExecutionProcessState as State
from a_conductor.execution_deduplication import DuplicateExecutionGuard
from a_conductor.supervised_run_coordinator import SupervisedRunCoordinator, SupervisedRunIdentity, SupervisedBackendPolicy
from a_conductor.zcode_runner import ZCodeTaskPacketIdentity
from a_conductor.zcode_production_assembly import derive_zcode_runtime_identity, ZCodeAssemblyError
from a_conductor.provider_config_store import SQLiteProviderConfigStore, ProviderConfigStoreError
from a_conductor.worker_lease import SQLiteWorkerLeaseStore, WorkerLeaseError, LeaseReleaseResult, LeaseMutationIntent
from tests.test_supervised_run_coordinator import ScriptedSupervised, make_child_result
from a_conductor.supervised_execution import SupervisedInspection, SupervisedInspectionState, SupervisedCollectOutcome
from tests.test_worker_lease import candidate, request, NOW
from tests.test_zcode_authority_bound_assembly import _profile, _lease, _assemble_full

OBS = {}
ARGV = ('synthetic-zcode', 'app-server')
RUNTIME = dict(provider_id='zcode-glm', model_id='glm-5.3', endpoint_base_url='http://127.0.0.1:1', runtime_provider_ref='r/provider', runtime_model_ref='r/model', generation=1)

class DurableSynthetic(ScriptedSupervised):
    def inspect(self, execution_id):
        self.store.get(execution_id)
        return SupervisedInspection(execution_id=execution_id, state=SupervisedInspectionState.RESULT_AVAILABLE, supervisor_pid=None, result_available=True, recovery_required=False)
    def collect(self, execution_id, *, expected_version):
        self.collect_calls += 1
        record = self.store.get(execution_id)
        return SupervisedCollectOutcome(record=record, result=make_child_result(execution_id, 0), recovery_required=False)

def context(root, *, store=None, port=None, packet=b'review', contract='review-1', **changes):
    root.mkdir(parents=True, exist_ok=True)
    store = store or SQLiteExecutionStore(root/'exec.sqlite')
    port = port or DurableSynthetic(root, store)
    identity = SupervisedRunIdentity(job_id='job:'+contract, work_order_ref=contract, project_id='p1', worker_id='worker1', backend_id='zcode-app-server', branch='review', head_before='a'*40, runtime_profile_ref=derive_zcode_runtime_identity(**RUNTIME), repo_root=str(root))
    identity = replace(identity, **changes)
    task = ZCodeTaskPacketIdentity(contract, hashlib.sha256(packet).hexdigest(), packet.decode())
    policy = SupervisedBackendPolicy(derive_operation_ref=lambda argv: task.canonical_operation_ref(), command_summary=lambda argv:'synthetic review', report_ref=lambda rel:rel+'/report.json')
    co = SupervisedRunCoordinator(execution_store=store, supervised=port, identity=identity, backend_policy=policy)
    return store, port, co

def run(co):
    return co.run(ARGV, timeout_seconds=1)

def decision(store, co):
    return DuplicateExecutionGuard(store=store).assess(co.fingerprint_spec(ARGV))

with tempfile.TemporaryDirectory(prefix='wo226-astra-') as temp:
    root = Path(temp)
    # BOTH canonical resource APIs can return the same active resource to an exact retry.
    leases = SQLiteWorkerLeaseStore(root/'lease.sqlite')
    req = request(mutation=False)
    c = candidate('a-worker-01')
    first = leases.try_acquire_result(req, c, lease_id='lease1', acquired_at=NOW)
    again = leases.try_acquire_result(req, c, lease_id='lease2', acquired_at=NOW)
    assert first.lease.lease_id == again.lease.lease_id and first.created and not again.created
    providers = SQLiteProviderConfigStore(root/'provider.sqlite')
    gen = providers.save_provider(_profile())
    now = datetime.now(timezone.utc)
    kwargs = dict(provider_id='zcode-glm', execution_id='dispatch-review', batch_id='batch-review', expected_max_concurrency=1, expected_configuration_generation=gen, now=now, ttl_seconds=600)
    admitted = providers.acquire_admission(**kwargs)
    existing = providers.acquire_admission(**kwargs)
    assert admitted.kind.value == 'ADMITTED' and existing.kind.value == 'EXISTING'
    assert admitted.admission.admission_id == existing.admission.admission_id
    OBS['resource_reentry'] = {'lease_created':[first.created,again.created], 'admission':[admitted.kind.value,existing.kind.value], 'same_resource_ids':True}

    # Barrier captures two empty durable reads before either proceeds to launch.
    race_root = root/'race'
    race_root.mkdir()
    actual = SQLiteExecutionStore(race_root/'exec.sqlite'); actual.initialize()
    barrier = Barrier(2)
    class BarrierStore:
        create = actual.create
        get = actual.get
        def find_by_fingerprint(self, fp):
            rows = actual.find_by_fingerprint(fp)
            barrier.wait(timeout=10)
            return rows
    wrapped = BarrierStore()
    port = DurableSynthetic(race_root, actual)
    _, _, co = context(race_root, store=wrapped, port=port)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:run(co), range(2)))
    records = actual.find_by_fingerprint(co.fingerprint_for_argv(ARGV))
    assert len(records) == 2 and port.launch_calls == 2 and all(r.exit_code == 0 for r in results)
    OBS['same_fingerprint_race'] = {'durable_records':len(records), 'synthetic_launch_calls':port.launch_calls, 'exit_codes':[r.exit_code for r in results]}

    # The real shared service also reaches its process-effect port twice.
    # The port throws immediately; no process can start and no provider is called.
    from a_conductor.supervised_execution import SupervisedExecutionService
    from tests.test_zcode_authority_bound_assembly import _Obs
    service_root = root/'service-race'; service_root.mkdir()
    service_store = SQLiteExecutionStore(service_root/'exec.sqlite'); service_store.initialize()
    service_barrier = Barrier(2)
    class ServiceBarrierStore:
        create = service_store.create
        get = service_store.get
        def find_by_fingerprint(self, fp):
            rows = service_store.find_by_fingerprint(fp)
            service_barrier.wait(timeout=10)
            return rows
    from threading import Lock
    class NoProcessController:
        calls = 0
        lock = Lock()
        def start(self,spec):
            with self.lock:
                self.calls += 1
            raise RuntimeError('synthetic effect boundary; no spawn')
    controller = NoProcessController()
    service = SupervisedExecutionService(store=service_store,controller=controller,observer=_Obs(),allowed_target_executables=('synthetic-zcode',))
    _,_,service_co = context(service_root,store=ServiceBarrierStore(),port=service)
    with ThreadPoolExecutor(max_workers=2) as pool:
        service_results = list(pool.map(lambda _:run(service_co),range(2)))
    service_records = service_store.find_by_fingerprint(service_co.fingerprint_for_argv(ARGV))
    assert controller.calls == 2 and len(service_records) == 2
    assert all(r.execution_state == State.RECOVERY_REQUIRED for r in service_records)
    OBS['real_service_race'] = {'process_effect_port_calls':controller.calls,'records':len(service_records),'real_spawns':0,'states':[r.execution_state.value for r in service_records]}

    # One older equivalent execution remains running; newest completed row wins guard.
    old, new = records[-1], records[0]
    actual.set_execution_state(old.execution_id, State.RUNNING, expected_version=old.version)
    assessed = decision(actual, co)
    assert assessed.decision.value == 'REUSE_COMPLETED' and assessed.record.execution_id == new.execution_id
    OBS['multiple_equivalent_records'] = {'decision':assessed.decision.value, 'older_state':actual.get(old.execution_id).execution_state.value, 'selected_newer_completed':True}

    # Unrelated runtime inserted between first and final lookup does not hijack exact fingerprint.
    store, port, co = context(root/'interleave')
    run(co); before = decision(store,co).record
    _, _, other = context(root/'interleave',store=store,port=port,contract='unrelated')
    run(other); after = decision(store,co).record
    assert before.execution_id == after.execution_id
    OBS['unrelated_interleave'] = {'same_exact_runtime_record':True,'unrelated_runs':1}

    # Fault boundary: discard caller result after collect, reconstruct from fresh store/port/co.
    # This is simulated caller memory loss; no OS process is killed.
    crash_root = root/'restart'
    store, port, co = context(crash_root)
    result = run(co); original = decision(store,co).record
    store.set_execution_state(original.execution_id,State.SUCCEEDED,expected_version=original.version)
    del result, co, store
    reopened, next_port, next_co = context(crash_root)
    recovered = run(next_co); replay = decision(reopened,next_co).record
    assert recovered.exit_code == 0 and next_port.launch_calls == 0 and replay.execution_id == original.execution_id
    OBS['post_success_pre_handoff_restart'] = {'first_launch_calls':port.launch_calls,'restart_launch_calls':next_port.launch_calls,'same_runtime_id':True,'cleanup_handoff':'ABSENT_NO_WO226_IMPLEMENTATION'}

    # Durable cut states: record-before-effect never returns SAFE_TO_LAUNCH.
    cuts = {}
    for state in [State.QUEUED,State.STARTING,State.RUNNING,State.RECOVERY_REQUIRED]:
        cut_root = root/('cut-'+state.value)
        cut_store,cut_port,cut_co = context(cut_root)
        cut_store.create(replace(original,execution_id='cut-'+state.value,repo_root=str(cut_root),command_fingerprint=cut_co.fingerprint_for_argv(ARGV),execution_state=state))
        cuts[state.value] = decision(cut_store,cut_co).decision.value
    assert cuts == {'QUEUED':'ATTACH_RUNNING','STARTING':'ATTACH_RUNNING','RUNNING':'ATTACH_RUNNING','RECOVERY_REQUIRED':'BLOCKED_UNKNOWN'}
    OBS['durable_crash_cut_decisions'] = cuts

    # Changes use actual task/runtime derivation, not invented hash rules.
    variants = {}
    for label, changes in [('task_sha',{'packet':b'changed'}),('contract',{'contract':'review-2'}),('HEAD',{'head_before':'b'*40})]:
        _,_,changed = context(crash_root,store=reopened,port=next_port,**changes)
        variants[label] = decision(reopened,changed).decision.value
    for key,value in [('provider_id','other'),('model_id','other'),('runtime_model_ref','r/other'),('runtime_provider_ref','r/other'),('generation',2),('endpoint_base_url','http://127.0.0.1:2')]:
        rt = derive_zcode_runtime_identity(**{**RUNTIME,key:value})
        _,_,changed = context(crash_root,store=reopened,port=next_port,runtime_profile_ref=rt)
        variants[key] = decision(reopened,changed).decision.value
    assert set(variants.values()) == {'SAFE_TO_LAUNCH'} and next_port.launch_calls == 0
    OBS['identity_change_no_reuse'] = variants
    _,_,foreign = context(crash_root,store=reopened,port=next_port,worker_id='foreign-worker')
    assessed = decision(reopened,foreign)
    assert assessed.decision.value == 'REUSE_COMPLETED' and assessed.record.worker_id != foreign.identity.worker_id
    OBS['foreign_worker_guard_only'] = 'REUSE_COMPLETED; WO226 separate worker fence required'

    # Canonical lease replacement, stale snapshot, owner fence and release lost acknowledgement.
    leased = first.lease
    try:
        leases.release(leased.lease_id,session_id='foreign',task_id=leased.task_id,released_at=NOW)
        raise AssertionError('foreign release accepted')
    except WorkerLeaseError as e:
        assert e.code == 'LEASE_OWNER_MISMATCH'
    released = leases.release(leased.lease_id,session_id=leased.session_id,task_id=leased.task_id,released_at=NOW)
    new_req = replace(req,session_id='new-owner')
    replacement = leases.try_acquire_result(new_req,c,lease_id='lease-new-owner',acquired_at=NOW)
    retry_release = leases.release(leased.lease_id,session_id=leased.session_id,task_id=leased.task_id,released_at=NOW)
    assert leased.released_at is None and leases.inspect_health(leased.lease_id,now=NOW).lease.released_at is not None
    assert replacement.lease.session_id == 'new-owner' and retry_release.already_released
    assert leases.inspect_health(replacement.lease.lease_id,now=NOW).lease.released_at is None
    OBS['lease_owner_change'] = {'old_snapshot_still_looks_active':True,'foreign_release':'LEASE_OWNER_MISMATCH','retry_old_release':[retry_release.released,retry_release.already_released],'new_owner_untouched':True}
    ambiguous = [LeaseReleaseResult(released=a,already_released=b) for a,b in [(False,False),(True,True)]]
    OBS['ambiguous_release_shapes'] = [{'released':r.released,'already_released':r.already_released,'usable_handoff':'MUST_REJECT; consumer absent'} for r in ambiguous]
    # Admission lost-ack replay is NOT the lease API's already-released shape.
    a = admitted.admission
    release_kw = dict(provider_id=a.provider_id, execution_id=a.execution_id,batch_id=a.batch_id,now=now)
    providers.release_admission(a.admission_id,**release_kw)
    try:
        providers.release_admission(a.admission_id,**release_kw)
        raise AssertionError('repeat admission release accepted')
    except ProviderConfigStoreError as e:
        assert e.code == 'PROVIDER_ADMISSION_NOT_ACTIVE'
        OBS['provider_release_lost_ack'] = {'retry_error':e.code,'canonical_reread':providers.get_admission(a.admission_id).status}

    # Actual accepted assembly entrypoint: mutation control passes, READ_ONLY fails.
    assembly_root=root/'assembly'; assembly_root.mkdir()
    _assemble_full(assembly_root)
    try:
        _assemble_full(assembly_root,lease_overrides=dict(mutation_intent=LeaseMutationIntent.READ_ONLY,mutable_scope=()))
        raise AssertionError('READ_ONLY accepted')
    except ZCodeAssemblyError as e:
        OBS['READ_ONLY_assembly']={'mutation_control':'PASS','READ_ONLY_error':e.code,'synthetic_provider_calls':0}
        assert e.code == 'ZCODE_LEASE_MUTATION_INTENT_INSUFFICIENT'

print(json.dumps({'source_base':'7afb33d738086db50bc027c4c47165179a1cb96f','observations':OBS},indent=2))
