# WO-P1-162 — GLM-First Execution + Universal Agent Entry

Date: 2026-09-04 (opened as WO-P1-157; renumbered 2026-09-07)
Owner: GLM-1 (continuation of the GPT-B drafting lane)
Status: RECONCILED_ON_MAIN / READY_FOR_FOCUSED_REREVIEW
Priority: P0 delivery-throughput hardening
Repository: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo157-glm-first-entry
Branch: docs/wo-p1-157-glm-first-entry (transport name only; WO identity is WO-P1-162)
Renumber: WO-P1-157 → WO-P1-162 per the GPT1 integration checkpoint on PR #219 — GPT2 / Issue #210 keeps WO157/AIP-3.
Original stacked base: 0fd540c622d4539a2e809b8a441661896179f2ad
Current base after PR221 merge: df5a25f1f9949e6938ea4bbcf0150515e6e5fa85
Dependencies: PR #208, PR #218, PR #209 and PR #221 SATISFIED; current main is df5a25f1f9949e6938ea4bbcf0150515e6e5fa85
Risk: R2 process/governance change
Classification: EXTEND existing Fast Execution protocol; no new scheduler/router/runtime authority

## Goal

Make every new chat/session/agent enter A-Sunday Conductor through one short, deterministic startup protocol and make GLM/ZCode the default bounded implementation engine while GPT remains architecture, trust, integration, acceptance, merge, and release authority.

The workflow must reduce prompt relay and repeated ceremony without weakening repository ownership, secret, destructive-operation, deterministic verification, exact-SHA review, or release gates.

## Allowed mutable scope

- 00-AGENT-ENTRY.md
- PROJECT-GRAPH.yaml
- AGENTS.md
- PROJECT-PLAN.md
- CURRENT-WORK.md
- handoff.md
- COLLAB.md
- docs/agent-collab/FAST_EXECUTION_PROTOCOL.md
- docs/agent-collab/COLLAB_PROTOCOL.md
- docs/agent-collab/CAPABILITY_MATRIX.md
- docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md
- this work order
- one new concise agent-entry protocol under docs/agent-collab/
- docs/USER-GUIDE.md
- docs/contracts/recovery-reconciliation.md

## Forbidden scope

- PR #208 candidate branch
- PR #209 branch
- PR #211 coordination branch
- WO155 source/tests/work-order frozen candidate
- WO156 source/tests/work-order
- ODP source/tests/worktrees
- product source/tests/runtime
- live DB, credentials, ZCode config, Worker processes

## Design decisions

1. Universal entry is file-first and starts at AGENTS.md.
2. Startup reading becomes risk/context selective after the mandatory continuity core, rather than forcing all large design/product docs for every task.
3. Mandatory continuity core:
   AGENTS.md -> actual Git/worktree/claim state -> CURRENT-WORK.md -> handoff.md -> active WO -> only graph/protocol/design nodes required by task.
4. DEFECT_LESSONS.md remains mandatory before src/a_conductor mutation.
5. READY bounded implementation defaults to GLM/ZCode when capable/ready/authorized; GPT owns planning boundaries and final acceptance.
6. GPT does not regenerate long bespoke prompts when a durable WO/task packet already exists. Manual fallback is one pointer command to the packet.
7. Zero-Relay later removes even that pointer command after R3 acceptance; workflow must work safely before Zero-Relay is complete.
8. Deterministic evidence remains completion authority.
9. R0/R1/R2/R3 shortest truthful assurance path remains binding.
10. Maximum default WIP remains 3 mutable lanes + 1 independent read-only review lane.

## Acceptance

- All listed canonical workflow files agree on entry order and GLM-first/GPT-governance role split.
- No contradiction with PR208 Fast Execution safety invariants.
- No instruction requires chat memory as authority.
- No instruction tells an agent to bypass claim/secret/destructive/review gates.
- No change to product source/runtime behavior.
- diff-check and strict UTF-8 pass.
- independent exact-SHA review required because this is R2.
- merge order: PR208 -> WO157.


