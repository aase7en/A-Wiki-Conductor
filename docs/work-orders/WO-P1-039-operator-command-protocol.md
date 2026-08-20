# WO-P1-039: Transport-Neutral Operator Command Protocol

Status: completed
Lane/files: `src/a_conductor/operator_protocol.py`, `tests/test_operator_protocol.py`, `docs/contracts/operator-command-api.md`, `docs/contracts/telegram-hermes-gateway.md`, `COLLAB.md`, `docs/work-orders/WO-P1-039-operator-command-protocol.md`
Branch: main
Model tier: high

## Goal

Define a transport-neutral, payload-minimal operator command protocol that future Telegram/Hermes, Discord, desktop, or other gateways can use without duplicating durable job state, planning, routing, or native execution logic.

## Parallel-safety boundary

This work order runs in parallel with `WO-P1-038`. It is additive-only and MUST NOT edit P1-038-owned files (`job_control.py`, `__init__.py`, `test_job_control.py`, `CURRENT-WORK.md`, `handoff.md`, or the P1-038 contract/work-order files).

## Acceptance

- Pure protocol types/parser only; no network, Telegram SDK, Discord SDK, SQL, scheduler, or subprocess.
- Command vocabulary is bounded and versioned.
- No generic shell/argv/command field exists.
- No raw high-level goal/prompt/transcript field exists; conversational intent remains Hermes/A-Wiki responsibility.
- Mutating job commands carry explicit `job_id`, `expected_version`, and required bounded identifiers.
- `execute` accepts only an opaque allowlisted `operation_ref`.
- Read-only commands support status/job/events views.
- Telegram/Hermes contract defines Hermes as preferred Telegram gateway and forbids competing long-poll consumers on the same bot token.
- Telegram Mini App is a later UI over the same operator API, not a separate execution authority.
- Targeted tests + compileall + diff/static API safety pass.
- Full suite is not required to close this additive parallel work order while the independent Windows pytest runtime crash investigation is active; record that limitation explicitly.

## Forbidden

- No Telegram bot token or credential handling.
- No Bot API calls.
- No webhooks or long polling implementation.
- No direct mutation of A-Wiki/Hermes/Pi5.
- No generic command execution.
- No planner/router/model-selection implementation.
- No P1-038 file edits.

## Verify

- `python -m pytest tests/test_operator_protocol.py -q`
- `python -m compileall -q src`
- `git diff --check`
- static scan for generic command/prompt/network fields

## Verification evidence

- RED: missing `a_conductor.operator_protocol` module.
- Targeted protocol tests: 37 passed.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Static request/response schema scan: no generic command/prompt/token/stdout/stderr fields.
- Static import scan: no Telegram/Discord/network/subprocess dependency.
- Full-suite verification intentionally deferred because an independent Windows Python `0x80000003` full-suite crash is under parallel GPT Work investigation; P1-039 does not touch that path.
- P1-038-owned files were not edited or staged by this work order.

## Checkpoint log

- [2026-08-20] Opened in parallel while GPT Work investigates the unrelated Windows full-suite runtime crash and P1-038 remains uncommitted but targeted-green.
- [2026-08-20] Completed additive transport-neutral protocol + Telegram/Hermes architecture contract with targeted/static gates green.
