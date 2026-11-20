"""Materialize a new connector instance from a validated reference (WO-P1-060 PR-B).

Copies the validated per-instance layout (instance.ps1, start/stop scripts,
cmd wrappers, profile template, serena-home seed) from a reference instance,
re-rendering name/port/project/profile literals. Shared machine paths
($TunnelClientPath / $LegacySecretPath) are parsed from the reference so the
new instance always follows the same validated source of truth.
"""

from __future__ import annotations

import re
import sys
from enum import Enum
from pathlib import Path

from .instance_rebind import _PROJECTS_LINE_RE
from .instance_runtime import _ps_quote
from .local_instances import LocalInstance, _TUNNEL_ID_RE

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHARED_PATH_RES = (
    re.compile(r"^\$TunnelClientPath\s*=\s*'([^']*)'", re.MULTILINE),
    re.compile(r"^\$LegacySecretPath\s*=\s*'([^']*)'", re.MULTILINE),
)
_LISTEN_RE = re.compile(r"(?m)^(\s*listen_addr:\s*127\.0\.0\.1:)\d+")
_TEMPLATE_PROJECT_RE = re.compile(r"(--project\s+)(?:\"[^\"]*\"|\S+)")


class InstanceCreateError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def next_health_port(instances: tuple[LocalInstance, ...]) -> int:
    ports = []
    for instance in instances:
        tail = instance.health_address.rsplit(":", 1)[-1]
        if tail.isdigit():
            ports.append(int(tail))
    return max(ports, default=18010) + 1


def _reference_root(
    instances_root: Path, reference_root: Path | None
) -> Path:
    if reference_root is not None:
        return reference_root
    for candidate in sorted(instances_root.iterdir()):
        if (candidate / "instance.ps1").is_file():
            return candidate
    raise InstanceCreateError("REFERENCE_MISSING")


def _shared_paths(reference: Path) -> tuple[str, str]:
    text = (reference / "instance.ps1").read_text(encoding="utf-8")
    matches = [pattern.search(text) for pattern in _SHARED_PATH_RES]
    if not all(matches):
        raise InstanceCreateError("REFERENCE_PS1_INVALID")
    return matches[0].group(1), matches[1].group(1)


def _default_work_number(instances_root: Path, reference: Path) -> int:
    count = 0
    if instances_root.is_dir():
        for candidate in instances_root.iterdir():
            if (candidate / "instance.ps1").is_file():
                count += 1
    return max(count, 0) + 1


def _retitle_cmd_text(text: str, title: str) -> str:
    updated, count = re.subn(
        r"(?m)^title .*$", lambda _m: "title " + title, text, count=1
    )
    if count == 0:
        updated = text.replace("@echo off", f"@echo off\ntitle {title}", 1)
    return updated


class _RuntimeForensicsHardeningState(Enum):
    TRANSFORMED = "TRANSFORMED"
    ALREADY_HARDENED = "ALREADY_HARDENED"
    PASSTHROUGH_UNRECOGNIZED = "PASSTHROUGH_UNRECOGNIZED"
    REFUSED_AMBIGUOUS = "REFUSED_AMBIGUOUS"


_STRING_REGION_KINDS = frozenset(
    {"single_quoted", "double_quoted", "literal_here", "expandable_here"}
)
_NONEXECUTING_REGION_KINDS = frozenset(
    {"comment", "block_comment", "literal_here", "expandable_here"}
)
_COMMENT_REGION_KINDS = frozenset({"comment", "block_comment"})


def _rest_of_line_is_blank(text: str, index: int) -> bool:
    end = text.find("\n", index)
    return not text[index : end if end != -1 else len(text)].strip()


def _find_here_terminator(text: str, search_from: int, quote: str) -> int:
    """Offset of a closing quote+'@' at the beginning of a line, or -1.

    Per PowerShell spec §2.3.5.2 the here-string body ends at the FIRST line
    whose beginning is the closing mark; any trailing content on that line
    (e.g. ``"@ | Out-Null``) is live code after the closer, not part of the
    string. Indented closers do not close.
    """
    marker = quote + "@"
    newline = text.find("\n", search_from)
    while newline != -1:
        line_begin = newline + 1
        if text.startswith(marker, line_begin):
            return line_begin
        newline = text.find("\n", line_begin)
    return -1


def _lex_powershell(text: str) -> tuple[list[tuple[str, int, int]], bool]:
    """One bounded lexical scan of PowerShell source with offsets.

    Returns ``(regions, valid)``: non-overlapping sorted ``(kind, start, end)``
    intervals for line comments, non-nesting block comments (first ``#>``
    closes per spec §2.2.3), single-quoted literals, double-quoted strings,
    literal here-strings and expandable here-strings. ``valid`` is False when
    a string, here-string or block comment is unterminated at EOF (EOF lexical
    validity). This is a bounded provenance scan, not a parser.
    """
    regions: list[tuple[str, int, int]] = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "<" and i + 1 < n and text[i + 1] == "#":
            # PowerShell block comments do NOT nest (spec §2.2.3): the region
            # ends at the FIRST "#>", everything after is live code.
            end = text.find("#>", i + 2)
            if end == -1:
                regions.append(("block_comment", i, n))
                return regions, False
            regions.append(("block_comment", i, end + 2))
            i = end + 2
            continue
        if ch == "#":
            end = text.find("\n", i)
            if end == -1:
                regions.append(("comment", i, n))
                i = n
            else:
                regions.append(("comment", i, end))
                i = end
            continue
        if (
            ch == "@"
            and i + 1 < n
            and text[i + 1] in ("'", '"')
            and _rest_of_line_is_blank(text, i + 2)
        ):
            quote = text[i + 1]
            kind = "literal_here" if quote == "'" else "expandable_here"
            terminator = _find_here_terminator(text, i + 2, quote)
            if terminator == -1:
                regions.append((kind, i, n))
                return regions, False
            regions.append((kind, i, terminator + 2))
            i = terminator + 2
            continue
        if ch == "'":
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            if j >= n:
                regions.append(("single_quoted", i, n))
                return regions, False
            regions.append(("single_quoted", i, j + 1))
            i = j + 1
            continue
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "`":
                    j += 2
                    continue
                if text[j] == '"':
                    break
                j += 1
            if j >= n:
                regions.append(("double_quoted", i, n))
                return regions, False
            regions.append(("double_quoted", i, j + 1))
            i = j + 1
            continue
        if ch == "`":
            i += 2
            continue
        i += 1
    return regions, True