## Implementation checkpoint - 2026-09-04

Claim established first on remote branch `docs/wo-p1-157-glm-first-entry` at commit `f2ba49f`.

Implemented policy/docs changes:
- added universal front door `00-AGENT-ENTRY.md`;
- added task-selective `PROJECT-GRAPH.yaml`;
- added `docs/agent-collab/AGENT_ENTRY_PROTOCOL.md`;
- updated `AGENTS.md` so every execution surface uses the same startup core;
- updated Fast Execution, provider-neutral collaboration, capability routing, top-level collaboration and product plan to the same GLM-first/GPT-governance model;
- updated Zero-Relay roadmap maturity language so the current WO155 preview is treated as prototype/callability evidence, not production acceptance;
- preserved current live `CURRENT-WORK.md` / `handoff.md` ownership with GPT-A; no mutation of those shared hotspots in this lane.
- synchronized developer/recovery entry wording in `docs/USER-GUIDE.md` and `docs/contracts/recovery-reconciliation.md` after fresh-agent contradiction audit.

Current workflow can be used before Zero-Relay is complete through one-pointer human relay. Zero-Relay later removes only the transport step.

Deterministic docs validation passed across the 15-file canonical set: diff-check, strict UTF-8, YAML parse, required-path/reference check, secret-shape scan, and canonical old-entry contradiction search. Independent exact-SHA review remains required before merge.

- GLM independent R2 review of e486350/13a5f62 found WO157-F1 (P2): COLLAB.md Pause/Resume still prescribed the superseded entry order. This lane repaired that one canonical line; exact old-entry remnants are now zero under the focused sweep, UTF-8/YAML/diff-check pass, and focused exact-SHA re-review is required.

## Recomposition checkpoint - 2026-09-05

- PR #208 / WO154 is merged/released; PR #218 / WO156 is also merged/released. Current main is `f0ddd0b9245cef7a7525a670f470e1de595d4615`; PR #209 incident/runbook evidence is also merged while installed self-heal E2E remains pending.
- PR208 merge released the shared continuity hotspots; WO157 scope is explicitly amended to fold current truth into `CURRENT-WORK.md` and `handoff.md` before freeze.
- WO157 was recomposed again by non-force merge of current main `f0ddd0b9245cef7a7525a670f470e1de595d4615`; no rebase/reset/clean/stash/force-push used.
- Known `COLLAB.md` claims-table conflict was resolved by preserving merged PR208 truth, retaining WO155 preview/shaping status, and updating WO157 to current-main successor status.
- Post-merge semantic validation PASS on the 15-file docs-only delta: old-entry remnants 0, strict UTF-8/no-U+FFFD PASS, secret-shape PASS, YAML/path references PASS, git diff-check PASS, operator protocol 37/37 PASS. Exact-head CI + focused independent rereview remain required before PR219 acceptance.

## WO162 reconciliation checkpoint — 2026-09-07 (GLM-1)

