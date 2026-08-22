# A-Sunday Conductor

A local autonomous control plane for coordinating AI agents, coding agents, MCP servers, local/cloud models, and A-Wiki memory.

**A-Sunday Conductor** is the product display name; `A-Wiki-Conductor` is the repository/project name, and `a_conductor` is the internal Python package.

## What it is

- a **Control Center** desktop application (CLI-inspired, information-dense) that manages registered projects and three reusable worker slots (`a-worker-01..03`);
- a **durable job/execution fabric** with supervised subprocess execution, transport-loss recovery, duplicate-execution protection, and bounded output backpressure;
- an **operator protocol** (command/response) with a Telegram gateway mapping;
- the foundation for the long-term autonomous loop: `PLAN -> DECOMPOSE -> ROUTE -> EXECUTE -> VERIFY -> REVIEW -> REPAIR -> CONTINUE -> COMPLETE`.

The first worker runtime is a semantic coding engine used as the MCP execution hand (see Credits) — not the whole orchestrator. A-Wiki remains the brain: policies, memory, and orchestration intelligence. A-Sunday Conductor is the execution fabric and control plane.

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

The control database defaults to `%LOCALAPPDATA%\A-Conductor\control-center.sqlite` (the data folder keeps its pre-rename name so upgrades preserve existing data) and can be overridden with `--database <path>`.

**คู่มือภาษาไทยฉบับเต็ม: [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md)** — ติดตั้ง, ใช้งานทุกหน้าจอ, ตั้งค่า engine ต่อ worker, จัดการ tunnel instances, แก้ปัญหาเบื้องต้น

## Download / install

Grab **`A-Sunday-Conductor-Setup.exe`** from the latest [GitHub Release](https://github.com/aase7en/A-Wiki-Conductor/releases) — a per-user installer (no admin): Start Menu + Desktop shortcuts, and a standard "Add or remove programs" entry. The portable single-file exe is available in the same release. Attribution for the bundled engine is in [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) (Serena, MIT).

> SmartScreen note: the executables are not digitally signed yet, so Windows may show "Windows protected your PC" on first run — choose **More info → Run anyway**.

## Distribution / fork-and-run

The app is a **pure local desktop program** (Windows 10/11, Python 3.11+, standard library only — no server, no web deployment):

1. Clone/fork this repository.
2. `python -m pip install -e .[test]` then run `a-conductor` (see the User Guide).
3. For non-developer machines, build a portable single-file executable with PyInstaller: `python scripts/build_portable.py` → `dist/A-Sunday Conductor.exe`.
4. Build the Setup installer on top of that: `python scripts/build_installer.py` → `dist/A-Sunday-Conductor-Setup.exe` (bundles the portable exe, this README's guide, and the third-party notices).

Out of the box, every user gets: project/worker registry, per-worker engine config dialog, durable job control with the optional supervised mode, and CI via GitHub Actions. The **CONNECTORS** panel manages local connector instances that follow the validated layout (`C:\AI\serena-instances\<name>\` with `instance.ps1` + Start/Stop scripts) — users without that infrastructure simply see an empty instances panel; creating instances/tunnels is a per-user setup documented in the User Guide §7.

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
- `docs/references/` — external-system reference notes for the bundled engine

## Credits

A-Sunday Conductor uses [Serena](https://github.com/oraios/serena) (MIT) as its internal semantic code engine. All user-facing tooling and branding are A-Sunday Conductor's own.

## Agent entry contract

Before non-trivial work, every agent/session must read, in order: `PROJECT-PLAN.md`, `COLLAB.md`, `CURRENT-WORK.md`, `handoff.md`, and the active `docs/work-orders/<id>.md`. See `AGENTS.md` for the full contract.
