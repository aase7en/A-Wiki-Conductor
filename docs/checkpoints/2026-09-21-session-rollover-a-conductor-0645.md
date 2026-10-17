# Session rollover checkpoint — A-Sunday Conductor — 2026-09-21

Created for intentional ChatGPT session/context rotation.

Status: DURABLE CHECKPOINT / RECOVER-FIRST
Topology: CONTROL_PLANE_ONLY
Authority repo: `A:\GitHub\A-Wiki-Conductor`
Execution repo: `A:\GitHub\SunDayRemoteMCP`
Checkpoint base: `main@777779e83873a6f2b9f02b71a8944189102a73a2`
Checkpoint branch: `checkpoint/session-rollover-20260921-0645`
Checkpoint worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-rollover-20260921-0645`

## 1. Resume rule

A fresh session must start:

`RECOVER -> VERIFY ACTUAL GIT/GITHUB/RUNTIME -> HARVEST TERMINAL RESULTS -> RECONCILE CLAIMS -> CONTINUE NEXT SAFE ACTION`

Do not recreate work from chat memory. Do not redispatch terminal reviewers. Do not mutate the protected root checkout.

Read in the normal entry sequence:
1. uploaded A-Sunday global protocol;
2. repo `00-AGENT-ENTRY.md`;
3. `PROJECT-GRAPH.yaml`;
4. `AGENTS.md`;
5. actual Git/GitHub/runtime;
6. this checkpoint;
7. active Issue/WO documents only as needed.

## 2. Critical current-main truth

At checkpoint creation:

- remote `main`: `777779e83873a6f2b9f02b71a8944189102a73a2`;
- commit is PR #454 / WO452 merge;
- main push CI `35567284564`: **SUCCESS**;
- Windows job includes GUI/core suites, packaging, Portable smoke, and Frozen Setup install/uninstall E2E;
- macOS and Ubuntu smoke: SUCCESS.

Any new session must re-query `main` before relying on this SHA.

## 3. Protected root checkout — DO NOT TOUCH

Root checkout:

`A:\GitHub\A-Wiki-Conductor`

Observed state at rollover:

- branch: `main`;
- local HEAD: `1a5ea1b8574f783c002589ffe3fb51b30303e24c`;
- upstream: `origin/main`;
- local root is **66 commits behind** remote main;
- untracked/protected entries include:
  - `$null`
  - `0`
  - `docs/prompts/GLM-WO230-ZRA2-REVIEW-TASK-CONTRACT-AUTHORITY.md`

Rules:

- no reset;
- no clean;
- no stash;
- no checkout/switch over that root;
- no assumption that those files are disposable.

Use fresh isolated worktrees from actual remote main.

## 4. WO452 — COMPLETE / CLOSED

Issue: #452
PR: #454
Purpose: ZRA-3A graph-run authority + successor activation-binding design

Accepted exact design candidate:

`3e8a3086c5053de638b9a91314526e83ec33f3a8`

Merge/current main:

`777779e83873a6f2b9f02b71a8944189102a73a2`

Evidence:

- independent R3 A0004: PASS_DESIGN;
- P0/P1/P2/P3 = `0/0/0/5`;
- GPT-5.6 Sol adjudication: ACCEPTED;
- exact-head CI `35565209196`: SUCCESS;
- post-main CI `35567284564`: SUCCESS.

Issue #452 was folded and CLOSED during rollover preparation.

Historical design worktree:

`A:\GitHub\_worktrees\A-Wiki-Conductor-wo452-design`

Observed:

- branch `docs/wo-p1-452-zra3a-design`;
- HEAD `3e8a3086c5053de638b9a91314526e83ec33f3a8`;
- remote branch equals HEAD;
- clean;
- merged/historical — do not resume source work there.

## 5. ZRA-3 parent ownership

Parent Issue: #215

Binding ownership split remains:

- #215 owns automatic accepted-completion -> NEXT_READY continuation/selection;
- accepted #433 owns generic/manual production runtime activation;
- no successor work may create a second scheduler/job/task/claim/lease/retry/review/completion authority.

A final parent checkpoint was added during rollover noting WO452 complete and Child A #461 as the next bounded source slice.

## 6. Next Windows implementation frontier — Issue #461

Issue #461:
`ZRA-3A Child A — GraphStore v2 run-authority persistence foundation`

State at rollover:

- OPEN;
- R3;
- CONTROL_PLANE_ONLY;
- `NOT_CLAIMED`;
- worktree: NONE;
- branch: NONE;
- tracked source mutation: NONE.

WO452 post-main prerequisite is now satisfied.

Expected bounded ownership after a fresh claim:

Allowed hypothesis:
- `docs/work-orders/WO-P1-461-graphstore-v2-run-authority.md`
- `src/a_conductor/graph/store.py`
- `tests/test_graph_store.py`
- `tests/test_graph_run_authority.py` only if RED matrix warrants it.

Forbidden unless a new reviewed finding expands scope:
- `runtime_activation.py`;
- scheduler/ready/dispatch;
- ControlCenter/project registry;
- provider/lease/job/execution stores;
- graph domain model;
- graph `__init__` exports;
- Mac WO453 / SunDayRemoteMCP;
- WO449 Browser-Wake files.

Before any #461 source mutation, a new session must:

1. re-pin actual current main;
2. re-pin #215/#433/#449/#453 ownership/collisions;
3. read `DEFECT_LESSONS.md`;
4. create a fresh isolated #461 worktree/branch;
5. publish exact claim/owner/base/HEAD/scope;
6. add RED tests before production code.

Do not assume source release solely from this checkpoint.

## 7. Windows-other lane — WO449 / PR #460

Owner: Windows other session
Issue: #449
PR: #460
Purpose: Browser Wake contract security repair
Current candidate:

`9a57fb4de66eee13c33b2af05c3a5ae3368457d4`

Base:

`777779e83873a6f2b9f02b71a8944189102a73a2`

Tracked diff is the WO449 three-file Browser-Wake repair scope. This rollover session does not own those files.

### Independent cycle-3 review

Detached worktree:

`A:\GitHub\_worktrees\A-Wiki-Conductor-review-wo449-9a57fb4`

Run:

`run:WO-P1-449:r3-rereview-cycle3:1:a1:6aa68091fdd2`

Pointer state:

- TERMINAL;
- exit code 0;
- finished `2026-09-21T06:40:20.754436Z`;
- final git status clean;
- exact candidate/base correct.

Reviewer verdict:

- **PASS**
- P0=0
- P1=0
- P2=0
- P3=2

Reviewer independently ran:
- 99 focused tests PASS;
- 229 expanded tests PASS;
- independent secret-shape/harmless-marker probes PASS;
- diff-check clean;
- review tree clean.

**Do not redispatch this reviewer.**

### WO449 exact-head CI

Run:

`35567781770`

At checkpoint recovery around 06:52Z:

- head SHA: `9a57fb4...`;
- Ubuntu smoke: SUCCESS;
- macOS smoke: SUCCESS;
- Windows `test` rerun: **IN_PROGRESS**;
- job id: `106239785113`;
- it had restarted at `2026-09-21T06:49:20Z` after earlier GUI flake attempts.

Replay rule:

- do not rerun again while this exact job is live;
- owner session must harvest terminal CI, adjudicate reviewer P3, and merge only if exact-head gates pass;
- this checkpoint grants no takeover authority over WO449.

## 8. Mac lane — WO453 / PR #456

Owner: Mac other session
Issue: #453
PR: #456
Purpose: FMG-PROD canonical SRM cutover design

Current exact candidate:

`2a49df85a537765259b3503602abe5e818bac456`

Base/current-main at candidate freeze:

`777779e83873a6f2b9f02b71a8944189102a73a2`

PR state at checkpoint:

- OPEN;
- DRAFT;
- MERGEABLE;
- exact-head CI `35567805260`: SUCCESS on Windows/macOS/Ubuntu.

Mac ownership remains sole mutable ownership of:

`docs/work-orders/WO-P1-453-fmg-prod-canonical-srm-cutover.md`

Windows must not edit WO453 or mutate/restart SRM canonical runtime.

Mac has explicitly requested one independent exact-SHA R3 Windows reviewer.

Review preconditions:

- no A-Sunday independent reviewer currently live;
- fresh CoinTH quota/readiness immediately before dispatch;
- exact model `cointh-glm/glm-5.3`;
- MAX;
- detached clean tree at exact candidate;
- mutable scope EMPTY.

At rollover, no WO453 reviewer had been dispatched from this Windows session.

A new Windows session may perform the review only after fresh recovery confirms:
- WO449 reviewer remains terminal;
- no new independent A-Sunday reviewer has started;
- exact PR456 head/base are unchanged;
- provider route is READY/ADMITTED.

## 9. Review-lane occupancy

At the latest process census:

- no live WO449/WO452/WO453 A-Sunday reviewer process was found;
- WO449 cycle-3 reviewer is terminal and must not be redispatched;
- WO452 reviewers are terminal/historical;
- WO453 review is NOT_STARTED from this session.

There is a live Kilo reviewer for the ENV project; it is a separate project and does not itself consume A-Sunday mutation authority, but exact process identity must still be respected.

Always recover actual process/pointer state before dispatch.

## 10. CURRENT-WORK / handoff hotspot conflict

Do **not** assume `CURRENT-WORK.md` or `handoff.md` on main contains this rollover.

Open PR #316 currently modifies both global continuity hotspots:

- `CURRENT-WORK.md`
- `handoff.md`

Therefore this rollover intentionally did **not** mutate those two files.

Classification:

`CLAIM_CONFLICT / SAFE_TO_MUTATE_GLOBAL_CONTINUITY_HOTSPOTS = NO`

This checkpoint file plus Issue #215/#461 comments is the durable rollover pointer until that hotspot ownership is reconciled.

A fresh session should prefer:

actual Git/GitHub/runtime -> this checkpoint -> Issue #215/#461 -> current work-order files

before trusting stale global projections.

## 11. Protected / forbidden operations after rotation

Do not:

- reset/clean/stash the protected root checkout;
- redispatch completed WO452 reviewers;
- redispatch WO449 cycle-3 reviewer;
- mutate WO449 Browser-Wake scope from the new Windows session unless ownership is explicitly transferred;
- mutate Mac WO453 scope;
- create Child A source changes before a fresh #461 claim;
- merge any PR using stale base/head evidence;
- expose CoinTH/provider secrets.

Before every material GLM dispatch, refresh CoinTH quota/readiness through the approved secret-safe resolver.

## 12. Exact next-safe-action order for a fresh Windows session

1. Run the normal A-Sunday startup/read protocol.
2. Recover actual remote `main`, PR #460, PR #456, Issues #449/#453/#461, process census, and delegated-run pointers.
3. Harvest WO449 CI `35567781770` if terminal; do not take over its mutable lane.
4. If the A-Sunday independent review slot is free and PR #456 head/base remain exact, service the Mac WO453 independent R3 review baton after fresh CoinTH preflight.
5. Separately prepare #461 only after re-pinning collision/ownership state:
   - read `DEFECT_LESSONS.md`;
   - create fresh isolated worktree;
   - bind claim and exact scope;
   - RED-first.
6. Continue roadmap automatically under A-Faster until a real authority/safety gate appears.

## 13. Replay-safety summary

- WO452: COMPLETE_VERIFIED / CLOSED; no replay.
- WO449 cycle-3 reviewer: COMPLETE_VERIFIED; no reviewer replay.
- WO449 exact-head CI: RUNNING at checkpoint; harvest before retry.
- WO453 exact-head CI: COMPLETE_VERIFIED; independent review NOT_STARTED.
- WO461 source implementation: NOT_STARTED / NOT_CLAIMED; safe only after fresh claim gate.
- protected root checkout: UNKNOWN USER WORK / PROTECTED; no destructive operation.

## 14. Session rotation verdict

Context state: RED / rotation requested by user.

No new non-trivial work should start in the old chat after this checkpoint.

New session must recover actual state rather than assume this snapshot is still current.
