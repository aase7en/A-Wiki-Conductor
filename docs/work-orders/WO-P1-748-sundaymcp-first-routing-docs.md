# WO-P1-748: SundayMCP-first active routing docs
Status: IN_PROGRESS (docs-only, R2 binding routing change)
Issue: https://github.com/aase7en/A-Wiki-Conductor/issues/748
Authority repo: aase7en/A-Wiki-Conductor
Topology: CONTROL_PLANE_ONLY
Owner/claim: ChatGPT integrator; exclusive docs-only scope of Issue #748
Worktree: /Volumes/MAC_WORK/DevWorkspace/Github/AWC-wo748-sundaymcp-routing
Branch: docs/wo748-sundaymcp-first-routing
Base SHA: 224d72742063575c44ec46899a34a9889780f71d
Allowed scope: this WO, docs/agent-collab/TOOL_AND_FAST_PATH_ROUTING.md, docs/agent-collab/CAPABILITY_MATRIX.md
Forbidden: src/, runtime, services, other worktrees, AGENTS.md, CURRENT-WORK.md, historical rewriting, secrets, merge
Goal: Align active machine execution routing with SundayMCP macOS/Windows PRIMARY, RDC conditional fallback, GitHub remote truth, legacy Serena/Worker 1-5 non-default.
Preserve control-plane / execution-substrate roles, task/claim gates, GLM model routing and historical records.
Acceptance: no active worker-first/RDC-first routing; no false semantic parity or unified multi-device claim; two-file bounded diff; R2 review and CI as required.
Verification: git diff --check; exact changed-files scope; targeted active-routing grep; UTF-8/link checks; independent exact-SHA review and CI before merge.
Evidence/result: Issue #748, branch/PR candidate SHA and review/CI.
Replay safety: all writes bounded to dedicated isolated worktree; do not retry unknown writes without inspection.
Checkpoint 2026-11-13: Windows SundayMCP session terminated; Mac SundayMCP verified; origin/main equals 224d727; root dirty untracked protected; dedicated worktree created clean. No automatic merge.