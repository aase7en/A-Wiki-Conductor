# WO-P1-545 — Codex NightShift lifecycle hooks

Status: ACTIVE / AUTHORING / RED-GREEN COMPLETE
Issue: #545
Topology: CONTROL_PLANE_ONLY
Risk: R3 lifecycle/routing enforcement
Claim: WO-P1-545-CODEX-NIGHTSHIFT-HOOKS-MAC-001
Repo: A-Wiki-Conductor
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo545-codex-nightshift-hooks
Branch: feat/wo-p1-545-codex-nightshift-hooks
Original base: 85b02d9f9f200aedfa22417c9b4c61ac363f40cb
Composed current main: 0795e92798b03d86def63f2298b9a16924037964 (#537 post-main)

## Goal

Make a Codex Goal/Luna supervisor reliably re-enter the accepted A-Sunday
workflow after startup, resume, prompt submission and compaction, and continue a
nonterminal NightShift parent from an accepted #531 turn receipt without creating
a second scheduler, claim/lease system, quota authority, review authority, or
completion authority.

The adapter keeps heavy labor GLM-first, uses Flash for bounded read-only work,
keeps JEV inside its accepted semantic-decision mode, and allows an already-
authorized Codex executor fallback while a proven GLM provider route is blocked.

## Authority and predecessors

- A-FastTask remains router/binder authority.
- A-Faster owns utilization/refill semantics; #517 and #537 are reused.
- A-NightShift owns parent continuation/wait/terminal semantics; #529/#522 reused.
- #530 owns hierarchical Kilo/GLM child routing and exact sunday_dispatch transport.
- #531 owns the same-thread turn receipt/resume contract; v1 schema is unchanged.
- #535 owns CLI/provider transport hardening.
- #498 executable mutation guard is a protected sibling and is not imported or changed.
- #509 JEV-5 is a protected sibling; this WO never promotes JEV mode.

## Hook shape

Project-local .codex/hooks.json registers:

- SessionStart — startup/resume/clear/compact policy reinjection;
- UserPromptSubmit — tasking reminder without rewriting the user prompt;
- PreCompact/PostCompact — stateless continuation boundary only;
- PreToolUse — deny recognized direct kilo run bypass and annotate canonical Sunday dispatch;
- PostToolUse — re-inject harvest/dedupe/refill rules after Sunday execution tools;
- Interrupt — preserve the invariant that parent-turn interruption does not imply durable child cancellation;
- Stop — consume one accepted #531 turn-receipt pointer and continue once when actionable.

Every command handler has a Windows-specific `commandWindows` launcher in addition to the POSIX command. Both resolve the Git toplevel at execution time; no operator-specific repo path is embedded.

All hooks use one stdlib-only read-only script. Hooks write no state and make no
network, Git, provider, quota, process or secret calls.

## Stop continuation contract

The final assistant message may carry exactly one bounded pointer:

A_SUNDAY_TURN_RECEIPT_REF=<absolute temp receipt path>

The hook validates the existing #531 receipt shape, temp-root confinement,
schema version, generation type, receipt identity, status and stop gate.
CONTINUE + stop_gate=NONE continues the same parent after fresh recovery,
except known unchanged-wait reasons which stop the model turn to preserve the
#520 no-model-spin contract. stop_hook_active=true always prevents a second
continuation in the same turn. Missing/malformed/terminal/real-stop receipts
fail closed by allowing the turn to end; no state is guessed.

## GLM/Codex fallback

GLM-5.3 MAX remains the preferred R2/R3 heavy executor. GLM-5.3-Flash remains
bounded read-only assistance. JEV remains advisory/accepted-mode evidence only.

A fresh provider-scoped GLM five-hour exhaustion may classify
GLM_ROUTE_BLOCKED; it is not parent quota exhaustion while an accepted Codex
fallback exists. A-Faster now describes a bounded executor fallback: Luna at
max effort for well-scoped high-volume implementation, Sol for complex repair/
integration/acceptance-bound work, and Astra only for exceptional escalation.
Every route inherits the same claim/WIP/scope/review/verification authority.

If all accepted Codex execution capacity is also exhausted, NightShift may
checkpoint and become quota-terminal only after children are reconciled and no
accepted fallback/recheck route remains. Model identity never grants authority.

## GLM author admission attempt

Before implementation, the required fresh CoinTH/GLM preflight was attempted
through the approved secret-safe boundary. The execution surface blocked the
resolver/probe command before it ran. No secret was read or exposed and no fresh
quota tuple was produced.

Classification:

- PROXY_QUOTA_STATE=UNKNOWN
- UPSTREAM_PROVIDER_READINESS=UNKNOWN
- GLM_ROUTE_READY=FALSE
- blocker PREFLIGHT_EXECUTION_BLOCKED

Therefore no GLM author dispatch was made. The bounded Codex/Sol fallback
continued the already-admitted #545 lane, and the typed blocker was folded to
Issue #545 rather than inferred from another lane's quota evidence.

## RED / GREEN

RED before production edits: 13 failed, 103 passed. The failures were exactly the new hook/fallback semantics; prior controls stayed green.

Current GREEN after Windows hook support, strict #531 receipt validation, Interrupt semantics, JEV System-One advisory, device-capacity projection, and background liveness projection: **122 passed**.

Focused command:
`python3 -m pytest -q tests/test_codex_a_sunday_hooks.py tests/test_a_faster_invocation_contract.py tests/test_a_nightshift_skill_contract.py`

Static compatibility gates also pass:
- `python3 -m py_compile .codex/hooks/a_sunday_lifecycle.py`
- `python3 -m json.tool .codex/hooks.json`
- `git diff --check`

## Legacy A-Wiki Codex hook collision audit

Windows inspection proved the older A-Wiki project hook set has previously been trusted by Codex: the user-level Codex config contains trusted hashes for handlers from `A:\\GitHub\\A-Wiki\\.codex\\hooks.json`.

Two legacy A-Wiki behaviors are explicitly **incompatible with A-Conductor** and must never be copied into this project:
- SessionStart `session-start-git-pull.sh` switches to `main` and performs fetch/pull-rebase;
- Stop `stop-auto-commit.sh` stages/commits and pushes `main`.

A-Conductor requires exact claimed worktree/branch/HEAD ownership and expected-head fan-in. Therefore #545 uses a separate project-local hook set and performs no Git mutation. This WO does not delete the A-Wiki hooks: they remain A-Wiki-local policy and require a separate migration claim if that project is modernized.

Official Codex hook capability was rechecked for this slice: SessionStart/UserPromptSubmit/PreCompact/PostCompact/PreToolUse/PostToolUse/Interrupt/Stop are supported lifecycle events; repo hooks should resolve from the Git root; PreToolUse can deny Bash/MCP/local-tool calls; Stop blocking continues the turn and `stop_hook_active` prevents a continuation loop; Windows handlers use the supported Windows-specific command override.

## A-Faster / NightShift refinements

- JEV is treated as a System-One advisory fast path for condition checks, evidence/relevance scoring, routing suggestions, guardrails and confidence only when the currently accepted JEV mode permits it. It remains non-authoritative.
- Windows `SunDay-Worker 1..5` plus `SundayMCP Mac` are discovered as execution-capacity surfaces. ONLINE never grants mutation admission or multiplies WIP by itself.
- long-running children expose `BACKGROUND_LIVENESS_PULSE` from durable state so Mission Control/transport can show state, elapsed time, last activity, output size and next action without spinning a model turn.
- parent Stop/Interrupt/closed Codex UI never implies separately supervised durable children were cancelled.

## Provider-neutral SundayFamily follow-up

Issue #340 is the existing canonical PNX roadmap. A durable extension now records SELF-HOOK runtime, ordinary Chat/browser/Gemini bridge adapters, device-capacity projection, subscription-capacity failover, host conformance and operator liveness. #545 implements only the thin Codex adapter; it does not create the future SundayFamily event bus or browser bridge.

## Exact mutation scope

- .codex/hooks.json
- .codex/hooks/a_sunday_lifecycle.py
- tests/test_codex_a_sunday_hooks.py
- .agents/skills/a-faster/SKILL.md
- .agents/skills/a-nightshift/SKILL.md
- .agents/skills/a-nightshift/references/overnight-supervisor.md
- tests/test_a_faster_invocation_contract.py
- tests/test_a_nightshift_skill_contract.py
- this work order

No #498/#537/#509 path is in scope. No scheduler/task/job/claim/lease/provider
store or SunDayRemoteMCP source is modified.

## R3 review repair checkpoint

Independent structural review of candidate `4467b8acd05c6ab480e5bf2d096abc7908ea9616`
returned CHANGES_REQUIRED with P0=0, P1=1, P2=3:

- P1: no deterministic end-to-end `A_SUNDAY_TURN_RECEIPT_REF` emission contract;
- P2: Stop continued non-actionable/terminal reasons;
- P2: hook validation did not fully mirror the closed bounded #531 v1 receipt shape;
- P2: direct-Kilo bypass missed quoted/absolute Windows paths.

Repair is RED/GREEN within the existing #545 claim and scope. The supervisor
contract now materializes exactly one `turn-receipt.json` under the existing
ephemeral run authority for actionable CONTINUE turns and emits exactly one
final `A_SUNDAY_TURN_RECEIPT_REF=<absolute path>` marker. The Stop hook
continues only NEXT_READY / CHILD_RESULT_READY / TURN_BUDGET_BOUNDARY, mirrors
the closed/bounded #531 v1 constraints in stdlib-only validation, and the Kilo
guard covers quoted/unquoted Windows and POSIX paths.

Post-repair related verification: **302 passed** plus py_compile, JSON parse and
`git diff --check` PASS. The old candidate is superseded and must not be
accepted; a new exact SHA requires fresh hosted CI and independent rereview.

## Second review hardening checkpoint

The exact-SHA rereview of `1be73f08f5af8c7a7ca5e92f1b41550abdf5045d` was read-only and produced actionable deterministic evidence before its stalled process was cancelled by exact Sunday execution id and harvested. No final PASS verdict was claimed for that superseded SHA.

Confirmed defects and repairs:
- #531 `run_id` length: schema maxLength is 128; the hook now rejects values above 128 instead of relying only on the regex.
- malformed `outstanding_exec_refs`: element type/pattern validation now occurs before uniqueness/set evaluation, so JSON objects/lists fail closed rather than raising TypeError.
- Windows npm/shim Kilo routes: direct-run bypass detection now covers `kilo`, `kilo.exe`, `kilo.cmd`, and `kilo.bat` for quoted/unquoted Windows and POSIX paths.
- receipt materialization is fail-closed on the complete recovered #531 identity tuple. Unknown/stale/incompatible identity, including a `max` supervisor effort that v1 cannot encode, yields `RESUME_RECEIPT_IDENTITY_UNAVAILABLE` and forbids the pointer marker instead of synthesizing resume state.

Targeted RED/GREEN regressions were added before the corresponding repairs. The prior SHA and its successful hosted CI are superseded and cannot be used as final acceptance evidence.

## Final R3 review repair checkpoint

Two independently harvested read-only reviews of candidate `3748b9ff146d8b1ccc03edb8806d209ce490cdbd`
found one P1 and one P2 defect. The candidate and its green hosted CI are therefore
superseded and are not acceptance evidence:

- P1: Stop accepted any otherwise-valid receipt below the temp root instead of
  requiring the canonical `turn-receipt.json` inside the directory whose name
  matches the receipt `run_id`.
- P2: malformed JSON enum values for `status`, `effort`, `reason`, or
  `stop_gate` could reach Python set-membership before type validation and raise
  `TypeError`.

The repair remains within the existing #545 hook/test scope. The receipt loader now
fails closed unless the resolved file is exactly `<temp>/<run_id>/turn-receipt.json`,
and every enum field is proven to be a string before membership validation. Focused
regressions cover wrong run directory, wrong receipt filename, and list/object enum
values. Post-repair related verification is **337 passed** plus py_compile, hook JSON
parse, and `git diff --check` PASS. A fresh exact SHA still requires new independent
review and hosted CI.

## Remaining acceptance gates

Before acceptance:

1. focused and related tests plus hook schema/static checks;
2. strict UTF-8, git diff --check, exact-scope and added-line secret scan;
3. freeze exact candidate SHA;
4. independent R3 exact-SHA review after the shared review slot is free;
5. exact-head hosted CI;
6. Sol expected-head acceptance/merge and post-main verification.

Project hooks are unmanaged Codex hooks: the operator must review/trust the
current project hook definition before Codex executes it. Trust is deployment
consent only and grants no A-Sunday mutation/task authority.