def _mask_regions(
    text: str, regions: list[tuple[str, int, int]], kinds: frozenset[str]
) -> str:
    chars = list(text)
    # Analysis views tolerate CRLF line endings without mutating the stored or
    # written original bytes: carriage returns become same-length spaces so
    # anchored marker/signal/adjacency matching is newline-agnostic.
    for position, ch in enumerate(chars):
        if ch == "\r":
            chars[position] = " "
    for kind, start, end in regions:
        if kind in kinds:
            for position in range(start, end):
                chars[position] = " "
    return "".join(chars)


def _position_in_regions(
    position: int, regions: list[tuple[str, int, int]], kinds: frozenset[str]
) -> bool:
    return any(kind in kinds and start <= position < end for kind, start, end in regions)


def _powershell_executable_view(
    text: str, regions: list[tuple[str, int, int]] | None = None
) -> str:
    """Mask comments and here-strings while preserving offsets.

    Ordinary quoted strings stay intact because structural markers legitimately
    include quoted fragments; matches inside string regions are filtered by
    provenance instead (``_filtered_matches``).
    """
    if regions is None:
        regions, _valid = _lex_powershell(text)
    return _mask_regions(text, regions, _NONEXECUTING_REGION_KINDS)


def _powershell_control_token_view(
    text: str, regions: list[tuple[str, int, int]] | None = None
) -> str:
    """View for control-token scans: ordinary string literals masked entirely.

    Literal data can never grant or deny control authority here; executable
    subexpression openers are refused separately by the interpolation bound.
    """
    if regions is None:
        regions, _valid = _lex_powershell(text)
    return _mask_regions(text, regions, _NONEXECUTING_REGION_KINDS | _STRING_REGION_KINDS)


def _filtered_matches(pattern, view: str, regions: list[tuple[str, int, int]]):
    """Matches of `pattern` whose start position is executable code, not string data."""
    return [
        match
        for match in pattern.finditer(view)
        if not _position_in_regions(match.start(), regions, _STRING_REGION_KINDS | _COMMENT_REGION_KINDS)
    ]


def _expandable_interpolation_is_supported(
    text: str, regions: list[tuple[str, int, int]]
) -> bool:
    """Refuse any active, unescaped ``$(`` inside expandable content.

    Expression-independent bound: the opener alone refuses, whether the
    enclosed expression is exit/throw/return, a nested subexpression, an
    ordinary command, or multiline. Backtick escape parity applies: `` `$( ``
    is inert data, ``` ``$( ``` is active.
    """
    for kind, start, end in regions:
        if kind not in ("double_quoted", "expandable_here"):
            continue
        i = start + (2 if kind == "expandable_here" else 1)
        limit = end - (2 if kind == "expandable_here" else 1)
        while i < limit:
            ch = text[i]
            if ch == "`":
                i += 2
                continue
            if ch == "$" and text[i + 1 : i + 2] == "(":
                return False
            i += 1
    return True

_ARCHIVE_TEST_PATH_HEADER = "if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {"
_FOREACH_LOG_HEADER = "foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {"
_RUNTIME_EXIT_IF_HEADER = "if ($RuntimeExitCode -eq 0) {"
_RUNTIME_EXIT_ELSE_HEADER = "} else {"
_TRY_HEADER = "try {"
_FINALLY_HEADER = "finally {"

_CANONICAL_BLOCK_HEADERS = frozenset(
    {
        _ARCHIVE_TEST_PATH_HEADER,
        _FOREACH_LOG_HEADER,
        _RUNTIME_EXIT_IF_HEADER,
        _RUNTIME_EXIT_ELSE_HEADER,
        _TRY_HEADER,
        _FINALLY_HEADER,
    }
)

# Exact headers emitted by the supported production generator
# (setup_wizard.FirstInstanceCreator). Recognition is deliberately exact-string:
# any change to the generator's helper or preflight shape stays fail-closed
# until this whitelist is consciously updated. Arbitrary functions or guards
# are NOT permitted.
_WIZARD_HELPER_FUNCTION_HEADERS = frozenset(
    {
        "function Write-Log([string]$Message) {",
        "function Fail([string]$Code, [string]$Message) {",
    }
)
_WIZARD_PREFLIGHT_GUARD_HEADERS = frozenset(
    {
        "if (-not (Test-Path -LiteralPath $TunnelClientPath -PathType Leaf)) {",
        "if (-not (Test-Path -LiteralPath $LegacySecretPath -PathType Leaf)) {",
        "if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {",
        "if (-not (Test-Path -LiteralPath $TunnelIdPath -PathType Leaf)) {",
        "if ($TunnelId -cnotmatch '^tunnel_[0-9a-f]{32}$') {",
    }
)
# Exact generated preflight guard bodies (single exact Fail call each; raw text
# compared under line-ending + per-line indentation normalization only). A Fail
# call is executable termination authority: it is permitted ONLY inside these
# validated bodies.
_WIZARD_PREFLIGHT_GUARD_BODIES: dict[str, str] = {
    "if (-not (Test-Path -LiteralPath $TunnelClientPath -PathType Leaf)) {":
        'Fail \'CONFIG_NOT_FOUND\' "tunnel-client not found: $TunnelClientPath"\n',
    "if (-not (Test-Path -LiteralPath $LegacySecretPath -PathType Leaf)) {":
        'Fail \'CONFIG_NOT_FOUND\' "credential not found: $LegacySecretPath"\n',
    "if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {":
        "Fail 'PROJECT_PATH_NOT_FOUND' $ProjectPath\n",
    "if (-not (Test-Path -LiteralPath $TunnelIdPath -PathType Leaf)) {":
        'Fail \'CONNECTOR_CONFIGURATION_REQUIRED\' "Create $TunnelIdPath"\n',
    "if ($TunnelId -cnotmatch '^tunnel_[0-9a-f]{32}$') {":
        "Fail 'TUNNEL_ID_MISSING' 'Tunnel ID is missing or invalid.'\n",
}
_ALLOWED_BLOCK_HEADERS = _CANONICAL_BLOCK_HEADERS

