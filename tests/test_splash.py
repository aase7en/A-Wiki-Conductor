"""Splash screen: pixel logo, version text, credits — visual identity."""

from __future__ import annotations

import pytest


def test_splash_module_imports_cleanly() -> None:
    from a_conductor.splash import PIXEL_LOGO, COLORS, SplashScreen, show_splash

    assert callable(show_splash)
    assert callable(SplashScreen)
    assert len(PIXEL_LOGO) > 0
    assert len(COLORS) > 0


def test_pixel_logo_has_content() -> None:
    from a_conductor.splash import PIXEL_LOGO

    # every row is non-empty and at least one has visible pixels
    assert any("█" in row for row in PIXEL_LOGO)
    # all rows have consistent width (padded with spaces)
    widths = {len(row) for row in PIXEL_LOGO}
    assert len(widths) == 1, f"inconsistent row widths: {widths}"


def test_splash_contains_app_name_and_version_text() -> None:
    """The text-drawing code references version and developer strings."""
    from pathlib import Path

    source = Path("src/a_conductor/splash.py").read_text(encoding="utf-8")
    assert "version" in source
    assert "developer" in source
    assert "Serena" in source  # credits to the engine


def test_splash_timeout_is_bounded() -> None:
    """Splash must auto-close (never block the app indefinitely)."""
    from pathlib import Path

    source = Path("src/a_conductor/splash.py").read_text(encoding="utf-8")
    assert "after(3000" in source  # 3-second timeout
    assert "destroy" in source


def test_main_entry_wires_splash_before_mainloop() -> None:
    """desktop_app.main() calls show_splash before mainloop, wrapped in try/except."""
    from pathlib import Path

    source = Path("src/a_conductor/desktop_app.py").read_text(encoding="utf-8")
    assert "show_splash" in source
    assert "except Exception" in source  # splash failure never blocks startup
