from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path

import pytest

from a_conductor import dex_identity
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


def test_dedicated_root_digest_helper_exists() -> None:
    assert hasattr(dex_identity, "canonical_root_digest")
    assert callable(dex_identity.canonical_root_digest)


@pytest.mark.parametrize(
    ("platform_tag", "canonical_path", "expected"),
    [
        (
            "win32",
            "c:\\repo\\work",
            "aa2a21e52e96d0188faca668dcbeda48d6c0c454859ab32caee8cd325ad4c786",
        ),
        (
            "posix",
            "/srv/repo",
            "e316d7049a2dcb0ae2be546a7fedb07d537ac769735d567e96985a2e0a73084f",
        ),
        (
            "win32",
            "\\\\server\\share\\repo",
            "b4f5a4a7b27cc64a7e11dff32f2412e63c279e11e5150b7bf3f97a8c6893c2ba",
        ),
    ],
)
def test_canonical_root_digest_matches_frozen_srm_vectors(
    platform_tag: str, canonical_path: str, expected: str
) -> None:
    assert (
        dex_identity.canonical_root_digest(canonical_path, platform_tag=platform_tag)
        == expected
    )


@pytest.mark.parametrize(
    "platform_tag",
    ["nt", "WIN32", "windows", "darwin", "", None, 7, b"win32"],
)
def test_canonical_root_digest_rejects_non_srm_platform_tags(
    platform_tag: object,
) -> None:
    with pytest.raises(ValueError):
        dex_identity.canonical_root_digest("c:\\repo\\work", platform_tag=platform_tag)


@pytest.mark.parametrize(
    "canonical_path",
    ["", None, 7, b"c:\\repo\\work", "c:\\repo\\wo\x00rk", "c:\\repo\rrk", "c:\\repo\nrk"],
)
def test_canonical_root_digest_rejects_invalid_canonical_path(
    canonical_path: object,
) -> None:
    with pytest.raises(ValueError):
        dex_identity.canonical_root_digest(canonical_path, platform_tag="win32")


def test_canonical_root_digest_is_distinct_from_binding_digest() -> None:
    binding = _binding("c:\\repo\\authority", "/srv/execution")
    root_digest = dex_identity.canonical_root_digest(
        "c:\\repo\\authority", platform_tag="win32"
    )
    assert root_digest != binding_digest(binding)
    assert root_digest == dex_identity.canonical_root_digest(
        "c:\\repo\\authority", platform_tag="win32"
    )


def test_binding_digest_preimage_unchanged_by_root_digest_helper() -> None:
    binding = _binding("c:\\repo\\authority", "/srv/execution")
    assert (
        binding_digest(binding)
        == "81e55bd0f4e5cf75ea314aa626465b604a4b0f060e15e5791770224b2cbb64bd"
    )