# Exact generated helper bodies (raw text, compared under line-ending +
# per-line indentation normalization only). The Fail body's ``exit 1`` is the
# ONLY terminal-flow token exemption; Write-Log earns none.
_WIZARD_HELPER_BODIES: dict[str, str] = {
    "function Write-Log([string]$Message) {": (
        "$line = ('{0} [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $InstanceName, $Message)\n"
        "Write-Host $line\n"
        "Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8\n"
    ),
    "function Fail([string]$Code, [string]$Message) {": (
        'Write-Log ("{0}: {1}" -f $Code, $Message)\n'
        "exit 1\n"
    ),
}


def _normalize_helper_body(body: str) -> str:
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(
        line.strip() for line in normalized.split("\n") if line.strip()
    )


def _validated_helper_exemptions(
    text: str, spans: list[tuple[str, int, int]]
) -> tuple[list[str], list[tuple[int, int]], list[tuple[int, int]]] | None:
    """Validate supported helper functions and preflight guards by full-body contract.

    Each recognized helper-function or preflight-guard span must be unique,
    top-level, and its raw body must equal the exact generated body modulo line
    endings and per-line indentation (comments or any addition/deletion/
    reorder/alteration fail). Returns ``(allowed_headers, exempt_exit_intervals,
    validated_fail_intervals)`` — allowed header names, the exact ``exit 1``
    line interval inside the validated Fail helper body, and the validated
    preflight guard body intervals where generated ``Fail`` calls may live — or
    None when a recognized-shape block fails the contract.
    """
    recognized = _WIZARD_HELPER_FUNCTION_HEADERS | set(_WIZARD_PREFLIGHT_GUARD_BODIES)
    counts = {
        header: sum(1 for h, _s, _e in spans if h == header) for header in recognized
    }
    allowed: list[str] = []
    exempt: list[tuple[int, int]] = []
    fail_intervals: list[tuple[int, int]] = []
    for header, start, end in spans:
        if header not in counts:
            continue
        if counts[header] != 1:
            return None
        if any(s < start and end < e for _h, s, e in spans):
            return None
        body = text[start + 1 : end]
        if header in _WIZARD_HELPER_FUNCTION_HEADERS:
            expected = _WIZARD_HELPER_BODIES[header]
        else:
            expected = _WIZARD_PREFLIGHT_GUARD_BODIES[header]
        if _normalize_helper_body(body) != _normalize_helper_body(expected):
            return None
        allowed.append(header)
        if header == "function Fail([string]$Code, [string]$Message) {":
            body_offset = start + 1
            for line in body.splitlines(keepends=True):
                if line.strip() == "exit 1":
                    line_start = body_offset
                    exempt.append((line_start, line_start + len(line.rstrip("\r\n"))))
                body_offset += len(line)
        else:
            fail_intervals.append((start + 1, end))
    return allowed, exempt, fail_intervals

_TOP_LEVEL_ANCESTRY: tuple[tuple[str, ...], ...] = ((),)
_RUNTIME_EXIT_ANCESTRY: tuple[tuple[str, ...], ...] = ((), (_TRY_HEADER,))
_ARCHIVE_MOVE_ANCESTRY: tuple[tuple[str, ...], ...] = (
    (_ARCHIVE_TEST_PATH_HEADER, _FOREACH_LOG_HEADER),
)
_EXIT_LOG_IF_ANCESTRY: tuple[tuple[str, ...], ...] = (
    (_RUNTIME_EXIT_IF_HEADER,),
    (_RUNTIME_EXIT_IF_HEADER, _TRY_HEADER),
)
_EXIT_LOG_ELSE_ANCESTRY: tuple[tuple[str, ...], ...] = (
    (_RUNTIME_EXIT_ELSE_HEADER,),
    (_RUNTIME_EXIT_ELSE_HEADER, _TRY_HEADER),
)


def _scan_block_spans(
    executable: str, trivia_view: str
) -> tuple[list[tuple[str, int, int]], bool] | None:
    """Quote-aware full brace scan.

    Returns ``(spans, pairing_valid)`` where each span is the stripped opening
    line (header), the absolute offset of its ``{`` and of its matching ``}``;
    ``None`` when brace balance is unprovable. ``pairing_valid`` enforces the
    bounded try/finally grammar with source-interval adjacency: every ``try {``
    must be closed then paired one-to-one with a sibling ``finally {`` whose
    opener is the next block opener at that depth, and the source interval
    between the try's closing brace and the ``finally`` keyword may contain
    only whitespace and comments (checked on ``trivia_view``, where strings
    and here-strings stay visible so quoted statements cannot hide). This is a
    bounded shape check, not a parser rewrite.
    """
    spans: list[tuple[str, int, int]] = []
    stack: list[tuple[str, int]] = []
    quote: str | None = None
    pairing_valid = True
    pending_finally: tuple[int, int] | None = None
    offset = 0
    for line in executable.splitlines(keepends=True):
        length = len(line.rstrip("\r\n"))
        index = 0
        while index < length:
            char = line[index]
            if quote is not None:
                if (
                    quote == "'"
                    and char == "'"
                    and index + 1 < length
                    and line[index + 1] == "'"
                ):
                    index += 2
                    continue
                if char == "`" and quote == '"' and index + 1 < length:
                    index += 2
                    continue
                if char == quote:
                    quote = None
                index += 1
                continue
            if char in ("'", '"'):
                quote = char
            elif char == "{":
                depth = len(stack)
                header = line.strip()
                open_position = offset + index
                if header == _FINALLY_HEADER:
                    if pending_finally is None or pending_finally[0] != depth:
                        pairing_valid = False
                    else:
                        try_close = pending_finally[1]
                        keyword_start = open_position - len("finally ")
                        if trivia_view[try_close + 1 : keyword_start].strip():
                            pairing_valid = False
                        pending_finally = None
                elif pending_finally is not None and pending_finally[0] == depth:
                    pairing_valid = False
                stack.append((header, open_position))
            elif char == "}":
                if not stack:
                    return None
                header, open_position = stack.pop()
                spans.append((header, open_position, offset + index))
                if header == _TRY_HEADER:
                    pending_finally = (len(stack), offset + index)
            index += 1
        offset += len(line)
    if stack or quote is not None:
        return None
    if pending_finally is not None:
        pairing_valid = False
    return spans, pairing_valid


