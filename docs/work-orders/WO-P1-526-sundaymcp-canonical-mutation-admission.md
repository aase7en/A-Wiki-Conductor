# WO-P1-526 — SundayMCP canonical mutation admission + exact worktree binding

Status: P0 DOCS ACTIVE / SOURCE NOT AUTHORIZED
Issue: #526
Parent: #495
Topology: CROSS_REPO
Risk: R3 — mutation admission / concurrency / durable execution / repository identity
Owner/integrator: GPT-5.6 Sol
Claim: WO-P1-526-SUNDAYMCP-ADMISSION-MAC-001
Authority repo: A-Wiki-Conductor
Authority base at claim: d3f319a64fd4cef03a7fe5e23a676ba6db8d4b2b
Authority worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo526-sundaymcp-admission
Branch: docs/wo-p1-526-sundaymcp-admission
Execution substrate in P0: /Users/aase7en/GitHub/SunDayRemoteMCP
Observed SRM branch/HEAD: main @ 2f033cfb1f61b6dff9c2e55264cca6f2a9125e95
SRM remote state: LOCAL_ONLY / no configured Git remote / GitHub repo not found

## 1. Goal

Close the three acceptance gaps exposed by the terminal #525 three-session canary
without creating a second admission, claim, scheduler, retry, project, or completion authority.

The production mutation path must prove, before process spawn:

1. canonical A-Conductor WorkerLease / hotspot admission is the winning authority;
2. the admitted exact target worktree, branch, HEAD, task/claim generation and mutable scope
   are the same lane that SundayMCP will execute;
3. SRM execution-substrate identity is independently pinned and cannot be confused with
   the target worktree identity;
4. stale session / Active Project / device generation cannot redirect the mutation;
5. duplicate or conflicting sessions fail closed before consequential side effect.

P0 is architecture and failure-model freeze only. It authorizes mutation of this WO file only.

## 2. Recovered evidence

### 2.1 #525 terminal canary

#525 is CLOSED with verdict `ISSUE_525_PASS_NOT_PROVEN`; it MUST NOT be replayed.

Positive evidence:
- one SESSION_A ignored effect only;
- SESSION_B fenced before process start by exact-scope `scope-timeout`;
- SESSION_C made no write and refused to invent mutation authority;
- duplicate effects = 0;
- tracked changes = 0;
- exact owner cleanup completed.

Acceptance gaps:
- SESSION_A `sunday_status.claimPresent=false`;
- no direct canonical Mac WorkerLease proof accompanied the winner;
- SESSION_A `cwd/canonicalPath` was canonical A-Wiki main while its exact mutable
  scope/effect was inside the canary worktree;
- SESSION_C never reached the same canonical collision-admission path.

### 2.2 `claimPresent` is not WorkerLease truth

Current SRM `sunday_status.claimPresent` is derived from existence of
`done-claim.json`. That file is executor completion-claim evidence.

Therefore:

```text
claimPresent=false
!= no A-Conductor WorkerLease
!= no project/task claim
= no SRM done-claim.json for that execution
```

P1 MUST NOT reuse or rename this field as lease/admission authority.

### 2.3 Current SRM path binding

Current `sunday_dispatch` accepts `cwd` and `scopes` independently.
When `cwd` is omitted the MCP boundary supplies `process.cwd()`.
The manifest stores that resolved cwd.

SRM then:
- canonicalizes `manifest.cwd` for `identity.json`;
- canonicalizes scopes separately as overlap/alias evidence;
- acquires the declared scopes independently.

This explains the #525 state where scope/effect targeted the canary worktree while
the execution canonical path described canonical main.

### 2.4 Current SRM identity conflation

Current `supervisor.ts` also calls `snapshotRepo(manifest.cwd)` when verifying
the admission compatibility SHA and during repo-binding evidence.

That means one `manifest.cwd` currently participates in two conceptually
different identities:
1. the target workspace in which the command actually executes; and
2. the repository whose SHA is compared with the admission compatibility member.

For SundayFamily multi-project execution these identities MUST be separable.
A target A-Wiki worktree and the SRM substrate source/build are not necessarily
the same physical repository and cannot be proven by one cwd field.

