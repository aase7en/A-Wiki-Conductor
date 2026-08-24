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


def test_gpu_motion_contract_is_gentle_and_amber_is_eye_only() -> None:
    from a_conductor import gpu_particle_logo as g

    assert 0.0 < g.GPU_FACE_PARALLAX_CLIP <= 0.02
    assert 0.0 < g.GPU_GAZE_CLIP <= 0.04
    assert g.GPU_FACE_PARALLAX_CLIP < g.GPU_GAZE_CLIP
    assert "v_eye" in g._VERTEX_SHADER
    assert "v_eye" in g._FRAGMENT_SHADER
    assert "vec3(0.96, 0.55, 0.10)" in g._FRAGMENT_SHADER
    assert "__FACE_PARALLAX__" not in g._VERTEX_SHADER
    assert "__GAZE__" not in g._VERTEX_SHADER
    assert f"{g.GPU_FACE_PARALLAX_CLIP:.6f}" in g._VERTEX_SHADER
    assert f"{g.GPU_GAZE_CLIP:.6f}" in g._VERTEX_SHADER

def test_compact_logo_is_derived_asset_not_legacy_tiny_placeholder() -> None:
    from PIL import Image
    compact = ASSET.parent / "logo-face.png"
    assert compact.is_file()
    with Image.open(compact) as image:
        assert image.size == (256, 256)
        assert image.mode == "RGB"
