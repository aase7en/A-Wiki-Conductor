# WO-P1-381 — Work-order identity collision remediation + atomic guard

Status: READY_FOR_REVIEW (final checkpoint below)
Issue: #381
Identity schema: ISSUE_NUMBER_V1
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
  - for files declaring `Identity schema: ISSUE_NUMBER_V1`, requires an
    `Issue: #N` line matching the filename N;
  - for GitHub-backed WOs with N >= 381 that declare an Issue line,
    requires issue number == N even when the marker is accidentally
    omitted;
  - includes the repo regression proving unique WO-P1 numeric ids plus
    temp-directory unit fixtures for duplicate-number and issue-mismatch
    detection. No GitHub API is used.
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
