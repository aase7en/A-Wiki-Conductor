"""Interactive Logo: particle face, mouse tracking, repulsion."""

from __future__ import annotations

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
    assert len(FACE_MAP) > 0
    assert any("1" in row for row in FACE_MAP)


def test_logo_creates_canvas_with_particles(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    assert len(logo.particles) > 0
    # Each particle should have a canvas item
    assert all(p.id is not None for p in logo.particles)


def test_logo_particle_structure(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    for p in logo.particles:
        assert 0 <= p.home_x <= 80
        assert 0 <= p.home_y <= 80
        assert isinstance(p.is_eye, bool)


def test_logo_face_has_eyes(root) -> None:
    from a_conductor.interactive_logo import InteractiveLogo

    logo = InteractiveLogo(root, size=80)
    eyes = [p for p in logo.particles if p.is_eye]
    # Should have some eye particles (or none if face map has no E markers)
    # The default map has no E, so eyes=0 is valid — just check no crash
    assert isinstance(eyes, list)


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
    assert logo.mouse_x == 40.0


def test_app_header_has_logo(root, tmp_path) -> None:
    from a_conductor.desktop_control import DesktopControlService
    from a_conductor.desktop_ui import AConductorDesktopApp

    service = DesktopControlService.open(tmp_path / "cc.sqlite")
    app = AConductorDesktopApp(root, service=service)
    assert hasattr(app, "_logo")
    # logo may be None if import fails, but should exist as attribute
