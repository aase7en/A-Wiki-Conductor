# WO196 — GLM physical workspace identity proof lab

Task: WO196-GLM-C1-LAB-001
Status: PREPARED / USER-STARTED GOAL / EVIDENCE ONLY
Parent: WO-P1-196, bounded C1 child of Issue216 GPT1-ZRA4-PREFLIGHT-001
Executor: one fresh Windows ZCode / GLM-5.3 session
Design owner: Poppy Javis / GPT-6 Astra on home Mac
Acceptance: existing GPT1/Sol integrator, parent ZRA-4 owner
Product implementation: HOLD — this packet never authorizes it

## 1. Goal

Turn the physical-identity proposal into an adversarial, reproducible engineering lab:
prove native alias behavior, model resource conflicts, minimize admission failures,
prototype host observation outside production, and hand the parent integrator a precise
implementation-readiness matrix. Spend roughly 10–16h of useful work, up to20h when
new evidence justifies it. Finish early if objectives are met. No token quota, repeated
passing stress loops or artificial workload. Respect real provider usage/availability.

The user starts Goal mode in the installed ZCode surface and pastes a pointer here.
Continue bounded programs without asking the human to carry results or type continue.
If this ZCode session is already running WO193/191/192/194/195 or another goal, this
pointer does not cancel or transfer it. Use a separate eligible session/worktree, or queue
this packet until its owner finishes. Never reuse a busy workspace to save startup time.

## 2. Exact starting identity

Repository: https://github.com/aase7en/A-Wiki-Conductor.git
Source baseline: 46f90b329d4991211f5c8a26406f3aca2162e9a7
Delivery source branch: codex/wo-p1-196-physical-identity-spec
GLM branch: codex/wo-p1-196-glm-identity-lab
Windows worktree: A:/GitHub/_worktrees/A-Wiki-Conductor-wo196-glm-identity-lab
Work order: docs/work-orders/WO-P1-196-physical-workspace-identity.md
Design: docs/plans/2026-09-11-physical-workspace-identity-contract.md
Result: runs/WO-P1-196/glm/result.json and result.md
Portable tracked handback: docs/reviews/WO-P1-196-glm-identity-lab.md

Use the exact containing delivery commit named by the human pointer/Issue216 handoff,
not a mutable branch tip. Record that SHA plus SHA-256 of this packet and the design at
startup. The delivery must descend from the source baseline with NO production source
changes. Verify these source Git blob IDs (not SHA-256 file hashes):
registry.py 5a50d3d6717c8230992518f21730271c0fd3f2f1;
worker_lease.py dad529bbb2670439f9ae2a76d3f15a61a93d91b4;
graph/analyze.py 670b5e84258550b0f2a36510cbf9b52bc3af1b09.

Git CRLF checkout can change raw packet bytes. If a hash mismatch occurs, inspect it
before use. Do not normalize and silently accept a mismatching packet. Obtain the
exact committed blob in this owned clean scope, compare it to the declared hash, and
record any rematerialization; do not change global Git configuration. The prepared
Windows worktree should already contain the canonical bytes.

## 3. Startup / claim / anti-duplication

Read the repository front door and routed nodes, actual CURRENT-WORK, this WO, design,
Issue216 latest comments, Issue233 current checkpoint and open PR scopes. Keep parent
ZRA4 ownership and source hold intact. Check actual branch/HEAD/dirty owner; verify
worktree matches the declared path and existing prepared branch. Fetch never grants
permission to merge/rebase/reset/switch another worktree.

Before any lab/prototype writes publish WO196-GLM-C1-LAB-001 in a checkpoint in THIS WO
on the GLM branch, with exact source/delivery/packet identity, owner, paths and available
capacity. Commit/push that docs checkpoint and post its pointer to Issue216. Do not
claim an active slot from a stale/no-process observation; follow the repo WIP policy.
If another session owns this exact child or resource, STOP_COLLISION/QUEUED_CAPACITY.
No co-writers or background subagents. This task does not hold source mutation scope.

Work-order numbers are not unique enough in this repository snapshot: two WO195 branches
refer to different goals. Identify every neighboring task with repo + claim + branch +
path + SHA. Do not resolve ownership by guessing which WO number is newer.

Known exclusions: WO193 output attestation; WO191/WO195 production continuation;
WO192/194 live Worker/launcher recovery; WO195 ZRA2 PhaseB materialization
(feat/wo-p1-195-zra2-phase-b-materializer); parent C2 batch
identity/fan-in; all SundayFamily MCP capability/fork work. Consume their existing
relevant evidence without implementing or re-auditing their full programs.

