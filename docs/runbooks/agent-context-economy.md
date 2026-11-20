# Agent Context Economy — Reusable Runbook
Status: scoped guidance (WO-P1-677); existing SSoT, claim and continuity authorities remain binding.

## Goal
Reduce unnecessary file reads, duplicated tool output and long-context recurrence **without** reducing verifiable evidence or accepted work. A smaller tool response does not by itself prove fewer billed tokens.

## Minimum safe startup
1. Read the repository entry, graph and AGENTS; follow security and ownership rules first.
2. Recover actual Git/runtime, Work Order, claim, outstanding executions and exact-SHA evidence. Do not redispatch on UNKNOWN.
3. Read the relevant CURRENT-WORK **section** and active Work Order; read handoff on resume/transfer/ambiguity, not blindly as live truth.
4. Load only graph-selected workflows; mandatory source, security and acceptance evidence always takes precedence over the heuristic budget.

## Progressive context defaults
- Start with a scoped file list/headings and symbol-level search. Avoid recursive whole-repo dumps, full logs and outputs from generated trees.
- An initial ordinary file excerpt of 120 lines / 12 KiB maximum is a **soft trial budget**, not an enforced ban: expand when the task requires authoritative detail.
- For large CURRENT-WORK.md, DEFECT_LESSONS.md, PROJECT-PLAN.md and handoff.md locate the relevant heading/range, then read bounded excerpts. Do not reload their full contents at every micro-step.
- Return compact **lossless-reference** tool receipts: task, repo/worktree/branch/SHA, test status+exit, failing assertions, evidence path/range/digest, truncation flag and next safe action. Keep raw evidence retrievable via existing durable systems.
- Reuse SundayMCP batch/compact tools only when the model-visible channel passes the real ChatGPT canary. Existing Issue #541 owns the separate read tool work; do not implement shadow receipts here.
- Prefer targeted tests during edits, then risk-required exact-SHA CI/review. Never skip an applicable test, review or authorization merely to save tokens.

## Ignore files are context filters, not security gates
- .kilocodeignore and .cursorignore exclude common generated/binary/media/log files from ordinary assistant discovery. Terminal, MCP and other harnesses may still read them. Use real filesystem permissions, path allowlists, approvals and secret handling.
- 3D/images/PDF/logs are legitimate sources for relevant work. Permit **narrow exact-path task exceptions** via authorized agent/tool settings; never globally relax secrets gates.
- Do **not** copy blanket media excludes to ENV Webapp, Estate, Figma/design/3D-first repos without checking their agent rules and asset discovery use cases.
- Never ignore active Work Orders, AGENTS, entry, graph, task checkpoints, CURRENT-WORK or exact result metadata. Do not make a second HANDOFF.json source of truth.

## Safe lifecycle and rotation
RECOVER -> RECONCILE/HARVEST -> CLAIM -> SCOPED EXECUTE -> VERIFY -> FREEZE SHA -> RISK REVIEW/CI -> CHECKPOINT/FOLD -> RELEASE -> COMPACT/ROTATE IF SAFE.

No unconditional auto-commit, context clear, lease release, blind retry or duplicate writer. Existing ContextRolloverGuard/A-NightShift govern continuation; a vendor hook is not mutation authority.

## Prove savings with actual measurements
Where the provider provides it, record input/output/cache-read/cache-write tokens, model+effort, tool bytes/truncation, repeated-file reads, context rotations, accepted task success/rework, latency and cost. Missing values are UNKNOWN. Compare equivalent tasks before claiming percentage or billing savings.

## Rollout to another project
Read that repo's current AGENTS, tool configs, asset types, tasks, ownership and Git status. Use an accepted work order/isolated branch. Reuse the **principles**; adapt ignore patterns per repo; run allow/deny fixture tests and targeted smoke. Do not change editor-global permissions or other projects silently.

References: AWC AGENTS.md, PROJECT-GRAPH.yaml, docs/agent-collab/FAST_EXECUTION_PROTOCOL.md, Work Order #677, Issue #541, https://kilo.ai/docs/customize/context/kilocodeignore , https://prod.cursor.com/docs/reference/ignore-file .