def _enclosing_from_spans(
    spans: list[tuple[str, int, int]], position: int
) -> tuple[str, ...]:
    """Headers of blocks enclosing ``position``, innermost first."""
    enclosing = sorted(
        ((close - open_position, header) for (header, open_position, close) in spans if open_position < position < close)
    )
    return tuple(header for _span_length, header in enclosing)


_TERMINAL_FLOW_PATTERN = re.compile(r"\b(?:exit|throw|return)\b", re.IGNORECASE)
_LOOP_CONTROL_PATTERN = re.compile(r"\b(?:break|continue)\b", re.IGNORECASE)
_CATCH_PATTERN = re.compile(r"\bcatch\b", re.IGNORECASE)


def _terminal_control_flow_is_canonical(
    control: str, exit_marker, exempt_intervals: list[tuple[int, int]]
) -> bool:
    """Prove the only terminal statement outside the exact generated helper ``exit 1`` is the canonical exit marker.

    ``control`` is the control-token view (literal data masked). Terminal
    tokens inside the validated Fail body's exact ``exit 1`` line interval are
    the sole exemption; every remaining token must be the single canonical
    exit marker. Loop-control tokens are refused anywhere.
    """
    if _LOOP_CONTROL_PATTERN.search(control) is not None:
        return False
    outside_exempt = []
    for token in _TERMINAL_FLOW_PATTERN.finditer(control):
        if any(start <= token.start() and token.end() <= end for start, end in exempt_intervals):
            continue
        outside_exempt.append(token)
    if len(outside_exempt) != 1:
        return False
    token = outside_exempt[0]
    return (
        exit_marker.start() <= token.start() and token.end() <= exit_marker.end()
    )


_SMART_QUOTE_CODEPOINTS = (
    "\u201c",
    "\u201d",
    "\u201e",
    "\u2018",
    "\u2019",
    "\u201a",
    "\u201b",
)


def _contains_smart_quotes(text: str) -> bool:
    """PowerShell accepts smart quotes as string delimiters; the bounded lexer does not model them.

    The supported generators never emit them, so any occurrence refuses a
    positive verdict rather than mis-lexing the script.
    """
    return any(codepoint in text for codepoint in _SMART_QUOTE_CODEPOINTS)


_RUNTIME_LAUNCH_LEGACY_PATTERN = re.compile(
    r"(?m)^[ \t]*\$RuntimeProcess = Start-Process -FilePath \$TunnelClientPath -PassThru[ \t]*$"
)
_RUNTIME_LAUNCH_WIZARD_PATTERN = re.compile(
    r"(?m)^[ \t]*\$RuntimeProcess = Start-Process -FilePath \$TunnelClientPath `[ \t]*\n"
    r"[ \t]*-ArgumentList @\('run', '--profile-file', \$RuntimeProfile, '--pid\.file', \$PidFile\) `[ \t]*\n"
    r"[ \t]*-NoNewWindow -PassThru `[ \t]*\n"
    r"[ \t]*-RedirectStandardOutput \$RuntimeStdout `[ \t]*\n"
    r"[ \t]*-RedirectStandardError \$RuntimeStderr[ \t]*$"
)
_FAIL_TOKEN_PATTERN = re.compile(r"(?i)\bfail\b")


