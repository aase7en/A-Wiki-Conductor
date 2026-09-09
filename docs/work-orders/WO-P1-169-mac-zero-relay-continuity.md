# WO-P1-169 — Mac Zero-Relay continuity record

Date: 2026-09-10 (Asia/Bangkok)
Status: CLAIMED / DOCS-ONLY
Owner: GPT-5.6 Sol integrator documentation lane
Parallel implementation owner: WO-P1-168 / GPT-6 Astra
Risk: R2 operational/security documentation
Classification: REUSE existing Zero-Relay authority; no product/runtime authority changes

## Goal

Preserve the current home-Mac continuation state so a new GPT/GLM/Astra session can recover
without reading the prior ChatGPT transcript.

This work order records operational facts, solved/open problems, safe continuation steps,
and ownership. It does not implement the Claude harness repair and does not claim
Zero-Relay operational success.

## Authority and identity

- Repository: aase7en/A-Wiki-Conductor
- Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo169-docs
- Branch: docs/wo-p1-169-mac-zero-relay-continuity
- Base: 77e7b0f8e9460f78fa2ef4a1ddaad62131c2c7f2
- Durable claim: Issue #233 comment 5607093650
- Discovery/continuity anchors: Issue #233 comments 5606720902 and 5606878598
- Active source repair: WO-P1-168 in /Users/aase7en/Desktop/A-Wiki-Conductor-wo168

## Mutable scope

- docs/work-orders/WO-P1-169-mac-zero-relay-continuity.md
- docs/incidents/2026-09-10-mac-zero-relay-host-migration.md
- docs/runbooks/mac-zero-relay-continuation.md

Everything else is read-only.

Explicitly forbidden:
- src/a_conductor/**
- tests/**
- WO-P1-168 files/worktree/branch
- CURRENT-WORK.md
- handoff.md
- COLLAB.md
- DEFECT_LESSONS.md until the WO168 repair is frozen and accepted
- private secret values
- runtime/provider databases

## Current factual state

At claim:
- root main is clean and equals origin/main at 77e7b0f8e9460f78fa2ef4a1ddaad62131c2c7f2;
- the Windows work host is offline/unreachable, so continuation moved to the home Mac;
- the Mac has the repository and Claude Code CLI, but no installed Serena, Sunday Worker fleet,
  A-Conductor desktop/runtime, or ZCode requirement for the current critical path;
- Cointh Anthropic-compatible endpoint reachability from the Mac is proven only at the
  unauthenticated boundary (HTTP 401 / missing_key);
- an authenticated GLM-5.3 turn is not yet proven;
- current main Claude invocation contains --safe-mode;
- Claude Code 2.1.152 on this Mac rejects --safe-mode in a real --print invocation;
- WO168 owns the bounded compatibility repair and currently has active WIP.

## Parallelism rule

WO169 is documentation-only. It must not edit, test-modify, reset, stash, rebase, terminate,
or otherwise interfere with WO168. Any WO168 design seen before a frozen candidate is
PROPOSED / UNACCEPTED and must be labeled that way.

## Acceptance

- incident record and continuation runbook created;
- solved vs open/unproven items explicitly separated;
- no secret value or historical exposed credential copied;
- no unsupported Windows facts promoted to current Mac truth;
- no product/source/test/global-projection overlap with WO168;
- git diff --check and strict UTF-8 pass;
- added-line secret scan passes;
- branch pushed and draft PR opened;
- no self-merge; independent docs/security review required.

## Checkpoint

Next safe action for this lane:
verify the three docs, commit/push, open a draft PR, checkpoint Issue #233, then remain
read-only while WO168 continues.


### Verification pitfall and correction

Two early local checks were explicitly rejected as evidence:
1. plain `git diff` omitted the three untracked docs, so a diff-based secret scan had not
   scanned their content;
2. a zsh string variable containing three paths was not word-split, so a follow-up shell
   scan addressed one invalid combined path.

The accepted replacement check reads each exact file directly in Python, decodes strict
UTF-8, scans the real content for credential-like values, and runs per-file no-index
whitespace checks. Accepted result before staging: secret hits = 0; whitespace issues = 0
for all three files.

Lesson for this lane: untracked-file verification must enumerate actual paths explicitly;
a reported PASS with no demonstrated input coverage is not completion evidence.


### Parallel WO168 independent-review checkpoint

Astra froze candidate `654e36d497a875f06adba83e4ca2c14f1a647dbc` / PR #237 while
this docs lane was active. Sol performed independent review without touching WO168:
RED reconstruction = 4 failed / 15 passed; candidate host = 3/3 PASS; focused = 44 PASS
with 6 expected skips; related = 142 PASS with 3 Windows-only skips; independent
unknown-tool/MCP injection probe = 2/2 PASS. PR #237 comment 5607237872 is the
durable exact-SHA review checkpoint.

Hosted run 34391873577 remains a merge gate; macOS/Ubuntu smoke are green and
Windows/full was still in progress at this checkpoint. WO169 does not authorize merge.


### Next-R3 shaping (read-only)

Current-main audit narrows the post-WO168 Mac blocker to platform process observation /
spawn / exact termination and composition. Higher-level supervised execution, durable
identity/store/coordinator and Claude/provider authority are reusable. Proposed next
classification: EXTEND/WRAP existing process protocols with POSIX/macOS primitives and
explicit platform assembly; do not create a second supervisor/scheduler/store. Full
fault matrix and acceptance boundary are recorded in
`docs/runbooks/mac-zero-relay-continuation.md` §11. This is shaping only; no WO170/source
claim is opened until WO168 post-main verification closes.
