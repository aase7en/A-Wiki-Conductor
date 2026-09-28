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
