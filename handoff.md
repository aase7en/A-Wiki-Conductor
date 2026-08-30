# HANDOFF — A-Sunday Conductor

Last updated: 2026-08-30 — WO-P1-112 COMPLETE / AHA-6 next

## Current objective

AHA-5 is accepted on main. Next: AHA-6 parallel READY-task execution with lease/scope collision safety; automatic GLM proxy dispatch must use an external secret resolver and quota preflight.

## Repository state

- AHA-5 PR: `#149` — MERGED.
- Accepted main: `f648e04eba647d3a40b6aaa8353c90714f0a2ea1`.
- Post-main CI: `33284585961` — SUCCESS on Windows/Ubuntu/macOS.
- Windows Frozen Setup install/uninstall E2E: PASS.
- Work order: `docs/work-orders/WO-P1-112-aha5-agent-review-repair-loop.md` — COMPLETE.
- Next mutation requires a new bounded AHA-6 work order/claim.

## Accepted predecessor

AHA-4B PR #147 merged as `7f9a16f6dfafe17f3795167da22d4886945611e0`.
Exact-head CI `33260601487` and post-main CI `33261050931` passed Windows/Ubuntu/macOS;
Windows passed Frozen Setup install/uninstall E2E.

## AHA-5 checkpoint

- Proposal boundary GREEN: `agent_change_packets.py` decodes Claude/GLM result envelopes
  and applies only complete-file proposals that pass exact identity, active lease,
  mutable/forbidden scope, exact HEAD and overwrite content-hash preconditions.
- Relevant regression: 176 passed; compileall/diff-check PASS.
- GLM remains read-only by design; Conductor owns materialization. This supersedes the
  earlier idea of granting GLM direct repository mutation rights.
- Raw direct-GLM maintenance probe timed out and exposed a Windows descendant/pipe-hold
  hazard. Do not use raw subprocess for the live slice; use `SupervisedExecutionService`.
- Next safe action: checkpoint commit, then run a supervised direct-Z.ai GLM proposal
  from exact clean HEAD and review/apply it through the new boundary.

## 2026-08-30 AHA-5 file bridge checkpoint

- proposal/result decoding, exact identity, one-file-per-task scope and content-hash preconditions are implemented;
- human one-prompt bridge reads/writes durable `runs/` task/result files; integrator reads results directly;
- deterministic review → repair packet → repaired result E2E is GREEN without human result copy-back;
- Claude provider execution is isolated from user-level settings with `--setting-sources project,local`;
- direct GLM-5.3 MAX reached Z.ai but provider returned HTTP 429 `[1113]` insufficient resource package;
- the user also has a working external Claude-CLI GLM proxy profile, but its credential is intentionally not tracked or copied into Conductor artifacts;
- automatic proxy dispatch remains fail-closed until that credential/profile is exposed through an approved external secret resolver; the durable one-prompt file bridge remains usable without result copy-back;
- these are external provider/configuration conditions, not permission to weaken deterministic gates;
- next safe action: defect-memory + broad regression/chaos + diff/secret audit, then PR/CI/re-audit/merge.

- AHA-5 audit evidence: related suite 122 passed; CI-equivalent full suite 1687 passed, 1 environment skip, 0 failed; compileall/diff-check/secret-pattern scan PASS.

## AHA-5 final acceptance

- PR #149 merged after exact-head CI passed.
- Post-main CI `33284585961` passed all jobs, including Windows packaging and Frozen Setup E2E.
- Local CI-equivalent suite: 1687 passed, 1 environment skip, 0 failed.
- Related AHA-5 regression: 122 passed.
- Automatic GLM proxy use remains fail-closed until an approved external runtime profile is configured; quota must be checked before dispatch.
