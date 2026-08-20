# WO-P1-041: Telegram Operator Response Renderer

Status: in_progress
Lane/files: `src/a_conductor/telegram_operator_render.py`, `tests/test_telegram_operator_render.py`, `COLLAB.md`, `docs/work-orders/WO-P1-041-telegram-response-renderer.md`
Branch: main
Model tier: mid

## Goal

Render bounded `OperatorResponse` metadata and static `/a` help into concise Telegram-safe text without any Telegram SDK, network, Markdown injection dependency, raw output, secret, or execution logic.

## Parallel-safety boundary

Additive-only while `WO-P1-038` remains dirty and under Windows runtime-crash investigation. Do not edit P1-038-owned files.

## Acceptance

- Pure renderer accepts only `OperatorResponse` plus static command metadata.
- Output is plain text by default; no Telegram HTML/Markdown parse-mode assumption.
- Response includes code/state/version/worker/attempt/evidence refs when present.
- Bounded output length; refs are capped and count-overflow is summarized.
- No raw stdout/stderr/prompt/token/secret fields can enter through the typed response.
- Help clearly states `/a run ...` is Hermes/A-Wiki conversational territory, not a direct operator protocol command.
- Targeted tests + compileall + diff/import scan pass.
- Full suite deferred while independent Windows Python `0x80000003` investigation is active.

## Forbidden

- No Telegram SDK/Bot API/token/webhook/long-poll.
- No SQL/job mutation/execution.
- No Markdown/HTML parse-mode requirement.
- No P1-038 edits.

## Verify

- `python -m pytest tests/test_operator_protocol.py tests/test_telegram_operator_commands.py tests/test_telegram_operator_render.py -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened after pure Telegram command mapper commit `441611d`.
