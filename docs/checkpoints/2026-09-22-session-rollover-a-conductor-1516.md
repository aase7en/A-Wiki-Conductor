# Session rollover checkpoint — A-Sunday Conductor

Status: CHECKPOINT / CHAT ROLLOVER READY
Date: 2026-09-22 15:16 ICT
Authority repo: `A:\GitHub\A-Wiki-Conductor`
Execution repo: `A:\GitHub\SunDayRemoteMCP`
Checkpoint base: A-Wiki `main@bd04d897d928300a06de680995f8fbaf1834aa9c`

## Authority rule for next session

Do not use this checkpoint as project authority when actual repo/GitHub/runtime/delegated state can be recovered. This file is an index and recovery map only.

Authority order:

`actual runtime/Git/GitHub/durable delegated state -> claims/work orders/evidence -> CURRENT-WORK/active WO/handoff/COLLAB -> checkpoint/chat summary`

Start substantial work with:

`00-AGENT-ENTRY.md -> PROJECT-GRAPH.yaml -> AGENTS.md -> actual repo/worktree/branch/HEAD/dirty/claim -> CURRENT-WORK.md -> active WO -> handoff.md when needed -> task-relevant files`

This checkpoint supersedes PR #462 and PR #465 as the preferred rollover index. Their historical evidence remains valid, but their task/frontier snapshots are stale.

## Actual repository state at checkpoint

### A-Wiki authority

- GitHub `main = bd04d897d928300a06de680995f8fbaf1834aa9c`.
- Merge `bd04d897...` is PR #474, the WO473 closeout fold.
- Protected root checkout `A:\GitHub\A-Wiki-Conductor` remains intentionally untouched:
  - local `main@1a5ea1b8574f783c002589ffe3fb51b30303e24c`;
  - behind `origin/main` by 120 commits at checkpoint;
  - untracked `$null`, `0`, and `docs/prompts/GLM-WO230-ZRA2-REVIEW-TASK-CONTRACT-AUTHORITY.md`.
- Never reset/clean/stash/switch that root merely to make it current. Use isolated worktrees.
- WO473 closeout worktree remains at `0145640fdb092ed39c69de42ec00ea2cb0058adb`; PR #474 is already merged, so that worktree is historical/cleanup-only unless explicitly reclaimed.

### SunDayRemoteMCP execution substrate

- Canonical local `A:\GitHub\SunDayRemoteMCP\main = e3ec2e06baf464e68c4166faae65f51c60fd5477`.
- SRM still has no configured Git remote.
- Canonical root has protected untracked `.serena/`; do not clean/reset/stash it.
- Many historical SRM worktrees exist. Do not broad-clean them. Reconcile exact ownership before cleanup.
- Read-only DEPDIET audit worktree:
  `A:\GitHub\_worktrees\SunDayRemoteMCP-ro472-depdiet-audit-e3ec2e0`
  is detached, clean, exact `e3ec2e06...`.

## Major session outcomes

### Legacy rollover state reconciled

The PR #462 / 06:45 rollover state was already superseded by actual Git/GitHub state.

During recovery the following old lanes were found already completed/closed rather than READY to redispatch:

- #461 / PR #466 GraphStore post-main repair;
- #458 / PR #464 provider fallback;
- #459 / PR #468 secret writer;
- #453 / PR #456 Mac-owned file-safety lane;
- #470 / PR #471 ZRA-3A Child-B preparation application.

Do not resurrect any of these from old checkpoint text. Re-read actual GitHub if they ever become relevant again.

### #457 — BWA-1A Sunday-Family Extension

- Issue #457 remains OPEN and `HUMAN_DECISION_REQUIRED`.
- Independent GLM-5.3 MAX core review was harvested earlier in this session:
  - exact candidate `ef0c05f1b647533dc56ec888746d0145bfea5cdc`;
  - verdict `PASS_CORE_SLICE`;
  - P0/P1/P2/P3 = 0/0/0/3.
- That review completion does NOT lift the human gate.
- Do not create extension repo/source, merge, or infer the repo/host-language decision from this checkpoint.

### #473 — DEPDIET first removal slice — COMPLETE

Issue #473 is CLOSED.

Accepted execution change:

