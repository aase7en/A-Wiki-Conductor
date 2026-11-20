"""WO-P1-419 GOT-1b-B — production merge/post-main closeout evidence provider.

REUSE -> WRAP only: a READ-ONLY evidence provider that composes
already-authoritative durable facts with bounded read-only Git/GitHub
observations into the EXISTING ``CloseoutEvidenceBundle`` consumed by the
existing GoalCloseout planner and ContinuityGuard classifier. This module
owns no second closeout DTO authority, store, scheduler, claim, lease,
review, fold, retry, notification, wake, resume, or completion authority:
``GoalCloseout`` remains the sole planner and ``classify_continuity`` the
sole classifier.

Reused authorities (never modified here):
- ``goal_closeout_assembly.CloseoutEvidenceProvider`` /
  ``CloseoutEvidenceBundle`` / ``completed_closeout_checkpoint_refs`` over
  the ``SQLiteJobStore`` CHECKPOINT journal;
- ``goal_closeout`` evidence DTOs, planner finding semantics, and
  ``closeout_checkpoint_ref`` stage identities;
- ``continuity_guard.ContinuitySnapshot`` / ``MergeFoldFact`` /
  ``classify_continuity``;
- ``SQLiteWorkerLeaseStore`` canonical lease health/release semantics;
- ``project_identity.StrictReadOnlyGitRunner`` fixed read-only Git argv
  precedent;
- ``zero_relay_review_evidence`` durable accepted-review + re-pin precedent;
- ``native_git_transactions`` snapshot/re-pin precedent;
- ``upstream_check`` injected bounded-fetcher transport style only.

One ``evidence()`` call performs bounded ordered reads (durable journal /
lease / review -> local Git -> merge observation -> post-main run
observation -> re-pinned journal + local Git) and returns ONE internally
consistent immutable bundle. Any drift across the observation window, any
observation-channel identity mismatch, and any transport failure raises a
typed error and returns no partial bundle. Missing, unavailable, stale or
contradictory FACTS stay UNKNOWN so the existing planner blocks on them;
this provider never coerces UNKNOWN into success.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol
from urllib.request import urlopen

from .continuity_guard import (
    ContinuityClassification,
    ContinuitySnapshot,
    JobFact,
    LeaseFact,
    MergeFoldFact,
    classify_continuity,
)
from .goal_closeout import (
    CloseoutStage,
    FoldRequirement,
    MergeEvidence,
    OwnershipEvidence,
    ReviewEvidence,
    VerificationEvidence,
    closeout_checkpoint_ref,
)
from .goal_closeout_assembly import (
    CloseoutEvidenceBundle,
    completed_closeout_checkpoint_refs,
)
from .job_store import JobStoreError, SQLiteJobStore
from .worker_lease import LeaseHealthKind, SQLiteWorkerLeaseStore, WorkerLeaseError

PRODUCTION_REPOSITORY = "aase7en/A-Wiki-Conductor"
PRODUCTION_WORKFLOW_ID = 338737025
PRODUCTION_WORKFLOW_NAME = "CI"

_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}/[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_RUN_ID_RE = re.compile(r"^[0-9]{1,32}$")
_WORKFLOW_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}$")
_RUN_STATUS_RE = re.compile(r"^[a-z_]{1,32}$")
_RUN_CONCLUSION_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,31}$")
_DISPOSITIONS = frozenset({"ACCEPTED", "REJECTED"})
_DIRTY_STATES = frozenset({"CLEAN", "DIRTY", "UNKNOWN"})

_FETCH_TIMEOUT_SECONDS = 8
_MAX_PR_PAYLOAD_BYTES = 256 * 1024
_MAX_RUNS_PAYLOAD_BYTES = 512 * 1024
_MAX_RUNS_EXAMINED = 100

_GITHUB_BASE = "https://api.github.com/repos"


class ProductionCloseoutObservationError(RuntimeError):
    """Stable typed fail-closed provider failure; never a success path."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


# ---------------- observation DTOs (new module only) ----------------


def _text(value: str, field: str, *, max_length: int = 256) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{field} is invalid")
    return value.strip()


def _sha_or_none(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ValueError(f"{field} is invalid")
    return value.casefold()


@dataclass(frozen=True, slots=True)
class MergeObservation:
    """Bounded read-only PR merge observation — explicit, never a bare bool."""

    observed: bool
    repository: str
    pr_number: int
    merged: bool | None
    merge_commit_sha: str | None
    pr_head_sha: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.observed, bool):
            raise ValueError("observed is invalid")
        if not isinstance(self.repository, str) or not _REPO_RE.fullmatch(self.repository):
            raise ValueError("repository is invalid")
        if isinstance(self.pr_number, bool) or not isinstance(self.pr_number, int):
            raise ValueError("pr_number is invalid")
        if not 1 <= self.pr_number <= 10**9:
            raise ValueError("pr_number is invalid")
        if self.merged is not None and not isinstance(self.merged, bool):
            raise ValueError("merged is invalid")
        object.__setattr__(self, "merge_commit_sha", _sha_or_none(self.merge_commit_sha, "merge_commit_sha"))
        if self.observed and self.pr_head_sha is None:
            raise ValueError("pr_head_sha is required when observed")
        object.__setattr__(self, "pr_head_sha", _sha_or_none(self.pr_head_sha, "pr_head_sha"))


