# A-Sunday Conductor — Agent Entry Contract

A-Wiki Conductor is the project/repository name. **A-Sunday Conductor** is the product display name (chosen 2026-08-22; supersedes "A-Conductor" as the public name). The internal Python package remains `a_conductor` and the data folder remains `%LOCALAPPDATA%\A-Conductor\` — do not rename those without an explicit migration decision.

**Important/secret files live in the private Drive layer** `L:\My Drive\A-Wiki-Data` (junction `drive/` from A-Wiki): Tunnel IDs → `secrets/a-conductor-tunnels.md`, connector-deletion zip backups → `backups/a-conductor-instances/` (the app writes there automatically when the folder exists). Read that layer's `AGENTS.md` + `LAYOUT.md` before touching it; never copy secrets into this repo.

Before any non-trivial work, every ChatGPT session, GPT Work task, A-Worker, Serena session, Codex task, or external AI/coding agent must read, in order:

1. `PROJECT-PLAN.md` — authoritative product vision, architecture, roadmap, constraints.
2. `DESIGN.md` — authoritative product UI/interaction direction, responsive rules, Sunday Family logo/motion, and performance contract.
3. `COLLAB.md` — A-Wiki cross-agent lanes, claims, work-order rules, pause/resume.
4. `CURRENT-WORK.md` — current phase, active work order, checklist, blockers.
5. `handoff.md` — latest verified resume state.
6. The active `docs/work-orders/<id>.md`.
7. `DEFECT_LESSONS.md` — บทเรียนจากข้อผิดพลาดที่เคยเกิดจริง (อ่านก่อนแก้โค้ดใน src/)

## Core continuity rule

Do not rely on chat/session memory as the source of truth. Durable project files, repository/runtime state, work orders, evidence, decisions, and handoff artifacts are authoritative.

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

## Development discipline

- Binding delivery policy: `docs/agent-collab/FAST_EXECUTION_PROTOCOL.md`. Classify work R0/R1/R2/R3 and use the shortest assurance loop that truthfully matches blast radius; repository/ownership/secret/destructive-operation gates never weaken.
- Current P0 delivery accelerator: `docs/plans/2026-09-04-zero-relay-accelerator-roadmap.md` / `WO-P1-155`. Until ZRA-3 is accepted, prefer eliminating human GPT↔external-agent relay before starting new ODP feature lanes that are not required by the zero-relay path.
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
