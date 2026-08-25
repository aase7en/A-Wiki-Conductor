# GE-0005 — D3: A-Wiki access is conductor-bridge-only (and D2 resolved by GE-0002)

Status: ACCEPTED — GPT-5.6 Sol MAX integrator decision, 2026-08-26
Date: 2026-08-25
Evidence: A-Wiki `docs/architecture/brain-vs-conductor-division.md`; `conductor/{state,gate,plan,verify,recall,claim,bridge}.py`; brain `.tmp/` stores are machine-local gitignored JSON.

## Decision

The Graph Runtime touches A-Wiki ONLY through `python -m conductor` (status/gate/plan/verify/claim/recall) or its importable `conductor/` package. It never reads/writes brain `.tmp/*` stores (task-board.json, agent-claims.json, blackboard, memory-ledger) directly — those are machine-local implementation details whose owner may change them (HOLD phases 8-11).

- Capability matching for dispatch: Conductor maps `required_capabilities` (awiki-task/v1 enum) to its OWN Worker/Provider registry; the bridge supplies GO/NO-GO + deterministic plan decomposition when asked.
- Model routing: reuse the POLICY artifacts (roster/policy confs) as inputs only; no re-coded tiering inside the scheduler.
- D2 (awiki-task/v1 schema mutation): not needed — see GE-0002 (graph fields live Conductor-side).

## Enforcement

Add a deterministic CI/static grep gate forbidding `a_conductor` imports of A-Wiki `scripts.lib.*` and direct references to A-Wiki `.tmp/` stores. Bridge entry points (`python -m conductor` or the importable `conductor/` package) are the only approved brain access seam. Any future exception requires a new ADR/reuse-gate decision.\n