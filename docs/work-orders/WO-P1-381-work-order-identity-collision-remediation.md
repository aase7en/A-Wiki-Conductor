# WO-P1-381 — Work-order identity collision remediation + atomic guard

Status: READY_FOR_REVIEW (final checkpoint below)
Issue: #381
Identity schema: GITHUB_ISSUE_V1
Risk: R3 coordination identity
Topology: CONTROL_PLANE_ONLY

## Binding
Authority repo: aase7en/A-Wiki-Conductor
Worktree: A:/GitHub/_worktrees/A-Wiki-Conductor-wo381-identity-remediation
Branch: fix/wo-p1-381-identity-collision
Base: 2a461ae22ab28ad3b48f15660ab818f700faab30
Owner: GLM author lane under GPT integrator authority (Issue #381 packet,
runs/WO-P1-381/author/task.md)

## Collision and chronology

- origin/main at 2a461ae contained two distinct canonical work-order files
  claiming the same numeric id WO-P1-260:
  - `docs/work-orders/WO-P1-260-dex-2b-conductor-reconciliation-receipt.md`
    (DEX-2b control-plane reconciliation, Issue #348);
  - `docs/work-orders/WO-P1-260-a-faster-durable-lanes.md`
    (A-Faster durable lane identity, Issue #374).
- Both tracks minted WO-P1-260 independently and landed on origin/main
  (`cbd4760` merged the A-Faster lane; the DEX packet arrived via the
  DEX-ARCH-1 contract freeze lineage), so the repository's canonical
  work-order namespace no longer had a unique owner for numeric id 260.
- Issue #381 is the deciding authority for the remediation recorded here.

## Canonical resolution (per Issue #381)

- DEX keeps WO-P1-259 / WO-P1-260: the DEX-2b file, its contracts and its
  ADR references are untouched canonical owners of those ids.
- The A-Faster durable-lane record rebinds to Issue #374 => canonical id
  WO-P1-374:
  `docs/work-orders/WO-P1-260-a-faster-durable-lanes.md` was renamed to
  `docs/work-orders/WO-P1-374-a-faster-durable-lanes.md`; its header, claim
  family and result destination now use WO-P1-374; the accepted
  pre-remediation attempt evidence (claim, lane, run id, BINDING_DIGEST,
  branch, dispatch head, run directories) is preserved verbatim in its
  "Historical alias / migration" section.
- `.agents/skills/a-faster/references/durable-lanes.md` now presents
  WO-P1-374 as the canonical A-Faster example identity (worked example
  recomputed: BINDING_DIGEST
  `e55d20348b88454ebeb8e655afc8c3ddc571e3428560e642d884841699d7db22`) and
  notes that pre-remediation WO-P1-260 pointers remain valid evidence
  aliases, not canonical task ids.
- Deferred rebinds, each a separate lane with its own authority (not
  executed here): Context Rollover Guard => Issue #369 / WO-P1-369;
  Claude adapter => Issue #375 / WO-P1-375; Kilo adapter => Issue #376 /
  WO-P1-376.
- New GitHub-backed work orders created after this policy use their issue
  number as the numeric suffix: Issue #N => WO-P1-N.
- Historical evidence is preserved; Git history was never rewritten and old
  run ids/branches are not denied — they are superseded identity aliases.

## A-FastTask hotspot boundary

`.agents/skills/a-fasttask/**` is a forbidden path for this work order and
was not touched. The A-FastTask router-only boundary (WO-P1-245 /
WO-P1-247) is unchanged; this remediation grants A-Faster and A-FastTask no
new execution, claim, or review authority.

## Identity policy (binding after this work order)

- New GitHub-backed WOs use the issue number as the numeric suffix
  (N >= 381 era).
- Legacy accepted ids stay canonical unless they collide; on collision the
  loser rebinds to its own issue number and preserves the old identity as
  an explicitly labelled historical alias (never falsified, never deleted).
- Enforcement mechanism: the deterministic, offline repository guard
  `tests/test_work_order_identity.py` —
  - scans tracked `docs/work-orders/WO-P1-*.md` filenames;
  - parses numeric N from WO-P1-N;
  - fails on more than one canonical file using the same N;
  - for files declaring `Identity schema: GITHUB_ISSUE_V1` (the one
    canonical marker, matching Issue #381 and accepted WO-P1-369),
    requires exactly one `Issue: #N` line matching the filename N;
  - for every plain numeric WO with N >= 381, requires exactly one
    `Issue: #N` line matching N even when the marker is accidentally
    omitted — missing and duplicate Issue lines are both violations
    (closes the missing-Issue bypass found in repair-002 review);
  - includes the repo regression proving unique WO-P1 numeric ids plus
    temp-directory unit fixtures for duplicate-number, issue-mismatch,
    missing-issue and duplicate-issue detection. No GitHub API is used.
- No new task DB, scheduler, claim, lease, or review authority is created;
  the guard only reads filenames and headers.

## Allowed mutable scope

1. RENAME docs/work-orders/WO-P1-260-a-faster-durable-lanes.md
   -> docs/work-orders/WO-P1-374-a-faster-durable-lanes.md
2. MODIFY .agents/skills/a-faster/references/durable-lanes.md
3. NEW docs/work-orders/WO-P1-381-work-order-identity-collision-remediation.md
4. NEW tests/test_work_order_identity.py

Everything else read-only. Forbidden: `.agents/skills/a-fasttask/**`,
`src/**`, DEX WO259/WO260 docs and contracts, Context Rollover
branch/files, Claude/Kilo adapter branches/files, and any Git history
rewrite (reset/clean/stash/rebase/force).

## 2026-09-19 final checkpoint — READY_FOR_REVIEW

- RED (evidence, pre-remediation tree at base 2a461ae):
  `python -m pytest -q tests/test_work_order_identity.py` failed exactly
  the repo regression with
  `duplicate canonical work-order id WO-P1-260: WO-P1-260-a-faster-durable-lanes.md and WO-P1-260-dex-2b-conductor-reconciliation-receipt.md`
  while all seven unit fixtures passed.
- Implemented: the four scope paths above (rename + rebind + historical
  alias section, reference example rebind with recomputed verified digest,
  this record, the deterministic guard).
- GREEN: `python -m pytest -q tests/test_work_order_identity.py` — all
  tests pass on the candidate; no duplicate WO-P1 numeric ids remain.
- Gates: exact scope check (four paths only), `git diff --check`
  2a461ae..HEAD, strict UTF-8 on changed files, canonical-reference grep
  (remaining WO-P1-260 mentions are inside explicitly labelled historical
  alias sections), zero `.agents/skills/a-fasttask/**` diff, fake-secret
  scan over added lines.
- Next gates: independent exact-SHA read-only review + exact-head CI
  before merge; GPT accept/merge only. No push/merge/self-accept.

## 2026-09-19 repair-002 checkpoint — READY_FOR_REVIEW

Integrator review of candidate 50f02a found two authority defects: the
marker text diverged from Issue #381 and accepted WO-P1-369 (canonical
marker is exactly `Identity schema: GITHUB_ISSUE_V1`; 50f02a introduced
a non-canonical variant), and the N>=381 backstop only rejected wrong
Issue numbers when an Issue line was present, so a new numeric WO
omitting both the marker and the Issue line could evade the atomic
allocation rule.

- RED (tests added first on dispatch head 50f02a2, clean tree):
  `python -m pytest -q tests/test_work_order_identity.py` → 4 failed,
  8 passed. Failing regressions:
  `test_above_threshold_without_marker_or_issue_is_detected` (N>=381
  with no marker and no Issue line passed the old guard),
  `test_above_threshold_duplicate_issue_lines_is_detected` (two
  identical Issue lines passed),
  `test_canonical_marker_below_threshold_requires_issue` (canonical
  marker without Issue line was not recognized),
  `test_canonical_marker_issue_mismatch_is_detected` (canonical marker
  with mismatching Issue below threshold was not recognized).
  Evidence: runs/WO-P1-381/repair/attempt-0002/red-pytest.txt.
- Implemented (repair-002, mutable scope only: the guard/tests, this
  work order, WO-P1-374; the durable-lanes reference needed no change —
  it carries no marker text):
  - canonical marker constant/text unified to `Identity schema:
    GITHUB_ISSUE_V1` in the guard, fixtures, WO-P1-374 and this work
    order; zero occurrences of the non-canonical variant remain in the
    candidate;
  - every plain numeric `WO-P1-N-*.md` with N >= 381 now requires
    exactly one `Issue: #N` line — zero Issue lines (the missing-Issue
    bypass) and duplicate Issue lines (even identical) are violations;
  - `GITHUB_ISSUE_V1` at any numeric N requires exactly one matching
    Issue line; marker on a non-numeric token remains a violation;
  - legacy/revision token files below the threshold remain untouched
    unless they declare the marker. No GitHub API/network dependency.
- GREEN: identity suite 12/12 (`green-identity.txt`); adjacent
  continuity/authority suites 178/178 across
  test_work_order_identity, test_continuity_guard,
  test_continuity_projection, test_awiki_a_conductor_authority_contract,
  test_project_identity (`green-adjacent.txt`).
- Gates: full duplicate numeric sweep — 181 numeric ids, max 381, zero
  duplicates, only N>=381 file is this work order with its matching
  `Issue: #381` line (`duplicate-sweep.txt`); `git diff --check`
  50f02a2..worktree clean; strict UTF-8 with zero U+FFFD on all four
  scope files (`utf8-check.txt`); credential/secret pattern scan over
  110 added lines — zero hits; DEX WO-P1-259/WO-P1-260 blob diffs empty;
  `.agents/skills/a-fasttask/**` diff empty; historical WO-P1-260
  evidence untouched — digest
  `cca025dd01a90d0a86f6a86b16e2a4c42f04c618cfd1df62bec160be5fa14d3f`
  and historical run/branch/claim strings
  preserved verbatim; canonical WO374 worked-example digest
  `e55d20348b88454ebeb8e655afc8c3ddc571e3428560e642d884841699d7db22`
  recomputes exactly from the displayed canonical bytes
  (`digest-recompute.txt`).
- Commit subject: `fix(WO381): harden GitHub issue work-order identity
  guard`.
- Next gates: integrator push -> Draft PR -> exact-SHA independent R3
  review + CI; GPT accept/merge only. No self-accept/merge.
