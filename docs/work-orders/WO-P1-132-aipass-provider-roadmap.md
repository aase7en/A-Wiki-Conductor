# WO-P1-132 — AiPASS Provider Roadmap Capture

Date: 2026-09-02
Owner: GPT-5.6 Sol integrator
Status: RECONCILED / READY_FOR_REVIEW
Priority: P1 planning; must not preempt WO096 or active WO134 acceptance gates
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

The protected root checkout is stale and dirty and remains untouched. This work uses a clean isolated worktree and has merged authoritative `origin/main@9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48`. WO127 and WO128 core are released; WO134 is a separate active product/review lane and does not claim this docs-only scope.
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

## Reclaim checkpoint — 2026-09-02
- PR #183 remains draft at `ca32390084658044ff2555167e4eb5ecf980cf42`; authoritative `origin/main` is `9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48`.
- Feature/main mutable-path overlap is 0 and `git merge-tree --write-tree origin/main HEAD` succeeds.
- Current official AiPASS Terms still require explicit written authorization for the automated/direct API modes in §3.4; live automation remains `BLOCKED_EXTERNAL`.
- `niawjunior/aipass-bridge` current main is `e01d6734400f743c1f84222d504b8ee98fea050b`; repository license metadata is null and root `LICENSE` is absent, so code reuse remains blocked.
- Reconcile scope stays docs-only: current priority/dependency state, current reference commit/evidence, and claim bookkeeping.

## Semantic reconcile checkpoint — 2026-09-02
- Merged authoritative `origin/main@9a88b1d38d90bf8ce98dcef9a5108e270e8d2b48` into the draft branch; feature/main path overlap before merge was 0 and the post-merge PR delta remains exactly four roadmap/coordination docs.
- Roadmap priority now records WO127 and WO128 T0+T1 as released, WO134 Provider Evidence Detail as the active provider frontier, and AIP-1 as next only after WO134 acceptance.
- Current bridge reference is `niawjunior/aipass-bridge@e01d6734400f743c1f84222d504b8ee98fea050b`; repository license metadata is null and root `LICENSE` remains absent, so source copying remains blocked.
- Official AiPASS Terms effective 2026-08-19 §3.4 were refreshed; automated bot/unapproved-software or direct API/API-key/token use remains `BLOCKED_EXTERNAL` absent explicit written authorization or an official supported path.
- No `src/**`, `tests/**`, CURRENT-WORK, handoff, live Worker/tunnel, credentials, cookies, tokens, or AiPASS automation were mutated.
- Next gate: strict UTF-8/diff/scope/secret audit -> commit/push reconciled docs -> remote PR diff audit -> CI/review -> merge only after WO134 dependency wording remains truthful.