### 2.5 Canonical mutation admission already exists

Accepted #500 owns atomic WorkerLease / physical-hotspot admission.
Its production authority is `SQLiteWorkerLeaseStore` over the canonical
A-Conductor control database.

P1 MUST REUSE it. SRM PathLock / durable scope fencing remains defense-in-depth,
not a replacement WorkerLease authority.

### 2.6 Explicit lane binding already exists

Accepted #507 requires material requests to bind:

- authority/execution repo identity;
- canonical repo/worktree identity;
- branch + expected HEAD;
- task / Work Order;
- claim/lease + generation when applicable;
- mutable scope + mutation intent;
- execution_id + attempt_id;
- device_id + connection_generation for remote routing.

Serena/Worker Active Project is corroborating executor context only and never authority.

## 3. Reuse / wrap / extend decision

### REUSE — #500

Reuse the existing WorkerLease row, hotspot key, store identity and atomic
same-hotspot admission. No second SQLite DB, lease table, lock service or claim store.

### WRAP — #498

The executable pre-dispatch guard is the launch-time consumer of WorkerLease truth.
#526 does not take over #498.

Before integrated acceptance, #498 must close its durable blocking findings:
- `hotspot_key`;
- `required_capabilities`;
- `runtime_id`;
- `lease_ttl_seconds`.

Heartbeat / expiry lifecycle advancement remains distinct from immutable request identity.

### REUSE — DEX / #507

Reuse:
- `execution_id` / `attempt_id`;
- canonical physical root digest;
- Conductor-owned `binding_digest`;
- claim generation;
- exact SHA compatibility evidence;
- `device_id + connection_generation`;
- OUTCOME_UNKNOWN / no-blind-replay semantics.

### EXTEND — SRM verification boundary only

Extend SRM only enough to verify an already-admitted mutation target.
SRM still does not decide task ownership, WorkerLease admission, retry,
completion, review or acceptance.

## 4. Two identities that MUST NOT be conflated

### 4.1 TARGET_LANE_IDENTITY

This identifies where consequential work is allowed to run:

```text
target_repo
target_canonical_worktree_path
target_canonical_worktree_digest
target_branch
target_expected_head
task_or_work_order
claim_or_lease_ref
claim_generation
mutation_intent
mutable_scope
hotspot_key
execution_id
attempt_id
device_id + connection_generation when routed
```

For mutation, `cwd` MUST resolve to this exact canonical worktree identity.

### 4.2 SUBSTRATE_BUILD_IDENTITY

This identifies the SRM implementation/build providing execution capability:

```text
substrate = SunDayRemoteMCP
substrate_canonical_source_or_install_identity
substrate_exact_source/build_sha
device identity
boot / process creation identity as applicable
```

It is verified independently of target `cwd`.

A target repo HEAD MUST NOT be compared to the SRM substrate SHA, and the SRM
source tree MUST NOT substitute for the target lane worktree.

## 5. Canonical pre-spawn invariant

For an A-Conductor-governed consequential mutation, process spawn is allowed only if:

1. current durable task/claim generation is still valid;
2. #500 atomic WorkerLease admission is ACTIVE for the exact physical hotspot;
3. accepted #498 pre-dispatch guard revalidates the immutable lease/request identity;
4. target worktree physically canonicalizes successfully;
5. canonical(target `cwd`) == admitted target worktree canonical identity;
6. observed target branch == admitted branch;
7. observed target HEAD == admitted expected HEAD;
8. every mutable scope is inside/belongs to the admitted target lane and resolves to
   the expected physical hotspot set;
9. substrate build identity matches its separately pinned execution-substrate identity;
10. execution_id + attempt_id + binding_digest match the admitted attempt;
11. device_id + connection_generation match when remote/device routed;
12. no conflicting live/unknown execution or hotspot owner exists.

Any UNKNOWN or mismatch fails closed before shim/child spawn.

## 6. Smallest admission handoff

The control plane authors one bounded immutable admission reference.
It is evidence projected from existing authorities, not a new authority store.

Minimum semantic content:

