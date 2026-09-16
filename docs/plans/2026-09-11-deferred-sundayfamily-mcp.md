# Deferred roadmap — SundayFamily MCP capability and stability evolution

Date: 2026-09-11
Status: DEFERRED / LATE ROADMAP / NOT READY FOR IMPLEMENTATION
Capture: [WO-P1-189](../work-orders/WO-P1-189-zero-relay-priority-capture.md)
Priority authority: explicit user instruction to finish the no-human-relay path first.

## Current focus

Finish the existing [Zero-Relay Accelerator](2026-09-04-zero-relay-accelerator-roadmap.md):
the user states a goal once; eligible GPT/integrator, GLM/ZCode, and Codex execution
surfaces exchange task packets, exact results, review findings, and bounded repairs
without the user repeatedly copying prompts/results or typing `continue` between them.
Use existing capability/authorization/ownership routing; not every task must visit
every model or platform. An unavailable Codex/provider surface is not an invented
automatic route, and a published packet is not evidence of dispatch or execution.

The existing dependency sequence remains ZRA-1 accepted proof -> ZRA-2 automatic
verify/review/repair -> ZRA-3 accepted NEXT READY continuation -> ZRA-4 bounded
parallelism -> ZRA-5/ODP integration when its own prerequisites are satisfied.
Reuse the [cost-first delivery workflow](../runbooks/cost-first-delivery.md).
Necessary security, ownership, recovery, and release fixes remain in the active path;
deferring future stability enhancements does not defer a current blocking defect.

## Late-roadmap backlog

| Candidate | Purpose | Evidence before adoption |
|---|---|---|
| SundayFamily MCP branding and packaging | Our product identity with Serena attribution and complete third-party notices | Clear packaging scope, license review, and no implied ownership of upstream code |
| Lower RAM/CPU per active workload | Avoid duplicate indexing/watchers, bound caches, and evaluate demand-loaded engines | Same-workload Windows/macOS measurements including child processes, cold/warm latency, and tool correctness |
| Multi-folder and multi-client ergonomics | Reuse file access and safe project-specific semantic engines | Worktree/project isolation, concurrent edit safety, and no cross-project stale results |
| Hybrid tool selection | Compare file/grep tools, ast-grep, and Serena/LSP for each task | Capability parity for required operations; exact tool failures stay visible |
| Alternative engine evaluation | Reassess mcp-language-server, codebase-memory-mcp, Locus, Codanna, and cclsp | Pinned upstream/license/platform evidence and local benchmark; no blanket performance claim |
| Later reliability/transport refinement | Improve reconnect, headless operation, and optional RDC/SSH adapters where a proven gap remains | Reuse existing recovery authority; no duplicate restart/task/retry controller or blind task replay |

Research leads, not approved dependencies:
[Serena](https://github.com/oraios/serena),
[mcp-language-server](https://github.com/isaacphi/mcp-language-server),
[ast-grep MCP](https://github.com/ast-grep/ast-grep-mcp),
[codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp),
[Locus](https://github.com/paladini/locus-mcp),
[Codanna](https://github.com/bartolli/codanna), and
[cclsp](https://github.com/ktnyt/cclsp).
Recheck license and redistribution terms before copying or rebranding any code.
No fork, dependency installation, benchmark campaign, or runtime migration is started
by recording this backlog. Existing Serena fork-decision rules still apply.

## Reopening

Revisit this backlog in a later roadmap review after the accepted Zero-Relay critical
path, with a fresh bounded WO/claim and measured user benefit. It must not consume the
mutable lane or reviewer needed to close current Zero-Relay blockers.
Success remains accepted work with zero human relay actions, not more busy agents,
more campaign goals, or a renamed connector. No resource/performance gain is claimed yet.
