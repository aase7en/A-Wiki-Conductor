"""WO-P1-074 — pure interactive Guide HTML generation tests."""

from pathlib import Path

import pytest

from a_conductor.guide_html import (
    GUIDE_SECTION_KEYS,
    extract_guide_section,
    render_guide_html,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("filename", "language"),
    [
        ("USER-GUIDE-EN.md", "en"),
        ("USER-GUIDE.md", "th"),
    ],
)
def test_all_six_sections_extract_from_markdown_source(filename: str, language: str) -> None:
    source = (ROOT / "docs" / filename).read_text(encoding="utf-8")
    assert GUIDE_SECTION_KEYS == (
        "start",
        "setup",
        "daily",
        "add_chat",
        "terms",
        "troubleshooting",
    )
    for key in GUIDE_SECTION_KEYS:
        section = extract_guide_section(source, key)
        assert section.strip(), (language, key)
        assert len(section) < len(source) or key == "start"


def test_render_guide_html_is_local_no_script_and_has_progress() -> None:
    source = (ROOT / "docs" / "USER-GUIDE-EN.md").read_text(encoding="utf-8")

    html = render_guide_html(source, section_key="daily", language="en")

    assert "Step 3 / 6" in html
    assert "Daily" in html or "Everyday" in html
    assert "A-Sunday Conductor" in html
    assert "<script" not in html.lower()
    assert "javascript:" not in html.lower()
    assert "http://fonts." not in html.lower()
    assert "https://fonts." not in html.lower()
    assert "<link " not in html.lower()


def test_render_guide_html_removes_active_and_remote_resource_tags() -> None:
    source = '''## Glossary
terms
## How everything connects
flow
## First-time setup (5 steps)
setup
## Daily use (3 steps)
<iframe src="https://evil.example/x"></iframe>
<embed src="https://evil.example/y">
<object data="https://evil.example/z"></object>
<video src="https://evil.example/v"></video>
<audio src="https://evil.example/a"></audio>
<style>@import url(https://evil.example/s.css);</style>
<script>alert(1)</script>
'''
    html = render_guide_html(source, section_key="daily", language="en")
    lowered = html.lower()
    for tag in ("<iframe", "<embed", "<object", "<video", "<audio", "<script"):
        assert tag not in lowered
    assert "evil.example" not in lowered
    assert "@import" not in lowered



def test_guide_html_allowlist_drops_unsafe_attrs_and_svg_resources() -> None:
    source = '''## Glossary
terms
## How everything connects
flow
## First-time setup (5 steps)
setup
## Daily use (3 steps)
<img src="https://evil.example/i.png" onerror="alert(2)">
<svg><a href="https://evil.example/svg">remote-svg</a></svg>
<a href="javascript:alert(3)" style="background:url(https://evil.example/bg)">unsafe-link</a>
<a href="https://safe.example/help" style="background:url(https://evil.example/bg2)">safe-link</a>
'''
    rendered = render_guide_html(source, section_key="daily", language="en").lower()
    assert "<img" not in rendered
    assert "<svg" not in rendered
    assert "javascript:" not in rendered
    assert "style=" not in rendered
    assert "evil.example" not in rendered
    assert 'href="https://safe.example/help"' in rendered

def test_start_here_contains_plain_connection_flow() -> None:
    source = (ROOT / "docs" / "USER-GUIDE-EN.md").read_text(encoding="utf-8")

    html = render_guide_html(source, section_key="start", language="en")

    assert "ChatGPT" in html
    assert "Tunnel" in html
    assert "Connector" in html
    assert "Project" in html
    assert "Step 1 / 6" in html


def test_unknown_guide_section_is_rejected() -> None:
    source = (ROOT / "docs" / "USER-GUIDE-EN.md").read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="unknown guide section"):
        extract_guide_section(source, "not-real")

def test_user_guides_match_live_execution_slot_model() -> None:
    for name in ("USER-GUIDE.md", "USER-GUIDE-EN.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert "AI EXECUTION SLOTS" in text, name
        assert "BOUND PROJECT" in text, name
        assert "ACTIVE PROJECT" in text, name
        assert "[DRIFT]" in text, name