def _is_runtime_forensics_hardened(text: str) -> bool:
    """Recognize the complete generated forensics shape under lexical provenance.

    Requires EOF lexical validity, no active ``$(`` interpolation in expandable
    content, no smart-quote codepoints, provenance-filtered canonical markers
    and legacy-seam absence, complete archive-block operations, exactly one
    executable runtime launch of an enumerated generated template ordered after
    the archive/STARTING markers and before wait/refresh/capture, generated
    Fail calls only inside validated preflight guard bodies, canonical brace
    ancestry with bounded try/finally adjacency pairing, exact helper-body
    contracts (only the generated Fail ``exit 1`` is exempt from the
    terminal-flow proof), and canonical terminal control flow.
    """
    regions, lex_valid = _lex_powershell(text)
    if not lex_valid:
        return False
    if _contains_smart_quotes(text):
        return False
    if not _expandable_interpolation_is_supported(text, regions):
        return False
    executable = _powershell_executable_view(text, regions)
    control = _powershell_control_token_view(text, regions)
    archive_ancestry = (_ARCHIVE_TEST_PATH_HEADER, _FOREACH_LOG_HEADER)
    pattern_ancestry_pairs = (
        (
            re.compile(
                r"(?m)^[ \t]*\$RuntimeArchiveDir\s*=\s*Join-Path \$LogsDir 'runtime-archive'[ \t]*$"
            ),
            _TOP_LEVEL_ANCESTRY,
        ),
        (
            (
                re.compile(
                    r"(?m)^[ \t]*New-Item -ItemType Directory -Force -Path \$RuntimeArchiveDir \| Out-Null[ \t]*$"
                ),
                re.compile(
                    r"(?m)^[ \t]*New-Item -ItemType Directory -Force -Path \$RunDir, \$LogsDir, \$SerenaHome, \$RuntimeArchiveDir \| Out-Null[ \t]*$"
                ),
            ),
            _TOP_LEVEL_ANCESTRY,
        ),
        (
            re.compile(
                r"(?m)^[ \t]*\$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'[ \t]*$"
            ),
            _TOP_LEVEL_ANCESTRY,
        ),
        (
            re.compile(
                r"(?m)^[ \t]*foreach \(\$RuntimeLog in @\(\$RuntimeStdout, \$RuntimeStderr\)\) \{[ \t]*$"
            ),
            _TOP_LEVEL_ANCESTRY,
        ),
        (
            re.compile(
                r"(?m)^[ \t]*if \(Test-Path -LiteralPath \$RuntimeLog -PathType Leaf\) \{[ \t]*$"
            ),
            ((_FOREACH_LOG_HEADER,),),
        ),
        (
            re.compile(
                r"(?m)^[ \t]*\$Leaf = \[System\.IO\.Path\]::GetFileName\(\$RuntimeLog\)[ \t]*$"
            ),
            (archive_ancestry,),
        ),
        (
            re.compile(
                r"(?m)^[ \t]*\$Archived = Join-Path \$RuntimeArchiveDir \(\$ArchiveStamp \+ '-' \+ \$Leaf\)[ \t]*$"
            ),
            (archive_ancestry,),
        ),
        (
            re.compile(
                r"(?m)^[ \t]*Move-Item -LiteralPath \$RuntimeLog -Destination \$Archived -Force[ \t]*$"
            ),
            (archive_ancestry,),
        ),
        (
            re.compile(r'(?m)^[ \t]*Write-Log "STARTING:'),
            _TOP_LEVEL_ANCESTRY,
        ),
        (
            (_RUNTIME_LAUNCH_LEGACY_PATTERN, _RUNTIME_LAUNCH_WIZARD_PATTERN),
            _RUNTIME_EXIT_ANCESTRY,
        ),
        (
            re.compile(r"(?m)^[ \t]*\$RuntimeProcess\.WaitForExit\(\)[ \t]*$"),
            _RUNTIME_EXIT_ANCESTRY,
        ),
        (
            re.compile(r"(?m)^[ \t]*\$RuntimeProcess\.Refresh\(\)[ \t]*$"),
            _RUNTIME_EXIT_ANCESTRY,
        ),
        (
            re.compile(
                r"(?m)^[ \t]*\$RuntimeExitCode\s*=\s*\$RuntimeProcess\.ExitCode[ \t]*$"
            ),
            _RUNTIME_EXIT_ANCESTRY,
        ),
        (
            re.compile(r'(?m)^[ \t]*Write-Log "STOPPED: tunnel-client exit_code=0"[ \t]*$'),
            _EXIT_LOG_IF_ANCESTRY,
        ),
        (
            re.compile(
                r'(?m)^[ \t]*Write-Log \("TUNNEL_START_FAILED: Tunnel client exited with code \{0\}; '
                r'exit_code=\{0\}" -f \$RuntimeExitCode\)[ \t]*$'
            ),
            _EXIT_LOG_ELSE_ANCESTRY,
        ),
        (
            re.compile(r"(?m)^[ \t]*exit \$RuntimeExitCode[ \t]*$"),
            _RUNTIME_EXIT_ANCESTRY,
        ),
    )
    resolved_matches = []
    for pattern, allowed_ancestry in pattern_ancestry_pairs:
        if isinstance(pattern, tuple):
            combined = []
            for member in pattern:
                combined.extend(_filtered_matches(member, executable, regions))
            if len(combined) != 1:
                return False
            resolved_matches.append((combined[0], allowed_ancestry))
            continue
        found = _filtered_matches(pattern, executable, regions)
        if len(found) != 1:
            return False
        resolved_matches.append((found[0], allowed_ancestry))
    exit_marker = resolved_matches[-1][0]

    legacy_patterns = (
        re.compile(r"(?m)^[ \t]*Wait-Process -Id \$RuntimeProcess\.Id[ \t]*$"),
        re.compile(r"(?m)^[ \t]*if \(\$RuntimeProcess\.ExitCode -ne 0\) \{[ \t]*$"),
    )
    if any(_filtered_matches(pattern, executable, regions) for pattern in legacy_patterns):
        return False

    trivia_view = _mask_regions(text, regions, _COMMENT_REGION_KINDS)
    scan = _scan_block_spans(executable, trivia_view)
    if scan is None:
        return False
    spans, pairing_valid = scan
    if not pairing_valid:
        return False

    validation = _validated_helper_exemptions(text, spans)
    if validation is None:
        return False
    helper_headers, exempt_intervals, fail_intervals = validation
    allowed_headers = _ALLOWED_BLOCK_HEADERS | frozenset(helper_headers)
    if any(header not in allowed_headers for header, _s, _e in spans):
        return False

    # Fail is termination authority wherever it resolves to the generated
    # helper: PowerShell command invocation is case-insensitive and legal at
    # any statement position (new line, after ';', after '&'), so authority is
    # proven with a case-insensitive token scan on the control-token view
    # (string/comment/here-string literals masked: profile filenames and other
    # data can never become control). Exempt ONLY the validated Fail helper
    # definition line and the validated guard-body call spans.
    for header, start, _end in spans:
        if header == "function Fail([string]$Code, [string]$Message) {":
            line_start = text.rfind("\n", 0, start) + 1
            fail_intervals.append((line_start, start))
    for token in _FAIL_TOKEN_PATTERN.finditer(control):
        if not any(start <= token.start() < end for start, end in fail_intervals):
            return False

    # Backticks in executable code are line-continuation/escape syntax the
    # bounded lexer does not model; the generated shapes use them ONLY inside
    # the matched launch template. Any other code backtick (e.g. an escaped
    # ``F`ail`` command spelling) refuses the positive verdict.
    launch_match = resolved_matches[9][0]
    for position, char in enumerate(text):
        if char != "`":
            continue
        if _position_in_regions(position, regions, _STRING_REGION_KINDS | _COMMENT_REGION_KINDS):
            continue
        if launch_match.start() <= position < launch_match.end():
            continue
        if any(
            kind in ("literal_here", "expandable_here") and start <= position < end
            for kind, start, end in regions
        ):
            continue
        return False

    if not _terminal_control_flow_is_canonical(control, exit_marker, exempt_intervals):
        return False
    if _CATCH_PATTERN.search(control) is not None:
        return False

    positions = []
    for match, allowed in resolved_matches:
        start = match.start()
        ancestry = _enclosing_from_spans(spans, start)
        if ancestry not in allowed:
            return False
        positions.append(start)
    return positions == sorted(positions)


