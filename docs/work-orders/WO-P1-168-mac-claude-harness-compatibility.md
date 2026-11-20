# WO-P1-168 — Mac Claude harness compatibility

## R4 current authority — controlled continuation after quota reset

Status: READY_FOR_EXACT_SHA_REVIEW / R3 BOUNDED CORRECTIVE REPAIR
Owner: GPT-6 Astra / Poppy Javis, Codex task 01a0877a-2949-7270-a5de-57806897774f
Transfer authority: Issue #233 comment 5613527320 (Sol claim RELEASED/TRANSFERRED).
Worktree: /Users/aase7en/Desktop/A-Wiki-Conductor-wo168-r4
Branch: gpt/wo-p1-168-r4-settings-file-boundary
Committed handoff: 30497a0f62afc9792997dfa0ec6891aef197b0a9
Preserved dirty patch SHA256: b7174bd72221b1af27724ed26327a3df7eb13bb889bec619e2599bf55e321ae3
Evidence destination: runs/WO-P1-168/r4-astra/

The transfer was verified against GitHub, HEAD/upstream and all three dirty-file
hashes before mutation. This checkpoint preserves Sol's R4 filesystem repair.
The same WO scope remains: harness source, harness/backend tests, this WO and
ignored evidence. Root main, global continuity files, WO169 and other lanes are
read-only. Sol/integrator retains independent exact-SHA verification and merge.

Remaining bounded repairs, RED-first:
1. Reject duplicate JSON object keys, including decoded key aliases, before any
   deny-only projection. Ambiguous configuration maps to typed settings failure
   and must never call the runner.
2. Bound Windows quoting expansion of sanitized inline settings before runner,
   retaining conservative room for the fixed invocation and packet path. Reject
   oversized payloads with CLAUDE_SETTINGS_TOO_LARGE on every platform.

Keep R4 filesystem identity/bounded-read checks, process-bound provider identity,
read-only tools, explicit task packet, deny-only settings and no-session behavior.
Use synthetic fixtures and loopback only. No private credential/live provider.
Acceptance: RED evidence -> focused/related/real-Mac GREEN -> clean frozen commit
and pushed existing branch -> durable result for independent Sol/integrator review.
No self-merge and no claim of operational Zero Relay.

Everything below is dated history unless explicitly marked as an R4 checkpoint.

## R1 historical authority — superseded by R2/R3/R4

Status: FROZEN / READY_FOR_EXACT_SHA_REVIEW / R3 CORRECTIVE REPAIR
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

### R1 verification checkpoint

- RED commit 9b74137: 3 failures / 19 passes; the real CLI ignored both selected
  project and local deny rules, while allowed Read succeeded (positive control).
- GREEN after restoring project,local: 22/22 pass (6 real CLI cases + 16 harness
  contracts). Both deny sources now return error tool results without file
  content; permitted Read still returns the synthetic content. Bash/Write remain
  unavailable. No customization markers or session JSONL; no user settings load.
- Focused and related frontier: 186 passed / 12 expected skips (6 opt-in CLI +
  6 Windows integration) with actual python3.12, 4.50s.
- Compileall, whitespace, UTF-8 and bounded added-line credential-pattern checks
  PASS. Source delta remains one file; no resolver/native/supervisor changes.
- Real host CLI remains 2.1.152; all final host test children exited naturally.
  The separate failed hostile-selected-env diagnostic was terminated by verified
  exact PID/command identity and is not counted as GREEN.

Exact R1 candidate SHA is recorded after commit in runs/WO-P1-168/result.md and
its hashed assurance directory, plus the successor draft PR. Original parser
RED remains reproducible at 16dc834; initial PR #237 is merged, so R1 uses a new
PR from its actual merged base, without rewriting the accepted branch.

Security statement: preserve the ORIGINAL selected project/local permissions
and settings trust, plus plan/tool ceiling/no persistence/task binding. Bare,
skill suppression and strict empty MCP isolate customization execution. Explicit
environment-reference allowlist and redaction are unchanged. Selected project/
local env config remains trusted as before this task; it can override provider
variables and must be validated in the separate live-pilot authorization gate.
No claim that compatibility repair solves that pre-existing configuration risk.

