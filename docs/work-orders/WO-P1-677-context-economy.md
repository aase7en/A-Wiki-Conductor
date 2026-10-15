# WO-P1-677 — Cross-project Agent Context Economy, First Slice
Authority: https://github.com/aase7en/A-Wiki-Conductor/issues/677
Claim: issue comment 6197697952; scope refinement 6197739514.
User goal: reduce repeated reads, tool-output inflation and token use across projects without changing SSoT/ownership safety.

## Binding
- CROSS_REPO, R2 shared read/agent instruction policy; control A-Wiki-Conductor, execution SunDayRemoteMCP.
- AWC: A:\GitHub\_worktrees\A-Wiki-Conductor-wo677-context, branch chore/wo677-context-economy-awc, base 46faaebce16d9d86b7a14c70fa05e52906b61d9d.
- SRM: A:\GitHub\_worktrees\SunDayRemoteMCP-wo677-context, branch chore/wo677-context-economy-srm, base a105986e1b40adadee730cf8486fa567cf6404d8.
- Owned AWC paths: .kilocodeignore, .cursorignore, docs/runbooks/agent-context-economy.md, this WO, narrow AGENTS.md link, tests/test_agent_context_economy_config.py.
- Owned SRM paths: .kilocodeignore, .cursorignore. All other files forbidden; no source/runtime edits, global config, secret, cleanup or merge.
- Protected canonical roots preserved. No worktree changes shared with existing Issue #541 lossless MCP read or Issue #327 router.

## Verification/acceptance
1. Official Kilo/Cursor pattern syntax and correct filenames confirmed. Tests prove ignores exclude representative heavy files but do not exclude entry, graph, current work, Work Orders, source/tests or result receipts.
2. Bound read plan supports exact-range evidence retrieval, no lossy masking or skip of mandatory checks.
3. Per repo git diff --check, UTF-8, no accidental artifact/secret; deterministic tests. Independent R2 exact-SHA review + CI if required before merge.
4. No invented savings. Record input/cache tokens only if model provider supplies actual values.
5. Other project adoption is documented only, pending their per-repo safe mutation gate.

## Checkpoint/stop
Until acceptance, state remains CANDIDATE / REVIEW_REQUIRED, not COMPLETE. Never mutate either protected root; stop on HEAD drift, claim conflict or unknown state. Persist PR/sha/test pointer in this issue. Do not self-merge.
