"""Pure Markdown -> local HTML guide transformation (WO-P1-074).

The Markdown files remain the content SSoT. This module only selects a bounded
section and renders a local HTML/CSS document in memory.
"""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from typing import Final
from urllib.parse import urlparse


GUIDE_SECTION_KEYS: Final = (
    "start",
    "setup",
    "daily",
    "add_chat",
    "terms",
    "troubleshooting",
)

_SECTION_INDEX: Final = {
    "terms": 0,
    "start": 1,
    "setup": 2,
    "daily": 3,
    "add_chat": 4,
}

_LABELS: Final = {
    "en": {
        "start": "Start Here",
        "setup": "First Setup",
        "daily": "Daily Use",
        "add_chat": "Add Chat",
        "terms": "Terms",
        "troubleshooting": "Troubleshooting",
    },
    "th": {
        "start": "เริ่มที่นี่",
        "setup": "ตั้งค่าครั้งแรก",
        "daily": "ใช้งานประจำวัน",
        "add_chat": "เพิ่มแชท",
        "terms": "คำศัพท์",
        "troubleshooting": "แก้ปัญหา",
    },
    "zh-CN": {
        "start": "从这里开始",
        "setup": "首次设置",
        "daily": "日常使用",
        "add_chat": "添加聊天",
        "terms": "术语",
        "troubleshooting": "故障排除",
    },
}

_FLOW = "ChatGPT → Tunnel → Connector → Project"

_HEADING_RE = re.compile(r"^##\s+.+$", re.MULTILINE)
_NUMERIC_8_RE = re.compile(r"^##\s+8\.\s+.+$", re.MULTILINE)
_NUMERIC_9_RE = re.compile(r"^##\s+9\.\s+.+$", re.MULTILINE)
_ALLOWED_HTML_TAGS: Final = frozenset(
    {
        "p", "h1", "h2", "h3", "h4", "ul", "ol", "li", "strong", "em",
        "code", "pre", "blockquote", "table", "thead", "tbody", "tr", "th",
        "td", "hr", "br", "a", "abbr",
    }
)
_VOID_HTML_TAGS: Final = frozenset({"hr", "br"})
_SUPPRESSED_HTML_CONTAINERS: Final = frozenset(
    {"script", "style", "iframe", "object", "video", "audio", "svg", "math"}
)


