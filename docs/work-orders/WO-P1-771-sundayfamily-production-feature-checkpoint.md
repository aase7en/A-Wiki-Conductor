# WO-P1-771 — SundayFamily AI Edge / Settings / Production Installer Requirements Checkpoint

Identity schema: GITHUB_ISSUE_V1
Issue: #771
Status: DOCS-ONLY AUTHOR CANDIDATE — NOT MERGED / NOT PRODUCTION AUTHORIZED
Risk: R1 docs-only with R2 review of governance/UX boundaries
Topology: CONTROL_PLANE_ONLY

## Goal and source
Preserve the operator's 2026-11-17 ChatGPT design discussion about SundayFamily production vision as a durable, agent-readable *requirements addendum*. This is NOT a new roadmap, task router, provider registry, queue, claim store, security permission, release authorization, or UI redesign.

Authority: `aase7en/A-Wiki-Conductor`; execution substrate remains `aase7en/SunDayRemoteMCP`, knowledge/skill source remains A-Wiki. Reuse `docs/plans/2026-11-13-sunday-family-unified-dashboard-routing-roadmap.md` (WO-P1-744 / #744). Existing implementation / evaluation work is not implicitly reopened.

## Claim / scope / exact base
- Issue: https://github.com/aase7en/A-Wiki-Conductor/issues/771 (claim checkpoint comment on issue).
- GitHub-only isolated branch: `docs/wo-p1-771-sundayfamily-ai-edge-checkpoint`.
- Exact base verified: `main@6ccc341013085d72fae90902115ab42c76e0217d`.
- Owner: ChatGPT integrator as bounded docs-only lane. No local checkout, no live runtime or provider invocation.
- Allowed: this **NEW** WO and **NEW** `docs/plans/2026-11-17-sundayfamily-ai-edge-production-requirements.md`.
- Forbidden: root `AGENTS.md`, `PROJECT-GRAPH.yaml`, `DESIGN.md`, SFU26 master roadmap, UX-1 docs, `CURRENT-WORK.md`, `handoff.md`, `src/`, `web/`, tests, infrastructure, secrets, installer/runtime mutation.
- Explicit conflict: #769 / PR #770 owns scoped visual design and overlapping AGENTS/project plan/continuity files. Do not alter them or assume UX-1 functional green-light.
- Unrelated Windows AWC dirty file `src/a_conductor/memory_presence.py` and untracked `.kilo/`; SRM untracked `.serena/` are untouched.
- Replay safety: inspect issue, branch and candidate PR/head before retry. No blind duplicate writes.

## Deliverable
One new, clearly labeled requirements document that maps:
1. ChatGPT/SundayMCP main-brain vs asynchronous agent/AI Edge boundaries.
2. Free/Batch/Local/Paid model capability policy and settings without hard-coded provider choices.
3. Reuse of existing `SemanticDecisionProvider`, Jev, SFU26 route/evaluation/telemetry cards; optional Google-type decision adapter subject to official API/privacy/price proof.
4. User-facing safe AI Control Center configuration and honest statistics.
5. One-command packaged Windows/macOS installation with signed release/preflight/doctor/rollback and no prerequisite manually installed dev runtimes.
6. UX/UI ownership separation (Gemini Carbon chat-only in another session).
7. Security/evidence/approval/release gates; per-card acceptance and next-safe work.

## Acceptance / review
- Exactly two new scoped Markdown files in PR; no change to existing files or code.
- Language distinguishes OPERATOR REQUIREMENTS from DESIGN CANDIDATES and UNVERIFIED provider/version/pricing claims.
- Does not override current SFU26 authority, visual work PR #770, Tk fallback, Command Gateway, provider/egress gates, or accepted claim/recovery protocol.
- GitHub PR diff examined at exact head; basic markdown/whitespace check; repository-required CI / independent review as applicable. **Do not self-merge**.
- Once review accepted and PR merged, fold into the existing continuity/AGENTS read path only via **separately claimed non-overlapping** work after PR #770.
- Gemini Carbon advice stays advisory; operator + integrator discuss before acceptance.

## Verified snapshot (2026-11-17, not timeless)
- Windows AWC local/remote main `6ccc341013085d72fae90902115ab42c76e0217d`, main dirty as recorded in Issue #771.
- SRM Windows `main@06265f7af67af56c5ffb653edb262c0639cd8677`, untracked `.serena/`.
- SundayFamily `web/sunday-family/` exists within AWC. The private remote `sunday-family-extension` repository is **populated**: verified `main@c3d88e7ab647debeb3a8bbe9f3dbdcb08696f8f8` (last push observed 2026-11-01) contains `manifest.json`, `package.json`, `src/`, `tests/`, `scripts/`, `docs/`, `vendor/`, `vectors/`, and `AGENTS.md`, plus three feature branches. An inspected *local checkout* returned an empty tracked HEAD tree; that is not evidence of an empty remote repository. Existing MV3 code must be reused/audited before any new implementation. Browser transport and installed/deployed readiness are **UNVERIFIED**. Do not infer full runtime readiness from repository contents.
- #769 / PR #770 open at checkpoint; therefore shared document edits are excluded.
- No paid model routing/benchmark/installer tests executed by this checkpoint.

## Exact next safe action
Freeze the two-file docs candidate, open reviewable PR linked to #771, verify the remote diff and CI status, await independent acceptance, then coordinate AGENTS/roadmap alignment only after #770's owner/claim is reconciled. No source implementation or production install from this issue alone.

## 2026-11-17 Operator multi-frontend expansion — CHECKPOINT

The operator expanded this **same** SundayFamily requirements/WO scope to include Gemini/Claude/other AI frontends, browser-mediated proposals, native MCP/API/CLI, and Kilo/GLM workers. This is not a new repo, task/claim/queue authority or new source implementation authorization.

- Edited only the already-scoped, newly introduced requirements document (section 10), on the same owned PR #772 branch; root `AGENTS.md`, `PROJECT-GRAPH.yaml`, UX, master roadmap and continuity hotspots remain forbidden.
- Principle: model-agnostic frontend/planner/reviewer **proposal/advisory** contracts with currently accepted GPT integrator/merge/release authority unchanged until explicit governance approval.
- Browser consumer AI: native MCP only when verified for specific account/client; otherwise manual read-only Context Pack export / `WorkOrderProposal` import for v1. Optional MV3 `PROPOSE_ONLY` extension is post-v1 and requires an independent R3 security claim.
- Confirmed reuse from read-only source: existing provider SQLite config, worker lease hotspot fence, pure worktree lifecycle classifier, TypeSafe adapter pinned to `jev-1.13.0` at checked SHA, SRM installer/doctor read models. Do not assert actual end-to-end installs or live multi-AI tests.
- Exact next action: review full two-file PR diff/hosted CI on its **new** head; request focused independent delta re-review of the factual correction; merge expected head only after acceptance, then post-main verify. PR #770 is merged at `789ee650b7723bcca7a986f569ef3b47962debc4`; still recheck issue #769 continuity ownership before a **separately claimed** root AGENTS/graph alignment WO after #772 is accepted. No source/provider/runtime/UX mutation from this checkpoint.
- Physical Windows/macOS checkouts and unrelated user files were not changed by this GitHub-only docs update.