- **Renumber**: WO-P1-157 → WO-P1-162 per the GPT1 integration checkpoint on PR #219 (GPT2 / Issue #210 keeps WO157/AIP-3). File renamed `WO-P1-162-glm-first-execution-entry.md`; branch name retained as PR #219 transport only. Historical checkpoint text above keeps its original WO157 wording as evidence.
- **PR #220 folded and MERGED**: stacked repair head `a55041175a6709d01710fd2f0f2c8ddd7cd8bb49` merged into this lane by non-force merge (`50f20fe`); its semantics were already `STACKED_REPAIR_SEMANTICS = PASS` with exact-head CI `33947807332` SUCCESS. **PR #220 is MERGED into this branch** (merge commit `50f20fe59679803b02557e75538faa9ea3c5de22`, observed 2026-09-07T01:47:34Z).
- **Recomposed onto current main** `df5a25f1f9949e6938ea4bbcf0150515e6e5fa85` by non-force merge (`f56d532`); no rebase/reset/clean/stash/force-push. The `CURRENT-WORK.md` / `handoff.md` conflicts were resolved as a newest-first union that preserves every WO158 r1-r6 evidence section from main.
- **Current truth folded** (supersedes the stale text below): PR #221 / WO-P1-158 / ZRA-1 is MERGED (`df5a25f`, merged 2026-09-06T22:32:41Z, post-main CI `34064328672` SUCCESS, accepted head `01517ea` is an ancestor). ZRA-0 is ACCEPTED/CLOSED. The `READY_FOR_GPT1_EXACT_SHA_ACCEPTANCE` projections that main carried past the merge were MERGED_NOT_FOLDED drift; this lane is the fold-back. Frontier: A-Wiki #54 (ZR-1, GLM1/Q25 claim, clean isolated worktree) → ZRA-2 (#214) → ZRA-3 (#215) → ZRA-4 (#216). PR #222 (WO159) and PR #223 are separate open drafts; PR #211 stays historical/do-not-merge.
- **New governance rule**: `AGENT_ENTRY_PROTOCOL.md` §2 now classifies state disagreement as `STALE_LOCAL_CHECKOUT` (local view behind remote; remote SSoT not implicated) vs `SSOT_DRIFT` / `MERGED_NOT_FOLDED` (canonical remote evidence contradicts tracked continuity projections; dependent mutation blocked until fold-back) vs `UNKNOWN` (fail closed). This is the durable rule form of the defect this checkpoint repaired.
- Exact frozen head for rereview: this commit (SHA recorded in PR #219). GLM-1 does not merge; GPT1 focused rereview + exact-head CI + GPT-A acceptance/merge remain required.

## WO162 final governance repair checkpoint — 2026-09-07 (GLM-1)

- Binding input: GPT1 focused rereview of `a4ee9539fd5903720eb08fc31983dc96df1432c7` (comment `5563933645`; exact-head CI `34074156876` Windows/Ubuntu/macOS all SUCCESS) = CHANGES_REQUIRED / MERGE_READY NO. Repairs are bounded to that review; no P0-B source work, no A-Wiki #54, no ZRA-2/3/4.
- **P1-1 repaired** — exactly one current authority: `CURRENT-WORK.md` and `handoff.md` each carry a single-authority rule inside the top WO162 section plus a `HISTORICAL EVIDENCE` separator; the 2026-09-05 "Post-PR208 … (authoritative)" sections and the 2026-09-03 "authoritative/current" headers are re-marked `HISTORICAL / SUPERSEDED BY WO162`. Historical evidence is preserved, not deleted.
- **P1-2 repaired** — PR #220 observed MERGED into this branch (`50f20fe`, 2026-09-07T01:47:34Z) folded into all current WO162 projections (this doc, CURRENT-WORK, handoff, COLLAB). The earlier "can close after PR #219 merges" wording is superseded.
- **Issue #213 reconciled** — ZRA-1 preflight durable claim closed as completed with exact PR221 acceptance evidence (accepted head `01517ea`, merge `df5a25f`, post-main CI `34064328672` SUCCESS); GitHub no longer shows OPEN + stale CHANGES_REQUIRED.
- **P2-1 repaired** — PR #219 title/body refreshed to WO-P1-162 identity, current base/main/candidate SHA, PR221/ZRA-1 MERGED, ZRA-0 ACCEPTED/CLOSED, PR220 MERGED, frontier `A-Wiki #54 → ZRA-2 → ZRA-3 → ZRA-4`, current gates, GLM no-self-merge.
- Verification on this repair head: git diff --check PASS; strict UTF-8/no-U+FFFD; PROJECT-GRAPH.yaml parse OK; `tests/test_operator_protocol.py` PASS; single-authority contradiction scan PASS (exactly one `(authoritative)` current section per file; all other authority-worded headers marked HISTORICAL); scope audit = governance/continuity files only vs `main@df5a25f`; added-line secret scan 0 hits.
- Stop state: **READY_FOR_GPT1_FINAL_WO162_ACCEPTANCE** at this commit's exact head (SHA + CI in PR #219 evidence). GLM-1 does not merge.
