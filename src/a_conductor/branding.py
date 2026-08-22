"""Single source of truth for the user-facing product display name."""

from __future__ import annotations

# Display name used in window titles, the installer, Start Menu, and docs.
# Chosen 2026-08-22: "A" honors the user's AI co-developer, "Sunday" honors
# the user's son (น้องซันเดย์) and matches the family company name, and
# "Conductor" keeps the project's founding codename. The internal package
# (a_conductor), the repo name (A-Wiki-Conductor), and the on-disk data
# directory are unchanged so upgrades preserve existing user data.
APP_NAME = "A-Sunday Conductor"

# Product version. Kept in sync with pyproject.toml by
# tests/test_build_installer.py::test_pyproject_version_matches_branding.
APP_VERSION = "0.2.4"