Known limitations: installed Windows/Linux/newer Claude behavior remains
unproven; the original settings-source contract and one uniform argv are kept.
On this Mac bare mode exposes only Read. Canonical production supervised-process
composition remains Windows-specific, a separate R3 portability lane; no runtime
installation, authenticated GLM, or operational Zero-Relay proof occurred here.
Independent final review/CI and integrator acceptance of R1 remain pending.

Next safe action: inspect/review R1 exact SHA and hosted CI, then integrator
adjudication/merge. Keep the merged R0 security claim superseded until R1 is
accepted; do not start a live provider turn based only on its earlier green CI.

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


### R1 independent rejection — provider authority regression

After the original merge/post-main success, R1 reopened this WO because the accepted
`--setting-sources=` profile discarded project/local `permissions.deny` rules.
R1 candidate `56224670256c36b11389f9048ffdf956bfe7143f` restored
`--setting-sources project,local` and proved the deny rules, but independent GPT review
found a P1 provider-binding regression.

A real Mac Claude 2.1.152 probe put a hostile `ANTHROPIC_BASE_URL` and synthetic wrong
token into selected project settings while process env carried the authorized loopback
route. The authorized server received zero requests and the child timed out. Therefore
selected project/local settings can rewrite the provider route, reproducing the authority
class from DEFECT_LESSONS #20. Issue #233 comment 5610084601 freezes R1 as
CHANGES_REQUIRED / DO_NOT_MERGE.

### R2 design — sanitized deny-only settings projection

R2 claim: Issue #233 comment 5610087728.
Branch: `gpt/wo-p1-168-r2-sanitized-permissions`.
Base: frozen R1 `56224670256c36b11389f9048ffdf956bfe7143f`.

The harness now keeps ambient settings excluded with `--setting-sources=`. It reads only
worktree `.claude/settings.json` and `.claude/settings.local.json`, validates them
under bounded fail-closed rules, unions only `permissions.deny`, and passes a newly
constructed deny-only JSON object through explicit `--settings`.

No `env`, hooks, MCP, plugin flags, `defaultMode`, allow or ask rules are projected.
The settings files are bounded to 64 KiB each; deny rules are bounded by count and length;
the sanitized argv payload is capped at 16 KiB for cross-platform command-line safety.
Symlink/outside-worktree settings, malformed JSON/types, null ambiguity and oversized
input/output fail before the runner.

R2 RED commit:
`cf0680f6d88e05f01a9eaad57b57c84ae5c4c9f8`.

Unit RED on frozen R1 source:
13 failed / 15 passed, covering invocation contract, project+local deny projection,
malformed settings, oversized settings and symlink escape.

R2 current GREEN evidence:
- unit harness: 31/31 PASS;
- real installed Mac Claude 2.1.152 hostile-settings loopback: 6/6 PASS;
- related Claude/supervised/native/provider frontier: 201 PASS / 12 expected skips;
- compileall PASS;
- git diff --check PASS;
- no private credential or live provider used.

The host fixture places hostile provider env, hooks, MCP enablement, bypass default mode
and allow rules into project/local settings. The accepted process-bound synthetic provider
still receives the requests, project/local denied files do not leak, allowed Read works,
Write/Bash remain refused, and no customization/session residue is created.

Important CLI semantic: Claude 2.1.152 may suppress a denied tool call and restart the
model turn rather than emit a `tool_result.is_error`. R2 acceptance therefore pins the
security invariant (no denied execution/content leak), not one response representation.


### R3 parser-boundary hardening after interrupted Astra review

Astra's independent R2 review hit its Codex usage limit before returning a final
verdict, so the run does not provide acceptance authority. Before interruption it
completed deterministic adversarial probes that found a valid parser-boundary
defect family in exact R2 candidate
`11e045d643105625afc740ba295781cb41c25cdc`.

