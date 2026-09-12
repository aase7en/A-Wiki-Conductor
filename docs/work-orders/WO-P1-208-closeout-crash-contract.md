# WO-P1-208 — Closeout crash-boundary proof and GLM campaign

Status: DESIGN_PREPARED_FOR_PARENT_REVIEW / GLM_CHILD_QUEUED
Date: 2026-09-12
Owner: Poppy Javis / GPT-6 Astra / home macOS
Claim: WO208-ASTRA-CLOSEOUT-PROOF-001
Parent: Issue214 / WO165; consumes WO205, whose owner retains Phase-D authority
Risk: R2 non-binding design/evidence; future production changes R3, NOT authorized here
Base: 02d39cbd9bca1ab3bb19b6e0cfbb0766c991f971
Branch: codex/wo-p1-208-closeout-crash-contract
Mac worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo208

## Scope and purpose

User authorized a difficult Astra analysis plus a sustained bounded GLM packet after
sending WO196 to GLM. Extend WO205's restart/version-conflict proof with real-store
crash-cut counterexamples and explicit external-effect port obligations. Do not duplicate
Phase-C/D architecture, WO204 independent review, WO196 identity lab or WO206 controller.
Source/accepted semantics remain unchanged; proposed obligations require parent acceptance.

Owned tracked paths:
- docs/work-orders/WO-P1-208-closeout-crash-contract.md
- docs/plans/2026-09-12-closeout-crash-boundary-contract.md
- docs/reviews/WO-P1-208-closeout-crash-evidence.md
- docs/prompts/GLM-WO208-CLOSEOUT-CRASH-LAB.md
Ignored: runs/WO-P1-208/; owned synthetic temp roots wo208-* only.
All production source/tests, other WOs, global CURRENT-WORK/handoff/COLLAB, A-Wiki,
private storage, live databases/processes/providers and active Windows worktrees read-only.

## Reuse and ownership gate

Classification EXTEND existing WO205 evidence requirements; REUSE GoalCloseoutExecutor,
SQLiteJobStore and existing checkpoint/recovery patterns. No new production store,
scheduler, job lifecycle, lease, outbox or controller. A-Wiki authoritative main checked
at 566637ac8d2636d6c63eda2bd6ebe81b55bd3d72; existing cross-agent work-order protocol reused.
Current main/source verified; fresh clean isolated scope; no matching WO208 branch/doc
found. Public claim is posted to Issues214/233 before deeper experiments.

Known owners stay unchanged: WO201 PhaseC, WO205 PhaseD, WO203 repair/WO204 review,
WO196 identity lab, WO197/198 ZRA4, WO200/206 master, WO202 process cleanup, WO207 launcher.
GLM child is QUEUED, not a second live goal; no preemption or escape from master stop gates.

## Acceptance

- Pin source symbols/blob IDs and distinguish planner facts from runtime guarantees.
- Reproduce meaningful crash/concurrency boundaries with real sacrificial job store and
  labelled synthetic effect ports; include positive controls and replayable evidence.
- Propose smallest same-authority recovery obligations; disclose unsupported cases.
- Deliver finite GLM campaign with exact immutable input/output scope, checkpoints,
  no-progress/quota/ownership stops and no source/merge authority.
- Validate docs/UTF8/diff/scope, push exact SHA, draft PR and public Windows pointer.

## Checkpoint

Bootstrap only. Parent implementation and acceptance are not transferred. Next: publish
claim, then execute native Mac synthetic probes and write contract/evidence/lab packet.
Global continuity fold remains with the existing single writer; scoped WO + public issue
checkpoint supply its fold-in evidence.


### Native proof and packet checkpoint — 2026-09-12

Public reservation: Issue214 comment5639611854 / Issue233 comment5639612131.
Completed native Mac source-seam proof: concurrent callers produced two synthetic fold
file effects but one checkpoint; stale facts produced an effect before CAS rejected;
unsafe UNKNOWN reentry repeated an effect after reopening; truthful positive reload kept
one effect and reached COMPLETE then ALREADY_COMPLETE. Real JobStore/executor; synthetic
ports/facts only. These are not production incidents or actual power-loss tests.

Existing closeout/store baseline: 94 passed in 0.30s, exit0. Source blob pins and the exact
replayable Python probe plus captured output are in the tracked evidence document.
No production GoalCloseoutExecutor instantiation found under src at base. Parent must
establish actual reachability/exclusion before assigning production defect severity.

Deliverables: non-binding crash/effect contract plus nine-program GLM campaign (10–18h
useful work, up to24 only if justified; finish early if done). Child evidence scope is
NEW docs/reviews/WO-P1-208-glm-closeout-lab.md and appended checkpoints in this WO on its
own branch; ignored runs/WO-P1-208/glm only for executable lab artifacts. No source changes.
WO196/WO204/WO206 current goals are not preempted. Child QUEUED, not launched.

