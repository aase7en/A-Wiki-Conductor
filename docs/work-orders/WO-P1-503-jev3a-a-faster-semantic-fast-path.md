# WO-P1-503 — JEV-3A A-Faster semantic fast path

Status: ACTIVE / R1-R2 / CONTROL_PLANE_ONLY
Parent: Issue #501
Issue: #503
Reuse class: EXTEND A-Faster; do not create a new skill/control plane

## Lane binding

- Authority repo: `A:\GitHub\A-Wiki-Conductor`
- Execution repo: same repo
- Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo503-jev3a`
- Branch: `docs/wo-p1-503-a-faster-jev-fast-path`
- Base at claim: `bf1d9727c6f0b88abd11b6a744e6276c69e769ca`
- Mutable slot: M3
- Owner: bounded docs/skill lane; GPT-5.6 Sol remains integrator/acceptance authority

## Goal

Extend the existing A-Faster acceleration overlay so bounded semantic judgments can use the provider-neutral JEV fast path before frontier reasoning, without changing task/claim/mutation/review/completion authority.

## Allowed scope

- `.agents/skills/a-faster/SKILL.md`
- NEW `.agents/skills/a-faster/references/jev-semantic-fast-path.md`
- this Work Order

## Routing contract

1. Deterministic facts first: Git/claims/WIP/quota/exact-SHA/math/date/counting remain tool/code facts.
2. Jev eligibility is initially limited to:
   - task classification;
   - skill/capability suggestion;
   - failure classification;
   - evidence relevance/support;
   - escalation decision.
3. `review_severity` remains frontier reasoning until separately proven.
4. Authority/security/ownership/claims/mutation/merge/completion never route through Jev as an authority source.
5. Modes:
   - OFF: no semantic call;
   - SHADOW: record evidence only;
   - ADVISORY: expose a bounded recommendation to deterministic policy/integrator.
6. Failure/timeout/malformed/low-confidence/high-risk uncertainty -> frontier escalation; no blind retry.
7. Jev service calls consume no separate mutable/review WIP slot; the surrounding admitted engineering lane remains the WIP owner.
8. A-FastTask remains router/binder. A-Faster remains an overlay only.
9. GPT-5.6 Sol remains architecture/integration/adjudication/acceptance authority.
10. GLM-5.3 remains primary bounded engineering labor; MAX remains required where R2/R3/review policy says so.
11. JEV-5 production admission is required before any automatic routing with product consequence.

## Documentation shape

Keep `SKILL.md` concise. Add only the trigger/routing summary and link to the detailed reference. Put eligibility, fallback, telemetry and examples in `references/jev-semantic-fast-path.md`.

## Verification

- no duplicated scheduler/provider registry/authority semantics;
- terminology matches JEV/ODP roadmap and A-FastTask base;
- exact three-path scope;
- `git diff --check`;
- UTF-8/U+FFFD and added-line credential/session scan;
- independent review as required before merge.