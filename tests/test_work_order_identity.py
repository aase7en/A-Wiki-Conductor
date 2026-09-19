"""Deterministic work-order identity guard (WO-P1-381 / Issue #381).

Policy enforced offline, with no GitHub API access:

- Each canonical ``docs/work-orders/WO-P1-*.md`` numeric id is used by at
  most one tracked file (revision-suffixed tokens such as ``028R1`` are
  distinct canonical identities).
- Files declaring ``Identity schema: GITHUB_ISSUE_V1`` must carry exactly
  one ``Issue: #N`` line whose N equals the filename numeric id.
- Every plain numeric work order with id >= 381 must carry exactly one
  ``Issue: #N`` line matching its id, even when the marker line is
  accidentally omitted (missing and duplicate Issue lines are both
  violations).
- Legacy/revision token files below the threshold are untouched unless
  they declare the marker.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK_ORDERS_DIR = REPO_ROOT / "docs" / "work-orders"

IDENTITY_MARKER = "Identity schema: GITHUB_ISSUE_V1"
GITHUB_BACKED_MIN_N = 381

FILENAME_TOKEN_RE = re.compile(r"^WO-P1-(?P<token>[0-9A-Za-z]+)(?:-.*)?\.md$")
LEADING_DIGITS_RE = re.compile(r"^(?P<digits>\d+)")
ISSUE_LINE_RE = re.compile(r"^Issue:[ \t]*#(?P<num>\d+)[ \t]*$", re.MULTILINE)


def identity_token(filename: str) -> str | None:
    match = FILENAME_TOKEN_RE.match(filename)
    if match is None:
        return None
    return match.group("token")


def canonical_key(token: str) -> tuple[str, object]:
    if token.isdigit():
        return ("numeric", int(token))
    return ("token", token.lower())


def leading_numeric_id(token: str) -> int | None:
    match = LEADING_DIGITS_RE.match(token)
    if match is None:
        return None
    return int(match.group("digits"))


def issue_numbers(content: str) -> list[int]:
    return [int(m.group("num")) for m in ISSUE_LINE_RE.finditer(content)]


def check_work_order_identities(files: list[tuple[str, str]]) -> list[str]:
    violations: list[str] = []
    seen: dict[tuple[str, object], str] = {}
    for filename, content in sorted(files):
        token = identity_token(filename)
        if token is None:
            continue
        key = canonical_key(token)
        if key in seen:
            label = f"WO-P1-{token}"
            violations.append(
                f"duplicate canonical work-order id {label}: "
                f"{seen[key]} and {filename}"
            )
        else:
            seen[key] = filename
        issues = issue_numbers(content)
        if token.isdigit():
            numeric_n = int(token)
            if numeric_n >= GITHUB_BACKED_MIN_N:
                if len(issues) != 1:
                    violations.append(
                        f"{filename}: GitHub-backed work-order id >= "
                        f"{GITHUB_BACKED_MIN_N} requires exactly one "
                        f"'Issue: #{numeric_n}' line, found {len(issues)}"
                    )
                elif issues[0] != numeric_n:
                    violations.append(
                        f"{filename}: GitHub-backed work-order id >= "
                        f"{GITHUB_BACKED_MIN_N} requires Issue number == "
                        f"{numeric_n}, found {sorted(set(issues))}"
                    )
            if IDENTITY_MARKER in content:
                if len(issues) != 1:
                    violations.append(
                        f"{filename}: {IDENTITY_MARKER} requires exactly one "
                        f"'Issue: #{numeric_n}' line, found {len(issues)}"
                    )
                elif issues[0] != numeric_n:
                    violations.append(
                        f"{filename}: {IDENTITY_MARKER} requires Issue number "
                        f"== {numeric_n}, found {sorted(set(issues))}"
                    )
        else:
            if IDENTITY_MARKER in content:
                violations.append(
                    f"{filename}: {IDENTITY_MARKER} requires a purely numeric "
                    f"canonical id, got token {token!r}"
                )
            github_n = leading_numeric_id(token)
            if github_n is not None and github_n >= GITHUB_BACKED_MIN_N and issues:
                if any(n != github_n for n in issues):
                    violations.append(
                        f"{filename}: GitHub-backed work-order id >= "
                        f"{GITHUB_BACKED_MIN_N} requires Issue number == "
                        f"{github_n}, found {sorted(set(issues))}"
                    )
    return violations


def iter_directory_work_orders(directory: Path) -> list[tuple[str, str]]:
    files: list[tuple[str, str]] = []
    if not directory.is_dir():
        return files
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix != ".md":
            continue
        if identity_token(path.name) is None:
            continue
        files.append((path.name, path.read_text(encoding="utf-8")))
    return files


def iter_repo_work_orders() -> list[tuple[str, str]]:
    output = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            "docs/work-orders",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    files: list[tuple[str, str]] = []
    for line in output.splitlines():
        rel = line.strip()
        if not rel:
            continue
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        if identity_token(path.name) is None:
            continue
        files.append((path.name, path.read_text(encoding="utf-8")))
    return files


def write_work_order(directory: Path, filename: str, content: str) -> None:
    (directory / filename).write_text(content, encoding="utf-8")


def test_repo_work_order_identities_are_unique_and_consistent() -> None:
    violations = check_work_order_identities(iter_repo_work_orders())
    assert violations == [], "work-order identity violations:\n" + "\n".join(violations)


def test_clean_directory_passes(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-410-alpha.md",
        "# WO-P1-410 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #410\n",
    )
    write_work_order(
        tmp_path,
        "WO-P1-411-beta.md",
        "# WO-P1-411 — beta\n\nIssue: #411\n",
    )
    write_work_order(
        tmp_path,
        "WO-P1-028R1-regression.md",
        "# WO-P1-028R1 — regression\n\nIssue: #99\n",
    )
    write_work_order(tmp_path, "README.md", "# not a work order\nIssue: #1\n")
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_duplicate_numeric_id_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-412-alpha.md",
        "# WO-P1-412 — alpha\n\nIssue: #412\n",
    )
    write_work_order(
        tmp_path,
        "WO-P1-412-beta.md",
        "# WO-P1-412 — beta\n\nIssue: #412\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "duplicate canonical work-order id WO-P1-412" in violations[0]
    assert "WO-P1-412-alpha.md" in violations[0]
    assert "WO-P1-412-beta.md" in violations[0]


def test_zero_padded_duplicate_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-413-alpha.md",
        "# WO-P1-413 — alpha\n\nIssue: #413\n",
    )
    write_work_order(
        tmp_path,
        "WO-P1-0413-beta.md",
        "# WO-P1-0413 — beta\n\nIssue: #413\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "duplicate canonical work-order id" in violations[0]
    assert "WO-P1-0413-beta.md" in violations[0]
    assert "WO-P1-413-alpha.md" in violations[0]


def test_marker_issue_mismatch_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-414-alpha.md",
        "# WO-P1-414 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #415\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 2
    assert "GitHub-backed" in violations[0]
    assert "requires Issue number == 414" in violations[0]
    assert IDENTITY_MARKER in violations[1]
    assert "requires Issue number == 414" in violations[1]


def test_marker_requires_issue_line(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-416-alpha.md",
        "# WO-P1-416 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 2
    assert "GitHub-backed" in violations[0]
    assert "exactly one 'Issue: #416' line" in violations[0]
    assert IDENTITY_MARKER in violations[1]
    assert "exactly one 'Issue: #416' line" in violations[1]


def test_backstop_issue_mismatch_without_marker_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-417-alpha.md",
        "# WO-P1-417 — alpha\n\nIssue: #418\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "GitHub-backed" in violations[0]
    assert "Issue number == 417" in violations[0]


def test_legacy_issue_mismatch_below_threshold_is_allowed(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-260-legacy.md",
        "# WO-P1-260 — legacy\n\nIssue: #348\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_above_threshold_without_marker_or_issue_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-418-alpha.md",
        "# WO-P1-418 — alpha\n\nBody with no identity lines.\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "WO-P1-418-alpha.md" in violations[0]
    assert "exactly one 'Issue: #418' line" in violations[0]


def test_above_threshold_duplicate_issue_lines_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-419-alpha.md",
        "# WO-P1-419 — alpha\n\nIssue: #419\nIssue: #419\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "WO-P1-419-alpha.md" in violations[0]
    assert "exactly one 'Issue: #419' line" in violations[0]
    assert "found 2" in violations[0]


def test_canonical_marker_below_threshold_requires_issue(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-350-alpha.md",
        "# WO-P1-350 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "GITHUB_ISSUE_V1" in violations[0]
    assert "exactly one 'Issue: #350' line" in violations[0]


def test_canonical_marker_issue_mismatch_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-351-alpha.md",
        "# WO-P1-351 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #352\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "GITHUB_ISSUE_V1" in violations[0]
    assert "requires Issue number == 351" in violations[0]
