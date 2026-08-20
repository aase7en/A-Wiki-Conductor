# HANDOFF — A-Conductor

Last updated: 2026-08-20

## Current task

`WO-AC-RES-002 — Supervised Subprocess Launch / Inspect / Collect`

Status: `IN_PROGRESS`

## Baseline

- branch: main
- baseline HEAD: `0a3040d`
- AC-RES-001 durable execution records complete
- active Conductor listener: PID `25396`

## Boundary

Do not create a second generic process manager. Reuse exact-owned-process control; supervisor helper is only a transport-independent wrapper around a validated target command. No retry/reconnect/deduplication/Serena-specific integration yet.

## Next safe action

RED tests first: helper never uses shell, result JSON excludes argv/env/output, launch returns after startup handshake, inspect never launches, collect never reruns.
