# WO-P1-074 — Interactive embedded HTML Guide

Status: IN_PROGRESS
Owner: GPT-5.6 Sol
Branch: `feat/interactive-html-guide`
Depends on: WO-P1-073 / PR #103 (stacked until P4 merges)

## Objective

Replace the plain Markdown-only Guide surface with a beginner-friendly embedded HTML/CSS
Guide while keeping the existing Markdown files as the single content source of truth.

## Upstream / reuse decision

Classification: EXTEND.

- Keep Tk/Ttk application architecture and existing singleton Guide `Toplevel`.
- Use TkinterWeb `HtmlFrame` as the primary local renderer.
- Use Python-Markdown to transform existing Markdown to HTML in memory.
- Do not add pywebview/Chromium/Electron.
- Do not require JavaScript. Guide interaction must work with HTML/CSS + Python/Tk callbacks.
- Preserve the existing plain `tk.Text` Markdown viewer as a fail-safe fallback.

Research pinned for implementation review (2026-08-26):
- TkinterWeb 4.25.3 (MIT), current PyPI release.
- Python-Markdown 3.10.3 (BSD-3-Clause), current PyPI release.
- PyInstaller bundle must collect TkinterWeb/Tkhtml runtime packages explicitly.

## User outcome

A first-time AI-tool user can open Guide and understand:
`ChatGPT -> Tunnel -> Connector -> Project`,
first setup, daily use, adding a chat, terms, and troubleshooting without leaving the app.

## Content / UX contract

- `docs/USER-GUIDE.md` and `docs/USER-GUIDE-EN.md` remain content SSoT.
- HTML is generated in memory; no second hand-maintained HTML prose file.
- Local TOC/section buttons: Start Here, First Setup, Daily Use, Add Chat, Terms, Troubleshooting.
- Show a clear `Step n / 6` marker for the selected section.
- Start Here includes a prominent plain-language flow.
- Glossary terms may use native HTML title/abbr tooltips; no JS requirement.
- External URLs open only after exiplicit user click.
- No remote stylesheet, font, image, script, analytics, or network request in Guide rendering.
- Existing External/Open File button remains available.
- Existing singleton behavior remains: repeat Guide click lifts/focuses the same window.
- No continuous animation; reduced-motion is effectively the default.

## Runtime / failure contract

- Primary renderer: TkinterWeb HtmlFrame.
- `javascript_enabled=False`.
- `messages_enabled=False`.
- If import/initialization/rendering fails, fall back to the existing read-only Markdown `tk.Text`.
- Fallback must still preserve clickable external URL.
- Guide failure must never crash the main application.

## Packaging contract

- Runtime deps recorded in `pyproject.toml`.
- Portable PyInstaller build explicitly collects:
  - `tkinterweb`
  - `tkinterweb_tkhtml`
  - `tkinterweb_tkhtml_extras`
- Setup ships the already-built Portable payload plus Markdown guides.
- THIRD-PARTY-NOTICES includes TkinterWeb/Tkhtml/Tkhtml-Extras and Python-Markdown.

## Test seams

1. Pure section extraction works from the current EN and TH Markdown structures.
2. HTML render contains source content, progress marker, local shell, and no `<script>`/remote assets.
3. Unknown section fails deterministically.
4. Primary Guide path constructs HtmlFrame and loads HTML.
5. Renderer failure falls back to `tk.Text`.
6. Singleton Guide remains one window.
7. External link callback rejects/ignores non-http(s) as external navigation.
8. Build contract collects all TkinterWeb runtime packages.
9. Frozen/installed acceptance opens Guide from the exact release artifact.

## Acceptance

- [ ] RED test evidence recorded.
- [ ] Pure guide tests green.
- [ ] GUI primary + fallback tests green.
- [ ] Existing Guide/singleton tests reconciled to new accepted design.
- [ ] Real TkinterWeb render tested in an isolated environment.
- [ ] Portable build/frozen Guide smoke green.
- [ ] `git diff --check` + py_compile green.
- [ ] Remote PR diff audited.
- [ ] Windows + Ubuntu + macOS CI green before merge.
- [ ] Post-merge fetch/reconcile and branch/worktree cleanup.