```text
schema_version
execution_id
attempt_id
task_ref / work_order_ref
claim_ref
claim_generation
worker_lease_ref
worker_lease_store_identity
hotspot_key

target:
  repo_ref
  canonical_worktree_path
  canonical_worktree_digest
  branch
  expected_head
  mutable_scope_digest

substrate:
  repo_ref = SunDayRemoteMCP
  canonical_local_identity_ref
  exact_sha_or_build_digest

device:
  device_id
  connection_generation

binding_digest
```

The existing Conductor DEX binding digest remains the digest authority.
Do not create a second SRM digest authority.

## 7. SRM dispatch behavior

For the authority-bound mutation path:

1. require the admission/binding reference;
2. set/require `cwd` to the admitted target worktree, never a convenient caller default;
3. independently canonicalize the target cwd and compare to the admitted target identity;
4. observe target Git root/branch/HEAD and compare to target lane fields;
5. verify each declared mutable scope belongs to the admitted target/hotspot;
6. verify SRM substrate identity independently of target cwd;
7. only then run existing durable overlap checks / PathLock;
8. only then spawn the shim/child;
9. persist immutable verification evidence before/around spawn per DEX rules;
10. on response/session loss, recover the same execution identity — never respawn by assumption.

Standalone/read-only SRM operations may retain their existing degraded observation mode,
but they MUST NOT be presented as canonical A-Conductor mutation admission.

## 8. Local-only SunDayRemoteMCP identity

### Facts

Current Mac SRM checkout:
- canonical project path: `/Users/aase7en/GitHub/SunDayRemoteMCP`;
- branch: `main`;
- exact HEAD: `2f033cfb1f61b6dff9c2e55264cca6f2a9125e95`;
- tracked tree: clean at recovery;
- configured Git remote: none;
- package repository URL: not authoritative/blank;
- GitHub repository search under the owner did not find SunDayRemoteMCP.

Historical DEX acceptance already used a local-only SRM exact-SHA compatibility anchor,
but that historical SHA does not authorize mutation of the current SRM HEAD.

### P0 proposal — LOCAL_ONLY_CANONICAL

`REMOTE_UNVERIFIED` is not automatically equivalent to unknown physical identity.
A local-only execution repo MAY become an accepted mutation binding only after this exact
R3 contract is independently accepted and all of these are proven at P1 claim time:

1. explicit durable authority says local-only mutation binding is permitted for that lane;
2. canonical physical SRM path exists and is uniquely resolved on the target device;
3. exact SRM HEAD/build digest is pinned;
4. tracked ownership/dirty state is known;
5. no configured remote is falsely represented as a remote release;
6. branch/worktree and mutation scope are isolated;
7. device identity is explicit; a local-only binding cannot silently migrate to another device;
8. no push/PR/publication/remote-release claim is inferred;
9. any later remote creation or SHA/path drift invalidates the compatibility set and requires re-pin.

Until independent R3 acceptance of this proposal:
`SAFE_TO_MUTATE_EXECUTION_REPO = NO`.

## 9. Failure vocabulary

Reuse existing typed failures where semantics match:

- `PROJECT_IDENTITY_FAILED` — canonical physical identity cannot be proved;
- `CROSS_REPO_SHA_MISMATCH` — pinned compatibility member mismatches;
- `STALE_GENERATION` — claim generation is stale;
- `DUPLICATE_LIVE_ATTEMPT` — same binding already has live attempt;
- existing scope-overlap denial — defense-in-depth execution fence.

P1 may add bounded target-lane reasons only where existing codes are ambiguous:

- `TARGET_WORKTREE_BINDING_REQUIRED`;
- `TARGET_WORKTREE_MISMATCH`;
- `TARGET_BRANCH_MISMATCH`;
- `TARGET_HEAD_MISMATCH`;
- `TARGET_SCOPE_MISMATCH`;
- `SUBSTRATE_IDENTITY_UNRESOLVED`;
- `DEVICE_GENERATION_MISMATCH`.

No failure code grants retry authority.

## 10. Required RED / fault gates before source implementation acceptance

Deterministic tests must prove:

