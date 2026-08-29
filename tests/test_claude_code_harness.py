from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from a_conductor.claude_code_harness import (
    ClaudeCodeHarnessAdapter,
    ClaudeCodeHarnessError,
    ClaudeCodeRunnerResult,
    HarnessDispatch,
    HarnessExecutionStatus,
    MutationIntent,
    TaskPacketFile,
)
from a_conductor.provider_configuration import (
    ActorCapabilityEvidence,
    EgressBoundary,
    HarnessStrategy,
    ProviderConfiguration,
    ProviderEndpointConfig,
    ProviderHealth,
    ProviderModelConfiguration,
    ProviderObservation,
    ProviderTrustClass,
    ProtocolFamily,
)

NOW = datetime(2026, 8, 28, 2, 30, tzinfo=timezone.utc)


def make_profile() -> ProviderConfiguration:
    return ProviderConfiguration(
        provider_id="provider-glm-shared",
        display_name="GLM Shared Provider",
        provider_type="cloud-proxy",
        protocol_family=ProtocolFamily.ANTHROPIC_MESSAGES,
        endpoint_ref="provider-config:glm-shared/base-url",
        credential_ref="secret-ref:provider/glm-shared/main",
        trust_class=ProviderTrustClass.TRUSTED_THIRD_PARTY,
        egress_boundary=EgressBoundary.EXTERNAL_THIRD_PARTY,
        harness_strategies=(HarnessStrategy.CLAUDE_CODE_CLI,),
        max_concurrency=1,
        models=(
            ProviderModelConfiguration(
                model_id="glm-5.3",
                display_name="GLM-5.3",
                actor_capabilities=(
                    ActorCapabilityEvidence(
                        capability="documentation",
                        evidence_level="DECLARED",
                        source="test",
                    ),
                ),
                supported_effort_levels=("DEFAULT", "HIGH", "MAX"),
            ),
        ),
        enabled=True,
    )


def make_observation(*, health=ProviderHealth.AVAILABLE, observed_at=NOW):
    return ProviderObservation(
        provider_id="provider-glm-shared",
        health=health,
        observed_at=observed_at,
        provenance="fake:test",
        latency_ms=20,
    )


def make_dispatch(worktree: Path, **overrides) -> HarnessDispatch:
    values = dict(
        execution_id="exec-aha3-test",
        task_contract_ref="work-order:WO-P1-091",
        project_id="a-wiki-conductor",
        worktree_path=str(worktree),
        expected_branch="feat/wo-p1-091-claude-code-harness",
        expected_head="a" * 40,
        provider_id="provider-glm-shared",
        model_id="glm-5.3",
        harness_strategy=HarnessStrategy.CLAUDE_CODE_CLI,
        effort_level="HIGH",
        mutation_intent=MutationIntent.READ_ONLY,
        timeout_seconds=120,
        max_output_bytes=4096,
    )
    values.update(overrides)
    return HarnessDispatch(**values)


def make_packet(worktree: Path, text: str = "# Bounded task\nRead only.\n") -> TaskPacketFile:
    path = worktree / ".a-conductor" / "task-packets" / "WO-P1-091.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return TaskPacketFile(
        task_contract_ref="work-order:WO-P1-091",
        path=str(path),
        sha256=digest,
    )


class FakeRunner:
    def __init__(self, result: ClaudeCodeRunnerResult) -> None:
        self.result = result
        self.calls = []

    def run(self, invocation):
        self.calls.append(invocation)
        return self.result


def success_runner(payload=None) -> FakeRunner:
    if payload is None:
        payload = {"type": "result", "is_error": False, "result": "done"}
    return FakeRunner(
        ClaudeCodeRunnerResult(
            exit_code=0,
            stdout=json.dumps(payload),
            stderr="",
            timed_out=False,
        )
    )


