# WO-P1-196 — Physical workspace identity design and evidence

Status: DESIGN DELIVERED FOR PARENT REVIEW / GLM LAB PREPARED_NOT_STARTED
Claim: WO196-ASTRA-C1-DESIGN-001
Owner: Poppy Javis / GPT-6 Astra / home macOS Codex
Parent: Issue #216 / GPT1-ZRA4-PREFLIGHT-001 (GPT1 retains ZRA-4 authority)
Date: 2026-09-11
Risk: R2 design packet; proposed production work is R3 and NOT authorized here
Base: 46f90b329d4991211f5c8a26406f3aca2162e9a7
Branch: codex/wo-p1-196-physical-identity-spec
Mac worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo196

## User authority and non-overlap

User explicitly asked the home Mac Astra task to take the difficult identity planning
subtask, publish it for Windows visibility and give GLM a short file pointer. This is a
bounded C1 design/evidence extension of existing Q18/Q59 findings, not a duplicate
ZRA-4 preflight or transfer of the parent claim. No C2 batch/fan-in/source ownership.
Issue216 parent still blocks implementation until ZRA-3 acceptance. Proposed designs
remain unaccepted until the parent integrator reviews them.

Owned additive tracked paths:
- this work order
- docs/plans/2026-09-11-physical-workspace-identity-contract.md
- docs/prompts/GLM-WO196-PHYSICAL-IDENTITY-LAB.md
Ignored owned evidence: runs/WO-P1-196/; synthetic tempfile fixtures only.
All source/tests/global continuity/A-Wiki/private/runtime/provider paths are read-only.
No active Windows project rebinding or live process/lease/DB operations. Remote Windows
observations/proofs use Sunday Worker only and explicit isolated paths.

Before deeper work: commit/push this bootstrap and publish Issue216 + Issue233 scope.
Reuse existing claim/WO/evidence protocol; do not create another claim store or scheduler.

## Deliverable

An implementation-ready proposal for physical root identity, resource conflict domains,
case/path/scope semantics and migration/fencing limits; source-mapped synthetic native
Mac/Windows observations; a bounded GLM evidence-lab packet runnable now without product
mutation. Future product implementation needs parent acceptance/dependency/claim gates.

## Acceptance of this planning task

- Existing identity/conflict/lease call paths mapped at the base SHA.
- Alias and shared Git metadata counterexamples demonstrated with synthetic data.
- Explicit distinction: logical repo vs local worktree vs physical write resource vs
  shared Git metadata; cross-host equality is not guessed from path or remote URL.
- TOCTOU, hard links, nonexistent targets, unsupported filesystems and legacy leases
  have conservative dispositions, not optimistic normalization.
- GLM packet has precise immutable inputs, writable evidence-only scope, finite programs,
  restart/checkpoint/output instructions and explicit product-implementation hold.
- UTF-8/link/scope checks; exact delivery/packet hash; clean/pushed branch and draft PR;
  public handoff for Windows. No merge and no claim of accepted ZRA-4 safety.

## Checkpoint

Bootstrap: source/read-only issue evidence inspected. Existing parent authority retained.
Known adjacent lanes: WO193 byte validation; WO191/WO195 ZRA3 composition; WO192/194 Worker
runtime; another local WO195 is ZRA2 PhaseB. Never route from WO number alone: exact claim,
branch, path and SHA are required. No source changes will occur in WO196.


### Design delivery checkpoint — 2026-09-11

The proposal and ten-program GLM packet are complete for parent review. Production
implementation and ZRA4 acceptance remain HOLD; this is not a source fix or independent
acceptance. GLM is PREPARED_NOT_STARTED and must claim capacity before writing its lab.

Native synthetic evidence at the pinned source:
- Mac symlink and Windows junction refer to the same directory object, yet lexical keys
  differ. The real WorkerLeaseBroker grants LEASED + LEASED for the same src/a.py scope
  with two distinct fake READY workers in one sacrificial SQLite store (two active rows).
- Mac hardlinks refer to one file object while literal scopes appear disjoint. Dot-segment
  and alternate-separator forms also expose scope projection questions.