## 4. Writable scope

Tracked files allowed ON THE GLM BRANCH:
- NEW docs/reviews/WO-P1-196-glm-identity-lab.md
- docs/work-orders/WO-P1-196-physical-workspace-identity.md (append child checkpoints only)

Ignored: runs/WO-P1-196/glm/ for code prototypes, test corpus, sacrificial databases,
manifest/results and a task-local environment if necessary. New tempfile roots must be
created by this process with a wo196- prefix and recorded. All prototypes are research
artifacts, not production modules/imports. Include small replayable code/patch excerpts
in the tracked handback so the result is not lost if ignored storage is unavailable.

Everything else is read-only: src/**, tests/**, shared/global docs, existing other WOs,
this packet/design, .github/**, packaging/config/locks, A-Wiki/private Drive, ZCode state,
Worker launchers, active databases, provider credentials, installed runtimes and other
projects. No source fixes, live aliases/drive mappings, fleet operations or process kills.

Synthetic directory symlinks/junctions/hard links under an owned tempfile are allowed.
No elevated privilege request merely to create one: record SKIPPED_NOT_SUPPORTED if the
host refuses. Never point a synthetic link at the real project, home directory, Drive,
installed application, live database or network share. Use only local sacrificial targets.
Remove each created link itself before its own target cleanup; never recursively traverse
a link into a target. If target ownership becomes uncertain, retain the fixture and report.

Local Git fixtures with no remotes are allowed under the lab/temp root, using one empty
synthetic commit and linked worktrees. No push/network fetch inside a synthetic fixture.
No Git configuration change to the user's repositories or account. Do not scan disks or
create multi-GB corpora. Use stdlib/available pytest and Git; no global package installation.

## 5. Required conceptual boundaries

The design's four identities are non-interchangeable: logical project, physical worktree,
actual write resource and shared Git metadata. A path/hash/HEAD/project label is not a
physical object. Same physical root across different project labels must still conflict.
Same GitHub origin across independent clones is not proof of shared local files.

Observer results are SAME / DISTINCT_WITHIN_SUPPORTED_DOMAIN / UNKNOWN. Unknown must
not mean free to mutate. Registry remains pure. Observer provenance must not come from
caller-supplied verified=True/host_id fields. Initial proposal is host-local under one
existing lease authority; cross-host shares/enrollment are not implemented in the lab.

Root canonicalization is only alias detection. It does not automatically prove exclusive
admission, anchored I/O or cross-host coordination. A repeated stat before write leaves a
TOCTOU window. Hard links/nested roots/shared Git state can defeat simplistic root keys.
Keep authorization separate from a conservative resource reservation. Preserve the
existing glob solver semantics; do not invent a new scheduler or lock database.

## 6. Sequential programs

| Program | Target effort | Mandatory artifact |
|---|---:|---|
| L00 claim/consume prior evidence | 0.5h | source/owner/packet manifest |
| L01 native Windows root alias matrix | 1–1.5h | minimized native observations |
| L02 broker exclusion reproducer | 1–1.5h | real sacrificial-store RED/control |
| L03 observer prototype and support table | 1.5–2.5h | native adapter experiment, not production |
| L04 case/scope/Unicode/namespace cases | 1–2h | semantic ambiguity matrix |
| L05 hardlink/nested/nonexistent resources | 1–1.5h | conflict-footprint counterexamples |
| L06 deterministic TOCTOU barriers | 1.5–2h | operation-boundary evidence |
| L07 Git shared-resource lab | 1h | per-worktree/common resource map |
| L08 copied-state migration model | 1–1.5h | old/new authority failure matrix |
| L09 reduce/model-check/handback | 1–2h | bounded oracle + implementation gates |

Estimates are guidance, not mandatory runtime. Do not repeat a settled investigation just
because it is listed below. Reuse parent Q18/Q59 and WO196 native proof; add counterexamples,
negative controls and supported-host depth. Checkpoint each program before moving on.

### L00 — startup manifest

Record actual Windows/Python/Git versions without environment dumps. Capture source blob
IDs, packet/design SHA-256, branch/HEAD, capacity/owner disposition and existing evidence
consumed. Distinguish native observation, simulation, source reasoning and untested claim.
Create an invariant-to-evidence ledger, not another project roadmap or claim system.

### L01 — alias identity observations

Within a new tempfile create real root plus junction alias. Compare lexical key, final
resolved path and native object identity. Cover nested junction and alternate spellings;
8.3 aliases only if enabled, with explicit skip if unavailable. Do not enable system-wide
8.3 support, developer mode or elevation. Positive control: two distinct directories.
Record which APIs succeeded and why UNKNOWN is necessary when they fail. Do not claim
SMB behavior from an NTFS test or use a live network share to fill that evidence gap.

### L02 — real broker RED, not an invented alternative broker

Reuse tests.test_worker_lease helpers and the real WorkerLeaseBroker/SQLiteWorkerLeaseStore.
Create two synthetic READY candidates with distinct worker/session/task IDs, same mutable
scope, actual and alias roots. Preserve fake facts as labelled fixture data. Demonstrate
both leases currently succeed. Negative control: same spelling + conflicting scope must
be refused by the existing broker. A fresh copied DB is used per case; no live table.

Repeat with different project labels using consistent request/candidate fixtures and
record whether physical conflict is masked. Use two store instances to explore atomic
query behavior with barriers. Never patch source, inspect live leases or release another
worker. The desired eventual behavior is one winner or typed refusal, not two winners.
A failing baseline is expected evidence, not permission to fix it in this lab.

### L03 — observation adapter prototype

Prototype Windows directory-handle observation under runs/WO-P1-196/glm/prototypes/ using
bounded stdlib ctypes calls after reading current Microsoft API contracts. Set argtypes,
restype and INVALID_HANDLE_VALUE handling correctly; close every owned handle in finally.
Document file-open flags, directory access, share modes, reparse behavior and 128-bit IDs.
No arbitrary device paths or privilege changes. Compare volume serial/file ID for two
open handles and keep final path as explanation. Produce UNKNOWN on unsupported results;
never derive a trusted host namespace from an environment variable supplied by a task.

Mac adapter work here is a model/source plan unless native Mac tools are independently
available through an authorized lane. Do not label simulated POSIX code as native Mac proof.
Reuse Astra native Mac observations and leave specific missing Mac cases for its owner.

### L04 — case and scope semantics

Build a finite corpus for separators, dot segments, absolute/drive-relative paths, ADS,
trailing dots/spaces, Unicode forms and wildcard grammar. Use synthetic fixtures to learn
actual case behavior; do not assume it from the OS name. Do not normalize away an escape
before authorization. Compare current graph.analyze.write_sets_overlap behavior with the
proposal's validation predicates; retain the existing fnmatch-style language semantics.

Record authorized / conflicting / unsupported separately. In the proposal model, broad
root reservation must not grant broad write authority. Unknown scope interpretation means
unsupported or conservative exclusion, never a more permissive path. Keep corpus entries
short and parameterized with bounded case IDs (avoid Windows PYTEST_CURRENT_TEST overflow).

### L05 — physical footprint beyond the root

Use hard-linked files under synthetic independent/nested roots. Show distinct root IDs do
not imply distinct file objects. Test nested worktree roots, child links and nonexistent
leaves. Propose exact first-slice refusals and characterize what a future anchored writer
must prove. nlink inspection is evidence at an instant, not a guarantee no link can appear
later. Do not recursively scan an entire repository to claim hardlink absence.

For nonexistent paths model nearest existing anchored parent + constrained suffix with
strict validation. No fabricated future file ID. Distinguish replacement from in-place
editing: atomic replacement can have different hardlink effects, but cannot be silently
substituted for every operation. Record the accepted operation class as a decision input.

### L06 — TOCTOU experiments

Use deterministic events/barriers: observe -> before lease -> after lease -> before open/
write -> after possible side effect. Swap only owned temporary path components, and use a
synthetic outside sentinel inside the same temporary lab as the forbidden target. An unsafe
prototype may demonstrate sentinel modification; it must never target real user files.
Compare resolve-then-open against an anchored proof candidate, but do not claim a generic
safe writer from one passing case. A post-side-effect mismatch is recovery, not retry.

Record handle lifetime, object replacement/reuse, cleanup and capability limitations.
Stop immediately if a fixture path escapes its owned lab. No broad process killer or
real Worker concurrency; native helper subprocesses have finite timeout and exact ownership.

### L07 — Git resource domains

Create a temporary Git repo without remote, one fixture commit and linked worktrees.
Use Git rev-parse to identify absolute git dir/common dir, then compare native objects.
Demonstrate separate data roots but shared common metadata. Classify operations from
actual repo adapters: file edit, index/HEAD update, common refs/config/maintenance.
Do not execute destructive maintenance or alter real branches. Git's own lock semantics
are retained; do not implement a competing lock daemon. Unclassified mutation stays gated.

### L08 — version/migration model with copied state only

List actual lexical worktree-key writers/readers. Build an in-memory state model or
sacrificial SQLite copy illustrating old owner alive -> new writer sees incomparable key
-> second lease hazard. Model a stopped-intake migration and a same-authority version fence.
A fake migration that simply deletes active rows is invalid. Recovery/expired uncertainty
must keep ownership/capacity until existing accepted evidence permits release.

Show failure cases for interrupted migration, rollback with active new-format owners,
unsupported old writer, missing observation and remounted root. Produce decision inputs
for the integrator; do not select or apply a live schema migration.

### L09 — bounded model, minimization and handback

Build a small pure model with explicit state enumeration for observations, active owners,
resource classes, writer version and operation capability. Check invariants over a finite
state space and report its bounds. This is not a model of the whole OS. Avoid random huge
stress matrices without a hypothesis. Reuse/minimize equivalent cases, preserve seeds and
show negative controls can catch the original failure.

For each proposed implementation slice list exact likely source consumers, API questions,
required source claim and whether prerequisites are accepted or pending. Do not mint a
new WO or start product implementation. The outcome is READY_FOR_PARENT_DESIGN_REVIEW or
DESIGN_GAPS, with source mutation still HOLD. Commit/push the allowed docs handback and
publish its branch/SHA in Issue216. No human result copy-back and no merge.

## 7. Concrete execution and evidence rules

Run the existing narrow baseline once:

```text
python -m pytest -q tests/test_worker_lease.py
```

Write each lab experiment under the ignored prototypes directory. Each command should
terminate within a documented bound (normally <=60 seconds per process). Long analysis
continues across checkpoints; it is not one unbounded process. Capture raw child output
with binary Python I/O when byte identity matters. Never use implicit PowerShell text
rewrites of UTF-8 files. Check exit codes individually; a later successful command cannot
turn an earlier failed proof into PASS.

Manifest each experiment: claim, delivery/source/probe SHA, host/runtime/API, synthetic
fixture ownership, expected result, observed result, native/simulated, exit code, elapsed
time and cleanup outcome. Artifacts must not contain secret values, home listings, private
config or unrelated logs. Limit raw logs/corpus; summarize at semantic boundaries.

Runtime errors are not safety verdicts. Two attempts failing identically without new
information trigger ROOT_CAUSE/STOP_NO_PROGRESS rather than infinite retries. A failed
proof never authorizes broadening source or runtime scope. No repeated polls for merge.

## 8. Resume and checkpoints

After every program, blocker or context rollover write runs/WO-P1-196/glm/checkpoint.json
and append concise status to the scoped WO on this branch. Include completed programs,
owned dirty files, source/packet hashes, invariant gaps, result locations and next action.
Commit/push at meaningful milestones. On resume verify actual owner/branch/HEAD and read
that same checkpoint; do not rebuild the lab or rerun every predecessor automatically.

Stop at COMPLETE_FOR_PARENT_REVIEW, DESIGN_GAPS, STOP_COLLISION, QUEUED_CAPACITY,
SOURCE_DRIFT, ENVIRONMENT_BLOCKED, SAFETY_BLOCK or STOP_NO_PROGRESS. Record what is done
and what is not. Do not proceed to another campaign when this one ends.

## 9. Required result

runs/WO-P1-196/glm/result.json must include:
work_order, child_claim, status, repo, branch, source_sha, delivery_sha, packet_sha256,
design_sha256, host, programs, experiments, findings, source_consumer_map, decisions_pending,
changed_tracked_files, cleanup, elapsed_hours, independent_review_status, merge_performed,
next_safe_action. Set merge_performed=false. Compute candidate_sha after the final commit
and record it in the public handoff/result without circular self-hashing.

Each finding names exact input/API/source identity and has a minimized replay command.
Native evidence and model inference are separate. A probe author cannot supply the sole
independent acceptance review of that probe. Retain gaps honestly: source/current tests
can be correct at their declared metadata boundary while insufficient for a broader
physical-isolation claim. Do not call every unsupported case an exploitable production bug.

Tracked docs/reviews/WO-P1-196-glm-identity-lab.md must carry the compact matrix, explicit
source hold, commands, API references, small prototype excerpts, probe hashes and links
needed for cold-start review. Raw ignored files alone are not a durable cross-machine
handoff. Parent integrator reads this branch/result directly; no repeated custom prompts.

## 10. What this packet does not finish

It does not make ZRA4 operational, fix existing lease/source code, complete ZRA2/ZRA3,
merge WO193, deploy Worker self-heal or authorize shared network workspaces. A finished
lab removes design uncertainty so GLM can implement a later exact-scope accepted packet.
The expensive Astra work is the failure model and decomposition; this lab does the
repeatable experiments, model checking, minimization and evidence packaging.
