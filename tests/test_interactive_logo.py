"""Interactive Logo: image-mapped particles, gaze tracking, and repulsion."""

from __future__ import annotations

import math

import pytest


@pytest.fixture()
def root():
    import tkinter as tk

    try:
        window = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk display unavailable: {exc}")
    window.withdraw()
    yield window
    try:
        window.destroy()
    except tk.TclError:
        pass


def test_logo_module_imports() -> None:
    from a_conductor.interactive_logo import InteractiveLogo, Particle, FACE_MAP

    assert callable(InteractiveLogo)
    assert callable(Particle)
    assert len(FACE_MAP) > 0
    assert any("1" in row for row in FACE_MAP)
    assert any("E" in row for row in FACE_MAP)


def test_eye_target_moves_toward_pointer_but_is_bounded() -> None:
    from a_conductor.interactive_logo import eye_target

    x, y = eye_target(10.0, 20.0, 1000.0, 20.0, max_shift=4.5)
    assert y == pytest.approx(20.0)
    assert x > 10.0
    assert math.hypot(x - 10.0, y - 20.0) <= 4.5 + 1e-9


def test_eye_target_at_home_is_stable() -> None:
    from a_conductor.interactive_logo import eye_target

    assert eye_target(10.0, 20.0, 10.0, 20.0) == (10.0, 20.0)


def test_family_eye_regions_have_positive_and_negative_hits() -> None:
    from a_conductor.interactive_logo import FAMILY_EYE_REGIONS, normalized_eye_hit

    cx, cy, _radius = FAMILY_EYE_REGIONS[0]
    assert normalized_eye_hit(cx, cy)
    assert not normalized_eye_hit(0.5, 0.9)


def test_repulsion_impulse_pushes_away_and_fades_outside_radius() -> None:
    from a_conductor.interactive_logo import repulsion_impulse

    ix, iy = repulsion_impulse(20.0, 10.0, 10.0, 10.0, radius=20.0, force=4.0)
    assert ix > 0.0
    assert iy == pytest.approx(0.0)
    assert repulsion_impulse(31.0, 10.0, 10.0, 10.0, radius=20.0, force=4.0) == (
        0.0,
        0.0,
    )


def test_logo_creates_canvas_with_particles(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    assert len(logo.particles) > 0
    assert all(p.id is not None for p in logo.particles)


def test_logo_particle_structure(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    for p in logo.particles:
        assert 0 <= p.home_x <= 80
        assert 0 <= p.home_y <= 80
        assert isinstance(p.is_eye, bool)
        assert p.base_radius > 0
        assert 0.0 <= p.seed <= 1.0


def test_logo_face_has_eyes(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    eyes = [p for p in logo.particles if p.is_eye]
    assert len(eyes) > 0


def test_logo_start_stop(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    logo.start()
    assert logo._running is True
    logo.stop()
    assert logo._running is False


def test_logo_mouse_tracking_updates_position(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    logo.mouse_x = 40.0
    logo.mouse_y = 40.0
    logo.mouse_active = True
    assert logo.mouse_x == 40.0
    assert logo.mouse_active is True


def test_monochrome_particle_source_gets_family_label(root, tmp_path) -> None:
    import tkinter as tk

    from a_conductor.interactive_logo import InteractiveLogo, MONO_DOT_COLOR

    source = tk.PhotoImage(width=96, height=72)
    source.put("#000000", to=(0, 0, 96, 72))
    # Dense white portrait-like field with black negative space.
    source.put("#ffffff", to=(12, 8, 84, 64))
    path = tmp_path / "family.png"
    source.write(path, format="png")

    logo = InteractiveLogo(root, size=120)
    assert logo.load_image(path) is True
    assert logo._monochrome_source is True
    assert any(p.color == MONO_DOT_COLOR for p in logo.particles)
    # Image particles are capped, then the procedural label is appended.
    assert len(logo.particles) > 0


def test_app_header_has_logo(root, tmp_path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    service = DesktopControlService.open(tmp_path / "cc.sqlite")
    app = AConductorDesktopApp(root, service=service)
    assert hasattr(app, "_logo")


def test_monochrome_particle_color_is_neutral_gray() -> None:
    from a_conductor.interactive_logo import MONO_DOT_COLOR

    value = MONO_DOT_COLOR.lstrip("#")
    red, green, blue = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    assert red == green == blue


def test_baked_sunday_family_asset_does_not_add_duplicate_label(root, monkeypatch) -> None:
    from pathlib import Path

    from a_conductor.interactive_logo import InteractiveLogo

    asset = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"
    logo = InteractiveLogo(root, size=120)
    calls: list[tuple] = []
    monkeypatch.setattr(
        logo,
        "_add_particle_label",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert logo.load_image(asset) is True
    assert logo._monochrome_source is True
    assert calls == []


def test_dense_fallback_idle_skips_canvas_coordinate_writes(root, monkeypatch) -> None:
    from pathlib import Path

    from a_conductor.interactive_logo import (
        FALLBACK_IDLE_PARTICLE_LIMIT,
        InteractiveLogo,
    )

    asset = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"
    logo = InteractiveLogo(root, size=120)
    assert logo.load_image(asset) is True
    assert len(logo.particles) > FALLBACK_IDLE_PARTICLE_LIMIT

    logo._running = True
    logo.mouse_active = False
    monkeypatch.setattr(logo, "_refresh_pointer", lambda: None)
    monkeypatch.setattr(logo, "_update_mouse_trail", lambda: None)
    monkeypatch.setattr(logo, "_trail_impulse", lambda _particle: (0.0, 0.0))
    monkeypatch.setattr(logo.canvas, "after", lambda *args, **kwargs: None)

    writes = 0
    original_coords = logo.canvas.coords

    def count_coords(*args):
        nonlocal writes
        writes += 1
        return original_coords(*args)

    monkeypatch.setattr(logo.canvas, "coords", count_coords)
    logo._animate()

    assert writes == 0
