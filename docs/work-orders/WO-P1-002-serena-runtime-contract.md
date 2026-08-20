# WO-P1-002: Serena Runtime Manager Contract from Validated Prototype

Status: in_progress
Lane/files: `docs/contracts/serena-runtime-manager.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, `docs/work-orders/WO-P1-002-serena-runtime-contract.md`
Branch: main
Model tier: mid

## Goal + Acceptance criteria

Extract the validated manual multi-Serena implementation into a product-grade runtime-manager contract **without copying secrets or launcher implementation blindly**.

Acceptance:
- inspect `C:/AI/serena-instances/` and `SERENA-MULTI-INSTANCE.md` read-only;
- record reusable runtime-profile fields and lifecycle semantics;
- define explicit worker/process/tunnel/health ownership invariants;
- define idempotent start/targeted stop/restart/release behavior;
- define stale PID, port collision, tunnel collision, project-identity, and unhealthy failure handling;
- distinguish `REUSE`, `WRAP`, `EXTEND`, and private/local-only prototype data;
- no process-manager source code yet;
- no secret, tunnel credential, API key, or machine-private token copied into the repo.

## Reference pattern

- `PROJECT-PLAN.md` sections 3-7, 11-13.
- `docs/contracts/core-domain.md`.
- Validated runtime evidence under `C:/AI/serena-instances/`.

## Steps

1. Inspect the external runbook and instance structure read-only.
2. Inspect representative `instance.ps1`, `start.ps1`, `stop.ps1`, and status/health logic without copying secrets.
3. Extract stable product concepts vs machine-specific details.
4. Define RuntimeProfile, ProcessOwnership, HealthProbe, TunnelBinding, lifecycle, failure-state, and recovery contracts.
5. Review against Worker/Runtime domain boundaries and A-Wiki reuse gate.
6. Update checkpoint/current-work/handoff.

## Forbidden

- No changes under `C:/AI/serena-instances/`.
- No process start/stop/restart during this WO.
- No tunnel provisioning/config changes.
- No API keys/tokens/tunnel IDs in tracked files.
- No process-manager production source code.
- No A-Wiki/Phase6 mutation.
- No Git remote/push.

## Verify commands

- confirm only docs/coordination files changed;
- secret-like scan on the new contract;
- search new contract for accidental concrete tunnel IDs or credentials;
- `git diff --check`.

## Checkpoint log

- [2026-08-20] ChatGPT/Sunday-Conducter: opened after typed domain implementation commit `dbf5b34c44a3a10d70bf994a78739324c43bfe7a`. External prototype inspection is read-only.
