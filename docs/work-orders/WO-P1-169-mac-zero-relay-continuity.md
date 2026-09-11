# WO-P1-169 — Mac Zero-Relay continuity record

Date: 2026-09-10 (Asia/Bangkok)
Status: FROZEN / DRAFT PR #238 / DOCS CLAIM RELEASED / INDEPENDENT DOCS REVIEW PENDING
Owner: GPT-5.6 Sol integrator documentation lane
Parallel implementation status: WO-P1-168 R4 FROZEN / PR #242 exact-head CI SUCCESS / independent exact-SHA review pending
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
- Active WO168 R4 evidence worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo168-r4

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

Historical checkpoint: run `34391873577` was still in progress when this line was
first written. Final truth now supersedes it: exact-head CI `34391873577` SUCCESS,
PR #237 merged as `577d9483720c857a89a5d2c9ea9359f9c0aa50b5`, and post-main
CI `34393512623` SUCCESS.


### Next-R3 shaping (read-only)

Current-main audit narrows the post-WO168 Mac blocker to platform process observation /
spawn / exact termination and composition. Higher-level supervised execution, durable
identity/store/coordinator and Claude/provider authority are reusable. Proposed next
classification remains EXTEND/WRAP existing process protocols with POSIX/macOS primitives
and explicit platform assembly; do not create a second supervisor/scheduler/store. Full
fault matrix and acceptance boundary are recorded in
`docs/runbooks/mac-zero-relay-continuation.md` §11. WO170 remains blocked until WO168 R4
receives a truly independent exact-SHA review, merge and post-main verification.

### Current R4 reviewer/resource checkpoint

WO168 R4 exact candidate is `7d0fd83bb5608a4ab025d5000203cbad2a31831f`
on draft PR #242. Candidate branch/worktree/upstream are clean and identical. Exact-head
hosted CI `34440601328` completed SUCCESS across Windows/full, Ubuntu and macOS.

Sol/integrator independently re-ran deterministic exact-SHA checks: focused harness/backend
64 PASS, real Mac Claude 2.1.152 synthetic loopback 6 PASS, related frontier 227 PASS /
12 expected skips, compileall/diff/credential-pattern checks PASS, with no new confirmed
P0/P1/P2. However Sol authored part of the inherited R4 filesystem repair, so this evidence
is not used as the sole independent R3 review. A fresh read-only Codex review session also
hit the shared usage limit and produced no acceptance result. The review gate remains
`REVIEW_BLOCKED`, not waived.

### Planned Windows 11 primary-host handoff

The user's next session will return primary development to the Windows 11 PC and use
Sunday-Worker 1-5. GitHub already holds the full frozen R4 candidate on PR #242; `main`
remains at `577d9483720c857a89a5d2c9ea9359f9c0aa50b5` until the independent review gate
passes. On Windows: fetch/prune first, fast-forward the local main only, inspect actual
worktrees/claims, assign one free Worker to an independent read-only exact-SHA review of
PR #242, then let the GPT integrator accept/merge with expected-head fencing if P0/P1/P2=0.
After post-main CI succeeds, pull main again so Windows and Mac can converge on the same
accepted merge. Do not delete historical Mac worktrees/branches during this handoff.

### Windows 11 primary-host continuation checkpoint — 2026-09-10

This checkpoint supersedes the earlier *planned Windows return* wording above without
rewriting its historical chronology.

Actual Windows repository/runtime state was re-pinned before further work:
- protected root: `A:\GitHub\A-Wiki-Conductor`, `main@f4ecf9a8e5a3aa9f92e3cd4ee4c16125f45e43e2`;
- fetched `origin/main = 577d9483720c857a89a5d2c9ea9359f9c0aa50b5`; root is behind 585;
- root remains protected/dirty: the QR working blob is already identical to the accepted
  `origin/main` blob, and untracked `$null` is a 54-byte shell-diagnostic artifact, but no
  reset/clean/stash/restore/pull was used to bypass the clean-root precondition;
