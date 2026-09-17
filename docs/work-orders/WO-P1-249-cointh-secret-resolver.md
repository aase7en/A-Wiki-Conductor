# WO-P1-249 — Canonical CoinTH secret resolver for A-FastTask

Status: ACTIVE / R2 DOCS-ROUTING
Issue: #337
Owner: GPT-5.6 Sol integrator
Base: `main@018779d0d2f5a7a7a21adb277e23a617692c36fd`
Branch: `docs/wo-p1-249-cointh-secret-resolver`

## Goal

Make fresh-session CoinTH quota preflight deterministic without chat memory or recursive filesystem/Drive searches. A-FastTask must resolve only the canonical secret key through the already-approved private Project Protocol/resolver boundary, then use the existing quota runbook.

## Allowed scope

- `.agents/skills/a-fasttask/SKILL.md`
- `.agents/skills/a-fasttask/references/conductor.md`
- `docs/runbooks/cointh-glm-quota.md`
- `docs/work-orders/WO-P1-249-cointh-secret-resolver.md`

Forbidden: secret values, credential rotation, provider/source/runtime code, `CURRENT-WORK.md`, `handoff.md`, `COLLAB.md`, scheduler/task/claim/lease/review authority, machine-wide environment changes.

## Contract

1. Canonical key name: `COINTH_GLM_AUTH_TOKEN`.
2. Fresh sessions MUST NOT scan disks, Drive, repo files, shell history, logs, or other stores to discover the token.
3. Resolve only that named key using the approved private Project Protocol / existing A-Wiki secret resolver boundary.
4. Never print, log, commit, echo, screenshot, or persist the secret value into task/result/evidence artifacts.
5. Quota preflight remains `GET https://cointh.com/glm/api/quota` with `x-api-key` and the established five-hour tuple.
6. A 401/403 from a client that has not been proven compatible is not sufficient evidence that the credential is invalid; retry once through the proven PowerShell `Invoke-RestMethod` path before classifying auth/entitlement failure.
7. This work creates no new secret store or authority system.

## Acceptance

- A-FastTask explicitly routes material GLM dispatch through canonical quota preflight.
- The conductor reference defines resolver-first/no-search behavior.
- The quota runbook uses `COINTH_GLM_AUTH_TOKEN` consistently and distinguishes client compatibility from auth failure.
- Exact changed scope is limited to the four allowed paths.
- `git diff --check`, strict UTF-8/readability, and secret-shaped added-line scan pass.
- Independent exact-SHA review returns no blocking R2 finding and exact-head hosted CI is green before merge.

## Continuity

This WO changes routing documentation only. It does not move the user's existing secret. Private machine-specific secret locations remain in the private Project Protocol, not in the public repository. If secret storage changes later, update only the private resolver configuration/Project Protocol; A-FastTask should not need a new search rule.