class _GuideHTMLSanitizer(HTMLParser):
    # Allowlist generated Markdown HTML without permitting resource loading.

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._suppressed: list[str] = []

    def _safe_attrs(self, tag: str, attrs: list[tuple[str, str | None]]) -> str:
        values = {name.lower(): value for name, value in attrs if value is not None}
        kept: list[tuple[str, str]] = []
        if tag == "a":
            href = values.get("href", "").strip()
            if href.startswith("#"):
                kept.append(("href", href))
            elif urlparse(href).scheme.lower() in {"http", "https"}:
                kept.append(("href", href))
            title = values.get("title")
            if title:
                kept.append(("title", title))
        elif tag == "abbr":
            title = values.get("title")
            if title:
                kept.append(("title", title))
        return "".join(
            f' {name}="{html.escape(value, quote=True)}"' for name, value in kept
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._suppressed:
            if tag in _SUPPRESSED_HTML_CONTAINERS:
                self._suppressed.append(tag)
            return
        if tag in _SUPPRESSED_HTML_CONTAINERS:
            self._suppressed.append(tag)
            return
        if tag not in _ALLOWED_HTML_TAGS:
            return
        self.parts.append(f"<{tag}{self._safe_attrs(tag, attrs)}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if self._suppressed or tag not in _ALLOWED_HTML_TAGS:
            return
        self.parts.append(f"<{tag}{self._safe_attrs(tag, attrs)}>")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._suppressed:
            if tag == self._suppressed[-1]:
                self._suppressed.pop()
            return
        if tag in _ALLOWED_HTML_TAGS and tag not in _VOID_HTML_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._suppressed:
            self.parts.append(html.escape(data))


def guide_section_labels(language: str) -> dict[str, str]:
    """Return localized navigation labels, falling back to English."""

    base = _LABELS.get(language, _LABELS["en"])
    return {key: base[key] for key in GUIDE_SECTION_KEYS}


def _heading_spans(markdown_text: str) -> list[re.Match[str]]:
    return list(_HEADING_RE.finditer(markdown_text))


def _slice_heading(markdown_text: str, headings: list[re.Match[str]], index: int) -> str:
    if index >= len(headings):
        return ""
    start = headings[index].start()
    end = headings[index + 1].start() if index + 1 < len(headings) else len(markdown_text)
    return markdown_text[start:end].strip()


def extract_guide_section(markdown_text: str, section_key: str) -> str:
    """Extract one stable beginner section from the existing guide structure."""

    if section_key not in GUIDE_SECTION_KEYS:
        raise ValueError(f"unknown guide section: {section_key}")
    headings = _heading_spans(markdown_text)
    if section_key in _SECTION_INDEX:
        return _slice_heading(markdown_text, headings, _SECTION_INDEX[section_key])

    # Troubleshooting is a stable numbered section in both TH/EN guide sources.
    match = _NUMERIC_8_RE.search(markdown_text)
    if match is None:
        return ""
    next_match = _NUMERIC_9_RE.search(markdown_text, match.end())
    end = next_match.start() if next_match is not None else len(markdown_text)
    return markdown_text[match.start():end].strip()


def _sanitize_generated_html(value: str) -> str:
    """Allow text/structure only; resource-capable HTML is removed fail-closed."""

    sanitizer = _GuideHTMLSanitizer()
    sanitizer.feed(value)
    sanitizer.close()
    return "".join(sanitizer.parts)


def render_guide_html(markdown_text: str, *, section_key: str, language: str) -> str:
    """Render one guide section into a self-contained local HTML document."""

    section = extract_guide_section(markdown_text, section_key)
    if not section:
        raise ValueError(f"guide section has no content: {section_key}")

    try:
        import markdown
    except ImportError as exc:  # runtime fallback is handled by desktop_ui
        raise RuntimeError("Python-Markdown is unavailable") from exc

    rendered = markdown.markdown(
        section,
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html",
    )
    rendered = _sanitize_generated_html(rendered)
    labels = guide_section_labels(language)
    step = GUIDE_SECTION_KEYS.index(section_key) + 1
    label = labels[section_key]

    flow = ""
    if section_key == "start":
        flow = (
            '<div class="flow">'
            '<span title="The AI conversation">ChatGPT</span>'
            '<b>→</b><span title="Secure transport">Tunnel</span>'
            '<b>→</b><span title="Local Serena/MCP runtime">Connector</span>'
            '<b>→</b><span title="The folder being worked on">Project</span>'
            "</div>"
        )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ background:#0d1117; color:#d8dee6; font-family:Segoe UI,Arial,sans-serif;
       margin:0; padding:18px 22px; line-height:1.55; }}
h1,h2,h3 {{ color:#f0f3f6; margin-top:18px; }}
h2 {{ border-bottom:1px solid #242b35; padding-bottom:7px; }}
code,pre {{ font-family:Cascadia Mono,Consolas,monospace; background:#080b0f; color:#d8dee6; }}
pre {{ border:1px solid #242b35; padding:10px; overflow:auto; }}
table {{ border-collapse:collapse; width:100%; }}
th,td {{ border:1px solid #242b35; padding:7px 9px; text-align:left; vertical-align:top; }}
th {{ background:#11161d; color:#f0f3f6; }}
a {{ color:#78a9e6; }}
.progress {{ color:#7d8794; font-family:Cascadia Mono,Consolas,monospace; font-size:12px;
             margin-bottom:8px; }}
.section-title {{ color:#f0f3f6; font-weight:bold; font-size:18px; margin-bottom:10px; }}
.flow {{ border:1px solid #3a4554; background:#11161d; padding:14px 12px; margin:12px 0 18px 0;
         text-align:center; font-family:Cascadia Mono,Consolas,monospace; font-size:15px; }}
.flow span {{ display:inline-block; border:1px solid #3a4554; padding:5px 8px; margin:3px; }}
.flow b {{ color:#7d8794; margin:0 4px; }}
</style>
</head>
<body>
<div class="progress">A-Sunday Conductor · Step {step} / 6</div>
<div class="section-title">{html.escape(label)}</div>
{flow}
{rendered}
</body>
</html>"""
