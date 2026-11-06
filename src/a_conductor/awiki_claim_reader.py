"""Read-only #551 adapter; a satisfied claim is not runtime mutation authority.

The A-Wiki reader owns COLLAB parsing, claim identity and generation. This
adapter adds exact consumer binding, not a claim store, lease or DEX receipt.
Production refill remains unwired pending reconciliation and R3 acceptance.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .native_adapters import NativeCommandRunner, NativeGitReadAdapter
from .native_execution import (
    NativeCommandResult,
    NativeCommandSpec,
    NativeExecutionScope,
    NativeSubprocessRunner,
)
from .project_identity import GitReadOnlyRunner, StrictReadOnlyGitRunner


class ClaimBindingError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ClaimTaskBinding:
    task_id: str
    claim_id: str
    generation: int
    repository: str
    worktree: str
    branch: str
    head_sha: str
    agent: str
    scope: tuple[str, ...]


# Fixed code only: arguments never become Python/shell source. -I excludes
# ambient PYTHONPATH and the target worktree from the canonical import path.
_READ = """
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from conductor.state import ClaimLookupError, read_canonical_claim_strict
try:
    result = read_canonical_claim_strict(Path(sys.argv[1]), sys.argv[2])
except ClaimLookupError as error:
    print(json.dumps({"ok": False, "error": str(error)}))
    sys.exit(1)