Next safe action: validate/freeze/push docs, prepare clean canonical-byte Windows child
worktree, publish exact delivery SHA/hashes/PR pointer to Issues214/233. Parent design
acceptance remains pending; WO205 retains PhaseD scope. No merge from this lane.


## Child claim — WO208-GLM-CLOSEOUT-LAB-001 (2026-09-12, Windows GLM)

- Claim started by user goal pointer at delivery `b1d52d0c03100f0bfffd9a4adca0c6240f43ac2c` (worktree HEAD verified == pointer; branch `codex/wo-p1-208-glm-closeout-lab`, clean, on base `02d39cb`).
- Identity verified: packet SHA-256 `849d7c87...de93639`; proposal `5c3dcd55...add7d2`; seed `96a5bbc1...d0e0b6b6`; all four source/test blob IDs MATCH (goal_closeout `0acdf8c9`, job_store `bde34b6f`, job_state `816784b4`, test_goal_closeout `b4055cae`).
- WO205 read via `git show origin/docs/wo-p1-205-zra2-phase-d-gate:...` without switching branches. Parent Phase-D authority and WO201/205 source HOLD intact. WO206 master is parked at its own BLOCKED_EXTERNAL_GPT_ACCEPTANCE gate; not disturbed.
- Writable scope: NEW `docs/reviews/WO-P1-208-glm-closeout-lab.md`, append-only checkpoints here, ignored `runs/WO-P1-208/glm/**` (wo208- prefixed temp roots). All src/tests read-only.
- Owner: this GLM session (WO208-GLM-CLOSEOUT-LAB-001); capacity gate passed (evidence-only docs lane; no active owner of this child found in Issue #214/#233 latest).
- SAFE_TO_RUN_LAB=YES under packet synthetic-only rules.


### GLM lab completion checkpoint — WO208-GLM-CLOSEOUT-LAB-001 (2026-09-12)

All programs C00-C08 DONE with native Windows evidence: seed reproduces verbatim (hash typo F1 recorded); real child-process cut matrix (os._exit at each boundary) with safe restart (1 effect -> COMPLETE) vs unsafe restart (2 effects after REAL crash) vs concurrent two-process barrier race (2 effects); lost-acknowledgment matrix proves only the reopened journal distinguishes commit-vs-not; lab owner-gate suppresses the stale effect (residual TOCTOU -> DESIGN_DECISION_REQUIRED); destination-enforced idempotent receipts proven incl. two-process single winner; odd lease port contract recorded (F2); 96-state finite model: conservative policy 0 violations, unsafe blind-retry caught (negative control). Decision packet for WO205 in the tracked handback. COMPLETE_FOR_PARENT_REVIEW; product implementation remains HOLD with the parent integrator. No source/test mutation; other lanes untouched.


### Astra lab-review reservation — 2026-09-12

Claim WO208-ASTRA-LAB-REVIEW-001. User reports GLM complete and requests high-reasoning
follow-up plus a durable next-task pointer. Review exact lab b3a553ca3bb51753daa84b5f6be0dc81f1d025d6;
its branch/worktree stays frozen. Original proposal accepted DESIGN ONLY by Sol; this is
independent review of GLM lab evidence, not self-acceptance of the Astra architecture.
Review worktree /Users/aase7en/Desktop/A-Wiki-Conductor-wo208-review;
branch codex/wo-p1-208-lab-review; R2 docs/evidence review, no source authorization.
Owned: this scoped checkpoint; NEW docs/reviews/WO-P1-208-astra-lab-review.md;
NEW docs/prompts/GLM-WO208-CLOSEOUT-REPAIR.md. Ignored runs/WO-P1-208/review for read-only
artifact copies and synthetic reviewer experiments. All original packet/proposal/seed,
GLM report, source/tests, global SSoT, other WOs/live runtime/A-Wiki remain immutable.
No new controller, broad audit, source fix or merge. Existing WO205 owner decides PhaseD.

Initial review observations (not final verdict): F1 hash typo claim contradicted by exact
original recorded/computed hash on both Mac and Windows; C03 report explicitly says final
transition fault injection was preempted by FOLD_CHECKPOINT_MISSING. Need inspect actual
lab programs, controls and portable replay before acceptance. Next: publish claim, inspect
frozen artifacts, adjudicate and publish one bounded same-WO repair packet if required.

### Astra lab review completed / bounded repair prepared — 2026-09-12

Reviewed frozen GLM lab b3a553ca3bb51753daa84b5f6be0dc81f1d025d6. Verdict:
CHANGES_REQUIRED (LAB EVIDENCE), not a production defect/severity claim. Sol's original
DESIGN_ONLY acceptance is preserved. Five P2 evidence gaps: unreachable COMPLETE fault
hooks, drivers that return success despite failed expectations, finite-model claim gaps,
version-dependent receipt identity coverage, and nonportable ignored-only scripts.
F1's alleged seed hash typo is independently falsified on both hosts; original immutable
seed is correct. Useful seed/fold-checkpoint/concurrency observations remain evidence.

Targeted native Mac proofs: C03 both COMPLETE variants stop at FOLD_CHECKPOINT_MISSING;
C07 unsafe candidate emits I1=8/I3=8 but exits0; unsupported COMPLETE action unvalidated;
C05 same operation prefix with v8/v9 creates two receipt rows. Native Windows C03 rerun
confirms unreachable hooks. No production source/tests/global SSoT/other lane mutation.
Full review: docs/reviews/WO-P1-208-astra-lab-review.md. Ignored local reviewer proofs:
runs/WO-P1-208/review/. Source base and original lab remain frozen.

Successor packet: docs/prompts/GLM-WO208-CLOSEOUT-REPAIR.md;
task WO208-GLM-CLOSEOUT-REPAIR-001, PREPARED_NOT_STARTED / QUEUED_CAPACITY.
Prepared target branch codex/wo-p1-208-glm-closeout-repair at exact review delivery;
Windows A:/GitHub/_worktrees/A-Wiki-Conductor-wo208-glm-closeout-repair.
Review delivery SHA/hash/worktree verification are published externally in Issue214/233
to avoid self-referential commit hashes. The child claims before execution.
Assigned repair writes on its own branch: original GLM report correction, appended WO
checkpoints, and eight explicitly named research-bundle paths in the packet (one optional).
Ignored runs/WO-P1-208/glm-repair only; source/tests remain immutable. This scoped extension
does not grant production or global SSoT authority and does not reopen the frozen lab.

Current coordination refresh: origin/main cfcb369fe5ab3a50569defa822289f10f2f38aac;
Phase B post-main accepted at 8700d21887500965ffc33bcbffa1f33602d9c2f6; WO216 C0 separately
released by Sol (Issue214 comment5640984367). Do not preempt that goal or the current master.
WO205 source still needs its own dependency/acceptance/release gates; this lab is not accepted.
Next safe action: publish exact review delivery, prepare/verify Windows repair lane, then
one eligible GLM session follows the packet. Exact repaired candidate returns for independent
review; no merge by Astra/GLM. Global CURRENT-WORK/handoff fold remains with the single writer,
fed by this scoped checkpoint plus Issue214/233, as the original WO requires.


## GLM repair claim — WO208-GLM-CLOSEOUT-REPAIR-001 (2026-09-12)

- Claim per repair packet at HEAD `1c8d8259e29ce634bc8d6c44d29eec1126da319a` (worktree clean, HEAD == review delivery as required).
- Immutable inputs verified: packet SHA-256 `3422c736...dcf41b5`; review `0a3b6d92...9b16bad`; proposal `5c3dcd55...add7d2`; seed doc `96a5bbc1...d0e0b6b6`; all four source/test blob IDs MATCH (`0acdf8c9`, `bde34b6f`, `816784b4`, `b4055cae`).
- Five frozen artifacts recovered from the frozen lab worktree (its HEAD verified `b3a553c`, tracked-clean) into owned `runs/WO-P1-208/glm-repair/original/`; **all five raw SHA-256 + byte sizes match the review table exactly** (no normalization needed).
- F1 retraction verified at startup: the recorded digest in seed/review/packet is uniformly `...addda6c1301a579aac` and equals the freshly computed fence hash — the original "…6a1301 typo" claim was this lane's own misreading and will be retracted per R-F1.
- Scope: the three writable paths from the packet only (corrected lab review doc, append-only WO checkpoints, NEW bundle under `docs/reviews/wo208-closeout-lab/`). Frozen lab worktree/branch untouched. No collision with any active goal (WO214 master parked at its own external gate; separate worktrees/claims).

### GLM repair completion — WO208-GLM-CLOSEOUT-REPAIR-001 (2026-09-12)

All repair programs P0–P6 complete at this branch: R1 COMPLETE lost-ack pair rebuilt on real prerequisites with hook-entry proof; R2 strict enforcement everywhere (cut markers, distinct fallback exits, negative controls, strict two-process predicates); R3 72-state action-validating transition model with 7/7 named mutants caught and unsupported actions rejected; R4 stable operation identity across version advance + separate-effect atomicity cut; R5 tracked replayable bundle + manifest, replayed from a clean Windows export (baseline 94 + all four entrypoints exit 0); F1 RETRACTED with byte-level proof (uniform digest across all three documents; original misread). Corrected handback prepended to the original review doc with the full supersession map; original provenance retained verbatim. F2/F3 retained as parent decision inputs. STATUS=COMPLETE_FOR_INDEPENDENT_REVIEW (MAC_REPLAY_PENDING for the reviewer); no source mutation, no merge, frozen lab branch untouched.
