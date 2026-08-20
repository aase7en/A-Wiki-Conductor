# WO-P1-043: Strict Operator Wire Codec

Status: in_progress
Lane/files: `src/a_conductor/operator_wire.py`, `tests/test_operator_wire.py`, `COLLAB.md`, `docs/work-orders/WO-P1-043-operator-wire-codec.md`
Branch: main
Model tier: high

## Goal

Define a strict bounded JSON wire representation for `operator.v1` requests/responses so future Hermes-on-Pi5, Telegram gateway, Discord gateway, desktop bridge, or HTTP/IPC transport can exchange typed operator messages without introducing arbitrary payloads.

## Parallel-safety boundary

Additive-only while `WO-P1-038` remains dirty and the Windows full-suite crash is under external investigation. Do not edit P1-038-owned files.

## Acceptance

- Encode/decode only `OperatorRequest` and `OperatorResponse`.
- JSON object only; bounded byte length.
- Duplicate keys rejected.
- Non-finite JSON constants rejected.
- Request decode delegates to strict `parse_operator_request` exact-field policy.
- Response decode accepts only the bounded response field set; unknown fields rejected.
- No generic `payload`, command, argv, prompt, token, stdout/stderr field.
- Stable compact UTF-8 JSON output; no network/HTTP/socket dependency.
- Targeted tests + compileall + diff/import/static scan pass.
- Full suite deferred while independent Windows Python `0x80000003` investigation is active.

## Forbidden

- No network server/client.
- No auth/token/credential implementation.
- No Telegram/Discord SDK.
- No P1-038 edit/import.
- No arbitrary JSON passthrough field.

## Verify

- `python -m pytest tests/test_operator_protocol.py tests/test_operator_wire.py -q`
- `python -m compileall -q src`
- `git diff --check`

## Checkpoint log

- [2026-08-20] Opened after operator dispatcher commit `a950d17` to prepare a transport-neutral Hermes/Pi5 wire boundary without touching network or credentials.
