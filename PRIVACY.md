# Privacy Policy

A-Sunday Conductor is a **local desktop application**. It:

- Does **not** collect, store, or transmit any personal data
- Does **not** include telemetry or analytics
- Does **not** require an account
- Stores all data locally on your machine (`%LOCALAPPDATA%\A-Conductor\`)

The only network connections the app can make:

1. **GitHub API** (optional, when you press "Check for Updates" or
   "Check Engine Update") — requests to `api.github.com` /
   `raw.githubusercontent.com` to check the latest release or engine
   version. No data is sent beyond the HTTP request itself.
2. **Setup Wizard downloads** (only when you choose to install) —
   downloads installers from `github.com/astral-sh/uv` releases,
   `python.org`, `nodejs.org`, and the Serena / tunnel-client GitHub
   releases, then runs them locally to set up the engine. Nothing is
   uploaded; these downloads happen only with your explicit action.
3. **External links** — the Guide, Donate, and Sponsor buttons can open
   pages in your browser (GitHub, OpenAI docs). The app itself sends
   nothing to those pages.
4. **GitHub push/pull** (developer mode) — standard Git operations if you
   cloned the repository.

If you use the Serena engine through connectors, those connections are
between your local Serena instances and OpenAI's tunnel service — governed
by OpenAI's terms, not this app.

---

*Last updated: 2026-08-25*
