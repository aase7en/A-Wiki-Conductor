# WO-P1-132 — AiPASS Provider Roadmap Capture

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: ROADMAP_CAPTURED / DRAFT_PR_183
Priority: P1 planning; must not preempt WO096, WO127, or WO128
Repository: `A:\GitHub\A-Wiki-Conductor`
Worktree: `A:\GitHub\A-Wiki-Conductor-wo132-aipass-roadmap`
Branch: `docs/wo-p1-132-aipass-provider-roadmap`
Base: `origin/main@9118a289b9fcd87e0bae4e4eb601cc585062856d`

## Goal

Capture a durable, priority-ordered roadmap for evaluating AiPASS as an optional provider lane in A-Sunday Conductor without creating a second orchestration, provider, execution, or filesystem-authority system.

## Reuse-before-build classification

- Existing provider configuration / policy / authority / operator view / runtime assembly: `REUSE + EXTEND`.
- Existing resilient execution / transport recovery / evidence / deduplication: `REUSE`.
- AiPASS bridge architecture: `REFERENCE`, then implement only the minimum Conductor-owned adapter seam.
- Browser-backed provider abstraction: defer generalization until a second provider proves reuse.
- AiPASS local file-agent protocol: `DO NOT ADOPT` as Conductor execution authority.

## Safety gate

The protected root checkout is stale and dirty and remains untouched. This work uses a clean isolated worktree from authoritative GitHub main. PR #182 / WO127 does not claim `PROJECT-PLAN.md`; WO128 is isolated to provider-store/projection scope.
## Allowed scope

- `PROJECT-PLAN.md`
- `docs/plans/2026-09-02-aipass-provider-integration-roadmap.md`
- this work order
- bounded `COLLAB.md` claim/release bookkeeping only

## Forbidden scope

- all `src/**` and `tests/**`
- `CURRENT-WORK.md` and `handoff.md` active-frontier ownership
- WO127 / WO128 implementation scope
- WO096 live Worker/tunnel operations
- credentials, cookies, tokens, private Drive secrets, or live AiPASS automation

## Acceptance criteria

- Current project priorities remain authoritative and AiPASS is placed after provider-control/evidence prerequisites.
- Authorization/legal/terms and source-license gates are explicit and fail closed.
- The roadmap defines phased read-only, fake-backend, resilience, live-pilot, cost-routing, and UI work.
- AiPASS cannot become direct Git/filesystem mutation authority.
- Existing `CONFIGURED != READY != AUTHORIZED` semantics are preserved and extended truthfully.
- No code from the reference repository is copied by this work order.
- A future implementation can allocate bounded work orders from the roadmap without relying on this chat.
## Checkpoint — 2026-09-02

- Authoritative main verified at `9118a289b9fcd87e0bae4e4eb601cc585062856d` before claim.
- Open PR #182 / WO127 was inspected and does not claim `PROJECT-PLAN.md`; WO128 remains isolated to its provider-store/projection lane.
- Added the binding roadmap section to `PROJECT-PLAN.md` and the detailed plan under `docs/plans/`.
- Priority remains WO096 P0, then active WO127/WO128, then AiPASS AIP-1 contract work.
- Official AiPASS terms effective 2026-08-19 were re-verified; live automated use remains `BLOCKED_EXTERNAL` absent official support or explicit written authorization.
- Reference repo inspected at `12b87bfd968db1e0d112eb8bd99b6481b3d7aaf7`; no root `LICENSE` file was visible, so this work copies no source code.
- Verification: UTF-8 reads PASS; `git diff --check` PASS; changed scope is docs/roadmap only.
- Root checkout remained untouched; no `src/**`, tests, live Worker/tunnel, credential, WO127, WO128, or WO096 mutation occurred.
- Draft PR: #183 (docs: add AiPASS provider integration roadmap); merge remains gated by normal review/CI discipline.
