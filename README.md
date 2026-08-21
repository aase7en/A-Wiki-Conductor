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

**คู่มือภาษาไทยฉบับเต็ม: [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md)** — ติดตั้ง, ใช้งานทุกหน้าจอ, ตั้งค่า Serena ต่อ worker, จัดการ tunnel instances, แก้ปัญหาเบื้องต้น

## Distribution / fork-and-run

The app is a **pure local desktop program** (Windows 10/11, Python 3.11+, standard library only — no server, no web deployment):

1. Clone/fork this repository.
2. `python -m pip install -e .[test]` then run `a-conductor` (see the User Guide).
3. For non-developer machines, build a portable single-file executable with PyInstaller: `pyinstaller --windowed --onefile --name A-Conductor --paths src entry.py` → `dist/A-Conductor.exe`.

Out of the box, every user gets: project/worker registry, per-worker Serena config dialog, durable job control with the optional supervised mode, and CI via GitHub Actions. The **SERENA TUNNEL INSTANCES** panel manages local instances that follow the validated layout (`C:\AI\serena-instances\<name>\` with `instance.ps1` + Start/Stop scripts) — users without that infrastructure simply see an empty instances panel; creating instances/tunnels is a per-user setup documented in the User Guide §7.

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