print(json.dumps(result))
"""
_SHA = re.compile(r"[0-9a-f]{40}")
_CLAIM = re.compile(r"awiki-claim-[0-9a-f]{20}")
_UPSTREAM_ERRORS = frozenset({
    "CLAIM_NOT_FOUND", "CLAIM_AMBIGUOUS", "GIT_HISTORY_SHALLOW",
    "BRANCH_HEAD_UNRESOLVED", "BRANCH_UNBOUND", "BRANCH_INVALID",
    "OWNER_UNBOUND", "SCOPE_UNSAFE", "GIT_UNAVAILABLE", "TASK_ID_REQUIRED",
    "CLAIM_TABLE_MALFORMED", "CLAIM_TABLE_UNAVAILABLE",
})


def _text(value: object) -> bool:
    return (
        isinstance(value, str) and bool(value) and value == value.strip()
        and len(value) <= 1024 and not any(ord(char) < 32 for char in value)
    )


def _valid_scope(scope: object) -> bool:
    if not isinstance(scope, tuple) or not scope or not all(_text(item) for item in scope):
        return False
    if len(set(scope)) != len(scope):
        return False
    for item in scope:
        if not _text(item) or any(char in item for char in "\\:;,|"):
            return False
        path = PurePosixPath(item)
        if path.is_absolute() or item.startswith("~") or ".." in path.parts:
            return False
    return True


def _command_ok(result: object) -> bool:
    return (
        isinstance(result, NativeCommandResult) and not result.timed_out
        and not result.stdout_truncated and not result.stderr_truncated
    )


class AWikiClaimReader:
    """Use a trusted, clean exact-revision A-Wiki checkout without mutating it.

    The operator supplies the approved authority revision and task binding.
    Neither comes from a provider/model response. Call at the existing admission
    seam; the returned binding is a snapshot, not a fence across side effects.
    """

    def __init__(
        self,
        *,
        authority_root: Path,
        authority_head: str,
        python_executable: str = sys.executable,
        runner: NativeCommandRunner | None = None,
        git: GitReadOnlyRunner | None = None,
    ) -> None:
        if not isinstance(authority_head, str) or not _SHA.fullmatch(authority_head):
            raise ClaimBindingError("CLAIM_READER_REVISION_INVALID")
        self._root = Path(authority_root).resolve(strict=True)
        self._revision = authority_head
        self._python = python_executable
        self._scope = NativeExecutionScope(
            root=self._root, mutation_allowed=False,
            allowed_executables=(python_executable, "git"),
            max_timeout_seconds=120, max_output_bytes=65536,
        )
        self._runner = runner or NativeSubprocessRunner(self._scope)
        self._git = git or StrictReadOnlyGitRunner()
        self._status = NativeGitReadAdapter(self._scope, runner=self._runner)

    def _verify_source(self) -> None:
        root = self._git.show_toplevel(self._root)
        head = self._git.head(self._root)
        if not root.success or Path(root.stdout).resolve() != self._root:
            raise ClaimBindingError("CLAIM_READER_WORKTREE_MISMATCH")
        if not head.success or head.stdout != self._revision:
            raise ClaimBindingError("CLAIM_READER_REVISION_MISMATCH")
        status = self._status.status_short()
        if not _command_ok(status) or status.exit_code != 0:
            raise ClaimBindingError("CLAIM_READER_UNAVAILABLE")
        if status.stdout.strip():
            raise ClaimBindingError("CLAIM_READER_DIRTY")

    def _verify_consumer(self, binding: ClaimTaskBinding) -> None:
        root = Path(binding.worktree).resolve(strict=True)
        observed = self._git.show_toplevel(root)
        if not observed.success or Path(observed.stdout).resolve() != root:
            raise ClaimBindingError("CLAIM_WORKTREE_MISMATCH")
        branch = self._git.branch(root)
        head = self._git.head(root)
        if not branch.success or branch.stdout != binding.branch:
            raise ClaimBindingError("CLAIM_WORKTREE_BRANCH_MISMATCH")
        if not head.success or head.stdout != binding.head_sha:
            raise ClaimBindingError("CLAIM_WORKTREE_HEAD_MISMATCH")

    def require_binding(self, binding: ClaimTaskBinding) -> ClaimTaskBinding:
        """Raise code-only refusal unless every canonical/local field matches."""
        if (
            not isinstance(binding, ClaimTaskBinding)
            or not all(_text(getattr(binding, field)) for field in (
                "task_id", "claim_id", "repository", "worktree", "branch", "head_sha", "agent",
            ))
            or not _SHA.fullmatch(binding.head_sha)
            or not _CLAIM.fullmatch(binding.claim_id)
            or type(binding.generation) is not int or binding.generation < 1
            or not Path(binding.worktree).is_absolute()
            or binding.branch == "HEAD" or binding.agent.lower() == "unknown"
            or not _valid_scope(binding.scope)
        ):
            raise ClaimBindingError("CLAIM_BINDING_INVALID")
        try:
            self._verify_source()
            self._verify_consumer(binding)
            result = self._runner.run(NativeCommandSpec(
                argv=(self._python, "-I", "-B", "-c", _READ,
                      binding.worktree, binding.task_id),
                cwd=".", timeout_seconds=120, mutation_intent=False,
            ))
            if not _command_ok(result):
                raise ClaimBindingError("CLAIM_READER_UNAVAILABLE")
            try:
                payload = json.loads(result.stdout)
            except (ValueError, TypeError):
                raise ClaimBindingError("CLAIM_RESPONSE_INVALID") from None
            if result.exit_code != 0:
                error = payload.get("error") if isinstance(payload, dict) else None
                code = error.split(":", 1)[0] if isinstance(error, str) else ""
                raise ClaimBindingError(code if code in _UPSTREAM_ERRORS else "CLAIM_READER_FAILED")
            if (
                not isinstance(payload, dict)
                or payload.get("schema") != "awiki-claim-reader/v1"
                or payload.get("authority_source") != "COLLAB.md+Git"
                or payload.get("worktree_binding") != "CONSUMER_VERIFY_REQUIRED"
                or type(payload.get("generation")) is not int
            ):
                raise ClaimBindingError("CLAIM_RESPONSE_INVALID")
            for field, expected, code in (
                ("task_id", binding.task_id, "CLAIM_TASK_MISMATCH"),
                ("repository", binding.repository, "CLAIM_REPOSITORY_MISMATCH"),
                ("agent", binding.agent, "CLAIM_OWNER_CONFLICT"),
                ("claim_id", binding.claim_id, "CLAIM_ID_MISMATCH"),
                ("generation", binding.generation, "CLAIM_GENERATION_MISMATCH"),
                ("branch", binding.branch, "CLAIM_BRANCH_MISMATCH"),
                ("branch_head_sha", binding.head_sha, "CLAIM_HEAD_MISMATCH"),
                ("scope", list(binding.scope), "CLAIM_SCOPE_MISMATCH"),
            ):
                if payload.get(field) != expected:
                    raise ClaimBindingError(code)
            self._verify_source()
            self._verify_consumer(binding)
        except ClaimBindingError:
            raise
        except Exception:
            # Neither canonical diagnostics nor Git/decoder causes are telemetry.
            raise ClaimBindingError("CLAIM_READER_UNAVAILABLE") from None
        return binding