1. exact admitted target worktree + branch + HEAD + scope can reach spawn;
2. #525 regression: scope points into canary worktree but cwd points at canonical main -> reject before spawn;
3. same repo name but wrong physical worktree -> reject before spawn;
4. correct worktree but wrong branch -> reject before spawn;
5. correct branch but HEAD drift -> reject before spawn;
6. scope outside admitted target worktree/hotspot -> reject before spawn;
7. canonical alias to the same physical target follows documented alias semantics;
8. alias to different physical target -> reject;
9. target HEAD cannot satisfy or substitute for SRM substrate SHA;
10. SRM substrate SHA/build mismatch -> reject independently of target cwd;
11. stale claim generation -> reject before spawn;
12. each #498 immutable WorkerLease identity drift -> guard DENY before SRM dispatch;
13. heartbeat/expires_at lifecycle advancement alone remains allowed by #498 semantics;
14. same execution/attempt/binding duplicate -> recover existing attempt, no second child;
15. conflicting duplicate binding -> typed rejection;
16. stale device connection_generation -> reject before delivery/spawn;
17. Active Project mismatch cannot redirect target;
18. `claimPresent=false` never gets interpreted as absence of WorkerLease;
19. three simultaneous sessions on one admitted physical hotspot -> exactly one canonical winner,
    two canonical losers denied before process start, zero duplicate effects;
20. response/ChatGPT/MCP loss after admission -> recover original durable identity, no blind replay.

The final three-session mutation race is a NEW canary after implementation acceptance.
Issue #525 is never reused.

## 11. P1 source-scope hypothesis

Exact paths are NOT authorized by P0 and must be re-pinned after review.

Expected A-Wiki focus:
- existing DEX identity/binding formation;
- existing WorkerLease / #498 guard consumption seam;
- a narrow adapter that projects accepted lane/admission evidence into Sunday dispatch;
- deterministic target-binding fault tests.

Expected SRM focus:
- `src/sunday/mcp-runtime-tools.ts`;
- `src/sunday/supervisor.ts`;
- narrow evidence/types needed to separate target-lane identity from substrate identity;
- focused tests only.

Do not add:
- another task DB;
- another WorkerLease/claim store;
- another scheduler/router authority;
- a second retry engine;
- acceptance/completion authority in SRM;
- a global Active Project registry.

## 12. Dependency / fan-in order

1. P0 exact docs candidate freeze.
2. Independent R3 exact-SHA review; P0/P1/P2 must be zero.
3. Exact-head hosted CI and expected-head merge; post-main verify.
4. Re-recover #498. Integrated mutation path cannot claim canonical launch safety
   until #498 blocking immutable-field repair is accepted.
5. If P0 review accepts `LOCAL_ONLY_CANONICAL`, open a separate isolated SRM
   local-only source lane bound to exact path/SHA; otherwise execution-source mutation stays blocked.
6. Implement RED-first smallest target/substrate identity separation.
7. Deterministic fault/adversarial suite.
8. Freeze exact A-Wiki + SRM compatibility pair/set; independent R3 review.
9. Only after integrated acceptance create a NEW three-session mutation canary:
   one winner + two losers denied before process start.
10. Fold verified evidence to #526/#495 and continue NEXT_READY.

## 13. P0 verification

Before this docs claim may freeze:

- exact authority worktree/branch/base re-pinned;
- only this WO path changed;
- strict UTF-8;
- `git diff --check`;
- added-content secret/credential scan;
- references to #500/#507/DEX checked against actual accepted state;
- #498 ownership explicitly preserved;
- #499 UNKNOWN state not replayed;
- #522 post-main state reconciled separately;
- no SRM source mutation;
- no Worker/Serena rebind;
- no shadow authority/store.

After freeze:
- independent exact-SHA R3 review;
- hosted CI;
- expected-head merge;
- post-main verification.

## 14. Stop conditions

Stop only on a real gate:

- identity / ownership / replay state UNKNOWN for the lane being mutated;
- collision with a protected mutable owner;
- independent R3 P0/P1/P2 finding;
- exact-head CI failure attributable or unresolved;
- local-only SRM identity proposal rejected or remains materially ambiguous;
- #498 dependency blocks integrated launch acceptance;
- authorization/security gate;
- no safe non-overlapping next action.

A ChatGPT/session rollover, transport timeout, or lack of a remote URL alone is not
execution failure and does not authorize redispatch.