Observed on R2:
- deeply nested JSON below the 64 KiB source-file ceiling raised unhandled
  `RecursionError`;
- a JSON integer above Python's configured integer-string conversion limit raised
  unhandled `ValueError`;
- the settings source used `Path.read_bytes()`, so the nominal 64 KiB gate was
  applied only after an unbounded whole-file read.

Issue #233 comments `5610802627` and `5610806494` record the rejection and
successor claim. R2 / PR #240 remains frozen CHANGES_REQUIRED even though hosted
CI run `34417195891` succeeded.

R3 RED commit:
`05d49e6bbc37421471cc95c0cf937573c2380b8f`.

RED result: 5 failed / 38 passed:
- two harness parser exceptions escaped instead of typed rejection;
- one test proved settings still used unbounded `Path.read_bytes()`;
- two backend tests proved the hostile parser exceptions escaped the durable
  backend instead of mapping to typed no-mutation recovery.

R3 repair is intentionally local to the harness. It does not add a broad backend
`except Exception`. The harness now:
- opens each settings path as an exact regular file with no-follow where the OS
  supports it;
- compares opened-handle and named-file identity before reading;
- rejects non-regular/symlink/identity-drift cases;
- rejects a stat-proven oversized file before content read;
- otherwise reads at most the configured limit plus one byte;
- rechecks file identity/size/mtime after reading;
- maps UTF-8, JSON `ValueError` and parser `RecursionError` to
  `CLAUDE_SETTINGS_INVALID`.

R3 verification before candidate freeze:
- focused harness + backend: 43/43 PASS;
- real installed Mac Claude 2.1.152 hostile-settings loopback: 6/6 PASS;
- Claude/supervised/native/provider frontier: 206 PASS / 12 expected skips;
- compileall PASS;
- git diff --check PASS;
- no residual Claude/pytest probe processes;
- no private credential/live provider used.

The accepted R2 security behavior is preserved: ambient settings remain excluded,
only bounded project/local `permissions.deny` are projected, admitted provider
endpoint/auth remains process-bound, hostile hooks/MCP/defaultMode/allow fields
do not cross, denied file content does not leak, and allowed Read remains a
positive control.

R3 still requires exact-SHA independent review and hosted CI before merge. Astra
quota exhaustion is an execution-resource condition, not grounds to weaken the
independent-review gate.


### R4 root-cause reset — settings filesystem boundary

R3 candidate `b1e048ffa9c51d37af19164fab0f789015b22fe1` passed its full
hosted CI run `34422252499`, including Windows E2E, macOS and Ubuntu. It is still
CHANGES_REQUIRED: a later real local probe made the worktree `.claude` directory a
self-referential symlink and the R3 pre-open `Path.resolve()` raised an unhandled
`RuntimeError`. The same audit showed a POSIX FIFO at `settings.json` could reach
blocking `os.open(O_RDONLY)` before R3 proved the entry was a regular file.

This is durable evidence that CI green alone is not acceptance and that the repeated
R1/R2/R3 defects shared one root cause: project-controlled mutable settings filesystem
state was being validated piecemeal.

Issue #233 comment `5611006221` rejects R3 and comment `5611009217` opens R4.
R4 branch: `gpt/wo-p1-168-r4-settings-file-boundary`.
R4 base: exact R3 `b1e048ffa9c51d37af19164fab0f789015b22fe1`.

R4 RED commit:
`30497a0f62afc9792997dfa0ec6891aef197b0a9`.

RED result: 3 failed / 44 passed:
- worktree `.claude` symlink loop -> unhandled RuntimeError;
- FIFO settings object reached `os.open` before regular-file rejection;
- backend mapped the escaping path error to UNKNOWN / BACKEND_EXECUTION_FAILED instead
  of typed NO_MUTATION / HARNESS_FAILED.