@dataclass(frozen=True, slots=True)
class PostMainRunObservation:
    """Bounded read-only post-main CI run observation for the merge commit."""

    observed: bool
    repository: str | None
    workflow_id: int | None
    workflow_name: str | None
    run_id: str | None
    run_head_sha: str | None
    status: str | None
    conclusion: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.observed, bool):
            raise ValueError("observed is invalid")
        if self.repository is not None and (
            not isinstance(self.repository, str) or not _REPO_RE.fullmatch(self.repository)
        ):
            raise ValueError("repository is invalid")
        for name in ("workflow_id",):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 10**12
            ):
                raise ValueError(f"{name} is invalid")
        if self.workflow_name is not None and (
            not isinstance(self.workflow_name, str)
            or not _WORKFLOW_NAME_RE.fullmatch(self.workflow_name)
        ):
            raise ValueError("workflow_name is invalid")
        if self.run_id is not None and (
            not isinstance(self.run_id, str) or not _RUN_ID_RE.fullmatch(self.run_id)
        ):
            raise ValueError("run_id is invalid")
        object.__setattr__(self, "run_head_sha", _sha_or_none(self.run_head_sha, "run_head_sha"))
        for name in ("status", "conclusion"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value or len(value) > 32
            ):
                raise ValueError(f"{name} is invalid")
        if self.status is not None and not _RUN_STATUS_RE.fullmatch(self.status):
            raise ValueError("status is invalid")
        if self.conclusion is not None and not _RUN_CONCLUSION_RE.fullmatch(self.conclusion):
            raise ValueError("conclusion is invalid")
        if self.observed:
            for name in (
                "repository", "workflow_id", "workflow_name", "run_id", "run_head_sha", "status",
            ):
                if getattr(self, name) is None:
                    raise ValueError(f"{name} is required when observed")


@dataclass(frozen=True, slots=True)
class LocalGitObservation:
    """One read-only local Git identity observation (None = unavailable)."""

    branch: str | None
    head: str | None
    dirty_state: str | None

    def __post_init__(self) -> None:
        if self.branch is not None:
            object.__setattr__(self, "branch", _text(self.branch, "branch", max_length=256))
        if self.head is not None:
            head = _text(self.head, "head", max_length=64)
            if not _SHA_RE.fullmatch(head):
                raise ValueError("head is invalid")
            object.__setattr__(self, "head", head.casefold())
        if self.dirty_state is not None:
            state = self.dirty_state.upper()
            if state not in _DIRTY_STATES:
                raise ValueError("dirty_state is invalid")
            object.__setattr__(self, "dirty_state", state)


@dataclass(frozen=True, slots=True)
class AcceptedReviewObservation:
    """Durable accepted-review fact bound to the exact reviewed head."""

    reviewed_head: str
    disposition: str

    def __post_init__(self) -> None:
        head = _text(self.reviewed_head, "reviewed_head", max_length=64)
        if not _SHA_RE.fullmatch(head):
            raise ValueError("reviewed_head is invalid")
        object.__setattr__(self, "reviewed_head", head.casefold())
        if not isinstance(self.disposition, str) or self.disposition not in _DISPOSITIONS:
            raise ValueError("disposition is invalid")


# ---------------- observation ports ----------------


class MergeObservationPort(Protocol):
    def observe_merge(self) -> MergeObservation: ...


class PostMainRunObservationPort(Protocol):
    def observe_post_main_run(self, merge_commit_sha: str) -> PostMainRunObservation: ...


class LocalGitObservationPort(Protocol):
    def observe(self) -> LocalGitObservation: ...

    def candidate_is_ancestor(
        self, candidate_sha: str, merge_commit_sha: str
    ) -> bool | None: ...


class ReviewObservationPort(Protocol):
    def observe_review(self) -> AcceptedReviewObservation | None: ...


# ---------------- strict read-only local Git observer ----------------


