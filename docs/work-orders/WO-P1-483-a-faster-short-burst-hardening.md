# WO-P1-483 — A-Faster short-burst orchestration and timeout recovery hardening

Status: ACTIVE / DOCS-ONLY SHAPING
Issue: #483
Topology: CONTROL_PLANE_ONLY
Risk: R2 policy/tooling; source mutation may become R3 if execution semantics change
Claim: WO-P1-483-SHORT-BURST-DOCS-WINDOWS-001
Authority repo: A:\GitHub\A-Wiki-Conductor
Worktree: A:\GitHub\_worktrees\A-Wiki-Conductor-wo483-short-burst
Branch: docs/wo-p1-483-short-burst-hardening
Base SHA: 90d92bff51f1547548199be941c85c54d0a9fd3a

## Goal

Eliminate the recurring perceived-hang pattern by making short-burst orchestration, bounded output and timeout recovery explicit in A-Faster without weakening durable recovery or creating a second scheduler/retry authority.

## Current observed failure classes

- broad output/search/read exceeds wrapper limits;
- wrapper timeout while child may still run;
- long foreground build/test occupies a turn too long;
- repeated broad recovery scans add latency;
- pre-model transport failures waste turns;
- opaque tool cards hide progress.

## Desired contract

RECOVER EXACT EVIDENCE -> ONE BOUNDED ACTION/DISPATCH -> USER CHECKPOINT -> NEXT BURST

- exact-path/pointer reads before broad scans;
- bounded line/char output by default;
- long work goes background with PID/log/exit marker;
- wrapper timeout => UNKNOWN/RECOVER, never automatic FAILURE;
- redispatch forbidden until execution-pointer/result/exit/exact-PID reconciliation;
- pre-model transport failure is not acceptance evidence;
- explicit user-visible checkpoints independent of tool-card UI.

## Current mutation restriction

DOCS ONLY. Until #480 follow-up PR #490 is accepted/merged/post-main:
- do not modify .agents/skills/a-faster/**
- do not modify delegated_run_artifacts.py or its tests
- do not modify shared runner behavior
- do not overlap JEV family scopes

## JEV protected scope

Do not touch any JEV #484/#486/#488/#492 scripts/tests/fixtures/docs/roadmap.

## This shaping slice mutable scope

- docs/work-orders/WO-P1-483-a-faster-short-burst-hardening.md

Flash shaping may read current A-Faster docs/helpers but must leave all other tracked files unchanged.

## Shaping deliverable

Classify each desired behavior as:
- existing seam to REUSE;
- prompt/skill policy;
- executable helper/runner change;
- not enforceable in repo code.

Propose smallest future mutable scope and deterministic RED/test matrix. No second scheduler/task/retry authority.
