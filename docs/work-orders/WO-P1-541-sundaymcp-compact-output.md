# WO-P1-541 — SundayMCP lossless compact output

Status: ACTIVE / BORROWED CONTINUITY LANE
Issue: #541
Task topology: CROSS_REPO
Risk: R2 shared MCP presentation contract

## Authority and lane binding

Authority repo: A-Wiki-Conductor
Authority worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo541-compact-output
Authority branch: docs/wo-p1-541-compact-output
Authority base: b644fa02f480ae18fbae3d2b7a6d06f7fc79f726
Authority claim: WO-P1-541-COMPACT-OUTPUT-AWIKI-001

Execution repo: SunDayRemoteMCP
Execution worktree: /Users/aase7en/GitHub/_worktrees/SunDayRemoteMCP-wo541-compact-read
Execution branch: feat/wo-p1-541-compact-read
Execution base: e6460ebb3823f1b0c179f78b9f1944b05963531f
Execution claim: WO-P1-541-COMPACT-READ-SRM-001

## Problem

Legacy `read_file` returns the file body directly in tool text, so ChatGPT can render
large raw-source cards in the conversation. The UI noise must be reduced without
turning a lossy summary into evidence authority or reducing model evidence access.

## Proven reusable seam

CTS-0 proved the existing `sunday_batch_read` dual-channel pattern:
- compact human-facing `content` receipt;
- bounded rich `structuredContent` for model/tool consumption;
- explicit truncation and omission metadata.

CTS-1 must REUSE/EXTEND this pattern. No new evidence database or task authority.

## CTS-1 source contract

Add an additive read-only Sunday tool, provisionally `sunday_compact_read`, that:
- accepts one local text path plus bounded line offset/length and byte budget;
- reuses the existing validated filesystem read engine;
- emits a short visible receipt only;
- places the bounded source range in `structuredContent`;
- exposes deterministic evidence identity: path, requested range and SHA-256 digest;
- marks truncation explicitly;
- optionally accepts an expected range digest and fails closed on mismatch.

The digest identifies the exact decoded selected range returned by the existing
TextFileHandler line-range engine, before the byte cap is applied. Existing line-range
semantics (including its final-line newline behavior) are reused, not redefined. It
must not be described as a whole-file digest unless the implementation actually
hashes the whole file.

Legacy `read_file` behavior stays unchanged in CTS-1.

## Exact execution scope

Allowed initially:
- `src/sunday/compact-read.ts` (new)
- `src/sunday/mcp-runtime-tools.ts`
- `test/test-sunday-compact-read.js` (new)

Forbidden:
- legacy `read_file` handler/behavior
- supervisor/job/claim/lease semantics
- provider/secrets configuration
- unrelated filesystem/edit/terminal behavior
- canonical Mission Control roadmap while #537 owns that hotspot

## Acceptance

- visible receipt is materially smaller than returned source for a large text range;
- structured payload preserves the exact bounded selected content;
- digest mismatch is explicit and fail-closed;
- truncation is explicit and never presented as full evidence;
- path/range/digest identity is deterministic across identical rereads;
- malformed args, directories and non-text payloads fail closed;
- no shadow evidence/task/claim/review/completion authority;
- focused tests + build + related Sunday MCP tool-contract tests pass;
- strict UTF-8, diff-check, exact-scope and secret scan pass;
- freeze exact SRM SHA and obtain independent review + hosted CI before acceptance.

## Follow-on gates

CTS-2 must verify the real ChatGPT connector: smaller visible tool surface and no
measured model-evidence regression. Routing adoption (CTS-3+) is forbidden until
CTS-2 passes. The canonical Mission Control roadmap update remains owned by #537
until its current read scope is terminal and harvested.