- SRM base: `2e6aeabd09a321232098187dba4c522e37e4b1de`;
- accepted candidate and canonical SRM main:
  `e3ec2e06baf464e68c4166faae65f51c60fd5477`;
- exact mutation: `package.json` + `package-lock.json` only;
- removed direct roots:
  - `@tiptap/pm`
  - `remark`
  - `remark-gfm`
  - `remark-parse`
  - `unified`
- semantic lock result: 67 unreachable entries removed, 0 added; `@tiptap/pm` remains transitively reachable.

Accepted independent review:

- evidence:
  `runs/WO-P1-473/r2-review/attempt-0005-static-e3ec2e0-v1/`
- run:
  `run:WO-P1-473:r2-static-review:a5:f05646ef0027`
- GLM-5.3 MAX;
- PASS;
- P0/P1/P2/P3 = 0/0/0/3;
- exit 0;
- 2,620 security samples;
- no MCP descendant;
- no scope violation;
- exact review tree clean.

Historical review attempts are NOT acceptance evidence:

- attempt-0001: security-invalid due over-broad MCP process heuristic;
- attempt-0002: provenance collision invalid;
- attempt-0003: security-invalid `node.exe:mcp-server`;
- root cause of attempt-0003: the in-repo regression test intentionally spawns
  `test/fixtures/dying-mcp-server.js`; monitor v5 narrowed the fixture exemption without whitelisting arbitrary `node.exe`;
- attempt-0004: invalidated before dispatch by task/config identity drift.

Integration/closeout:

- canonical SRM was fast-forwarded locally to `e3ec2e06...`;
- PR #474 merged exact head `0145640fdb092ed39c69de42ec00ea2cb0058adb`;
- A-Wiki merged main `bd04d897d928300a06de680995f8fbaf1834aa9c`;
- Issue #473 CLOSED;
- post-main CI on `bd04d897...`: Windows `test` SUCCESS, Ubuntu smoke SUCCESS, macOS smoke SUCCESS;
- WO473 claim released.

### #472 — DEPDIET parent — OPEN / next candidate proven

Issue #472 remains OPEN and is still the authority for the broader dependency/feature-pack boundary.

Important failed advisory attempts:

1. Flash audit attempt-0001:
   - run `run:WO-P1-472:audit:1:a1:30a2a0a83322`;
   - quota/admission were READY;
   - terminal `EXECUTION_TIMEOUT` after 15 minutes;
   - no accepted result.

2. Flash audit attempt-0002:
   - run `run:WO-P1-472:audit:1:a2:1fe39538bb48`;
   - quota/admission were READY;
   - terminal `EXECUTION_TIMEOUT` after 5 minutes;
   - no accepted result.

Do not redispatch those attempts.

Accepted targeted read-only proof:

- lane: `lane:WO-P1-472:candidate-proof:1`;
- run: `run:WO-P1-472:candidate-proof:1:a1:2c36e9e9afee`;
- GLM-5.3 MAX;
- exact SRM SHA `e3ec2e06baf464e68c4166faae65f51c60fd5477`;
- terminal exit 0;
- 5,099 process samples;
- no MCP descendant;
- no scope violation;
- audit worktree remained clean.

Sol routing adjudication folded to Issue #472 comment
`5773277123`:

- next bounded removal candidate: direct roots `glob` + `file-type`;
- exhaustive static proof found no first-party static/dynamic/build/test/full-toolset/postinstall/release/MCPB/runtime use;
- production closure delta:
  - `glob`: 26 entries;
  - `file-type`: 7 entries;
  - union: 33 production orphans;
- MATERIAL RECIPE CORRECTION:
  package-lock mutation must remove **31 entries, not 33** because top-level
  `signal-exit@4.1.0` and `lru-cache@10.4.3` remain reachable from the dev tree;
- `SAFE_TO_OPEN_MUTATION_CLAIM = YES` only for one future bounded R2 package slice:
  - `package.json`: remove direct dependency keys `glob` and `file-type`;
  - `package-lock.json`: remove the two matching root keys and exactly the 31 true full-tree orphan entries;
  - no other source/package/runtime mutation.

This is mutation-claim readiness, not a live claim. At checkpoint there is no accepted mutable #472 writer.