- WO168 R4 / PR #242 remains Draft at exact head
  `7d0fd83bb5608a4ab025d5000203cbad2a31831f`, with exact-head CI `34440601328`
  SUCCESS across Windows/full, Ubuntu and macOS and no independent acceptance verdict yet.

Additional deterministic exact-SHA Windows evidence was gathered from a disposable archive,
not the protected root: focused harness/host/backend verification = **63 passed / 7 skipped**;
broader supervised/provider/resolver/config-store verification = **127 passed**;
`compileall` and `git diff --check` PASS; a real Windows directory-junction escape probe for
`.claude` fails closed as `CLAUDE_SETTINGS_INVALID`. These checks strengthen evidence but do
not substitute for the required independent R3 review.

Independent GLM/ZCode diagnostic evidence identified the earlier direct-headless 401 root
cause without changing repository or ZCode configuration: Desktop and direct headless ZCode
load different provider config files; the headless record lacked the custom Cointh key and
fell through to an unrelated ambient `ANTHROPIC_API_KEY`. A bounded positive headless probe
with the legitimate Cointh credential returned `AUTH_ROUTE_OK`. Current accepted WO158
production source already avoids this ambient-env defect: it resolves the accepted secret-ref,
delivers it ephemerally as `ANTHROPIC_API_KEY`, and constructs the ZCode child environment
without parent-environment inheritance. Do not duplicate the secret into a second ZCode config
as the Zero-Relay architecture.

Installed/live truth is intentionally separate from current source truth. The running
`A-Sunday Conductor.exe` SHA-256
`9432D96E867C486D012AA797C3D764103AABEAA97D8F2C068FAD9D84BAD3AC87` exactly matches the
released v0.6.0 artifact recorded by WO63, while current source declares v0.7.0 and WO96 remains
an active P0 release blocker. The live `control-center.sqlite` is healthy (`integrity_check=ok`)
but still has no `provider_*` tables. Do not force-upgrade the installed v0.6.0 application or
migrate its live DB merely to prove Zero-Relay. The next live model proof should use current
source in an isolated proof runtime with sacrificial/copied control state and the authorized
provider route.

Issue #213 already records GPT1-authorized `PROOF_C` lifecycle PASS on 2026-09-09, so that
ZCode stdin-EOF lifecycle proof must not be rerun. The remaining ZRA-1 live gate is one real,
harmless no-human-relay model task bound to canonical provider snapshot + admission +
WorkerLease + verified task packet, with exact result identity and no orphan execution.
Read-only future-node shaping is checkpointed on Issue #214 comment `5618617122`, Issue #215
comment `5618660853`, and Issue #216 comment `5618664042`; those notes do not release their
dependency gates or create new authorities.

A future ZCode/Hermes/OpenCode-style custom Provider Settings console is captured separately by
WO170 / Draft PR #243 and is deliberately deferred until Zero-Relay is accepted through ZRA-4.
It must not displace this P0 path.

Current exact next safe action for WO168 remains: obtain a genuinely independent exact-SHA
review of PR #242. Durable long-run GLM packet `WO-P1-172` / `GLM-MARATHON-5H-001` can perform
that review first and then continue the Zero-Relay queue without human result copy-back. Only
an exact `PASS` with P0=P1=P2=0 at the freshly re-pinned PR #242 head may open the fenced
merge gate.

### WO169 Windows-continuation freeze / claim release

Windows continuation docs were verified and checkpointed as commit
`941bf194194bd5e85ca1dc8ecdbd05e47915b60f` on the existing PR #238 branch. The checkpoint
changed exactly the three WO169-owned docs files; `git diff --check`, strict UTF-8 and full-file
credential-value pattern scans passed. No product source/tests/global continuity/private
secret/runtime/provider/Worker state was mutated.

This lane no longer needs mutable ownership. The final metadata-only release commit is pushed
to the same Draft PR #238 and Issue #233 records its exact final head. PR #238 remains pending
independent docs/security review; release of this docs claim is not merge/acceptance authority.
