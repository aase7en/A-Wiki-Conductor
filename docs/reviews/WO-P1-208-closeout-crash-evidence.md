# WO208 — native Mac closeout seam evidence

Author: Poppy Javis / home Mac Astra, 2026-09-12
Not an independent acceptance review. No production files changed.

Source base: 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971.
Probe ran at docs-only bootstrap d0228940ebd909d4a87ec0ad8325700d152bb908.
Git blob IDs (not file SHA-256):
- src/a_conductor/goal_closeout.py: 0acdf8c99194818169239a2eaf4aeac7758e3f39
- src/a_conductor/job_store.py: bde34b6f4e1163caaa7b641a21dd741e14e5cda8
- src/a_conductor/job_state.py: 816784b431c4d03d9cfbe23a806525adc29645f4
- tests/test_goal_closeout.py: b4055cae6a79c2165aa20dd0c5172c4cf0736446

Baseline command: `python3 -m pytest -q tests/test_goal_closeout.py tests/test_job_store.py`
Result: **94 passed in 0.30s**, exit 0, native macOS Python 3.12.2.
Probe command: `python3 runs/WO-P1-208/probe.py`; exit 0. Owned tempfile cleanup complete.

The real executor and job store were used; fold/lease ports and review/merge/ownership
facts were labelled fixtures. Real SQLite rows were advanced through valid state
transitions and verification checkpointing. No network, provider, private files or live
runtime. These are seam counterexamples to overly broad composition guarantees, not
proven production failures. Restart here means reopened store/reconstructed caller;
actual process-death cuts remain work for the GLM lab. Thread result ordering is not fixed.

## Captured output

```json
{
  "host": "Darwin",
  "python": "3.12.2",
  "source_sha": "d0228940ebd909d4a87ec0ad8325700d152bb908",
  "evidence_class": "native Python/SQLite, synthetic effect ports; not production reachability",
  "concurrent": {
    "effects": 2,
    "results": [
      {
        "decision": "RECOVERY_REQUIRED",
        "detail": "CHECKPOINT_AFTER_EFFECT_FAILED"
      },
      {
        "decision": "FOLD_REQUIRED",
        "detail": ""
      }
    ],
    "new_checkpoints": 1,
    "state": "REVIEW_PENDING"
  },
  "stale": {
    "effects": 1,
    "result": {
      "decision": "RECOVERY_REQUIRED",
      "detail": "CHECKPOINT_AFTER_EFFECT_FAILED"
    },
    "state": "BLOCKED"
  },
  "unknown_reentry": {
    "effects": 2,
    "results": [
      {
        "decision": "RECOVERY_REQUIRED",
        "detail": "FOLD_OUTCOME_UNKNOWN"
      },
      {
        "decision": "RECOVERY_REQUIRED",
        "detail": "FOLD_OUTCOME_UNKNOWN"
      }
    ],
    "new_checkpoints": 0
  },
  "positive": {
    "effects": 1,
    "results": [
      {
        "decision": "FOLD_REQUIRED",
        "detail": ""
      },
      {
        "decision": "COMPLETE_ALLOWED",
        "detail": ""
      },
      {
        "decision": "ALREADY_COMPLETE",
        "detail": ""
      }
    ],
    "state": "COMPLETE"
  },
  "temp_cleanup": "complete"
}
```

## Replayable probe

In an owned isolated checkout at the pinned source, copy the following Python fence to
ignored `runs/WO-P1-208/probe.py`, then run the command above from that checkout root.
This is the exact probe, not a pseudocode algorithm. Preserve fixture-only boundaries.
Probe SHA-256: `bf1136e729cbe8676676031120a586610adeeb3dccca20addda6c1301a579aac`.

