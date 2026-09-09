# WO-P1-168 — Mac Claude harness compatibility

## R1 current authority — post-merge permission preservation

Status: CLAIMED / R3 CORRECTIVE REPAIR
Owner: GPT-6 Astra / Poppy Javis; integrator retains acceptance/merge/release
Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo168-r1
Branch: codex/wo-p1-168-r1-permissions
Base: 577d9483720c857a89a5d2c9ea9359f9c0aa50b5 (PR #237 external merge)
Result: runs/WO-P1-168/result.md; assurance under the same task directory

PR #237 was accepted/merged by the separate Sol integrator while the author lane
was interrupted. The author did not merge. Its green CI/review did not cover
project/local permission-deny preservation. An incomplete independent review
raised this question before its session hit a usage limit; no final review was
produced by that session. Fresh synthetic real-CLI evidence now proves the gap:
654e36d reads a project-denied file and sends its synthetic content to loopback;
the same argv with original project,local sources preserves the deny rule.
Evidence: prior worktree runs/WO-P1-168/permission-probe.txt (1 failed/1 passed).
This supersedes the earlier READY claim on the security invariant.

This is the same explicitly authorized compatibility repair, reopened with a
bounded WO-only governance checkpoint before source mutation. Fresh origin/main
and worktrees checked. WO169/PR #238 owns only three different docs; all other
open lanes are disjoint. No global projection/other WO ownership is claimed.
Source scope is exactly claude_code_harness.py plus the two original test files;
this WO owns its own checkpoint. Everything else remains read-only. No new
coordination/provider/secret/process authority. No authenticated provider call.

Corrective contract: restore the original project,local settings trust boundary
while retaining bare + disabled skills + strict empty MCP + plan + tool ceiling.
Project/local permission rules must stay effective. Those selected settings were
already trusted by the pre-repair invocation and may contain provider env values;
this task does not claim immunity to selected project/local env overrides. The
unselected user settings remain excluded. A separate synthetic probe confirmed
that hostile selected project env can redirect to loopback port 1; timeout was
recorded as failure and its owned exact-identity process was terminated. Do not
silently drop permission rules to suppress that pre-existing settings behavior.

R1 RED must exercise denied Read through the real host CLI, plus deterministic
settings-source preservation. R1 GREEN must preserve the original loopback happy
path and Bash/Write refusal, deny project/local Read, exclude user settings, skip
hooks/skills/MCP/context, and pass focused/related suites. No CI host dependency.
Next: commit/push this claim -> re-pin clean -> add/run RED -> restore settings
sources -> GREEN -> clean candidate push -> exact-SHA integrator review. The
merged source does not grant this author merge/acceptance authority.

## Historical R0 implementation checkpoint — superseded where R1 says otherwise

Date: 2026-09-10 (Asia/Bangkok)
Status: FROZEN / READY_FOR_EXACT_SHA_REVIEW (not accepted)
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

### GREEN / bounded repair checkpoint

Production change is only the fixed argv in claude_code_harness.py. The initial
replacement's empty standalone settings argument was rejected by the canonical
native runner; use --setting-sources= as one nonempty argv element. No native
validation relaxation was made. Native assembly tests now reach the supervised
plan boundary. Initial host expectation of exactly three exposed tools was too
strong: 2.1.152 bare exposes Read only. The test now verifies Read exists and the
actual tool set is a subset of the three-name allowlist; Write and Bash tool-use
injections are independently refused with error results and no marker writes.

Verification:
- RED commit: 16dc834 (real host 3 failures; contract 1 failure / 15 passes).
- Mac host: 2.1.152, arm64; optional integration 3/3 PASS in 3.29s.
- Focused harness/supervised mapping/backend/assembly: 44 PASS, 6 expected skips
  (3 Windows integration + 3 opt-in host cases).
- Related native/supervised/provider authority and runtime: 142 PASS, 3 Windows
  integration skips in 4.34s using the actual python3.12 executable.
- The first related run via python3 hit six fixture executable-name mismatches:
  sys.executable basename python3 versus sys._base_executable basename python3.12.
  Running the actual interpreter resolved all six without a source/test change.
- Compileall, git diff --check, strict UTF-8 and added-line credential-pattern
  scan PASS. No private secret was read or used.

Commands (from this worktree):
```sh
A_CONDUCTOR_TEST_CLAUDE=/Users/aase7en/.nvm/versions/node/v24.15.0/bin/claude python3 -m pytest -q tests/test_claude_code_host_compatibility.py
python3 -m pytest -q tests/test_claude_code_harness.py tests/test_claude_code_supervised_runner.py tests/test_claude_code_job_backend.py tests/test_claude_code_job_assembly.py tests/test_claude_code_host_compatibility.py
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pytest -q tests/test_supervised_execution.py tests/test_supervised_helper_kind.py tests/test_supervised_child.py tests/test_supervised_command_runner.py tests/test_supervised_run_coordinator.py tests/test_native_execution.py tests/test_provider_configuration.py tests/test_provider_execution_authority.py tests/test_provider_runtime_assembly.py tests/test_provider_runtime_binding.py
```

Security invariants: unchanged permission-mode plan; tool ceiling Read/Glob/Grep;
no-session-persistence; verified packet path/hash, fixed prompt/model/effort;
no ambient user/project/local settings; bare disables automatic customization
loading; skills disabled; empty strict MCP config; unchanged two environment
bindings; unchanged secret resolver/redaction, supervised lifecycle/dedup/provider
authority. No shell/subprocess was added to production. Host probes use only a
synthetic token and ephemeral loopback server; all CLI children exited naturally.
The opt-in fixture has hostile user/project/local hooks, environment overrides,
CLAUDE.md, skill and MCP definitions; no customization marker, forbidden-write
marker, ambient prompt canary or session JSONL was observed.

Known limitations:
- This is CLI containment, not an OS filesystem/network sandbox. Read permissions
  and managed-policy trust remain existing external boundaries.
- --bare changes discovery and auth behavior intentionally. Jobs cannot depend on
  ambient project/local settings. 2.1.152 exposes only Read; Glob/Grep availability
  is CLI-dependent. The explicit Bearer token is proven on this host only.
- No actual Windows/Linux installed Claude CLI run, real GLM turn, live DB,
  or installed Conductor runtime proof is claimed. The same explicit argv and
  unchanged native contracts apply on all OSes; unsupported CLIs reject rather
  than retry with weaker flags. Hosted CI and integrator review remain gates.
- CURRENT-WORK/handoff/COLLAB remain untouched as requested; integrator owns
  canonical projection closeout. Do not follow their old WO166 frontier blindly.

Next safe action: independently review the pushed exact candidate SHA and CI;
GPT integrator adjudicates/accepts/merges. Only after acceptance, a separately
authorized isolated authenticated one-shot can test Zero Relay. This lane does
not self-merge or claim ZERO_RELAY_OPERATIONAL. Exact frozen SHA and changed-file
hashes are in runs/WO-P1-168/result.md and the candidate assurance manifest/PR.
