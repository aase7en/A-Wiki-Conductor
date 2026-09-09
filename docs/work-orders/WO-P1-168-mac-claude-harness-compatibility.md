# WO-P1-168 — Mac Claude harness compatibility

Date: 2026-09-10 (Asia/Bangkok)
Status: CLAIMED / REPRODUCING
Owner: GPT-6 Astra / Poppy Javis, bounded repair lane
Integrator: GPT integrator retains independent acceptance, merge, release, downstream ZRA
Risk: R3 (customization isolation and provider credential confinement)
Classification: EXTEND existing fixed Claude invocation; REUSE supervised execution and provider authority

## Authority and identity

The user's 2026-09-10 bounded repair task explicitly authorizes this source repair,
RED/GREEN verification, clean isolated candidate and push; forbids self-merge and
credential use unless necessary. Issue #233 comments 5606720902 / 5606878598
provide discovery evidence, not substitute authority.

- Repository: aase7en/A-Wiki-Conductor
- Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo168
- Branch: codex/wo-p1-168-mac-claude-harness
- Base: 77e7b0f8e9460f78fa2ef4a1ddaad62131c2c7f2
- Claim: WO-P1-168 / GPT-6 Astra / this exact branch and scope only
- Result: runs/WO-P1-168/result.md; assurance under runs/WO-P1-168/assurance/<sha>/
- Remote durable checkpoint: this same WO on the pushed branch

## Bounded governance bootstrap

Only this new WO/claim is created before rerunning the source gate. No global
projection ownership is claimed. The user explicitly excludes ad-hoc edits to
CURRENT-WORK.md, handoff.md and COLLAB.md; the integrator must fold the final result
through its single-writer closeout. This WO is the existing durable task/claim
contract, not a new claim store. A-Wiki's local CLI hardcodes its own REPO_ROOT;
invoking it here would claim the wrong repository. No A-Wiki mutation is authorized.

Preflight: fetched origin; root main is clean and equals base; only root worktree
existed before this lane. All remote branch merge-base deltas were checked against
this exact source/test scope: no intersection. Open PRs #202/#204/#207/#222/#223
are disjoint. Existing COLLAB claims and Issue #233 were read; no live Claude
harness repair owner is recorded. Re-pin before source mutation and push.
A-Wiki remote main=566637ac8d2636d6c63eda2bd6ebe81b55bd3d72; local is ahead one
commit and preserved. Existing cross-agent-work-orders protocol/claim implementation
were inspected; no coordination primitive is built or redesigned.

## Allowed scope

- src/a_conductor/claude_code_harness.py
- src/a_conductor/claude_code_supervised_runner.py (only if compatibility requires it)
- tests/test_claude_code_harness.py
- tests/test_claude_code_supervised_runner.py (only if needed)
- tests/test_claude_code_host_compatibility.py (optional host proof, CI-safe skip)
- this WO (bootstrap and evidence checkpoint only)
- ignored runs/WO-P1-168/ evidence

Everything else is read-only, including global projections, other WOs, private
Drive, runtime DBs, dependencies, process authority, provider stores and A-Wiki.
No new scheduler/lease/secret store; no installations; no authenticated GLM turn.

## Failure model before mutation

The unsupported flag is not assumed redundant: upstream changelog introduces
--safe-mode at Claude Code 2.1.169; installed Mac is 2.1.152. Removing it alone
can expose hooks/MCP/skills/plugins/ambient context even with plan + read-only
built-in tools. Any replacement must prove customization isolation, exact packet
binding, unchanged environment-reference allowlist and synthetic auth binding.
No version/platform guess may weaken Windows/Linux confinement. Unknown CLI
capability must reject at parser/runtime rather than retry a weaker command.
Use bounded loopback fake-provider host evidence, not private credentials. Timeout
is never GREEN; host proof must observe the expected API boundary and child exit.
No raw subprocess path may be added to production.

## Acceptance / verification

1. RED: real installed CLI rejects current production-generated --print argv with
   unknown --safe-mode, exit 1; optional integration test must fail on old source.
2. GREEN: repaired production argv completes against synthetic loopback provider;
   task/model/header binding and isolation sentinels are checked.
3. Deterministic contracts keep plan, Read/Glob/Grep, no-session-persistence,
   settings isolation, task hash/path binding, explicit auth/base-url refs,
   supervision and redaction intact; no dangerous permission bypass.
4. Focused Claude + related supervised suites pass; host dependency optional.
5. Cross-platform expectations explicitly recorded, no OS-specific weakening.
6. Scoped clean committed candidate pushed; exact SHA/files/evidence recorded;
   READY_FOR_EXACT_SHA_REVIEW is not acceptance or ZERO_RELAY_OPERATIONAL.

Two bounded repair cycles before root-cause reset; independent exact-SHA review
and hosted CI remain integrator gates. Do not self-merge.

## Checkpoint

Bootstrap only. Next: re-pin clean worktree/claim -> real RED -> minimum compatible
confinement design -> tests -> freeze/push -> durable result for integrator.

### RED / design decision

Source gate passed on clean bootstrap ce303c88d0fc1c0ec552bbfd038beb1185297836.
Only the authorized new optional host test is dirty. Latest Issue #233 still
ends at comment 5606878598. RED: 3 real installed-CLI cases fail on unsupported
--safe-mode in 2.37s; baseline exit=1, no provider request. Evidence is retained
in runs/WO-P1-168/host-red.txt and baseline-probe.json.

Select one uniform explicit confinement profile (no platform/version heuristic):
--bare + --disable-slash-commands + --strict-mcp-config with empty MCP config,
--setting-sources empty. Keep all remaining task/tools/permission/persistence
and secret/supervised contracts. Bare suppresses ambient customization loading;
explicit skill/MCP exclusions close bare's explicit-opt-in surfaces; excluding
project/local settings also prevents env overrides and custom hooks. Unsupported
flags fail at the CLI; there is no automatic weaker retry. No API change or
credential-binding expansion is needed: a synthetic ANTHROPIC_AUTH_TOKEN probe
on 2.1.152 reached loopback /v1/messages with the exact Bearer header and exited
normally after the server's deliberate 400. API-key/OAuth fallback is not added.

Upstream evidence checked 2026-09-10:
- https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
  (2.1.169 introduces safe-mode; not obsolete/redundant).
- https://code.claude.com/docs/en/cli-reference
  (bare, disable-slash-commands, strict-mcp-config, tools).
- installed 2.1.152 --help advertises all replacement flags and warns bare has
  different auth semantics; exact-token loopback proof therefore remains required.

This strengthens explicit isolation on every OS; real newer Windows/Linux CLI
behavior is not inferred from the Mac test and must remain a declared limitation.
