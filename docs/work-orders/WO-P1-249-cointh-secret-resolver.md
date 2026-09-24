# WO-P1-249 — CoinTH resolver and dual-layer readiness repair

Status: BLOCKED_FOR_COMPLETION (`.agents/` WRITE BLOCKED)
Issue: #337 (user-provided task reference; GitHub API unavailable during takeover)
Historical candidate: PR #338, head `0b1513127d0cfe7e362f48f95a328123c214fc2f` — conflicting; do not rebase or mutate.
Owner: GPT integrator
Base: `main@1486e75484afa21a79810a7ebe0e92abb384c3b7`
Branch: `docs/wo-p1-249-cointh-dual-readiness`
Takeover date: 2026-09-24

## Goal

Create a fresh successor candidate that preserves the accepted deterministic CoinTH secret-resolution behavior and adds independent proxy quota/upstream provider readiness admission semantics.

## Allowed scope

- `.agents/skills/a-fasttask/SKILL.md`
- `.agents/skills/a-fasttask/references/conductor.md`
- `docs/runbooks/cointh-glm-quota.md`
- `docs/work-orders/WO-P1-249-cointh-secret-resolver.md`

No secrets, source/runtime changes, new secret store, quota/provider authority, scheduler, task store, claim/lease authority, or automatic paid-provider fallback. Do not edit `CURRENT-WORK.md` or `handoff.md`; the task's exact four-path scope is retained.

## Accepted historical behavior recovered from Git objects

- Resolve only the canonical key `COINTH_GLM_AUTH_TOKEN` via the approved private Project Protocol/existing A-Wiki resolver boundary; never recursively search disks, Drive, repo, logs, shell history, or unrelated environment stores.
- Keep secret value and source path out of output, logs, and persisted artifacts.
- Use the proven PowerShell `Invoke-RestMethod` client; an unproven client's 401/403 requires one compatibility recheck before auth classification.
- HTTP 401/403 is auth/entitlement evidence, not quota exhaustion; malformed or missing quota evidence fails closed.
- Historical implementation commits inspected: `c502c43`, `57374e5`, `ffa6f10`, `e919663`, `0b5742c`, and head `0b15131`. The head commit itself only normalizes a final newline in `conductor.md`; the accepted resolver behavior is in its ancestors. The historical branch is not a mutation base for this successor.

## Required dual-layer contract

1. `PROXY_QUOTA_STATE = AVAILABLE | EXHAUSTED | UNKNOWN` is separate from `UPSTREAM_PROVIDER_READINESS = READY | THROTTLED | UNAVAILABLE | UNKNOWN`.
2. CoinTH `GET /glm/api/quota` is proxy/account evidence only. Proxy `AVAILABLE` does not prove upstream readiness.
3. Material GLM dispatch requires proxy `AVAILABLE` AND upstream `READY`, plus existing model/route/authorization/scope gates. Unknown, stale, malformed, or provenance-free evidence fails closed. Neither proxy quota nor process liveness implies `READY`.
4. `THROTTLED` retains source/time/reset/cooldown evidence and suppresses repeated GLM probes until reset unless material evidence changes; independent safe GPT/Codex work continues.
5. At/after reset, perform exactly one bounded live admission/smoke recheck before refilling GLM lanes. Classify transport only after throttling is no longer the known blocker.
6. Operator/vendor evidence must carry source, observation time, reset, and freshness provenance and cannot be generalized beyond its freshness window. Without a stated freshness window it is `UNKNOWN`.
7. Incident: `PROXY_QUOTA=AVAILABLE + UPSTREAM_PROVIDER_READINESS=THROTTLED => GLM_ROUTE_READY=FALSE / UPSTREAM_PROVIDER_THROTTLED`, not `KILO_TRANSPORT_BROKEN`.

## Takeover and incident evidence

- Actual checkout at takeover: worktree `/Users/aase7en/GitHub/_worktrees/A-Wiki-Conductor-wo337-dual-quota`; branch `docs/wo-p1-249-cointh-dual-readiness`; HEAD exactly the declared base; clean before edits; remote `origin` points to `https://github.com/aase7en/A-Wiki-Conductor.git` and branch tracks `origin/main`.
- Issue #337 and PR #338 were requested for inspection. `gh issue/pr view` failed because `api.github.com` was unreachable. PR head and accepted historical content were inspected from local Git objects only; GitHub issue text/reviews/status remain unverified.
- Incident semantics are supplied by the user for 2026-09-24. This WO records them as required contract, not independently verified live telemetry.
- Current sandbox exposes `.agents/` as read-only. Both patch and direct write attempts to the two allowed `.agents/` files were denied; no bypass was attempted. They still need the same contract ported before this candidate meets complete acceptance.

## Candidate changes and verification

- Updated `docs/runbooks/cointh-glm-quota.md` with canonical resolver constraints, proxy/upstream state separation, admission/reset behavior, provenance/freshness rules, and the required incident classification.
- This WO restores the historical missing work-order artifact and records takeover, evidence limits, and the `.agents/` write blocker.
- Still required for a complete candidate: apply matching A-FastTask skill/reference changes within the allowed scope when a writable checkout is available; then run strict UTF-8, `git diff --check`, exact four-path scope, added-content secret-signature scan, and any existing focused docs/contract tests that touch A-FastTask.
- No commit, push, merge, reset, clean, stash, or global config change performed.

## Acceptance

Complete only when all four allowed files carry one consistent contract, deterministic checks pass, and the candidate is ready for integrator review. Until the `.agents/` restriction is resolved in an authorized writable checkout, this is a partial candidate and not complete.