def _has_runtime_forensics_structural_signal(text: str) -> bool:
    """Detect executable forensics/legacy lines without promoting comments, strings, or letter-case variants.

    PowerShell identifiers are case-insensitive, so every distinctive marker of
    the generated forensic shape is matched case-insensitively: a recognizable
    case-equivalent fragment fails CLOSED when the case-exact transform grammar
    cannot support it. Marker matches starting inside string regions are
    provenance-filtered; when the lexical scan itself is invalid at EOF the
    unfiltered view is used so recognizable fragments never fall to generic
    passthrough through a broken lexis.
    """
    regions, lex_valid = _lex_powershell(text)
    executable = _powershell_executable_view(text, regions)
    patterns = (
        re.compile(r"(?im)^[ \t]*\$RuntimeArchiveDir\s*=\s*Join-Path \$LogsDir 'runtime-archive'[ \t]*$"),
        re.compile(r"(?im)^[ \t]*New-Item -ItemType Directory -Force -Path \$RuntimeArchiveDir \| Out-Null[ \t]*$"),
        re.compile(r"(?im)^[ \t]*\$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'[ \t]*$"),
        re.compile(r"(?im)^[ \t]*foreach \(\$RuntimeLog in @\(\$RuntimeStdout, \$RuntimeStderr\)\) \{[ \t]*$"),
        re.compile(r"(?im)^[ \t]*if \(Test-Path -LiteralPath \$RuntimeLog -PathType Leaf\) \{[ \t]*$"),
        re.compile(r"(?im)^[ \t]*\$Leaf = \[System\.IO\.Path\]::GetFileName\(\$RuntimeLog\)[ \t]*$"),
        re.compile(r"(?im)^[ \t]*\$Archived = Join-Path \$RuntimeArchiveDir \(\$ArchiveStamp \+ '-' \+ \$Leaf\)[ \t]*$"),
        re.compile(r"(?im)^[ \t]*Move-Item -LiteralPath \$RuntimeLog -Destination \$Archived -Force[ \t]*$"),
        re.compile(
            r'(?im)^[ \t]*Write-Log \("TUNNEL_START_FAILED: Tunnel client exited with code \{0\}; '
            r'exit_code=\{0\}" -f \$RuntimeExitCode\)[ \t]*$'
        ),
        re.compile(r"(?im)^[ \t]*\$RuntimeProcess\.Refresh\(\)[ \t]*$"),
        re.compile(r"(?im)^[ \t]*\$RuntimeExitCode\s*=\s*\$RuntimeProcess\.ExitCode[ \t]*$"),
        re.compile(r'(?im)^[ \t]*Write-Log "STOPPED: tunnel-client exit_code=0"[ \t]*$'),
        re.compile(r"(?im)^[ \t]*exit \$RuntimeExitCode[ \t]*$"),
        re.compile(r"(?im)^[ \t]*Wait-Process -Id \$RuntimeProcess\.Id[ \t]*$"),
        re.compile(r"(?im)^[ \t]*\$RuntimeProcess\.WaitForExit\(\)[ \t]*$"),
        re.compile(r"(?im)^[ \t]*if \(\$RuntimeProcess\.ExitCode -ne 0\) \{[ \t]*$"),
    )
    if lex_valid:
        return any(
            _filtered_matches(pattern, executable, regions) for pattern in patterns
        )
    return any(pattern.search(executable) is not None for pattern in patterns)


