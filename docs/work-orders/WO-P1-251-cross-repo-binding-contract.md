# WO-P1-251 — CROSS_REPO binding contract

Status: COMPLETE
Issue: #349
Risk: R2 NORMAL — binding coordination / SSoT policy
Owner/integrator: GPT-5.6 Sol
Topology: CROSS_REPO

AUTHORITY_REPO: `A:\GitHub\A-Wiki-Conductor`
AUTHORITY_BASE: `7c0ff0d68c816a3f307fa39851129bcbab7c9f16`

EXECUTION_REPO: `A:\GitHub\SunDayRemoteMCP`
EXECUTION_BASE: `2b7996ced0ceaff5b97c7bef3f601765213de5ec`

## Goal

Define the first repo-native CROSS_REPO binding contract for A-Sunday Conductor: repo-role classification, per-lane execution-context binding, exact-SHA compatibility set, global WIP accounting, set-level completion, and a durable Windows no-console rule.

This work must not create a second scheduler, task store, claim authority, reviewer authority, completion authority, mutable global Active Project, or copy Project Sources into repo roots.

## Topology vocabulary

The accepted definition home produced by this Work Order is `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`. This Work Order uses the exact labels `CONTROL_PLANE_ONLY`, `EXECUTION_SUBSTRATE_ONLY`, and `CROSS_REPO` without maintaining a second definition copy here.

Per-lane binding:

`repo -> worktree -> branch -> HEAD -> task/claim -> scope`

Compatibility set at freeze:

`{AUTHORITY_REPO@SHA_AUTH, EXECUTION_REPO@SHA_EXEC}`

Any member head drift invalidates the set until re-pin and focused review of affected delta.

## Global WIP

One global budget across the compatibility set:

- mutable lanes: 3
- independent read-only review lanes: 1
- `1 MUTABLE HOTSPOT = 1 MUTATION OWNER`

CROSS_REPO never multiplies WIP per repository.

## Durable Windows no-console rule

Invoke the exact installed executable directly wherever possible. When PowerShell is unavoidable, launch it hidden with no new console window. Background child processes use `CREATE_NO_WINDOW` / `windowsHide` on Windows. Never change global shell settings or profiles. Process termination targets an exact PID with verified command identity only; broad process kill remains forbidden.

## Claims / mutation lanes