Required future verification floor remains:

1. exact 2-root manifest edit;
2. exact 31-entry lock orphan removal;
3. no survivor version/integrity/resolved churn;
4. build with existing dependency environment, no install/update/prune/audit/publish;
5. search `--glob/--iglob` path smoke;
6. file read/preview `fileType` payload smoke;
7. full-toolset startup;
8. npm-pack/release dry-run + MCPB smoke under the existing authorization rules;
9. full deterministic runner or justified differential;
10. exact-SHA R2 MAX independent review before canonical integration.

## Concurrent work to recover before new mutation

### #475 / PR #476 — MSP roadmap

This lane appeared concurrently during the session and was not authored/accepted by this checkpoint lane.

Current observed state:

- Issue #475 OPEN:
  `MSP — Multi-Session Provenance & Collision Hardening`;
- phase: DESIGN / ROADMAP ONLY; source mutation blocked;
- PR #476 OPEN, non-draft, mergeable;
- PR head: `acfa39d13ecac7201595ccba48ad958acf27a9b2`;
- PR base at observation: old A-Wiki `2867797ca991e249c97999b6f0cebff4d12143a5`;
- PR CI: Windows test SUCCESS, Ubuntu smoke SUCCESS, macOS smoke SUCCESS.

Because current A-Wiki main is now `bd04d897...`, the next session MUST recover/reconcile #475/PR #476 before opening overlapping governance/continuity mutation. Do not silently repin, merge, or rewrite it.

## Other durable gates

- Issue #215 remains OPEN: automatic NEXT READY continuation parent.
- Issue #457 remains OPEN / HUMAN_DECISION_REQUIRED.
- Issue #342 remains the Kilo MCP isolation/security follow-up. Preserve:
  `KILO_PURE=1` + disable every configured MCP in `KILO_CONFIG_CONTENT` + live descendant census + secret-safe output. `--pure` alone is not sufficient.
- Never persist raw MCP command lines, tokens, credentials, secret values, or share URLs.
- Before every material GLM dispatch, refresh CoinTH quota plus exact model admission.
- Use GLM-5.3 MAX for material R2/R3 implementation/review and Flash only for bounded read-only assist.
- Large all-in-one Flash audits proved inefficient in this session; prefer bounded micro-runs and harvest each terminal attempt before replay.

## WIP / delegated state at rollover

Session-local accepted state:

- mutable DEPDIET writer: NONE;
- independent review lane: FREE;
- #472 Flash attempts 0001/0002: TERMINAL_ERROR / harvested;
- #472 targeted MAX proof: TERMINAL / harvested;
- #473 delegated attempts: terminal and reconciled;
- no accepted RUNNING delegated execution from this session should be redispatched.

However, fresh session recovery is mandatory because other ChatGPT sessions may have advanced #475/PR #476 or created new delegated runs after this checkpoint.

Default global WIP remains:
- max 3 mutable lanes;
- max 1 independent read-only review lane;
- counted globally across sessions/devices/repos.

## Exact next safe action

1. Recover actual A-Wiki GitHub `main`, Issue #472, Issue #475 / PR #476, Issue #457 and Issue #215.
2. Recover delegated run/process/result state before dispatch. `RUNNING` never redispatches; `TERMINAL_UNHARVESTED` harvests first.
3. Confirm canonical SRM still `main@e3ec2e06...` and protected `.serena/` remains unexplained/untouched.
4. Reconcile #475/PR #476 against current `main@bd04d897...`.
5. If no newer authority/collision supersedes the DEPDIET frontier, create a fresh bounded #472 R2 mutation claim/worktree for `glob + file-type` using the proven **31-entry** lock recipe.
6. Refresh CoinTH quota + exact GLM-5.3 admission immediately before any material GLM dispatch.
7. Continue automatically through implementation -> deterministic verification -> frozen exact SHA -> independent MAX review -> Sol adjudication -> canonical SRM ff-only integration -> A-Wiki fold/closeout as policy permits.
8. Do not start #457 source work unless the human decision gate is explicitly resolved.

## New-chat handoff note

The user requested a copyable prompt in the assistant response. The prompt should point to this checkpoint PR/file but must still instruct the next session to recover actual runtime/Git/GitHub state first.
