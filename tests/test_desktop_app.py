from __future__ import annotations

from dataclasses import dataclass

import pytest

import a_conductor.desktop_app as desktop_app


@dataclass(frozen=True)
class _Kind:
    value: str


@dataclass(frozen=True)
class _Result:
    kind: _Kind
    reason_code: str


class _Service:
    def __init__(self) -> None:
        self.calls = []

    def activate_runtime(self, database, request):
        self.calls.append((database, request))
        return _Result(_Kind("FIXED_POOL_EXECUTED"), "PARALLEL_READY_RUN_COMPLETED")


def _activation_args(tmp_path):
    return [
        "--database",
        str(tmp_path / "control.sqlite"),
        "--activate-runtime",
        "--graph-id",
        "graph-1",
        "--graph-run-id",
        "run-1",
        "--node-id",
        "n1",
        "--project-root",
        str(tmp_path),
        "--task-contract-ref",
        "tasks/task.json",
        "--task-packet",
        str(tmp_path / "packet.md"),
        "--provider-id",
        "provider-1",
        "--model-id",
        "model-1",
        "--runtime-kind",
        "serena",
        "--effort-level",
        "MAX",
    ]


def test_runtime_activation_cli_delegates_without_constructing_tk(
    tmp_path, monkeypatch, capsys
):
    service = _Service()
    monkeypatch.setattr(desktop_app, "_open_service", lambda database: service)

    def _tk_forbidden():
        raise AssertionError("runtime activation CLI must not construct Tk")

    monkeypatch.setattr(desktop_app.tk, "Tk", _tk_forbidden)

    code = desktop_app.main(_activation_args(tmp_path))

    assert code == 0
    assert len(service.calls) == 1
    database, request = service.calls[0]
    assert database == tmp_path / "control.sqlite"
    assert request.graph_id == "graph-1"
    assert request.graph_run_id == "run-1"
    assert request.node_id == "n1"
    assert request.task_contract_ref == "tasks/task.json"
    assert request.provider_id == "provider-1"
    assert request.model_id == "model-1"
    output = capsys.readouterr().out
    assert "A-CONDUCTOR_RUNTIME_ACTIVATION_OK" in output
    assert "FIXED_POOL_EXECUTED" in output
    assert "PARALLEL_READY_RUN_COMPLETED" in output


def test_runtime_activation_cli_requires_all_identity_pointers(
    tmp_path, monkeypatch, capsys
):
    service = _Service()
    monkeypatch.setattr(desktop_app, "_open_service", lambda database: service)
    args = _activation_args(tmp_path)
    index = args.index("--task-contract-ref")
    del args[index : index + 2]

    code = desktop_app.main(args)

    assert code == 2
    assert service.calls == []
    output = capsys.readouterr().out
    assert "A-CONDUCTOR_RUNTIME_ACTIVATION_FAILED" in output
    assert "TASK_CONTRACT_REF_REQUIRED" in output


def test_default_parser_does_not_require_runtime_activation_fields():
    args = desktop_app.build_parser().parse_args([])

    assert args.activate_runtime is False
