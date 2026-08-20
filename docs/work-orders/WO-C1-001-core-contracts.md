# WO-C1-001: Core Contracts + Invariants

Status: done
Lane/files: `AGENTS.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/contracts/**`, `schemas/**`, `docs/work-orders/WO-C1-001-core-contracts.md`
Branch: not-initialized (local project is not yet a Git repository)
Model tier: primary-only

## Goal + Acceptance criteria

Establish A-Conductor's provider-neutral core vocabulary and machine-readable safety contracts before any runtime/process/UI implementation.

Acceptance requires:
- canonical definitions for `Project`, `Worker`, `Runtime`, `Agent`, `Provider`, `Capability`, `Assignment`, `Health`, `Execution`, and `ReviewResult`;
- explicit invariants separating A-Wiki, A-Conductor, Serena, workers, execution surfaces, and deterministic verification;
- versioned JSON Schema Draft 2020-12 contracts for task, repository identity/mutation gate, and evidence records;
- retry/recovery/approval semantics documented without duplicating A-Wiki's work-order/claim protocol;
- schemas parse mechanically as valid JSON;
- no UI/runtime/process-manager production code introduced;
- current-work + handoff updated with evidence.

## Reference pattern

- `PROJECT-PLAN.md` sections 1-5, 8-12, 15-17.
- A-Wiki `docs/protocols/cross-agent-work-orders.md` — reuse work orders/claims/pause-resume.
- A-Wiki `docs/protocols/cross-agent-plan-handoff.md` — reuse session/handoff semantics.
- A-Wiki `AGENTS.md` — cost-first routing, claim gate, deterministic/safety principles.
- `AGENTS.md` in this repo — project entry contract.

## Steps

1. Tailor `COLLAB.md` lanes/hotspots for A-Conductor.
2. Define canonical domain vocabulary + invariants.
3. Create `task-contract.schema.json`.
4. Create `repository-identity.schema.json`.
5. Create `evidence-record.schema.json`.
6. Document risk/approval/retry/recovery semantics and A-Wiki reuse boundaries.
7. Mechanically parse/inspect schemas and check cross-file naming consistency.
8. Update `CURRENT-WORK.md`, this checkpoint log, and `handoff.md`.

## Forbidden

- No A-Wiki repository mutation.
- No Phase 6 mutation.
- No Serena fork.
- No UI implementation.
- No runtime/process manager implementation.
- No SQLite broker implementation yet.
- No duplicate claim/work-order/handoff engine.
- No GitHub repository publication before `DR-C1-001` is resolved.
- No secrets or API keys.

## Verify commands

- `python -m json.tool schemas/task-contract.schema.json > NUL`
- `python -m json.tool schemas/repository-identity.schema.json > NUL`
- `python -m json.tool schemas/evidence-record.schema.json > NUL`
- `python -c "import json, pathlib; [json.loads(p.read_text(encoding='utf-8')) for p in pathlib.Path('schemas').glob('*.json')]; print('schemas-json-ok')"`
- Search for unresolved placeholder markers (`<...>`, `TODO`) in final C1 contract files; intentional future fields must be explicitly labeled.

## Checkpoint log (append-only)

- [2026-08-20] ChatGPT/Sunday-Conducter: A-Wiki reuse gate checked; no live A-Wiki claim and no matching A-Conductor task-board entry found at check time. Bootstrapped A-Wiki work-order templates; created `AGENTS.md`, `CURRENT-WORK.md`, and `handoff.md`. Local A-Conductor repo is not Git-initialized; GitHub publication remains `DR-C1-001`. Next: domain vocabulary + schemas.

- [2026-08-20] ChatGPT/Sunday-Conducter: C1 completed. Added canonical domain contract plus Task/RepositoryIdentity/Evidence JSON Schemas and examples. Deterministic verification: 3 schemas parsed, Draft 2020-12 check_schema PASS, 3 examples validate PASS, placeholder scan clean. SHA256: core-domain=4d0689dc29953aa54d128523ac6bf6e9008e63be21f97560d4a76b141ecadaf7; task=000355629887896e24fec94e61e44cb5b84ea7f1d616f789d9857f9748f9d1a6; repo-identity=1acaef58c07f2499810d866a4327f37e385d193c37ba0e5be62552746972c12c; evidence=57292f14c42829fd4676d01af400478ff7e9652670091f4b3931ec0efe266ac0. No runtime/UI code added.
