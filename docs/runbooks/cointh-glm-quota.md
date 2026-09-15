# CoinTH GLM quota preflight

Status: OPERATIONAL GUIDANCE / USER-PROVIDED METHOD / LIVE_PROOF_BLOCKED_403
Source date: 2026-09-15
Related: `WO-P1-243`, `docs/agent-collab/CAPABILITY_MATRIX.md`, WO-P1-113 quota tuple.

## Purpose
Use CoinTH's quota API to check the current GLM five-hour window before launching or retrying GLM work. This avoids treating a model-call failure as the only quota signal.

According to user-provided CoinTH guidance, this quota check itself does **not** consume GLM quota. Treat that statement as `USER_PROVIDED` until an authorized live preflight confirms the behavior.

## Live verification note ? 2026-09-15
Authorized secret-safe attempts reached the endpoint but returned HTTP 403 using both the existing A-Wiki CoinTH auth-token credential and Kilo's configured `cointh-glm` API credential. No credential value was printed or persisted. Classify the current quota API path as `AUTH_REQUIRED / ENTITLEMENT_MISMATCH`; do not infer remaining quota from this endpoint until credential/entitlement is corrected. The user-provided non-consuming behavior remains unverified.

## Endpoint

```text
GET https://cointh.com/glm/api/quota
Header: x-api-key: <API KEY>
```

Expected quota fields:
- `remaining_5h`
- `used_5h`
- `limit_5h`
- `window_reset_at`
- `window_reset_in_sec`

These are the full five-hour tuple already required by the project's CoinTH/GLM provider preflight contract.
## Secret-safe usage
Do not put a real API key in repository files, task packets, logs, screenshots, or committed shell scripts. Prefer an already-authorized environment/secret resolver.

PowerShell example:

```powershell
curl.exe -s https://cointh.com/glm/api/quota `
  -H "x-api-key: $env:COINTH_GLM_API_KEY"
```

Bash example:

```bash
curl -s https://cointh.com/glm/api/quota \
  -H "x-api-key: $COINTH_GLM_API_KEY"
```

Never print the environment variable itself. Redact headers if command tracing/debug output is enabled.

## Routing rule
When GLM quota state is unknown or a GLM call appears rate-limited, prefer this read-only quota preflight before repeated model probes.

- Remaining quota available: continue only if normal provider/auth/admission/ownership gates also pass.
- `remaining_5h` exhausted: classify `RATE_LIMITED`; use `window_reset_at` / `window_reset_in_sec` for the next eligible retry time.
- HTTP 401/403: classify `AUTH_REQUIRED`; do not retry model calls blindly.
- Network/endpoint failure: classify `TRANSPORT_FAILURE`.
- Missing/malformed five-hour tuple: classify quota evidence as unverified and fail closed for automatic dispatch.

Quota evidence never transfers task ownership, bypasses claims/leases, or authorizes fallback to a different model/provider.