### Lane A — authority routing contract
Repo: A-Wiki-Conductor
Scope:
- `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
- `PROJECT-GRAPH.yaml`

Task:
- define the three topology values at one authoritative routing definition home;
- define full per-lane tuple;
- define global-cross-repo WIP accounting;
- define exact-SHA compatibility pair/set and set-level completion pointer;
- project the Windows no-console rule;
- preserve existing A-FastTask router/binder-only authority floor.

### Lane B — authority entry / A-FastTask projection
Repo: A-Wiki-Conductor
Scope:
- `00-AGENT-ENTRY.md`
- `.agents/skills/a-fasttask/SKILL.md`
- `.agents/skills/a-fasttask/references/conductor.md`
- `.agents/skills/a-fasttask/references/closeout.md`

Task:
- project, but do not redefine, topology semantics;
- align the pre-existing derived-liveness enumeration with `EXECUTION_LIVENESS_PROTOCOL.md`;
- project the full lane-binding tuple and exact-SHA set;
- make WIP accounting global across set members;
- make CROSS_REPO evidence fold target the authority repo;
- project the durable no-console rule where execution routing is described.

### Lane C — execution-substrate mirror
Repo: SunDayRemoteMCP
Scope:
- `AGENTS.md`

Task:
- declare SunDayRemoteMCP as `EXECUTION_SUBSTRATE_ONLY` for A-Wiki-governed CROSS_REPO work;
- require authority WO/claim reference plus exact compatibility pair before mutation;
- preserve SRM-owned WO-SRM self-governance for SRM-owned tasks;
- add the durable no-console rule;
- bind cross-repo references by exact SHA, never by copied control-plane source.

## Forbidden

- no `src/`, test, runtime, provider, DB, credentials, or secret mutation in this WO;
- no mutation of dirty/stale canonical A-Wiki root;
- no broad reset/clean/stash/checkout/rebase/force;
- no broad process kill;
- no Project Sources copied into either repo root;
- no second task/claim/scheduler/review/completion authority.

## Dispatch invariants

Before every material GLM dispatch:
1. fresh CoinTH quota/readiness preflight through the approved secret-safe resolver;
2. exact lane binding and claimed scope;
3. no overlapping writer;
4. durable result destination under ignored `runs/WO-P1-251/<lane>/`;
5. no secrets in prompt/logs.

Worker/GLM DONE is a claim only. Deterministic exact-SHA evidence wins.

## Verification / acceptance

Per repo:
- exact claimed path scope;
- `git diff --check`;
- strict UTF-8;
- added-line secret scan;
- referenced relative paths resolve;
- no runtime/source/schema change;
- classification vocabulary has one definition home and projections do not fork it.

Set-level:
- freeze one exact candidate head per repo;
- independent read-only review of the compatibility pair must return `P0=0 P1=0 P2=0`;
- A-Wiki exact-head hosted CI required;
- SunDayRemoteMCP exact-head deterministic fallback allowed only if hosted CI is absent and must be explicitly recorded;
- merge expected heads only, authority repo first then execution repo;
- post-main verification both repos;
- Issue #349 records final merged SHA pair, CI/fallback evidence, independent-review reference, and global WIP ledger before closure.

## Closeout / final evidence

Reviewed compatibility pair:
- A-Wiki candidate: `ce6085cab4f1c804731f770d1baab1dc721142ff`
- SunDayRemoteMCP candidate: `1fca9d24c37e49762ea6fbce8b2927726d94e0b7`
- focused independent rereview: PASS, `P0=0 P1=0 P2=0`
- rereview task SHA256: `C548B15DAEB31104D40773D1DA9653976107FC34F80CA93E945872AA9DA4E9A2`

Authority delivery:
- PR #350 merged authority-first;
- A-Wiki merge commit: `fb29fac5fe059f9a9f1ca1ac461b3e0138f7659f`;
- reviewed authority candidate is an ancestor of the merge commit;
- all seven reviewed authority paths have identical merged-tree content;
- exact-head CI run `35324897261`: Windows/full, Ubuntu smoke, and macOS smoke PASS;
- post-main CI run `35329574109` on `fb29fac5...`: Windows/full, Ubuntu smoke, and macOS smoke PASS.

Execution delivery:
- SunDayRemoteMCP canonical main: `1fca9d24c37e49762ea6fbce8b2927726d94e0b7`;
- no hosted remote/CI is configured for this repository, so the Work Order's deterministic fallback was used;
- exact-head fallback PASS: build, local-policy tests, tool-policy tests, MCP facade tests, diff/scope;
- post-main verification on canonical main PASS: build, local-policy tests, tool-policy tests, MCP facade tests;
- canonical SRM worktree clean after verification.

Final merged compatibility pair:
`{A-Wiki-Conductor@fb29fac5fe059f9a9f1ca1ac461b3e0138f7659f, SunDayRemoteMCP@1fca9d24c37e49762ea6fbce8b2927726d94e0b7}`

Accepted routing addition:
- exact upstream GLM admission `RATE_LIMITED` outranks reseller/proxy quota counters;
- within a proven blocked window, repeat quota/credential root-cause loops and live GLM probes are suppressed unless material evidence changes;
- after terminal execution harvest/ownership reconciliation, GPT-5.6 Sol may take over eligible READY implementation/analysis work;
- independent-review gates remain independent, and no silent paid/provider substitution is allowed;
- at/after reset, quota plus exact admission are refreshed before GLM lanes refill.

Final WIP ledger:
- mutable implementation lanes: 0;
- independent read-only review lanes: 0;
- no live WO-P1-251 delegated execution/reviewer process observed at closeout;
- cleanup state: `PENDING` until this closeout fold is merged and Issue #349 is checkpointed/closed; branch deletion remains a separate later decision.

Next READY sequence after closeout:
1. WO-SRM-005 — re-pin the CoinTH live-admission preflight onto current SunDayRemoteMCP main, exact-SHA verify/review/accept;
2. WO-SRM-004 / SEM-0 — re-pin onto then-current SRM main, exact-SHA review/fan-in;
3. Issue #341 SEM-1a from freshly accepted semantic foundation.