def _harden_start_script_runtime_forensics(text: str) -> str:
    """Upgrade validated legacy start.ps1 text without replacing its credential/preflight logic."""
    regions, _lex_valid = _lex_powershell(text)
    executable = _powershell_executable_view(text, regions)
    archive_assignment_pattern = re.compile(
        r"(?m)^[ \t]*\$RuntimeArchiveDir\s*=\s*Join-Path \$LogsDir 'runtime-archive'[ \t]*$"
    )
    exit_capture_pattern = re.compile(
        r"(?m)^[ \t]*\$RuntimeExitCode\s*=\s*\$RuntimeProcess\.ExitCode[ \t]*$"
    )
    refresh_pattern = re.compile(r"(?m)^[ \t]*\$RuntimeProcess\.Refresh\(\)[ \t]*$")
    exit_command_pattern = re.compile(r"(?m)^[ \t]*exit \$RuntimeExitCode[ \t]*$")

    complete_hardening = (
        archive_assignment_pattern.search(executable) is not None
        and exit_capture_pattern.search(executable) is not None
        and refresh_pattern.search(executable) is not None
        and exit_command_pattern.search(executable) is not None
    )
    if complete_hardening:
        return text
    if (
        archive_assignment_pattern.search(executable) is not None
        or exit_capture_pattern.search(executable) is not None
    ):
        return text

    stdout_pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)\$RuntimeStdout\s*=.*$")
    stderr_pattern = re.compile(r"(?m)^(?P<indent>[ \t]*)\$RuntimeStderr\s*=.*$")
    start_pattern = re.compile(r'(?m)^(?P<indent>[ \t]*)Write-Log "STARTING:')
    wait_process_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)Wait-Process -Id \$RuntimeProcess\.Id[ \t]*$"
    )
    method_wait_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)\$RuntimeProcess\.WaitForExit\(\)[ \t]*\r?\n"
        r"(?P=indent)if \(\$RuntimeProcess\.ExitCode -ne 0\) \{[ \t]*\r?\n"
        r"(?P=indent)[ \t]+Fail 'TUNNEL_START_FAILED' \"Tunnel client exited with code "
        r"\$\(\$RuntimeProcess\.ExitCode\)\.\"[ \t]*\r?\n"
        r"(?P=indent)\}[ \t]*$"
    )

    stdout_matches = _filtered_matches(stdout_pattern, executable, regions)
    stderr_matches = _filtered_matches(stderr_pattern, executable, regions)
    start_matches = _filtered_matches(start_pattern, executable, regions)
    wait_process_matches = _filtered_matches(wait_process_pattern, executable, regions)
    method_wait_matches = _filtered_matches(method_wait_pattern, executable, regions)
    if (
        len(stdout_matches) != 1
        or len(stderr_matches) != 1
        or len(start_matches) != 1
        or len(wait_process_matches) + len(method_wait_matches) != 1
        or stderr_matches[0].start() >= start_matches[0].start()
    ):
        return text

    archive = """New-Item -ItemType Directory -Force -Path $RuntimeArchiveDir | Out-Null
$ArchiveStamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
foreach ($RuntimeLog in @($RuntimeStdout, $RuntimeStderr)) {
    if (Test-Path -LiteralPath $RuntimeLog -PathType Leaf) {
        $Leaf = [System.IO.Path]::GetFileName($RuntimeLog)
        $Archived = Join-Path $RuntimeArchiveDir ($ArchiveStamp + '-' + $Leaf)
        Move-Item -LiteralPath $RuntimeLog -Destination $Archived -Force
    }
}
"""
    exit_block = """$RuntimeProcess.WaitForExit()
$RuntimeProcess.Refresh()
$RuntimeExitCode = $RuntimeProcess.ExitCode
if ($RuntimeExitCode -eq 0) {
    Write-Log "STOPPED: tunnel-client exit_code=0"
} else {
    Write-Log ("TUNNEL_START_FAILED: Tunnel client exited with code {0}; exit_code={0}" -f $RuntimeExitCode)
}
exit $RuntimeExitCode"""

    def _indent_block(block: str, indent: str) -> str:
        return "\n".join(indent + line if line else "" for line in block.splitlines())

    def _filtered_first(pattern, source: str):
        source_regions, _valid = _lex_powershell(source)
        found = _filtered_matches(
            pattern, _powershell_executable_view(source, source_regions), source_regions
        )
        return found[0] if found else None

    stderr_match = stderr_matches[0]
    stderr_indent = stderr_match.group("indent")
    hardened = (
        text[: stderr_match.end()]
        + "\n"
        + stderr_indent
        + "$RuntimeArchiveDir = Join-Path $LogsDir 'runtime-archive'"
        + text[stderr_match.end() :]
    )

    start_match = _filtered_first(start_pattern, hardened)
    if start_match is None:
        return text
    start_indent = start_match.group("indent")
    archive_block = _indent_block(archive.rstrip("\n"), start_indent) + "\n\n"
    hardened = hardened[: start_match.start()] + archive_block + hardened[start_match.start() :]

    if wait_process_matches:
        wait_match = _filtered_first(wait_process_pattern, hardened)
        if wait_match is None:
            return text
        replacement = _indent_block(exit_block, wait_match.group("indent"))
        return hardened[: wait_match.start()] + replacement + hardened[wait_match.end() :]

    method_match = _filtered_first(method_wait_pattern, hardened)
    if method_match is None:
        return text
    replacement = _indent_block(exit_block, method_match.group("indent"))
    return hardened[: method_match.start()] + replacement + hardened[method_match.end() :]


def _classify_start_script_runtime_forensics(
    text: str,
) -> tuple[str, _RuntimeForensicsHardeningState]:
    """Return a transformed/verified script plus an explicit safety classification."""
    hardened = _harden_start_script_runtime_forensics(text)
    if hardened != text:
        if _is_runtime_forensics_hardened(hardened):
            return hardened, _RuntimeForensicsHardeningState.TRANSFORMED
        return text, _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    if _is_runtime_forensics_hardened(text):
        return text, _RuntimeForensicsHardeningState.ALREADY_HARDENED
    if _has_runtime_forensics_structural_signal(text):
        return text, _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS
    return text, _RuntimeForensicsHardeningState.PASSTHROUGH_UNRECOGNIZED


def _substitute_reference_literals(
    text: str, reference_slug: str, profile: str, slug: str
) -> str:
    """Apply the per-instance profile/slug substitutions in canonical order."""
    text = text.replace(f"serena-{reference_slug}.yaml.template", f"{profile}.yaml.template")
    text = text.replace(f"serena-{reference_slug}.yaml", f"{profile}.yaml")
    text = text.replace(f"'{reference_slug}-'", f"'{slug}-'")
    return text