- Mac synthetic linked Git worktrees have different physical data roots and the same
  physical Git common directory. No fixture has a remote or touches a live runtime.
- These are isolated broker/resource counterexamples, not proof of production overwrite.

Mac and Windows source blobs matched; full identities and results are in the proposal.
Local ignored replay/evidence: runs/WO-P1-196/mac_probe.py and mac-proof.json. The proposal
preserves portable observations; the GLM handback must add minimized replay excerpts.

The design separates root/resource/Git identity, authorization vs reservation, observation
vs anchored I/O, and host-local scope vs unsupported cross-host shared storage. It reuses
the existing registry/glob/lease/dispatch authorities and gates legacy migration. The GLM
packet allows only its new review document, appended child WO checkpoints, and ignored
synthetic lab artifacts. Source, existing tests and other lane workspaces remain immutable.

Claim visibility:
- https://github.com/aase7en/A-Wiki-Conductor/issues/216#issuecomment-5635827069
- https://github.com/aase7en/A-Wiki-Conductor/issues/233#issuecomment-5635827405

Exact delivery SHA, packet/design SHA-256, prepared Windows worktree and draft PR will be
recorded in the Issue216/233 delivery handoff after the commit, avoiding circular hashes.
Global CURRENT-WORK/handoff projections remain with their existing single writer; this
scoped checkpoint and the public issue handoff are the integrator's fold-in input.
Next: GLM claims the separate evidence lane when capacity permits, executes the packet,
and publishes its exact-SHA handback for the parent integrator. Do not merge or auto-start
production implementation when the lab finishes.


### GLM lab claim — WO196-GLM-C1-LAB-001 (2026-09-12, Windows)

- Claim WO196-GLM-C1-LAB-001 started by user goal pointer at delivery SHA `10dca359568c216983199a6899b0af3863b5e9d7` (worktree HEAD verified == pointer; branch `codex/wo-p1-196-glm-identity-lab`, clean, on source baseline `46f90b3`).
- Identity verified: packet SHA-256 `24f5969b2fbd252809187d52158ad72a8ee5f17290d892dbd1e66f072fbe44fe`; design SHA-256 `b131c0248a7f9f9aa12f49991d8576cd2a7e7ec3d70a20b4c5a5eb48537babc3`; source blob IDs MATCH for registry.py / worker_lease.py / graph/analyze.py.
- Latest Issue #216 closeout observed: design delivered + DESIGN-ONLY acceptance; Windows lab PREPARED_NOT_STARTED/QUEUED_CAPACITY → this claim fills that queue slot; no other session owns this child. Host DESKTOP-7IB57R4, Windows 11 x64, Python 3.11.15, git available. Parent ZRA-4 ownership + product implementation HOLD intact.
- Writable scope (exact): NEW `docs/reviews/WO-P1-196-glm-identity-lab.md`, append-only checkpoints in this WO, ignored `runs/WO-P1-196/glm/`. All src/tests read-only. WO200 lane untouched and unmodified (separate claim/worktree; parked at its own external CI gate).
- SAFE_TO_RUN_LAB=YES within the packet's synthetic-fixture rules (wo196- prefixed tempfile roots; junctions/hardlinks only at sacrificial local targets; no elevation; no network).


### GLM lab completion checkpoint — WO196-GLM-C1-LAB-001 (2026-09-12)

All programs L00-L09 DONE with native Windows evidence: alias matrix (incl. the new NT-prefix vector), real-broker alias RED (LEASED+LEASED incl. cross-project), observer prototype + support table (FileIdInfo unsupported on this volume -> legacy ids), 10-class scope gap corpus, hardlink/replace footprint, TOCTOU escape + anchored candidate, Git common-dir domain, migration-fence model (delete-rows INVALID), 108-state model check (conservative policy 0 violations). Verdict: READY_FOR_PARENT_DESIGN_REVIEW; product implementation remains HOLD. Tracked handback: docs/reviews/WO-P1-196-glm-identity-lab.md; machine result: runs/WO-P1-196/glm/result.json. No source/test mutation; WO200 and every other lane untouched.
