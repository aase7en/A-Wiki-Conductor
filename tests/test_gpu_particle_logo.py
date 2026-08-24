"""GPU Sunday Family particle renderer contracts."""

from __future__ import annotations

from pathlib import Path

import pytest


ASSET = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"


def test_gpu_module_imports_without_requiring_context() -> None:
    from a_conductor.gpu_particle_logo import GPUParticleLogo, gpu_backend_available

    assert callable(GPUParticleLogo)
    assert isinstance(gpu_backend_available(), bool)


def test_family_particle_asset_is_present_and_png() -> None:
    assert ASSET.is_file()
    assert ASSET.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_family_gpu_sampling_is_dense_bounded_and_tracks_eyes() -> None:
    from a_conductor.gpu_particle_logo import build_particle_vertices, gpu_backend_available

    if not gpu_backend_available():
        pytest.skip("GPU dependencies are intentionally optional on this platform")

    packed, count, aspect = build_particle_vertices(
        ASSET,
        max_particles=12_000,
        max_dimension=360,
    )
    assert 2_000 < count <= 12_000
    assert len(packed) == count * 5
    assert aspect == pytest.approx(1448 / 1086, rel=1e-4)

    eye_weights = packed[4::5]
    assert max(eye_weights) > 0.5


def test_gpu_can_be_disabled_for_safe_fallback(monkeypatch) -> None:
    from a_conductor import gpu_particle_logo

    monkeypatch.setenv("A_CONDUCTOR_GPU_PARTICLES", "0")
    assert gpu_particle_logo.gpu_backend_available() is False
