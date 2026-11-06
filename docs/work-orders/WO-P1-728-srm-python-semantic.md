# WO-P1-728 SRM Read-Only Python Semantic Tools

Identity schema: GITHUB_ISSUE_V1
Issue: #728
Parent: #725 (Serena retirement / SRM gap-closeout program).
Status: DOCS_BOOTSTRAP / IMPLEMENTATION_NOT_STARTED / R3 / EXECUTION_SUBSTRATE_ONLY.
Owner: Windows docs-lane executor (AUTHOR; not acceptance authority).
Claim: GAP-CLOSEOUT-727-728-DOCS-001 (explicit user assignment; four-doc scope).
Base: origin/main adf997e5d2eaa3411a6d348b110daa8e11fd56b1 (remote verified).
Worktree: `A:\GitHub\AWC-gapclose-gov`.
Branch: `docs/gap-closeout-727-728`.
Device: Windows, native local tool surface.

## Scope And Authority

Driving issue: [#728](https://github.com/aase7en/A-Wiki-Conductor/issues/728).
Implementation repository: `aase7en/SunDayRemoteMCP` (SRM). This authority-repo
lane only creates WO727/WO728 and updates CURRENT-WORK.md/handoff.md. Commit,
normal push and one docs PR are authorized; NO merge, source/runtime/config
changes, worker operations or protected-root mutation. R0 docs capture only;
the future subprocess/lifecycle implementation is R3 and needs its own exact
SRM repo/worktree/branch/HEAD/claim/scope and integrator framing before mutation.
The docs claim is not an SRM source claim. Retain one owner per mutable hotspot
when #727 and #728 implementation scopes are assigned.

The [scope refinement / implementation map](https://github.com/aase7en/A-Wiki-Conductor/issues/728#issuecomment-6678698817)
narrows the issue body's original defs/refs/rename wording: v1 is READ-ONLY
Python definitions, references and `documentSymbol` navigation. NO editor seam,
NO mutation tools. Track B / `CUTOVER-MUTATE` canonical admission remains gated.
Project-wide rename is a separate future slice plus admission/gate decision;
neither Python nor TS rename is activated by this WO. v1 completion must not
be reported as original rename acceptance or full retirement capability proof.

Working-set-only languages: Python now; preserve existing TS/JS support. No
Serena 40+ language replication, memory store, REPL UX, SSH bridge or in-memory
execution feature work. REUSE language-neutral engine/contracts, routed adapter,
session cache and registration path; EXTEND with one Python provider adapter.

## Frozen Contract And Failure Model

The map was researched at SRM `e44c48f` on 2026-11-06. Paths/lines below are
historical implementation guidance, not fresh source verification. Re-verify
all anchors and actual contracts at the implementation head; record drift.

| Seam | Existing contract / historical anchors | Bounded v1 change |
|---|---|---|
| Neutral semantic contract | `src/sunday/semantic/types.ts:15-51,154-164,235-245`; `engine.ts:72-133,533` | New `PythonSemanticAdapter` at `src/sunday/semantic/providers/python-lsp.ts`, using context/provider/reader seams only; do NOT wire `SemanticFileEditor` |
| Existing provider | `src/sunday/semantic/providers/typescript.ts` | Preserve in-process TypeScript language service; it is NOT an LSP client |
| LSP plumbing | Proposed `src/sunday/semantic/lsp/client.ts` and `protocol.ts` | Minimal stdio JSON-RPC client for `pyright-langserver`: initialize handshake, request/response correlation, bounded failure handling; defs/refs/documentSymbol only |
| File dispatch | `src/sunday/mcp-semantic-tools.ts:200,323-439` | Replace hardcoded `.ts` gate in `resolveFileContext` with extension -> provider registry, routing TS/JS as currently supported and `.py` to Python; preserve typed unsupported-language refusal |
| Cache | `src/sunday/mcp-semantic-tools.ts:237-314` | Reuse existing provider-agnostic LRU 8 / TTL 10-minute, content-hash-validated session cache; disposal owns Python server lifetime |
| Dependency / host precedent | Lazy `typescript` devDependency with `SEMANTIC_PROVIDER_UNAVAILABLE`; `src/utils/system-info.ts:465-490` Python detection | Lazy import/resolution for optional pyright, mirror typed unavailable behavior; no eager hard runtime dependency or missing-host spawn-and-hang |
| MCP boundary | `src/sunday/mcp-semantic-tools.ts:6-8,93-105,878-951`; `src/sunday/mcp-tools.ts:69-77,167-168` | Preserve no-mutation registration; language-aware CTS-style bounded descriptions and existing schemas/handler/definition wiring |

Use `pyright-langserver` over stdio, one server per semantic session, not a new
global daemon. Bind `serverId` to spawn identity and increment `generation` on
restart. Launch hidden on Windows (`windowsHide`); own exact child handles/PIDs
and command identity. Idle shutdown, cache TTL/LRU disposal and kill-on-exit must
clean owned children; never broad-kill Python, Node, pyright or worker processes.
Initialization/crash/timeout/missing-dependency paths return bounded typed failure
without hanging or silently selecting a different language/provider.

Mirror the TypeScript devDependency precedent: lazy import/provider setup;
absent Python/pyright yields `SEMANTIC_PROVIDER_UNAVAILABLE`, not runtime install
or an unhandled module error. Resolve unsupported-extension errors through the
existing typed surface (`SEMANTIC_UNSUPPORTED_LANGUAGE` reserved in `errors.ts:17`;
map mentions outer `EUNSUPPORTED`); verify the actual boundary before choosing
the exact response, do not invent a second error vocabulary. Call hierarchy is
optional; leave `callees` unimplemented v1, retaining typed
`SEMANTIC_CAPABILITY_MISSING` negotiation (`engine.ts:82-91`).

Mutation engine operations at `engine.ts:1280-1334` do not grant MCP mutation
authority. Preserve the negative registration assertion at
`test/test-sunday-semantic-mcp-tools.js:98-102`. A future rename slice needs
Track B authorized-transition + atomic-write admission for the Python provider.
No direct write or editor shortcut may bypass that gate.

Registration reuses `sunday_*` exposure (`tool-policy.ts:33-36`) and the uniform
policy/guard dispatch pattern governed by #727; do not broaden policy to enable
Python. Coordinate/rebase shared SRM hotspots through the integrator, never
overwrite the other lane. `mcpb-bundle/manifest.json` must stay synchronized;
prove it with `npm run validate:tools` at the candidate head.

## Acceptance And Verification

Issue #728 checklist is applied with the posted read-only v1 refinement, not
the superseded rename requirement:

- [ ] Python definitions, references and documentSymbol navigation operate through SRM on real Python fixtures and a read-only `a_conductor` working-set probe; record tested repo/head and bounded results, never mutate it.
- [ ] New/changed tools follow existing registration/policy/guard patterns and CTS-3-style descriptions; existing TS/JS behavior remains supported.
- [ ] No editor seam or mutation tools registered; Track B / CUTOVER-MUTATE holds, project-wide rename explicitly remains a separate gated follow-up.
- [ ] Failing-test-first behavior changes; new tests plus relevant existing suites green, with exact commands/counts and missing-host rows reported honestly.
- [ ] Lazy optional dependency failure is typed SEMANTIC_PROVIDER_UNAVAILABLE; unsupported extension and missing optional capability remain typed, no hang or silent fallback.
- [ ] Session cache reuse and hash invalidation proven; idle/TTL/LRU disposal, restart generation and kill-on-exit clean only owned subprocesses, including failure paths.
- [ ] `npm run validate:tools` passes with mcpb-bundle manifest sync checked.
- [ ] CI green on exact reviewed head; independent review PASS from a fresh session, NOT the implementer, before merge; post-main CI verified.
- [ ] Evidence checkpoint on #728 states read-only v1 delivered, rename deferred, and the exact remaining #725 retirement gates; no automatic full Stage-3 acceptance.

Follow temp-git-repo fixture patterns from
`test/test-sunday-semantic-mcp-tools.js:26-56,368-380` in new
`test/test-sunday-semantic-python-*.js`. Hosts missing Python/pyright must have
typed-fail/explicit skip rows, like the existing symlink skip precedent at
`:254-260`; skips are not successful real-provider proof. Provider-present
evidence is still required for defs/refs/documentSymbol acceptance. Include
isolated protocol/lifecycle failure tests and no-mutation assertions. Tests
import `../dist`; re-verify commands, then `npm run build` before `npm test`,
plus `npm run validate:tools`, UTF-8/no BOM, diff/secret/exact-scope checks.

SRM delivery sequence: freeze exact candidate -> fresh independent review PASS
on that head -> green CI run ID on that SAME head -> integrator merges expected
head only -> post-main CI run ID on exact merge -> evidence checkpoint on #728.
Record SRM PR URL, reviewed SHA/reviewer evidence, candidate CI ID, merge SHA,
post-main CI ID, dependency-present/absent results and residuals on #728; fold
accepted status to this authority WO. Head drift requires re-pin and focused
review/CI as applicable. This docs PR does not pass any implementation gate.

## Checkpoint

2026-11-06: full #728 body and scope-refinement comment read; WO716/WO724 format
and clean assigned docs worktree/base/remote verified. Original issue rename
wording is deliberately narrowed, not silently marked complete. No SRM code,
Python/pyright installation, subprocess or protected-root changes performed.
GLM_OFFLOAD=NOT_BENEFICIAL for already-delegated fixed-contract docs capture
and deterministic checks; no further provider dispatch. Implementation/tests,
real-provider probe, independent review, CI, merge and post-main are NOT_RUN.
Docs verification and exact candidate are recorded in the docs PR.

Docs verification: canonical identity suite 33 passed in 6.59s, including this
new WO and WO727; strict UTF-8/no BOM, added local links and bounded added-line
secret-shape scan passed. Initial validator shell-quoting failure and successful
corrected run are recorded in WO727. Staged diff-check passed; Git produced
LF-to-CRLF normalization warnings. No implementation test pass is claimed.

Next safe action: orchestrator reviews the docs candidate, then binds a separate
SRM implementation lane and re-verifies provider/registry/lifecycle anchors;
retain read-only scope and the independent mutation gate. No merge by this lane.
