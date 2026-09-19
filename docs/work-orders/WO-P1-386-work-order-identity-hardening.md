# WO-P1-386 — Work-Order Identity Guard Hardening

Status: CLAIMED / GOVERNANCE_BOOTSTRAP
Issue: #386
Identity schema: GITHUB_ISSUE_V1
Risk: R3 — repository identity policy
Topology: CONTROL_PLANE_ONLY

## Binding

- repo: aase7en/A-Wiki-Conductor
- worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo386-identity-hardening
- branch: fix/wo-p1-386-work-order-identity-hardening
- base: 3067bd32569d7bcd6cc41e18c1c97a9a4f7db9c9
- claim: WO-P1-386-WORK-ORDER-IDENTITY-HARDENING-001
- integrator: GPT-5.6 Sol
- preferred bounded implementer: GLM-5.3 MAX
- predecessor: WO-P1-381 accepted/closed; do not rewrite accepted historical evidence

## Reuse classification

EXTEND only:
- tests/test_work_order_identity.py deterministic offline guard

Optional new deterministic fixture:
- tests/fixtures/work_order_identity/legacy_identity_filenames.txt

The fixture is a frozen regression exception set, NOT a task/claim/project authority.

## Goal

Close four non-blocking P3 gaps identified by independent review of WO381:

1. freeze the pre-policy legacy identity space so a new Work Order cannot evade
   GitHub-backed allocation by choosing an unused number below 381;
2. treat malformed `WO-P1-*.md` filenames as violations instead of silently
   skipping them;
3. parse `Identity schema:` and `Issue:` only from real Markdown text, not
   fenced code examples;
4. make revision/noncanonical token policy explicit and historical-only.

## Frozen legacy rule

At this Work Order's dispatch base, capture the exact existing filenames whose
identity shape is legacy/non-current:

- every `WO-P1-*.md` whose parsed token is not purely numeric; OR
- every purely numeric token with numeric id < 381.

Store them sorted in the optional fixture above.

After this policy:
- an existing filename in that frozen set remains accepted subject to the
  pre-existing marker/Issue checks;
- a new filename with pure numeric id < 381 is forbidden even if it carries a
  matching Issue line or GITHUB_ISSUE_V1 marker;
- a new revision/noncanonical token is forbidden at any number;
- current canonical plain numeric ids >= 381 continue to use the existing
  exact Issue-number rules;
- do not use Git history, GitHub API, timestamps or chat memory to identify
  legacy files. CI shallow clones must behave identically.

Changing the frozen exception fixture later is a policy mutation requiring its
own explicit Work Order/review; normal new Work Orders must never update it.

## Markdown fence-aware parsing

Identity marker and Issue lines inside fenced code blocks are examples only and
MUST NOT count as authority.

Implement bounded line parsing for fenced blocks:
- backtick or tilde fences;
- opening fence has at least 3 identical fence chars, with up to 3 leading spaces;
- closing fence uses the same char and length >= opening;
- content until closing fence is ignored for identity marker/Issue parsing;
- unclosed fence ignores the remainder of the document;
- do not attempt a full Markdown parser.

Outside fences:
- marker recognition should be line-oriented/exact, not arbitrary substring;
- Issue recognition remains exact line-oriented.

## Malformed filename rule

Any tracked/untracked non-ignored Markdown file in `docs/work-orders` whose
name begins `WO-P1-` but cannot be parsed by the canonical filename grammar
MUST produce a deterministic violation.

Do not silently exclude it in iterator helpers.

Files not beginning `WO-P1-` remain outside this guard.

## Revision token rule

Non-pure-numeric tokens are historical exceptions only if their exact filename
is in the frozen legacy fixture.

They never become GITHUB_ISSUE_V1 current identities.

Existing frozen historical revision files remain readable; new revision-token
files fail regardless of whether they carry a matching Issue line.

## Mutable scope ONLY

- tests/test_work_order_identity.py
- NEW tests/fixtures/work_order_identity/legacy_identity_filenames.txt
- this Work Order

Everything else read-only.

## Forbidden

- production src/**
- A-Faster / A-FastTask
- accepted WO381 document
- Hook Contract / adapters / WO389
- CURRENT-WORK / handoff / COLLAB / PROJECT-PLAN
- GitHub/network/history-dependent validation
- reset/clean/stash/rebase/force/history rewrite

## RED-first acceptance

Before implementation demonstrate failing regressions for:
1. new unused numeric id <381 with matching Issue + marker;
2. new revision token not in frozen set;
3. malformed `WO-P1-*.md` filename;
4. fake Issue inside fenced code does not satisfy real requirement;
5. fake identity marker inside fenced code does not trigger marker authority;
6. real marker/Issue outside fence still work;
7. tilde and backtick fences;
8. unclosed fence behavior;
9. current repository corpus remains green once the exact legacy fixture is generated.

## GREEN

- focused identity suite green;
- adjacent continuity/authority suites green;
- deterministic fixture sorted, unique, newline-terminated;
- every fixture filename exists at dispatch base and meets legacy predicate;
- no current canonical >=381 filename appears in fixture;
- adding a synthetic lower numeric/revision file cannot be made valid by matching
  Issue/marker lines;
- no Git history/API/network access;
- diff/scope/UTF-8/U+FFFD/secret checks pass.

R3:
- exact-SHA independent review;
- exact-head CI;
- GPT-5.6 Sol acceptance;
- post-main verification.

## Replay safety

Recover pointer/process/result/Git before redispatch.
RUNNING never redispatches.
TERMINAL_UNHARVESTED is harvested first.