class StrictLocalGitObserver:
    """Fixed read-only Git argv only (``project_identity`` precedent WRAP).

    Exposes exactly: branch/head identity, porcelain status, local object
    provability, and candidate->merge ancestry. No fetch, no checkout, no
    reset/clean/stash/commit, no network, no mutation — ever."""

    def __init__(
        self,
        *,
        worktree: str | Path,
        git_executable: str = "git",
        timeout_seconds: int = 5,
    ) -> None:
        if not isinstance(git_executable, str) or not git_executable.strip():
            raise ValueError("git_executable is invalid")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, int)
            or timeout_seconds < 1
        ):
            raise ValueError("timeout_seconds is invalid")
        self._worktree = Path(worktree).expanduser().resolve(strict=False)
        self._git_executable = git_executable.strip()
        self._timeout_seconds = timeout_seconds

    def _run(self, args: tuple[str, ...]) -> subprocess.CompletedProcess | None:
        argv = [
            self._git_executable,
            "-c",
            f"safe.directory={self._worktree.as_posix()}",
            "-C",
            str(self._worktree),
            *args,
        ]
        try:
            return subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self._timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

    def observe(self) -> LocalGitObservation:
        branch_result = self._run(("rev-parse", "--abbrev-ref", "HEAD"))
        branch = branch_result.stdout.strip() if branch_result and branch_result.returncode == 0 else None
        if branch is not None and (not branch or len(branch) > 256):
            branch = None
        head_result = self._run(("rev-parse", "HEAD"))
        head = None
        if head_result is not None and head_result.returncode == 0:
            candidate = head_result.stdout.strip()
            if _SHA_RE.fullmatch(candidate):
                head = candidate.casefold()
        status_result = self._run(("status", "--porcelain"))
        if status_result is None or status_result.returncode != 0:
            dirty = None
        else:
            dirty = "DIRTY" if status_result.stdout.strip() else "CLEAN"
        return LocalGitObservation(branch=branch, head=head, dirty_state=dirty)

    def candidate_is_ancestor(
        self, candidate_sha: str, merge_commit_sha: str
    ) -> bool | None:
        if not isinstance(candidate_sha, str) or not _SHA_RE.fullmatch(candidate_sha):
            return None
        if not isinstance(merge_commit_sha, str) or not _SHA_RE.fullmatch(merge_commit_sha):
            return None
        candidate = candidate_sha.casefold()
        merge = merge_commit_sha.casefold()
        # prove the merge object exists locally first: a missing object is
        # UNKNOWN ancestry, never a silent False and never a network fetch
        object_probe = self._run(("cat-file", "-e", f"{merge}^{{commit}}"))
        if object_probe is None or object_probe.returncode != 0:
            return None
        relation = self._run(("merge-base", "--is-ancestor", candidate, merge))
        if relation is None:
            return None
        if relation.returncode == 0:
            return True
        if relation.returncode == 1:
            return False
        return None


# ---------------- bounded GitHub observation adapter ----------------


Fetcher = Callable[[str], str]


class _DuplicateKeyError(ValueError):
    pass


class _NonStandardJsonConstant(ValueError):
    pass


def _reject_json_constant(_value: str):
    raise _NonStandardJsonConstant


def _pairs_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError
        result[key] = value
    return result


