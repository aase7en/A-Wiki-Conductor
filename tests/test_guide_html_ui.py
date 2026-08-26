"""WO-P1-074 — embedded Guide primary/fallback UI tests."""

from __future__ import annotations

import tkinter as tk

from a_conductor.desktop_ui import AConductorDesktopApp
from tests.test_desktop_ui import FakeService, ImmediateExecutor, root, sample_snapshot


class FakeHtmlFrame(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master)
        self.options = kwargs
        self.loaded_html: list[str] = []

    def load_html(self, html_source, base_url=None, fragment=None):
        self.loaded_html.append(html_source)


def _descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from _descendants(child)


def test_guide_uses_injected_html_frame_with_javascript_off(root) -> None:
    made: list[FakeHtmlFrame] = []

    def factory(master, **kwargs):
        frame = FakeHtmlFrame(master, **kwargs)
        made.append(frame)
        return frame

    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        guide_html_frame_factory=factory,
    )

    window = app.open_guide()

    assert window is not None
    assert len(made) == 1
    frame = made[0]
    assert frame.options["javascript_enabled"] is False
    assert frame.options["messages_enabled"] is False
    assert frame.options["images_enabled"] is False
    assert frame.loaded_html
    assert "Step 1 / 6" in frame.loaded_html[-1]
    assert "ChatGPT" in frame.loaded_html[-1]
    window.destroy()


def test_guide_renderer_failure_falls_back_to_markdown_text(root) -> None:
    def failing_factory(master, **kwargs):
        raise RuntimeError("renderer unavailable")

    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        guide_html_frame_factory=failing_factory,
    )

    window = app.open_guide()

    assert window is not None
    text_widgets = [w for w in _descendants(window) if isinstance(w, tk.Text)]
    assert len(text_widgets) == 1
    assert "A-Sunday Conductor" in text_widgets[0].get("1.0", "end")
    window.destroy()


def test_guide_singleton_reuses_primary_window(root) -> None:
    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        guide_html_frame_factory=lambda master, **kwargs: FakeHtmlFrame(master, **kwargs),
     )

    first = app.open_guide()
    second = app.open_guide()

    assert first is second
    first.destroy()


def test_guide_external_url_opener_is_http_only(root) -> None:
    opened: list[str] = []
    app = AConductorDesktopApp(
        root,
        service=FakeService(sample_snapshot()),
        background_executor=ImmediateExecutor(),
        guide_url_opener=opened.append,
     )

    app._open_guide_web_link("https://example.com/help")
    app._open_guide_web_link("http://example.com/plain")
    app._open_guide_web_link("file:///C:/secret.txt")
    app._open_guide_web_link("javascript:alert(1)")
    app._open_guide_web_link("#local")

    assert opened == ["https://example.com/help", "http://example.com/plain"]
