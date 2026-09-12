"""WO208 closeout lab repair — child helper (R2 repair).

Runs one closeout scenario to an EXACT cut and hard-exits with a distinct
code. R2 repair properties:

- every cut writes a ``cut-marker.txt`` AT the boundary reached (inside the
  wrapper, immediately before os._exit) — the parent REQUIRES the marker whose
  name matches the exit code, so a fallback exit with the same code but no
  marker cannot masquerade as the hook being entered;
- every unreachable-path fallback uses exit code 79 (DISTINCT from all cut
  codes), so "returned past the hook" is always visible;
- effect receipts are restart-aware (unique per-process names) and fsynced.

Usage: python wo208_child.py --repo-root R --mode M --dir D
Exit codes: 10..14 cuts (see MODE_EXIT), 15 unsafe-restart, 16 safe-restart,
18 barrier timeout, 0 stale-gated/gated results written, 79 UNEXPECTED PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(sys.argv[sys.argv.index("--repo-root") + 1]).resolve() if "--repo-root" in sys.argv else None
if REPO_ROOT is None:
    print("--repo-root is required", file=sys.stderr)
    raise SystemExit(2)
sys.path[:0] = [str(REPO_ROOT / "src"), str(REPO_ROOT)]

from a_conductor.domain import TaskState  # noqa: E402
from a_conductor.goal_closeout import (  # noqa: E402
    CloseoutStage,
    FoldEvidence,
    FoldRequirement,
    GoalCloseoutExecutor,
    closeout_checkpoint_ref,
)
from a_conductor.job_store import SQLiteJobStore  # noqa: E402
from tests.test_goal_closeout import (  # noqa: E402
    JOB, SHA, TASK, ATTEMPT, FakeLeasePort, facts, V,
)

MODE_EXIT = {
    "before-effect": 10,
    "effect-commit": 11,
    "fold-response": 12,
    "checkpoint-commit": 13,
    "complete-commit": 14,
}


def marker(folder: Path, name: str) -> None:
    (folder / f"cut-marker-{name}.txt").write_text(name, encoding="utf-8")


def seed(folder: Path):
    store = SQLiteJobStore(folder / "jobs.sqlite")
    job = store.create_job(job_id=JOB, work_order_ref="wo208-repair", project_id="synthetic")
    for state in (TaskState.READY, TaskState.CLAIMED, TaskState.GATING,
                  TaskState.EXECUTING, TaskState.VERIFYING, TaskState.REVIEW_PENDING):
        extra = {"worker_id": "synthetic-worker"} if state is TaskState.CLAIMED else {}
        job = store.transition(JOB, state, expected_version=job.version, **extra)
    ref = closeout_checkpoint_ref(CloseoutStage.VERIFY_CHECKPOINT,
                                  task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
    before = job.version
    job = store.checkpoint(JOB, checkpoint_ref=ref, expected_version=job.version)
    snapshot = facts(
        state=job.state, version=job.version,
        verification=V(mutation_version=before, checkpoint_version=job.version,
                       checkpoint_ref=ref),
        completed_closeout_refs=frozenset({ref}),
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
    )
    return store, snapshot


def fold_ref_for() -> str:
    return closeout_checkpoint_ref(CloseoutStage.FOLD, task_id=TASK, candidate_sha=SHA,
                                   merge_key="nomerge", fold_key="required")


class FileEffect:
    """Restart-aware fold port: unique per-process receipt names, fsync+close."""

    def __init__(self, folder: Path, gate: "VersionGate | None" = None) -> None:
        self.folder = folder
        self.gate = gate
        existing = list(folder.glob("effect-*.txt"))
        self.count = len(existing)

    def fold(self, request):
        if self.gate is not None:
            self.gate.check()
        self.count += 1
        stem = f"{os.getpid()}-" if self.folder.name.endswith("processes") else ""
        target = self.folder / f"effect-{stem}{self.count:02d}.txt"
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(request.checkpoint_ref)
            handle.flush()
            os.fsync(handle.fileno())
        return type("FoldOutcome", (), {"completed": True})()


class VersionGate:
    """Lab owner precondition at the effect boundary (unchanged from original)."""

    def __init__(self, store, expected_version: int) -> None:
        self.store = store
        self.expected = expected_version
        self.refused = None

    def check(self) -> None:
        current = self.store.get_job(JOB)
        if current.version != self.expected or current.state is not TaskState.REVIEW_PENDING:
            self.refused = f"version {current.version}/state {current.state.value}"
            raise RuntimeError("EFFECT_STALE_OWNER_REFUSED")


def fresh_facts(store: SQLiteJobStore, *, fold_completed, bound_merge="ab12"):
    job = store.get_job(JOB)
    refs = frozenset(e.checkpoint_ref for e in store.list_events(JOB) if e.checkpoint_ref)
    verify_ref = closeout_checkpoint_ref(
        CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
    return facts(
        state=job.state, version=job.version,
        verification=V(mutation_version=job.version - 1, checkpoint_version=job.version,
                       checkpoint_ref=verify_ref),
        completed_closeout_refs=refs,
        fold=FoldEvidence(requirement=FoldRequirement.REQUIRED,
                          completed=fold_completed, bound_task_id=TASK,
                          bound_merge_commit=bound_merge),
    )


def run_cut(mode: str, folder: Path) -> None:
    store, snapshot = seed(folder)
    effect = FileEffect(folder)

    if mode == "before-effect":
        marker(folder, mode)
        os._exit(MODE_EXIT[mode])

    if mode == "effect-commit":
        class CutEffect(FileEffect):
            def fold(self, request):
                super().fold(request)
                marker(folder, mode)
                os._exit(MODE_EXIT[mode])
        GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(),
                             fold_port=CutEffect(folder)).execute_next(snapshot)
        os._exit(79)  # returned past the hook: must be distinct

    if mode == "fold-response":
        class CutStore(SQLiteJobStore):
            def checkpoint(self, job_id, *, checkpoint_ref, expected_version,
                           evidence_ref=None):
                marker(folder, mode)   # hook entered BEFORE any commit
                os._exit(MODE_EXIT[mode])
        GoalCloseoutExecutor(job_store=CutStore(folder / "jobs.sqlite"),
                             lease_release_port=FakeLeasePort(),
                             fold_port=effect).execute_next(snapshot)
        os._exit(79)

    if mode == "checkpoint-commit":
        class CutStore(SQLiteJobStore):
            def checkpoint(self, job_id, *, checkpoint_ref, expected_version,
                           evidence_ref=None):
                result = super().checkpoint(job_id, checkpoint_ref=checkpoint_ref,
                                            expected_version=expected_version,
                                            evidence_ref=evidence_ref)
                marker(folder, mode)   # AFTER the real commit
                os._exit(MODE_EXIT[mode])
        GoalCloseoutExecutor(job_store=CutStore(folder / "jobs.sqlite"),
                             lease_release_port=FakeLeasePort(),
                             fold_port=effect).execute_next(snapshot)
        os._exit(79)

    if mode == "complete-commit":
        # TRUTHFUL prerequisites (R1 fix): stage 1 runs the real fold effect +
        # checkpoint through the actual executor, THEN stage 2 reopens with
        # truthful facts and cuts inside the real COMPLETE transition.
        class Stage1Store(SQLiteJobStore):
            def transition(self, job_id, target_state, *, expected_version, **kw):
                if target_state is TaskState.COMPLETE:
                    os._exit(79)  # stage 1 must not reach COMPLETE
                return super().transition(job_id, target_state,
                                          expected_version=expected_version, **kw)
        r1 = GoalCloseoutExecutor(job_store=Stage1Store(folder / "jobs.sqlite"),
                                  lease_release_port=FakeLeasePort(),
                                  fold_port=effect).execute_next(snapshot)
        if r1.decision.value != "FOLD_REQUIRED":
            os._exit(79)
        reopened = SQLiteJobStore(folder / "jobs.sqlite")

        class CutStore(SQLiteJobStore):
            def transition(self, job_id, target_state, *, expected_version, **kw):
                result = super().transition(job_id, target_state,
                                            expected_version=expected_version, **kw)
                if target_state is TaskState.COMPLETE:
                    marker(folder, mode)   # after COMPLETE commit
                    os._exit(MODE_EXIT[mode])
                return result
        GoalCloseoutExecutor(job_store=CutStore(folder / "jobs.sqlite"),
                             lease_release_port=FakeLeasePort(),
                             fold_port=effect).execute_next(
                                 fresh_facts(reopened, fold_completed=True))
        os._exit(79)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--dir", required=True, type=Path)
    args = parser.parse_args()
    folder: Path = args.dir
    folder.mkdir(parents=True, exist_ok=True)

    if args.mode == "seed-only":
        seed(folder)
        os._exit(0)

    if args.mode in MODE_EXIT:
        run_cut(args.mode, folder)

    if args.mode == "unsafe-restart":
        store = SQLiteJobStore(folder / "jobs.sqlite")
        job = store.get_job(JOB)
        refs = frozenset(e.checkpoint_ref for e in store.list_events(JOB) if e.checkpoint_ref)
        verify_ref = closeout_checkpoint_ref(
            CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
        snapshot = facts(
            state=job.state, version=job.version,
            verification=V(mutation_version=job.version - 1,
                           checkpoint_version=job.version, checkpoint_ref=verify_ref),
            completed_closeout_refs=refs,
            fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=None),
        )
        effect = FileEffect(folder)
        result = GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(),
                                      fold_port=effect).execute_next(snapshot)
        (folder / "unsafe-result.json").write_text(json.dumps(
            {"decision": result.decision.value, "detail": result.detail,
             "effects_this_run": effect.count}), encoding="utf-8")
        marker(folder, "unsafe-restart")
        os._exit(15)

    if args.mode == "safe-restart":
        store = SQLiteJobStore(folder / "jobs.sqlite")
        effect = FileEffect(folder)
        r1 = GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(),
                                  fold_port=effect).execute_next(
                                      fresh_facts(store, fold_completed=True))  # RELEASE/COMPLETE path
        job = store.get_job(JOB)
        from dataclasses import replace
        r2 = GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(),
                                  fold_port=effect).execute_next(
                                      replace(fresh_facts(store, fold_completed=True),
                                              version=job.version, state=job.state))
        job = store.get_job(JOB)
        (folder / "safe-result.json").write_text(json.dumps({
            "first": {"decision": r1.decision.value, "detail": r1.detail},
            "second": {"decision": r2.decision.value, "detail": r2.detail},
            "final_state": job.state.value,
            "effects_this_run": effect.count,
        }), encoding="utf-8")
        marker(folder, "safe-restart")
        os._exit(16)

    if args.mode == "stale-gated":
        store, snapshot = seed(folder)
        store.transition(JOB, TaskState.BLOCKED, expected_version=snapshot.version,
                         worker_id="synthetic-worker")
        from dataclasses import replace
        gate = VersionGate(store, expected_version=snapshot.version)
        effect = FileEffect(folder, gate=gate)
        try:
            result = GoalCloseoutExecutor(
                job_store=store, lease_release_port=FakeLeasePort(),
                fold_port=effect).execute_next(
                    replace(snapshot, state=TaskState.BLOCKED))
        except RuntimeError as exc:
            (folder / "stale-gated.json").write_text(json.dumps(
                {"effect_count": effect.count, "gate_refused": gate.refused,
                 "raised": str(exc)}), encoding="utf-8")
            os._exit(0)
        (folder / "stale-gated.json").write_text(json.dumps(
            {"effect_count": effect.count, "gate_refused": gate.refused,
             "decision": result.decision.value, "detail": result.detail}),
            encoding="utf-8")
        os._exit(0)

    if args.mode == "concurrent-baseline":
        store = SQLiteJobStore(folder / "jobs.sqlite")
        job = store.get_job(JOB)
        refs = frozenset(e.checkpoint_ref for e in store.list_events(JOB) if e.checkpoint_ref)
        verify_ref = closeout_checkpoint_ref(
            CloseoutStage.VERIFY_CHECKPOINT, task_id=TASK, candidate_sha=SHA, attempt_id=ATTEMPT)
        snapshot = facts(
            state=job.state, version=job.version,
            verification=V(mutation_version=job.version - 1,
                           checkpoint_version=job.version, checkpoint_ref=verify_ref),
            completed_closeout_refs=refs,
            fold=FoldEvidence(requirement=FoldRequirement.REQUIRED, completed=False),
        )
        effect = FileEffect(folder)
        ready = folder / f"ready-{os.getpid()}.txt"
        ready.write_text("ready", encoding="utf-8")
        deadline = time.monotonic() + 15.0
        while len(list(folder.glob("ready-*.txt"))) < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        if len(list(folder.glob("ready-*.txt"))) < 2:
            marker(folder, "barrier-timeout")
            os._exit(18)
        result = GoalCloseoutExecutor(job_store=store, lease_release_port=FakeLeasePort(),
                                      fold_port=effect).execute_next(snapshot)
        (folder / f"concurrent-{os.getpid()}.json").write_text(json.dumps(
            {"decision": result.decision.value, "detail": result.detail,
             "effects_this_run": effect.count}), encoding="utf-8")
        os._exit(17)

    # -- S5 helper modes (finite owned helpers; no real Worker/service) ----
    if args.mode == "hang-past-timeout":
        # finite (self-terminates after 120s) but stays alive far past the
        # driver's 6s test timeout -- the REAL timeout proof helper.
        marker(folder, "hang-past-timeout")
        time.sleep(120)
        os._exit(19)

    if args.mode == "bounded-sibling":
        # bounded sibling started alongside the hang helper; writes its
        # start marker and exits 0 quickly -- proves sibling reap on exit.
        (folder / "bounded-sibling-started.txt").write_text(
            str(os.getpid()), encoding="utf-8")
        os._exit(0)

    if args.mode == "early-first-child-fail":
        # first child fails before any effect/checkpoint exists
        marker(folder, "early-first-child-fail")
        print("first child failed before effect", file=sys.stderr)
        os._exit(21)

    if args.mode == "no-output-mode":
        # exits nonzero WITHOUT writing any output artifact
        os._exit(22)

    print(f"unknown mode {args.mode}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    raise SystemExit(main())
