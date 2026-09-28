# WO-P1-564 — CoinTH live quota policy and global Codex pre-dispatch hook

Issue: #564
Status: ACTIVE / CLAIMED / HOOK CONFIGURED / CODEX TRUST REVIEW REQUIRED
Risk/topology: R3 / CONTROL_PLANE_ONLY
Owner/integrator: Poppy Javis
Repository: aase7en/A-Wiki-Conductor
Worktree: /Users/aase7en/.codex/worktrees/cointh-quota-preflight/A-Wiki-Conductor-codex-supervisor
Branch: codex/wo-p1-564-cointh-quota-hook
Base HEAD: 0f0a5f17b33e82516e39ff00f482887728810e87

## Goal

Use one fresh CoinTH API quota GET before every eligible GLM request so a valid
positive proxy balance can be used for real, bounded work without a separate
upstream smoke call. Add a user-global Codex PreToolUse hook that enforces this
quota check without calling a model. A concrete provider response from the real
GLM request, not a prior smoke, establishes or blocks that exact model route.

## Binding behavior

- Request `https://cointh.com/glm/api/quota` over verified HTTPS with
  `x-api-key` from the existing `COINTH_GLM_AUTH_TOKEN` environment binding.
  Add no-cache request headers. Make one request immediately before each
  matching GLM tool call; do not cache quota state or probe a model.
- A successful HTTP 200 with a complete, internally valid five-hour tuple,
  `remaining_5h > 0`, and no positive expiry flag means
  `PROXY_QUOTA_STATE=AVAILABLE`, regardless of `window_source`. Preserve
  `window_source=stale` as observed metadata; it does not veto the user's
  authorized dispatch rule.
- A complete tuple with `remaining_5h == 0` is `EXHAUSTED`. Missing credentials,
  non-200/transport/TLS errors, malformed/incomplete counters, inconsistent
  fields, or an expired tuple are `UNKNOWN`. Never collapse `UNKNOWN` into
  `EXHAUSTED` or claim upstream throttling from a quota response.
- Do not send a separate upstream readiness/smoke request before a useful
  real task. Let the actual model request prove the route. If that request
  returns explicit upstream throttle/reset evidence, record and block only that
  exact provider/model route until reset unless new material evidence changes.
  Diagnose other concrete route errors only after observing the actual failure;
  do not loop probes.
- The hook only observes explicit model/tool arguments for a GLM route. Positive
  quota silently lets the original tool call continue under its normal Codex
  permission prompt. Exhausted/unknown quota denies only that GLM call. It does
  not authorize tasks, claims, WIP, mutation, direct Kilo bypass, review, merge,
  or completion. Other calls pass through unchanged.
- Read the credential only from the already-bound environment variable. Never
  scan Drive, `.env`, files, keychain, or process arguments for credentials;
  never print, persist, log, or pass the secret as a subprocess argument.

## Exact scope

- `docs/runbooks/cointh-glm-quota.md`
- `docs/runbooks/codex-global-cointh-quota-hook.md` (new)
- `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`
- `docs/agent-collab/CAPABILITY_MATRIX.md` (scope addendum: keep model routing evidence aligned)
- `.agents/skills/a-fasttask/references/conductor.md`
- `scripts/codex_hooks/cointh_quota_pretool.py` (new)
- this work order
- local Mac Codex configuration: `/Users/aase7en/.codex/hooks.json` and
  `/Users/aase7en/.codex/hooks/cointh_quota_pretool.py`

## Protected and forbidden scope

