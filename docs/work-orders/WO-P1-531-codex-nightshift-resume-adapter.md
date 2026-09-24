# WO-P1-531 — DEX-3b Codex NightShift resume adapter

Issue: #531
Class: CONTROL_PLANE_ONLY
Risk: R3
Claim: WO-P1-531-CODEX-RESUME-ADAPTER-MAC-001
Base: 1486e75484afa21a79810a7ebe0e92abb384c3b7
Worktree: /Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo531-codex-resume-adapter
Branch: docs/wo-p1-531-codex-resume-adapter

## Goal

Freeze a capability-proven local Codex DEX-3b resume adapter so an A-NightShift parent goal can survive the end of one Codex turn without depending on a ChatGPT user turn.

The adapter is transport only. Issue #215 remains automatic NEXT_READY continuation authority; A-NightShift remains run supervisor; A-Faster remains router/binder; Sunday remains execution substrate.

## Proven Codex capabilities

Current bundled Codex CLI exposes:
- `codex exec resume <SESSION_ID> [PROMPT]`;
- `codex resume <SESSION_ID> [PROMPT]`;
- `codex queue --thread <THREAD> --message <TEXT>`.

The contract must choose a bounded supported resume form and fail closed if capability probing changes.

## Contract requirements

- bind `run_id`, `thread_id`, model/effort, contract ref, receipt ref, repo/worktree identity and wake generation;
- parent turn emits one small machine-readable turn receipt with `CONTINUE` or `TERMINAL`, reason, outstanding executions and exact next safe action;
- resume is allowed only when parent goal is durably NONTERMINAL, no live parent process owns the same thread, generation/fencing matches, and resume capability is VERIFIED;
- wake message is only a pointer to existing durable goal/receipt; adapter does not select roadmap work;
- duplicate wake, stale generation, missing/ambiguous receipt, live-parent ownership, terminal receipt or frozen stop gate fail closed;
- secrets, raw argv/env, share URLs and prompt bodies are not persisted;
- ordinary ChatGPT timeout/session loss is irrelevant.

## Allowed tracked scope

- new `docs/contracts/codex-nightshift-resume-adapter-v1.md`
- optional new `docs/contracts/codex-nightshift-resume-adapter-v1.schema.json`
- new focused `tests/test_codex_nightshift_resume_adapter_contract.py`
- this WO

## Forbidden

NightShift/A-Faster files, `src/a_conductor/**`, SRM source, CURRENT-WORK, handoff, COLLAB, secrets, new scheduler/task/claim/retry/review/completion authority.

## Verification

- deterministic contract/schema tests;
- capability probe evidence for bundled Codex `exec resume`;
- fault cases: duplicate wake, stale generation, live owner, missing receipt, terminal receipt;
- UTF-8, diff-check, exact scope, secret scan;
- independent R3 review + CI + Sol acceptance.


## Capability / implementation checkpoint

The initial GLM-5.3 MAX author execution `exec-muf9hhe8-okmgo4m4` entered the
same zero-output Kilo/provider transport stall as the concurrent WO529/WO530
runs. It was cooperatively cancelled by exact execution id, harvested and
collected with no tracked mutation; Sol performed the bounded contract work
instead of blind redispatch.

A live Codex DEX-3b capability probe then proved the exact runtime behavior:
1. GPT-6 Luna / Medium seed turn completed and returned a persisted thread id;
2. `codex exec resume` rejected unsupported `-s` / `-C` options
   deterministically;
3. the supported noninteractive command form resumed the SAME thread and
   returned the expected continuation marker.

The v1 contract/schema therefore pins the proven `exec resume` surface,
generation fencing, no-live-owner admission, terminal/no-resume semantics,
ambiguous-delivery fail-closed handling, pointer-only wake payloads and the
strict transport-only authority boundary.

Verification: focused contract tests 27/27 PASS; strict UTF-8 and
git diff --check PASS. Independent R3 review and hosted CI remain required
before acceptance.
