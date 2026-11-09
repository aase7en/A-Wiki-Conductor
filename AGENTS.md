# A-Sunday Conductor — Agent Entry Contract

A-Wiki Conductor is the project/repository name. **A-Sunday Conductor** is the product display name (chosen 2026-08-22; supersedes "A-Conductor" as the public name). The internal Python package remains `a_conductor` and the data folder remains `%LOCALAPPDATA%\A-Conductor\` — do not rename those without an explicit migration decision.

**Important/secret files live in the private Drive layer** `L:\My Drive\A-Wiki-Data` (junction `drive/` from A-Wiki): Tunnel IDs → `secrets/a-conductor-tunnels.md`, connector-deletion zip backups → `backups/a-conductor-instances/` (the app writes there automatically when the folder exists). Read that layer's `AGENTS.md` + `LAYOUT.md` before touching it; never copy secrets into this repo.

**macOS SundayMCP recovery:** if the ChatGPT `SundayMCP Mac` connector is unavailable after a Mac restart, read `docs/runbooks/sundaymcp-mac-restart.md` before trying alternate transports. `npm run device:start` is the separate Desktop Commander remote-device path, not the OpenAI Secure MCP Tunnel runtime used by that connector.

Before any non-trivial work, every ChatGPT session, GPT Work/Codex task, A-Worker, Serena/SunDay Worker session, ZCode/GLM goal, local model, or external coding agent must use the same startup path:

1. `00-AGENT-ENTRY.md` - universal front door and role split.
2. `PROJECT-GRAPH.yaml` - select only the workflow/design/architecture nodes relevant to the task.
3. `AGENTS.md` - this repository contract.
4. Verify actual repository/worktree/remote/branch/HEAD/dirty state plus current claim/ownership before trusting summaries. Actual state is evidence of what exists; it never overrides user authority, safety constraints, or binding repository policy.
5. Read `CURRENT-WORK.md`.
6. Read the active work order under `docs/work-orders/` when one exists or has already been claimed. Read `handoff.md` only for resume/transfer work, unclear continuity, or when `CURRENT-WORK.md` points to it for material context.
7. Read the task-relevant nodes selected by `PROJECT-GRAPH.yaml`.
8. Read `DEFECT_LESSONS.md` before any `src/a_conductor/` mutation.
9. Classify R0/R1/R2/R3, prove non-overlap, claim the lane, then run the shortest truthful loop in `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`.

If a new task has no work order yet, product/source mutation remains blocked. A bounded docs-only governance bootstrap may create the initial work order/claim in a clean isolated scope, after which the full mutation gate must be rerun immediately.

`PROJECT-PLAN.md` and `DESIGN.md` are no longer mandatory large reads for every task. They remain authoritative and become mandatory when the project graph selects architecture/roadmap or UI/UX nodes. This reduces repeated startup cost without weakening continuity or safety.

For bounded agent reads and reusable cross-project context reduction, apply `docs/runbooks/agent-context-economy.md` as a **soft evidence-preserving heuristic**; never skip mandatory Work Order, safety, full-source or verification evidence solely to save tokens.

Default delivery model:

`GPT GOVERNANCE -> CAPABILITY-SELECTED EXECUTION -> DETERMINISTIC VERIFY -> INDEPENDENT REVIEW AS REQUIRED -> GPT ACCEPT/MERGE`

- Select the implementation executor by task class, risk, capability, readiness, authorization, cost, and availability using `docs/agent-collab/CAPABILITY_MATRIX.md`; GLM/ZCode is the current preferred candidate for bounded READY work when those gates permit it.
- GPT/integrator retains architecture, trust-boundary, dependency-order, SSoT, final defect adjudication, merge, release, and acceptance authority.
- R3 work requires GPT/integrator authority/failure-model framing before mutation as well as final GPT acceptance.
- A durable WO/task packet is the prompt contract. Do not regenerate a long bespoke prompt when a one-line pointer to that packet is sufficient.
- Until Zero-Relay is accepted, the human fallback is one pointer command only; result copy-back is not required when the integrator can read the result destination directly.

## Core continuity rule

Do not rely on chat/session memory as the source of truth. Durable project files, repository/runtime state, work orders, evidence, decisions, and handoff artifacts are authoritative within user/safety/repository-policy constraints.

Before stopping or delegating non-trivial work, update the active work order checkpoint, `CURRENT-WORK.md`, and `handoff.md` so another agent with no access to the previous conversation can continue safely.

### Context-window rollover

If the active chat/session context becomes crowded or near its practical limit, do not continue until continuity becomes unreliable. First checkpoint the active work order, branch/HEAD/worktree state, completed evidence, blocker/decision state, exact next safe action, and forbidden/ownership constraints in repository continuity artifacts. Only then recommend opening a new session. The new session must be able to resume from the repository entry sequence above without requiring the user to reconstruct or paste the prior chat history.

## A-Wiki reuse-before-build gate

Before creating or redesigning handoff, work-order, claim/lease, scheduler, task-router, model-router, memory, long-horizon orchestration, or other coordination primitives:

- inspect the authoritative A-Wiki GitHub state;
- inspect relevant A-Wiki protocols/ADRs/skills/scripts;
- inspect current work orders and live claims/leases when available;
- inspect known worktrees/branches/handoffs that may contain parallel work;
- classify the proposal as `REUSE`, `WRAP`, `EXTEND`, `REPLACE`, or `NEW`;
- prefer `REUSE -> WRAP -> EXTEND`;
- treat overlapping `REPLACE`/`NEW` work as `DECISION_REQUIRED`.

A local worktree alone is never sufficient evidence that equivalent work does not already exist.

## Safety

- Never modify the A-Wiki repository merely because A-Conductor depends on it; explicit authority is required for A-Wiki mutations.
- Never broad-kill `python.exe`, Serena, tunnel-client, `node.exe`, or ZCode processes. Process operations require exact PID + command identity.
- While ZCode is running, never run recursive/broad content searches over `%USERPROFILE%\.zcode\v2` (including Desktop Commander search). These can retain Windows file handles and block ZCode's atomic `config.json` replacement. Use a targeted single-file read, a temporary snapshot, or `scripts/diagnose_zcode_config_lock.ps1`; see `docs/runbooks/zcode-config-lock.md`.
- Never silently `reset`, `clean`, `stash`, `checkout/switch`, `rebase`, `merge`, or force-push user work.
- Preserve dirty/uncommitted work.
- Worker/process operations require explicit identity and PID ownership.
- Do not expose or commit secrets/API keys.
- Do not initialize or publish a GitHub repository without an explicit repository/visibility decision.

## Repo map & developer commands

- Layout: `src/a_conductor/` is a mostly flat module layout (the only subpackage is `graph/`, the DAG engine). Real entrypoints: `a_conductor.desktop_app:main` (Tk GUI) and `a_conductor.web_api:main` (HTTP), both exposed as console scripts; `python -m a_conductor` reaches the GUI. Module families cover supervised execution, worker leases, provider admission, harness adapters (Serena/ZCode/Claude Code), zero-relay, and orchestration. `tests/` is flat `test_*.py` files — no `conftest.py`, no pytest markers, no unit/integration split. `scripts/` holds build/installer/verify tooling plus `diagnose_zcode_config_lock.ps1`. Work orders live in `docs/work-orders/`. `web/sunday-family/` is a React + Vite subapp.
- Install: `python -m pip install -e .[test]` (Python >=3.11; CI pins 3.11; no lockfile). There is no lint, typecheck, or format tooling in this repo — do not hunt for it or add it silently.
- Run: `a-conductor` (desktop), `a-conductor-web` (HTTP), or `python -m a_conductor`. Smoke test: `python -m a_conductor --smoke --database <temp path>.sqlite` — always pass `--database`; the default targets the live `%LOCALAPPDATA%\A-Conductor\control-center.sqlite`.
- Tests: `python -m pytest tests/ -q` (full) or `python -m pytest tests/test_<name>.py -q` (per file — the repo convention, matching CI). Tests are self-contained: plain `monkeypatch` + `tmp_path`, `LOCALAPPDATA` redirected, no live data touched; Tk/GUI tests skip headless-safe; supervised-process tests are Windows-only; a few tests opt in only when an installed CLI is present.
- CI (`.github/workflows/ci.yml`) deliberately runs one pytest process per file: subprocess-heavy tests sharing a single long-lived process trigger 0x80000003 faulthandler/GC noise on hosted Windows runners. If a full local run dies oddly, mirror CI's per-file loop before diagnosing a real defect.
- Headless/hosted Windows: set `A_CONDUCTOR_GPU_PARTICLES=0` (WGL access-violates under ModernGL).
- Known Windows-machine quirks: bare `python` can resolve to an instrumented venv that breaks env-sensitive tests — use a clean interpreter (e.g. `py -3.13`) for local pytest runs. PowerShell also mangles inline quoting in `gh --jq` / `python -c`; prefer `--json` piped through `Out-String` or a temp script file.
- Build: `python -m pip install pyinstaller==6.22.2` (exact pin), then `python scripts/build_portable.py` and `python scripts/build_installer.py`; verify frozen artifacts with `python scripts/verify_frozen_installer_e2e.py`.
- Web subapp: root `npm run web:dev` / `npm run web:build` delegate to `web/sunday-family`; run its tests with `npm --prefix web/sunday-family run test`.

## Development discipline

- Binding delivery policy: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`. Classify work R0/R1/R2/R3 and use the shortest assurance loop that truthfully matches blast radius; repository/ownership/secret/destructive-operation gates never weaken.
- Delivery gate sequence: exact reviewed head -> CI run ID on that exact head -> merge the expected head only -> post-main CI run ID -> checkpoint recorded on the driving issue.
- Current P0 delivery accelerator: `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md` / `WO-P1-155`. Until ZRA-4 bounded-parallel acceptance is complete, prefer eliminating human GPT↔external-agent relay before starting broad ODP feature lanes that are not required by the zero-relay path. ODP reconciliation/readiness may still proceed in parallel when it does not consume a required mutable lane or violate ownership/dependency gates.
- Every multi-step implementation chunk must have a work order.
- Keep tasks bounded and resumable.
- Production code requires defined acceptance criteria and verification; prefer failing-test-first for behavior changes.
- Deterministic verification is preferred over LLM assertions.
- `DONE` means evidence satisfies acceptance criteria, not that an agent said it is finished.

## Product vocabulary

- **A-Sunday Conductor** (display name; formerly "A-Conductor") — local autonomous control plane / manager.
- **A-Worker 1 / 2 / 3** — initial reusable execution slots; internal IDs `a-worker-01`, `a-worker-02`, `a-worker-03`.
- **Worker** is runtime-neutral; Serena is the first runtime implementation, not the definition of Worker.
- **A-Wiki** — brain, policies, reusable protocols, memory/knowledge.
- **Serena** — semantic coding/tooling engine and execution hand, not the whole orchestrator.

## Shared prompt placement protocol

When handing a prompt/instruction to the user for another AI agent, session, Goal, CLI, or UI surface, follow the canonical A-Wiki protocol at `aase7en/A-Wiki:docs/protocols/prompt-placement-protocol.md`. Before the prompt, state exact `PLACEMENT`, `MODE`, `PURPOSE`, whether it replaces/appends/interrupts/queues, and `WHEN TO SEND`. This placement contract changes no A-Sunday Conductor task/claim/routing/review/acceptance authority.