Do not modify `.agents/skills/a-fasttask/SKILL.md` while Issue #562 / PR #563
owns that path, or `.agents/skills/a-faster/SKILL.md` while Issue #549 / PR #550
owns it. Do not modify `.codex/hooks.json` or
`.codex/hooks/a_sunday_lifecycle.py` (Issue #545), `src/a_conductor/` or tests
owned by #498/#549, `src/a_conductor/a_faster_utilization_guard.py`, any
A-Wiki source/secret, or SunDayRemoteMCP. This global quota hook is separate
from the #498 executable GUARD and the #545 lifecycle hook; no trust hashes may
be fabricated or edited.

No user token, API key, Drive path containing secrets, or raw provider payload
with credentials may be committed. The public hook implementation contains no
credential material.

## Pre-dispatch and WIP evidence

Claim recorded on Issue #564 comment 5857716760. The last accepted A-Faster
snapshot recorded on Issue #547 comment 5847879995 was `FANOUT_TARGET=0`,
`UNUSED_SAFE_CAPACITY=1`, `A_FASTER_UNDERUTILIZED=true`,
`AUTO_REFILL_REQUIRED=false`, blockers
`NO_INDEPENDENT_READY_WORK,QUOTA_UNKNOWN,GLM_ROUTE_BLOCKED`. It is carried
forward unchanged: its quota/readiness fields predate the corrected user rule,
and its no-auto-refill decision does not prevent this explicitly requested
manual lane from consuming the one available mutable slot. This WO does not
create a second utilization authority or a per-device WIP budget.

Current issue/claim census at claim time: #498 owns one active mutable lane;
#562 owns one active author lane and has a separate exact-SHA review/CI slot
bound to candidate `3c27bfe77d43bd764fe7ea0593d8235bd15474e2`; #547/#549 remain
parked and #551 remains waiting on its external contract. This lane is the
third active mutable lane under the global limit of three. The only independent
review slot stays with #562 until its candidate is reconciled. SundayMCP
recovery found only terminal executions and its lane list was empty.

Before each material GLM dispatch, RECOVER terminal work, verify this exact
worktree/branch/HEAD/claim/scope, refresh the CoinTH GET, and confirm the
current claim/WIP census plus durable Sunday task binding. A complete valid
positive GET is `PROXY_QUOTA_STATE=AVAILABLE` even when
`window_source=stale`; the field remains audit metadata. Do not make a separate
upstream smoke call. The completed Kilo MAX review is actual successful
evidence that this exact route worked for that request. Do not wait for
Windows: the authorized Mac SundayMCP/Kilo route is independent. Do not issue a
second GLM request while an earlier matching execution is RUNNING/UNKNOWN/
TERMINAL_UNHARVESTED.

## Incident and advisory guidance

Record and prevent the two observed failures: (1) an HTTP 200 positive quota
tuple was incorrectly vetoed only because `window_source=stale`; classify a
fresh valid positive tuple as AVAILABLE and let the real task test upstream;
(2) the first Kilo CLI request placed its positional prompt after `--file`
options, so Kilo parsed it as a file path and exited before inference. The
prompt must immediately follow `kilo run`, before flags. The corrected GET
semantics and CLI ordering are recorded in the quota runbook and global-hook
guide.

JEV-5 is implemented and merged, but production JEV execution still defaults
to `OFF`; no dedicated executor/model-selection family is admitted for this
hook. Keep the quota hook deterministic and model-free. If a bounded route
suggestion is admitted in a future task-routing family, it may rank only a
deterministically eligible candidate set and may never alter quota, claims,
WIP, permissions, or mutation/review authority.

## Continuity and follow-up gates

- The repository handler now exists at `scripts/codex_hooks/cointh_quota_pretool.py`.
  A matching user-global copy is installed at
  `/Users/aase7en/.codex/hooks/cointh_quota_pretool.py`, and a narrow
  `PreToolUse` registration was appended to the existing
  `/Users/aase7en/.codex/hooks.json` without editing `hooks.state`. The current
  inherited `COINTH_GLM_AUTH_TOKEN` binding is present. A fresh secret-safe
  quota GET returned HTTP 200, `remaining_5h=80000000`, `used_5h=0`,
  `is_expired=false`, `window_source=stale`; classification is AVAILABLE.
  At this checkpoint approval was pending; see the later operator-approved
  activation record below for the current status.
- Issue #498's exact worktree still has dirty `CURRENT-WORK.md`, its work order,
  and `handoff.md`; #498 owns the first and last files. This #564 lane must not
  delegate or stop without the repository-required continuity checkpoint. The
  user's transfer/release decision is pending. Until then, do not edit those
  shared paths or send a GLM writer. The locally available positive quota does
  not override this ownership/continuity gate.
- `.agents/skills/a-fasttask/SKILL.md` is protected by the active #562 claim.
  Its old upstream-READY/stale-window wording needs a successor reconciliation
  after #562 releases the exact file. The non-overlapping A-FastTask reference,
  quota runbook, and routing guide are updated in this lane; do not claim the
  top-level skill itself is reconciled yet.

## Hook namespace repair — 2026-09-28

The installed Codex tool catalog exposes the Mac dispatch tool as
`mcp__codex_apps__sundaymcp_mac_sunday_dispatch`. The first hook registration
matched only the legacy Sunday namespace, so this task's actual durable Mac
dispatch could bypass the quota preflight. The matcher now includes the
observed Mac tool name, and the parser recognizes an explicit Kilo/Claude model
selector behind the actual `/usr/bin/env` wrapper. Repository and installed
handlers must remain byte-identical. This repairs a tool-name/wrapper mismatch;
it does not change quota policy, trust state, dispatch authority, or permission
handling.

## Acceptance

- One consistent proxy-quota state table and upstream-after-real-request rule
  appears in the runbook, routing guide, reference, and global-hook guide.
- Global hook examines only explicit GLM model invocations on supported Codex
  tool paths, makes exactly one bounded no-cache GET, and makes no model call.
- Hook preserves ordinary permission checks on success and blocks only the
  target GLM call for exhausted/unknown evidence.
- Static syntax/JSON/UTF-8/diff/scope/secret checks are clean. Exact-SHA hosted
  CI, independent exact-SHA R3 review, GPT adjudication, and post-main proof are
  still required before merge/acceptance.
- Local activation occurs only after `/hooks` review/trust; never write
  `hooks.state` trust hashes directly. Record trust state only after reading it
  back from Codex.

## Checkpoint — 2026-09-27 17:23 UTC

- Recovered current Issue #564 and both claim/scope comments. Issue remains
  OPEN; the exact worktree, branch, base HEAD, seven repository paths, and two
  user-local paths remain the only authorized scope. Git reports
  `codex/wo-p1-564-cointh-quota-hook @ 0f0a5f17b33e82516e39ff00f482887728810e87`.
- Recovered 160 SundayMCP executions: 106 COMPLETED, 14 FAILED, 40 CANCELLED;
  all replay records verify terminal state, with no RUNNING, UNKNOWN, ambiguous
  launch, or unharvested record. Sunday lane list is empty.
- Rechecked active ownership evidence. #498 remains OPEN at
  `wo-p1-498-live-identity-production @ 8d2aae705a6d2180fd36abaf7f1ed545355d554c`
  with dirty `CURRENT-WORK.md`, its WO, and `handoff.md`; #498 still owns the
  continuity paths. No transfer/release was recorded. Do not edit those files,
  delegate a GLM writer, or start a material delegated lane until the owner
  checkpoints/releases that scope. This is an ownership/continuity gate, not a
  CoinTH quota exhaustion finding.
- #562/#563 remains a separate R3 review/CI lane on exact candidate
  `3c27bfe77d43bd764fe7ea0593d8235bd15474e2`. Current run `36333019964` is
  still in progress on the Windows test job; Ubuntu/macOS smoke jobs passed.
  GitHub has no submitted review for current #563, so its independent-review
  slot remains occupied and cannot be reassigned to this lane.
- Reconciliation found the repository handler and installed user-global handler
  had different contents. Replaced the broader repository parser with the
  installed CLI-aware implementation, narrowed shell parsing to supported
  command segments, bounded the response, removed the credential from curl's
  child environment, and made malformed/expired reset tuples fail closed. The
  installed copy now matches the repository source byte-for-byte and is mode
  `0700`. The existing single global PreToolUse registration is preserved; no
  `hooks.state` file was written or found, so Codex `/hooks` trust/activation
  is not claimed.
- Static checks at this checkpoint: exact changed-path allowlist PASS; Python
  AST/compile and UTF-8 PASS; no trailing whitespace; `git diff --check` PASS;
  global config parses and has exactly one narrow registration for
  `Bash|mcp__sunday_mcp__sunday_dispatch`; source/install SHA equality PASS;
  no key-like credential signature in the seven repository changes. Automated
  tests are not authorized by this claim and were not run. No quota GET,
  model call, or JEV call was made in this checkpoint; quota must be freshly
  checked immediately before any later eligible GLM dispatch.
- Next safe sequence: wait for #563's existing CI/review fan-in; finish only
  non-overlapping static/documentation checks for #564; ask the user to review
  the concrete hook through Codex `/hooks` when convenient. Keep #564 local and
  unaccepted until its own exact-SHA CI, independent R3 review, GPT adjudication,
  and post-main verification complete.

### Follow-up — 2026-09-27 17:29 UTC

- Re-synced the installed handler after the final classifier edit; byte equality
  still holds. A zero-second countdown is not independently treated as
  exhaustion/expiry; `is_expired=true`, negative countdown, malformed reset
  timestamp, or inconsistent counters remain `UNKNOWN`. Positive balance is
  never vetoed by `window_source=stale`.
- No quota GET or GLM request was made in this follow-up: the #498 continuity
  owner gate still blocks a delegated GLM writer, and there is no eligible
  imminent dispatch to preflight. The last positive API tuple in this WO is
  historical evidence only, not a current admission result.

## Current checkpoint — 2026-09-28 Mac dispatch matcher repair

- Worktree remains `codex/wo-p1-564-cointh-quota-hook` based on
  `0f0a5f17b33e82516e39ff00f482887728810e87`. The exact seven repository
  paths already claimed by Issue #564 are dirty/untracked; no new scope or WIP
  lane was added.
- Recovered the actual SundayMCP Mac function name from the exposed tool
  catalog: `mcp__codex_apps__sundaymcp_mac_sunday_dispatch`. The global matcher
  previously used only a legacy namespace, so the current Mac dispatch did not
  reach this guard. Added the observed name in the config and parser.
- The real dispatch command wraps Kilo with `/usr/bin/env`; the parser now
  walks that wrapper and its environment assignments before requiring an
  explicit CLI model selector. The installed handler was recopied from the
  repository source. No quota state, credential, request body, or trust hash
  was printed or written.
- Static verification passed: exact seven-path scope, strict UTF-8,
  whitespace, JSON parse, Python AST parse, current MCP name + env-wrapped
  explicit GLM selector positive case, prompt-only non-dispatch negative case,
  repository/installed handler byte equality, and `git diff --check`. No
  automated tests were added or run. No provider/model request was made here.
- At this checkpoint, user approval/trust had not yet been reported; that
  historical status was superseded by the operator confirmation below. The
  hooks.state trust file was not changed by the integrator.
- Exact next action: review the seven-path diff, commit/push this replacement
  candidate on the existing branch, then obtain exact-head CI and an
  independent R3 review. If a GLM review is selected, make a fresh quota GET
  immediately before dispatch. JEV remains out of the quota hook and its
  executable advisory route is currently `OFF`.

## Adjacent hook false-positive observed — 2026-09-28

While recording the task's lessons in local memory, a shell command containing
only a documentation heredoc was denied by the existing A-Sunday lifecycle
hook because the prose mentioned the Kilo invocation syntax. No Kilo process or
model call was attempted and the blocked shell command did not execute. This
reveals a false positive in the #545-owned lifecycle guard. Its files are
outside this claim and were left unchanged; route that guard repair through its
existing owner after this lane is accepted.

## Bounded GLM-5.3 MAX policy alignment — 2026-09-28

- Dispatched by the GPT integrator as the bounded GLM-5.3 MAX implementation
  executor under this existing claim (quota-preflight evidence belongs to the
  dispatch record). Runtime status/collection for exec-mukj7wjw-emq1qe8f
  reported claimPresent=false, identityVerified=false, and
  bindingDigest=null; the model report is therefore not a claim or review
  receipt. GPT independently rechecked the exact Git worktree/branch/HEAD and
  changed-file scope; deterministic diff checks govern acceptance. Only the
  four already-claimed documentation paths
  changed: `docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md`,
  `docs/agent-collab/CAPABILITY_MATRIX.md`,
  `.agents/skills/a-fasttask/references/conductor.md`, and this work order.
- Aligned all three policy files with the user-directed acceptance
  clarification in Issue #564 comment 5861405985: every individual
  `SAFE_READY` task receives one `GLM_OFFLOAD` assessment after the normal
  task/dependency/claim/exact-scope/WIP/permission gates — size or GPT/Luna
  supervision alone never skips it; GLM-5.3 MAX is the default first executor
  to try for useful bounded reasoning, implementation, repair, tests, and
  eligible independent review whenever task fit and the exact route are
  admitted, while GLM-5.3 Flash stays bounded read-only; GPT/Luna remains
  supervisor for decomposition, trust/authority/architecture, integration,
  and final adjudication/acceptance, and takes implementation back only with
  a recorded GLM blocker; dispositions are `DISPATCHED`, `NOT_BENEFICIAL`
  with a concrete deterministic/no-inference reason, or `BLOCKED` with a
  typed route/claim/WIP/permission reason, with no empty prompts,
  manufactured tasks, redundant calls, or quota burning for token consumption
  alone — available quota is used productively for real READY work.
- Stated explicitly in all three policy files that the Codex PreToolUse
  registration is a quota guard only: it never selects models, creates tasks,
  or dispatches work and is not a second scheduler/model authority; accepted
  A-Faster `FANOUT_TARGET`/`AUTO_REFILL_REQUIRED` markers and the global WIP
  budget remain the capacity authorities.
- Quota semantics are unchanged and remain exactly as accepted in this WO:
  one fresh secret-safe CoinTH GET immediately before each material GLM
  request; a complete positive tuple is `AVAILABLE` even when
  `window_source=stale`; no upstream pre-probe; the real useful request tests
  the route; only an explicit upstream throttle/reset blocks that exact
  provider/model route until reset; no secrets printed, persisted, or passed
  in argv. Exact claim, mutation-owner, GLM task scope, independent R3 review
  identity, and GPT acceptance gates are not relaxed.
- Verification for this pass: `git status` shows only the four claimed paths
  modified; strict UTF-8 decode PASS; no trailing whitespace; `git diff
  --check` PASS. No hooks, `/Users/aase7en/.codex` files, protected skill
  files (`.agents/skills/a-fasttask/SKILL.md`,
  `.agents/skills/a-faster/SKILL.md`), `.codex/hooks`, runtime/source/tests,
  A-Wiki, SunDayRemoteMCP, or GitHub state were touched; nothing was
  committed or pushed. Exact-SHA CI, independent R3 review, GPT adjudication,
  and post-main proof remain open; no formal review or acceptance is claimed
  for this pass.


## Operator-approved global quota hook — 2026-09-28

- The operator confirmed approval through Codex /hooks and provided a
  screenshot with both A-Sunday PreToolUse entries enabled. The current
  user-global /Users/aase7en/.codex/hooks.json also contains the quota guard
  matcher for Bash, local Sunday dispatch, and SundayMCP Mac dispatch; the
  installed helper is present. No hook configuration, hooks.state, or trust
  hash was changed in this checkpoint.
- A fresh synthetic GLM dispatch event was sent to the installed quota helper
  before the material dispatch; it returned no deny and exit 0. The helper
  performs only a fresh quota GET and leaves Codex permission handling intact.
- This approval means the quota hook is enabled; it does not turn the hook into
  a model selector, task creator, or scheduler. The GLM-first task-routing
  policy is recorded separately above.


## PR checkpoint before WO-only follow-up — 2026-09-28

- The operator confirmed Codex `/hooks` approval and supplied screenshots with both A-Sunday PreToolUse entries enabled. The matching quota helper was exercised with a synthetic GLM dispatch event and returned allow/exit 0. The hook is a quota guard only; it does not choose GLM, create work, or schedule calls. The integrator did not change user-global hook configuration, `hooks.state`, or trust hashes.
- At this checkpoint, the GLM-first policy alignment and operator-approval record were committed/pushed on this branch at `4959e1683dbf590bc484665245c75290f6077ec1`. The tracked repository changes remained within the seven-path #564 scope.
- At that checkpoint, PR #565 was open/draft at SHA `4959e1683dbf590bc484665245c75290f6077ec1`, and exact-head CI run `36364631542` was queued. This is a historical snapshot: the subsequent WO-only follow-up advances the PR head. Re-fetch the live PR and CI before acting. No independent PR review had been recorded at that checkpoint. Merge, GPT acceptance, and post-main proof remained pending. Do not treat the GLM implementation execution as a review receipt: its runtime attestation had `claimPresent=false`, `identity.verified=false`, and no binding digest; the integrator checked the GitHub claim and diff directly.
- A post-dispatch quota read remained `AVAILABLE`; the samples span other activity and do not attribute the observed counter change to this one execution. No credential or raw response was recorded.
- Next action: recheck the exact-SHA CI and the available independent R3 review lane, then reconcile findings. Keep the branch frozen for review and do not merge until all acceptance evidence is present.


## Exact-SHA GLM review and bounded matcher repair — 2026-09-28

- Recovery/reconciliation found only terminal WO-P1-564 reviews before the
  retry. The reserved retry `exec-wo564r3-c4e918a2d703` / attempt
  `attempt-0002-c4e918a2d703` completed, was harvested, and was collected at
  `b4d71a55957809c72fd577f7198262d5091fcb5f`, with verified reviewer identity
  and binding digest
  `52b17d5162e816cbc08e5cc708e64263cceaca0d0e185600f959d776ea9a7a0a`. Output
  digest: `4fcaf9ef2dc11200bb379364e6c670c06eb43546dd9b449424f556f613c6f33c`.
  It returned `PASS WITH FINDINGS` (0 P0/P1, 1 P2, 6 P3). Kilo output showed
  `ask · glm-5.3` and a 23,126-byte review. The evidence bundle does not contain
  pre/post quota counters, so no exact quota delta is claimed.
- The executor used read-only `wc`, `git`, and `grep` commands despite the
  no-shell prompt; its initial hash command was denied. It made no edits, ran
  no tests, and made no GitHub or provider calls. Preserve that deviation in
  the review record; it does not invalidate the inspected code findings, but
  this is not final acceptance or review of a future candidate.
- GPT independently adjudicates P2-1 as blocking current acceptance:
  newline-separated shell commands containing an explicit GLM selector can be
  parsed as one segment and miss the required fresh quota GET. This contradicts
  the binding one-GET-before-each-eligible-GLM contract even though the helper
  is documented as an incomplete backstop. The issue review reservation is
  closed and its read-only slot released; the same #564 author claim is
  unblocked for a bounded repair.
- Next task under the existing claim: GLM-5.3 MAX first executor, change only
  `scripts/codex_hooks/cointh_quota_pretool.py` so explicit GLM selectors in
  separate newline-delimited shell commands are detected, while quoted prompt
  text and non-dispatch mentions remain non-matches. Preserve the exact
  one-GET quota semantics, provider classification, secret handling, normal
  permission flow, and all claim/authority boundaries. Do not edit protected
  #562/#549/#545 paths, local installed hooks/config, tests, or any other file.
  No commit, push, final review, or merge is authorized by this checkpoint.
- After the bounded result, GPT inspects every diff and a non-test syntax/diff
  check. Any changed candidate needs a new exact-SHA R3 review and fresh CI
  evidence before acceptance; do not reuse the review of the old SHA. Keep the
  accepted WIP markers unchanged: `FANOUT_TARGET=0`,
  `UNUSED_SAFE_CAPACITY=1`, `AUTO_REFILL_REQUIRED=false`.
- Planned durable author execution for this one-file continuation:
  `exec-wo564fix-67a9d11c951b` / `attempt-0001-67a9d11c951b`, same #564
  worktree/branch at dispatch HEAD `b4d71a55957809c72fd577f7198262d5091fcb5f`,
  scope `scripts/codex_hooks/cointh_quota_pretool.py`, model
  `cointh-glm/glm-5.3` MAX, binding digest
  `949a85635259b0f4221b0d24793a296b54403be709be2f13439252862261c028`.
  Dispatch only after a fresh quota-hook admission and another recovery check;
  if it denies or the ID already exists, stop and reconcile rather than retry.

## Harvested repair result — 2026-09-28

- The reserved execution above completed with verified exit code 0 and was
  harvested/collected: `exec-wo564fix-67a9d11c951b`, attempt
  `attempt-0001-67a9d11c951b`. Collection reports
  `identityVerified=true`, binding digest
  `949a85635259b0f4221b0d24793a296b54403be709be2f13439252862261c028`,
  execution HEAD `b4d71a55957809c72fd577f7198262d5091fcb5f`, and output digest
  `6b55e3b4a497f35c691ce3b21286bed6bfe2aad78d86f6d48595f3fd3dc2823f`.
  Kilo output identified `code · glm-5.3`; quota counters were not included,
  so this records model use, not an attributed token/quota delta.
- The source change remains within the one-file execution scope. It splits
  unquoted command separators and newlines while retaining quoted multiline
  text, and skips recognized here-document bodies so command-like examples in
  documentation are not treated as executable GLM calls. The existing model
  selector and quota-state paths remain unchanged.
- The author worktree is still on branch
  `codex/wo-p1-564-cointh-quota-hook`, HEAD
  `b4d71a55957809c72fd577f7198262d5091fcb5f`. Current tracked changes are the
  claimed hook and this work-order checkpoint only; no untracked paths were
  reported. `git diff --check` and in-memory Python syntax compilation pass.
  No tests were run because the current claim explicitly excludes tests.
- Re-fetching `gh pr diff 565` produced the same frozen old-review artifact:
  81,682 bytes, SHA-256
  `732d6d18f6b116dd07a9b1e491f634fdc2589e1dd0a1ac2c977d8c4f8a6d50b2`.
  Kilo's collected repair transcript says `code · glm-5.3`; the durable task
  binding requested MAX, but the transcript does not independently echo an
  effort/variant value, so that exact setting is not claimed as observed.
- The earlier exact-SHA review applies only to the frozen old candidate; its
  frozen diff hash was independently reproduced from current GitHub PR #565.
  This repaired working diff has no new PR head, CI, or independent R3 review.
  Do not treat the repair or static checks as acceptance. The prior checkpoint's
  publication/review/merge restrictions remain in force pending an authorized
  continuation and any needed test-scope addendum.

### GPT recovery and static review — 2026-09-28

- Recovered the latest execution through the durable SundayMCP endpoint after
  the Mac alias returned `Session terminated`. The generic endpoint confirms
  `exec-wo564fix-67a9d11c951b` is `COMPLETED`, harvested, and already
  collected; `identityVerified=true`, exit code 0, binding digest
  `949a85635259b0f4221b0d24793a296b54403be709be2f13439252862261c028`, and
  output digest `6b55e3b4a497f35c691ce3b21286bed6bfe2aad78d86f6d48595f3fd3dc2823f`.
  Its Kilo banner is `code · glm-5.3`. The Mac lane list is empty. No exact
  pre/post CoinTH counters were collected, so no token delta is attributed.
- GPT rechecked the candidate: only the already-claimed hook source and this
  work order are modified; HEAD remains
  `b4d71a55957809c72fd577f7198262d5091fcb5f`; Python AST parsing and
  `git diff --check` pass. No tests, commit, push, CI, or global-hook write was
  performed. The repository hook and installed user-global copy are currently
  not byte-identical because this working repair has not been installed.
- The candidate parser covers direct supported CLI selectors, unquoted
  separators/newlines, quoted multi-line prompts, and recognized heredocs. Its
  output explicitly leaves nested shell substitutions/backticks, some
  delimiter forms, and CRLF heredoc termination approximate; the hook is not a
  complete shell interpreter. These limitations need disposition in the new
  exact-SHA R3 review. The previous review does not cover this working diff.
- Clarification for future routing: even when enabled, this PreToolUse hook
  only makes one fresh quota admission decision for an already-selected GLM
  request. It does not select GLM, create a task, or dispatch one. GLM-first
  task selection remains a supervisor/router responsibility; do not describe
  quota-hook success as automatic GLM use. This run is evidence of an actual
  GLM-5.3 execution, while quota consumption remains unquantified.
- Next safe action: obtain a new independent exact-candidate R3 review and
  reconcile its findings under the existing claim. Keep the installed helper,
  hook registration, hooks.state, and trust hashes unchanged until that review
  and the required activation gates are satisfied. No acceptance or merge is
  claimed.

## Continuation scope addendum and focused test task — 2026-09-28

- Issue #564 scope addendum `5865895184` extends the same author claim by the
  single path `tests/test_cointh_quota_pretool.py`. It authorizes offline
  focused tests for newline-separated selectors, quoted multiline prompts,
  recognized heredocs, and preserved separator/env-wrapped selector behavior.
  It also authorizes a same-branch candidate commit/push after tests pass,
  exact-head CI, a new independent exact-SHA R3 review, GPT integrator
  adjudication, expected-head merge after all gates, post-main verification,
  and normal issue close/release. It creates no task/owner/worktree/WIP lane.
- Collision evidence: no candidate file or dirty path in all 70 registered
  worktrees; GitHub code search returned zero file matches, and open Issue/PR
  searches found no candidate. Keep accepted markers unchanged:
  `FANOUT_TARGET=0`, `UNUSED_SAFE_CAPACITY=1`,
  `AUTO_REFILL_REQUIRED=false`.
- The hook repair execution and harvest are terminal; no writer is active in
  this worktree. Current binding remains repo `aase7en/A-Wiki-Conductor`,
  worktree `/Users/aase7en/.codex/worktrees/cointh-quota-preflight/A-Wiki-Conductor-codex-supervisor`,
  branch `codex/wo-p1-564-cointh-quota-hook`, HEAD
  `b4d71a55957809c72fd577f7198262d5091fcb5f`. The test lane may mutate only
  the newly authorized test file and may read the existing hook source.
- GLM_OFFLOAD assessment for this focused R3 task: `ELIGIBLE` — bounded tests
  directly guard provider-admission behavior; exact issue addendum, path
  collision, same-lane WIP, and branch identity are confirmed. The immediately
  preceding real GLM-5.3 repair returned a patch at 2026-09-28 07:53:12 UTC,
  providing fresh exact-route success evidence; the approved Codex PreToolUse
  hook remains responsible for its single fresh CoinTH quota check before the
  next request. No separate quota smoke request or credential read is needed.
- Required next action: dispatch one durable Kilo child for GLM-5.3 MAX to
  implement only `tests/test_cointh_quota_pretool.py`, then harvest it and run
  that focused file plus the non-test scope/static/secret checks. No direct
  Kilo call, network request, user-global hook/config/trust edit, or other
  mutable path is authorized.

## Integrator shell-comment finding and bound repair — 2026-09-28

- Recovered and harvested test execution exec-mukyr4ps-tbb020dy / attempt-mukyr4z0-5vqayujm, exit 0, then collected it. Its runtime receipt has identityVerified=false, claimPresent=false, and no binding digest; treat its GLM narrative as advisory, not formal task evidence. The authorized test file exists in the exact #564 author worktree and was independently verified below.
- Integrator reran PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_cointh_quota_pretool.py -p no:cacheprovider -q: 22 passed, 0 failed. Python AST parsing and git diff --check also pass; scope remains the existing hook, WO checkpoint, and the single newly claimed test file.
- A bounded reproduction found another false positive: kilo run "task" # example: --model glm-5.3 currently returns true, even though the selector is only shell-comment text. This violates #564's explicit parsed-request boundary and could trigger the guard for a non-GLM invocation.
- Follow-up remains under the existing Issue #564 claim comment 5857716760, with exact mutation scope limited to scripts/codex_hooks/cointh_quota_pretool.py and tests/test_cointh_quota_pretool.py; no additional issue, owner, worktree, or WIP lane. The test must ensure a shell comment after a command is ignored while a real later newline-separated GLM command remains detected.
- GLM_OFFLOAD assessment for this bounded parser repair: ELIGIBLE for GLM-5.3 MAX. The approved PreToolUse hook supplies one fresh proxy-quota check immediately before the useful request; the real task request is the upstream observation, with no separate smoke probe. JEV is JEV_MODE_OFF; no advisory request is necessary for this deterministic parser case.
- Bound child identity: task WO-P1-564; claim reference Issue #564 comment 5857716760; repository aase7en/A-Wiki-Conductor; worktree /Users/aase7en/.codex/worktrees/cointh-quota-preflight/A-Wiki-Conductor-codex-supervisor; branch codex/wo-p1-564-cointh-quota-hook; dispatch HEAD b4d71a55957809c72fd577f7198262d5091fcb5f; model cointh-glm/glm-5.3 MAX; harness kilo-code-cli; device Aase7ens-MacBook-Pro.local; host darwin.
- Reserved execution/attempt: exec-wo564fix-eab4bdbd3abe / attempt-0002-eab4bdbd3abe. Binding digest: 8a83d8a01bc2b82284fa2027015ea0aeaca8f2422324d8bb40b37c9352fb12cd; canonical worktree digest: 1a760c7e52db4d6031f8a80fac022adf5540897d04748c46e72769c703418b82. Its writable scope excludes this work-order file.
- Accepted A-Faster markers stay unchanged: FANOUT_TARGET=0, UNUSED_SAFE_CAPACITY=1, AUTO_REFILL_REQUIRED=false. After child completion, harvest/collect, inspect only its two-path scope, independently rerun the focused suite and static checks, then continue the already-authorized candidate/CI/R3 review pipeline.

## Comment-aware matcher repair verified — 2026-09-28

- Recovered durable execution history before continuing: 178 executions total;
  no RUNNING/UNKNOWN work. All five current WO-P1-564 executions are terminal
  and harvested; the two bounded repair runs completed and the one obsolete
  review attempt is cancelled. No duplicate work was started.
- The latest exact candidate remains PR #565 at
  `b4d71a55957809c72fd577f7198262d5091fcb5f` on base
  `0f0a5f17b33e82516e39ff00f482887728810e87`; its hosted test and Ubuntu/macOS
  smoke checks pass. It remains open/draft with no GitHub review decision.
  The author branch remote still equals the local HEAD.
- The exact #564 addendum `5865895184` authorizes the offline test path
  `tests/test_cointh_quota_pretool.py`, focused verification, and same-branch
  commit/push after checks pass. Only the claimed hook, this work-order file,
  and that single added test file are changed; ignored pre-existing
  `scripts/codex_hooks/__pycache__/` is preserved.
- The second bound GLM repair `exec-wo564fix-eab4bdbd3abe` / attempt
  `attempt-0002-eab4bdbd3abe` completed, was harvested and collected with
  `identityVerified=true`, binding digest
  `8a83d8a01bc2b82284fa2027015ea0aeaca8f2422324d8bb40b37c9352fb12cd`,
  and output digest
  `fc03275103c4f5b15250f91732e24fe4fc451917eef0e7569d7145559f1926ae`.
  It added shell-comment-aware segment handling and four targeted cases; the
  output does not establish an exact quota delta. JEV remains OFF for this
  deterministic parser repair.
- Integrator verification on the current author worktree:
  `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_cointh_quota_pretool.py -p no:cacheprovider -q`
  reports 26 passed; `git diff --check` and AST parsing of the hook and test
  file pass. The changed-path allowlist matches the claim plus addendum.
- The earlier review P2 about newline-separated commands and the reproduced
  shell-comment false positive are both covered by the current matcher/tests.
  Do not reuse review evidence for SHA `b4d71a5`; the new candidate still needs
  exact-head hosted CI and an independent exact-SHA R3 review before GPT
  acceptance/merge. The user-authorized same-branch commit/push gate is now
  satisfied; retain draft status pending those gates.
- Accepted capacity markers remain unchanged:
  `FANOUT_TARGET=0`, `UNUSED_SAFE_CAPACITY=1`,
  `AUTO_REFILL_REQUIRED=false`.
