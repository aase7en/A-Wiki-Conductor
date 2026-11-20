# WO-P1-254 — Safe Kilo MCP connection-health foundation

Status: CLAIMED / IMPLEMENTATION
Issue: #355
Related defects: #343, #342
Risk: R3 CRITICAL — client lifecycle / connection-state / diagnostic security boundary
Topology: CONTROL_PLANE_ONLY
Owner/integrator: GPT-5.6 Sol
Implementation executor: GLM-5.3 MAX through Kilo CLI after fresh CoinTH preflight
Lane operator: SunDay-Worker 2

## Binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo254-kilo-mcp-health`
- Branch: `feat/wo-p1-254-kilo-mcp-health`
- Base/current bootstrap SHA: `8dd659df635b50988757414d3eae2f1cf923ba52`
- Runtime Kilo evidence: CLI `7.7.2`
- Supported CLI surface observed: `kilo mcp list` = "list MCP servers and their status"; no structured-output flag is exposed by its help.
- Durable authority: GitHub Issue #355

## Problem

Issue #343 proved that registration/config presence does not prove a live usable MCP route.
A long-lived Kilo backend may retain a stale MCP registry after the underlying registration
changes. A new chat can therefore still have zero injected `sunday_*` tools even when a later
standalone process would be healthy.

Issue #342 also requires that connection diagnostics never persist raw configuration, command
lines, environment values, headers, credentials, or Kilo share/session URLs.

The connection-health vocabulary is ordered evidence, not task/project authority:

`REGISTERED -> PROCESS_SPAWNED -> HANDSHAKE_CONNECTED -> TOOLS_INJECTED`

A higher stage must never be inferred from a lower one.

## Goal

Create a pure/injection-based foundation that can classify a safe Kilo MCP observation without
reading raw Kilo config or spawning/restarting processes in this slice.

The foundation must:
1. represent each observed connection stage independently;
2. reject logically impossible observations instead of normalizing them;
3. detect stale backend/config load relative to a later MCP registration/config update;
4. report a typed blocker/reload-required disposition;
5. expose only a bounded safe projection suitable for logs/UI/roadmap evidence;
6. remain provider/model/harness-neutral outside the Kilo-specific lifecycle vocabulary;
7. own no task, claim, scheduler, retry, review, completion, provider, process, or MCP authority.

## Claimed tracked scope

- NEW `src/a_conductor/kilo_mcp_health.py`
- NEW `tests/test_kilo_mcp_health.py`
- NEW `docs/work-orders/WO-P1-254-kilo-mcp-health.md`

No other tracked file is mutable in this slice.

## Contract shape

Implement a small typed model with equivalent semantics to:

- connection stage enum including at least:
  - `NOT_REGISTERED`
  - `REGISTERED`
  - `PROCESS_SPAWNED`
  - `HANDSHAKE_CONNECTED`
  - `TOOLS_INJECTED`
- blocker enum including at least:
  - `NOT_REGISTERED`
  - `PROCESS_NOT_SPAWNED`
  - `HANDSHAKE_NOT_CONNECTED`
  - `TOOLS_NOT_INJECTED`
  - `STALE_BACKEND_CONFIG`
  - `MALFORMED_OBSERVATION`
- one immutable observation type with bounded safe fields only, such as:
  - safe server name/id;
  - booleans for the four evidence stages;
  - bounded injected tool count and/or exact required-tool probe boolean;
  - registration/config update timestamp;
  - backend MCP-config load timestamp;
- one immutable result/projection type containing only:
  - safe server name/id;
  - highest proven stage;
  - blocker;
  - stale/reload-required boolean;
  - bounded tool count / required-tool-present boolean;
  - no raw command/config/env/header/URL/token fields.

Equivalent naming is allowed if semantics remain exact and tests are clear.

## Invariants

1. `TOOLS_INJECTED` requires handshake evidence.
2. `HANDSHAKE_CONNECTED` requires spawned-process evidence.
3. `PROCESS_SPAWNED` requires registration evidence.
4. A positive tool count or required-tool-present flag without `TOOLS_INJECTED` is malformed.
5. Negative tool count, bool-as-int count, unbounded count, invalid/blank/oversized server name, naive timestamps, or non-datetime timestamps fail closed.
6. If backend MCP-config load time is earlier than the relevant registration/config update time, classify `STALE_BACKEND_CONFIG`, set reload-required=true, and do not report `TOOLS_INJECTED` as currently usable even if stale tool evidence was previously observed.
7. A fresh backend with registration/process/handshake but no required tools is `HANDSHAKE_CONNECTED` + `TOOLS_NOT_INJECTED`.
8. Registration alone never implies process spawn.
9. Process spawn alone never implies handshake.
10. Handshake alone never implies tools injected.
11. The safe projection must have a fixed allowlist of fields and must not accept arbitrary raw metadata.
12. No subprocess, shell, filesystem config read, Kilo invocation, network call, process restart, credential access, or durable output persistence in this module.
13. No provider/model routing or A-FastTask mutation authority.
14. No broad kill/restart behavior; this slice only classifies evidence.
15. Future collection adapters must sanitize before first persistence per DEFECT_LESSONS #36.

## Failure model

Impossible or unsafe input raises/fails with a deterministic local code such as:
- `KILO_MCP_HEALTH_INVALID`
- `KILO_MCP_STAGE_CONTRADICTION`
- `KILO_MCP_TIMESTAMP_INVALID`
- `KILO_MCP_TOOL_COUNT_INVALID`

A stale-but-well-formed observation is not malformed; it returns a typed
`STALE_BACKEND_CONFIG` blocker.

## Required tests

At minimum:
- each valid stage independently;
- all monotonic stage contradictions;
- stale backend/config load;
- fresh backend/config load;
- stale observation suppresses usable-tools disposition;
- zero tools after handshake;
- required tool absent/present;
- tool-count bounds and bool-as-int rejection;
- blank/oversized/unsafe server name rejection;
- naive/non-datetime timestamp rejection;
- exact safe projection field allowlist;
- no arbitrary metadata field on the observation/result;
- result contains no command/config/env/header/token/url fields;
- deterministic equality/serialization behavior where exposed.

## Verification

After implementation:
- focused `tests/test_kilo_mcp_health.py`;
- directly related provider/harness tests only if imports/contracts touch them;
- `python -m compileall` for source/test;
- `git diff --check`;
- exact 3-path scope from base;
- added-line secret/URL scan;
- independent exact-SHA review;
- hosted CI before merge if branch is pushed.

## Forbidden

- no live `kilo mcp list` status dump in durable evidence;
- no raw config or environment persistence;
- no process restart/reload/kill in this slice;
- no provider credential or share/session URL handling beyond type-level prohibition;
- no mutation of WO253 files/hotspot;
- no `CURRENT-WORK.md`, `handoff.md`, or `COLLAB.md` mutation from this lane;
- no reset/clean/stash/rebase/force-push.

## Exit

Freeze one exact candidate SHA. The independent reviewer must verify that the model cannot
accidentally infer a higher state from lower evidence and that the safe projection cannot become
an alternate raw diagnostic/config dump.

A later separate phase may add a collector that obtains these booleans from a supported Kilo
surface and performs a bounded exact backend reload/reconnect workflow. This WO does not authorize
that phase.
