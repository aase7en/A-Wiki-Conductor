"""Production assembly for durable Claude jobs over supervised execution.

This module composes accepted AHA-4 seams only. It owns no lifecycle, process
runner, scheduler, retry loop, provider registry, durable store, or dedup logic.
"""

from __future__ import annotations

from typing import Callable, Sequence

from .claude_code_harness import ClaudeCodeHarnessAdapter, ClaudeCodeHarnessError
from .claude_code_job_backend import (
    ClaudeCodeJobBackend,
    ClaudeCodeOperationDefinition,
    ClaudeCodeProviderResolver,
    ClaudeCodeProviderState,
    provider_execution_authority_reason,
)
from .claude_code_supervised_runner import (
    EnvironmentReferenceResolver,
    build_supervised_claude_code_runner,
)
from .job_execution import JobExecutionContext


class ResolverBackedProviderExecutionAuthorityGuard:
    """Revalidate exact provider authority at secret and launch boundaries."""

    def __init__(
        self,
        *,
        provider_resolver: ClaudeCodeProviderResolver,
        definition: ClaudeCodeOperationDefinition,
        baseline: ClaudeCodeProviderState,
        clock: Callable[[], object],
    ) -> None:
        self._provider_resolver = provider_resolver
        self._definition = definition
        self._baseline = baseline
        self._clock = clock

    def check(self) -> str | None:
        try:
            current = self._provider_resolver.resolve(
                self._definition.dispatch.provider_id
            )
        except Exception:
            return "PROVIDER_AUTHORITY_CHECK_FAILED"
        if current is None:
            return "PROVIDER_CONFIGURATION_UNAVAILABLE"
        reason = provider_execution_authority_reason(
            self._definition, current, now=self._clock()
        )
        if reason is not None:
            return reason
        if (
            current.profile != self._baseline.profile
            or current.endpoint != self._baseline.endpoint
        ):
            return "PROVIDER_CONFIGURATION_DRIFT"
        return None


class SupervisedClaudeCodeAdapterFactory:
    """Build one supervised harness adapter from exact durable job identity."""

    def __init__(
        self,
        *,
        execution_store: object,
        supervised: object,
        reference_resolver: EnvironmentReferenceResolver,
        provider_resolver: ClaudeCodeProviderResolver,
        clock: Callable[[], object],
        require_provider_authority: bool = False,
        claude_executable: str = "claude",
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if not callable(getattr(reference_resolver, "resolve", None)):
            raise ValueError("reference_resolver must provide resolve")
        if not callable(getattr(provider_resolver, "resolve", None)):
            raise ValueError("provider_resolver must provide resolve")
        if not callable(clock):
            raise ValueError("clock must be callable")
        if not isinstance(require_provider_authority, bool):
            raise ValueError("require_provider_authority must be bool")
        if not isinstance(claude_executable, str) or not claude_executable.strip():
            raise ValueError("claude_executable must not be blank")
        if (
            not isinstance(poll_interval_seconds, (int, float))
            or isinstance(poll_interval_seconds, bool)
            or poll_interval_seconds <= 0
        ):
            raise ValueError("poll_interval_seconds must be > 0")
        self._execution_store = execution_store
        self._supervised = supervised
        self._reference_resolver = reference_resolver
        self._provider_resolver = provider_resolver
        self._clock = clock
        self._require_provider_authority = require_provider_authority
        self._claude_executable = claude_executable.strip()
        self._poll_interval_seconds = float(poll_interval_seconds)

    def build(
        self,
        definition: ClaudeCodeOperationDefinition,
        context: JobExecutionContext,
        state: ClaudeCodeProviderState,
    ) -> ClaudeCodeHarnessAdapter:
        if not isinstance(definition, ClaudeCodeOperationDefinition):
            raise ValueError("definition must be ClaudeCodeOperationDefinition")
        if not isinstance(context, JobExecutionContext):
            raise ValueError("context must be JobExecutionContext")
        if not isinstance(state, ClaudeCodeProviderState):
            raise ValueError("state must be ClaudeCodeProviderState")
        dispatch = definition.dispatch
        branch = dispatch.expected_branch
        if branch is None:
            raise ClaudeCodeHarnessError("HARNESS_BRANCH_REQUIRED")
        if self._require_provider_authority and definition.provider_requirement is None:
            raise ClaudeCodeHarnessError("HARNESS_PROVIDER_AUTHORITY_REQUIRED")
        authority_guard = None
        if definition.provider_security is not None:
            authority_guard = ResolverBackedProviderExecutionAuthorityGuard(
                provider_resolver=self._provider_resolver,
                definition=definition,
                baseline=state,
                clock=self._clock,
            )
        try:
            runner = build_supervised_claude_code_runner(
                project_root=dispatch.worktree_path,
                execution_store=self._execution_store,
                supervised=self._supervised,
                reference_resolver=self._reference_resolver,
                job_id=context.job_id,
                work_order_ref=context.work_order_ref,
                project_id=context.project_id,
                worker_id=context.worker_id,
                branch=branch,
                head_before=dispatch.expected_head,
                endpoint_ref=state.profile.endpoint_ref,
                credential_ref=state.profile.credential_ref,
                endpoint_url=state.endpoint.base_url,
                provider_requirement=definition.provider_requirement,
                claude_executable=self._claude_executable,
                poll_interval_seconds=self._poll_interval_seconds,
                authority_guard=authority_guard,
            )
        except ValueError as exc:
            raise ClaudeCodeHarnessError("HARNESS_ASSEMBLY_INVALID") from exc
        return ClaudeCodeHarnessAdapter(runner=runner)


def build_supervised_claude_job_backend(
    *,
    operations: Sequence[ClaudeCodeOperationDefinition],
    execution_store: object,
    supervised: object,
    reference_resolver: EnvironmentReferenceResolver,
    provider_resolver: ClaudeCodeProviderResolver,
    clock: Callable[[], object],
    require_provider_authority: bool = False,
    claude_executable: str = "claude",
    poll_interval_seconds: float = 0.05,
) -> ClaudeCodeJobBackend:
    """Assemble the durable Claude backend over the canonical supervisor."""
    factory = SupervisedClaudeCodeAdapterFactory(
        execution_store=execution_store,
        supervised=supervised,
        reference_resolver=reference_resolver,
        provider_resolver=provider_resolver,
        clock=clock,
        require_provider_authority=require_provider_authority,
        claude_executable=claude_executable,
        poll_interval_seconds=poll_interval_seconds,
    )
    return ClaudeCodeJobBackend(
        operations=operations,
        adapter_factory=factory,
        provider_resolver=provider_resolver,
        clock=clock,
        require_provider_authority=require_provider_authority,
    )
