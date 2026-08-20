# WO-P1-040: Telegram Operator Command Mapper

Status: in_progress
Lane/files: `src/a_conductor/telegram_operator_commands.py`, `tests/test_telegram_operator_commands.py`, `COLLAB.md`, `docs/work-orders/WO-P1-040-telegram-command-mapper.md`
Branch: main
Model tier: high

## Goal

Translate a deliberately small Telegram `/a ...` command grammar into the already-binding `operator.v1` request objects without any Telegram SDK, Bot API, network, token, SQL, or execution logic.

## Parallel-safety boundary

Additive-only while `WO-P1-038` remains dirty and under runtime-crash investigation. Do not edit any P1-038-owned file or durable execution implementation.

## Acceptance

- Pure text-to-`OperatorRequest` mapper.
- Supports `/a` and Telegram group form `/a@BotUsername`.
- Supports bounded commands: `status`, `job`, `events`, `create`, `ready`, `claim`, `gate`, `checkpoint`, `exec`.
- Exact token counts; no quoting/shell parsing/multiline command chaining.
- `/a run ...` and free-form goals are explicitly unsupported; Hermes/A-Wiki owns conversational interpretation.
- Numeric fields are strict decimal integers and delegated to `operator.v1` validation.
- No network/token/bot SDK imports.
- Targeted tests + compileall + diff/static scan pass.
- Full suite deferred while unrelated Windows Python `0x80000003` investigation is active.

## Forbidden

- No Telegram Bot API call.
- No bot token handling.
- No webhook/long-poll implementation.
- No generic command/argv/shell field.
- No planner/router/LLM intent parsing.
- No P1-038 edits.

## Verify

- `python -m pytest tests/test_operator_protocol.py tests/test_telegram_operator_commands.py -q`
- `python -m compileall -q src`
- `git diff --check`
- static transport/network/command scan

## Checkpoint log

- [2026-08-20] Opened after `P1-039` operator protocol commit `1adb118` while GPT Work investigates the independent full-suite Windows runtime crash.
