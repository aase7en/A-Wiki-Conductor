# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-28 — WO-P1-087 Sunday Family Multi-Model Agent Harness Accelerator

## Current Objective

Make the multi-model/sub-agent harness the primary new-feature accelerator so A-Sunday Conductor can dispatch bounded work to GLM/Claude-Code-style and future providers without the user manually copying prompts between models.

## Current Phase

PLAN / SSoT PRIORITY SWITCH + SAFE REPOSITORY CLEANUP.

## Current Task

`WO-P1-087` — define the provider-neutral Sunday Family agent-harness roadmap, preserve existing North Star/Capability Fabric authority, and prepare the first bounded provider/harness implementation slice.

## Repository State

- Repository: `aase7en/A-Wiki-Conductor`
- Working lane: `A:\GitHub\A-Wiki-Conductor-agent-harness`
- Branch: `docs/wo-p1-087-agent-harness-priority`
- Base/initial HEAD: `origin/main@9106da2e5d2e7f5a687d40cc0b4677b6321ce1c1`
- Shared `A:\GitHub\A-Wiki-Conductor`: stale local `main@f4ecf9a`, dirty `assets/donate-promptpay-qr.png`; protected/read-only.

## Live / Protected Parallel Work

- PR #110 / `docs/wo-p1-086-capability-vocabulary`: open C0 prerequisite; do not edit its two files from WO-P1-087.
- PR #104 / `feat/ge-6-scheduler`: active Graph ownership; do not overlap scheduler scope.
- PR #108 / `fix/v070-installer-target-ownership`: active installer/release safety ownership; do not overlap.
- `feat/north-star-runtime-sunday-family`: unique North Star integration branch; preserve and reconcile later.
- `docs/wo-p1-082-ultra-independent-audit`: unique unmerged audit lane; preserve pending explicit disposition.
- detached `A-Wiki-Conductor-glm-release-audit` contains untracked `.venv-audit/`; protected until evidence ownership is resolved.
- `A-Wiki-Conductor-v070-path-quote` contains an untracked work-order file; protected.

## Safe Cleanup Completed

After fresh fetch/ancestry/status verification:
- removed merged local worktrees/branches for capability-plan-main (PR #109), GE-005A (PR #102), and frozen-uninstall-self-delete (PR #107);
- removed patch-equivalent GLM N2/N3 side worktrees after proving their patches were already integrated into North Star;
- removed the obsolete local superseded capability-plan worktree/branch while preserving its unique remote backup;
- deleted remote branches already proven merged for repo-health-100, WO-P1-085, GE-005A, and frozen-uninstall-self-delete;
- removed Git worktree registration for old `A-Wiki-Conductor-release-v070`; physical directory deletion is BLOCKED by an unknown process lock, so no process was killed and the folder remains.

## Decisions

- Product/brand remains **A-Sunday Conductor / Sunday Family**.
- First preferred coding harness: Claude Code / Anthropic-style harness.
- First configured model/provider: GLM-5.3 through a user-configured Anthropic-compatible provider.
- GLM/provider identity is replaceable metadata, not task/scheduler authority.
- Direct API may be added for lightweight work later; GUI automation is not the core orchestration path.
- Secrets are credential references only; never persist the proxy key shown in prior screenshots.
- Third-party proxy is an explicit trust/data-egress boundary.

## Evidence / Next Safe Action

1. verify this docs-only diff (`diff --check`, file scope, secret scan);
2. commit/push WO-P1-087 and open a Draft PR;
3. reconcile exact PR #110 state/CI and accept C0 when review gates are satisfied;
4. create AHA-1 provider/harness contract work order from updated main;
5. leave the locked orphan release folder untouched until the owning process is identified or naturally releases it.
