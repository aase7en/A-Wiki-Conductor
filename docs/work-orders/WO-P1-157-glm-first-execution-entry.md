# WO-P1-157 — GLM-First Execution + Universal Agent Entry

Date: 2026-09-04
Owner: GPT-B / this chat
Status: RECOMPOSED_ON_MAIN / READY_FOR_FOCUSED_REREVIEW
Priority: P0 delivery-throughput hardening
Repository: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo157-glm-first-entry
Branch: docs/wo-p1-157-glm-first-entry
Original stacked base: 0fd540c622d4539a2e809b8a441661896179f2ad
Current base after PR218 merge: aa257f47ac3d0979c9b749896745cab6ce197975
Dependencies: PR #208 and PR #218 SATISFIED; current main is aa257f47ac3d0979c9b749896745cab6ce197975
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

- PR #208 / WO154 is merged/released; PR #218 / WO156 is also merged/released. Current main is `aa257f47ac3d0979c9b749896745cab6ce197975`.
- PR208 merge released the shared continuity hotspots; WO157 scope is explicitly amended to fold current truth into `CURRENT-WORK.md` and `handoff.md` before freeze.
- WO157 was recomposed again by non-force merge of current main `aa257f47ac3d0979c9b749896745cab6ce197975`; no rebase/reset/clean/stash/force-push used.
- Known `COLLAB.md` claims-table conflict was resolved by preserving merged PR208 truth, retaining WO155 preview/shaping status, and updating WO157 to current-main successor status.
- Post-merge semantic validation PASS on the 15-file docs-only delta: old-entry remnants 0, strict UTF-8/no-U+FFFD PASS, secret-shape PASS, YAML/path references PASS, git diff-check PASS, operator protocol 37/37 PASS. Exact-head CI + focused independent rereview remain required before PR219 acceptance.
