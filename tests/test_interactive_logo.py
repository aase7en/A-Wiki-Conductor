"""Interactive Logo: image-mapped particles, gaze tracking, and repulsion."""

from __future__ import annotations

import math
from collections import deque

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
    from a_conductor.interactive_logo import EYE_TRACK_RANGE, eye_target

    x, y = eye_target(10.0, 20.0, 1000.0, 20.0)
    assert y == pytest.approx(20.0)
    assert x > 10.0
    assert EYE_TRACK_RANGE <= 2.5
    assert math.hypot(x - 10.0, y - 20.0) <= 2.5 + 1e-9


def test_eye_target_at_home_is_stable() -> None:
    from a_conductor.interactive_logo import eye_target

    assert eye_target(10.0, 20.0, 10.0, 20.0) == (10.0, 20.0)


@pytest.mark.parametrize("mouse_x", [51.0, 1000.0])
def test_eye_particle_stays_within_three_pixels_under_sustained_interaction(
    mouse_x,
) -> None:
    from a_conductor.interactive_logo import InteractiveLogo, Particle

    class Clock:
        @staticmethod
        def call(*_args):
            return 1000

    class Canvas:
        tk = Clock()

        @staticmethod
        def after(*_args):
            return "after#next"

    eye = Particle(50.0, 50.0, is_eye=True, seed=0.5)
    logo = InteractiveLogo.__new__(InteractiveLogo)
    logo.canvas = Canvas()
    logo.particles = [eye]
    logo.mouse_x = mouse_x
    logo.mouse_y = 50.0
    logo.mouse_active = True
    logo._running = True
    logo._after_id = None
    logo._started_ms = 1000
    logo._trail = deque([[51.0, 50.0, 1.0]], maxlen=12)
    logo._refresh_pointer = lambda: None
    logo._update_mouse_trail = lambda: None

    max_displacement = 0.0
    for _ in range(180):
        logo._animate()
        max_displacement = max(
            max_displacement,
            math.hypot(eye.x - eye.home_x, eye.y - eye.home_y),
        )

    assert max_displacement <= 3.0


def test_non_eye_particle_stays_bounded_and_returns_after_pointer_leaves() -> None:
    from a_conductor.interactive_logo import InteractiveLogo, Particle

    class Clock:
        @staticmethod
        def call(*_args):
            return 1000

    class Canvas:
        tk = Clock()

        @staticmethod
        def after(*_args):
            return "after#next"

    face = Particle(50.0, 50.0, seed=0.5)
    logo = InteractiveLogo.__new__(InteractiveLogo)
    logo.canvas = Canvas()
    logo.particles = [face]
    logo.mouse_x = 51.0
    logo.mouse_y = 50.0
    logo.mouse_active = True
    logo._running = True
    logo._after_id = None
    logo._started_ms = 1000
    logo._trail = deque([[51.0, 50.0, 1.0]], maxlen=12)
    logo._refresh_pointer = lambda: None
    logo._update_mouse_trail = lambda: None

    max_displacement = 0.0
    for _ in range(180):
        logo._animate()
        max_displacement = max(
            max_displacement,
            math.hypot(face.x - face.home_x, face.y - face.home_y),
        )

    logo.mouse_active = False
    logo._trail.clear()
    for _ in range(120):
        logo._animate()

    assert max_displacement <= 2.0
    assert math.hypot(face.x - face.home_x, face.y - face.home_y) <= 0.1


def test_dense_fallback_bounds_visited_particles_and_uses_slower_cadence(
    monkeypatch,
) -> None:
    from a_conductor import interactive_logo as module

    class Clock:
        @staticmethod
        def call(*_args):
            return 1000

    scheduled: list[int] = []

    class Canvas:
        tk = Clock()

        @staticmethod
        def after(delay, _callback):
            scheduled.append(delay)
            return "after#next"

    faces = [
        module.Particle(20.0 + index % 80, 20.0 + index % 60, seed=index / 1400)
        for index in range(1300)
    ]
    eyes = [
        module.Particle(45.0 + index, 45.0, is_eye=True, seed=0.8)
        for index in range(6)
    ]
    visits = 0

    def count_repulsion(*_args, **_kwargs):
        nonlocal visits
        visits += 1
        return 0.0, 0.0

    monkeypatch.setattr(module, "repulsion_impulse", count_repulsion)
    logo = module.InteractiveLogo.__new__(module.InteractiveLogo)
    logo.canvas = Canvas()
    logo.particles = faces + eyes
    logo._face_particles = faces
    logo._eye_particles = eyes
    logo._dense_cursor = 0
    logo.mouse_x = -1000.0
    logo.mouse_y = -1000.0
    logo.mouse_active = True
    logo._running = True
    logo._after_id = None
    logo._started_ms = 1000
    logo._trail = deque(maxlen=12)
    logo._refresh_pointer = lambda: None
    logo._update_mouse_trail = lambda: None
    logo._trail_impulse = lambda _particle: (0.0, 0.0)

    logo._animate()

    assert 1000 <= module.MAX_IMAGE_PARTICLES <= 1300
    assert visits <= module.DENSE_FRAME_PARTICLE_LIMIT
    assert scheduled == [module.DENSE_ANIM_DELAY]
    assert module.DENSE_ANIM_DELAY > module.ANIM_DELAY


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
    assert logo._after_id is None


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

    service = DesktopControlService.open(
        tmp_path / "cc.sqlite",
        instances_root=tmp_path / "instances",
    )
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


