"""Deterministic work-order identity guard (WO-P1-381 / Issue #381,
hardened by WO-P1-386 / Issue #386).

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
- Frozen legacy exception set (WO-P1-386): only filenames listed in
  ``tests/fixtures/work_order_identity/legacy_identity_filenames.txt``
  may keep legacy/non-current identity shapes (non-pure-numeric tokens,
  or purely numeric ids < 381). Any NEW such filename is a violation
  even when it carries a matching marker and Issue line. The fixture is
  a frozen regression exception set, not task/claim authority; changing
  it requires its own explicit work order.
- Any Markdown file in ``docs/work-orders`` whose name begins with
  ``WO-P1-`` but does not match the canonical filename grammar is a
  deterministic malformed-filename violation (never silently skipped).
- ``Identity schema:`` and ``Issue:`` lines inside fenced code blocks
  (backtick or tilde fences, 0-3 leading spaces, >= 3 fence chars,
  closing fence of the same char and length >= opener, unclosed fence
  hides the remainder) are examples only and never count as authority.
  Outside fences both markers are recognized as exact whole lines, not
  arbitrary substrings.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORK_ORDERS_DIR = REPO_ROOT / "docs" / "work-orders"
LEGACY_FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "work_order_identity" / "legacy_identity_filenames.txt"
)

IDENTITY_MARKER = "Identity schema: GITHUB_ISSUE_V1"
GITHUB_BACKED_MIN_N = 381

FILENAME_TOKEN_RE = re.compile(r"^WO-P1-(?P<token>[0-9A-Za-z]+)(?:-.*)?\.md$")
LEADING_DIGITS_RE = re.compile(r"^(?P<digits>\d+)")
ISSUE_LINE_RE = re.compile(r"^Issue:[ \t]*#(?P<num>\d+)[ \t]*$", re.MULTILINE)
MARKER_LINE_RE = re.compile(r"^Identity schema: GITHUB_ISSUE_V1[ \t]*$", re.MULTILINE)
FENCE_LINE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")


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


def strip_fenced_blocks(content: str) -> str:
    """Drop lines inside fenced code blocks (bounded scanner, WO-P1-386).

    - backtick or tilde fences;
    - opening fence: 0-3 leading spaces and >= 3 identical fence chars;
    - closing fence: same char and length >= opener;
    - an unclosed fence hides the remainder of the document.
    """
    visible: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    for line in content.splitlines():
        match = FENCE_LINE_RE.match(line)
        if fence_char is None:
            if match is None:
                visible.append(line)
            else:
                fence_char = match.group("fence")[0]
                fence_len = len(match.group("fence"))
        elif (
            match is not None
            and match.group("fence")[0] == fence_char
            and len(match.group("fence")) >= fence_len
        ):
            fence_char = None
    return "\n".join(visible)


def has_identity_marker(visible_content: str) -> bool:
    return MARKER_LINE_RE.search(visible_content) is not None


def check_work_order_identities(
    files: list[tuple[str, str]],
    legacy_filenames: frozenset[str] | set[str] = frozenset(),
) -> list[str]:
    violations: list[str] = []
    seen: dict[tuple[str, object], str] = {}
    for filename, content in sorted(files):
        if not filename.startswith("WO-P1-"):
            continue
        token = identity_token(filename)
        if token is None:
            violations.append(
                f"{filename}: malformed 'WO-P1-' work-order filename does not "
                f"match the canonical grammar 'WO-P1-<token>[-slug].md'"
            )
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
        visible = strip_fenced_blocks(content)
        issues = issue_numbers(visible)
        marker = has_identity_marker(visible)
        legacy_shape = (not token.isdigit()) or int(token) < GITHUB_BACKED_MIN_N
        if legacy_shape and filename not in legacy_filenames:
            violations.append(
                f"{filename}: legacy-shaped work-order identity is not in the "
                f"frozen legacy exception set "
                f"(tests/fixtures/work_order_identity/legacy_identity_filenames.txt)"
            )
            continue
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
            if marker:
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
            if marker:
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
        if not path.name.startswith("WO-P1-"):
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
        if not path.name.startswith("WO-P1-") or path.suffix != ".md":
            continue
        files.append((path.name, path.read_text(encoding="utf-8")))
    return files


def write_work_order(directory: Path, filename: str, content: str) -> None:
    (directory / filename).write_text(content, encoding="utf-8")


def test_repo_work_order_identities_are_unique_and_consistent() -> None:
    violations = check_work_order_identities(
        iter_repo_work_orders(), legacy_filenames=load_legacy_fixture()
    )
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
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-028R1-regression.md"},
    )
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
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-260-legacy.md"},
    )
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
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-350-alpha.md"},
    )
    assert len(violations) == 1
    assert "GITHUB_ISSUE_V1" in violations[0]
    assert "exactly one 'Issue: #350' line" in violations[0]


def test_canonical_marker_issue_mismatch_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-351-alpha.md",
        "# WO-P1-351 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #352\n",
    )
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-351-alpha.md"},
    )
    assert len(violations) == 1
    assert "GITHUB_ISSUE_V1" in violations[0]
    assert "requires Issue number == 351" in violations[0]


# ---------------------------------------------------------------------------
# WO-P1-386 — frozen legacy exception set, malformed filenames, fence-aware
# authority parsing, revision-token policy.
# ---------------------------------------------------------------------------


def load_legacy_fixture() -> frozenset[str]:
    text = LEGACY_FIXTURE_PATH.read_text(encoding="utf-8")
    return frozenset(line for line in text.splitlines() if line)


def is_legacy_exception_filename(filename: str) -> bool:
    token = identity_token(filename)
    if token is None:
        return False
    if not token.isdigit():
        return True
    return int(token) < GITHUB_BACKED_MIN_N


def test_legacy_fixture_is_sorted_unique_and_newline_terminated() -> None:
    text = LEGACY_FIXTURE_PATH.read_bytes().decode("utf-8")
    assert text.endswith("\n")
    lines = text.splitlines()
    assert lines == sorted(lines)
    assert len(lines) == len(set(lines))
    assert all(lines)


def test_legacy_fixture_matches_current_corpus_legacy_set() -> None:
    corpus_legacy = {
        name for name, _content in iter_repo_work_orders() if is_legacy_exception_filename(name)
    }
    assert set(load_legacy_fixture()) == corpus_legacy


def test_legacy_fixture_entries_satisfy_legacy_predicate() -> None:
    for name in load_legacy_fixture():
        assert is_legacy_exception_filename(name), name


def test_legacy_fixture_has_no_github_backed_numeric_ids() -> None:
    for name in load_legacy_fixture():
        token = identity_token(name)
        assert token is not None, name
        assert not (token.isdigit() and int(token) >= GITHUB_BACKED_MIN_N), name


def test_new_low_numeric_id_with_matching_issue_and_marker_is_rejected(
    tmp_path: Path,
) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-350-synthetic.md",
        "# WO-P1-350 — synthetic\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #350\n",
    )
    write_work_order(
        tmp_path,
        "WO-P1-370-synthetic.md",
        "# WO-P1-370 — synthetic\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #370\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 2
    for filename in ("WO-P1-350-synthetic.md", "WO-P1-370-synthetic.md"):
        assert any(
            filename in v and "not in the frozen legacy exception set" in v
            for v in violations
        )


def test_legacy_listed_low_numeric_id_keeps_existing_legacy_rules(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-350-synthetic.md",
        "# WO-P1-350 — synthetic\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #350\n",
    )
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-350-synthetic.md"},
    )
    assert violations == []


def test_new_revision_token_with_matching_issue_is_rejected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-420R1-hotfix.md",
        "# WO-P1-420R1 — hotfix\n\nIssue: #420\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "WO-P1-420R1-hotfix.md" in violations[0]
    assert "not in the frozen legacy exception set" in violations[0]


def test_legacy_listed_revision_token_keeps_prior_legacy_behavior(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-028R1-old.md",
        "# WO-P1-028R1 — old regression\n\nIssue: #28\n",
    )
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-028R1-old.md"},
    )
    assert violations == []


def test_legacy_listed_revision_token_declaring_marker_still_violates(
    tmp_path: Path,
) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-028R1-old.md",
        "# WO-P1-028R1 — old regression\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #28\n",
    )
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-028R1-old.md"},
    )
    assert len(violations) == 1
    assert "GITHUB_ISSUE_V1" in violations[0]
    assert "purely numeric" in violations[0]


def test_malformed_wo_prefix_filenames_are_detected(tmp_path: Path) -> None:
    malformed = [
        "WO-P1--missing-token.md",
        "WO-P1-420_bad.md",
        "WO-P1-420.md.extra.md",
    ]
    for name in malformed:
        assert identity_token(name) is None, name
        assert name.startswith("WO-P1-") and name.endswith(".md"), name
        write_work_order(tmp_path, name, "# malformed candidate\n")
    write_work_order(tmp_path, "README.md", "# not a work order\nIssue: #1\n")
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 3
    for name in malformed:
        assert any(name in v and "malformed" in v for v in violations)


def test_fenced_fake_issue_cannot_satisfy_backstop(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-430-alpha.md",
        "# WO-P1-430 — alpha\n\n```\nIssue: #430\n```\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "exactly one 'Issue: #430' line" in violations[0]
    assert "found 0" in violations[0]


def test_fenced_fake_marker_and_issue_do_not_trigger_violations(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-431-alpha.md",
        "# WO-P1-431 — alpha\n\n```md\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #999\n```\n\nIssue: #431\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_fenced_fake_marker_cannot_activate_marker_policy(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-355-legacy.md",
        "# WO-P1-355 — legacy\n\n~~~\nIdentity schema: GITHUB_ISSUE_V1\n~~~\n",
    )
    violations = check_work_order_identities(
        iter_directory_work_orders(tmp_path),
        legacy_filenames={"WO-P1-355-legacy.md"},
    )
    assert violations == []


def test_real_marker_and_issue_outside_fence_are_recognized(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-432-alpha.md",
        "# WO-P1-432 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #432\n\n```\nnot authority\n```\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_marker_issue_mismatch_outside_fence_is_detected(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-433-alpha.md",
        "# WO-P1-433 — alpha\n\nIdentity schema: GITHUB_ISSUE_V1\nIssue: #434\n\n~~~\nexample\n~~~\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 2
    assert "requires Issue number == 433" in violations[0]
    assert "requires Issue number == 433" in violations[1]


def test_tilde_fenced_fake_issue_is_ignored(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-434-alpha.md",
        "# WO-P1-434 — alpha\n\nIssue: #434\n\n~~~python\nIssue: #999\n~~~\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_longer_closing_fence_closes_block(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-435-alpha.md",
        "# WO-P1-435 — alpha\n\n```\nIssue: #999\n````\n\nIssue: #435\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_mismatched_fence_char_does_not_close(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-436-alpha.md",
        "# WO-P1-436 — alpha\n\n```\n~~~\nIssue: #999\n```\n\nIssue: #436\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_unclosed_fence_hides_remainder(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-437-alpha.md",
        "# WO-P1-437 — alpha\n\nIssue: #437\n\n```\nIssue: #999\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_indented_opening_fence_with_three_spaces_opens_block(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-438-alpha.md",
        "# WO-P1-438 — alpha\n\nIssue: #438\n\n   ```\nIssue: #999\n   ```\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert violations == []


def test_four_space_indent_is_not_a_fence(tmp_path: Path) -> None:
    write_work_order(
        tmp_path,
        "WO-P1-439-alpha.md",
        "# WO-P1-439 — alpha\n\nIssue: #439\n\n    ```\nIssue: #999\n    ```\n",
    )
    violations = check_work_order_identities(iter_directory_work_orders(tmp_path))
    assert len(violations) == 1
    assert "exactly one 'Issue: #439' line" in violations[0]
    assert "found 2" in violations[0]
