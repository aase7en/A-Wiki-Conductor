# CoinTH GLM quota preflight

Status: OPERATIONAL GUIDANCE / PROVEN POWERSHELL CLIENT PATH
Source date: 2026-09-15; corrected by WO-P1-249 on 2026-09-17
Related: `WO-P1-243`, `WO-P1-249`, `docs/agent-collab/CAPABILITY_MATRIX.md`, WO-P1-113 quota tuple.

## Purpose

Use CoinTH's quota API to check the current GLM five-hour window before every material GLM dispatch or retry. This avoids treating a model-call failure as the only quota signal and avoids wasting a fresh session searching for credential files.

According to provider guidance supplied by the user, this quota GET does not consume model quota. Prior zero-delta operational checks support that behavior, but do not treat it as a permanent billing guarantee.

## Endpoint

```text
GET https://cointh.com/glm/api/quota
Header: x-api-key: <resolved COINTH_GLM_AUTH_TOKEN>
```

Expected quota fields:
- `remaining_5h`
- `used_5h`
- `limit_5h`
- `window_reset_at`
- `window_reset_in_sec`

These are the full five-hour tuple already required by the project's CoinTH/GLM provider preflight contract.

## Canonical secret contract

Canonical key name: `COINTH_GLM_AUTH_TOKEN`.

Do **not** search the filesystem or Google Drive for this key. Resolve only that named key through the approved private Project Protocol / existing A-Wiki environment resolver boundary. Machine-specific secret-source paths belong in the private Project Protocol, not this public repository.

The reusable repository boundary is `resolve_awiki_drive_root` + `AWikiDriveEnvironmentSource`; A-FastTask must reuse that boundary rather than creating another secret store or resolver.

Never put the real token in repository files, task packets, logs, screenshots, shell history, CI output, or committed scripts. Never print or echo the resolved value.

If the approved resolver/source is unavailable, fail closed with the appropriate typed secret/auth blocker. Do not recursively scan for alternative `.env` files and do not ask the user to reconstruct a path already recorded in the private Project Protocol.

## Proven client behavior

The current proven quota client path is PowerShell `Invoke-RestMethod` with the token supplied in memory as the `x-api-key` header.

Conceptually:

```powershell
# $token must already have been resolved in memory by the approved resolver.
$headers = @{ 'x-api-key' = $token }
Invoke-RestMethod -Method Get -Uri 'https://cointh.com/glm/api/quota' -Headers $headers
Remove-Variable token -ErrorAction SilentlyContinue
```

Do not persist the token into a machine-wide environment variable merely for this call.

A different HTTP client can produce a different authorization result. In particular, an unproven client returning HTTP 401/403 is not sufficient evidence that the stored credential is invalid.

## Classification

- HTTP 200 + `remaining_5h > 0` => `QUOTA_AVAILABLE`.
- HTTP 200 + `remaining_5h <= 0` => `RATE_LIMITED / QUOTA_EXHAUSTED`.
- Proven PowerShell client returns 401/403 => `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`.
- Unproven/new client returns 401/403 => `CLIENT_COMPATIBILITY_UNVERIFIED`; recheck once with the proven PowerShell path before an auth conclusion.
- Network/endpoint failure => `TRANSPORT_FAILURE`.
- Missing/malformed five-hour tuple => `QUOTA_UNKNOWN`.

`QUOTA_UNKNOWN != RATE_LIMITED`.

Quota evidence never transfers task ownership, bypasses claims/leases, or authorizes silent fallback to a different model/provider.

## Fresh-session rule

A fresh session should need only the durable task/work-order plus the private Project Protocol. It must not depend on chat memory for the credential location and must not perform broad secret discovery. The storage location may change later; the A-FastTask behavior should remain stable because it binds to the resolver contract, not to ad-hoc path search.