def test_compact_brand_fallback_uses_single_raster_not_dense_ovals(root) -> None:
    from pathlib import Path

    from a_conductor.interactive_logo import InteractiveLogo

    asset = Path(__file__).resolve().parents[1] / "assets" / "logo-face.png"
    logo = InteractiveLogo(root, size=120)

    assert logo.load_image(asset) is True
    assert logo._raster_item is not None
    assert len(logo.particles) == 0
    assert len(logo.canvas.find_all()) <= 7


def test_unmapped_fallback_clears_stale_pointer_activity() -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    class Canvas:
        @staticmethod
        def winfo_ismapped() -> bool:
            return False

    logo = InteractiveLogo.__new__(InteractiveLogo)
    logo.canvas = Canvas()
    logo.mouse_active = True

    logo._refresh_pointer()

    assert logo.mouse_active is False


def test_family_raster_preserves_visible_particle_contrast_at_header_size() -> None:
    from pathlib import Path

    from a_conductor.interactive_logo import prepare_family_raster

    asset = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"
    image, _bounds = prepare_family_raster(asset, 120)
    luminance = image.convert("L")
    histogram = luminance.histogram()

    assert image.size == (120, 120)
    assert luminance.getextrema()[1] >= 240
    assert sum(histogram[100:]) >= 4_500
    assert sum(histogram[160:]) >= 1_000


def test_family_fallback_uses_one_exact_raster_and_skips_idle_writes(
    root, monkeypatch
) -> None:
    from pathlib import Path

    from a_conductor.interactive_logo import InteractiveLogo, RASTER_IDLE_DELAY

    asset = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"
    logo = InteractiveLogo(root, size=120)
    assert logo.load_image(asset) is True
    assert logo._raster_item is not None
    assert logo._raster_photo is not None
    assert logo._raster_photo.width() == 120
    assert logo._raster_photo.height() == 120
    assert len(logo.particles) == 0
    assert len(logo._raster_eye_items) == 6
    assert len(logo.canvas.find_all()) <= 7

    logo._running = True
    logo.mouse_active = False
    monkeypatch.setattr(logo, "_refresh_pointer", lambda: None)
    scheduled: list[int] = []
    monkeypatch.setattr(
        logo.canvas,
        "after",
        lambda delay, _callback: scheduled.append(delay) or "after#raster",
    )

    writes = 0
    original_coords = logo.canvas.coords

    def count_coords(*args):
        nonlocal writes
        writes += 1
        return original_coords(*args)

    monkeypatch.setattr(logo.canvas, "coords", count_coords)
    logo._animate()

    assert writes == 0
    assert scheduled == [RASTER_IDLE_DELAY]


def test_family_raster_motion_is_bounded_and_returns_without_particle_work(
    root, monkeypatch
) -> None:
    from pathlib import Path

    from a_conductor import interactive_logo as module

    asset = Path(__file__).resolve().parents[1] / "assets" / "sunday-family-particle.png"
    logo = module.InteractiveLogo(root, size=120)
    assert logo.load_image(asset) is True
    monkeypatch.setattr(
        module,
        "repulsion_impulse",
        lambda *_args, **_kwargs: pytest.fail("raster fallback iterated particles"),
    )
    monkeypatch.setattr(logo, "_refresh_pointer", lambda: None)
    monkeypatch.setattr(logo.canvas, "after", lambda *_args, **_kwargs: "after#raster")

    requested_geometry = (
        int(logo.canvas.cget("width")),
        int(logo.canvas.cget("height")),
    )
    logo._running = True
    logo.mouse_active = True
    logo.mouse_x = 1000.0
    logo.mouse_y = 60.0
    maximum_face = maximum_eye = 0.0
    for _ in range(80):
        logo._animate()
        maximum_face = max(
            maximum_face, math.hypot(logo._raster_face_x, logo._raster_face_y)
        )
        maximum_eye = max(
            maximum_eye, math.hypot(logo._raster_eye_x, logo._raster_eye_y)
        )

    logo.mouse_active = False
    for _ in range(80):
        logo._animate()

    assert maximum_face <= module.RASTER_FACE_SHIFT + 1e-9
    assert maximum_eye <= module.RASTER_EYE_SHIFT + 1e-9
    assert math.hypot(logo._raster_face_x, logo._raster_face_y) < 0.1
    assert math.hypot(logo._raster_eye_x, logo._raster_eye_y) < 0.1
    assert logo._raster_eye_visible is False
    assert requested_geometry == (
        int(logo.canvas.cget("width")),
        int(logo.canvas.cget("height")),
    )