def _default_fetch(url: str) -> str:
    with urlopen(url, timeout=_FETCH_TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def _bounded_json(text: object, *, max_bytes: int, code_prefix: str) -> dict:
    if not isinstance(text, str):
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_INVALID")
    if len(text) > max_bytes:
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_TOO_LARGE")
    try:
        payload = json.loads(
            text, object_pairs_hook=_pairs_object, parse_constant=_reject_json_constant
        )
    except _DuplicateKeyError as exc:
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_INVALID") from exc
    except _NonStandardJsonConstant as exc:
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_INVALID") from exc
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_INVALID") from exc
    if not isinstance(payload, dict):
        raise ProductionCloseoutObservationError(f"{code_prefix}_PAYLOAD_INVALID")
    return payload


def _fetch(url: str, fetcher: Fetcher, code_prefix: str) -> str:
    try:
        return fetcher(url)
    except ProductionCloseoutObservationError:
        raise
    except Exception as exc:
        raise ProductionCloseoutObservationError(f"{code_prefix}_FETCH_FAILED") from exc


def _payload_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise ProductionCloseoutObservationError("MERGE_IDENTITY_INVALID")
    return value.casefold()


class BoundedGitHubObservationAdapter:
    """Bounded read-only GitHub REST adapter (``upstream_check`` style).

    Injectable fetcher, fixed timeout, bounded payload handling, strict
    required identity validation, no credential persistence and no raw
    secret logging. Observation identity is constructor-bound; there is no
    mutable global registry."""

    def __init__(
        self,
        *,
        repository: str,
        pr_number: int,
        workflow_id: int,
        workflow_name: str,
        fetcher: Fetcher | None = None,
        max_pr_payload_bytes: int = _MAX_PR_PAYLOAD_BYTES,
        max_runs_payload_bytes: int = _MAX_RUNS_PAYLOAD_BYTES,
    ) -> None:
        if not isinstance(repository, str) or not _REPO_RE.fullmatch(repository):
            raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        if (
            isinstance(pr_number, bool)
            or not isinstance(pr_number, int)
            or not 1 <= pr_number <= 10**9
        ):
            raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        if (
            isinstance(workflow_id, bool)
            or not isinstance(workflow_id, int)
            or not 1 <= workflow_id <= 10**12
        ):
            raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        if not isinstance(workflow_name, str) or not _WORKFLOW_NAME_RE.fullmatch(workflow_name):
            raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        if fetcher is not None and not callable(fetcher):
            raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        for name, value in (
            ("max_pr_payload_bytes", max_pr_payload_bytes),
            ("max_runs_payload_bytes", max_runs_payload_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ProductionCloseoutObservationError("ADAPTER_CONFIG_INVALID")
        self._repository = repository
        self._pr_number = pr_number
        self._workflow_id = workflow_id
        self._workflow_name = workflow_name
        self._fetcher = fetcher or _default_fetch
        self._max_pr = max_pr_payload_bytes
        self._max_runs = max_runs_payload_bytes

    def observe_merge(self) -> MergeObservation:
        url = f"{_GITHUB_BASE}/{self._repository}/pulls/{self._pr_number}"
        payload = _bounded_json(
            _fetch(url, self._fetcher, "MERGE"),
            max_bytes=self._max_pr,
            code_prefix="MERGE",
        )
        merged = payload.get("merged")
        if not isinstance(merged, bool):
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID")
        raw_commit = payload.get("merge_commit_sha")
        merge_commit = None
        if raw_commit is not None:
            if not isinstance(raw_commit, str) or not _SHA_RE.fullmatch(raw_commit):
                raise ProductionCloseoutObservationError("MERGE_IDENTITY_INVALID")
            merge_commit = raw_commit.casefold()
        head = payload.get("head")
        if not isinstance(head, dict):
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID")
        pr_head = _payload_sha(head.get("sha"), "head.sha")
        base = payload.get("base")
        if not isinstance(base, dict):
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID")
        repo = base.get("repo")
        if not isinstance(repo, dict):
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID")
        full_name = repo.get("full_name")
        if not isinstance(full_name, str) or not _REPO_RE.fullmatch(full_name):
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID")
        if full_name != self._repository:
            raise ProductionCloseoutObservationError("MERGE_REPO_MISMATCH")
        try:
            return MergeObservation(
                observed=True,
                repository=full_name,
                pr_number=self._pr_number,
                merged=merged,
                merge_commit_sha=merge_commit,
                pr_head_sha=pr_head,
            )
        except ValueError as exc:
            raise ProductionCloseoutObservationError("MERGE_PAYLOAD_INVALID") from exc

    def observe_post_main_run(self, merge_commit_sha: str) -> PostMainRunObservation:
        if not isinstance(merge_commit_sha, str) or not _SHA_RE.fullmatch(merge_commit_sha):
            raise ProductionCloseoutObservationError("POST_MAIN_IDENTITY_INVALID")
        merge = merge_commit_sha.casefold()
        url = (
            f"{_GITHUB_BASE}/{self._repository}/actions/workflows/"
            f"{self._workflow_id}/runs?per_page={_MAX_RUNS_EXAMINED}"
        )
        payload = _bounded_json(
            _fetch(url, self._fetcher, "POST_MAIN"),
            max_bytes=self._max_runs,
            code_prefix="POST_MAIN",
        )
        workflow_id = payload.get("workflow_id")
        if (
            isinstance(workflow_id, bool)
            or not isinstance(workflow_id, int)
        ):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        if workflow_id != self._workflow_id:
            raise ProductionCloseoutObservationError("POST_MAIN_WORKFLOW_IDENTITY_MISMATCH")
        runs = payload.get("runs")
        if not isinstance(runs, list):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        selected = None
        for run in runs[:_MAX_RUNS_EXAMINED]:
            if not isinstance(run, dict):
                raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
            head = run.get("head_sha")
            if not isinstance(head, str) or not _SHA_RE.fullmatch(head):
                raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
            if head.casefold() == merge:
                selected = run
                break
        if selected is None:
            return PostMainRunObservation(
                observed=False,
                repository=None,
                workflow_id=workflow_id,
                workflow_name=None,
                run_id=None,
                run_head_sha=None,
                status=None,
                conclusion=None,
            )
        run_id = selected.get("id")
        if isinstance(run_id, bool) or not isinstance(run_id, int) or not 1 <= run_id <= 10**12:
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        status = selected.get("status")
        if not isinstance(status, str) or not _RUN_STATUS_RE.fullmatch(status):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        if "conclusion" not in selected:
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        conclusion = selected.get("conclusion")
        if conclusion is not None and (
            not isinstance(conclusion, str) or not _RUN_CONCLUSION_RE.fullmatch(conclusion)
        ):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        run_workflow_id = selected.get("workflow_id")
        if run_workflow_id != self._workflow_id:
            raise ProductionCloseoutObservationError("POST_MAIN_WORKFLOW_IDENTITY_MISMATCH")
        name = selected.get("name")
        if not isinstance(name, str) or not _WORKFLOW_NAME_RE.fullmatch(name):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        if name != self._workflow_name:
            raise ProductionCloseoutObservationError("POST_MAIN_WORKFLOW_IDENTITY_MISMATCH")
        repository = selected.get("repository")
        if not isinstance(repository, dict):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        full_name = repository.get("full_name")
        if not isinstance(full_name, str) or not _REPO_RE.fullmatch(full_name):
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID")
        if full_name != self._repository:
            raise ProductionCloseoutObservationError("POST_MAIN_REPO_MISMATCH")
        try:
            return PostMainRunObservation(
                observed=True,
                repository=full_name,
                workflow_id=run_workflow_id,
                workflow_name=name,
                run_id=str(run_id),
                run_head_sha=merge,
                status=status,
                conclusion=conclusion,
            )
        except ValueError as exc:
            raise ProductionCloseoutObservationError("POST_MAIN_PAYLOAD_INVALID") from exc


# ---------------- production provider ----------------


def _clock_text(clock: Callable[[], object]) -> str:
    value = clock()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ProductionCloseoutObservationError("PROVIDER_CLOCK_INVALID")
        from datetime import timezone

        return (
            value.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    if not isinstance(value, str) or not value.strip():
        raise ProductionCloseoutObservationError("PROVIDER_CLOCK_INVALID")
    return value.strip()


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ProductionCloseoutEvidenceProvider:
    """READ-ONLY production closeout evidence provider (GOT-1b-B).

    Implements the existing ``CloseoutEvidenceProvider`` protocol: one
    ``evidence()`` call yields one internally consistent, re-pinned
    ``CloseoutEvidenceBundle`` composed from durable authorities plus
    bounded read-only observations. Observation identity (repository, PR,
    workflow id/name) is constructor-bound. Zero writes: no job, lease,
    review, checkpoint, Git, or GitHub mutation ever originates here."""

    def __init__(
        self,
        *,
        job_store: SQLiteJobStore,
        lease_store: SQLiteWorkerLeaseStore,
        git_observer: LocalGitObservationPort,
        merge_port: MergeObservationPort,
        post_main_port: PostMainRunObservationPort,
        review_port: ReviewObservationPort | None,
        review_required: bool,
        repository: str,
        pr_number: int,
        workflow_id: int,
        workflow_name: str,
        job_id: str,
        task_id: str,
        attempt_id: str,
        session_id: str,
        lease_id: str | None,
        candidate_sha: str,
        branch: str,
        worktree: str,
        clock: Callable[[], object],
    ) -> None:
        for method in ("get_job", "list_events"):
            if not callable(getattr(job_store, method, None)):
                raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        for method in ("inspect_health", "list_active"):
            if not callable(getattr(lease_store, method, None)):
                raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        for method in ("observe", "candidate_is_ancestor"):
            if not callable(getattr(git_observer, method, None)):
                raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not callable(getattr(merge_port, "observe_merge", None)):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not callable(getattr(post_main_port, "observe_post_main_run", None)):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not isinstance(review_required, bool):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if review_required and not callable(getattr(review_port, "observe_review", None)):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not isinstance(repository, str) or not _REPO_RE.fullmatch(repository):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if isinstance(pr_number, bool) or not isinstance(pr_number, int) or not 1 <= pr_number <= 10**9:
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if (
            isinstance(workflow_id, bool)
            or not isinstance(workflow_id, int)
            or not 1 <= workflow_id <= 10**12
        ):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not isinstance(workflow_name, str) or not _WORKFLOW_NAME_RE.fullmatch(workflow_name):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        if not callable(clock):
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID")
        try:
            self._job_id = _text(job_id, "job_id", max_length=128)
            self._task_id = _text(task_id, "task_id", max_length=256)
            self._attempt_id = _text(attempt_id, "attempt_id", max_length=256)
            self._session_id = _text(session_id, "session_id", max_length=128)
            self._lease_id = (
                None if lease_id is None else _text(lease_id, "lease_id", max_length=128)
            )
            candidate = _text(candidate_sha, "candidate_sha", max_length=64)
            if not _SHA_RE.fullmatch(candidate):
                raise ValueError("candidate_sha is invalid")
            self._candidate_sha = candidate.casefold()
            self._branch = _text(branch, "branch", max_length=256)
            self._worktree = _text(worktree, "worktree", max_length=1024)
        except ValueError as exc:
            raise ProductionCloseoutObservationError("PROVIDER_CONFIG_INVALID") from exc
        self._job_store = job_store
        self._lease_store = lease_store
        self._git_observer = git_observer
        self._merge_port = merge_port
        self._post_main_port = post_main_port
        self._review_port = review_port
        self._review_required = review_required
        self._repository = repository
        self._pr_number = pr_number
        self._workflow_id = workflow_id
        self._workflow_name = workflow_name
        self._clock = clock
        self._verify_ref = closeout_checkpoint_ref(
            CloseoutStage.VERIFY_CHECKPOINT,
            task_id=self._task_id,
            candidate_sha=self._candidate_sha,
            attempt_id=self._attempt_id,
        )

    # ---- one internally consistent, re-pinned observation ----

    def evidence(self) -> CloseoutEvidenceBundle:
        now_text = _clock_text(self._clock)

        # 1. durable facts: checkpoint journal, job state, lease authority,
        #    accepted review
        refs_first = self._durable_refs()
        job_state = self._job_state()
        own_health, own_lease = self._own_lease_health(now_text)
        active_leases = self._active_leases()
        review_observation = self._review_observation()

        # 2. local Git identity (first pin)
        git_first = self._git_observation()

        # 3. merge observation (bounded read-only)
        merge_obs = self._merge_observation()

        # 4. post-main run observation (bounded read-only)
        run_obs = self._post_main_observation(merge_obs)

        # 5. re-pin the durable journal and local Git identity
        refs_last = self._durable_refs()
        git_last = self._git_observation()

        # 6. any drift across the observation window fails closed
        if refs_first != refs_last:
            raise ProductionCloseoutObservationError("CHECKPOINT_JOURNAL_DRIFT")
        if git_first != git_last:
            raise ProductionCloseoutObservationError("LOCAL_GIT_DRIFT")
        git = self._bind_local_git_identity(git_first)

        return self._compose(
            refs=refs_last,
            job_state=job_state,
            own_health=own_health,
            own_lease=own_lease,
            active_leases=active_leases,
            review_observation=review_observation,
            git=git,
            merge_obs=merge_obs,
            run_obs=run_obs,
            now_text=now_text,
        )

    # ---- bounded ordered reads ----

    def _durable_refs(self) -> frozenset[str]:
        try:
            return completed_closeout_checkpoint_refs(self._job_store, self._job_id)
        except JobStoreError as exc:
            raise ProductionCloseoutObservationError("CHECKPOINT_JOURNAL_READ_FAILED") from exc
        except Exception as exc:
            raise ProductionCloseoutObservationError("CHECKPOINT_JOURNAL_READ_FAILED") from exc

    def _job_state(self):
        try:
            return self._job_store.get_job(self._job_id).state
        except JobStoreError as exc:
            raise ProductionCloseoutObservationError("DURABLE_JOB_READ_FAILED") from exc
        except Exception as exc:
            raise ProductionCloseoutObservationError("DURABLE_JOB_READ_FAILED") from exc

    def _own_lease_health(self, now_text: str):
        if self._lease_id is None:
            return None, None
        try:
            health = self._lease_store.inspect_health(self._lease_id, now=now_text)
        except WorkerLeaseError:
            return "UNAVAILABLE", None
        except Exception:
            return "UNAVAILABLE", None
        return health.kind, health.lease

    def _active_leases(self) -> tuple:
        try:
            return tuple(self._lease_store.list_active())
        except WorkerLeaseError as exc:
            raise ProductionCloseoutObservationError("DURABLE_LEASE_READ_FAILED") from exc
        except Exception as exc:
            raise ProductionCloseoutObservationError("DURABLE_LEASE_READ_FAILED") from exc

    def _review_observation(self) -> AcceptedReviewObservation | None:
        if not self._review_required or self._review_port is None:
            return None
        try:
            return self._review_port.observe_review()
        except ProductionCloseoutObservationError:
            raise
        except Exception as exc:
            raise ProductionCloseoutObservationError("REVIEW_OBSERVATION_FAILED") from exc

    def _git_observation(self) -> LocalGitObservation:
        try:
            observation = self._git_observer.observe()
        except ProductionCloseoutObservationError:
            raise
        except Exception as exc:
            raise ProductionCloseoutObservationError("LOCAL_GIT_OBSERVATION_FAILED") from exc
        if not isinstance(observation, LocalGitObservation):
            raise ProductionCloseoutObservationError("LOCAL_GIT_OBSERVATION_FAILED")
        return observation

    def _bind_local_git_identity(self, git: LocalGitObservation) -> LocalGitObservation:
        """Validate the pinned local Git identity against the configured
        lane identity AFTER the drift compare so a mid-observation change is
        always reported as drift, never silently re-bound."""
        if git.branch is None or git.head is None:
            raise ProductionCloseoutObservationError("LOCAL_GIT_IDENTITY_UNAVAILABLE")
        if git.branch != self._branch:
            raise ProductionCloseoutObservationError("LOCAL_BRANCH_MISMATCH")
        return git

    def _merge_observation(self) -> MergeObservation:
        try:
            observation = self._merge_port.observe_merge()
        except ProductionCloseoutObservationError:
            raise
        except Exception as exc:
            raise ProductionCloseoutObservationError("MERGE_OBSERVATION_FAILED") from exc
        if not isinstance(observation, MergeObservation):
            raise ProductionCloseoutObservationError("MERGE_OBSERVATION_FAILED")
        if observation.repository != self._repository:
            raise ProductionCloseoutObservationError("MERGE_REPO_MISMATCH")
        if observation.pr_number != self._pr_number:
            raise ProductionCloseoutObservationError("MERGE_PR_MISMATCH")
        if not observation.observed:
            # merge-state availability failure stays a FACT: merged remains
            # unknown and the existing planner blocks on MERGE_NOT_MERGED /
            # CONTINUITY_UNKNOWN — never fabricated success
            return observation
        if observation.pr_head_sha is None:
            raise ProductionCloseoutObservationError("MERGE_CANDIDATE_MISMATCH")
        if observation.pr_head_sha != self._candidate_sha:
            raise ProductionCloseoutObservationError("MERGE_CANDIDATE_MISMATCH")
        return observation

    def _post_main_observation(self, merge_obs: MergeObservation):
        if merge_obs.merged is not True or merge_obs.merge_commit_sha is None:
            return None
        merge_commit = merge_obs.merge_commit_sha
        try:
            observation = self._post_main_port.observe_post_main_run(merge_commit)
        except ProductionCloseoutObservationError:
            raise
        except Exception as exc:
            raise ProductionCloseoutObservationError("POST_MAIN_OBSERVATION_FAILED") from exc
        if not isinstance(observation, PostMainRunObservation):
            raise ProductionCloseoutObservationError("POST_MAIN_OBSERVATION_FAILED")
        if observation.repository is not None and observation.repository != self._repository:
            raise ProductionCloseoutObservationError("POST_MAIN_REPO_MISMATCH")
        if observation.workflow_id is not None and observation.workflow_id != self._workflow_id:
            raise ProductionCloseoutObservationError("POST_MAIN_WORKFLOW_IDENTITY_MISMATCH")
        if (
            observation.workflow_name is not None
            and observation.workflow_name != self._workflow_name
        ):
            raise ProductionCloseoutObservationError("POST_MAIN_WORKFLOW_IDENTITY_MISMATCH")
        if observation.observed and observation.run_head_sha != merge_commit:
            raise ProductionCloseoutObservationError("POST_MAIN_IDENTITY_MISMATCH")
        return observation

    # ---- composition (pure over the pinned observations) ----

    def _compose(
        self,
        *,
        refs: frozenset[str],
        job_state,
        own_health,
        own_lease,
        active_leases: tuple,
        review_observation: AcceptedReviewObservation | None,
        git: LocalGitObservation,
        merge_obs: MergeObservation,
        run_obs,
        now_text: str,
    ) -> CloseoutEvidenceBundle:
        merged = merge_obs.merged if merge_obs.observed else None
        merge_commit = merge_obs.merge_commit_sha if merged is True else None

        ancestry = None
        if merged is True and merge_commit is not None:
            try:
                ancestry = self._git_observer.candidate_is_ancestor(
                    self._candidate_sha, merge_commit
                )
            except ProductionCloseoutObservationError:
                raise
            except Exception as exc:
                raise ProductionCloseoutObservationError("LOCAL_GIT_OBSERVATION_FAILED") from exc
            if ancestry is not None and not isinstance(ancestry, bool):
                raise ProductionCloseoutObservationError("LOCAL_GIT_OBSERVATION_FAILED")

        run_id = None
        post_main_success = None
        post_main_merge_commit = None
        if run_obs is not None and run_obs.observed:
            run_id = run_obs.run_id
            post_main_merge_commit = merge_commit
            if run_obs.status == "completed":
                post_main_success = run_obs.conclusion == "SUCCESS"
            else:
                post_main_success = None

        merge = MergeEvidence(
            required=True,
            merged=merged,
            merge_commit=merge_commit,
            accepted_candidate_sha=self._candidate_sha if merged is True else None,
            accepted_candidate_ancestor=ancestry if merged is True else None,
            post_main_required=True,
            post_main_run_id=run_id,
            post_main_success=post_main_success,
            post_main_merge_commit=post_main_merge_commit,
        )

        verification_ok = self._verify_ref in refs
        verification = VerificationEvidence(
            task_id=self._task_id,
            attempt_id=self._attempt_id,
            ok=verification_ok,
            checkpoint_ref=self._verify_ref if verification_ok else None,
            mutation_version=None,
            checkpoint_version=None,
        )

        if not self._review_required:
            review = ReviewEvidence(required=False, passed=None, reviewed_sha=None)
        elif review_observation is None:
            review = ReviewEvidence(required=True, passed=None, reviewed_sha=None)
        elif review_observation.disposition != "ACCEPTED":
            review = ReviewEvidence(required=True, passed=False, reviewed_sha=None)
        else:
            review = ReviewEvidence(
                required=True,
                passed=True,
                reviewed_sha=review_observation.reviewed_head,
            )

        ownership_known = self._ownership_known(own_health, own_lease)
        verdict = classify_continuity(
            self._snapshot(
                refs=refs,
                job_state=job_state,
                own_health=own_health,
                own_lease=own_lease,
                active_leases=active_leases,
                git=git,
                merge_obs=merge_obs,
                merge_commit=merge_commit,
                ownership_known=ownership_known,
                now_text=now_text,
            )
        )
        conflicting = any(
            finding.kind is ContinuityClassification.CLAIM_CONFLICT
            for finding in verdict.findings
        )
        transition_in_progress = any(
            finding.kind is ContinuityClassification.RECONCILE_REQUIRED
            for finding in verdict.findings
        )
        ownership = OwnershipEvidence(
            known=ownership_known,
            conflicting=conflicting,
            transition_in_progress=transition_in_progress,
        )

        return CloseoutEvidenceBundle(
            verification=verification,
            continuity=verdict.classification,
            review=review,
            merge=merge,
            fold_requirement=FoldRequirement.REQUIRED,
            fold_not_required_reason=None,
            ownership=ownership,
            blocking_findings=(),
        )

    def _ownership_known(self, own_health, own_lease) -> bool:
        if self._lease_id is None:
            return True
        if own_lease is None:
            return False
        return (
            own_lease.session_id == self._session_id
            and own_lease.task_id == self._task_id
        )

    def _lease_state(self, lease, now_text: str) -> str:
        if getattr(lease, "quarantine_code", None) is not None:
            return "QUARANTINED"
        expires_at = getattr(lease, "expires_at", None)
        if not isinstance(expires_at, str) or not expires_at.strip():
            return "UNKNOWN"
        try:
            return (
                "STALE"
                if _parse_timestamp(now_text) >= _parse_timestamp(expires_at)
                else "ACTIVE"
            )
        except ValueError:
            return "UNKNOWN"

    def _release_complete(self, own_health, refs: frozenset[str]) -> bool | None:
        if self._lease_id is None:
            return True
        if own_health is LeaseHealthKind.RELEASED:
            release_ref = closeout_checkpoint_ref(
                CloseoutStage.RELEASE_LEASE,
                task_id=self._task_id,
                candidate_sha=self._candidate_sha,
                lease_id=self._lease_id,
            )
            return release_ref in refs
        if own_health is LeaseHealthKind.ACTIVE:
            return False
        return None

    def _snapshot(
        self,
        *,
        refs: frozenset[str],
        job_state,
        own_health,
        own_lease,
        active_leases: tuple,
        git: LocalGitObservation,
        merge_obs: MergeObservation,
        merge_commit: str | None,
        ownership_known: bool,
        now_text: str,
    ) -> ContinuitySnapshot:
        lease_facts = []
        for lease in active_leases:
            try:
                lease_facts.append(
                    LeaseFact(
                        lease_id=lease.lease_id,
                        session_id=lease.session_id,
                        task_id=lease.task_id,
                        worktree_key=lease.worktree_key,
                        mutable_scope=tuple(lease.mutable_scope),
                        state=self._lease_state(lease, now_text),
                    )
                )
            except ValueError as exc:
                raise ProductionCloseoutObservationError("DURABLE_LEASE_FACT_INVALID") from exc
        merge_fold = None
        if merge_commit is not None:
            fold_ref = closeout_checkpoint_ref(
                CloseoutStage.FOLD,
                task_id=self._task_id,
                candidate_sha=self._candidate_sha,
                merge_key=merge_commit,
                fold_key="required",
            )
            fold_complete = fold_ref in refs
            release_complete = self._release_complete(own_health, refs)
            merge_fold = MergeFoldFact(
                merge_commit=merge_commit,
                fold_complete=fold_complete,
                release_complete=release_complete,
            )
        mutable_scope = (
            tuple(own_lease.mutable_scope) if own_lease is not None else ()
        )
        try:
            return ContinuitySnapshot(
                worktree=self._worktree,
                branch=self._branch,
                session_id=self._session_id,
                task_id=self._task_id,
                expected_head=self._candidate_sha,
                local_head=git.head,
                remote_head=merge_obs.pr_head_sha,
                dirty_state=git.dirty_state,
                ownership_known=ownership_known,
                mutable_scope=mutable_scope,
                leases=tuple(lease_facts),
                job=JobFact(job_id=self._job_id, state=job_state),
                merge_fold=merge_fold,
                projections=(),
            )
        except ValueError as exc:
            raise ProductionCloseoutObservationError("PROVIDER_SNAPSHOT_INVALID") from exc


def bind_production_github_adapter(
    *,
    pr_number: int,
    fetcher: Fetcher | None = None,
) -> BoundedGitHubObservationAdapter:
    """Bind this WO's production GitHub observation identity (repo
    aase7en/A-Wiki-Conductor, workflow 338737025 / CI). Frozen constants —
    no mutable registry."""
    return BoundedGitHubObservationAdapter(
        repository=PRODUCTION_REPOSITORY,
        pr_number=pr_number,
        workflow_id=PRODUCTION_WORKFLOW_ID,
        workflow_name=PRODUCTION_WORKFLOW_NAME,
        fetcher=fetcher,
    )
