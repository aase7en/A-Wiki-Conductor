"""WO-P1-158 Phase D — SupervisedZCodeRunner (durable integration).

Integrates ZCode app-server execution into the existing durable authorities:

- ONE shared run lifecycle via ``SupervisedRunCoordinator`` (fingerprint,
  duplicate guard, record creation, launch, poll/timeout, collect/version CAS);
- durable ``backend_id = zcode-app-server``;
- identity-before-prompt: ``child.identity.json`` is atomically persisted and
  re-parsed BEFORE any protocol message is sent;
- runtime-selection double-check: the sanitized selection digest is validated
  once during preparation and again at the launch seam (``ZCODE_SELECTION_DRIFT``
  fails closed before spawn);
- strict artifact ordering: bounded stdout (final response) and redacted stderr
  as execution progresses, then atomic strict ``report.json``; the standard
  ``result.json`` is written ONLY when a REAL terminal exit code exists —
  UNKNOWN/EXIT_PENDING never fabricates a result and returns recovery-required;
- normal shutdown is stdin-EOF + bounded natural-exit wait; no terminate/kill
  ladder and no automatic kill.

No scheduler, retry engine, second execution store, admission, lease, or
provider-store authority is added here.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from .execution_deduplication import ExecutionFingerprintSpec
from .native_execution import NativeCommandResult
from .provider_configuration import (
    HarnessRuntimeBinding,
    runtime_selection_sha256,
)
from .supervised_run_coordinator import (
    SupervisedLauncher,
    SupervisedExecutionFingerprintStore,
    SupervisedRunCoordinator,
    SupervisedRunIdentity,
)
from .zcode_protocol import ZCODE_MAX_RESPONSE_BYTES, ZCodeProtocolError, ZCodeProtocolDriver
from .zcode_supervised_helper import (
    ZCodeChildIdentity,
    parse_child_identity_document,
    serialize_child_identity_document,
    target_argv_sha256,
    validate_app_server_argv,
    validate_output_budget,
)


ZCODE_BACKEND_ID = "zcode-app-server"


class ZCodeSelectionSource(Protocol):
    """Trusted Conductor-side provider of the sanitized runtime selection."""

    def resolved_selection(self) -> dict:
        """Return {'runtime_binding': HarnessRuntimeBinding|dict,
        'runtime_base_url': str, 'runtime_source_enabled': bool|None}."""


class ZCodeSpawnTransportFactory(Protocol):
    """Lifecycle seam owned by the supervised helper (Phase D runtime)."""

    def open(
        self,
        *,
        argv: tuple[str, ...],
        environment: dict[str, str],
        execution_id: str,
        run_dir: str,
    ) -> object: ...


class ZCodeFilesystem(Protocol):
    def write_atomic(self, relative_path: str, text: str) -> None: ...
    def read_text(self, relative_path: str) -> str: ...
    def append_text(self, relative_path: str, text: str) -> None: ...
    def write_bytes_file(self, relative_path: str, data: bytes) -> None: ...


@dataclass(frozen=True, slots=True)
class ZCodeRunResult:
    native: NativeCommandResult
    report: dict | None
    recovery_required: bool
    error_code: str | None = None


class ZCodeSelectionDriftError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("ZCODE_SELECTION_DRIFT")


def _selection_digest(selection: dict) -> str:
    binding = selection["runtime_binding"]
    if not isinstance(binding, HarnessRuntimeBinding):
        binding = HarnessRuntimeBinding.from_dict(binding)
    return runtime_selection_sha256(
        runtime_binding=binding,
        runtime_base_url=selection["runtime_base_url"],
        runtime_source_enabled=selection.get("runtime_source_enabled"),
    )


class SupervisedZCodeRunner:
    """One ZCode app-server turn under the existing durable authorities."""

    def __init__(
        self,
        *,
        execution_store: SupervisedExecutionFingerprintStore,
        supervised: SupervisedLauncher,
        identity: SupervisedRunIdentity,
        selection_source: ZCodeSelectionSource,
        spawn_transport_factory: ZCodeSpawnTransportFactory,
        filesystem: ZCodeFilesystem,
        executable: str,
        bundle_js: str,
        secret_reference: str,
        poll_interval_seconds: float = 0.05,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
        max_response_bytes: int = ZCODE_MAX_RESPONSE_BYTES,
    ) -> None:
        if identity.backend_id != ZCODE_BACKEND_ID:
            raise ValueError("identity.backend_id must be zcode-app-server")
        self._coordinator = SupervisedRunCoordinator(
            execution_store=execution_store,
            supervised=supervised,
            identity=identity,
            agent_ref="agent:zcode-app-server",
            poll_interval_seconds=poll_interval_seconds,
            sleep_fn=sleep_fn,
            clock_fn=clock_fn,
        )
        self._selection_source = selection_source
        self._spawn_transport_factory = spawn_transport_factory
        self._filesystem = filesystem
        self._executable = executable
        self._bundle_js = bundle_js
        if not isinstance(secret_reference, str) or not secret_reference.strip():
            raise ValueError("secret_reference is invalid")
        self._secret_reference = secret_reference
        self._max_response_bytes = validate_output_budget(max_response_bytes)

    # -- identity: argv fixed, prompt never present ----------------

    def argv(self) -> tuple[str, ...]:
        argv = (
            self._executable,
            self._bundle_js,
            "app-server",
            "--stdio",
            "--surface",
            "desktop",
        )
        if not validate_app_server_argv(
            argv, executable=self._executable, bundle_js=self._bundle_js
        ):
            raise ValueError("ZCODE_ARGV_GRAMMAR_INVALID")
        return argv

    def fingerprint_spec(self, *, operation_ref: str) -> ExecutionFingerprintSpec:
        argv = self.argv()
        base = self._coordinator.fingerprint_spec(argv)
        # ZCode operations key on an explicit operation_ref rather than the
        # argv digest so distinct tasks over the same fixed argv differ.
        return ExecutionFingerprintSpec(
            project_id=base.project_id,
            job_id=base.job_id,
            work_order_ref=base.work_order_ref,
            backend_id=base.backend_id,
            repo_root=base.repo_root,
            branch=base.branch,
            head_before=base.head_before,
            operation_ref=operation_ref,
            runtime_profile_ref=base.runtime_profile_ref,
            target_argv=argv,
        )

    # -- the one public run ---------------------------------------

    def run(
        self,
        *,
        prompt: str,
        workspace: str,
        operation_ref: str,
        execution_id: str,
        run_dir_ref: str,
        task_packet_sha256: str,
        timeout_seconds: int = 300,
        on_record_observed: Callable[[object], None] | None = None,
    ) -> ZCodeRunResult:
        argv = self.argv()
        argv_sha = target_argv_sha256(argv)

        # selection double-check — first at preparation
        selection = self._selection_source.resolved_selection()
        preparation_digest = _selection_digest(selection)

        # launch seam — second check immediately before spawn
        selection_at_seam = self._selection_source.resolved_selection()
        seam_digest = _selection_digest(selection_at_seam)
        if seam_digest != preparation_digest:
            raise ZCodeSelectionDriftError()

        # cross-object identity facts the caller must have bound already
        if not isinstance(task_packet_sha256, str) or len(task_packet_sha256) != 64:
            raise ValueError("task_packet_sha256 is invalid")

        environment = {"ELECTRON_RUN_AS_NODE": "1"}
        transport = self._spawn_transport_factory(
            argv=argv,
            environment=environment,
            execution_id=execution_id,
            run_dir=run_dir_ref,
        )

        # identity BEFORE prompt: persist + re-parse the bounded artifact
        identity = ZCodeChildIdentity(
            child_pid=getattr(transport, "child_pid", 0) or 1,
            child_created_epoch_ms=getattr(transport, "child_created_epoch_ms", 1) or 1,
            executable=self._executable,
            parent_pid=getattr(transport, "parent_pid", 1) or 1,
            target_argv_sha256=argv_sha,
            execution_id=execution_id,
        )
        identity_path = f"{run_dir_ref}/child.identity.json"
        self._filesystem.write_atomic(identity_path, serialize_child_identity_document(identity))
        parsed = parse_child_identity_document(json.loads(self._filesystem.read_text(identity_path)))
        if not parsed.matches(identity):
            return self._unknown(execution_id, run_dir_ref, argv, "ZCODE_IDENTITY_WRITE_FAILED")

        driver = ZCodeProtocolDriver(
            transport, max_response_bytes=self._max_response_bytes
        )
        stderr_notes: list[str] = []
        try:
            turn = driver.run_turn(
                prompt,
                workspace=workspace,
                deadline_seconds=float(timeout_seconds),
            )
        except ZCodeProtocolError as exc:
            self._append_stderr(run_dir_ref, stderr_notes, exc.code)
            return self._unknown(
                execution_id, run_dir_ref, argv, f"ZCODE_{exc.code}", turn=None
            )

        # ordering: stdout first, then stderr, then atomic report, then result
        self._filesystem.write_bytes_file(
            f"{run_dir_ref}/stdout.log", turn.response_text.encode("utf-8")
        )
        self._append_stderr(run_dir_ref, stderr_notes, "TURN_COMPLETED")
        report = {
            "schema": "zcode-report/1",
            "execution_id": execution_id,
            "task_packet_sha256": task_packet_sha256,
            "selection_sha256": seam_digest,
            "response_bytes": turn.bytes_received,
            "session_id": turn.session_id,
        }
        self._filesystem.write_atomic(
            f"{run_dir_ref}/report.json", json.dumps(report, sort_keys=True, separators=(",", ":"))
        )

        # normal shutdown: stdin EOF + bounded natural-exit wait, no kill
        exit_code = transport.close_stdin_and_wait(exit_wait_seconds=30)
        if exit_code is None:
            return self._unknown(
                execution_id, run_dir_ref, argv, "ZCODE_EXIT_PENDING", turn=turn, report=report
            )

        result = {
            "schema_version": 1,
            "execution_id": execution_id,
            "exit_code": exit_code,
            "response_sha256": _sha256_hex(turn.response_text.encode("utf-8")),
        }
        self._filesystem.write_atomic(
            f"{run_dir_ref}/result.json",
            json.dumps(result, sort_keys=True, separators=(",", ":")),
        )
        return ZCodeRunResult(
            native=NativeCommandResult(
                executable=argv[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
                argument_count=len(argv),
                exit_code=exit_code,
                timed_out=False,
                stdout=turn.response_text,
                stderr="\n".join(stderr_notes),
                stdout_sha256=result["response_sha256"],
                stderr_sha256=_sha256_hex("\n".join(stderr_notes).encode("utf-8")),
                stdout_truncated=False,
                stderr_truncated=False,
            ),
            report=report,
            recovery_required=False,
        )

    def _append_stderr(self, run_dir_ref: str, notes: list[str], code: str) -> None:
        notes.append(code)
        self._filesystem.append_text(f"{run_dir_ref}/stderr.log", code + "\n")

    def _unknown(
        self,
        execution_id: str,
        run_dir_ref: str,
        argv: tuple[str, ...],
        code: str,
        *,
        turn=None,
        report: dict | None = None,
    ) -> ZCodeRunResult:
        """UNKNOWN/EXIT_PENDING: report may record typed unknown state; the
        standard result.json is NEVER fabricated."""
        unknown_report = report or {
            "schema": "zcode-report/1",
            "execution_id": execution_id,
            "state": "UNKNOWN",
            "error_code": code,
        }
        if report is None:
            self._filesystem.write_atomic(
                f"{run_dir_ref}/report.json",
                json.dumps(unknown_report, sort_keys=True, separators=(",", ":")),
            )
        return ZCodeRunResult(
            native=NativeCommandResult(
                executable=argv[0].rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
                argument_count=len(argv),
                exit_code=None,
                timed_out=False,
                stdout="",
                stderr=code,
                stdout_sha256=_sha256_hex(b""),
                stderr_sha256=_sha256_hex(code.encode("utf-8")),
                stdout_truncated=False,
                stderr_truncated=False,
            ),
            report=unknown_report,
            recovery_required=True,
            error_code=code,
        )


def _sha256_hex(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()
