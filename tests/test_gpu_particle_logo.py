"""GPU Sunday Family particle renderer contracts."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import time

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


def test_gpu_sampling_density_tracks_luminance_instead_of_flattening_detail(
    tmp_path,
) -> None:
    from PIL import Image

    from a_conductor.gpu_particle_logo import build_particle_vertices

    source = Image.new("L", (64, 16), 64)
    source.paste(255, (32, 0, 64, 16))
    path = tmp_path / "tonal-particles.png"
    source.save(path)

    packed, count, _aspect = build_particle_vertices(
        path,
        max_particles=10_000,
        max_dimension=64,
        threshold=10,
    )
    left = sum(1 for u in packed[0::5] if u < 0.5)
    right = count - left

    assert count > 400
    # Bright landmarks need materially denser coverage, while some mid-tone
    # particles must remain so faces and the Sunday Family badge retain likeness.
    assert right >= left * 6


@pytest.mark.skipif(sys.platform != "win32", reason="real WGL framebuffer contract")
def test_real_gpu_framebuffer_contains_visible_family_particles() -> None:
    """A live context/count is insufficient: the back buffer must contain pixels."""
    import tkinter as tk

    from OpenGL import GL

    from a_conductor.gpu_particle_logo import GPUParticleLogo, gpu_backend_available

    if not gpu_backend_available():
        pytest.skip("GPU dependencies are unavailable")

    root = tk.Tk()
    root.configure(bg="#000000")
    logo = GPUParticleLogo(root, size=120)
    logo.pack()
    assert logo.load_image(ASSET)
    logo.start()
    root.deiconify()
    try:
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and not logo._gpu_ready:
            root.update()
        if logo.gpu_error and "GPU_FRAMEBUFFER_BLANK" in logo.gpu_error:
            pytest.fail(logo.gpu_error)
        if not logo._gpu_ready or logo._gl_frame is None:
            pytest.skip(f"real OpenGL context unavailable: {logo.gpu_error}")

        root.update_idletasks()
        logo._gl_frame.tkMakeCurrent()
        logo._redraw_gl(logo._gl_frame)
        GL.glReadBuffer(GL.GL_BACK)
        raw = bytes(
            GL.glReadPixels(0, 0, 120, 120, GL.GL_RGB, GL.GL_UNSIGNED_BYTE)
        )
        nonblack = sum(
            1
            for offset in range(0, len(raw), 3)
            if raw[offset] or raw[offset + 1] or raw[offset + 2]
        )

        assert logo._particle_count >= 6_000
        assert nonblack >= 500, "GPU initialized but rendered a blank family portrait"
        assert logo._frame_verified is True
        assert logo.renderer_name == "gpu-opengl"
    finally:
        logo.destroy()
        try:
            root.destroy()
        except tk.TclError:
            pass


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


def test_gpu_family_particles_remain_fine_at_header_size() -> None:
    from a_conductor import gpu_particle_logo as g

    maximum_point_size = (
        g.GPU_POINT_BASE_SIZE
        + g.GPU_POINT_LUMA_SIZE
        + g.GPU_POINT_INTERACTION_SIZE
    )

    assert 0.85 <= maximum_point_size <= 1.35
    assert "__POINT_BASE__" not in g._VERTEX_SHADER
    assert "__POINT_LUMA__" not in g._VERTEX_SHADER
    assert "__POINT_INTERACTION__" not in g._VERTEX_SHADER


def test_gpu_frame_health_gate_requires_meaningful_portrait_coverage() -> None:
    from a_conductor.gpu_particle_logo import minimum_visible_pixels

    assert 500 <= minimum_visible_pixels(120, 120) <= 1_000
    assert minimum_visible_pixels(32, 32) >= 32


def test_gpu_pointer_field_is_bounded_below_one_pixel_at_header_size() -> None:
    from a_conductor import gpu_particle_logo as g

    # NDC spans two units across the widget.  The independent design limit for
    # the local radial/tangential field is one physical pixel at 120 px.
    local_field_px = math.hypot(
        g.GPU_REPULSION_CLIP,
        g.GPU_TRAIL_CLIP,
    ) * (120 / 2)

    assert 0.0 < local_field_px <= 1.0
    assert "__REPULSION__" not in g._VERTEX_SHADER
    assert "__TRAIL__" not in g._VERTEX_SHADER
    assert f"{g.GPU_REPULSION_CLIP:.6f}" in g._VERTEX_SHADER
    assert f"{g.GPU_TRAIL_CLIP:.6f}" in g._VERTEX_SHADER


def test_gpu_eye_motion_excludes_local_distortion_and_stays_below_three_pixels() -> None:
    from a_conductor import gpu_particle_logo as g

    combined_eye_px = (
        g.GPU_FACE_PARALLAX_CLIP + g.GPU_GAZE_CLIP + g.GPU_IDLE_DRIFT_CLIP
    ) * (120 / 2)

    assert combined_eye_px <= 3.0
    assert "field * (1.0 - in_eye)" in g._VERTEX_SHADER


def test_gpu_pointer_leave_decays_and_requires_fresh_sample_before_reentry() -> None:
    from a_conductor.gpu_particle_logo import GPUParticleLogo

    logo = GPUParticleLogo.__new__(GPUParticleLogo)
    logo._mouse_x = 0.8
    logo._mouse_y = -0.6
    logo._render_mouse_x = 0.8
    logo._render_mouse_y = -0.6
    logo._mouse_vx = 1.0
    logo._mouse_vy = -0.5
    logo._interaction_strength = 1.0
    logo._mouse_active = True

    logo._advance_pointer_state(pointer_inside=False)

    assert 0.0 < logo._interaction_strength < 1.0
    assert 0.0 < logo._render_mouse_x < 0.8
    assert -0.6 < logo._render_mouse_y < 0.0
    assert logo._mouse_active is False

    for _ in range(40):
        logo._advance_pointer_state(pointer_inside=False)
    decayed_strength = logo._interaction_strength
    assert decayed_strength < 0.001
    assert abs(logo._render_mouse_x) < 0.001
    assert abs(logo._render_mouse_y) < 0.001

    # Merely becoming geometrically inside cannot reactivate a stale location.
    logo._advance_pointer_state(pointer_inside=True)
    assert logo._interaction_strength <= decayed_strength

    # A new Motion sample eases in; it does not jump straight to full strength.
    logo._mouse_x = -0.7
    logo._mouse_y = 0.5
    logo._mouse_active = True
    logo._advance_pointer_state(pointer_inside=True)
    assert decayed_strength < logo._interaction_strength < 1.0
    assert -0.7 < logo._render_mouse_x < 0.0
    assert 0.0 < logo._render_mouse_y < 0.5


def test_gpu_renderer_release_makes_context_current_then_releases_every_layer(
    monkeypatch,
) -> None:
    from a_conductor import gpu_particle_logo as g

    events: list[str] = []

    class Resource:
        def __init__(self, name: str) -> None:
            self.name = name

        def release(self) -> None:
            events.append(self.name)

    class Frame:
        context_created = True

        def tkMakeCurrent(self) -> None:
            events.append("current")

        def destroy(self) -> None:
            events.append("frame")

    frame = Frame()
    logo = g.GPUParticleLogo.__new__(g.GPUParticleLogo)
    logo._gl_frame = frame
    logo._vao = Resource("vao")
    logo._buffer = Resource("buffer")
    logo._program = Resource("program")
    logo._ctx = Resource("moderngl-context")
    logo._gpu_ready = True
    logo._frame_verified = True
    monkeypatch.setattr(
        g,
        "_release_pyopengltk_context",
        lambda released_frame: events.append(
            "native-context" if released_frame is frame else "wrong-frame"
        ),
    )

    logo._release_gl_renderer(destroy_frame=True)

    assert events == [
        "current",
        "vao",
        "buffer",
        "program",
        "moderngl-context",
        "native-context",
        "frame",
    ]
    assert logo._ctx is None
    assert logo._gl_frame is None
    assert logo._gpu_ready is False
    assert logo._frame_verified is False


def test_gpu_destroy_cancels_pending_fallback_and_guard_blocks_late_callback() -> None:
    from a_conductor.gpu_particle_logo import GPUParticleLogo

    scheduled: list[object] = []
    cancelled: list[str] = []

    class Frame:
        def after_idle(self, callback):
            scheduled.append(callback)
            return "after#fallback"

        def after_cancel(self, callback_id: str) -> None:
            cancelled.append(callback_id)

        def winfo_toplevel(self):
            return self

        def destroy(self) -> None:
            pass

    logo = GPUParticleLogo.__new__(GPUParticleLogo)
    logo.frame = Frame()
    logo._destroyed = False
    logo._fallback_after_id = None
    logo._fallback = None
    logo._gl_frame = None
    logo._ctx = None
    logo._vao = None
    logo._buffer = None
    logo._program = None
    logo._particle_count = 0
    logo._gpu_ready = False
    logo._running = False
    logo._motion_binding = None

    logo._schedule_fallback(RuntimeError("context failed"))
    assert logo._fallback_after_id == "after#fallback"

    logo.destroy()

    assert cancelled == ["after#fallback"]
    assert logo._fallback_after_id is None
    assert logo._destroyed is True
    scheduled[0]()
    assert logo._fallback is None

def test_compact_logo_is_derived_asset_not_legacy_tiny_placeholder() -> None:
    from PIL import Image
    compact = ASSET.parent / "logo-face.png"
    assert compact.is_file()
    with Image.open(compact) as image:
        assert image.size == (256, 256)
        assert image.mode == "RGB"
