# WO-P1-535 — CLI transport hardening

Issue: #535
Class: CROSS_REPO
Risk: R3
Claim: WO-P1-535-CLI-TRANSPORT-MAC-001

## Authority binding
- Authority repo: /Users/aase7en/GitHub/A-Wiki-Conductor
- Authority base: 1486e75484afa21a79810a7ebe0e92abb384c3b7
- Authority worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo535-cli-transport
- Authority branch: docs/wo-p1-535-cli-transport

## Execution binding
- Execution repo: /Users/aase7en/GitHub/SunDayRemoteMCP
- Execution base: 2f033cfb1f61b6dff9c2e55264cca6f2a9125e95
- Execution worktree: /Users/aase7en/GitHub/_worktrees/SunDayRemoteMCP-wo535-stdin-eof
- Execution branch: fix/wo-p1-535-stdin-eof
- Role: EXECUTION_SUBSTRATE_ONLY

## Reproduced defects
1. Sunday durable child launch preserves an open stdin pipe. Native Codex exec launched through Sunday waits at "Reading additional input from stdin..." with zero model events for >3 minutes. The same CLI command completes in about 6 seconds when stdin is closed from /dev/null.
2. Kilo 7.7.2 with cointh-glm/glm-5.3-flash remains zero-output and CoinTH quota unchanged even with stdin explicitly closed. Kilo reaches session bootstrap, session.turn.open and model-cache, then no provider request/response is logged.

## Goal
- add deterministic non-interactive child stdin EOF support in SunDayRemoteMCP;
- prove it with regression tests and exact Codex smoke;
- diagnose Kilo/CoinTH provider stall without exposing secrets;
- classify GLM route by actual provider/model evidence, not process liveness;
- keep GPT lanes usable when GLM route is blocked.

## Safety / authority
- A-Wiki-Conductor owns task/claim/WIP/review/acceptance.
- SunDayRemoteMCP may own only execution-lane/path-lock runtime state.
- No new scheduler/task/claim/retry/review/completion authority.
- Never reset/clean/stash unknown work or broad-kill processes.
- Never expose secrets, raw auth headers or share URLs.
- Do not patch vendor Kilo binary or global user config blindly.

## Lane plan
- M1: SRM stdin EOF implementation + tests.
- M2: read-only Kilo/CoinTH diagnosis.
- M3: existing WO529 P2 mutation-probe hardening.
- R1: GLM/Jev only after CoinTH smoke proves the route actually works.

## Acceptance
- regression test reproduces open-stdin hang and verifies deterministic EOF policy;
- Sunday-launched exact Codex CLI returns model event and exits;
- provider smoke truthfully marks CoinTH route READY or BLOCKED;
- Kilo diagnosis records exact first missing lifecycle boundary;
- independent R3 review and exact-SHA verification before merge/acceptance.


## Checkpoint — stdin EOF repair frozen

Execution author:
- Sunday exec: `exec-mufc2xdp-6ah7ybn7`
- SRM candidate: `44a4b6c` (`fix: support closed stdin for durable children`)
- execution branch: `fix/wo-p1-535-stdin-eof`
- SRM PR: https://github.com/aase7en/SunDayRemoteMCP/pull/1

Independent R3 review:
- Sunday exec: `exec-mufchmwk-vltw3gq7`
- verdict: PASS
- counts: P0=0 P1=0 P2=0 P3=1
- P3: additional explicit `closeStdin:false` and legacy-manifest recovery tests would improve coverage but are nonblocking.
- reviewer independently reproduced that the original output-ring fixture can lose FINAL-MARKER when `process.exit(0)` races stdout flush; callback-based fixture is therefore justified.

Author verification:
- RED: `closeStdin:true` on pre-fix supervisor timed out waiting for EOF.
- GREEN: explicit EOF test passes; omitted option preserves open stdin and cancellation.
- supervisor focused fault suite PASS.
- sunday batch suite 13/13 PASS.
- build/typecheck PASS.
- MCP dispatch smoke reached verified exit/harvest.
- git diff --check PASS.

The execution-substrate repair adds only an additive `closeStdin?: boolean` policy through Sunday runtime tool schema, manifest/evidence validation, supervisor request, and io-shim spawn. `true` maps stdin to the platform null device; absent/false preserves the legacy pipe.

## Checkpoint — GLM/Jev provider diagnosis

CoinTH/Kilo material route remains BLOCKED pending provider smoke:
- Kilo CLI 7.7.2 and VS Code-bundled Kilo 7.7.9 both time out on the same Flash smoke even with stdin EOF.
- `KILO_CONFIG_CONTENT={"share":"disabled"}` still lists `cointh-glm/glm-5.3` and `cointh-glm/glm-5.3-flash`, so the privacy overlay does not remove those model names.
- observed Kilo lifecycle reaches session bootstrap, turn.open, and model-cache before output stalls; no successful model receipt has been observed.
- CoinTH quota remained unchanged during the failed smoke attempts.
- mixed 7.7.2/7.7.9 state sharing is not proven causal.

Existing durable upstream recheck:
- Sunday exec: `exec-mufchq7d-8v9a099t`
- state at checkpoint: RUNNING
- behavior: wait across the current CoinTH quota window reset, then perform one Flash smoke with quota-before/quota-after evidence.
- do not duplicate this recheck while it remains active.

TypeSafe-Jev is independently proven:
- bounded live advisory was explicitly authorized in Issue #535.
- provider/model: `typesafe / jev-1.13.0`
- family: `failure_classification`
- result: `CODE_FAILURE`, confidence 0.52
- probabilities: CODE_FAILURE 0.61, TRANSPORT_FAILURE 0.37, TEST_FAILURE 0.01, AUTH_FAILURE 0.01, RATE_LIMITED 0.
- `authoritative_for_action=false`; actual runtime evidence remains authoritative.
