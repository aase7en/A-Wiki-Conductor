# WO-P1-769 — SundayFamily Color E-Ink + Manga Visual Direction Alignment
Issue: #769
Related: #743 (UX-1), #739 (SundayFamily charter)
Status: CLAIMED / DOCS_ONLY / PENDING_REVIEW
Task topology: CONTROL_PLANE_ONLY
Risk: R2 — shared UI/design guidance and Agent entry routing; no runtime/security contract mutation.
Owner: ChatGPT integrator via verified SundayMCP macOS
Branch: docs/wo-p1-769-eink-manga-direction
Base SHA: 6ccc341013085d72fae90902115ab42c76e0217d
Authority repo: aase7en/A-Wiki-Conductor
## Operator decision (2026-11-17 Asia/Bangkok)
The target SundayFamily **Web/PWA/production-management UI** shall use muted **Color E-Ink**, hand-drawn manga ink linework, and the original stippled family identity. This replaces earlier monochrome-only and dark-web visual proposals for SundayFamily target screens. Original Tk desktop behavior, approved transition and security contracts remain intact until separately authorized and verified.
## Allowed scope (single integrator writer)
- docs/design/sunday-family-design-system.md (curated accepted visual direction; implementation details remain proposal until verified)
- DESIGN.md (clarify Tk vs web design authority)
- AGENTS.md, PROJECT-GRAPH.yaml (read-routing pointer; no safety/agent-governance rewrite)
- docs/design/2026-11-10-sunday-family-ux1-design.md (target visual addendum)
- docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md (design dependency addendum)
- PROJECT-PLAN.md (product target design alignment only)
- CURRENT-WORK.md, handoff.md (exact task checkpoint; preserve older history)
- this WO.
## Forbidden
- src/, tests/, web/ source, generated files, security/authorization, task/claim/retry/scheduler state, credential material, Tk retirement, deployment, Git history cleanup, root checkout, unrelated claims.
## Mandatory constraints
- Keep SundayFamily as read/presentation layer; all privileged actions must traverse A-Conductor Command Gateway with existing claim/authorization/replay checks.
- Preserve existing UX-1 seven-section Thai-first Information Architecture until explicit IA decision. Screen list in Gemini 109-page prototype is **not** automatic approval for 8 primary sidebar entries or a new runtime API.
- Distinguish VERIFIED source facts from inferred/mock screenshot values; never turn stale/unknown into healthy/zero. Treat visual direction approval separately from remaining UX-1 behavior and packaging gates.
- Reference source: operator-supplied Gemini Carbon 109-page DOCX v1.0.0-rc1 (private chat; not in repo); do not claim it was committed, independently validated, or that design measurements were measured in this lane.
## Evidence and acceptance
- Operator decision recorded on #743 and #769; scope/claim on #769; one isolated clean worktree, base SHA pinned.
- Diff limited to allowed files; markdown/link/UTF-8, tokens sanity, YAML parse, and direct agent-read pointer checks pass.
- Independent exact-SHA design/governance review and hosted CI required before merge. No self-review substitution.
- Post-merge confirm new instructions on main; only then mark implementation-authority alignment complete.
## Checkpoint
Candidate and CI/review status: to be filled after actual tests. Until acceptance: DOCUMENTATION_CANDIDATE / NOT_MERGED. UX-2 implementation still separately gated.