R4 repairs only the harness file-read boundary:
- no-follow pre-open named metadata is mandatory; only initial FileNotFound is benign;
- non-regular entries fail before open;
- strict resolved containment is checked before open;
- open uses O_NOFOLLOW and O_NONBLOCK when the platform exposes them;
- opened handle must match the pre-open and current named identity;
- size/mtime stability is checked around open/read;
- content is still bounded to max+1 bytes;
- after read, identity and in-worktree containment are proved again;
- path resolution/metadata/open/read/close failures become typed settings failures.

Additional deterministic race coverage swaps `settings.json` to a new inode during the
bounded read. The post-read identity check rejects it before runner execution.

R4 current local evidence:
- focused harness + backend: 48/48 PASS;
- real installed Mac Claude 2.1.152 hostile-settings loopback: 6/6 PASS;
- Claude/supervised/native/provider frontier: 211 PASS / 12 expected skips;
- compileall PASS;
- git diff --check PASS;
- no residual Claude/pytest process;
- no private credential/live provider used.

R4 still requires exact candidate freeze, clean-archive re-verification, hosted exact-head
CI and independent exact-SHA review before any merge. Codex quota remains exhausted until
the reported reset window; Claude CLI OAuth is revoked and Gemini CLI requires interactive
authentication. These reviewer resource limits do not weaken the gate.


### R4 Astra corrective verification checkpoint — 2026-09-10

Ownership transfer: Issue #233 comment 5613527320. Exact inherited Sol patch was
preserved in checkpoint commit 70814c130886439b8fe323d40c787a3bdba80322 before
adding new P2 tests. No reset/rebase/force-push or change of worktree/branch.

P2 RED commit: f9ac5b0e001c9f2682b337a0ad6b28680ec8fb7f.
Focused RED: 14 failed / 50 passed. Both project/local settings reject duplicate
keys at root, permission level, escaped key aliases, identical duplicate values
and nested ignored objects. Backend tests require typed NO_MUTATION recovery.
The Windows test uses a 16,282-byte JSON payload that previously passed the byte
ceiling but expanded beyond CreateProcessW's 32,767-unit limit after quoting.
Prior real-Mac duplicate-key RED also showed synthetic denied-file content sent
to the synthetic loopback provider; its preserved evidence binds to Sol's patch.

Repair:
- JSON object_pairs_hook detects duplicate decoded keys before any projection;
  the existing parser error boundary maps rejection to CLAUDE_SETTINGS_INVALID.
- Pure stdlib list2cmdline serialization measures the Windows-quoted settings
  argument on every host. JSON output is explicitly ASCII-escaped, so its quoted
  character count equals UTF-16 units. The argument cap is 16,384 units, in
  addition to the existing 16 KiB JSON-byte cap, leaving 16,383 units for the
  other arguments/launcher/NUL. Overflow maps to CLAUDE_SETTINGS_TOO_LARGE before
  runner invocation. No process or provider code was added or changed.
- Existing R4 filesystem logic is unchanged by this corrective source delta.

Verification before source freeze:
- focused harness/backend: 64 passed;
- Claude/supervised/native/provider regression: 227 passed / 12 expected skips
  (6 Windows-specific integrations and 6 opt-in host tests, run separately below);
- actual Mac Claude Code 2.1.152: 6/6 passed with disposable HOME/project,
  synthetic credential and loopback provider only;
- large normal and quote-containing settings positive controls retain exact
  deny rules and fit the Windows command-line budget with room to spare;
- compileall and git diff --check passed.

Exact candidate SHA, clean-archive re-verification, changed-file list, hashes and
push evidence are recorded after commit in runs/WO-P1-168/r4-astra/result.md and
its assurance directory. This commit is the frozen candidate checkpoint; no
further source edits may be made without a new candidate and re-verification.

Remaining integrator gate: independently re-pin the pushed exact SHA, review the
R4 filesystem repair plus these two P2 closures, and inspect exact-head hosted CI
before any merge. This author does not merge. Mac production supervision and
live authenticated GLM/Zero Relay remain unproven and outside this repair.
Global CURRENT-WORK.md/handoff.md/COLLAB.md are unchanged under the existing
single-writer boundary; this WO is the lane's portable continuation checkpoint.
