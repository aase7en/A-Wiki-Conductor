# WO-P1-566 — SundayMCP Mac restart recovery runbook

Issue: #566
Topology: CROSS_REPO
Risk: R1 LOW / docs-only operational recovery

## Goal

Persist the proven macOS restart procedure for the ChatGPT `SundayMCP Mac` connector and make it discoverable from both mandatory agent contracts.

## Binding

Authority repo base: `a4113c122ab80ef505674666df67e1f117c1a4de`
Execution repo base: `377db1c7224337cdbb72da8d675191687b5b38aa`

## Exact mutable scope

A-Wiki-Conductor:
- `docs/runbooks/sundaymcp-mac-restart.md`
- `AGENTS.md`
- this Work Order

SunDayRemoteMCP:
- `AGENTS.md`

No source/runtime/config mutation is authorized by this Work Order.

## Incident evidence

After reboot the alias existed but was stopped. Alias-only reconnect failed because tunnel-client 0.0.14 requires an MCP target. The full reconnect using the existing tunnel identity, the environment-backed runtime credential reference, and the local SunDayRemoteMCP stdio child restored `process_running=true / healthy=true / ready=true`.

A ChatGPT read-only workspace/repo smoke then passed.

The separate `npm run device:start` command was observed starting the Desktop Commander remote-device bridge; it is not the Secure MCP Tunnel path for this connector.

## Acceptance

- one canonical runbook in the authority repo;
- both mandatory `AGENTS.md` files point to it;
- no credential values or tunnel IDs are committed;
- diff remains within exact docs scope;
- strict UTF-8 and whitespace/diff checks pass;
- each repo commits/pushes only its own bounded docs change;
- cross-repo evidence folds back to Issue #566.
