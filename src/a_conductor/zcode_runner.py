"""WO-P1-158 Phase D — SupervisedZCodeRunner (durable canonical integration).

ZCode app-server execution over the ONE canonical supervised lifecycle:

- ``SupervisedZCodeRunner`` builds a ``SupervisedRunRequest`` and delegates
  the durable lifecycle — fingerprint, ``DuplicateExecutionGuard``, execution
  record creation, launch, poll/timeout, collect/version CAS — to
  ``SupervisedRunCoordinator.run``. The high-level runner never spawns a
  transport directly and owns no second store/guard/poll authority.
- ``ZCodeBackendAdapter`` implements the ``SupervisedLauncher`` shape: its
  ``launch`` performs the bounded ZCode turn (repository-owned transport
  seam → fail-closed child identity → authorized selection → protocol turn
  → artifacts → EOF-only shutdown) and stores the terminal outcome;
  ``inspect``/``collect`` serve that outcome through the coordinator's
  canonical polling/collect path.
- ``result.json`` is the canonical six-key ``SupervisedChildResult``
  (schema_version, execution_id, child_pid, exit_code, started_at,
  finished_at) written ONLY on a real terminal child exit. The final
  response stays in ``stdout_ref``; redacted diagnostics in ``stderr_ref``;
  strict protocol metadata in the configured ``report_ref``. UNKNOWN /
  EXIT_PENDING never fabricates a result.
- Task authority: a verified ``TaskPacketFile`` (path/size/hash) — raw
  caller prompt strings are rejected; the packet is re-hashed immediately
  before the protocol send (TOCTOU closed).
- Selection authorization: the resolved runtime selection must match the
  accepted provider-model ``HarnessRuntimeBinding`` and authorized endpoint
  (not merely be stable), checked at preparation AND again at the launch
  seam; drift or unauthorized selection fails closed before any prompt.
- Credentials: resolved only through the accepted secret-reference
  authority at the execution boundary; the value passes only through the
  closed transport seam into process memory — never persisted, printed, or
  hashed into identity. No ZCode-config credential fallback exists here.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Callable, Protocol

from .claude_code_harness import TaskPacketFile
from .execution_record import ExecutionProcessState
from .provider_configuration import (
    HarnessRuntimeBinding,
    runtime_selection_sha256,
)
from .supervised_child import SupervisedChildResult
from .supervised_execution import (
    SupervisedCollectOutcome,
    SupervisedExecutionError,
    SupervisedInspection,
    SupervisedInspectionState,
    SupervisedLaunchOutcome,
    SupervisedLaunchPlan,
)
from .supervised_run_coordinator import (
    SupervisedBackendPolicy,
    SupervisedExecutionFingerprintStore,
    SupervisedLauncher,
    SupervisedRunCoordinator,
    SupervisedRunIdentity,
)
from .zcode_protocol import (
    ZCODE_MAX_RESPONSE_BYTES,
    ZCodeProtocolDriver,
    ZCodeProtocolError,
)
from .zcode_supervised_helper import (
    ZCodeChildIdentity,
    parse_child_identity_document,
    serialize_child_identity_document,
    target_argv_sha256,
    validate_app_server_argv,
    validate_output_budget,
)


ZCODE_BACKEND_ID = "zcode-app-server"
_RESULT_SCHEMA_VERSION = 1
_CODE_RE = re.compile(r"[A-Z0-9_]{3,64}")
_MAX_PACKET_BYTES = 262_144


class ZCodeRunError(SupervisedExecutionError):
    """Bounded typed failure; code-only (no secret/prompt material).

    Subclasses the generic supervised error so the shared coordinator's
    EXISTING catch maps ZCode backend failures into the durable supervised
    contract — no ZCode-specific catches are added anywhere else.
    """

    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not _CODE_RE.fullmatch(code):
            raise ValueError("zcode run error code is invalid")
        super().__init__(code, recovery_required=True)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iso_utc(epoch: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


# ---------------- verified task authority ----------------

@dataclass(frozen=True, slots=True)
class ZCodeTaskPacketIdentity:
    """The task packet is re-read, size-bounded, and re-hashed at intake.

    The authoritative confined path + expected SHA are retained so the
    final pre-send check re-reads the REAL file — never cached content.
    """

    task_contract_ref: str
    packet_sha256: str
    content: str
    path: str = ""
    trusted_root: str = ""

    @classmethod
    def from_task_packet_file(
        cls, packet: TaskPacketFile, *, max_packet_bytes: int = _MAX_PACKET_BYTES,
        trusted_root: str | None = None,
    ) -> "ZCodeTaskPacketIdentity":
        from pathlib import Path

        if not isinstance(packet, TaskPacketFile):
            raise ValueError("packet must be a TaskPacketFile")
        path = Path(packet.path)
        if trusted_root is not None:
            root = Path(trusted_root).expanduser().resolve(strict=False)
            try:
                resolved = path.expanduser().resolve(strict=False)
                resolved.relative_to(root)
            except ValueError as exc:
                raise ZCodeRunError("ZCODE_TASK_PACKET_OUTSIDE_TRUSTED_ROOT") from exc
            path = resolved
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE") from exc
        if len(raw) > max_packet_bytes:
            raise ZCodeRunError("ZCODE_TASK_PACKET_TOO_LARGE")
        digest = _sha256_hex(raw)
        if digest.casefold() != packet.sha256.casefold():
            raise ZCodeRunError("ZCODE_TASK_PACKET_HASH_MISMATCH")
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE") from exc
        return cls(
            task_contract_ref=packet.task_contract_ref,
            packet_sha256=digest,
            content=content,
            path=str(path),
            trusted_root=str(trusted_root) if trusted_root is not None else "",
        )

    def verify_unchanged(
        self, *, max_packet_bytes: int = _MAX_PACKET_BYTES
    ) -> str:
        """Final pre-send TOCTOU check: re-read the REAL confined file.

        The bytes that pass this check — and only those bytes — become the
        protocol input. Never trusts cached ``content``.
        """
        from pathlib import Path

        if not self.path:
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE")
        path = Path(self.path).expanduser().resolve(strict=False)
        if self.trusted_root:
            root = Path(self.trusted_root).expanduser().resolve(strict=False)
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise ZCodeRunError("ZCODE_TASK_PACKET_OUTSIDE_TRUSTED_ROOT") from exc
        if not path.is_file():
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE") from exc
        if len(raw) > max_packet_bytes:
            raise ZCodeRunError("ZCODE_TASK_PACKET_TOO_LARGE")
        if _sha256_hex(raw).casefold() != self.packet_sha256.casefold():
            raise ZCodeRunError("ZCODE_TASK_PACKET_TOCTOU")
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ZCodeRunError("ZCODE_TASK_PACKET_UNREADABLE") from exc

    def canonical_operation_ref(self) -> str:
        """Deterministic operation identity derived from trusted task identity:
        task_contract_ref + verified packet SHA — callers cannot choose it."""
        return f"zcode:{self.task_contract_ref}:{self.packet_sha256[:16]}"


# ---------------- seams (repository-owned implementations) ----------------

class ZCodeSelectionSource(Protocol):
    """Trusted Conductor-side provider of the authorized runtime selection."""

    def resolved_selection(self) -> dict: ...


class ZCodeSecretResolver(Protocol):
    """Accepted secret-reference authority at the execution boundary."""

    def resolve(self, secret_ref: str) -> str: ...


class ZCodeTransportFactory(Protocol):
    """Repository-owned seam: starts the app-server child and returns a
    transport carrying REAL process metadata. The resolved credential is
    supplied through the closed ``credential`` channel into the accepted
    ephemeral runtime environment — process memory only, never persisted."""

    def open_transport(
        self,
        *,
        argv: tuple[str, ...],
        environment: dict[str, str],
        credential: "ZCodeEphemeralCredential",
        execution_id: str,
        run_dir_ref: str,
    ) -> object: ...


@dataclass(frozen=True, slots=True, repr=False)
class ZCodeEphemeralCredential:
    """Typed ephemeral credential envelope: memory-only delivery channel.

    The value exists only inside this object for the duration of one launch.
    ``repr`` is disabled so debug output can never print the secret; the
    envelope exposes only the delivery-target key. The factory copies the
    value into the child environment (or another accepted ephemeral channel)
    and the envelope is dropped immediately after.
    """

    delivery_key: str  # environment variable name the child expects

    _value: str = ""

    def __post_init__(self) -> None:
        import re as _re

        if not isinstance(self.delivery_key, str) or not _re.fullmatch(
            r"[A-Z][A-Z0-9_]{0,63}", self.delivery_key
        ):
            raise ValueError("delivery_key is invalid")
        if not isinstance(self._value, str) or not self._value:
            raise ValueError("credential value is required")

    @property
    def environment_entry(self) -> tuple[str, str]:
        return (self.delivery_key, self._value)


class ZCodeFilesystem(Protocol):
    """Run-dir-confined artifact IO (relative paths only)."""

    def write_atomic(self, relative_path: str, text: str) -> None: ...
    def read_text(self, relative_path: str) -> str: ...
    def append_text(self, relative_path: str, text: str) -> None: ...
    def write_bytes_file(self, relative_path: str, data: bytes) -> None: ...


# ---------------- durable-metadata policy ----------------

def zcode_backend_policy(*, operation_ref: str) -> SupervisedBackendPolicy:
    """ZCode backend policy: operation identity from the task contract."""

    def _op(argv: tuple[str, ...]) -> str:
        return operation_ref

    def _summary(argv: tuple[str, ...]) -> str:
        return f"zcode app-server turn ({operation_ref})"

    def _report(run_rel: str) -> str:
        return f"{run_rel}/report.json"

    return SupervisedBackendPolicy(
        derive_operation_ref=_op,
        command_summary=_summary,
        agent_ref="agent:zcode-app-server",
        report_ref=_report,
    )


# ---------------- selection authorization (single authority) ----------------

def authorize_zcode_selection(
    *,
    selection_source: ZCodeSelectionSource,
    expected_binding: HarnessRuntimeBinding,
    expected_base_url: str,
    phase: str,
) -> str:
    """Resolve + authorize the runtime selection against the accepted
    provider-model binding and endpoint. Stable-but-wrong selections fail
    closed ``ZCODE_SELECTION_UNAUTHORIZED``. Shared by every launcher so the
    preparation and launch-seam checks can never drift apart."""
    selection = selection_source.resolved_selection()
    binding = selection.get("runtime_binding")
    if not isinstance(binding, HarnessRuntimeBinding):
        try:
            binding = HarnessRuntimeBinding.from_dict(binding)
        except (ValueError, TypeError) as exc:
            raise ZCodeRunError(f"ZCODE_SELECTION_{phase}_MALFORMED") from exc
    base_url = selection.get("runtime_base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ZCodeRunError(f"ZCODE_SELECTION_{phase}_MALFORMED")
    if (
        binding.harness_strategy is not expected_binding.harness_strategy
        or binding.runtime_provider_ref != expected_binding.runtime_provider_ref
        or binding.runtime_model_ref != expected_binding.runtime_model_ref
        or base_url.strip() != expected_base_url.strip()
    ):
        raise ZCodeRunError("ZCODE_SELECTION_UNAUTHORIZED")
    return runtime_selection_sha256(
        runtime_binding=binding,
        runtime_base_url=base_url,
        runtime_source_enabled=selection.get("runtime_source_enabled"),
    )


# ---------------- backend adapter (SupervisedLauncher shape) ----------------

class ZCodeBackendAdapter:
    """Bridges the coordinator lifecycle onto the bounded ZCode protocol turn.

    ``launch`` executes the whole bounded turn synchronously (identity →
    authorized selection → protocol → artifacts → EOF-only shutdown) and
    stores the terminal outcome; ``inspect``/``collect`` serve it through
    the coordinator's canonical polling and version-CAS collect path.
    """

    def __init__(
        self,
        *,
        transport_factory: ZCodeTransportFactory,
        filesystem: ZCodeFilesystem,
        execution_store: "SupervisedExecutionFingerprintStore | None" = None,
        selection_source: ZCodeSelectionSource,
        expected_binding: HarnessRuntimeBinding,
        expected_base_url: str,
        secret_resolver: ZCodeSecretResolver,
        secret_reference: str,
        packet: ZCodeTaskPacketIdentity,
        workspace: str,
        executable: str,
        bundle_js: str,
        max_response_bytes: int = ZCODE_MAX_RESPONSE_BYTES,
        deadline_seconds: float = 300.0,
        credential_delivery_key: str = "ANTHROPIC_API_KEY",
        child_observer=None,
    ) -> None:
        self._transport_factory = transport_factory
        self._fs = filesystem
        self._execution_store = execution_store
        self._child_observer = child_observer
        self._selection_source = selection_source
        self._expected_binding = expected_binding
        self._expected_base_url = expected_base_url
        self._secret_resolver = secret_resolver
        if not isinstance(secret_reference, str) or not secret_reference.startswith("secret-ref:"):
            raise ValueError("secret_reference must use the accepted secret-ref authority")
        self._secret_reference = secret_reference
        # validate the delivery-key grammar eagerly (bounded env-var name)
        ZCodeEphemeralCredential(
            delivery_key=credential_delivery_key, _value="probe-non-empty"
        )
        self._credential_delivery_key = credential_delivery_key
        self._packet = packet
        self._workspace = workspace
        self._executable = executable
        self._bundle_js = bundle_js
        self._max_response_bytes = validate_output_budget(max_response_bytes)
        if deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        self._deadline = float(deadline_seconds)
        self._outcomes: dict[str, SupervisedCollectOutcome] = {}

    # -- selection authorization ----------------------------------------

    def authorized_selection_digest(self, phase: str) -> str:
        return authorize_zcode_selection(
            selection_source=self._selection_source,
            expected_binding=self._expected_binding,
            expected_base_url=self._expected_base_url,
            phase=phase,
        )

    # -- SupervisedLauncher protocol --------------------------------------

    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome:
        record = plan.record
        run_rel = record.run_dir_ref
        execution_id = record.execution_id
        # canonical durable-record persistence (mirrors the native supervisor)
        if self._execution_store is not None:
            record = self._execution_store.create(record)
        argv = plan.target_argv
        if not validate_app_server_argv(
            argv, executable=self._executable, bundle_js=self._bundle_js
        ):
            raise ZCodeRunError("ZCODE_ARGV_GRAMMAR_INVALID")

        # launch-seam selection authorization (2nd check)
        seam_digest = self.authorized_selection_digest("SEAM")

        # credential: accepted secret-ref authority → process memory only
        try:
            secret_value = self._secret_resolver.resolve(self._secret_reference)
        except Exception as exc:
            raise ZCodeRunError("ZCODE_SECRET_RESOLUTION_FAILED") from exc
        if not isinstance(secret_value, str) or not secret_value:
            raise ZCodeRunError("ZCODE_SECRET_RESOLUTION_FAILED")
        # typed ephemeral envelope: memory-only channel to the repository-
        # owned transport factory. Non-serializable by construction; the
        # value is dropped when this method returns.
        try:
            credential = ZCodeEphemeralCredential(
                delivery_key=self._credential_delivery_key, _value=secret_value
            )
        except ValueError as exc:
            raise ZCodeRunError("ZCODE_SECRET_RESOLUTION_FAILED") from exc
        environment = {"ELECTRON_RUN_AS_NODE": "1"}
        # the closed factory seam receives ONLY the base environment plus the
        # typed credential envelope; the secret never enters argv, the
        # durable record, artifacts, or identity, and never replaces a
        # ZCode-config credential (no fallback path exists in this module)
        try:
            transport = self._transport_factory.open_transport(
                argv=argv,
                environment=environment,
                credential=credential,
                execution_id=execution_id,
                run_dir_ref=run_rel,
            )
        finally:
            credential = None
            secret_value = ""

        # child identity: REAL process metadata or fail closed — never 1s
        child_pid = getattr(transport, "child_pid", None)
        created = getattr(transport, "child_created_epoch_ms", None)
        parent_pid = getattr(transport, "parent_pid", None)
        for name, value in (
            ("child_pid", child_pid),
            ("child_created_epoch_ms", created),
            ("parent_pid", parent_pid),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
            ):
                raise ZCodeRunError("ZCODE_CHILD_IDENTITY_UNAVAILABLE")
        identity = ZCodeChildIdentity(
            child_pid=child_pid,
            child_created_epoch_ms=created,
            executable=self._executable,
            parent_pid=parent_pid,
            target_argv_sha256=target_argv_sha256(argv),
            execution_id=execution_id,
        )
        # identity BEFORE prompt: durable write → re-parse → exact match
        identity_doc = f"{run_rel}/child.identity.json"
        self._fs.write_atomic(identity_doc, serialize_child_identity_document(identity))
        try:
            parsed = parse_child_identity_document(json.loads(self._fs.read_text(identity_doc)))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ZCodeRunError("ZCODE_IDENTITY_WRITE_FAILED") from exc
        if not parsed.matches(identity):
            raise ZCodeRunError("ZCODE_IDENTITY_WRITE_FAILED")

        # task packet final pre-send TOCTOU check: re-read the REAL confined
        # file (path/symlink/size/hash/UTF-8). Only the exact verified bytes
        # that pass here become the protocol input — never cached content.
        verified_prompt = self._packet.verify_unchanged()

        started = time.time()
        driver = ZCodeProtocolDriver(transport, max_response_bytes=self._max_response_bytes)
        stderr_codes: list[str] = []
        report: dict | None = None
        turn = None
        error_code: str | None = None
        try:
            turn = driver.run_turn(
                verified_prompt,
                workspace=self._workspace,
                deadline_seconds=self._deadline,
            )
        except ZCodeProtocolError as exc:
            stderr_codes.append(exc.code)
            error_code = f"ZCODE_{exc.code}"
        self._fs.write_bytes_file(f"{run_rel}/stderr.log", ("\n".join(stderr_codes) + "\n").encode("utf-8"))

        if turn is not None:
            self._fs.write_bytes_file(f"{run_rel}/stdout.log", turn.response_text.encode("utf-8"))
            report = {
                "schema": "zcode-report/1",
                "execution_id": execution_id,
                "task_contract_ref": self._packet.task_contract_ref,
                "task_packet_sha256": self._packet.packet_sha256,
                "selection_sha256": seam_digest,
                "response_bytes": turn.bytes_received,
                "response_sha256": _sha256_hex(turn.response_text.encode("utf-8")),
                "session_id": turn.session_id,
            }
            self._fs.write_atomic(
                f"{run_rel}/report.json",
                json.dumps(report, sort_keys=True, separators=(",", ":")),
            )

        # normal shutdown: stdin EOF + bounded natural-exit wait; no kill
        exit_code = transport.close_stdin_and_wait(exit_wait_seconds=30)
        finished = time.time()
        if exit_code is None and report is not None:
            # protocol succeeded but the child did not terminate within the
            # bounded natural-exit wait: the report must record that pending
            # exit state so no reader mistakes artifacts for an accepted run
            report = {**report, "exit_state": "EXIT_PENDING"}
            self._fs.write_atomic(
                f"{run_rel}/report.json",
                json.dumps(report, sort_keys=True, separators=(",", ":")),
            )
        result: SupervisedChildResult | None = None
        if turn is not None and isinstance(exit_code, int) and not isinstance(exit_code, bool):
            # canonical six-key supervised result on a REAL terminal exit
            result = SupervisedChildResult(
                schema_version=_RESULT_SCHEMA_VERSION,
                execution_id=execution_id,
                child_pid=identity.child_pid,
                exit_code=exit_code,
                started_at=_iso_utc(started),
                finished_at=_iso_utc(finished),
            )
            self._fs.write_atomic(
                f"{run_rel}/result.json",
                json.dumps(
                    {
                        "schema_version": result.schema_version,
                        "execution_id": result.execution_id,
                        "child_pid": result.child_pid,
                        "exit_code": result.exit_code,
                        "started_at": result.started_at,
                        "finished_at": result.finished_at,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        if result is None and report is None:
            # typed unknown state; NEVER fabricate result.json
            self._fs.write_atomic(
                f"{run_rel}/report.json",
                json.dumps(
                    {
                        "schema": "zcode-report/1",
                        "execution_id": execution_id,
                        "state": "UNKNOWN",
                        "error_code": error_code or "ZCODE_EXIT_PENDING",
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )

        self._outcomes[execution_id] = SupervisedCollectOutcome(
            record=record,
            result=result,
            recovery_required=result is None,
            error_code=None if result is not None else (error_code or "ZCODE_EXIT_PENDING"),
        )
        if self._execution_store is not None and result is not None:
            try:
                self._execution_store.set_execution_state(
                    execution_id,
                    ExecutionProcessState.SUCCEEDED,
                    expected_version=record.version,
                    evidence_ref="zcode:natural-exit",
                )
            except Exception:
                # collect/version-CAS remains authoritative in the coordinator
                pass
        return SupervisedLaunchOutcome(
            record=record,
            supervisor_pid=None,
            child_pid=identity.child_pid,
            recovery_required=False,
        )

    def inspect(self, execution_id: str) -> SupervisedInspection:
        """Durable-first inspect: no process-local map is authoritative.

        An execution that exists durably but not in this process (restart /
        cross-process attach) resolves from the durable store + artifacts:
        a canonical result.json means RESULT_AVAILABLE; otherwise the child
        is re-observed via the recovery consumer semantics (evidence only).
        """
        try:
            outcome = self._outcomes.get(execution_id) or self._load_durable_outcome(execution_id)
        except ZCodeRunError:
            raise
        except Exception as exc:  # map backend errors at the backend boundary
            raise SupervisedExecutionError("ZCODE_INSPECT_FAILED") from exc
        if outcome is None:
            # distinguish durable-exists vs truly unknown via the store
            try:
                record = self._execution_store.get(execution_id) if self._execution_store else None
            except Exception:
                # durable row absent (store raises for missing) => unknown
                raise ZCodeRunError("ZCODE_EXECUTION_UNKNOWN")
            if record is None:
                raise ZCodeRunError("ZCODE_EXECUTION_UNKNOWN")
            return SupervisedInspection(
                execution_id=execution_id,
                state=SupervisedInspectionState.SUPERVISOR_EXITED_RESULT_MISSING,
                supervisor_pid=None,
                result_available=False,
                recovery_required=True,
            )
        return SupervisedInspection(
            execution_id=execution_id,
            state=SupervisedInspectionState.RESULT_AVAILABLE,
            supervisor_pid=None,
            result_available=True,
            recovery_required=False,
        )

    def _load_durable_outcome(self, execution_id: str) -> SupervisedCollectOutcome | None:
        """Reconstruct the collect outcome from DURABLE artifacts only.

        Requires a canonical six-key result.json for a completed outcome;
        no in-memory state is required for correctness after a restart.
        """
        from pathlib import Path

        if self._execution_store is None:
            return self._outcomes.get(execution_id)
        try:
            record = self._execution_store.get(execution_id)
        except Exception:
            return None  # no durable row => unknown, caller raises typed
        root = Path(record.repo_root)
        result_path = root / record.result_ref
        if not result_path.is_file():
            return None
        document = json.loads(result_path.read_text(encoding="utf-8"))
        result = SupervisedChildResult(**document)
        return SupervisedCollectOutcome(
            record=record, result=result, recovery_required=False
        )

    def recover(self, execution_id: str):
        """Production recovery composition: reconcile the durable
        child.identity.json evidence against live process truth under the
        existing recovery authority. Evidence only — never kills/replays."""
        from .zcode_child_recovery import (
            ZCodeChildRecoveryKind,
            read_child_identity_from_run_dir,
            reconcile_zcode_child,
        )

        if self._execution_store is None or self._child_observer is None:
            return ZCodeChildRecoveryKind.RECOVERY_REQUIRED
        record = self._execution_store.get(execution_id)
        run_dir = record.run_dir_ref
        document = read_child_identity_from_run_dir(
            __import__("pathlib").Path(record.repo_root) / run_dir
        )
        return reconcile_zcode_child(document, observer=self._child_observer).kind

    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome:
        """Version-honoring collect: CAS against the durable store version.

        An expected_version that does not match the durable record's current
        version fails closed — no silent collect, no blind replay.
        """
        try:
            outcome = self._outcomes.get(execution_id) or self._load_durable_outcome(execution_id)
        except ZCodeRunError:
            raise
        except Exception as exc:  # map backend errors at the backend boundary
            raise SupervisedExecutionError("ZCODE_COLLECT_FAILED") from exc
        if outcome is None:
            raise ZCodeRunError("ZCODE_EXECUTION_UNKNOWN")
        if self._execution_store is not None:
            try:
                record = self._execution_store.get(execution_id)
            except Exception:
                raise ZCodeRunError("ZCODE_EXECUTION_UNKNOWN")
            if record.version != expected_version:
                raise SupervisedExecutionError("ZCODE_VERSION_CONFLICT")
        return outcome


# ---------------- production service lifecycle launcher ----------------

class ZCodeServiceLifecycleLauncher:
    """THE production ZCode launcher: composes the REAL
    ``SupervisedExecutionService`` with the CLOSED
    ``SupervisedHelperKind.ZCODE_APP_SERVER_V1`` helper kind.

    ``launch`` performs the launch-seam authorization (selection + argv
    grammar + secret-ref resolution), then injects the accepted bounded
    runtime metadata + credential into the helper's environment through the
    service plan and delegates process authority entirely to the service —
    the specialized helper subprocess is spawned by the repository-owned
    owned-process controller, never by this class. The credential exists in
    supervisor process memory only between resolution and the service
    ``launch`` call; it is never persisted, printed, or hashed.
    """

    def __init__(
        self,
        *,
        service,
        selection_source: ZCodeSelectionSource,
        expected_binding: HarnessRuntimeBinding,
        expected_base_url: str,
        secret_resolver: ZCodeSecretResolver,
        secret_reference: str,
        packet: ZCodeTaskPacketIdentity,
        executable: str,
        bundle_js: str,
        max_response_bytes: int = ZCODE_MAX_RESPONSE_BYTES,
        deadline_seconds: float = 300.0,
        max_packet_bytes: int = _MAX_PACKET_BYTES,
        credential_delivery_key: str = "ANTHROPIC_API_KEY",
    ) -> None:
        for method_name in ("launch", "inspect", "collect"):
            if not callable(getattr(service, method_name, None)):
                raise ValueError(f"service must provide {method_name}")
        self._service = service
        self._selection_source = selection_source
        self._expected_binding = expected_binding
        self._expected_base_url = expected_base_url
        self._secret_resolver = secret_resolver
        if not isinstance(secret_reference, str) or not secret_reference.startswith("secret-ref:"):
            raise ValueError("secret_reference must use the accepted secret-ref authority")
        self._secret_reference = secret_reference
        if not isinstance(packet, ZCodeTaskPacketIdentity):
            raise ValueError("packet must be a ZCodeTaskPacketIdentity")
        self._packet = packet
        self._executable = executable
        self._bundle_js = bundle_js
        self._max_response_bytes = validate_output_budget(max_response_bytes)
        if deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive")
        self._deadline = float(deadline_seconds)
        self._max_packet_bytes = int(max_packet_bytes)
        # validate the delivery-key grammar eagerly (must also be within the
        # owned-process environment-override allowlist or launch fails closed)
        ZCodeEphemeralCredential(
            delivery_key=credential_delivery_key, _value="probe-non-empty"
        )
        self._credential_delivery_key = credential_delivery_key

    def authorized_selection_digest(self, phase: str) -> str:
        return authorize_zcode_selection(
            selection_source=self._selection_source,
            expected_binding=self._expected_binding,
            expected_base_url=self._expected_base_url,
            phase=phase,
        )

    def _helper_environment(self) -> tuple[tuple[str, str], ...]:
        """Accepted non-persistent runtime channel for the specialized helper.

        Bounded verified task-packet metadata + the resolved credential. The
        prompt bytes themselves never ride this channel — the helper re-opens
        and re-verifies the real packet file at send time."""
        try:
            secret_value = self._secret_resolver.resolve(self._secret_reference)
        except Exception as exc:
            raise ZCodeRunError("ZCODE_SECRET_RESOLUTION_FAILED") from exc
        if not isinstance(secret_value, str) or not secret_value:
            raise ZCodeRunError("ZCODE_SECRET_RESOLUTION_FAILED")
        try:
            credential = ZCodeEphemeralCredential(
                delivery_key=self._credential_delivery_key, _value=secret_value
            )
            delivery_key, delivery_value = credential.environment_entry
            return (
                ("ZCODE_TASK_PACKET_PATH", self._packet.path),
                ("ZCODE_TASK_PACKET_SHA256", self._packet.packet_sha256),
                ("ZCODE_TASK_PACKET_TRUSTED_ROOT", self._packet.trusted_root),
                ("ZCODE_TASK_PACKET_MAX_BYTES", str(self._max_packet_bytes)),
                ("ZCODE_OUTPUT_BUDGET", str(self._max_response_bytes)),
                ("ZCODE_DEADLINE_SECONDS", repr(self._deadline)),
                ("ZCODE_CREDENTIAL_DELIVERY_KEY", delivery_key),
                (delivery_key, delivery_value),
            )
        finally:
            # drop the in-memory credential references when this frame exits
            credential = None
            secret_value = ""

    # -- SupervisedLauncher protocol --------------------------------------

    def launch(self, plan: SupervisedLaunchPlan) -> SupervisedLaunchOutcome:
        from dataclasses import replace as _dc_replace
        from .supervised_execution import SupervisedHelperKind

        argv = plan.target_argv
        if not validate_app_server_argv(
            argv, executable=self._executable, bundle_js=self._bundle_js
        ):
            raise ZCodeRunError("ZCODE_ARGV_GRAMMAR_INVALID")
        # launch-seam selection authorization (2nd check) — before any spawn
        self.authorized_selection_digest("SEAM")
        helper_plan = _dc_replace(
            plan,
            helper_kind=SupervisedHelperKind.ZCODE_APP_SERVER_V1,
            environment_overrides=self._helper_environment(),
        )
        return self._service.launch(helper_plan)

    def inspect(self, execution_id: str) -> SupervisedInspection:
        return self._service.inspect(execution_id)

    def collect(self, execution_id: str, *, expected_version: int) -> SupervisedCollectOutcome:
        return self._service.collect(execution_id, expected_version=expected_version)


# ---------------- the high-level runner (no direct lifecycle) ----------------

class SupervisedZCodeRunner:
    """One ZCode app-server turn through the canonical supervised lifecycle."""

    def __init__(
        self,
        *,
        execution_store: SupervisedExecutionFingerprintStore,
        identity: SupervisedRunIdentity,
        adapter: ZCodeBackendAdapter,
        executable: str,
        bundle_js: str,
        task_packet: ZCodeTaskPacketIdentity,
        poll_interval_seconds: float = 0.05,
        sleep_fn: Callable[[float], None] = time.sleep,
        clock_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        if identity.backend_id != ZCODE_BACKEND_ID:
            raise ValueError(f"identity.backend_id must be {ZCODE_BACKEND_ID}")
        if not isinstance(task_packet, ZCodeTaskPacketIdentity):
            raise ValueError("task_packet must be a ZCodeTaskPacketIdentity")
        self._executable = executable
        self._bundle_js = bundle_js
        self._adapter = adapter
        self._task_packet = task_packet

        def _coordinator_factory():
            # operation identity is task-derived; supplied per run()
            return None

        self._store = execution_store
        self._identity = identity
        self._poll = poll_interval_seconds
        self._sleep = sleep_fn
        self._clock = clock_fn

    def argv(self) -> tuple[str, ...]:
        argv = (self._executable, self._bundle_js, "app-server", "--stdio", "--surface", "desktop")
        if not validate_app_server_argv(argv, executable=self._executable, bundle_js=self._bundle_js):
            raise ValueError("ZCODE_ARGV_GRAMMAR_INVALID")
        return argv

    def run(self, *, operation_ref: str | None = None, timeout_seconds: int = 300) -> object:
        """Execute through the coordinator: dedup → record → launch → poll →
        collect/version-CAS. Returns the coordinator's native-style result
        mapping; the canonical ZCode artifacts live in the run dir.

        Operation identity is DERIVED from the verified task identity
        (task_contract_ref + packet SHA). A caller ``operation_ref`` is
        accepted only as a diagnostic label when it exactly matches the
        derived identity; it can never choose a different dedup identity.
        """
        derived = self._task_packet.canonical_operation_ref()
        if operation_ref is not None and operation_ref != derived:
            raise ValueError(
                "operation_ref must match the derived task identity: " + derived
            )
        coordinator = SupervisedRunCoordinator(
            execution_store=self._store,
            supervised=self._adapter,
            identity=self._identity,
            backend_policy=zcode_backend_policy(operation_ref=derived),
            poll_interval_seconds=self._poll,
            sleep_fn=self._sleep,
            clock_fn=self._clock,
            max_output_bytes=ZCODE_MAX_RESPONSE_BYTES,
        )
        # preparation-time selection authorization (1st check) — fail before
        # any durable record exists when the selection is wrong
        self._adapter.authorized_selection_digest("PREP")
        return coordinator.run(
            self.argv(),
            environment_overrides=(),
            timeout_seconds=timeout_seconds,
        )
