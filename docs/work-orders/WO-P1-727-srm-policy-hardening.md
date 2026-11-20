# WO-P1-727 SRM Tool-Policy Hardening

Identity schema: GITHUB_ISSUE_V1
Issue: #727
Parent: #725 (Serena retirement / SRM gap-closeout program).
Status: DOCS_BOOTSTRAP / IMPLEMENTATION_NOT_STARTED / R3 / EXECUTION_SUBSTRATE_ONLY.
Owner: Windows docs-lane executor (AUTHOR; not acceptance authority).
Claim: GAP-CLOSEOUT-727-728-DOCS-001 (explicit user assignment; four-doc scope).
Base: origin/main adf997e5d2eaa3411a6d348b110daa8e11fd56b1 (remote verified).
Worktree: `A:\GitHub\AWC-gapclose-gov`.
Branch: `docs/gap-closeout-727-728`.
Device: Windows, native local tool surface.

## Scope And Authority

Driving issue: [#727](https://github.com/aase7en/A-Wiki-Conductor/issues/727).
Implementation repository: `aase7en/SunDayRemoteMCP` (SRM). This authority-repo
lane only creates WO727/WO728 and updates CURRENT-WORK.md/handoff.md. Commit,
normal push and one docs PR are authorized; NO merge, source/runtime changes,
worker/process operations, config edits or protected-root mutation. The docs
lane is R0 capture of the assigned contract, not new security-policy authority.
The implementation is R3 and needs a separate SRM worktree/branch/exact-HEAD/
claim/scope binding plus integrator authority/failure-model framing before code.
The claim above reserves docs only, not SRM source or implementation ownership.

REUSE existing tool exposure policy, FMG guard and attribution-context pattern;
EXTEND the CallTool dispatch seam, not the policy authority. Scope is exactly:

1. Execution-time policy parity at `server.ts` CallTool entry using
   `isToolNameExposed`, including an explicit `track_ui_event` exemption decision.
2. ONE uniform dispatch wrapper so every tool case follows policy -> guard ->
   handler, including `start_process` and related process tools. Today only four
   FMG tools are hand-wrapped; do not mistake FMG for a general process guard.
3. `AsyncLocalStorage` per-request remote attribution, mirroring the existing
   `uiOriginCallContext` pattern instead of shared mutable request flags.

## Frozen Contract And Failure Model

The [implementation seam map](https://github.com/aase7en/A-Wiki-Conductor/issues/727#issuecomment-6678698398)
is the implementation map, researched at SRM `e44c48f` on 2026-11-06. All anchors
below are SRM-relative historical anchors, NOT a current-head verification.
The implementer MUST re-verify paths/lines/call graph at their exact head and
record drift before mutation; the repo may have advanced beyond `e44c48f`.

| Item | Existing seam / historical anchors | Required bounded change |
|---|---|---|
| Execution policy | `src/server.ts:1245-1247` ListTools; `:1279` CallTool params; `src/sunday/tool-policy.ts:5-42`, `:33-36` exposure predicate | Enforce the same predicate immediately after params destructure, before telemetry or UI early branches; refusal shape matches unknown tool (`server.ts:1548-1552`) without revealing hidden-vs-unknown |
| Dispatch / FMG | `src/sunday/fmg/pipeline.ts:469-491`; `src/sunday/fmg/plan.ts:15,61-62`; four wrappers at `src/server.ts:1500,1508,1516,1540` | Every switch case and `sunday_*` fallback traverses one wrapper; delegate to `guardToolCall` only for its four supported FMG tools, preserving byte-compatible passthrough (`pipeline.ts:460-467`) elsewhere |
| Process path | `src/server.ts:1459-1486` -> `src/handlers/terminal-handlers.ts:22-25` -> `src/tools/improved-process-tools.ts:98,120`; `src/command-manager.ts:229-247` | Process paths traverse the uniform seam before handler; retain command blocklist and existing restrictions, without pretending FMG has gained process authorization |
| Remote attribution | `src/server.ts:152,158-175,284,1293-1315,1696-1711`; `src/utils/capture.ts:335,426-430,496-515` | Wrap request handling in ALS; capture reads request-local store; interleaved calls and asynchronous telemetry must not borrow another request's identity |
| Reused ALS / marker | `src/utils/capture.ts:8-22` uiOriginCallContext; `src/remote-device/desktop-commander-integration.ts:227-231` remote metadata | Mirror the context mechanism; preserve module-level fallback only for non-request Initialize/opt-out events, never as a concurrent-request authority |

Hidden/disallowed direct calls fail closed BEFORE guard/handler effects. Full
mode and existing exposed tools retain their policy semantics. `track_ui_event`
is not in the compact allowlist (`server.ts:1434-1444`): the integrator must pin
and test a narrow UI-origin exemption or an explicit no-exemption compatibility
decision before implementation. Do not exempt every UI-origin call or broaden
the allowlist to work around this case. Client-supplied metadata is attribution,
not permission. ALS changes attribution only, never policy semantics.

Adjacent findings ONLY / OUT OF SCOPE: `node:local` execution via
`interact_with_process` (`improved-process-tools.ts:27-92,131-133`),
`get_recent_tool_calls` history/argument exposure (`server.ts:1422-1432,1564`),
and `write_pdf` guardability (`server.ts:1503-1505`). General execution-policy
parity still covers these names; do not add sandbox/history-redaction/PDF-guard
features in this WO. The separate Initialize `currentClient` race is also an
adjacent finding, not permission to broaden request-attribution scope.

## Acceptance And Verification

Issue #727 checklist (retained verbatim):

- [ ] Calling a policy-hidden tool directly returns a policy refusal (test-proven)
- [ ] Process tools pass the guard (test-proven); no remaining guard bypass paths in audit
- [ ] Attribution correct under simulated concurrency (test-proven)
- [ ] CI green on the exact reviewed head; independent review PASS; post-main CI verified
- [ ] Evidence checkpoint on this issue

Additional required proof:

- [ ] Failing-test-first for every behavior change; record RED then GREEN evidence.
- [ ] Direct CallTool parity probe refuses EVERY non-exposed tool name, with zero handler effects; ListTools filtering alone is not proof (list != call probe).
- [ ] All dispatch cases, process tools and `sunday_*` fallback traverse policy -> guard -> handler once; unsupported FMG tools retain passthrough, not a fabricated process-policy verdict.
- [ ] Explicit `track_ui_event` decision and compact/full/UI-origin regression rows; no hidden-vs-unknown information leak, no weakening of existing policies.
- [ ] Concurrent local/remote calls, failures and deferred telemetry retain correct per-request attribution; non-request Initialize/opt-out emission remains supported.
- [ ] Independent exact-SHA review PASS from a fresh reviewer session, NOT the implementer, before merge; focused re-review after behavior/guard repairs.

Use SRM's existing runner/patterns: `test/test-sunday-tool-policy.js`,
`test/test-fmg-guard.js`, `test/test-blocked-commands.js` and
`test/test-blocklist-bypass.js`, with injected hooks and isolated temporary
fixtures. Re-verify runner commands at implementation head: the map records
auto-discovered `test/test*.js`, imports from `../dist`, `npm run build` before
`npm test`. Record exact commands/counts, regression/audit results, UTF-8/no BOM,
diff/secret/scope checks; no production process effects for fixture testing.

SRM delivery sequence: freeze exact candidate -> fresh independent review PASS
on that head -> green CI run ID on that SAME head -> integrator merges expected
head only -> post-main CI run ID on exact merge -> evidence checkpoint on #727.
Record SRM PR URL, reviewed SHA/reviewer evidence, candidate CI ID, merge SHA,
post-main CI ID and residuals on #727; fold accepted status to this authority WO.
Any head drift requires re-pin and focused review/CI as applicable. This docs PR
does not satisfy implementation review/CI or authorize its own merge.

## Checkpoint

2026-11-06: clean assigned docs worktree/branch/base and authoritative remote
verified; full #727 body and seam-map comment read, together with WO716/WO724
format precedents. Four-doc claim is disjoint from later SRM source lanes.
GLM_OFFLOAD=NOT_BENEFICIAL for this already-delegated docs capture: fixed supplied
contract and deterministic identity/diff checks; no further inference dispatch.
No SRM code/runtime/process state was changed or independently re-audited.
Implementation RED/GREEN, independent review, candidate CI, merge and post-main
gates are NOT_RUN. Docs verification evidence and exact docs candidate are
recorded in the docs PR; no self-referential SHA embedded here.

Docs verification: canonical identity suite 33 passed in 6.59s (includes both
new WOs); strict UTF-8/no BOM, added local links and bounded added-line secret-
shape scan passed. Initial Node validator invocation failed only from PowerShell
quote stripping (`SyntaxError: missing ) after argument list`); corrected quoting
passed, with no file writes. Git reports LF-to-CRLF normalization warnings when
staging the four docs; staged diff-check passed. No product suite or independent
review is claimed.

Next safe action: orchestrator reviews the docs candidate; separately bind the
SRM R3 implementation lane, re-verify the map, and settle the narrow UI exemption
decision before failing-test-first code. No merge by this lane.