def create_instance(
    instances_root: Path | str,
    name: str,
    project_path: Path | str,
    *,
    health_port: int,
    tunnel_id: str | None = None,
    reference_root: Path | str | None = None,
    work_number: int | None = None,
) -> Path:
    root = Path(instances_root).expanduser().resolve(strict=False)
    slug = (name or "").strip().lower()
    if not _SLUG_RE.match(slug) or set(slug) == {"-"}:
        raise InstanceCreateError("NAME_INVALID")
    target = root / slug
    if target.exists():
        raise InstanceCreateError("NAME_ALREADY_EXISTS")

    project = Path(project_path)
    if not project.is_absolute() or not project.is_dir():
        raise InstanceCreateError("PROJECT_NOT_FOUND")
    project = project.resolve(strict=False)
    if not 1 <= int(health_port) <= 65535:
        raise InstanceCreateError("PORT_INVALID")

    reference = _reference_root(root, Path(reference_root) if reference_root else None)
    reference = reference.resolve(strict=False)
    tunnel_client, legacy_secret = _shared_paths(reference)
    reference_slug = reference.name

    # Validate every reference artifact BEFORE creating anything, so a bad
    # reference never leaves a half-built skeleton folder behind.
    for script in ("start.ps1", "stop.ps1"):
        if not (reference / script).is_file():
            raise InstanceCreateError("REFERENCE_SCRIPT_MISSING")

    reference_start_text = (reference / "start.ps1").read_text(encoding="utf-8")
    _, reference_start_state = _classify_start_script_runtime_forensics(reference_start_text)
    if reference_start_state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS:
        raise InstanceCreateError("REFERENCE_START_SCRIPT_UNSAFE")

    for pattern, code in (
        ("Start-*.cmd", "REFERENCE_CMD_MISSING"),
        ("Stop-*.cmd", "REFERENCE_CMD_MISSING"),
        ("profiles/*.template", "REFERENCE_TEMPLATE_MISSING"),
    ):
        if not list(reference.glob(pattern)):
            raise InstanceCreateError(code)
    if not (reference / "serena-home" / "serena_config.yml").is_file():
        raise InstanceCreateError("REFERENCE_TEMPLATE_MISSING")

    clean_tunnel = (tunnel_id or "").strip()
    if tunnel_id is not None and not _TUNNEL_ID_RE.match(clean_tunnel):
        raise InstanceCreateError("TUNNEL_ID_INVALID")

    display = slug.title()
    instance_name = f"Serena-{display}"
    profile = f"serena-{slug}"
    number = work_number if work_number is not None else _default_work_number(root, reference)

    # Preflight the FINAL substituted start script (the exact snapshot that
    # will be written) BEFORE any target materialization: a verdict that would
    # change under profile/slug substitution must refuse with zero target side
    # effects, never after directories or config files already exist.
    substituted_start_text = _substitute_reference_literals(
        reference_start_text, reference_slug, profile, slug
    )
    final_start_text, final_start_state = _classify_start_script_runtime_forensics(
        substituted_start_text
    )
    if final_start_state is _RuntimeForensicsHardeningState.REFUSED_AMBIGUOUS:
        raise InstanceCreateError("REFERENCE_START_SCRIPT_UNSAFE")

    for folder in ("profiles", "config", "run", "logs", "serena-home"):
        (target / folder).mkdir(parents=True, exist_ok=True)

    instance_ps1 = "\n".join(
        [
            f"# {instance_name} instance configuration",
            f"$InstanceName = '{_ps_quote(instance_name)}'",
            f"$ProjectPath = '{_ps_quote(str(project))}'",
            f"$SerenaHome = '{_ps_quote(str(target / 'serena-home'))}'",
            f"$HealthListenAddress = '127.0.0.1:{health_port}'",
            f"$TunnelProfileName = '{_ps_quote(profile)}'",
            f"$TunnelClientPath = '{_ps_quote(tunnel_client)}'",
            f"$LegacySecretPath = '{_ps_quote(legacy_secret)}'",
        ]
    )
    (target / "instance.ps1").write_text(instance_ps1 + "\n", encoding="utf-8-sig", newline="\r\n")

    for script, action in (("start.ps1", "Start"), ("stop.ps1", "Stop")):
        source = reference / script
        if not source.is_file():
            raise InstanceCreateError("REFERENCE_SCRIPT_MISSING")
        if action == "Start":
            text = final_start_text
        else:
            text = _substitute_reference_literals(
                source.read_text(encoding="utf-8"), reference_slug, profile, slug
            )
        (target / script).write_text(text, encoding="utf-8", newline="\r\n")

        cmd_source = reference / f"{action}-Serena-{reference_slug.title()}.cmd"
        if not cmd_source.is_file():
            matches = sorted(reference.glob(f"{action}-*.cmd"))
            if len(matches) != 1:
                raise InstanceCreateError("REFERENCE_CMD_MISSING")
            cmd_source = matches[0]
        cmd_text = cmd_source.read_text(encoding="utf-8")
        cmd_text = _retitle_cmd_text(cmd_text, f"Sunday-works {number} - {display}")
        (target / f"{action}-{instance_name}.cmd").write_text(
            cmd_text, encoding="utf-8", newline="\r\n"
        )

    templates = sorted((reference / "profiles").glob("*.template"))
    if not templates:
        raise InstanceCreateError("REFERENCE_TEMPLATE_MISSING")
    template_text = templates[0].read_text(encoding="utf-8")
    template_text = _LISTEN_RE.sub(
        lambda m: m.group(1) + str(health_port), template_text, count=1
    )
    template_text = _TEMPLATE_PROJECT_RE.sub(
        lambda m: m.group(1) + f'"{project.as_posix()}"', template_text, count=1
    )
    (target / "profiles" / f"{profile}.yaml.template").write_text(
        template_text, encoding="utf-8", newline="\n"
    )

    reference_config = reference / "serena-home" / "serena_config.yml"
    if reference_config.is_file():
        config_text = reference_config.read_text(encoding="utf-8")
        replacement = "projects:\n- '" + _ps_quote(str(project)) + "'"
        config_text = _PROJECTS_LINE_RE.sub(
            lambda _m: replacement, config_text, count=1
        )
        (target / "serena-home" / "serena_config.yml").write_text(
            config_text, encoding="utf-8", newline="\n"
        )

    if sys.platform != "win32":
        from .instance_templates_sh import render_sh_scripts

        sh_scripts = render_sh_scripts(
            instance_name=instance_name,
            project=str(project),
            serena_home=str(target / "serena-home"),
            port=health_port,
            profile=profile,
            slug=slug,
            tunnel_client=tunnel_client,
            api_key_file="config/api-key",
        )
        for filename, content in sh_scripts.items():
            script = target / filename
            script.write_text(content, encoding="utf-8", newline="\n")
            script.chmod(0o755)

    if tunnel_id is not None:
        (target / "config" / "tunnel-id.txt").write_text(
            clean_tunnel + "\n", encoding="utf-8", newline="\r\n"
        )

    return target
