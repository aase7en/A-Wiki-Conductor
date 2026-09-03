# WO-P1-149 — Orchestration Decision Plane roadmap capture

Status: DOCS_ONLY / READY_FOR_REVIEW
Lane/files:
- `PROJECT-PLAN.md`
- `docs/research/fable-orchestrator-adoption-2026-09-03.md`
- `docs/plans/2026-09-03-orchestration-decision-plane-roadmap.md`
- `docs/work-orders/WO-P1-149-orchestration-decision-plane-roadmap.md`
Branch: `docs/wo-p1-149-orchestration-decision-plane-roadmap`
Model tier: primary-only (architecture / cross-repo authority boundary)

## Goal + Acceptance criteria

Capture the useful Fable Orchestrator concepts as a provider-neutral, capability-first Orchestration Decision Plane roadmap that strengthens A-Sunday Conductor while preserving A-Wiki orchestration authority and existing Conductor graph/provider/review/runtime systems.

Acceptance:
- upstream Fable behavior is recorded from primary source at a pinned SHA;
- adopted vs rejected concepts are explicit;
- reuse-before-build classification is explicit;
- roadmap defines packet, graph-admission, routing, adjudication, review, observability, and E2E slices;
- no active source/PR ownership is overlapped;
- no model/vendor is hard-coded into canonical task semantics;
- no live provider/worker traffic occurs;
- no second planner/router/scheduler/review/task/memory authority is introduced;
- deterministic docs checks pass.

## Reference pattern

- A-Wiki `docs/protocols/cross-agent-work-orders.md` — capability-first model routing and bounded work-order contracts.
- A-Wiki `skills/awiki/a-claim/SKILL.md` — claim-before-mutation coordination.
- `docs/contracts/a-wiki-a-conductor-integration.md` — A-Wiki brain/orchestration authority vs A-Conductor execution authority.
- `docs/contracts/capability-vocabulary-bridge.md` — canonical capability boundary.
- existing `src/a_conductor/graph/**` — TaskGraph/READY/scheduler/dispatch/store; inspect only in this WO.
- existing provider configuration/policy/execution-authority/selection-evidence seams; inspect only in this WO.
- upstream reference `codejunkie99/fable-orchestrator@3b653701d48095a488c350f7a9d5b1fca4d37183`.

## Steps

1. Recover current remote SSoT and inspect live PR/worktree ownership.
2. Run A-Wiki reuse-before-build inspection and classify the proposal.
3. Research pinned Fable source; separate facts from inference/recommendation.
4. Define a provider-neutral Orchestration Decision Plane architecture.
5. Decompose implementation into bounded future ODP nodes with dependencies and acceptance signals.
6. Update `PROJECT-PLAN.md` with the new roadmap pointer and authority boundary.
7. Run deterministic docs/scope/secret/UTF-8 checks.
8. Commit/push/open a docs-only PR only after diff and ownership verification.

## Forbidden

- `src/**` and `tests/**` mutation in this WO.
- `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, or other hotspot mutation while active lanes own/need them.
- PR #199 / WO148 provider-service-authorization source/test scope.
- PR #200 / WO147 ReviewBus adapter scope.
- live Worker/tunnel/provider mutation or prompt execution.
- A-Wiki repository mutation.
- new planner SSoT, scheduler, task graph store, provider registry, review lifecycle, claim system, or memory system.
- hard-coded vendor/model identity as canonical capability semantics.
- plaintext credentials, tokens, cookies, endpoints containing secrets, or private user data.
- weakening WO096 or AiPASS authorization/admission gates.

## Verify commands

```powershell
git diff --check
git status --short
git diff --name-only origin/main...HEAD
python -c "from pathlib import Path; files=[Path('PROJECT-PLAN.md'),Path('docs/research/fable-orchestrator-adoption-2026-09-03.md'),Path('docs/plans/2026-09-03-orchestration-decision-plane-roadmap.md'),Path('docs/work-orders/WO-P1-149-orchestration-decision-plane-roadmap.md')]; assert all('\ufffd' not in p.read_text(encoding='utf-8') for p in files); print('UTF8_OK')"
```

Additional gates:
- changed files equal the four declared files only;
- added-line credential-shaped scan = zero findings;
- no source/test/live-runtime mutation;
- final diff still describes future implementation as future work, not accepted behavior.

## Checkpoint log

- [2026-09-03] GPT-5.6 Sol: recovered actual state. Protected root `main` is stale/dirty with user-owned `assets/donate-promptpay-qr.png`; mutation forbidden there. Fetched `origin/main@6e96b773aeb0795807cb65abce93956b7702f33e` (PR #183 merge). Open PR #199/WO148 owns provider service authorization + `COLLAB.md`; PR #200/WO147 owns ReviewBus adapter. Created isolated clean worktree `A:\GitHub\A-Wiki-Conductor-wo149-orchestration-decision-plane` on branch `docs/wo-p1-149-orchestration-decision-plane-roadmap` at `6e96b77`. A-Wiki local claim `403dc41e4dbd` acquired for exactly the four docs files above. Reuse gate: `REUSE + WRAP + EXTEND`; A-Wiki remains high-level orchestration/model-policy authority, Conductor remains runtime/graph/provider/evidence authority. No production mutation authorized by this WO.
- [2026-09-03] GPT-5.6 Sol: roadmap capture implemented in exactly four declared docs files. `git diff --check` PASS; UTF-8 decode/U+FFFD gate PASS; added-line credential-shaped scan PASS; private-user-path scan PASS; `origin/main` remained `6e96b773aeb0795807cb65abce93956b7702f33e` after fresh fetch. ODP implementation remains future bounded work and must use separate WOs/claims; this WO performed no `src/**`, `tests/**`, live provider/Worker, A-Wiki, COLLAB/CURRENT-WORK/handoff mutation.
- [2026-09-03] GPT primary docs review corrected a contract-truth mismatch before acceptance: the roadmap no longer labels itself APPROVED while PR #201 is still Draft/unmerged. Status is now candidate/review-required; ODP-1..ODP-9 remain future slices requiring separate claims. Upstream Fable pin and REUSE+WRAP+EXTEND architecture remain unchanged.
