# A-Wiki Conductor (A-Conductor)

A local autonomous control plane for coordinating AI agents, coding agents, MCP servers, local/cloud models, and A-Wiki memory.

A-Conductor is the product name; `A-Wiki-Conductor` is the repository/project name.

## What it is

- a **Control Center** desktop application (CLI-inspired, information-dense) that manages registered projects and three reusable worker slots (`a-worker-01..03`);
- a **durable job/execution fabric** with supervised subprocess execution, transport-loss recovery, duplicate-execution protection, and bounded output backpressure;
- an **operator protocol** (command/response) with a Telegram gateway mapping;
- the foundation for the long-term autonomous loop: `PLAN -> DECOMPOSE -> ROUTE -> EXECUTE -> VERIFY -> REVIEW -> REPAIR -> CONTINUE -> COMPLETE`.

Serena is the first worker runtime implementation — the semantic coding engine and MCP execution hand — not the whole orchestrator. A-Wiki remains the brain: policies, memory, and orchestration intelligence. A-Conductor is the execution fabric and control plane.

## Requirements

- Python 3.11+
- Windows 10/11 for the full runtime feature set (owned-process control, PowerShell inspection, tunnel-client boundaries)
- No third-party Python dependencies — standard library only

## Install

```bash
git clone https://github.com/aase7en/A-Wiki-Conductor.git
cd A-Wiki-Conductor
python -m pip install -e .
```

## Run

```bash
a-conductor            # launch the Control Center desktop app
a-conductor --smoke    # construct, refresh, and destroy the UI without mainloop
```

The control database defaults to `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` and can be overridden with `--database <path>`.

## Develop

```bash
python -m pytest tests/ -q
```

## Documentation

- `PROJECT-PLAN.md` — authoritative product vision, architecture, roadmap, constraints
- `COLLAB.md` — cross-agent lanes, claims, work-order rules
- `CURRENT-WORK.md` / `handoff.md` — active execution state and resume snapshot
- `docs/work-orders/` — one bounded work order per implementation chunk
- `docs/contracts/` — binding architecture/behavior contracts
- `docs/references/` — external-system reference notes (e.g. Serena configuration)

## Agent entry contract

Before non-trivial work, every agent/session must read, in order: `PROJECT-PLAN.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, and the active `docs/work-orders/<id>.md`. See `AGENTS.md` for the full contract.
