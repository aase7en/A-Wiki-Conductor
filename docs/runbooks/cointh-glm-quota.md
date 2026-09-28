# CoinTH GLM quota preflight

Status: BINDING PROXY-QUOTA PRE-DISPATCH POLICY / UPSTREAM ERRORS ARE POST-REQUEST EVIDENCE
Related: Issue #564, Issue #337 / PR #538, `WO-P1-243`, `docs/agent-collab/CAPABILITY_MATRIX.md`

## Purpose and authority boundary

Perform one fresh CoinTH quota GET immediately before each material GLM dispatch. A valid positive proxy balance allows the authorized real task to be attempted; it does not prove upstream health or override model capability, user authorization, work-order, claim, WIP, permission, or scope gates. Do not make a separate upstream smoke/readiness call before useful work. Let the actual GLM task establish whether that exact route works, then diagnose a concrete provider failure if one occurs.

Keep these distinct states:

- `PROXY_QUOTA_STATE = AVAILABLE | EXHAUSTED | UNKNOWN`
- `UPSTREAM_PROVIDER_READINESS = READY | THROTTLED | UNAVAILABLE | UNKNOWN`

The proxy state is computed from the fresh GET response fields below. `window_source` is retained as response metadata and never vetoes a positive remaining balance. An actual successful GLM request is evidence that the route worked for that request. An explicit provider throttle in the actual response can block only that provider/model route until its stated reset. A proxy response never proves an upstream throttle.

## Credential and request

Use only the already-bound `COINTH_GLM_AUTH_TOKEN` environment variable. Never search Drive, repository files, `.env`, shell history, logs, keychain, or other disks for credentials. Never print, persist, log, screenshot, commit, or attach the key.

Request:

```text
GET https://cointh.com/glm/api/quota
x-api-key: <COINTH_GLM_AUTH_TOKEN>
Cache-Control: no-cache
Pragma: no-cache
```

Use verified HTTPS and make exactly one bounded GET immediately before each matching GLM tool call. The global Codex hook sends the secret to system `curl` through `--config -` on stdin; the secret must not appear in curl's argv or hook output. Do not cache a previous result. Missing credential, TLS/transport error, non-200 response, or malformed response is `UNKNOWN`, never `EXHAUSTED`.

The expected five-hour fields are `remaining_5h`, `used_5h`, `limit_5h`, `window_reset_at`, and `window_reset_in_sec`. The response may also include `is_expired` and `window_source`.

## Classification

| State | Required evidence |
|---|---|
| `AVAILABLE` | HTTP 200; complete numeric five-hour tuple; nonnegative, internally consistent counters; `remaining_5h > 0`; and `is_expired` is not true. |
| `EXHAUSTED` | HTTP 200; complete valid tuple; `remaining_5h == 0`; and no contradictory expiry/counter fields. |
| `UNKNOWN` | Missing credential; TLS/transport or non-200 error; absent, malformed, incomplete or inconsistent fields; or an expired/contradictory tuple. |

When a successful fresh GET has positive `remaining_5h` and `window_source=stale`, classify the proxy as `AVAILABLE` and preserve `window_source=stale` in the audit evidence. That field describes the source's window metadata; under this policy it is not an exhaustion signal or dispatch veto. Do not report `QUOTA_UNKNOWN`, `EXHAUSTED`, `GLM_ROUTE_BLOCKED`, or upstream throttling from that field alone.

HTTP 401/403 is authentication/entitlement evidence and leaves proxy quota `UNKNOWN`; it is not quota exhaustion. An invalid counter relationship or positive expiry flag also yields `UNKNOWN` rather than guessed capacity.

## After the real GLM request

Do not issue a separate upstream admission/smoke request before a useful task. Record the real request's outcome:

- success: the exact route worked for that attempt;
- explicit upstream 429/rate-limit plus reset evidence: mark only that provider/model route throttled until the stated reset, and do not repeat GLM probes before then unless material evidence changes;
- auth, transport, model-not-found, or other concrete error: diagnose that observed failure only; do not infer quota exhaustion or loop probes.

Harvest and reconcile every terminal delegated result before any retry or replacement. Never replay `RUNNING`, `UNKNOWN`, or terminal-unharvested work. Continue independent eligible work only under the existing claim, WIP, and collision rules.

## Global Codex hook

`docs/runbooks/codex-global-cointh-quota-hook.md` defines the Mac user's Codex-global `PreToolUse` guard. It examines only explicit GLM model requests on its documented tool paths, performs the one GET above, and silently allows an available request to continue through ordinary Codex permissions. `EXHAUSTED` or `UNKNOWN` denies only that matching GLM request. The hook makes no model call, stores no quota state, and grants no task/claim/WIP/mutation/review/merge authority. It only runs for Codex tool calls on this Mac; a command started outside Codex is outside this hook.

## JEV boundary

The quota hook is deterministic and must not call JEV. Current JEV execution defaults to `OFF`; no dedicated model/executor-selection family is admitted by this runbook. If an accepted `ADVISORY` mode later permits a sanitized route suggestion, JEV may rank only among models already made eligible by deterministic capability, quota, task-authority, and WIP checks. The deterministic router remains authoritative and falls back without JEV.

## Incident lessons — 2026-09-27

- An HTTP 200 with `remaining_5h=80,000,000`, `used_5h=0`, `is_expired=false`, and `window_source=stale` was mistakenly treated as a dispatch veto. Under this corrected rule it is `AVAILABLE`; record the source metadata and attempt useful authorized GLM work.
- A Kilo CLI attempt placed the prompt after repeated `--file` flags. Kilo interpreted the prompt as a path and exited before inference. Put the prompt immediately after `kilo run`, before `--model`, `--variant`, `--dir`, and `--file` flags; harvest the failed launch and do not call it a provider failure.
- Windows worker availability is optional capacity for Mac tasks. Never wait for Windows when the Mac Kilo/SundayMCP route and the task's own gates are ready.

No secret, credential path, quota response body, or raw provider payload belongs in this public-safe repository.
