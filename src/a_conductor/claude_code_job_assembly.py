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
)
from .claude_code_supervised_runner import (
    EnvironmentReferenceResolver,
    build_supervised_claude_code_runner,
)
from .job_execution import JobExecutionContext


class SupervisedClaudeCodeAdapterFactory:
    """Build one supervised harness adapter from exact durable job identity."""

    def __init__(
        self,
        *,
        execution_store: object,
        supervised: object,
        reference_resolver: EnvironmentReferenceResolver,
        claude_executable: str = "claude",
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if not callable(getattr(reference_resolver, "resolve", None)):
            raise ValueError("reference_resolver must provide resolve")
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
                claude_executable=self._claude_executable,
                poll_interval_seconds=self._poll_interval_seconds,
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
    claude_executable: str = "claude",
    poll_interval_seconds: float = 0.05,
) -> ClaudeCodeJobBackend:
    """Assemble the durable Claude backend over the canonical supervisor."""
    factory = SupervisedClaudeCodeAdapterFactory(
        execution_store=execution_store,
        supervised=supervised,
        reference_resolver=reference_resolver,
        claude_executable=claude_executable,
        poll_interval_seconds=poll_interval_seconds,
    )
    return ClaudeCodeJobBackend(
        operations=operations,
        adapter_factory=factory,
        provider_resolver=provider_resolver,
        clock=clock,
    )
