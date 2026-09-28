# SundayMCP Mac — restart recovery runbook

Status: PROVEN OPERATOR RECOVERY / macOS
Authority: A-Wiki-Conductor Issue #566
Purpose: restore the ChatGPT `SundayMCP Mac` connector after a Mac restart without recreating the tunnel or confusing it with a different remote-device transport.

## Proven path

```text
ChatGPT
  -> SundayMCP Mac connector
  -> OpenAI Secure MCP Tunnel
  -> tunnel-client managed runtime: sundaymcp-mac
  -> local stdio MCP child
  -> SunDayRemoteMCP
  -> Mac filesystem / Git / bounded process tools
```

The local MCP child is:

```text
$HOME/.hermes/node/bin/node $HOME/GitHub/SunDayRemoteMCP/dist/index.js --no-onboarding
```

## Important non-equivalence

`cd $HOME/GitHub/SunDayRemoteMCP && npm run device:start` is **not** this path.

That command starts the separate Desktop Commander remote-device bridge and may connect to `mcp.desktopcommander.app`. It is useful only for that transport. It is not the OpenAI Secure MCP Tunnel runtime used by the ChatGPT `SundayMCP Mac` connector.

Do not start `npm run device:start` merely because `SundayMCP Mac` is unavailable after reboot.

## Restart checklist

### 1. Inspect the existing managed runtime first

```bash
tunnel-client --version
tunnel-client runtimes list
tunnel-client runtimes status sundaymcp-mac --json
```

Normal post-restart evidence can be:

```text
alias exists
runtime_state = stopped
```

That does not mean the connector/tunnel must be recreated.

If structured status already shows all three below, recovery is complete:

```text
process_running = true
healthy = true
ready = true
```

### 2. Verify required environment references are loaded

Check presence only; never print values:

```bash
[ -n "$CONTROL_PLANE_API_KEY" ] && echo "API KEY: LOADED" || echo "API KEY: MISSING"
[ -n "$CONTROL_PLANE_TUNNEL_ID" ] && echo "TUNNEL ID: LOADED" || echo "TUNNEL ID: MISSING"
```

If either is missing, load it only from the approved private secret source governed by A-Wiki-Data. Never `cat` the secret file, paste values into chat, or commit them.

The runtime profile intentionally stores the API key as the reference `env:CONTROL_PLANE_API_KEY`; it must not contain the key value itself.

If the approved environment file was written with CRLF line endings, strip only a trailing carriage return from the in-memory variables after loading. Do not rewrite the secret file merely for this recovery.

### 3. Verify the local stdio target exists

```bash
test -x "$HOME/.hermes/node/bin/node" && echo "NODE: OK" || echo "NODE: MISSING"
test -f "$HOME/GitHub/SunDayRemoteMCP/dist/index.js" && echo "SRM DIST: OK" || echo "SRM DIST: MISSING"
```

If either is missing, stop and recover the exact SunDayRemoteMCP repo/runtime state before attempting alternate paths.

### 4. Reconnect the managed runtime

```bash
export SUNDAY_FULL_TOOLSET=1

tunnel-client runtimes connect \
  --alias sundaymcp-mac \
  --tunnel-id "$CONTROL_PLANE_TUNNEL_ID" \
  --runtime-api-key env:CONTROL_PLANE_API_KEY \
  --profile sundaymcp-mac \
  --profile-dir "$HOME/.config/tunnel-client" \
  --mcp-command "$HOME/.hermes/node/bin/node $HOME/GitHub/SunDayRemoteMCP/dist/index.js --no-onboarding"
```

Why the long form matters: with tunnel-client 0.0.14, `runtimes connect --alias sundaymcp-mac` alone is incomplete and can fail with:

```text
connect requires --mcp-server-url or --mcp-command
```

Do not respond to that error by creating another tunnel. Supply the proven MCP target.

### 5. Verify health after reconnect

```bash
tunnel-client runtimes status sundaymcp-mac --json
```

Success requires:

```text
process_running = true
healthy = true
ready = true
runtime_state = ready
```

The profile should resolve to `$HOME/.config/tunnel-client/sundaymcp-mac.yaml`, and the MCP target should point at the SunDayRemoteMCP child above.

### 6. Prove the ChatGPT path read-only

From a ChatGPT session with the `SundayMCP Mac` connector enabled:

```text
@SundayMCP Mac

ทดสอบแบบ READ-ONLY:
อ่าน workspace ปัจจุบัน
ตรวจ repo, branch, HEAD และ Git status บน Mac
ห้ามแก้ไขไฟล์
```

A successful `sunday_workspace_info` plus `sunday_repo_snapshot` proves the external path is live. Only after this read-only proof should normal repository mutation gates be considered.

## Troubleshooting rules

- `status = stopped`: reconnect the existing alias; do not recreate the tunnel first.
- `connect requires --mcp-server-url or --mcp-command`: the reconnect command omitted the MCP target.
- required environment reference missing: load the approved secret environment; never print values.
- `dist/index.js` missing: recover/build SunDayRemoteMCP only under its normal repo/ownership gate; do not substitute `device:start`.
- runtime is `ready` but ChatGPT reports a terminated session: verify connector enablement and fresh runtime status before changing tunnel identity.

- `tunnel-client run --profile sundaymcp-mac` is a foreground diagnostic path; prefer `runtimes connect` for the managed long-lived runtime.
- Never broad-kill `tunnel-client` or `node`; process action requires exact owned PID/identity.
- Never reset/clean/stash unknown Git work as part of connector recovery.

## Proven 2026-09-28 checkpoint

On the MacBook Pro, the existing alias survived restart but was stopped. Reconnect with the full stdio target restored a managed process. Structured status then reported `process_running=true`, `healthy=true`, and `ready=true`. ChatGPT subsequently read the A-Wiki-Conductor workspace and Git snapshot successfully through `SundayMCP Mac`.

This runbook records the recovery procedure. Live runtime/Git evidence always wins over historical values such as PIDs, health ports, HEAD SHAs, or tunnel metadata.
