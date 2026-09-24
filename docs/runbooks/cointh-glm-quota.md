# CoinTH GLM quota preflight

Status: OPERATIONAL GUIDANCE / PROXY QUOTA ONLY / UPSTREAM READINESS SEPARATE
Source date: 2026-09-24
Related: Issue #337 / PR #538, `WO-P1-243`, `docs/agent-collab/CAPABILITY_MATRIX.md`, WO-P1-113 quota tuple.

## Purpose and authority boundary

Use CoinTH's quota endpoint as proxy/account quota evidence before material GLM work. It is not upstream Z.AI admission or provider-health evidence. `PROXY_QUOTA_STATE=AVAILABLE` never establishes that the upstream provider is ready.

Keep these independent states:

- `PROXY_QUOTA_STATE = AVAILABLE | EXHAUSTED | UNKNOWN`
- `UPSTREAM_PROVIDER_READINESS = READY | THROTTLED | UNAVAILABLE | UNKNOWN`

Material GLM dispatch is admitted only when proxy quota is `AVAILABLE` and upstream readiness is `READY`, in addition to existing model, route, authorization, scope, and ownership gates. Either `UNKNOWN` fails closed. Process liveness is not readiness evidence.

## Canonical secret resolution

Canonical key name: `COINTH_GLM_AUTH_TOKEN`.

Resolve only this named key through the approved private Project Protocol/environment binding or its existing approved resolver. Never recursively search disks, Drive, repository files, shell history, logs, environment dumps, or unrelated `.env` files. Never print, log, persist, screenshot, commit, or attach the secret value or its source file. If the approved binding/resolver is unavailable, stop with a typed secret-source blocker; do not guess another location or create another secret store.

The historical accepted resolver contract reuses the existing A-Wiki environment resolver boundary (`resolve_awiki_drive_root` + `AWikiDriveEnvironmentSource`) and its private Project Protocol configuration. This runbook does not expose machine-specific locations.

## Proxy quota request

```text
GET https://cointh.com/glm/api/quota
Header: x-api-key: <resolved COINTH_GLM_AUTH_TOKEN>
```

Expected five-hour fields:

- `remaining_5h`
- `used_5h`
- `limit_5h`
- `window_reset_at`
- `window_reset_in_sec`

Use the proven PowerShell `Invoke-RestMethod` client with the token held only in memory. An unproven client's HTTP 401/403 is `CLIENT_COMPATIBILITY_UNVERIFIED`; recheck once with the proven client before concluding auth/entitlement failure. HTTP 401/403 is auth/entitlement evidence, never quota exhaustion.

Provider guidance says the quota GET does not consume GLM quota. A 2026-09-16 back-to-back check observed no change in `used_5h` or `remaining_5h`; this is supporting operational evidence, not a billing guarantee.

## Evidence classification

- Valid, current five-hour tuple with positive remaining amount: `PROXY_QUOTA_STATE=AVAILABLE`.
- Valid, current five-hour tuple at exhaustion: `PROXY_QUOTA_STATE=EXHAUSTED`, with reset evidence.
- HTTP 401/403: auth/entitlement evidence; proxy quota remains `UNKNOWN` unless independently established.
- Missing, stale, malformed, or provenance-free tuple; transport error; or unavailable approved secret source: `PROXY_QUOTA_STATE=UNKNOWN`.

Upstream readiness must come from bounded live admission/smoke evidence or operator/vendor evidence that records source, observation time, reset/cooldown, and its stated freshness window. Do not silently generalize beyond that window. If freshness is not specified, classify readiness as `UNKNOWN`. Actual Git/runtime evidence remains authoritative for repository, branch, claim, process, and transport facts; operator/vendor readiness reports are bounded runtime evidence only. Keep transport classification separate: while upstream throttling is the known blocker, do not label the route transport-broken.

## Upstream throttle and reset handling

When `UPSTREAM_PROVIDER_READINESS=THROTTLED`, retain the source, observation time, provider reset/cooldown, and freshness evidence. Stop repeated GLM admission/smoke probes until reset unless material evidence changes. Continue independent safe GPT/Codex work meanwhile.

At/after the recorded reset, perform exactly one bounded live admission/smoke recheck before refilling GLM lanes. Refresh proxy quota as a separate evidence read. Refill only if proxy quota is `AVAILABLE`, upstream readiness is `READY`, and all existing route/model/authorization/scope/ownership gates pass. If the check remains throttled, retain the new reset evidence and stop further probes until its next reset or material evidence change.

## Incident example: 2026-09-24

`PROXY_QUOTA=AVAILABLE` plus `UPSTREAM_PROVIDER_READINESS=THROTTLED` means `GLM_ROUTE_READY=FALSE / UPSTREAM_PROVIDER_THROTTLED`. It does not mean `KILO_TRANSPORT_BROKEN`. Proxy quota availability is not proof of upstream Z.AI admission.

Quota and readiness evidence never transfer task ownership, bypass claims/leases, create provider authority, or authorize automatic paid-provider fallback. Do not create a scheduler, task store, claim/lease authority, or additional quota/provider authority as part of this runbook.