```python
"""Synthetic GoalCloseout boundary probe. No providers, real repos or live stores."""
from pathlib import Path
import sys, tempfile, json, threading, subprocess, platform
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
ROOT = Path.cwd()
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from a_conductor.goal_closeout import (GoalCloseoutExecutor, FoldEvidence, FoldRequirement,
    FoldOutcome, CloseoutStage, closeout_checkpoint_ref)
from a_conductor.job_store import SQLiteJobStore, JobStoreError
from a_conductor.domain import TaskState
from tests.test_goal_closeout import facts, V, TASK, JOB, SHA, ATTEMPT, FakeLeasePort


def seed(folder):
    s = SQLiteJobStore(folder / 'jobs.sqlite')
    j = s.create_job(job_id=JOB, work_order_ref='synthetic-wo208', project_id='synthetic')
    for state in (TaskState.READY, TaskState.CLAIMED, TaskState.GATING,
                  TaskState.EXECUTING, TaskState.VERIFYING, TaskState.REVIEW_PENDING):
        extra = {'worker_id': 'synthetic-worker'} if state is TaskState.CLAIMED else {}
        j = s.transition(JOB, state, expected_version=j.version, **extra)
    vr = closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT,
        task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
    before = j.version
    j = s.checkpoint(JOB, checkpoint_ref=vr, expected_version=j.version)
    f = facts(state=j.state, version=j.version,
        verification=V(mutation_version=before, checkpoint_version=j.version, checkpoint_ref=vr),
        completed_closeout_refs=frozenset({vr}),
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False))
    return s, f


class Effects:
    def __init__(self, folder, *, barrier=None, unknown=False):
        self.folder, self.barrier, self.unknown = folder, barrier, unknown
        self.count = 0
        self.lock = threading.Lock()
    def fold(self, request):
        if self.barrier:
            self.barrier.wait(timeout=5)
        with self.lock:
            self.count += 1
            (self.folder / f'effect-{self.count}.txt').write_text(request.checkpoint_ref)
        return FoldOutcome(completed=None if self.unknown else True)


def ex(store, effect):
    return GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(), fold_port=effect)


def refs(store):
    return frozenset(e.checkpoint_ref for e in store.list_events(JOB) if e.checkpoint_ref)


def result(r):
    return {'decision': r.decision.value, 'detail': r.detail}


def run():
    out = {'host': platform.system(), 'python': platform.python_version(),
        'source_sha': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'evidence_class': 'native Python/SQLite, synthetic effect ports; not production reachability'}
    with tempfile.TemporaryDirectory(prefix='wo208-') as temp:
        root = Path(temp)
        def folder(name):
            p=root/name;p.mkdir();return p
        p=folder('concurrent');s,f=seed(p);eff=Effects(p,barrier=threading.Barrier(2))
        second=SQLiteJobStore(p/'jobs.sqlite')
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(ex(store,eff).execute_next,f) for store in (s,second)]
            rs=[x.result(timeout=10) for x in futures]
        out['concurrent']={'effects':eff.count,'results':[result(x) for x in rs],
            'new_checkpoints':len(refs(s)-f.completed_closeout_refs), 'state':s.get_job(JOB).state.value}
        assert eff.count==2 and len(refs(s)-f.completed_closeout_refs)==1
        assert {r.decision.value for r in rs}=={'FOLD_REQUIRED','RECOVERY_REQUIRED'}
        p=folder('stale');s,f=seed(p);eff=Effects(p)
        s.transition(JOB,TaskState.BLOCKED,expected_version=f.version)
        r=ex(s,eff).execute_next(f)
        out['stale']={'effects':eff.count,'result':result(r),'state':s.get_job(JOB).state.value}
        assert eff.count==1 and s.get_job(JOB).state is TaskState.BLOCKED
        p=folder('unknown');s,f=seed(p);eff=Effects(p,unknown=True)
        r1=ex(s,eff).execute_next(f)
        reopened=SQLiteJobStore(p/'jobs.sqlite')
        fresh=replace(f,version=reopened.get_job(JOB).version,
            completed_closeout_refs=refs(reopened),
            fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None))
        r2=ex(reopened,eff).execute_next(fresh)
        out['unknown_reentry']={'effects':eff.count,'results':[result(r1),result(r2)],
            'new_checkpoints':len(refs(reopened)-f.completed_closeout_refs)}
        assert eff.count==2 and refs(reopened)==f.completed_closeout_refs
        p=folder('positive');s,f=seed(p);eff=Effects(p)
        r1=ex(s,eff).execute_next(f)
        reopened=SQLiteJobStore(p/'jobs.sqlite');j=reopened.get_job(JOB)
        fresh=replace(f,version=j.version,state=j.state,completed_closeout_refs=refs(reopened),
            fold=FoldEvidence(requirement=FoldRequirement.REQUIRED,completed=True,
                bound_task_id=TASK,bound_merge_commit='ab12'))
        r2=ex(reopened,eff).execute_next(fresh);j=reopened.get_job(JOB)
        r3=ex(reopened,eff).execute_next(replace(fresh,version=j.version,state=j.state))
        out['positive']={'effects':eff.count,'results':[result(r1),result(r2),result(r3)],'state':j.state.value}
        assert eff.count==1 and j.state is TaskState.COMPLETE
        assert r3.decision.value=='ALREADY_COMPLETE'
    out['temp_cleanup']='complete'
    return out

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
```

## Interpretation and acceptance hold

Two same-version calls may perform two external effects before one checkpoint loses CAS.
A deliberately stale facts caller may also perform an effect after the real job became
BLOCKED. An unsafe restarted caller that loses UNKNOWN history may repeat the effect.
A truthful successful checkpoint/reload control keeps one effect and reaches COMPLETE;
a repeat observes ALREADY_COMPLETE. Preserve these positive semantics.

There was no production GoalCloseoutExecutor instantiation found under src at the base.
The parent must prove its actual caller's exclusion and recovery contract before treating
these observations as reachable defects. WO205 and its dependency gates retain authority.
The accompanying proposal and GLM lab specify missing process/recovery/port evidence.
