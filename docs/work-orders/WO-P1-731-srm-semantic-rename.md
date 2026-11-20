# WO-P1-731 SRM Project-Wide Semantic Rename (Track B admitted, fail-closed)

Identity schema: GITHUB_ISSUE_V1
Issue: #731
Parent: #728 lineage (semantic toolset), #725 program.
Status: DOCS_BOOTSTRAP / R2 (mutation surface, gated) / EXECUTION_SUBSTRATE_ONLY.
Base: origin/main 48b3ef614ff29da2de85a27fbda3e2b84613c734 (verify live before use).
Branch: docs/wo-731-rename-gate. Device: Windows.

## Authority

Driving issue [#731](https://github.com/aase7en/A-Wiki-Conductor/issues/731)
carries the user gate decision (2026-11-06): Track B / CUTOVER-MUTATE admitted
for RENAME ONLY. Implementation repo: aase7en/SunDayRemoteMCP, SRM PR gates
(exact reviewed head -> CI -> merge -> post-main -> deploy verify). No other
semantic mutation is admitted; default runtime behavior stays read-only.

## Frozen contract

| Seam | Anchor (researched at SRM 2632fb2; RE-VERIFY at lane head) | Bounded change |
|---|---|---|
| Registration | `src/sunday/mcp-semantic-tools.ts` (schemas record + definitions + dispatch), `test-sunday-semantic-mcp-tools.js` no-mutation assertion | `sunday_semantic_rename` registered ONLY under `SUNDAY_SEMANTIC_MUTATION=1`; default-mode assertion unchanged + new flagged-mode assertions |
| Engine mutation | `src/sunday/semantic/engine.ts` renameSymbol L1334, `#guardedEdit` L1178 (PRE/MID/POST probes) | Route rename through guardedEdit; all-or-nothing; typed EAMBIGUOUS/ENOTFOUND/DRIFT refusals before any write |
| File editor | `src/sunday/semantic/providers/typescript.ts` replaceRange L695 (proper-lockfile, verify-then-write, atomic tmp+rename) | Extract/port as shared editor seam; Python applies pyright `workspace/edit` through it; TS applies refs-driven per-file edits through it |
| Python provider | `src/sunday/semantic/providers/python-lsp.ts` (+ LSP client `lsp/client.ts`) | Add `textDocument/rename` + `workspace/edit` handling; sha256 re-verify post-edit; membership-drift validation still applies |
| Policy | `src/sunday/tool-policy.ts` (`sunday_` prefix exposure) + #42 execution-time parity | Rename visible only in flagged builds; parity enforcement automatically covers it (name starts with `sunday_`) |

## Acceptance / verification

Copy from issue #731 checklist. Mandatory: default-mode non-registration test;
flagged-mode end-to-end on a_conductor (Python) + SRM itself (TS); atomicity
test (simulated mid-failure leaves zero writes); independent review PASS on
exact head; post-main Codespell; deployed-runtime probe with flag OFF (tool
absent) then a local flagged probe (tool works). Deploy leaves flag OFF on both
runtimes; activation is a separate user decision.

## Out of scope

Replace/insert/delete symbol mutations, any policy weakening, FMG changes,
activation of the flag on any runtime, ChatGPT connector changes.