def test_dispatch_is_schema_aligned_and_has_no_freeform_execution_payload(tmp_path) -> None:
    dispatch = make_dispatch(tmp_path)
    schema = json.loads(
        Path("schemas/harness-dispatch.schema.json").read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(dispatch.as_dict())
    forbidden = {
        "prompt",
        "transcript",
        "command",
        "argv",
        "shell",
        "executable",
        "environment",
        "env",
        "authorized",
    }
    assert not forbidden.intersection(dispatch.__dataclass_fields__)


def test_adapter_builds_fixed_read_only_noninteractive_invocation(tmp_path) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test/v1")
    result = adapter.execute(
        make_dispatch(tmp_path), profile, endpoint, make_observation(), make_packet(tmp_path), now=NOW
    )
    assert result.status is HarnessExecutionStatus.SUCCESS
    assert len(runner.calls) == 1
    invocation = runner.calls[0]
    assert invocation.cwd == str(tmp_path)
    assert invocation.timeout_seconds == 120
    assert invocation.max_output_bytes == 4096
    assert invocation.argv[0] == "claude"
    assert "--print" in invocation.argv
    assert "--output-format" in invocation.argv
    assert "json" in invocation.argv
    assert "--no-session-persistence" in invocation.argv
    assert "--safe-mode" in invocation.argv
    setting_index = invocation.argv.index("--setting-sources")
    assert invocation.argv[setting_index + 1] == "project,local"
    assert "--permission-mode" in invocation.argv
    assert "plan" in invocation.argv
    assert "--system-prompt-file" in invocation.argv
    assert str(Path(make_packet(tmp_path).path)) in invocation.argv
    assert "--model" in invocation.argv and "glm-5.3" in invocation.argv
    assert "--effort" in invocation.argv and "high" in invocation.argv
    assert "--dangerously-skip-permissions" not in invocation.argv
    assert "bypassPermissions" not in invocation.argv
    assert "Bash" not in ",".join(invocation.argv)
    bindings = {item.key: item for item in invocation.environment_bindings}
    assert set(bindings) == {"ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN"}
    assert bindings["ANTHROPIC_BASE_URL"].source_ref == profile.endpoint_ref
    assert bindings["ANTHROPIC_AUTH_TOKEN"].source_ref == profile.credential_ref
    assert bindings["ANTHROPIC_AUTH_TOKEN"].secret is True
    assert endpoint.base_url not in repr(invocation)


def test_default_effort_omits_effort_flag(tmp_path) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    adapter.execute(
        make_dispatch(tmp_path, effort_level="DEFAULT"),
        profile,
        endpoint,
        make_observation(),
        make_packet(tmp_path),
        now=NOW,
    )
    assert "--effort" not in runner.calls[0].argv


@pytest.mark.parametrize(
    ("overrides", "code"),
    (
        ({"mutation_intent": MutationIntent.PROJECT_MUTATION}, "HARNESS_MUTATION_NOT_READY"),
        ({"harness_strategy": HarnessStrategy.DIRECT_API}, "HARNESS_STRATEGY_UNSUPPORTED"),
    ),
)
def test_adapter_fails_closed_before_runner_for_unsupported_dispatch(tmp_path, overrides, code) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(
            make_dispatch(tmp_path, **overrides),
            profile,
            endpoint,
            make_observation(),
            make_packet(tmp_path),
            now=NOW,
        )
    assert exc_info.value.code == code
    assert runner.calls == []


@pytest.mark.parametrize(
    "observation",
    (
        None,
        make_observation(health=ProviderHealth.DEGRADED),
        make_observation(observed_at=NOW - timedelta(seconds=301)),
    ),
)
def test_provider_must_be_fresh_and_available_before_runner(tmp_path, observation) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(
            make_dispatch(tmp_path),
            profile,
            endpoint,
            observation,
            make_packet(tmp_path),
            now=NOW,
        )
    assert exc_info.value.code == "PROVIDER_NOT_READY"
    assert runner.calls == []


def test_provider_and_model_identity_must_match_dispatch(tmp_path) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    for dispatch in (
        make_dispatch(tmp_path, provider_id="provider-other"),
        make_dispatch(tmp_path, model_id="model-other"),
    ):
        with pytest.raises(ClaudeCodeHarnessError) as exc_info:
            adapter.execute(
                dispatch,
                profile,
                endpoint,
                make_observation(),
                make_packet(tmp_path),
                now=NOW,
            )
        assert exc_info.value.code in {"PROVIDER_ID_MISMATCH", "MODEL_NOT_CONFIGURED"}
    assert runner.calls == []


def test_task_packet_is_bound_to_worktree_contract_size_and_hash(tmp_path) -> None:
    runner = success_runner()
    adapter = ClaudeCodeHarnessAdapter(runner=runner, max_task_packet_bytes=64)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    dispatch = make_dispatch(tmp_path)

    valid = make_packet(tmp_path)
    assert adapter.execute(
        dispatch, profile, endpoint, make_observation(), valid, now=NOW
    ).status is HarnessExecutionStatus.SUCCESS

    bad_hash = TaskPacketFile(valid.task_contract_ref, valid.path, "0" * 64)
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(dispatch, profile, endpoint, make_observation(), bad_hash, now=NOW)
    assert exc_info.value.code == "TASK_PACKET_HASH_MISMATCH"

    wrong_ref = TaskPacketFile("work-order:OTHER", valid.path, valid.sha256)
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(dispatch, profile, endpoint, make_observation(), wrong_ref, now=NOW)
    assert exc_info.value.code == "TASK_PACKET_REF_MISMATCH"

    outside_path = tmp_path.parent / "outside-task.md"
    outside_path.write_text("outside", encoding="utf-8")
    outside = TaskPacketFile(
        valid.task_contract_ref,
        str(outside_path),
        hashlib.sha256(outside_path.read_bytes()).hexdigest(),
    )
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(dispatch, profile, endpoint, make_observation(), outside, now=NOW)
    assert exc_info.value.code == "TASK_PACKET_OUTSIDE_WORKTREE"

    oversized = make_packet(tmp_path, "x" * 65)
    with pytest.raises(ClaudeCodeHarnessError) as exc_info:
        adapter.execute(dispatch, profile, endpoint, make_observation(), oversized, now=NOW)
    assert exc_info.value.code == "TASK_PACKET_TOO_LARGE"


def test_json_evidence_is_redacted_before_return(tmp_path) -> None:
    secret = "synthetic-sensitive-value-12345"
    runner = success_runner(
        {"type": "result", "is_error": False, "result": f"result contains {secret}"}
    )
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    result = adapter.execute(
        make_dispatch(tmp_path),
        profile,
        endpoint,
        make_observation(),
        make_packet(tmp_path),
        now=NOW,
        redaction_values=(secret,),
    )
    assert result.status is HarnessExecutionStatus.SUCCESS
    assert result.payload["result"] == "result contains [REDACTED]"
    assert secret not in repr(result)


def test_timeout_nonzero_invalid_json_and_error_payload_are_typed(tmp_path) -> None:
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    dispatch = make_dispatch(tmp_path)
    packet = make_packet(tmp_path)
    cases = (
        (ClaudeCodeRunnerResult(None, "", "", True), HarnessExecutionStatus.TIMEOUT),
        (ClaudeCodeRunnerResult(2, "{}", "failure", False), HarnessExecutionStatus.FAILED),
        (ClaudeCodeRunnerResult(0, "not-json", "", False), HarnessExecutionStatus.OUTPUT_INVALID),
        (
            ClaudeCodeRunnerResult(0, json.dumps({"is_error": True, "result": "bad"}), "", False),
            HarnessExecutionStatus.FAILED,
        ),
    )
    for raw, expected in cases:
        result = ClaudeCodeHarnessAdapter(runner=FakeRunner(raw)).execute(
            dispatch, profile, endpoint, make_observation(), packet, now=NOW
        )
        assert result.status is expected


def test_output_budget_fails_closed_without_returning_oversized_content(tmp_path) -> None:
    secret = "sensitive-output-value"
    runner = FakeRunner(
        ClaudeCodeRunnerResult(
            exit_code=0,
            stdout=json.dumps({"result": secret * 20}),
            stderr="",
            timed_out=False,
        )
    )
    adapter = ClaudeCodeHarnessAdapter(runner=runner)
    profile = make_profile()
    endpoint = ProviderEndpointConfig(profile.endpoint_ref, "https://api.example.test")
    result = adapter.execute(
        make_dispatch(tmp_path, max_output_bytes=80),
        profile,
        endpoint,
        make_observation(),
        make_packet(tmp_path),
        now=NOW,
        redaction_values=(secret,),
    )
    assert result.status is HarnessExecutionStatus.OUTPUT_LIMIT
    assert result.payload is None
    assert secret not in repr(result)


def test_adapter_result_has_no_task_completion_or_authorization_authority(tmp_path) -> None:
    result = ClaudeCodeHarnessAdapter(runner=success_runner()).execute(
        make_dispatch(tmp_path), make_profile(),
        ProviderEndpointConfig("provider-config:glm-shared/base-url", "https://api.example.test"),
        make_observation(), make_packet(tmp_path), now=NOW,
    )
    forbidden = {"task_state", "complete", "authorized", "authorization", "retry"}
    assert not forbidden.intersection(result.__dataclass_fields__)


def test_failed_stderr_is_redacted_before_return(tmp_path) -> None:
    secret = "synthetic-stderr-secret"
    runner = FakeRunner(ClaudeCodeRunnerResult(2, "{}", f"failure {secret}", False))
    result = ClaudeCodeHarnessAdapter(runner=runner).execute(
        make_dispatch(tmp_path), make_profile(),
        ProviderEndpointConfig("provider-config:glm-shared/base-url", "https://api.example.test"),
        make_observation(), make_packet(tmp_path), now=NOW,
        redaction_values=(secret,),
    )
    assert result.status is HarnessExecutionStatus.FAILED
    assert result.stderr == "failure [REDACTED]"
    assert secret not in repr(result)


def test_json_object_keys_are_redacted_too(tmp_path) -> None:
    secret = "synthetic-key-secret"
    runner = success_runner({secret: f"value {secret}", "is_error": False})
    result = ClaudeCodeHarnessAdapter(runner=runner).execute(
        make_dispatch(tmp_path), make_profile(),
        ProviderEndpointConfig("provider-config:glm-shared/base-url", "https://api.example.test"),
        make_observation(), make_packet(tmp_path), now=NOW,
        redaction_values=(secret,),
    )
    assert secret not in repr(result)
