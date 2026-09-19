from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path

import pytest

from a_conductor.dex_identity import (
    DexBindingIdentity,
    DexIdentityError,
    binding_digest,
    canonicalize_existing_root,
)


def _binding(authority_root: str, execution_root: str) -> DexBindingIdentity:
    return DexBindingIdentity(
        execution_id="exec-001",
        attempt_id="attempt-001",
        task_ref="WO-P1-260",
        lane_ref="lane:WO-P1-260:author:1",
        claim_ref="issue:348#dex2b-phase-a",
        claim_generation=3,
        authority_repo_identity=authority_root,
        execution_repo_identity=execution_root,
        authority_sha="a" * 40,
        execution_sha="b" * 40,
        host_id="host-01",
        boot_id="boot-01",
        executable_path="C:/Tools/kilo.exe",
        executable_sha256="c" * 64,
        argv_shape=("kilo", "run", "<task-ref>"),
    )


def test_existing_root_uses_physical_identity(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert canonicalize_existing_root(alias) == canonicalize_existing_root(target)


def test_missing_root_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(DexIdentityError, match="PROJECT_IDENTITY_FAILED"):
        canonicalize_existing_root(tmp_path / "missing")


def test_windows_final_path_normalization_is_deterministic(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    assert canonicalize_existing_root(
        root,
        platform_name="nt",
        final_path_resolver=lambda _: r"\\?\C:\Repo\Work",
    ) == r"c:\repo\work"
    assert canonicalize_existing_root(
        root,
        platform_name="nt",
        final_path_resolver=lambda _: r"\\?\UNC\Server\Share\Repo",
    ) == r"\\server\share\repo"


def test_binding_digest_is_stable_and_attempt_scoped(tmp_path: Path) -> None:
    auth = tmp_path / "auth"
    exec_root = tmp_path / "exec"
    auth.mkdir()
    exec_root.mkdir()
    binding = _binding(
        canonicalize_existing_root(auth),
        canonicalize_existing_root(exec_root),
    )
    first = binding_digest(binding)
    assert len(first) == 64
    assert first == binding_digest(binding)
    assert binding_digest(replace(binding, attempt_id="attempt-002")) != first
