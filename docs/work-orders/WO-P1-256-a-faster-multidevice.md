# WO-P1-256 — A-Faster multi-device multilane router profile

Status: IN_PROGRESS
Issue: #362
Risk: R3 — routing/cleanup/provider-harness policy, docs/skill only
Task topology: CONTROL_PLANE_ONLY
Authority repo / repo: `A:\GitHub\A-Wiki-Conductor`
Base: `origin/main@51a71eccae136d3144b508b5f136eff69e6b53ec`
Worktree: `A:\GitHub\_worktrees\A-Wiki-Conductor-wo256-a-faster`
Branch: `docs/wo-p1-256-a-faster-multidevice`
Owner: SunDay-Worker 4 under GPT-5.6 Sol integration

## Goal

Add **A-Faster** as an accelerated profile of the canonical A-FastTask
router/binder for safe multi-device, multi-harness execution. Preserve the
existing authority model and backward compatibility.

A-Faster must accelerate accepted work, not invent a second scheduler/task
store/claim/review/completion authority.

## Reuse classification

`EXTEND`, not `NEW`/shadow authority.

Existing canonical assets reused:

- `.agents/skills/a-fasttask/SKILL.md`
- A-FastTask closeout/recovery references
- `PROJECT-GRAPH.yaml` global WIP
- existing CoinTH quota/readiness policy
- existing Worker/RDC/GitHub/Kilo routes
- existing durable execution pointer/recovery protocol

A-Faster is a thin accelerated profile that MUST load A-FastTask first.

## User-requested operating profile

- attempt SunDay-Worker 1..5 every substantial engineering session;
- use RDC for Mac operations when actually exposed/online;
- coordinate Windows + macOS without overlapping mutable scope;
- use GitHub connector for remote truth when callable;
- prefer Kilo Code CLI GLM-5.3 MAX and Claude Code CLI GLM-5.3 MAX on
  independent bounded lanes;
- recycle/cleanup accepted merged lanes to reduce local disk load;
- use Ponytail/Caveman/Grill-me as advisory helpers only.

Default WIP remains one **global** `3 mutable + 1 review` budget.

## Allowed tracked scope

- NEW `.agents/skills/a-faster/**`
- MODIFY `.agents/skills/a-fasttask/SKILL.md` — accelerated-profile pointer only
- MODIFY `PROJECT-GRAPH.yaml`
- this Work Order

## Forbidden

- runtime/source/DB/provider implementation
- new task/claim/scheduler/result store
- mutable global Active Project authority
- secrets or raw credential-bearing diagnostics
- silent provider/model fallback
- reset/clean/stash/force cleanup
- third-party source copies inside A-Wiki other than metadata/provenance facts

## External advisory provenance / Windows state

Validated 2026-09-19:

- Ponytail: `DietrichGebert/ponytail`, MIT, source main SHA
  `e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156`; Claude Code plugin
  `ponytail@ponytail` v4.10.0 installed/enabled at user scope.
- Caveman skill: `JuliusBrussee/caveman` source SHA
  `542442bab314973709f95b85b1ac0b3f6f5b5dc6`; only
  `skills/caveman/SKILL.md` installed user-local. The repository license
  explicitly places this skill-side material under MIT; Engine-linked BSL
  directories are not installed/copied. Local skill SHA-256:
  `566828E1A89426CAABC6767DC7F9D94E72BA9C3D908FE829CEBB80380352C73B`.
- Grill-me: `JRA-CodingLab/grill-me`, MIT, source SHA
  `0df84b8129e9ab246f9b08a000a8a0d3f8481045`; skill-only user-local
  install. Local SHA-256:
  `763616D5E11B9C6D3D9FC75A0AF646C126E163A579A7B54F795DB15E5377DEA8`.

No third-party skill source is copied into A-Wiki by this WO.

## Current surface truth at claim

- Windows SunDay-Worker 1..5: invoked in this session.
- RDC: not exposed in the current ChatGPT tool registry;
  `PLUGIN_NOT_EXPOSED_TO_CHAT`. This blocks Mac-local actions only.
- GitHub connector: explicit connector invocation attempted but current
  conversation runtime returned `FORBIDDEN: restricted to developer MCPs`.
  Windows authenticated `gh` CLI is the declared temporary remote-truth
  fallback; it is not represented as the connector.
- Kilo CLI: installed and exact `cointh-glm/glm-5.3` route previously
  verified in current project flow.
- Claude Code CLI: installed v2.1.178. Exact `glm-5.3 --effort max`
  durable read-only preflight under
  `runs/WO-P1-256/claude-glm-preflight/` is terminal:
  `exit_code=1`, `API Error: Unable to connect to API (ConnectionRefused)`,
  zero input/output tokens and zero model usage/cost. Classify
  `CLAUDE_GLM_ROUTE_UNAVAILABLE`; do not retry blindly and do not silently
  fall back to another Claude/model/provider route. This blocks only Claude
  GLM lanes; Kilo/other already-proven routes may continue.

## Acceptance criteria

1. A-Faster explicitly loads/reuses A-FastTask and cannot grant authority.
2. Device + harness fields are part of every accelerated lane binding.
3. Global WIP stays 3 mutable + 1 independent read-only review across devices.
4. Same mutable hotspot cannot be owned by Windows/Mac/Kilo/Claude
   simultaneously.
5. Fresh CoinTH quota/readiness is mandatory before every material GLM dispatch.
6. Kilo/Claude exact-model routing has no silent fallback.
7. Ponytail/Caveman/Grill-me are optional advisory helpers only.
8. Cleanup remains fail-closed and non-force with durable evidence outside the
   target worktree.
9. YAML/frontmatter/references/UTF-8/diff/secret/scope checks pass.
10. Frozen exact SHA receives independent read-only review and exact-head CI
    before merge.
